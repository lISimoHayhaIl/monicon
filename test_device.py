"""Tests for the HID device layer (no hardware required)."""

import pytest
from unittest.mock import MagicMock, patch

from msi_monitor.device import (
    _build_report,
    _parse_response,
    MSIMonitor,
    REPORT_ID,
    MSG_LEN,
    INPUT_SOURCES,
)


class TestBuildReport:
    def test_length_is_always_64(self):
        for cmd in [b'5800110', b'5800130', b'5800190']:
            report = _build_report(cmd)
            assert len(report) == MSG_LEN

    def test_starts_with_report_id(self):
        report = _build_report(b'5800110')
        assert report[0] == REPORT_ID

    def test_contains_cmd_then_terminator(self):
        report = _build_report(b'5800130')
        # bytes 1-7 = command, byte 8 = 0x0d
        assert report[1:8] == b'5800130'
        assert report[8] == 0x0d

    def test_padded_with_zeros(self):
        report = _build_report(b'5800110')
        assert all(b == 0 for b in report[9:])


class TestParseResponse:
    def test_valid_response(self):
        # Simulate: ReportID=0x01, "5b00130DE2A", 0x0d, zeros
        body = bytes([REPORT_ID]) + b'5b00130DE2A' + b'\x0d' + b'\x00' * 50
        result = _parse_response(body)
        assert result == '5b00130DE2A'

    def test_wrong_report_id_returns_none(self):
        body = bytes([0x02]) + b'5b00130' + b'\x0d' + b'\x00' * 55
        assert _parse_response(body) is None

    def test_empty_data_returns_none(self):
        assert _parse_response(b'') is None

    def test_strips_trailing_nulls(self):
        body = bytes([REPORT_ID]) + b'5b00110' + b'\x0d' + b'\x00' * 55
        result = _parse_response(body)
        assert result == '5b00110'


class TestMSIMonitorInputSources:
    def test_all_known_sources_build_valid_reports(self):
        for name, cmd in INPUT_SOURCES.items():
            report = _build_report(cmd)
            assert len(report) == MSG_LEN, f"Bad report length for {name}"

    def test_set_input_raises_on_unknown_source(self):
        mon = MSIMonitor()
        mon._dev = MagicMock()
        with pytest.raises(ValueError, match="Unknown input source"):
            mon.set_input("vga")

    def test_set_input_sends_correct_dp_command(self):
        mon = MSIMonitor()
        mon._dev = MagicMock()
        mon._dev.read.return_value = []  # no response

        with patch.object(mon, '_send') as mock_send:
            mon.set_input("dp")
            mock_send.assert_called_once_with(INPUT_SOURCES["dp"])

    def test_set_input_case_insensitive(self):
        mon = MSIMonitor()
        mon._dev = MagicMock()
        mon._dev.read.return_value = []

        with patch.object(mon, '_send') as mock_send:
            mon.set_input("DP")
            mock_send.assert_called_once_with(INPUT_SOURCES["dp"])
