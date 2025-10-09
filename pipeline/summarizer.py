"""Generate lightweight textual summaries for retrieved literature."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from .search import SearchResult


class Summarizer:
    """Create a simple markdown summary using the retrieved metadata."""

    def __init__(self, output_root: Path):
        self.output_root = output_root
        self.summary_path = output_root / "文献自动总结.md"
        self.word_path = output_root / "文献自动总结.docx"

    def write_markdown(self, results: Iterable[SearchResult]) -> Path:
        lines = [
            "# 文献自动总结",
            "",
            "以下内容基于离线示例数据生成，真实环境请替换为实际抓取结果。",
            "",
        ]
        for item in results:
            lines.extend(
                [
                    f"## {item.title}",
                    f"- 来源：{item.source}",
                    f"- 年份：{item.year}",
                    f"- 刊物：{item.journal}",
                    f"- DOI：{item.doi or 'N/A'}",
                    f"- 研究类型：{item.study_type}",
                    f"- 样本量：{item.sample_size}",
                    f"- 影像学：{'、'.join(item.imaging_modality)}",
                    f"- 主要发现：{item.key_findings}",
                    "",
                ]
            )
        path = self.summary_path
        with path.open("w", encoding="utf-8") as fp:
            fp.write("\n".join(lines))
        return path

    def write_docx(self, results: Iterable[SearchResult]) -> Path:
        """Create a lightweight Word document containing the same summary."""

        def paragraph_xml(text: str) -> str:
            if not text:
                return "<w:p/>"
            escaped = escape(text)
            return (
                "<w:p>"
                "<w:r>"
                '<w:t xml:space="preserve">'
                f"{escaped}"
                "</w:t>"
                "</w:r>"
                "</w:p>"
            )

        paragraphs = [
            "文献自动总结",
            "",
            "以下内容基于离线示例数据生成，真实环境请替换为实际抓取结果。",
            "",
        ]
        for item in results:
            paragraphs.extend(
                [
                    item.title,
                    f"来源：{item.source}",
                    f"年份：{item.year}",
                    f"刊物：{item.journal}",
                    f"DOI：{item.doi or 'N/A'}",
                    f"研究类型：{item.study_type}",
                    f"样本量：{item.sample_size}",
                    f"影像学：{'、'.join(item.imaging_modality)}",
                    f"主要发现：{item.key_findings}",
                    "",
                ]
            )

        body = "".join(paragraph_xml(line) for line in paragraphs)
        document_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
            "<w:body>"
            f"{body}"
            "<w:sectPr>"
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
            'w:header="708" w:footer="708" w:gutter="0"/>'
            '<w:cols w:space="708"/>'
            '<w:docGrid w:linePitch="360"/>'
            "</w:sectPr>"
            "</w:body>"
            "</w:document>"
        )

        content_types_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
            "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
            "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
            "<Override PartName=\"/word/document.xml\" "
            "ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
            "</Types>"
        )

        rels_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"R1\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
            "Target=\"word/document.xml\"/>"
            "</Relationships>"
        )

        path = self.word_path
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types_xml)
            zf.writestr("_rels/.rels", rels_xml)
            zf.writestr("word/document.xml", document_xml)
        return path
