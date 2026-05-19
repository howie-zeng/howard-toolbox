import time

from gomoku.game import Color
from gomoku.server import (
    SEAT_HOLD_SECONDS,
    Room,
    accept_rematch,
    accept_undo,
    claim_seat,
    lan_urls,
    parse_message,
    place_move,
    request_rematch,
    request_undo,
    sanitize_display_name,
    sanitize_room_id,
)


def test_sanitize_display_name_caps_and_defaults() -> None:
    assert sanitize_display_name("") == "Player"
    assert sanitize_display_name("  Howard  ") == "Howard"
    assert sanitize_display_name("x" * 40) == "x" * 24


def test_sanitize_room_id_keeps_url_safe_chars() -> None:
    assert sanitize_room_id("Room ABC!@#") == "roomabc"
    assert sanitize_room_id("team-1_game") == "team-1_game"


def test_lan_urls_include_requested_port() -> None:
    assert any(url.endswith(":8123") for url in lan_urls(8123))


def test_parse_message_rejects_non_objects_and_oversized_payloads() -> None:
    assert parse_message('{"type": "join"}') == {"type": "join"}

    for raw in ("[]", "{}"):
        try:
            parse_message(raw)
        except Exception as error:
            assert "Message" in str(error)
        else:
            raise AssertionError("parse_message should reject malformed messages")


def test_room_rules_bind_moves_to_seated_player_ids() -> None:
    room = Room(room_id="room1")
    room.names = {"black-id": "Black", "white-id": "White", "watch-id": "Watch"}

    claim_seat(room, "black-id", {"color": "black"})
    claim_seat(room, "white-id", {"color": "white"})

    assert room.game.status == "playing"

    try:
        place_move(room, "watch-id", {"row": 7, "col": 7})
    except Exception as error:
        assert "Spectators cannot move" in str(error)
    else:
        raise AssertionError("spectator move should be rejected")

    place_move(room, "black-id", {"row": 7, "col": 7})

    assert room.game.move_number == 1
    assert room.game.board[7][7] == "black"


def test_rematch_requires_both_seated_players() -> None:
    room = Room(room_id="room1")
    room.names = {"black-id": "Black", "white-id": "White"}
    claim_seat(room, "black-id", {"color": "black"})
    claim_seat(room, "white-id", {"color": "white"})

    for row, col, player_id in [
        (7, 3, "black-id"),
        (0, 0, "white-id"),
        (7, 4, "black-id"),
        (0, 1, "white-id"),
        (7, 5, "black-id"),
        (0, 2, "white-id"),
        (7, 6, "black-id"),
        (0, 3, "white-id"),
        (7, 7, "black-id"),
    ]:
        place_move(room, player_id, {"row": row, "col": col})

    request_rematch(room, "black-id")
    assert room.game.status == "black_win"

    accept_rematch(room, "white-id")
    assert room.game.status == "playing"
    assert room.game.move_number == 0


def test_undo_requires_other_player_acceptance() -> None:
    room = Room(room_id="room1")
    room.names = {"black-id": "Black", "white-id": "White"}
    claim_seat(room, "black-id", {"color": "black"})
    claim_seat(room, "white-id", {"color": "white"})
    place_move(room, "black-id", {"row": 7, "col": 7})
    place_move(room, "white-id", {"row": 7, "col": 8})

    request_undo(room, "white-id")
    assert room.undo_request is not None
    assert room.game.move_number == 2

    accept_undo(room, "black-id")
    assert room.undo_request is None
    assert room.game.move_number == 1
    assert room.game.board[7][8] is None
    assert room.game.turn == "white"


def test_undo_requester_cannot_self_approve() -> None:
    room = Room(room_id="room1")
    room.names = {"black-id": "Black", "white-id": "White"}
    claim_seat(room, "black-id", {"color": "black"})
    claim_seat(room, "white-id", {"color": "white"})
    place_move(room, "black-id", {"row": 7, "col": 7})

    request_undo(room, "black-id")

    try:
        accept_undo(room, "black-id")
    except Exception as error:
        assert "other player" in str(error)
    else:
        raise AssertionError("undo requester should not self-approve")


def test_expiring_disconnected_seat_clears_pending_state() -> None:
    room = Room(room_id="room1")
    room.names = {"black-id": "Black", "white-id": "White"}
    claim_seat(room, "black-id", {"color": "black"})
    claim_seat(room, "white-id", {"color": "white"})
    place_move(room, "black-id", {"row": 7, "col": 7})
    request_undo(room, "black-id")
    room.rematch_accepts = {"black-id"}

    room.seats[Color.BLACK].connected = False
    room.seats[Color.BLACK].disconnected_at = time.time() - SEAT_HOLD_SECONDS - 1
    room.release_expired_seats()

    assert Color.BLACK not in room.seats
    assert room.undo_request is None
    assert room.rematch_accepts == set()
