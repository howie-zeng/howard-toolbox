from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "claude-code-routines"
    / "send_outlook_summary.py"
)
_SPEC = importlib.util.spec_from_file_location("send_outlook_summary", _MODULE_PATH)
send_outlook_summary = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(send_outlook_summary)


class _Message:
    def __init__(self, subject: str, sent_on: dt.datetime) -> None:
        self.Subject = subject
        self.SentOn = sent_on


class _Items:
    def __init__(self, messages: list[_Message]) -> None:
        self._messages = messages
        self.Count = len(messages)

    def Sort(self, field: str, descending: bool) -> None:
        assert field == "[SentOn]"
        assert descending is True

    def Item(self, index: int) -> _Message:
        return self._messages[index - 1]


class _Folder:
    def __init__(self, messages: list[_Message]) -> None:
        self.Items = _Items(messages)


class _Session:
    def __init__(self, messages: list[_Message]) -> None:
        self._folder = _Folder(messages)

    def GetDefaultFolder(self, folder_id: int) -> _Folder:
        assert folder_id == 5
        return self._folder


class _Outlook:
    def __init__(self, messages: list[_Message]) -> None:
        self.Session = _Session(messages)


def test_parser_requires_override_for_duplicate_send() -> None:
    parser = send_outlook_summary._build_parser()

    assert parser.parse_args(["--send"]).allow_duplicate is False
    assert parser.parse_args(["--send", "--allow-duplicate"]).allow_duplicate is True


def test_same_day_summary_is_detected() -> None:
    summary_date = dt.date(2026, 7, 17)
    subject = "Daily RESI/CLO Summary - 2026-07-17"
    outlook = _Outlook(
        [
            _Message("Different subject", dt.datetime(2026, 7, 17, 9, 30)),
            _Message(subject, dt.datetime(2026, 7, 17, 8, 45)),
        ]
    )

    assert send_outlook_summary._same_day_summary_was_sent(
        outlook,
        subject,
        summary_date,
    )


def test_prior_day_summary_does_not_block_send() -> None:
    summary_date = dt.date(2026, 7, 17)
    subject = "Daily RESI/CLO Summary - 2026-07-17"
    outlook = _Outlook(
        [_Message(subject, dt.datetime(2026, 7, 16, 8, 45))]
    )

    assert not send_outlook_summary._same_day_summary_was_sent(
        outlook,
        subject,
        summary_date,
    )
