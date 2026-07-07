"""Gerador de dashboard HTML estatico."""

from dataclasses import dataclass
from html import escape
from pathlib import Path

from market.market_dna import MarketPattern


@dataclass(frozen=True)
class DashboardBuilder:
    """Cria dashboard local para inspecao do MARKET DNA."""

    caminho_saida: Path = Path("resultados") / "market_dna_dashboard.html"

    def gerar(self, patterns: list[MarketPattern]) -> Path:
        """Gera arquivo HTML com a memoria operacional."""
        self.caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        self.caminho_saida.write_text(self._html(patterns), encoding="utf-8")
        return self.caminho_saida

    def _html(self, patterns: list[MarketPattern]) -> str:
        linhas = "\n".join(self._linha(pattern) for pattern in patterns)
        return self._layout(self._metricas(patterns), self._tabela(linhas))

    def _metricas(self, patterns: list[MarketPattern]) -> str:
        total = len(patterns)
        altas = sum(1 for pattern in patterns if pattern.direcao == "ALTA")
        baixas = sum(1 for pattern in patterns if pattern.direcao == "BAIXA")
        return f"<p>Snapshots: {total} | Altas: {altas} | Baixas: {baixas}</p>"

    def _tabela(self, linhas: str) -> str:
        cabecalho = "<tr><th>Data</th><th>Horario</th><th>Direcao</th><th>Preco</th></tr>"
        return f"<table>{cabecalho}<tbody>{linhas}</tbody></table>"

    def _linha(self, pattern: MarketPattern) -> str:
        return (
            "<tr>"
            f"<td>{escape(pattern.data)}</td>"
            f"<td>{escape(pattern.horario)}</td>"
            f"<td>{escape(pattern.direcao)}</td>"
            f"<td>{pattern.preco:.2f}</td>"
            "</tr>"
        )

    def _layout(self, metricas: str, tabela: str) -> str:
        return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>TraderIA WDO - MARKET DNA</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1d2433; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #d8dee8; padding: 10px; }}
    th {{ text-align: left; color: #667085; }}
  </style>
</head>
<body>
  <h1>MARKET DNA</h1>
  {metricas}
  {tabela}
</body>
</html>
"""
