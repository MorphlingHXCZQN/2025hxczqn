# 文档说明

> 所有工作流文件与 Word 模板已统一迁移至 `D/计划/` 目录，请从该目录获取最新版本。

- `D/计划/工作流总览.md`：整理了自动化检索、数据处理与文档归档的整体流程。
- `D/计划/检索与爬虫方案.md`：详细说明 PubMed 与 Google Scholar 的检索策略、爬虫架构、落盘结构与合规要点。
- `D/计划/literature_review_template.md`：文献记录模板，可按需导出为 Word 或在线协作文档。
- `D/计划/research_plan_draft.md`：结合现有临床数据背景的研究方案草稿，可在文献综述完成后继续完善。
- `D/计划/文献自动总结.md`：示例汇总文档，运行管线可额外生成 Word 版本（运行时创建，未纳入版本控制）。

## 离线示例爬虫工作流

仓库内新增 `pipeline/` Python 模块与 `configs/search.yml` 示例配置，可在无网络环境下复现从检索到落盘的完整流程：

```bash
python -m pipeline.run --config configs/search.yml
```

> ⚠️ 如需在 Windows 本地将结果直接写入 `D:\计划\`，请在执行命令时追加
>
> ```bash
> python -m pipeline.run --config configs/search.yml --output-root "D:/计划"
> ```
>
> 该参数会覆盖配置文件中的默认输出路径，首次运行会在 D 盘自动创建完整的目录结构。

默认启用 `offline_mode`，使用 `resources/` 目录中的示例数据生成以下文件：

- `D/计划/data/raw/<source>/<query>.json`：按数据源保存的原始元数据。
- `D/计划/data/processed/literature_summary.csv`：标准化后的检索结果表。
- `D/计划/文献自动总结.md`：根据元数据生成的 Markdown 摘要。
- `D/计划/logs/search_history.csv`：记录每次查询的执行时间与条数。

若要接入真实 API，请将 `configs/search.yml` 中的 `offline_mode` 设为 `false` 并扩展 `pipeline/` 下对应的数据源客户端以加入正式的网络请求逻辑。
