"""Offline-friendly Google Scholar client."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .config import PipelineConfig, QueryConfig
from .search import BaseClient, SearchResult


class GoogleScholarClient(BaseClient):
    source_name = "google_scholar"

    def __init__(self, config: PipelineConfig, stub_path: Path | None = None):
        self.config = config
        self.stub_path = stub_path or Path("resources/google_scholar_stub.json")

    def search(self, query: QueryConfig) -> Iterable[SearchResult]:
        if not self.config.offline_mode:
            raise RuntimeError(
                "Real Google Scholar access is not supported. "
                "Enable offline_mode and supply stub data."
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
            )

    def _load_stub(self) -> dict:
        with self.stub_path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
