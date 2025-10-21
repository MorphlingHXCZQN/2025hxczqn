"""Offline-friendly PubMed client used for tests and demos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .config import PipelineConfig, QueryConfig
from .search import BaseClient, SearchResult


class PubMedClient(BaseClient):
    """Simple client that replays stubbed PubMed responses."""

    source_name = "pubmed"

    def __init__(self, config: PipelineConfig, stub_path: Path | None = None):
        self.config = config
        self.stub_path = stub_path or Path("resources/pubmed_stub.json")

    def search(self, query: QueryConfig) -> Iterable[SearchResult]:
        if not self.config.offline_mode:
            raise RuntimeError(
                "Real PubMed access is not available in this environment. "
                "Set offline_mode=true in the config to use stub data."
            )

        payload = self._load_stub()
        records = payload.get(query.name, [])
        for record in records:
            yield SearchResult(
                title=record["title"],
                authors=tuple(record.get("authors", [])),
                year=int(record["year"]),
                journal=record.get("journal", ""),
                doi=record.get("doi", ""),
                study_type=record.get("study_type", ""),
                sample_size=record.get("sample_size", ""),
                imaging_modality=tuple(record.get("imaging_modality", [])),
                key_findings=record.get("key_findings", ""),
                access_type=record.get("access_type", "unknown"),
                source=self.source_name,
                link=record.get("link", ""),
                citation_count=int(record.get("citations", 0)),
            )

    def _load_stub(self) -> dict:
        with self.stub_path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
