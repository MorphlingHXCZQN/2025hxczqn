# 2025hxczqn

本仓库包含两份博士研究计划及其迭代优化工具：

- `plans/emergency_phd_plan.md`：聚焦脓毒症多源数据融合与智能急诊决策的急诊医学博士研究计划。
- `plans/imaging_phd_plan.md`：面向胶质瘤影像-多组学精准诊疗的医学影像博士研究计划。
- `tools/plan_optimizer.py`：结合DuckDuckGo检索与OpenAI GPT模型，对研究计划持续优化的命令行脚本。

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
   生成的优化建议会保存为 `plans/emergency_phd_plan_optimized.md` 并打印在终端，便于迭代完善研究计划。

> 如需针对影像计划进行迭代，可将 `--plan` 参数替换为 `plans/imaging_phd_plan.md` 并调整检索关键词。

如当前环境无法联网或缺少 OpenAI/requests 依赖，可使用离线模式快速获得启发式建议：

```bash
python tools/plan_optimizer.py \
    --plan plans/emergency_phd_plan.md \
    --query "sepsis precision medicine doctoral proposal" \
    --offline
```
