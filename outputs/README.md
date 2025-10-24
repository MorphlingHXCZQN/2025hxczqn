# Outputs Directory

This folder collects generated artefacts such as Word exports, PDF/HTML downloads,
and article summaries produced by the automation scripts. The directory is ignored
by Git (see `.gitignore`), ensuring binary files never block repository updates.

Typical files created here include:

- `serum_tdp43_sepsis_project.docx`: Word export of the project plan。
- `tdp43_recent_literature.docx`: 近五年高引用文献的 Word 汇总，由
  `tools/sci_citation_crawler.py --word-output ...` 自动生成。
- `literature_summaries/`: Machine-readable JSON/Markdown notes for each article。
- `literature/fulltext/`: 已成功抓取的 PDF/HTML 原文。

To rebuild the plan artefacts, run the literature pipeline:

```bash
python tools/literature_pipeline.py --cache data/cached_serum_tdp43_sepsis_crossref.json \
    --rows 12 --offline
```

The command will default to `outputs/` for all downloads and exports, keeping the
repository clean while still letting you regenerate everything locally.

To refresh the literature Word report with optional全文下载，可执行：

```bash
python tools/sci_citation_crawler.py \
    "serum TDP-43 sepsis" \
    --recent-years 5 \
    --rows 30 \
    --attempt-fulltext \
    --word-output outputs/tdp43_recent_literature.docx
```
