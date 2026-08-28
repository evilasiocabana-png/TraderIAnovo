"""Replay engine dedicated to causal XAUUSD pattern research."""

from __future__ import annotations

from collections import Counter, deque
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
from pathlib import Path
import pickle
from threading import RLock
import time

from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.causality import PatternCausalityAuditor
from replay.pattern_miner.detectors import CausalEventDetector
from replay.pattern_miner.indicators import IndicatorEngine
from replay.pattern_miner.mining import PatternMiner
from replay.pattern_miner.models import (
    CandleBar,
    EventRecord,
    IndicatorFrame,
    MarketEvent,
    PatternMinerResult,
    PatternReplayState,
    PatternReplayStatus,
    ReplaySpeed,
)


@dataclass(frozen=True, slots=True)
class PatternDatasetInfo:
    """Metadata for the closed-candle historical source."""

    name: str
    symbol: str
    timeframe: str
    path: Path
    candles: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    fingerprint: str


class PatternReplayEngine:
    """Process closed candles sequentially and mine causal event sequences."""

    def __init__(self, config: PatternMinerConfig | None = None) -> None:
        self.config = config or PatternMinerConfig()
        self.indicator_engine = IndicatorEngine(self.config)
        self.detector = CausalEventDetector(self.config)
        self.pattern_miner = PatternMiner(self.config)
        self.causality_auditor = PatternCausalityAuditor(self.config)
        self.candles: list[CandleBar] = []
        self.indicators = IndicatorFrame()
        self.records: list[EventRecord] = []
        self.dataset_info: PatternDatasetInfo | None = None
        self.status = PatternReplayStatus.EMPTY
        self.speed = ReplaySpeed.MAXIMUM
        self.current_index = -1
        self.event_counts: Counter[str] = Counter()
        self.recent_events: deque[MarketEvent] = deque(maxlen=30)
        self._live_tokens: deque[tuple[int, str, int]] = deque(maxlen=80)
        self.active_patterns = 0
        self.completed_pattern_occurrences = 0
        self.result: PatternMinerResult | None = None
        self.logs: deque[str] = deque(maxlen=100)
        self.error = ""
        self.cache_restored = False
        self._state_lock = RLock()

    def load_dataset(
        self,
        path: str | Path,
        *,
        name: str = "historicoXAU",
        symbol: str = "XAUUSD",
        timeframe: str = "M5",
    ) -> PatternReplayState:
        """Load only closed candles and precompute causal indicator columns."""

        with self._state_lock:
            started = time.perf_counter()
            try:
                source = Path(path)
                candles = self._read_closed_candles(source)
                if not candles:
                    raise ValueError("historicoXAU nao possui candles fechados validos.")
                fingerprint = self._sha256(source)
                self.candles = candles
                self.indicators = self.indicator_engine.compute(candles)
                self.dataset_info = PatternDatasetInfo(
                    name=name,
                    symbol=symbol,
                    timeframe=timeframe,
                    path=source,
                    candles=len(candles),
                    first_timestamp=candles[0].timestamp,
                    last_timestamp=candles[-1].timestamp,
                    fingerprint=fingerprint,
                )
                self._reset_processing()
                self.status = PatternReplayStatus.READY
                self._log(
                    f"Dataset carregado: {len(candles):,} candles fechados em "
                    f"{time.perf_counter() - started:.2f}s."
                )
            except (OSError, ValueError, csv.Error) as exc:
                self.error = str(exc)
                self.status = PatternReplayStatus.ERROR
                self._log(f"Falha ao carregar dataset: {exc}")
            return self.state()

    def start(self, speed: ReplaySpeed | str = ReplaySpeed.MAXIMUM) -> PatternReplayState:
        """Start or continue processing from the current candle."""

        with self._state_lock:
            if not self.candles:
                return self.state()
            self.speed = speed if isinstance(speed, ReplaySpeed) else ReplaySpeed(speed)
            if self.current_index >= len(self.candles) - 1:
                self.status = PatternReplayStatus.FINISHED
                return self.state()
            self.status = PatternReplayStatus.RUNNING
            self._log(f"Replay iniciado em modo {self.speed.value}.")
            return self.state()

    def pause(self) -> PatternReplayState:
        """Pause without losing causal state."""

        with self._state_lock:
            if self.status == PatternReplayStatus.RUNNING:
                self.status = PatternReplayStatus.PAUSED
                self._log("Replay pausado.")
            return self.state()

    def resume(self) -> PatternReplayState:
        """Resume a paused replay."""

        with self._state_lock:
            if self.status == PatternReplayStatus.PAUSED:
                self.status = PatternReplayStatus.RUNNING
                self._log("Replay retomado.")
            return self.state()

    def reset(self) -> PatternReplayState:
        """Reset replay progress while retaining the loaded dataset."""

        with self._state_lock:
            self._reset_processing()
            self.status = PatternReplayStatus.READY if self.candles else PatternReplayStatus.EMPTY
            self._log("Replay reiniciado.")
            return self.state()

    def process_batch(self, quantity: int | None = None) -> PatternReplayState:
        """Process a bounded batch; every candle is still handled sequentially."""

        with self._state_lock:
            if self.status != PatternReplayStatus.RUNNING:
                return self.state()
            remaining = len(self.candles) - (self.current_index + 1)
            if remaining <= 0:
                return self._finish()
            batch_size = min(quantity or self.batch_size(), remaining)
            started = time.perf_counter()
            for _ in range(batch_size):
                index = self.current_index + 1
                record = self.detector.process(index, self.candles, self.indicators)
                self.records.append(record)
                self.current_index = index
                self._consume_events(record)
                processed = index + 1
                if processed == self.config.warmup_candles:
                    self._log("Warm-up concluido.")
                if processed % 10000 == 0:
                    self._log(f"{processed:,} / {len(self.candles):,} candles.")
            elapsed = time.perf_counter() - started
            if batch_size >= 1000:
                self._log(f"Lote de {batch_size:,} candles processado em {elapsed:.2f}s.")
            if self.current_index >= len(self.candles) - 1:
                return self._finish()
            return self.state()

    def run_to_end(self) -> PatternReplayState:
        """Process all remaining candles without per-candle rendering."""

        with self._state_lock:
            self.start(ReplaySpeed.MAXIMUM)
            return self.process_batch(len(self.candles))

    def restore_cache(self) -> PatternReplayState:
        """Restore a compatible completed Event Store when available."""

        with self._state_lock:
            cache_path = self.cache_path
            if cache_path is None or not cache_path.exists():
                return self.state()
            try:
                with gzip.open(cache_path, "rb") as handle:
                    payload = pickle.load(handle)
                if payload.get("cache_key") != self.cache_key:
                    return self.state()
                self.records = payload["records"]
                self.current_index = len(self.records) - 1
                self.event_counts = Counter(payload["event_counts"])
                self.recent_events = deque(payload["recent_events"], maxlen=30)
                self.result = payload["result"]
                self.completed_pattern_occurrences = self.result.total_occurrences
                self.active_patterns = 0
                self.status = PatternReplayStatus.FINISHED
                self.cache_restored = True
                self._log("Event Store restaurado do cache compativel.")
            except (OSError, EOFError, pickle.PickleError, AttributeError, KeyError) as exc:
                self._log(f"Cache ignorado: {exc}")
            return self.state()

    def batch_size(self) -> int:
        """Return a UI-friendly batch size for the selected speed."""

        if self.speed == ReplaySpeed.VISUAL:
            return 1
        if self.speed == ReplaySpeed.FAST:
            return 500
        return max(len(self.candles) - (self.current_index + 1), 1)

    def state(self) -> PatternReplayState:
        """Return an immutable UI state."""

        with self._state_lock:
            current = self.records[self.current_index] if 0 <= self.current_index < len(self.records) else None
            info = self.dataset_info
            return PatternReplayState(
                status=self.status,
                speed=self.speed,
                dataset_loaded=bool(self.candles),
                dataset_name=info.name if info else "historicoXAU",
                symbol=info.symbol if info else "XAUUSD",
                timeframe=info.timeframe if info else "M5",
                total_candles=len(self.candles),
                current_index=self.current_index,
                current_record=current,
                event_counts=dict(self.event_counts),
                recent_events=tuple(self.recent_events),
                active_patterns=self.active_patterns,
                completed_pattern_occurrences=self.completed_pattern_occurrences,
                result=self.result,
                logs=tuple(self.logs),
                error=self.error,
                cache_restored=self.cache_restored,
            )

    @property
    def cache_key(self) -> str:
        """Combine dataset and threshold fingerprints."""

        if self.dataset_info is None:
            return ""
        raw = f"{self.dataset_info.fingerprint}|{self.config.fingerprint()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    @property
    def cache_path(self) -> Path | None:
        """Return the local cache path for the current research contract."""

        if self.dataset_info is None:
            return None
        return self.dataset_info.path.parent / f"pattern_miner_event_store_{self.cache_key}.pkl.gz"

    def _finish(self) -> PatternReplayState:
        if self.status == PatternReplayStatus.FINISHED and self.result is not None:
            return self.state()
        self._log("Replay concluido. Pattern Mining iniciado.")
        started = time.perf_counter()
        self.result = self.pattern_miner.mine(
            self.records,
            self.candles,
            cache_key=self.cache_key,
        )
        audit_started = time.perf_counter()
        causality_audit = self.causality_auditor.audit(self.candles, self.records)
        self.result = PatternMinerResult(
            rankings=self.result.rankings,
            discovered_patterns=self.result.discovered_patterns,
            candidate_patterns=self.result.candidate_patterns,
            total_occurrences=self.result.total_occurrences,
            discovery_end_index=self.result.discovery_end_index,
            validation_end_index=self.result.validation_end_index,
            cache_key=self.result.cache_key,
            causality_audit=causality_audit,
        )
        audit_status = "APROVADA" if causality_audit.passed else "REPROVADA"
        self._log(
            f"Auditoria causal {audit_status} em {time.perf_counter() - audit_started:.2f}s "
            f"({len(causality_audit.checks)} prefixos)."
        )
        self.completed_pattern_occurrences = self.result.total_occurrences
        self.active_patterns = 0
        self.status = PatternReplayStatus.FINISHED
        self._log(
            f"Pattern Mining concluido em {time.perf_counter() - started:.2f}s: "
            f"{self.result.candidate_patterns:,} candidatos e "
            f"{self.result.total_occurrences:,} ocorrencias."
        )
        self._save_cache()
        return self.state()

    def _save_cache(self) -> None:
        cache_path = self.cache_path
        if cache_path is None or self.result is None:
            return
        payload = {
            "cache_key": self.cache_key,
            "records": self.records,
            "event_counts": dict(self.event_counts),
            "recent_events": tuple(self.recent_events),
            "result": self.result,
        }
        temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
        try:
            with gzip.open(temporary, "wb", compresslevel=5) as handle:
                pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
            temporary.replace(cache_path)
            self._log(f"Event Store salvo em cache: {cache_path.name}.")
        except OSError as exc:
            self._log(f"Nao foi possivel salvar cache: {exc}")
            temporary.unlink(missing_ok=True)

    def _consume_events(self, record: EventRecord) -> None:
        for event in record.events:
            self.event_counts[event.event_type] += 1
            self.recent_events.append(event)
            self._live_tokens.append((record.index, event.event_type, event.direction))
        while self._live_tokens and record.index - self._live_tokens[0][0] > self.config.max_event_distance:
            self._live_tokens.popleft()
        # Streamlit may overlap fragment/session reruns; count from an immutable view.
        token_snapshot = tuple(self._live_tokens)
        directional = [token for token in token_snapshot if token[2] != 0]
        self.active_patterns = min(
            sum(
                max(len(directional) - length + 1, 0)
                for length in range(self.config.min_pattern_length, self.config.max_pattern_length + 1)
            ),
            999999,
        )
        if record.events:
            self.completed_pattern_occurrences += max(len(record.events) - 1, 0)

    def _reset_processing(self) -> None:
        self.detector.reset()
        self.records = []
        self.current_index = -1
        self.event_counts.clear()
        self.recent_events.clear()
        self._live_tokens.clear()
        self.active_patterns = 0
        self.completed_pattern_occurrences = 0
        self.result = None
        self.error = ""
        self.cache_restored = False

    def _log(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self.logs.append(f"{timestamp} | {message}")

    @staticmethod
    def _read_closed_candles(path: Path) -> list[CandleBar]:
        if not path.exists() or not path.is_file():
            raise OSError(f"Dataset nao encontrado: {path}")
        candles: list[CandleBar] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"datetime", "open", "high", "low", "close", "volume"}
            headers = {str(header).strip().lower() for header in reader.fieldnames or []}
            if not required.issubset(headers):
                raise ValueError("Dataset sem colunas OHLCV obrigatorias.")
            for row in reader:
                closed = str(row.get("is_closed", "1") or "1").strip().lower()
                if closed not in {"1", "true", "sim", "yes"}:
                    continue
                timestamp = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                bar = CandleBar(
                    index=len(candles),
                    timestamp=timestamp,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    spread=float(row.get("spread", 0.0) or 0.0),
                    real_volume=float(row.get("real_volume", 0.0) or 0.0),
                )
                if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
                    raise ValueError(f"OHLC invalido no candle {bar.index}.")
                candles.append(bar)
        return candles

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
