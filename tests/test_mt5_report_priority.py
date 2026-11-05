import threading
import subprocess
from contextlib import nullcontext
from unittest.mock import Mock, patch
from core.mt5_external_process_gate import mt5_external_process_slot, mt5_report_process_slot
from application.dashboard_service import DashboardService


def test_operational_reader_preempts_report_without_parallel_slot():
    entered = threading.Event()
    finished = threading.Event()
    def reader():
        with mt5_external_process_slot(timeout=2) as ok:
            assert ok
            entered.set()
        finished.set()
    with mt5_report_process_slot() as cancel:
        assert cancel is not None
        t = threading.Thread(target=reader)
        t.start()
        assert cancel.wait(1)
        assert not entered.is_set()
    assert finished.wait(2)
    t.join()


def test_report_cannot_start_while_operation_holds_slot():
    with mt5_external_process_slot(timeout=0) as ok:
        assert ok
        with mt5_report_process_slot() as cancel:
            assert cancel is None


def test_preempted_report_stops_only_its_worker_and_returns_fallback():
    cancel=threading.Event()
    process=Mock()
    def busy(**kwargs):
        cancel.set()
        raise subprocess.TimeoutExpired('read only report', .1)
    process.communicate.side_effect=busy
    with patch('application.dashboard_service.mt5_report_process_slot',return_value=nullcontext(cancel)), patch('application.dashboard_service.subprocess.Popen',return_value=process), patch('application.dashboard_service.terminate_process_tree') as stop:
        assert DashboardService()._get_mt5_trade_audit_report_external() is None
        stop.assert_called_once_with(process)
    process.communicate.assert_called_once()


def test_report_exception_releases_slot():
    try:
        with mt5_report_process_slot() as cancel:
            assert cancel is not None
            raise RuntimeError('report failed')
    except RuntimeError:
        pass
    with mt5_external_process_slot(timeout=0) as ok:
        assert ok
