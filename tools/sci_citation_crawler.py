"""Utility to fetch highly cited SCI literature via the Crossref API.

This module provides a simple command line interface that can be scheduled or
run manually to retrieve the most cited papers related to serum TDP-43 and
sepsis-associated brain injury. Results are emitted as Markdown or CSV to
facilitate direct inclusion in research plans.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency for offline cache usage
    requests = None


CROSSREF_API = "https://api.crossref.org/works"
USER_AGENT = (
    "sci-citation-crawler/1.0 (mailto:research-informatics@example.com)"
)


@dataclasses.dataclass
class Article:
    """Container for article metadata returned by Crossref."""

    title: str
    doi: str
    year: Optional[int]
    journal: str
    citation_count: int
    authors: str


def fetch_articles(
    query: str,
    rows: int = 20,
    from_year: Optional[int] = None,
    issn_filter: Optional[str] = None,
) -> List[Article]:
    """Retrieve highly cited articles from Crossref."""

    if requests is None:
        raise RuntimeError(
            "The 'requests' package is required for live fetching. "
            "Install it or provide a cached dataset via --cache."
        )

    headers = {"User-Agent": USER_AGENT}
    params = {
        "query": query,
        "sort": "is-referenced-by-count",
        "order": "desc",
        "rows": rows,
    }
    filters: List[str] = []
    if from_year is not None:
        filters.append(f"from-pub-date:{from_year}-01-01")
    if issn_filter:
        filters.append(f"issn:{issn_filter}")
    if filters:
        params["filter"] = ",".join(filters)

    response = requests.get(CROSSREF_API, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])

    articles: List[Article] = []
    for item in items:
        title = item.get("title", ["Unnamed Article"])[0]
        doi = item.get("DOI", "")
        year = None
        if item.get("issued", {}).get("date-parts"):
            year = item["issued"]["date-parts"][0][0]
        journal = item.get("container-title", ["Unknown Journal"])[0]
        citation_count = item.get("is-referenced-by-count", 0)
        authors = ", ".join(
            filter(
                None,
                [
                    " ".join(
                        filter(
                            None,
                            [
                                person.get("given", ""),
                                person.get("family", ""),
                            ],
                        )
                    ).strip()
                    for person in item.get("author", [])
                ],
            )
        )

        articles.append(
            Article(
                title=title,
                doi=doi,
                year=year,
                journal=journal,
                citation_count=citation_count,
                authors=authors,
            )
        )

    return articles


def load_cached_articles(cache_path: Path) -> List[Article]:
    """Load article metadata from a JSON cache file."""

    if not cache_path.exists():
        raise FileNotFoundError(f"Cache file not found: {cache_path}")

    raw = json.loads(cache_path.read_text(encoding="utf-8"))

    articles: List[Article] = []
    for item in raw:
        articles.append(
            Article(
                title=item.get("title", "Unnamed Article"),
                doi=item.get("doi", ""),
                year=item.get("year"),
                journal=item.get("journal", "Unknown Journal"),
                citation_count=item.get("citation_count", 0),
                authors=item.get("authors", ""),
            )
        )

    return sorted(articles, key=lambda item: item.citation_count, reverse=True)


def to_markdown(articles: Iterable[Article]) -> str:
    """Render a Markdown table from article metadata."""

    header = "| 标题 | 期刊 | 年份 | 引用次数 | DOI | 作者 |\n"
    separator = "| --- | --- | --- | --- | --- | --- |\n"
    rows = []
    for article in articles:
        doi_link = f"https://doi.org/{article.doi}" if article.doi else ""
        rows.append(
            "| {title} | {journal} | {year} | {citations} | {doi} | {authors} |".format(
                title=article.title.replace("|", "／"),
                journal=article.journal.replace("|", "／"),
                year=article.year or "-",
                citations=article.citation_count,
                doi=f"[{article.doi}]({doi_link})" if article.doi else "-",
                authors=(article.authors or "-").replace("|", "／"),
            )
        )
    return header + separator + "\n".join(rows)


def to_csv(articles: Iterable[Article]) -> str:
    """Render a CSV string from article metadata."""

    lines = ["title,journal,year,citation_count,doi,authors"]
    for article in articles:
        line = ",".join(
            json.dumps(value, ensure_ascii=False)
            for value in (
                article.title,
                article.journal,
                article.year,
                article.citation_count,
                article.doi,
                article.authors,
            )
        )
        lines.append(line)
    return "\n".join(lines)


def write_output(content: str, output: Optional[Path]) -> None:
    """Write scraper output to a path or stdout."""

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch highly cited SCI literature for serum TDP-43 studies.",
    )
    parser.add_argument("query", help="Keyword query, e.g. 'serum TDP-43 sepsis'.")
    parser.add_argument(
        "--rows",
        type=int,
        default=20,
        help="Maximum number of articles to fetch (default: 20).",
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=datetime.now().year - 10,
        help="Lower bound year for publication date filter (default: 10 years ago).",
    )
    parser.add_argument(
        "--issn",
        help="Optional ISSN filter to restrict results to a specific journal.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "csv"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write results to file (default: stdout).",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        help=(
            "Path to a JSON cache generated from an earlier run. "
            "If provided, data are loaded offline and the query argument is only used "
            "for provenance in logs."
        ),
    )
    return parser.parse_args(args)


def main(cli_args: Optional[List[str]] = None) -> None:
    options = parse_args(cli_args)
    try:
        if options.cache:
            articles = load_cached_articles(options.cache)
        else:
            articles = fetch_articles(
                query=options.query,
                rows=options.rows,
                from_year=options.from_year,
                issn_filter=options.issn,
            )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    except requests.RequestException as exc:  # type: ignore[arg-type]
        raise SystemExit(f"Failed to fetch articles: {exc}") from exc

    if not articles:
        raise SystemExit("No articles found for the provided query.")

    articles = articles[: options.rows]

    if options.format == "markdown":
        content = to_markdown(articles)
    else:
        content = to_csv(articles)

    write_output(content, options.output)


if __name__ == "__main__":
    main()
