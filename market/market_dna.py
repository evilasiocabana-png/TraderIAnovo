"""Memoria operacional para comparar contextos de mercado."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from domain.market_state import MarketState


@dataclass(frozen=True)
class MarketPattern:
    """Padrao historico persistido pelo MARKET DNA."""

    data: str
    horario: str
    preco: float
    amplitude: float
    volume: int
    vwap: float
    atr: float
    pullback_pontos: float
    direcao: str
    posicao_no_dia: float
    resultado_operacao: float | None = None
    observacao: str = ""


@dataclass(frozen=True)
class MarketSimilarity:
    """Comparacao entre o contexto atual e um padrao historico."""

    pattern: MarketPattern
    similaridade: int
    motivos: list[str]


@dataclass
class MarketDNA:
    """Persiste e compara padroes historicos de mercado."""

    pasta: Path = Path("data") / "market_dna"

    def criar_pattern(self, estado: MarketState) -> MarketPattern:
        """Converte estado de mercado em padrao persistivel."""
        data, horario = self._separar_data_horario(estado.candle.data)
        return MarketPattern(
            data,
            horario,
            estado.preco,
            estado.candle.amplitude,
            estado.candle.volume,
            estado.vwap,
            estado.atr,
            estado.pullback_pontos,
            estado.direcao,
            estado.posicao_no_dia,
            estado.resultado_operacao,
            estado.observacao,
        )

    def salvar(self, pattern: MarketPattern) -> Path:
        """Salva um padrao em JSONL."""
        self.pasta.mkdir(parents=True, exist_ok=True)
        caminho = self.pasta / f"{pattern.data}.jsonl"
        with caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(asdict(pattern), ensure_ascii=False) + "\n")
        return caminho

    def carregar(self) -> list[MarketPattern]:
        """Carrega todos os padroes historicos."""
        if not self.pasta.exists():
            return []
        patterns: list[MarketPattern] = []
        for caminho in sorted(self.pasta.glob("*.jsonl")):
            patterns.extend(self._ler_arquivo(caminho))
        return patterns

    def comparar(self, atual: MarketPattern, limite: int = 5) -> list[MarketSimilarity]:
        """Compara um padrao atual com o historico."""
        similares = [self._comparar_um(atual, item) for item in self.carregar()]
        filtrados = [item for item in similares if item.pattern.data != atual.data]
        return sorted(filtrados, key=lambda item: item.similaridade, reverse=True)[:limite]

    def taxa_lucro(self, similares: list[MarketSimilarity]) -> float | None:
        """Calcula taxa de lucro dos padroes similares."""
        resultados = [item.pattern.resultado_operacao for item in similares]
        conhecidos = [resultado for resultado in resultados if resultado is not None]
        if not conhecidos:
            return None
        return sum(1 for resultado in conhecidos if resultado > 0) / len(conhecidos)

    def _ler_arquivo(self, caminho: Path) -> list[MarketPattern]:
        patterns: list[MarketPattern] = []
        with caminho.open("r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                if linha.strip():
                    patterns.append(self._pattern_from_dict(json.loads(linha)))
        return patterns

    def _pattern_from_dict(self, dados: dict[str, Any]) -> MarketPattern:
        campos = MarketPattern.__dataclass_fields__
        normalizado = {campo: dados.get(campo) for campo in campos}
        normalizado["amplitude"] = self._amplitude(dados)
        normalizado["direcao"] = dados.get("direcao", "NEUTRO")
        normalizado["posicao_no_dia"] = dados.get("posicao_no_dia", 0.5)
        return MarketPattern(**normalizado)

    def _amplitude(self, dados: dict[str, Any]) -> float:
        if dados.get("amplitude") is not None:
            return dados["amplitude"]
        return dados.get("maxima", 0.0) - dados.get("minima", 0.0)

    def _comparar_um(self, atual: MarketPattern, antigo: MarketPattern) -> MarketSimilarity:
        motivos: list[str] = []
        score = 25 if atual.direcao == antigo.direcao else 0
        if score:
            motivos.append(f"direcao {atual.direcao}")
        score += self._pontuar(atual.amplitude, antigo.amplitude, 20, "amplitude", motivos)
        score += self._pontuar(atual.volume, antigo.volume, 20, "volume", motivos)
        score += self._pontuar(atual.atr, antigo.atr, 15, "ATR", motivos)
        score += self._pontuar(
            atual.pullback_pontos,
            antigo.pullback_pontos,
            10,
            "pullback",
            motivos,
        )
        score += self._pontuar(
            atual.posicao_no_dia,
            antigo.posicao_no_dia,
            10,
            "posicao",
            motivos,
        )
        return MarketSimilarity(antigo, min(score, 100), motivos)

    def _pontuar(
        self,
        atual: float,
        antigo: float,
        peso: int,
        nome: str,
        motivos: list[str],
    ) -> int:
        maior = max(abs(atual), abs(antigo), 1)
        pontos = max(0, round(peso * (1 - abs(atual - antigo) / maior)))
        if pontos >= peso * 0.7:
            motivos.append(f"{nome} parecido")
        return pontos

    def _separar_data_horario(self, valor: str) -> tuple[str, str]:
        partes = valor.split()
        if len(partes) >= 2:
            return partes[0], partes[1]
        return valor, ""
