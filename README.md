# 食道肿瘤影像检索与离线管线

本项目提供一个可在无网络环境下运行的离线检索演示流程，模拟在 PubMed 与 Google Scholar 上检索“食道肿瘤 + 影像（CT/MRI）”相关文献并生成摘要与日志。仓库同时包含 Windows 本地 `D:\计划` 目录结构的示例输出，可在拥有真实网络权限时替换为线上抓取结果。

## 项目结构

```
├── configs/              # 管线配置（默认检索关键字、数据源）
├── docs/                 # 工作流说明、上传指导等文档
├── pipeline/             # 管线代码（配置加载、检索、下载、摘要生成）
├── resources/            # PubMed 与 Google Scholar 的桩数据
├── tests/                # Pytest 用例，覆盖核心离线流程
└── D/计划/               # Windows 风格的示例输出与工作流说明
```

## 快速开始

1. **安装依赖**（可选）：管线仅使用标准库，如需在虚拟环境中运行可自行为 `requirements.txt` 或 `pyproject.toml` 安装。
2. **执行离线演示管线**：

   ```bash
   python -m pipeline.run --config configs/search.yml
   ```

   命令会在仓库内复现 `D/计划` 下的示例输出（含 CSV、Markdown、7 轮迭代日志，以及运行时生成但不纳入版本控制的 Word 摘要）。

3. **指向 Windows 本地 `D:\计划` 目录**（如需在本地电脑运行并保持目录结构）：

   ```bash
   python -m pipeline.run --config configs/search.yml --output-root "D:/计划"
   ```

   建议在执行前先创建虚拟环境或使用 PyCharm/VS Code 打开仓库，根据 `docs/工作流总览.md` 与 `docs/检索与爬虫方案.md` 继续扩展真实爬虫逻辑。

## 上传到 GitHub 的建议流程

由于当前环境无法直接访问您的 GitHub 账号，仓库已整理好必要的文档与目录。请参考 `docs/github_upload.md` 中的详细步骤，在本地完成以下操作：

1. 克隆/复制本仓库到本地；
2. 在 GitHub 创建新的远程仓库；
3. 关联远程并推送 `main`（或其他）分支；
4. 确认 `D/计划` 内的示例文件已包含在版本历史中，或按需修改 `.gitignore` 排除真实下载的大体量数据。

如需将仓库作为模板，可先在本地运行 `pytest` 与示例管线，验证离线流程通过，再推送到远程。

## 开发与测试

- 运行全部用例：

  ```bash
  pytest
  ```

- 修改配置后再次验证：

  ```bash
  python -m pipeline.run --config configs/search.yml
  ```

- 生成的关键成果包括：

  - `data/processed/literature_summary.csv`：带引用次数的归一化结果；
  - `文献自动总结.md` 与 `文献自动总结.docx`：摘要；
  - `研究方案迭代日志.md`：7 轮医工融合研究策略迭代记录；
  - `研究方案最终稿.md`：基于高引用文献形成的定稿研究方案。

欢迎在 `docs/` 目录下补充更多研究笔记或扩展真实爬虫脚本时的注意事项，以便团队协同使用。
