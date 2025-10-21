"""Utilities for writing search outputs to disk."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .search import SearchResult


class OutputManager:
    """Persist search results using the repository directory structure."""

    def __init__(self, output_root: Path):
        self.output_root = output_root
        self.raw_root = output_root / "data" / "raw"
        self.processed_root = output_root / "data" / "processed"
        self.pdf_root = output_root / "data" / "pdfs"
        self.logs_root = output_root / "logs"

    def prepare(self) -> None:
        for path in [
            self.raw_root / "pubmed",
            self.raw_root / "google_scholar",
            self.processed_root,
            self.pdf_root / "open_access",
            self.pdf_root / "restricted",
            self.logs_root,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def write_raw(self, source: str, query_name: str, results: Iterable[SearchResult]) -> None:
        target = self.raw_root / source / f"{query_name}.json"
        serialisable = [self._as_dict(item) for item in results]
        with target.open("w", encoding="utf-8") as fp:
            json.dump(serialisable, fp, ensure_ascii=False, indent=2)

    def write_summary(self, results: Iterable[SearchResult]) -> Path:
        target = self.processed_root / "literature_summary.csv"
        rows = [
            [
                r.title,
                "; ".join(r.authors),
                r.year,
                r.journal,
                r.doi,
                r.study_type,
                r.sample_size,
                "; ".join(r.imaging_modality),
                r.key_findings,
                r.access_type,
                r.source,
                r.link,
                r.citation_count,
            ]
            for r in results
        ]
        with target.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(
                [
                    "title",
                    "authors",
                    "year",
                    "journal",
                    "doi",
                    "study_type",
                    "sample_size",
                    "imaging_modality",
                    "key_findings",
                    "access_type",
                    "source",
                    "link",
                    "citations",
                ]
            )
            writer.writerows(rows)
        return target

    def append_history(self, query_name: str, source: str, count: int) -> None:
        target = self.logs_root / "search_history.csv"
        exists = target.exists()
        with target.open("a", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            if not exists:
                writer.writerow(["timestamp", "query", "source", "results"])
            writer.writerow(
                [datetime.utcnow().isoformat(), query_name, source, count]
            )

    @staticmethod
    def _as_dict(item: SearchResult) -> dict:
        return {
            "title": item.title,
            "authors": list(item.authors),
            "year": item.year,
            "journal": item.journal,
            "doi": item.doi,
            "study_type": item.study_type,
            "sample_size": item.sample_size,
            "imaging_modality": list(item.imaging_modality),
            "key_findings": item.key_findings,
            "access_type": item.access_type,
            "source": item.source,
            "link": item.link,
            "citations": item.citation_count,
        }
