# 2025hxczqn

本仓库包含多份研究计划及其配套工具（当前迭代：**v0.4 – 无二进制阻塞版本**）：

- `plans/emergency_phd_plan.md`：聚焦脓毒症多源数据融合与智能急诊决策的急诊医学博士研究计划。
- `plans/imaging_phd_plan.md`：面向胶质瘤影像-多组学精准诊疗的医学影像博士研究计划。
- `plans/serum_tdp43_sepsis_project.md`：血清 TDP-43 在脓毒症脑损伤预后预测中的双版本（动物/临床）研究方案。
- `tools/plan_optimizer.py`：结合 DuckDuckGo 检索与 OpenAI GPT 模型，对研究计划持续优化的命令行脚本。
- `tools/sci_citation_crawler.py`：抓取与筛选血清 TDP-43 / SAE 相关高引用 SCI 文献，输出 Markdown/CSV 表格。
- `tools/literature_pipeline.py`：基于缓存或在线检索，自动完成文献下载、摘要、创新点提取与 Word 导出。
- `tools/cleanup_workspace.py`：一键清理忽略目录中的缓存/二进制产物，确保在提交 PR 前工作区保持整洁。

## 快速开始

1. 安装依赖：
   ```bash
   pip install openai requests
   ```
2. 配置 OpenAI API Key：
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. 运行优化工具（示例）：
   ```bash
   python tools/plan_optimizer.py \
       --plan plans/emergency_phd_plan.md \
       --query "sepsis precision medicine doctoral proposal" \
       --model gpt-4o-mini
   ```
   生成的优化建议会保存到当前工作目录，例如 `./emergency_phd_plan_optimized.md`，并打印在终端，便于迭代完善研究计划。

> 如需针对影像计划进行迭代，可将 `--plan` 参数替换为 `plans/imaging_phd_plan.md` 并调整检索关键词。

如当前环境无法联网或缺少 OpenAI/requests 依赖，可使用离线模式快速获得启发式建议：

```bash
python tools/plan_optimizer.py \
    --plan plans/emergency_phd_plan.md \
    --query "sepsis precision medicine doctoral proposal" \
    --offline
```

若希望将迭代后的计划统一保存到特定目录，可通过 `--output-dir` 参数显式指定，例如：

```bash
python tools/plan_optimizer.py \
    --plan plans/imaging_phd_plan.md \
    --query "glioma radiomics doctoral proposal" \
    --output-dir iterations
```

在 Windows 环境下，如果未显式提供 `--output-dir`，脚本会自动将优化结果保存至 `D:\work\2025hxczqn`，以满足“将两份最终迭代的研究计划保存在本地工作文件夹”这一需求；在其它平台则仍默认使用当前工作目录。

## 高引用文献抓取与计划迭代

1. **抓取文献列表**（联网环境）：
   ```bash
   python tools/sci_citation_crawler.py "serum TDP-43 sepsis" --rows 20 --format markdown --output data/cached_serum_tdp43_sepsis_crossref.json
   ```
   生成的缓存文件可拷贝至离线环境使用。
2. **运行文献迭代管线**：
   ```bash
   python tools/literature_pipeline.py \
       --plan plans/serum_tdp43_sepsis_project.md \
       --cache data/cached_serum_tdp43_sepsis_crossref.json \
       --rows 12 \
       --offline
   ```
   运行时若未提供 `--output-dir` 与 `--word-output`，脚本会自动将所有下载、摘要与 Word 导出保存到仓库根目录下的 `outputs/` 文件夹（已在 `.gitignore` 中忽略）。若无缓存且具备网络，可省略 `--cache` 参数以实时抓取。

3. **清理工作区以避免二进制文件误提交**：
   ```bash
   python tools/cleanup_workspace.py
   ```
   如需演练可加 `--dry-run` 观察即将删除的文件。建议在生成 Word/PDF 等二进制文件后执行一次，再 `git status` 确认无多余改动。

> 说明：`data/` 目录用于存放文献元数据缓存；`outputs/` 目录用于存放本地生成的二进制/大文件。两者均已在版本控制中忽略，避免推送二进制文件阻塞分支更新，可按 README 指引随时重新生成。如需彻底清空，可运行 `python tools/cleanup_workspace.py`。

## 版本记录

- **v0.4 (当前)**：增强 `.gitignore` 模式、提供清理脚本，确保仓库内不再遗留 Word/PDF/压缩包等二进制 artefact，便于更新 PR。
- **v0.3 及更早**：允许自定义 Word 导出路径，支持离线缓存与多模态迭代分析。
