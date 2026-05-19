from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

BOARD_SIZE = 15
WIN_LENGTH = 5


class GameError(ValueError):
    """Raised when a requested game action is illegal."""


class Color(StrEnum):
    BLACK = "black"
    WHITE = "white"

    @property
    def other(self) -> Color:
        return Color.WHITE if self == Color.BLACK else Color.BLACK


@dataclass(frozen=True)
class Move:
    row: int
    col: int
    color: Color

    def to_dict(self) -> dict[str, Any]:
        return {"row": self.row, "col": self.col, "color": self.color.value, "notation": coordinate_label(self.row, self.col)}


@dataclass
class GomokuGame:
    size: int = BOARD_SIZE
    board: list[list[Color | None]] = field(init=False)
    turn: Color = Color.BLACK
    status: str = "waiting"
    winner: Color | None = None
    win_line: list[tuple[int, int]] = field(default_factory=list)
    moves: list[Move] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.size < WIN_LENGTH:
            raise ValueError(f"Board size must be at least {WIN_LENGTH}")
        self.board = [[None for _ in range(self.size)] for _ in range(self.size)]

    @property
    def move_number(self) -> int:
        return len(self.moves)

    def place_stone(self, row: int, col: int) -> Move:
        if self.is_terminal:
            raise GameError("Game is already over")
        self._validate_position(row, col)
        if self.board[row][col] is not None:
            raise GameError("Cell is already occupied")

        color = self.turn
        move = Move(row=row, col=col, color=color)
        self.board[row][col] = color
        self.moves.append(move)
        self.status = "playing"

        line = self._winning_line(row, col, color)
        if line:
            self.status = f"{color.value}_win"
            self.winner = color
            self.win_line = line
        elif self.move_number == self.size * self.size:
            self.status = "draw"
        else:
            self.turn = color.other

        return move

    @property
    def is_terminal(self) -> bool:
        return self.status in {"black_win", "white_win", "draw"}

    def undo_last_move(self) -> Move:
        if not self.moves:
            raise GameError("No moves to undo")

        move = self.moves.pop()
        self.board[move.row][move.col] = None
        self.turn = move.color
        self.status = "playing" if self.moves else "waiting"
        self.winner = None
        self.win_line = []
        return move

    def reset(self) -> None:
        self.board = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.turn = Color.BLACK
        self.status = "waiting"
        self.winner = None
        self.win_line = []
        self.moves = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "board": [[cell.value if cell else None for cell in row] for row in self.board],
            "turn": self.turn.value,
            "status": self.status,
            "winner": self.winner.value if self.winner else None,
            "win_line": [{"row": row, "col": col, "notation": coordinate_label(row, col)} for row, col in self.win_line],
            "moves": [move.to_dict() for move in self.moves],
            "move_number": self.move_number,
        }

    def _validate_position(self, row: int, col: int) -> None:
        if not 0 <= row < self.size or not 0 <= col < self.size:
            raise GameError(f"Move ({row}, {col}) is outside the {self.size}x{self.size} board")

    def _winning_line(self, row: int, col: int, color: Color) -> list[tuple[int, int]]:
        for row_step, col_step in ((1, 0), (0, 1), (1, 1), (1, -1)):
            line = self._line_through(row, col, row_step, col_step, color)
            if len(line) >= WIN_LENGTH:
                return line
        return []

    def _line_through(self, row: int, col: int, row_step: int, col_step: int, color: Color) -> list[tuple[int, int]]:
        before = self._collect_direction(row, col, -row_step, -col_step, color)
        after = self._collect_direction(row, col, row_step, col_step, color)
        return list(reversed(before)) + [(row, col)] + after

    def _collect_direction(self, row: int, col: int, row_step: int, col_step: int, color: Color) -> list[tuple[int, int]]:
        cells: list[tuple[int, int]] = []
        current_row = row + row_step
        current_col = col + col_step

        while 0 <= current_row < self.size and 0 <= current_col < self.size:
            if self.board[current_row][current_col] != color:
                break
            cells.append((current_row, current_col))
            current_row += row_step
            current_col += col_step

        return cells


def coordinate_label(row: int, col: int) -> str:
    return f"{chr(ord('A') + col)}{row + 1}"
