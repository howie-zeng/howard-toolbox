from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import socket
import string
import time
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gomoku.game import Color, GameError, GomokuGame

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STALE_ROOM_SECONDS = 60 * 60
SEAT_HOLD_SECONDS = 90
MAX_NAME_LENGTH = 24
MAX_ROOM_LENGTH = 32
DEFAULT_PORT = 8000
ROOM_ALPHABET = string.ascii_lowercase + string.digits


@dataclass
class Seat:
    player_id: str
    display_name: str
    connected: bool = True
    disconnected_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "connected": self.connected,
        }


@dataclass
class UndoRequest:
    player_id: str
    move_number: int
    move: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "move_number": self.move_number,
            "move": self.move,
        }


@dataclass
class Room:
    room_id: str
    game: GomokuGame = field(default_factory=GomokuGame)
    seats: dict[Color, Seat] = field(default_factory=dict)
    sockets: dict[str, WebSocket] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)
    rematch_accepts: set[str] = field(default_factory=set)
    undo_request: UndoRequest | None = None
    version: int = 0
    last_seen: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def touch(self) -> None:
        self.last_seen = time.time()

    def bump(self) -> None:
        self.version += 1
        self.touch()

    def seat_for(self, player_id: str) -> Color | None:
        for color, seat in self.seats.items():
            if seat.player_id == player_id:
                return color
        return None

    def release_expired_seats(self) -> None:
        now = time.time()
        expired = [
            color
            for color, seat in self.seats.items()
            if not seat.connected and seat.disconnected_at is not None and now - seat.disconnected_at > SEAT_HOLD_SECONDS
        ]
        for color in expired:
            player_id = self.seats[color].player_id
            del self.seats[color]
            self.rematch_accepts.discard(player_id)
            if self.undo_request and self.undo_request.player_id == player_id:
                self.undo_request = None

    def snapshot(self) -> dict[str, Any]:
        self.release_expired_seats()
        seats = {color.value: self.seats[color].to_dict() if color in self.seats else None for color in Color}
        spectators = max(0, len(self.names) - len(self.seats))
        return {
            "type": "snapshot",
            "room_id": self.room_id,
            "version": self.version,
            "move_number": self.game.move_number,
            "game": self.game.to_dict(),
            "seats": seats,
            "spectators": spectators,
            "rematch_accepts": list(self.rematch_accepts),
            "undo_request": self.undo_request.to_dict() if self.undo_request else None,
        }


class RoomRegistry:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def get(self, room_id: str) -> Room:
        room = self.rooms.get(room_id)
        if room is None:
            room = Room(room_id=room_id)
            self.rooms[room_id] = room
        room.touch()
        return room

    def cleanup(self) -> None:
        now = time.time()
        stale = [
            room_id
            for room_id, room in self.rooms.items()
            if not room.sockets and now - room.last_seen > STALE_ROOM_SECONDS
        ]
        for room_id in stale:
            del self.rooms[room_id]


def create_app(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> FastAPI:
    app = FastAPI(title="LAN Gomoku")
    app.state.registry = RoomRegistry()
    app.state.host = host
    app.state.port = port
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/config")
    async def config() -> dict[str, Any]:
        return {"port": port, "host": host, "lan_urls": lan_urls(port), "default_room": make_room_code()}

    @app.websocket("/ws/{room_id}")
    async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
        await websocket.accept()
        registry: RoomRegistry = app.state.registry
        registry.cleanup()
        room = registry.get(sanitize_room_id(room_id))
        player_id = ""

        try:
            while True:
                try:
                    raw = await websocket.receive_text()
                    message = parse_message(raw)
                    action = message["type"]

                    async with room.lock:
                        if action == "join":
                            player_id = sanitize_token(message.get("player_id")) or secrets.token_urlsafe(18)
                            display_name = sanitize_display_name(message.get("display_name"))
                            room.sockets[player_id] = websocket
                            room.names[player_id] = display_name
                            seat_color = room.seat_for(player_id)
                            if seat_color:
                                seat = room.seats[seat_color]
                                seat.display_name = display_name
                                seat.connected = True
                                seat.disconnected_at = None
                            room.bump()
                            await websocket.send_json({"type": "hello", "player_id": player_id, "display_name": display_name})
                            await broadcast(room)
                            continue

                        require_joined(player_id)

                        if action == "claim_seat":
                            claim_seat(room, player_id, message)
                        elif action == "move":
                            place_move(room, player_id, message)
                        elif action == "undo_request":
                            request_undo(room, player_id)
                        elif action == "undo_accept":
                            accept_undo(room, player_id)
                        elif action == "rematch_request":
                            request_rematch(room, player_id)
                        elif action == "rematch_accept":
                            accept_rematch(room, player_id)
                        elif action == "leave":
                            leave_room(room, player_id)
                        else:
                            raise GameError(f"Unknown action: {action}")

                        room.bump()
                        await broadcast(room)
                except (GameError, ValueError, TypeError, json.JSONDecodeError) as error:
                    await send_error(websocket, str(error))
                    async with room.lock:
                        await websocket.send_json(room.snapshot())
        except WebSocketDisconnect:
            async with room.lock:
                if player_id:
                    mark_disconnected(room, player_id)
                    room.bump()
                    await broadcast(room)

    return app


async def broadcast(room: Room) -> None:
    snapshot = room.snapshot()
    disconnected: list[str] = []
    for player_id, websocket in room.sockets.items():
        try:
            await websocket.send_json(snapshot)
        except RuntimeError:
            disconnected.append(player_id)
    for player_id in disconnected:
        room.sockets.pop(player_id, None)
        mark_disconnected(room, player_id)


async def send_error(websocket: WebSocket, message: str) -> None:
    await websocket.send_json({"type": "error", "message": message})


def parse_message(raw: str) -> dict[str, Any]:
    if len(raw) > 2048:
        raise GameError("Message is too large")
    message = json.loads(raw)
    if not isinstance(message, dict):
        raise GameError("Message must be a JSON object")
    action = message.get("type")
    if not isinstance(action, str) or not action:
        raise GameError("Message type is required")
    return message


def require_joined(player_id: str) -> None:
    if not player_id:
        raise GameError("Join before sending game actions")


def claim_seat(room: Room, player_id: str, message: dict[str, Any]) -> None:
    room.undo_request = None
    color = parse_color(message.get("color"))
    existing_color = room.seat_for(player_id)
    if existing_color == color:
        return
    if existing_color is not None:
        raise GameError("You already have a seat")
    if color in room.seats:
        raise GameError(f"{color.value.title()} seat is already taken")
    room.seats[color] = Seat(player_id=player_id, display_name=room.names[player_id])
    if len(room.seats) == 2 and room.game.status == "waiting":
        room.game.status = "playing"


def place_move(room: Room, player_id: str, message: dict[str, Any]) -> None:
    color = room.seat_for(player_id)
    if color is None:
        raise GameError("Spectators cannot move")
    if room.game.turn != color:
        raise GameError("It is not your turn")
    row = parse_int(message.get("row"), "row")
    col = parse_int(message.get("col"), "col")
    room.game.place_stone(row, col)
    room.rematch_accepts.clear()
    room.undo_request = None


def request_undo(room: Room, player_id: str) -> None:
    if room.seat_for(player_id) is None:
        raise GameError("Only seated players can request undo")
    if room.game.status != "playing":
        raise GameError("Undo is available only while the game is playing")
    if not room.game.moves:
        raise GameError("No moves to undo")
    latest = room.game.moves[-1]
    room.undo_request = UndoRequest(player_id=player_id, move_number=room.game.move_number, move=latest.to_dict())


def accept_undo(room: Room, player_id: str) -> None:
    if room.seat_for(player_id) is None:
        raise GameError("Only seated players can accept undo")
    if room.undo_request is None:
        raise GameError("No undo request is pending")
    if room.undo_request.player_id == player_id:
        raise GameError("The other player must accept undo")
    if room.undo_request.move_number != room.game.move_number:
        raise GameError("Undo request is stale")
    room.game.undo_last_move()
    room.undo_request = None
    room.rematch_accepts.clear()


def request_rematch(room: Room, player_id: str) -> None:
    if not room.game.is_terminal:
        raise GameError("Rematch is available after the game is over")
    if room.seat_for(player_id) is None:
        raise GameError("Only seated players can request rematch")
    room.undo_request = None
    room.rematch_accepts = {player_id}


def accept_rematch(room: Room, player_id: str) -> None:
    if not room.game.is_terminal:
        raise GameError("Rematch is available after the game is over")
    if room.seat_for(player_id) is None:
        raise GameError("Only seated players can accept rematch")
    room.rematch_accepts.add(player_id)
    seated_ids = {seat.player_id for seat in room.seats.values()}
    if len(seated_ids) == 2 and seated_ids <= room.rematch_accepts:
        room.game.reset()
        room.game.status = "playing"
        room.rematch_accepts.clear()
        room.undo_request = None


def leave_room(room: Room, player_id: str) -> None:
    room.sockets.pop(player_id, None)
    room.names.pop(player_id, None)
    for color, seat in list(room.seats.items()):
        if seat.player_id == player_id:
            del room.seats[color]
    room.rematch_accepts.discard(player_id)
    room.undo_request = None


def mark_disconnected(room: Room, player_id: str) -> None:
    room.sockets.pop(player_id, None)
    for seat in room.seats.values():
        if seat.player_id == player_id:
            seat.connected = False
            seat.disconnected_at = time.time()


def parse_color(value: Any) -> Color:
    try:
        return Color(str(value))
    except ValueError as error:
        raise GameError("Color must be black or white") from error


def parse_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GameError(f"{name} must be an integer")
    return value


def sanitize_display_name(value: Any) -> str:
    name = str(value or "").strip()
    name = "".join(char for char in name if char.isprintable())
    if not name:
        return "Player"
    return name[:MAX_NAME_LENGTH]


def sanitize_room_id(value: str) -> str:
    room_id = "".join(char for char in value.lower() if char.isalnum() or char in "-_")[:MAX_ROOM_LENGTH]
    return room_id or make_room_code()


def sanitize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(char for char in value if char.isalnum() or char in "-_")[:128]


def make_room_code(length: int = 6) -> str:
    return "".join(secrets.choice(ROOM_ALPHABET) for _ in range(length))


def lan_urls(port: int) -> list[str]:
    ips = ["127.0.0.1"]
    lan_ip = likely_lan_ip()
    if lan_ip and lan_ip not in ips:
        ips.append(lan_ip)
    host_name = socket.gethostname()
    try:
        for info in socket.getaddrinfo(host_name, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except socket.gaierror:
        pass
    return [f"http://{ip}:{port}" for ip in ips]


def likely_lan_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LAN Gomoku.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for LAN play.")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bind port.")
    parser.add_argument("--open-browser", action="store_true", help="Open the local game URL after startup.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    urls = lan_urls(args.port)
    print("LAN Gomoku URLs:")
    for url in urls:
        print(f"  {url}")
    if args.host == "0.0.0.0":
        print("LAN mode enabled. Share the non-localhost URL with coworkers on the same WiFi/LAN.")
    if args.open_browser:
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    uvicorn.run(create_app(host=args.host, port=args.port), host=args.host, port=args.port)
