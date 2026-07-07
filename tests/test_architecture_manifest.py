"""Testes da auditoria arquitetural baseada em manifesto."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import architecture_audit


REQUIRED_FIELDS = {
    "layers",
    "public_services",
    "domain_contracts",
    "providers",
    "adapters",
    "events",
    "architecture_rules",
    "architecture_rule_descriptions",
}

REQUIRED_LAYERS = {
    "application",
    "core",
    "database",
    "domain",
    "market",
    "replay",
    "research",
    "risk",
    "strategies",
    "tests",
}

REQUIRED_PUBLIC_SERVICES = {
    "ConfigurationService",
    "DashboardService",
    "ReplayService",
    "ResearchLabService",
    "SessionService",
}

REQUIRED_DOMAIN_CONTRACTS = {
    "BacktestResult",
    "DecisionContext",
    "ExecutionOrder",
    "MarketSnapshot",
    "RiskDecision",
    "StrategySignal",
}

REQUIRED_PROVIDERS = {
    "HistoricalDataProvider",
    "HistoricalDatasetCatalog",
    "HistoricalDataSourceRegistry",
}

REQUIRED_RULE_DESCRIPTIONS = {
    "dashboard_service_facade",
    "domain_purity",
    "strategies_return_strategy_signal",
    "replay_no_physical_data_access",
    "research_no_physical_data_access",
    "adapters_own_physical_formats",
    "ai_never_executes_orders",
    "real_operation_disabled",
}


class ArchitectureManifestTest(unittest.TestCase):
    """Valida comparacao entre manifesto oficial e projeto real."""

    def test_manifesto_existe(self) -> None:
        self.assertTrue(
            architecture_audit.MANIFEST_PATH.exists(),
            "architecture_manifest.json deve existir na raiz do projeto.",
        )

    def test_manifesto_e_carregado_corretamente(self) -> None:
        manifest = architecture_audit.load_manifest()

        self.assertTrue(REQUIRED_FIELDS.issubset(manifest))

    def test_manifesto_contem_camadas_servicos_contratos_e_providers_minimos(
        self,
    ) -> None:
        manifest = architecture_audit.load_manifest()

        self.assertTrue(REQUIRED_LAYERS.issubset(set(manifest["layers"])))
        self.assertTrue(
            REQUIRED_PUBLIC_SERVICES.issubset(set(manifest["public_services"]))
        )
        self.assertTrue(
            REQUIRED_DOMAIN_CONTRACTS.issubset(set(manifest["domain_contracts"]))
        )
        self.assertTrue(REQUIRED_PROVIDERS.issubset(set(manifest["providers"])))

    def test_manifesto_documenta_regras_arquiteturais_formais(self) -> None:
        manifest = architecture_audit.load_manifest()
        descriptions = manifest["architecture_rule_descriptions"]

        self.assertTrue(REQUIRED_RULE_DESCRIPTIONS.issubset(descriptions))
        self.assertIn("DashboardService", descriptions["dashboard_service_facade"])
        self.assertIn("nao executa ordens reais", descriptions["replay_no_physical_data_access"])
        self.assertIn("nao executa ordens reais", descriptions["research_no_physical_data_access"])
        self.assertIn("Operacao real permanece desabilitada", descriptions["real_operation_disabled"])

    def test_auditoria_compara_manifesto_vs_projeto(self) -> None:
        manifest = architecture_audit.load_manifest()

        report = architecture_audit.compare_manifest(manifest)
        compliance = report["manifest_compliance"]
        sections = compliance["sections"]

        self.assertIn("Manifest", "Manifest Compliance")
        self.assertIn("layers", sections)
        self.assertIn("public_services", sections)
        self.assertIn("domain_contracts", sections)
        self.assertIn("providers", sections)
        self.assertIn("adapters", sections)
        self.assertIn("events", sections)
        self.assertIn("architecture_rules", sections)
        self.assertEqual(compliance["status"], "OK")

    def test_manifesto_nao_possui_referencias_invalidas(self) -> None:
        manifest = architecture_audit.load_manifest()
        report = architecture_audit.compare_manifest(manifest)
        sections = report["manifest_compliance"]["sections"]

        invalid_sections = {
            name: section["missing"]
            for name, section in sections.items()
            if section["missing"]
        }

        self.assertEqual(
            invalid_sections,
            {},
            f"Manifesto possui referencias ausentes no projeto: {invalid_sections}",
        )

    def test_divergencias_sao_reportadas_sem_quebrar_execucao(self) -> None:
        manifest = architecture_audit.load_manifest()
        manifest["layers"] = [*manifest["layers"], "camada_inexistente"]

        report = architecture_audit.compare_manifest(manifest)
        layer_report = report["manifest_compliance"]["sections"]["layers"]

        self.assertEqual(report["manifest_compliance"]["status"], "DIVERGENT")
        self.assertIn("camada_inexistente", layer_report["missing"])
        self.assertTrue(layer_report["divergences"])

    def test_json_invalido_falha_de_forma_clara(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "architecture_manifest.json"
            path.write_text("{invalid-json", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "Manifesto de arquitetura invalido",
            ):
                architecture_audit.load_manifest(path)

    def test_auditoria_gera_relatorio_com_manifest_compliance(self) -> None:
        report = architecture_audit.run_audit(write_reports=False)
        markdown = architecture_audit._to_markdown(report)

        self.assertIn("Manifest Compliance", markdown)
        self.assertIn("Status geral", markdown)
        self.assertIn("public_services", markdown)

    def test_relatorio_json_e_serializavel(self) -> None:
        report = architecture_audit.run_audit(write_reports=False)

        serialized = json.dumps(report, ensure_ascii=False)

        self.assertIn("manifest_compliance", serialized)


if __name__ == "__main__":
    unittest.main()
