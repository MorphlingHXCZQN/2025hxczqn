"""Configuration utilities for the retrieval pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when PyYAML is absent
    yaml = None


@dataclass
class QueryConfig:
    """Configuration for a single search query."""

    name: str
    keywords: str
    years: Sequence[int]
    modalities: Sequence[str]
    sources: Sequence[str]


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration loaded from YAML."""

    output_root: Path
    offline_mode: bool
    queries: List[QueryConfig]
    iterations: int = 1

    @classmethod
    def from_path(cls, path: Path) -> "PipelineConfig":
        text = path.read_text(encoding="utf-8")
        payload = load_mapping(text)

        queries = [
            QueryConfig(
                name=item["name"],
                keywords=item["keywords"],
                years=tuple(item.get("years", [])),
                modalities=tuple(item.get("modalities", [])),
                sources=tuple(item.get("sources", [])),
            )
            for item in payload.get("queries", [])
        ]

        output_root = Path(payload["output_root"]).expanduser()
        return cls(
            output_root=output_root,
            offline_mode=bool(payload.get("offline_mode", False)),
            queries=queries,
            iterations=int(payload.get("iterations", 1)),
        )

    def iter_sources(self) -> Iterable[str]:
        seen = set()
        for query in self.queries:
            for source in query.sources:
                if source not in seen:
                    seen.add(source)
                    yield source


def load_mapping(text: str) -> dict:
    """Load configuration from YAML or JSON text."""

    if yaml is not None:
        return yaml.safe_load(text)  # type: ignore[no-any-return]
    return json.loads(text)
