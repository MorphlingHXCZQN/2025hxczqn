"""Command-line entry point for the retrieval pipeline."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from typing import Dict, Iterable, List

from .config import PipelineConfig
from .downloader import OutputManager
from .google_scholar import GoogleScholarClient
from .pubmed import PubMedClient
from .search import BaseClient, SearchResult, SearchRunner
from .summarizer import Summarizer


def build_clients(config: PipelineConfig) -> Dict[str, BaseClient]:
    clients: Dict[str, BaseClient] = {}
    for source in config.iter_sources():
        if source == "pubmed":
            clients[source] = PubMedClient(config)
        elif source == "google_scholar":
            clients[source] = GoogleScholarClient(config)
        else:
            raise ValueError(f"Unsupported source '{source}'")
    return clients


def execute_pipeline(
    config_path: Path,
    *,
    output_root: Path | None = None,
) -> List[SearchResult]:
    config = PipelineConfig.from_path(config_path)
    if output_root is not None:
        config = replace(config, output_root=output_root.expanduser())
    manager = OutputManager(config.output_root)
    manager.prepare()

    clients = build_clients(config)
    runner = SearchRunner(config, clients)
    aggregated, per_query = runner.run()

    for (query_name, source), records in per_query.items():
        manager.write_raw(source, query_name, records)
        manager.append_history(query_name, source, len(records))

    summary_path = manager.write_summary(aggregated)
    summarizer = Summarizer(config.output_root)
    summary_markdown = summarizer.write_markdown(aggregated)
    summary_docx = summarizer.write_docx(aggregated)

    print(f"Raw outputs written to: {manager.raw_root}")
    print(f"Tabular summary: {summary_path}")
    print(f"Markdown summary: {summary_markdown}")
    print(f"Word summary: {summary_docx}")
    return aggregated


def main(argv: Iterable[str] | None = None) -> List[SearchResult]:
    parser = argparse.ArgumentParser(description="Run the literature retrieval pipeline")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the YAML configuration file",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help=(
            "Override the output directory defined in the configuration file. "
            "Useful for targeting a Windows D drive, e.g. --output-root "
            "\"D:/计划\""
        ),
    )
    args = parser.parse_args(argv)
    return execute_pipeline(args.config, output_root=args.output_root)


if __name__ == "__main__":
    main()
