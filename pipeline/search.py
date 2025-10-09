"""Core search orchestration for the literature pipeline."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, MutableMapping, Sequence, Tuple

from .config import PipelineConfig, QueryConfig


@dataclass
class SearchResult:
    """Normalized representation of a retrieved article."""

    title: str
    authors: Sequence[str]
    year: int
    journal: str
    doi: str
    study_type: str
    sample_size: str
    imaging_modality: Sequence[str]
    key_findings: str
    access_type: str
    source: str
    link: str

    def unique_id(self) -> str:
        if self.doi:
            return self.doi.lower()
        return f"{self.title.lower()}::{self.source}"


class SearchRunner:
    """Execute queries against configured sources and normalise results."""

    def __init__(self, config: PipelineConfig, clients: Dict[str, "BaseClient"]):
        self.config = config
        self.clients = clients

    def run(self) -> Tuple[List[SearchResult], MutableMapping[Tuple[str, str], List[SearchResult]]]:
        aggregated: list[SearchResult] = []
        per_query: MutableMapping[Tuple[str, str], List[SearchResult]] = defaultdict(list)
        seen_ids: set[str] = set()

        for query in self.config.queries:
            for source in query.sources:
                client = self.clients.get(source)
                if client is None:
                    raise ValueError(f"No client registered for source '{source}'")
                for item in client.search(query):
                    per_query[(query.name, source)].append(item)
                    uid = item.unique_id()
                    if uid in seen_ids:
                        continue
                    seen_ids.add(uid)
                    aggregated.append(item)
        return aggregated, per_query


class BaseClient:
    """Protocol for search clients."""

    source_name: str

    def search(self, query: QueryConfig) -> Iterable[SearchResult]:
        raise NotImplementedError
