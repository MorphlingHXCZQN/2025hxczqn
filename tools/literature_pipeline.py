"""Integrated literature workflow for the serum TDP-43 SAE project.

This module orchestrates the following steps:
1. Load high-citation articles via :mod:`tools.sci_citation_crawler` (live or cached).
2. Filter the articles to retain studies published within the last *N* years.
3. Attempt to download full-text PDFs or, when unavailable, retrieve abstracts.
4. Generate concise summaries (via OpenAI if configured, otherwise heuristic fallbacks).
5. Aggregate innovation opportunities informed by the summaries.
6. Update the master project plan with an auto-generated iteration section.
7. Export the refreshed plan to a Word document stored under the requested path.

Network access is optional. Passing ``--offline`` disables all live HTTP calls and
limits the workflow to cached metadata and locally stored files.
"""

from __future__ import annotations

import argparse
import dataclasses
import html
import json
import logging
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

# Support both "python -m tools.literature_pipeline" and "python tools/literature_pipeline.py"
if __package__ is None or __package__ == "":  # pragma: no cover - runtime convenience
    import sys

    CURRENT_FILE = Path(__file__).resolve()
    sys.path.append(str(CURRENT_FILE.parent.parent))
    from tools import sci_citation_crawler  # type: ignore
else:  # pragma: no cover - normal package import
    from . import sci_citation_crawler

try:  # pragma: no cover - optional dependency
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - offline environments
    requests = None

try:  # pragma: no cover - optional dependency for PDF parsing
    from pypdf import PdfReader  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    PdfReader = None

try:  # pragma: no cover - optional dependency for OpenAI summarisation
    from openai import OpenAI  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    OpenAI = None

USER_AGENT = "literature-pipeline/1.0 (mailto:research-informatics@example.com)"
PLAN_START_MARKER = "<!-- LITERATURE_ITERATION_START -->"
PLAN_END_MARKER = "<!-- LITERATURE_ITERATION_END -->"


@dataclasses.dataclass
class SummaryResult:
    """Container describing local processing for an article."""

    article: sci_citation_crawler.Article
    source: str
    local_path: Optional[Path]
    summary: str
    keywords: Sequence[str]

    def to_json(self) -> dict:
        return {
            "title": self.article.title,
            "doi": self.article.doi,
            "year": self.article.year,
            "journal": self.article.journal,
            "citation_count": self.article.citation_count,
            "source": self.source,
            "local_path": str(self.local_path) if self.local_path else None,
            "summary": self.summary,
            "keywords": list(self.keywords),
        }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download, summarise, and integrate recent serum TDP-43 literature.",
    )
    parser.add_argument(
        "--query",
        default="serum TDP-43 sepsis",
        help="Keyword query for Crossref lookups (default: 'serum TDP-43 sepsis').",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        help="Path to cached Crossref metadata (JSON).",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=25,
        help="Maximum number of records to process (default: 25).",
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=None,
        help="Lower bound publication year filter (overrides --years if provided).",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Process articles published within the last N years (default: 5).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory to store downloads and summaries (default: 'outputs/').",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="Path to the Markdown project plan to update.",
    )
    parser.add_argument(
        "--word-output",
        type=Path,
        default=None,
        help="Destination .docx path for the exported plan (omit to skip Word generation).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable live HTTP calls (use cached data only).",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model for summarisation (used only if API key available).",
    )
    parser.add_argument(
        "--max-summary-words",
        type=int,
        default=180,
        help="Target word count for generated summaries (default: 180 words).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute results without writing files (for testing).",
    )
    return parser.parse_args(argv)


def load_articles(args: argparse.Namespace) -> List[sci_citation_crawler.Article]:
    """Fetch or load article metadata respecting CLI options."""

    if args.cache:
        articles = sci_citation_crawler.load_cached_articles(args.cache)
    else:
        if args.offline:
            raise RuntimeError("Offline mode requires --cache metadata.")
        articles = sci_citation_crawler.fetch_articles(
            query=args.query,
            rows=args.rows,
            from_year=args.from_year or datetime.now().year - max(args.years, 1),
            issn_filter=None,
        )
    if args.rows:
        return articles[: args.rows]
    return articles


def filter_recent(
    articles: Iterable[sci_citation_crawler.Article],
    years: int,
    explicit_from_year: Optional[int] = None,
) -> List[sci_citation_crawler.Article]:
    """Return only articles within the requested year range."""

    if explicit_from_year is not None:
        min_year = explicit_from_year
    else:
        current_year = datetime.now().year
        min_year = current_year - years
    filtered: List[sci_citation_crawler.Article] = []
    for article in articles:
        if article.year is None:
            continue
        if article.year >= min_year:
            filtered.append(article)
    return sorted(filtered, key=lambda item: (item.year or 0, -item.citation_count), reverse=True)


def safe_filename(title: str, suffix: str) -> str:
    stem = re.sub(r"[^0-9A-Za-z一-龥_-]+", "_", title).strip("_")
    if not stem:
        stem = "article"
    return f"{stem}{suffix}"


def download_pdf(doi: str, dest_dir: Path) -> Optional[Path]:
    """Attempt to download a PDF for the given DOI."""

    if not doi or requests is None:
        return None
    headers = {"Accept": "application/pdf", "User-Agent": USER_AGENT}
    url = f"https://doi.org/{doi}"
    try:
        response = requests.get(url, headers=headers, timeout=45)
    except Exception:  # pragma: no cover - network dependent
        return None
    if response.status_code != 200:
        return None
    if "application/pdf" not in response.headers.get("Content-Type", "").lower():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(doi.replace("/", "_"), ".pdf")
    pdf_path = dest_dir / filename
    pdf_path.write_bytes(response.content)
    return pdf_path


def extract_text_from_pdf(pdf_path: Path) -> Optional[str]:
    """Extract raw text from a PDF using PyPDF if available."""

    if PdfReader is None:  # pragma: no cover - depends on optional dependency
        return None
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:  # pragma: no cover - PDF parsing errors
        return None
    parts: List[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(filter(None, parts))
    return text or None


def fetch_crossref_abstract(doi: str) -> Optional[str]:
    """Retrieve article abstract from Crossref if accessible."""

    if not doi or requests is None:
        return None
    url = f"{sci_citation_crawler.CROSSREF_API}/{doi}"
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except Exception:  # pragma: no cover - network dependent
        return None
    if response.status_code != 200:
        return None
    message = response.json().get("message", {})
    abstract = message.get("abstract")
    if not abstract:
        return None
    return clean_crossref_abstract(abstract)


def clean_crossref_abstract(raw: str) -> str:
    """Convert JATS XML abstracts into readable plain text."""

    text = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_text_payload(
    article: sci_citation_crawler.Article,
    downloads_dir: Path,
    offline: bool,
) -> Tuple[str, str, Optional[Path]]:
    """Return (payload_text, source_label, local_path)."""

    pdf_path: Optional[Path] = None
    if not offline:
        pdf_path = download_pdf(article.doi, downloads_dir)
    if pdf_path:
        text = extract_text_from_pdf(pdf_path)
        if text:
            return text, "pdf", pdf_path
    if not offline:
        abstract = fetch_crossref_abstract(article.doi)
    else:
        abstract = None
    if abstract:
        return abstract, "abstract", None
    placeholder = (
        f"未能自动获取《{article.title}》（{article.year or '-'}，{article.journal}）的原文或摘要。"
        "请人工检索并补充关键信息。"
    )
    return placeholder, "metadata", None


def summarise_payload(
    payload: str,
    article: sci_citation_crawler.Article,
    model: str,
    max_words: int,
) -> Tuple[str, Sequence[str]]:
    """Generate a concise summary and keyword set for an article."""

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and OpenAI is not None:
        client = OpenAI(api_key=api_key)
        prompt = textwrap.dedent(
            f"""
            你是一名医学研究秘书。请阅读下面的文献内容，提炼 3-4 个要点，用中文撰写约 {max_words} 字的结构化摘要（含研究对象、方法、结果、启示）。
            文本：{payload}
            """
        )
        try:  # pragma: no cover - depends on network + API availability
            response = client.responses.create(
                model=model,
                input=prompt,
                max_output_tokens=600,
            )
            content = response.output_text
            summary = content.strip()
        except Exception as exc:  # pragma: no cover - API failure fallback
            logging.warning("OpenAI summarisation failed: %s", exc)
            summary = heuristic_summary(article, payload, max_words)
    else:
        summary = heuristic_summary(article, payload, max_words)
    keywords = infer_keywords(article, summary)
    return summary, keywords


def heuristic_summary(
    article: sci_citation_crawler.Article,
    payload: str,
    max_words: int,
) -> str:
    """Fallback summary generator that never relies on network calls."""

    base = f"《{article.title}》（{article.year or '-'}，{article.journal}）"
    if "未能自动获取" in payload:
        return (
            f"{base} 的原文/摘要未通过自动化流程获得。根据题目推测其与 {keyword_hint(article)} 相关，"
            "建议由指定研究人员人工阅读全文并补充要点。"
        )
    sentences = re.split(r"(?<=[。！？])", payload)
    cleaned = "".join(sentences[:4])
    if not cleaned:
        cleaned = payload[: max_words * 4]
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned.split()) > max_words:
        cleaned = " ".join(cleaned.split()[:max_words])
    return f"{base} 摘要要点：{cleaned}"


def keyword_hint(article: sci_citation_crawler.Article) -> str:
    title_lower = article.title.lower()
    if "complement" in title_lower or "c5" in title_lower:
        return "补体-脑损伤互作"
    if "phosphorylated" in title_lower or "phospho" in title_lower:
        return "TDP-43 磷酸化与神经退行性风险"
    if "sepsis" in title_lower:
        return "脓毒症相关炎症及脑功能损害"
    return "TDP-43 相关病理"


def infer_keywords(article: sci_citation_crawler.Article, summary: str) -> Sequence[str]:
    """Extract coarse keywords from titles + summary heuristically."""

    tokens = set()
    text = f"{article.title} {summary}".lower()
    mapping = {
        "complement": "补体调控",
        "c5a": "补体C5a",
        "c3": "补体C3",
        "tdp-43": "TDP-43",
        "phosphory": "TDP-43磷酸化",
        "sepsis": "脓毒症",
        "encephalopathy": "脑功能障碍",
        "biomarker": "生物标志物",
        "mortality": "死亡率",
        "neurodegeneration": "神经退行",
        "neuroinflammation": "神经炎症",
        "machine learning": "机器学习",
        "deep learning": "深度学习",
    }
    for needle, keyword in mapping.items():
        if needle in text:
            tokens.add(keyword)
    return sorted(tokens)


def write_summary_files(
    results: Sequence[SummaryResult],
    output_dir: Path,
    dry_run: bool,
) -> None:
    summaries_dir = output_dir / "summaries"
    if dry_run:
        return
    summaries_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        filename = safe_filename(result.article.title, ".md")
        path = summaries_dir / filename
        content = textwrap.dedent(
            f"""
            # {result.article.title}

            - 期刊：{result.article.journal}
            - 年份：{result.article.year or '-'}
            - DOI：{result.article.doi or '-'}
            - 引用次数：{result.article.citation_count}
            - 文本来源：{result.source}
            - 本地文件：{result.local_path or '（无）'}
            - 关键词：{', '.join(result.keywords) if result.keywords else '（待补充）'}

            ## 摘要
            {result.summary}
            """
        ).strip()
        path.write_text(content, encoding="utf-8")
    data_path = output_dir / "recent_summaries.json"
    data_path.write_text(
        json.dumps([result.to_json() for result in results], ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def derive_innovations(results: Sequence[SummaryResult]) -> List[str]:
    """Translate keyword occurrences into actionable innovation ideas."""

    innovations: List[str] = []
    keyword_pool = {kw for result in results for kw in result.keywords}
    if {"补体调控", "补体C5a", "补体C3"} & keyword_pool:
        innovations.append(
            "将 C3/C5a 动态纳入 O 型轨迹分析，并探索补体抑制剂对 TDP-43 轨迹重塑的干预试验。"
        )
    if "TDP-43磷酸化" in keyword_pool:
        innovations.append(
            "增设血清磷酸化 TDP-43 分型，与全长 TDP-43 及传统神经标志物进行分层比较。"
        )
    if "死亡率" in keyword_pool:
        innovations.append(
            "在多变量模型中引入 90 天死亡率与 ICU 复合不良结局，评估 TDP-43 增量价值。"
        )
    if "生物标志物" in keyword_pool and "深度学习" not in keyword_pool:
        innovations.append(
            "利用深度学习多模态模型比较 TDP-43 与补体、神经丝蛋白组合对 SAE 预测的贡献。"
        )
    if not innovations:
        innovations.append("依据标题信息未发现新的主题，建议人工审核补充创新点。")
    return innovations


def render_iteration_section(
    results: Sequence[SummaryResult],
    innovations: Sequence[str],
) -> str:
    """Construct the Markdown section injected into the plan."""

    lines: List[str] = []
    lines.append("## 9. 近五年文献驱动的迭代更新")
    lines.append("本节内容由 `tools/literature_pipeline.py` 自动生成，覆盖最近 5 年内与血清 TDP-43/脓毒症脑损伤相关的高引用研究。")
    lines.append("")
    lines.append("### 9.1 摘要与获取状态")
    lines.append("| 标题 | 年份 | 文本来源 | 本地文件 | 关键词 | 摘要要点 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for result in results:
        local = result.local_path.as_posix() if result.local_path else "-"
        keywords = ", ".join(result.keywords) if result.keywords else "-"
        summary = result.summary.replace("|", "／").replace("\n", "<br>")
        lines.append(
            f"| {result.article.title.replace('|', '／')} | {result.article.year or '-'} | {result.source} | {local} | {keywords or '-'} | {summary} |"
        )
    lines.append("")
    lines.append("### 9.2 创新点更新")
    for idx, idea in enumerate(innovations, start=1):
        lines.append(f"{idx}. {idea}")
    lines.append("")
    lines.append("### 9.3 后续行动")
    lines.append("- 对于仍需人工补充的文献，指定责任人于 2 周内完成原文下载与深度笔记。")
    lines.append("- 结合补体轴与 TDP-43 双标志物轨迹，验证深度学习模型在外部中心的泛化性能。")
    lines.append("- 依据最新证据修订随访 CRF 表单，新增磷酸化 TDP-43 与补体并行采样栏位。")
    return "\n".join(lines)


def update_plan(
    plan_path: Path,
    section_text: str,
    dry_run: bool,
) -> None:
    content = plan_path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(PLAN_START_MARKER) + r".*?" + re.escape(PLAN_END_MARKER),
        flags=re.DOTALL,
    )
    if not pattern.search(content):
        raise RuntimeError(
            "Plan file缺少自动化占位符，请确保包含 LITERATURE_ITERATION_START/END 标记。"
        )
    replacement = f"{PLAN_START_MARKER}\n{section_text}\n{PLAN_END_MARKER}"
    new_content = pattern.sub(replacement, content, count=1)
    if dry_run:
        logging.info("Dry-run: 计划书不会被写入。")
        return
    plan_path.write_text(new_content, encoding="utf-8")


def export_to_docx(markdown_text: str, destination: Path, dry_run: bool) -> None:
    """Minimal DOCX writer that converts Markdown to simple paragraphs."""

    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    paragraphs = []
    for line in markdown_text.splitlines():
        stripped = line.rstrip()
        if not stripped:
            paragraphs.append("<w:p/>")
            continue
        plain = stripped
        # rudimentary markdown clean-up
        plain = re.sub(r"^#+\s*", "", plain)
        plain = plain.replace("* ", "• ")
        plain = plain.replace("- ", "• ")
        plain = html.escape(plain)
        paragraphs.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p>".format(plain)
        )
    body = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {paragraphs}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
""".format(paragraphs="\n    ".join(paragraphs))
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    with open(destination, "wb") as handle:
        import zipfile

        with zipfile.ZipFile(handle, "w") as docx:
            docx.writestr("[Content_Types].xml", content_types)
            docx.writestr("_rels/.rels", rels)
            docx.writestr("word/document.xml", body)


def run_pipeline(args: argparse.Namespace) -> Tuple[List[SummaryResult], List[str]]:
    articles = load_articles(args)
    recent = filter_recent(articles, years=args.years, explicit_from_year=args.from_year)
    output_dir = args.output_dir
    downloads_dir = output_dir / "downloads"
    results: List[SummaryResult] = []
    for article in recent:
        payload, source, local_path = load_text_payload(article, downloads_dir, args.offline)
        summary, keywords = summarise_payload(payload, article, args.model, args.max_summary_words)
        results.append(
            SummaryResult(
                article=article,
                source=source,
                local_path=local_path,
                summary=summary,
                keywords=keywords,
            )
        )
    innovations = derive_innovations(results)
    return results, innovations


def main(argv: Optional[Sequence[str]] = None) -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = parse_args(argv)
    args.output_dir = args.output_dir.expanduser()
    args.plan = args.plan.expanduser()
    if args.cache is not None:
        args.cache = args.cache.expanduser()
    if args.word_output is not None:
        args.word_output = args.word_output.expanduser()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results, innovations = run_pipeline(args)
    if not results:
        logging.warning("No recent articles matched the criteria; nothing to update.")
        return
    write_summary_files(results, args.output_dir, args.dry_run)
    section = render_iteration_section(results, innovations)
    update_plan(args.plan, section, args.dry_run)
    if args.dry_run:
        logging.info("Processed %s articles (dry-run; no files written).", len(results))
    elif args.word_output is not None:
        plan_text = args.plan.read_text(encoding="utf-8")
        export_to_docx(plan_text, args.word_output, args.dry_run)
        logging.info(
            "Processed %s articles; plan + DOCX updated at %s.",
            len(results),
            args.word_output,
        )
    else:
        logging.info("Processed %s articles; plan updated (no DOCX requested).", len(results))


if __name__ == "__main__":  # pragma: no cover
    main()
