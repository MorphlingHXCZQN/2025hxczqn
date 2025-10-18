# 数据目录说明

该目录用于存放运行爬虫与文献迭代管线时生成的**元数据缓存**，例如 Crossref API 的 JSON 结果。

由于部分平台限制二进制或大文件推送，本仓库默认不跟踪任何运行产生的数据。若需离线运行脚本，可按以下步骤生成缓存：

1. 联网环境下执行：
   ```bash
   python tools/sci_citation_crawler.py "serum TDP-43 sepsis" --rows 25 --format markdown --output data/cached_serum_tdp43_sepsis_crossref.json
   ```
   或使用 `--format csv` 获取表格文件。
2. 将生成的 `data/cached_serum_tdp43_sepsis_crossref.json` 文件复制至无法联网的环境，并在运行 `tools/literature_pipeline.py` 时通过 `--cache` 参数引用。
3. 文献下载、摘要与 Word 导出文件会保存在仓库根目录下的 `outputs/` 目录（参见该目录下的 README），可根据需要备份或清理。

> 提示：`data/` 目录已在 `.gitignore` 中忽略，用于缓存的 JSON/CSV 文件不会被提交；`outputs/` 目录同样被忽略，以避免二进制文件阻塞推送。提交前如需彻底清理缓存，请执行 `python tools/cleanup_workspace.py`。
