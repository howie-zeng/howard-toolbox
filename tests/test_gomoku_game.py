import pytest

from gomoku.game import Color, GameError, GomokuGame


def play_moves(game: GomokuGame, moves: list[tuple[int, int]]) -> None:
    for row, col in moves:
        game.place_stone(row, col)


def test_black_wins_with_horizontal_five() -> None:
    game = GomokuGame()

    play_moves(
        game,
        [
            (7, 3),
            (0, 0),
            (7, 4),
            (0, 1),
            (7, 5),
            (0, 2),
            (7, 6),
            (0, 3),
            (7, 7),
        ],
    )

    assert game.status == "black_win"
    assert game.winner == Color.BLACK
    assert game.win_line == [(7, 3), (7, 4), (7, 5), (7, 6), (7, 7)]


def test_white_wins_with_vertical_five() -> None:
    game = GomokuGame()

    play_moves(
        game,
        [
            (0, 0),
            (2, 8),
            (0, 1),
            (3, 8),
            (0, 2),
            (4, 8),
            (0, 3),
            (5, 8),
            (1, 0),
            (6, 8),
        ],
    )

    assert game.status == "white_win"
    assert game.winner == Color.WHITE
    assert game.win_line == [(2, 8), (3, 8), (4, 8), (5, 8), (6, 8)]


def test_diagonal_win_at_board_edge() -> None:
    game = GomokuGame()

    play_moves(
        game,
        [
            (0, 0),
            (0, 1),
            (1, 1),
            (0, 2),
            (2, 2),
            (0, 3),
            (3, 3),
            (0, 4),
            (4, 4),
        ],
    )

    assert game.status == "black_win"
    assert game.win_line == [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]


def test_anti_diagonal_overline_counts_as_win() -> None:
    game = GomokuGame()

    play_moves(
        game,
        [
            (5, 5),
            (0, 0),
            (4, 6),
            (0, 1),
            (3, 7),
            (0, 2),
            (2, 8),
            (0, 3),
            (1, 9),
        ],
    )

    assert game.status == "black_win"
    assert game.win_line == [(1, 9), (2, 8), (3, 7), (4, 6), (5, 5)]


def test_rejects_occupied_cell_and_wrong_bounds() -> None:
    game = GomokuGame()

    game.place_stone(7, 7)

    with pytest.raises(GameError, match="already occupied"):
        game.place_stone(7, 7)

    with pytest.raises(GameError, match="outside"):
        game.place_stone(15, 0)


def test_rejects_moves_after_game_over() -> None:
    game = GomokuGame()

    play_moves(
        game,
        [
            (7, 3),
            (0, 0),
            (7, 4),
            (0, 1),
            (7, 5),
            (0, 2),
            (7, 6),
            (0, 3),
            (7, 7),
        ],
    )

    with pytest.raises(GameError, match="already over"):
        game.place_stone(8, 8)


def test_reset_clears_board_and_serializes_state() -> None:
    game = GomokuGame()
    game.place_stone(7, 7)
    game.reset()

    state = game.to_dict()

    assert state["status"] == "waiting"
    assert state["turn"] == "black"
    assert state["move_number"] == 0
    assert state["winner"] is None
    assert state["win_line"] == []
    assert all(cell is None for row in state["board"] for cell in row)


def test_undo_last_move_restores_board_and_turn() -> None:
    game = GomokuGame()
    game.place_stone(7, 7)
    game.place_stone(7, 8)

    undone = game.undo_last_move()

    assert undone.color == Color.WHITE
    assert game.board[7][8] is None
    assert game.board[7][7] == Color.BLACK
    assert game.turn == Color.WHITE
    assert game.status == "playing"
    assert game.move_number == 1


def test_undo_rejects_empty_board() -> None:
    game = GomokuGame()

    with pytest.raises(GameError, match="No moves"):
        game.undo_last_move()
