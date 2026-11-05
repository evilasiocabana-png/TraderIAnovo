"""Regressao: launcher legado nao pode truncar a auditoria completa em 8s."""
import json
from contextlib import nullcontext
from dataclasses import asdict
from unittest.mock import Mock, patch
from application.dashboard_service import DashboardService
from application.dashboard_view_model import DashboardMT5TradeAuditViewModel

def test_full_history_survives_legacy_short_timeout():
    process = Mock()
    process.communicate.return_value = (json.dumps(asdict(DashboardMT5TradeAuditViewModel(mt5_connection_status='CONNECTED'))), '')
    with patch.dict('os.environ', {'TRADERIA_MT5_REPORT_EXTERNAL_TIMEOUT_SECONDS':'8'}), patch('application.dashboard_service.mt5_report_process_slot', return_value=nullcontext(__import__('threading').Event())), patch('application.dashboard_service.subprocess.Popen', return_value=process), patch('application.dashboard_service.time.monotonic', side_effect=[0, 9]):
        result = DashboardService()._get_mt5_trade_audit_report_external()
    assert result.mt5_connection_status == 'CONNECTED'
    assert process.communicate.call_args.kwargs['timeout'] <= 0.1
    process.kill.assert_not_called()
