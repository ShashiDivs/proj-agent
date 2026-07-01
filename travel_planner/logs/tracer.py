"""
Run-level tracer: collects per-agent latency, token counts, and estimated cost.
Writes structured logs to run_logs/ — one rotating app.log and one traces.jsonl.
"""

import time
import json
import logging
import os
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Log file paths ────────────────────────────────────────────────────────────
_HERE     = Path(__file__).parent.parent          # travel_planner/
_LOG_DIR  = _HERE / "run_logs"
_LOG_DIR.mkdir(exist_ok=True)

_APP_LOG    = _LOG_DIR / "app.log"
_TRACES_LOG = _LOG_DIR / "traces.jsonl"

# ── Logging setup ─────────────────────────────────────────────────────────────
_FMT     = "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s"
_DATE    = "%Y-%m-%d %H:%M:%S"

def _setup_logging():
    root = logging.getLogger()
    if root.handlers:          # already configured (Streamlit hot-reload guard)
        return
    root.setLevel(logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FMT, _DATE))
    root.addHandler(console)

    # Rotating file handler — max 5 MB, keep 3 backups
    file_handler = RotatingFileHandler(
        _APP_LOG, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_FMT, _DATE))
    root.addHandler(file_handler)

_setup_logging()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# ── Pricing (DeepSeek-V3.2 via Azure — approximate USD per 1M tokens) ─────────
INPUT_COST_PER_M  = 0.27
OUTPUT_COST_PER_M = 1.10


# ── Trace data classes ────────────────────────────────────────────────────────

@dataclass
class AgentTrace:
    agent:             str
    latency_ms:        float
    prompt_tokens:     int
    completion_tokens: int
    search_calls:      int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_usd(self) -> float:
        return (
            self.prompt_tokens     / 1_000_000 * INPUT_COST_PER_M +
            self.completion_tokens / 1_000_000 * OUTPUT_COST_PER_M
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_tokens"] = self.total_tokens
        d["cost_usd"]     = self.cost_usd
        return d


# ── RunTracer ─────────────────────────────────────────────────────────────────

class RunTracer:
    """Module-level singleton — reset at the start of each plan() call."""

    def __init__(self):
        self.traces:        list[AgentTrace] = []
        self._timers:       dict[str, float] = {}
        self._search_calls: dict[str, int]   = {}
        self._run_meta:     dict             = {}

    def reset(self, query: str = "", thread_id: str = ""):
        self.traces.clear()
        self._timers.clear()
        self._search_calls.clear()
        self._run_meta = {
            "run_id":    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query":     query,
            "thread_id": thread_id,
        }

    # ── Per-agent lifecycle ───────────────────────────────────────────────────

    def start_agent(self, agent: str):
        self._timers[agent] = time.perf_counter()
        self._search_calls[agent] = 0
        get_logger(agent).info("▶  started")

    def count_search(self, agent: str):
        self._search_calls[agent] = self._search_calls.get(agent, 0) + 1

    def end_agent(self, agent: str, prompt_tokens: int, completion_tokens: int):
        latency_ms = (time.perf_counter() - self._timers.pop(agent, time.perf_counter())) * 1000
        searches   = self._search_calls.pop(agent, 0)
        trace = AgentTrace(agent, latency_ms, prompt_tokens, completion_tokens, searches)
        self.traces.append(trace)
        get_logger(agent).info(
            "✔  done | latency=%.0fms | tokens=%d (in=%d out=%d) | searches=%d | cost=$%.6f",
            latency_ms, trace.total_tokens, prompt_tokens, completion_tokens,
            searches, trace.cost_usd,
        )

    def end_agent_no_llm(self, agent: str, search_calls: int = 0):
        latency_ms = (time.perf_counter() - self._timers.pop(agent, time.perf_counter())) * 1000
        trace = AgentTrace(agent, latency_ms, 0, 0, search_calls)
        self.traces.append(trace)
        get_logger(agent).info("✔  done | latency=%.0fms | searches=%d", latency_ms, search_calls)

    # ── Summary + persistence ─────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "total_agents":      len(self.traces),
            "total_tokens":      sum(t.total_tokens for t in self.traces),
            "prompt_tokens":     sum(t.prompt_tokens for t in self.traces),
            "completion_tokens": sum(t.completion_tokens for t in self.traces),
            "total_cost_usd":    sum(t.cost_usd for t in self.traces),
            "total_latency_ms":  sum(t.latency_ms for t in self.traces),
            "total_searches":    sum(t.search_calls for t in self.traces),
        }

    def save(self):
        """Append the completed run as one JSON line to traces.jsonl."""
        record = {
            **self._run_meta,
            "summary": self.summary(),
            "agents":  [t.to_dict() for t in self.traces],
        }
        with open(_TRACES_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        get_logger("tracer").info(
            "run saved | run_id=%s | file=%s", self._run_meta.get("run_id"), _TRACES_LOG
        )


# ── Past-run loader ───────────────────────────────────────────────────────────

def load_past_runs(limit: int = 50) -> list[dict]:
    """Read the last `limit` runs from traces.jsonl, newest first."""
    if not _TRACES_LOG.exists():
        return []
    runs = []
    with open(_TRACES_LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return list(reversed(runs[-limit:]))


# Singleton
tracer = RunTracer()
