from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[1] / "gomoku" / "static"


def test_board_static_structure_is_preserved() -> None:
    index_html = (STATIC_DIR / "index.html").read_text()
    app_js = (STATIC_DIR / "app.js").read_text()

    assert '<div class="board-shell">' in index_html
    assert '<div id="board" class="board"' in index_html
    assert "querySelectorAll(\".cell\")" in app_js
    assert "const STAR_POINTS = [" in app_js
    assert "addAxisLabel" in app_js


def test_request_dialog_and_leave_seat_controls_are_wired() -> None:
    index_html = (STATIC_DIR / "index.html").read_text()
    app_js = (STATIC_DIR / "app.js").read_text()
    styles_css = (STATIC_DIR / "styles.css").read_text()

    assert '<dialog id="requestDialog"' in index_html
    assert 'id="requestAcceptButton"' in index_html
    assert 'id="requestRejectButton"' in index_html
    assert 'id="leaveSeatButton"' in index_html
    assert '<script src="/static/app.js?v=' in index_html

    assert "showRequestDialog" in app_js
    assert 'rejectType: "undo_reject"' in app_js
    assert 'rejectType: "rematch_reject"' in app_js
    assert "send({ type: state.pendingRequest[actionKey] })" in app_js
    assert 'send({ type: "release_seat" })' in app_js
    assert "requestDialog.showModal()" in app_js

    assert ".request-dialog" in styles_css
    assert ".dialog-actions" in styles_css


def test_board_coordinate_counts_match_15_by_15_board() -> None:
    app_js = (STATIC_DIR / "app.js").read_text()

    assert "const BOARD_SIZE = 15;" in app_js
    assert "for (let index = 0; index < BOARD_SIZE; index += 1)" in app_js
    assert "for (let row = 0; row < BOARD_SIZE; row += 1)" in app_js
    assert "for (let col = 0; col < BOARD_SIZE; col += 1)" in app_js
    assert app_js.count("addAxisLabel(") == 5
