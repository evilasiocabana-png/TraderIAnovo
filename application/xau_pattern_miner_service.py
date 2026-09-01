"""Application facade for the causal multi-market Pattern Miner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from application.model28_pattern_miner_shadow import (
    DEFAULT_MODEL_28_RESEARCH_REPORT_PATH,
    synchronize_model28_replay_contracts,
)
from domain.operational_pattern import OperationalPatternSpec, ShadowSignalResult
from replay.pattern_miner import PatternMinerConfig, PatternReplayEngine
from replay.pattern_miner.models import PatternReplayState, ReplaySpeed
from replay.pattern_miner.operational import OperationalPatternStore, ShadowSignalJournal


DEFAULT_HISTORICO_XAU_PATH = (
    Path(__file__).resolve().parents[1]
    / ".traderia"
    / "research"
    / "historicoXAU"
    / "historicoXAU_XAUUSD_M5.csv"
)
DEFAULT_OPERATIONAL_PATTERN_STORE_PATH = (
    DEFAULT_HISTORICO_XAU_PATH.parent / "model28_operational_patterns.json"
)
DEFAULT_SHADOW_SIGNAL_JOURNAL_PATH = (
    DEFAULT_HISTORICO_XAU_PATH.parent / "model28_shadow_signals.json"
)
DEFAULT_MARKET_HISTORY_ROOT = (
    Path(__file__).resolve().parents[1]
    / ".traderia"
    / "research"
    / "historicosMercado"
)


def pattern_miner_dataset_path(symbol: str) -> Path:
    """Return the isolated 100k M5 closed-candle dataset for one market."""

    normalized = str(symbol or "").strip().upper()
    if normalized == "XAUUSD":
        return DEFAULT_HISTORICO_XAU_PATH
    return (
        DEFAULT_MARKET_HISTORY_ROOT
        / f"historico{normalized}"
        / f"historico{normalized}.csv"
    )


@dataclass(slots=True)
class XauPatternMinerService:
    """Expose one isolated market miner without any execution dependency."""

    engine: PatternReplayEngine = field(
        default_factory=lambda: PatternReplayEngine(PatternMinerConfig())
    )
    dataset_path: Path = DEFAULT_HISTORICO_XAU_PATH
    operational_store_path: Path = DEFAULT_OPERATIONAL_PATTERN_STORE_PATH
    shadow_journal_path: Path = DEFAULT_SHADOW_SIGNAL_JOURNAL_PATH
    symbol: str = "XAUUSD"
    timeframe: str = "M5"
    dataset_name: str = "historicoXAU"

    @classmethod
    def for_symbol(cls, symbol: str) -> "XauPatternMinerService":
        normalized = str(symbol or "").strip().upper()
        if not normalized:
            raise ValueError("Ativo obrigatorio para o Pattern Miner.")
        return cls(
            dataset_path=pattern_miner_dataset_path(normalized),
            operational_store_path=DEFAULT_OPERATIONAL_PATTERN_STORE_PATH,
            shadow_journal_path=DEFAULT_SHADOW_SIGNAL_JOURNAL_PATH,
            symbol=normalized,
            timeframe="M5",
            dataset_name=f"historico{normalized.removesuffix('USD') if normalized == 'XAUUSD' else normalized}",
        )

    def load(self) -> PatternReplayState:
        """Load this market's official closed-candle source."""

        return self.engine.load_dataset(
            self.dataset_path,
            name=self.dataset_name,
            symbol=self.symbol,
            timeframe=self.timeframe,
        )

    def ensure_loaded(self) -> PatternReplayState:
        """Load once and preserve replay progress across UI reruns."""

        state = self.engine.state()
        return state if state.dataset_loaded else self.load()

    def start(self, speed: str) -> PatternReplayState:
        return self.engine.start(ReplaySpeed(speed))

    def pause(self) -> PatternReplayState:
        return self.engine.pause()

    def resume(self) -> PatternReplayState:
        return self.engine.resume()

    def reset(self) -> PatternReplayState:
        return self.engine.reset()

    def process_batch(self, quantity: int | None = None) -> PatternReplayState:
        return self.engine.process_batch(quantity)

    def run_to_end(self) -> PatternReplayState:
        return self.engine.run_to_end()

    def restore_cache(self) -> PatternReplayState:
        return self.engine.restore_cache()

    def state(self) -> PatternReplayState:
        return self.engine.state()

    @property
    def summary_path(self) -> Path:
        return self.dataset_path.parent / "pattern_miner_summary.json"

    def save_summary(self) -> dict[str, object]:
        """Persist only the lightweight final evidence consumed by the UI."""

        state = self.state()
        result = state.result
        info = self.engine.dataset_info
        if result is None or info is None or state.status.value != "FINISHED":
            raise ValueError(f"Replay {self.symbol} ainda nao foi concluido.")
        rankings = [
            {
                "pattern_id": item.pattern_id,
                "events": item.display_sequence,
                "direction": item.direction_label,
                "occurrences": item.occurrences,
                "mfe_mean_atr": item.mfe_mean_atr,
                "mae_mean_atr": item.mae_mean_atr,
                "first_passage_1_atr": item.first_passage_1_atr,
                "first_passage_2_atr": item.first_passage_2_atr,
                "first_passage_1_expectancy_net": (
                    item.first_passage_1_expectancy_net
                ),
                "first_passage_2_expectancy_net": (
                    item.first_passage_2_expectancy_net
                ),
                "fp1_discovery_net": item.fp1_discovery_net,
                "fp1_validation_net": item.fp1_validation_net,
                "fp1_oos_net": item.fp1_oos_net,
                "fp2_discovery_net": item.fp2_discovery_net,
                "fp2_validation_net": item.fp2_validation_net,
                "fp2_oos_net": item.fp2_oos_net,
                "discovery": item.discovery_performance,
                "validation": item.validation_performance,
                "oos": item.oos_performance,
                "expectancy": item.expectancy,
                "score": item.score,
            }
            for item in result.rankings
        ]
        stat = self.dataset_path.stat()
        payload: dict[str, object] = {
            "schema_version": "pattern-miner-market-summary-v1",
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "dataset_name": self.dataset_name,
            "dataset_path": str(self.dataset_path),
            "dataset_size": stat.st_size,
            "dataset_mtime_ns": stat.st_mtime_ns,
            "dataset_fingerprint": info.fingerprint,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_candles": state.total_candles,
            "event_counts": dict(state.event_counts),
            "discovered_patterns": result.discovered_patterns,
            "candidate_patterns": result.candidate_patterns,
            "total_occurrences": result.total_occurrences,
            "cache_key": result.cache_key,
            "causality_passed": bool(
                result.causality_audit and result.causality_audit.passed
            ),
            "rankings": rankings,
        }
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.summary_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        for attempt in range(20):
            try:
                os.replace(temporary, self.summary_path)
                break
            except PermissionError:
                if attempt == 19:
                    self.summary_path.write_bytes(temporary.read_bytes())
                    temporary.unlink(missing_ok=True)
                    break
                import time

                time.sleep(0.1)
        return payload

    def load_summary(self) -> dict[str, object] | None:
        """Read a summary only while it matches the current dataset file."""

        if not self.summary_path.exists() or not self.dataset_path.exists():
            return None
        try:
            payload = json.loads(self.summary_path.read_text(encoding="utf-8"))
            stat = self.dataset_path.stat()
            if (
                str(payload.get("symbol", "")).upper() != self.symbol
                or int(payload.get("dataset_size", -1)) != stat.st_size
                or int(payload.get("dataset_mtime_ns", -1)) != stat.st_mtime_ns
            ):
                return None
            return payload
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def calculate_maximum(self) -> PatternReplayState:
        """Run or restore one complete Maximum replay and persist its summary."""

        self.ensure_loaded()
        state = self.restore_cache()
        if state.status.value != "FINISHED":
            self.start("Maximum")
            state = self.run_to_end()
        if state.status.value == "FINISHED":
            self.save_summary()
        return state

    def release(self) -> None:
        """Release candles and records before the next sequential market."""

        self.engine = PatternReplayEngine(PatternMinerConfig())

    def operational_specs(self) -> tuple[OperationalPatternSpec, ...]:
        return OperationalPatternStore(self.operational_store_path).load()

    def promote_pattern(self, pattern_id: str) -> OperationalPatternSpec:
        """Keep promotion automatic and tied to the frozen Replay report."""

        raise ValueError(
            f"Promocao manual desnecessaria para {pattern_id}. O M28 promove "
            "automaticamente os contratos aprovados em Discovery, Validation "
            "e OOS nas 100 mil velas."
        )

    def set_shadow(self, versioned_id: str, enabled: bool) -> OperationalPatternSpec:
        return OperationalPatternStore(self.operational_store_path).set_shadow(
            versioned_id,
            enabled,
        )

    def shadow_results(self) -> tuple[ShadowSignalResult, ...]:
        return ShadowSignalJournal(self.shadow_journal_path).load()

    def prepare_adaptive_shadow(self, limit: int = 12) -> tuple[OperationalPatternSpec, ...]:
        """Synchronize the Replay-approved contracts used by live M28 Demo."""

        del limit
        prepared = synchronize_model28_replay_contracts(
            registry_path=self.operational_store_path,
            report_path=DEFAULT_MODEL_28_RESEARCH_REPORT_PATH,
            config=self.engine.config,
        )
        return tuple(
            item
            for item in prepared
            if item.symbol == self.symbol and item.timeframe == self.timeframe
        )
