"""Testes da auditoria do Data Readiness Gate."""

import unittest

from application.data_readiness_gate_log import (
    DataReadinessGateLog,
    InMemoryDataReadinessGateLogger,
)


class DataReadinessGateLogTest(unittest.TestCase):
    """Valida logger estruturado do readiness gate."""

    def test_logger_em_memoria_registra_decisao(self) -> None:
        logger = InMemoryDataReadinessGateLogger()
        record = DataReadinessGateLog(
            dataset_id="wdo_1m_2026",
            provider="csv",
            evaluated_at="2026-06-26T18:00:00",
            requested_action="REPLAY",
            readiness_status="READY_FOR_REPLAY",
            decision="ALLOWED",
            reasons=[],
        )

        logger.log(record)

        self.assertEqual(logger.list_logs(), [record])
        self.assertEqual(logger.list_logs()[0].provider, "csv")

    def test_log_preserva_compatibilidade_com_provider_default(self) -> None:
        record = DataReadinessGateLog(
            dataset_id="wdo_1m_2026",
            evaluated_at="2026-06-26T18:00:00",
            requested_action="RESEARCH",
            readiness_status="NOT_VALIDATED",
            decision="BLOCKED",
        )

        self.assertEqual(record.provider, "unknown")
        self.assertEqual(record.reasons, [])


if __name__ == "__main__":
    unittest.main()
