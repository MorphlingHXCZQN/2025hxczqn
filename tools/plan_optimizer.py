"""Utilities for iteratively优化博士研究计划.

This module提供一个命令行工具, 将当前研究计划、网络检索摘要与GPT模型交互, 以便持续优化文本。

Usage示例::

    python tools/plan_optimizer.py \
        --plan plans/emergency_phd_plan.md \
        --query "sepsis precision emergency medicine" \
        --model gpt-4o-mini

运行流程:
1. 读取研究计划文本。
2. 调用 DuckDuckGo 检索获取相关网页标题与摘要, 避免与既有研究同质化。
3. 将计划、检索摘要与自定义优化目标发送给 OpenAI GPT 模型, 获得改进建议或修订后的计划草稿。
4. 将建议保存为 Markdown, 并在终端打印。

注意事项:
- 需要环境变量 ``OPENAI_API_KEY`` 或通过 ``--api-key`` 参数显式提供。
- 网络检索仅做参考, 请确保遵守相关网站使用条款与学术规范。
- 建议在版本控制下使用, 方便比较不同迭代结果。
"""

from __future__ import annotations

import argparse
import os
import textwrap
from dataclasses import dataclass
from typing import Iterable, List, Optional

import importlib
import importlib.util

requests_spec = importlib.util.find_spec("requests")
if requests_spec is not None:
    requests = importlib.import_module("requests")
else:  # pragma: no cover - 运行时提示用户安装依赖
    requests = None

openai_spec = importlib.util.find_spec("openai")
if openai_spec is not None:
    OpenAI = importlib.import_module("openai").OpenAI
else:  # pragma: no cover - 运行时提示用户安装依赖
    OpenAI = None


DUCKDUCKGO_URL = "https://duckduckgo.com/html/"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def fetch_duckduckgo_results(query: str, max_results: int = 5) -> List[SearchResult]:
    """Fetch简易 DuckDuckGo 搜索结果.

    为避免依赖复杂解析库, 这里采用 DuckDuckGo 简洁 HTML 接口并做轻量解析。
    """

    if requests is None:
        raise ModuleNotFoundError(
            "缺少 requests 依赖, 可执行 'pip install requests' 或使用 --offline 模式。"
        )

    params = {"q": query, "kl": "wt-wt"}
    headers = {"User-Agent": "Mozilla/5.0 (ResearchPlanOptimizer)"}
    response = requests.post(DUCKDUCKGO_URL, data=params, headers=headers, timeout=15)
    response.raise_for_status()

    results: List[SearchResult] = []
    for block in response.text.split('<div class="result__body">'):
        if "result__title" not in block:
            continue
        title_start = block.find('result__a">')
        url_start = block.find('href="')
        snippet_start = block.find('result__snippet">')
        if title_start == -1 or url_start == -1:
            continue

        title = block[title_start + len('result__a">') :].split("</a>", 1)[0]
        title = title.replace("<b>", "").replace("</b>", "").strip()

        url = block[url_start + len('href="') :].split('"', 1)[0]

        snippet = ""
        if snippet_start != -1:
            snippet = block[snippet_start + len('result__snippet">') :].split("</a>", 1)[0]
            snippet = (
                snippet.replace("<b>", "")
                .replace("</b>", "")
                .replace("<span class=\"result__snippet js-result-snippet\">", "")
                .replace("</span>", "")
                .strip()
            )
        results.append(SearchResult(title=title, url=url, snippet=snippet))
        if len(results) >= max_results:
            break
    return results


@dataclass
class GPTInteractionConfig:
    model: str
    api_key: str
    temperature: float = 0.3
    max_tokens: int = 1200


def build_prompt(plan_text: str, results: Iterable[SearchResult], objective: str) -> str:
    """组装发送给GPT的提示词."""

    bullet_points = "\n".join(
        f"- {res.title}\n  链接: {res.url}\n  摘要: {res.snippet}" for res in results
    ) or "- (无外部检索结果, 请聚焦内部优化)"

    template = f"""你是一名科研规划顾问, 需要基于当前博士研究计划进行优化, 避免与公开研究雷同。

### 当前计划
{plan_text}

### 外部检索摘要
{bullet_points}

### 优化目标
{objective}

请结合外部信息与既有工作, 输出: 
1. 三条关键优化建议 (每条≤80字)。
2. 一份在原结构基础上的修订版计划(如无必要可保持部分章节)。
3. 标记需要进一步查证的内容并给出参考方向。
"""
    return textwrap.dedent(template)


def call_gpt(config: GPTInteractionConfig, prompt: str) -> str:
    """调用OpenAI GPT接口."""

    if OpenAI is None:
        raise ModuleNotFoundError(
            "缺少 openai 依赖, 可执行 'pip install openai>=1.0' 或使用 --offline 模式。"
        )

    client = OpenAI(api_key=config.api_key)
    response = client.responses.create(
        model=config.model,
        input=[{"role": "user", "content": prompt}],
        temperature=config.temperature,
        max_output_tokens=config.max_tokens,
    )
    return response.output_text


def generate_offline_output(plan_text: str, objective: str) -> str:
    """在无法访问外部服务时, 基于简单启发式生成建议."""

    headings: List[str] = []
    for line in plan_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("# "))

    headings_preview = "、".join(headings[:5]) or "(未检测到标题)"

    suggestions = [
        "强化数据治理与质量控制流程, 明确数据溯源与共享机制。",
        "在方法部分加入可复现性计划, 指定评估指标与开源策略。",
        "规划跨学科合作资源, 对接潜在临床或工程伙伴。",
    ]

    template = f"""## 离线优化建议\n\n### 关键优化建议\n1. {suggestions[0]}\n2. {suggestions[1]}\n3. {suggestions[2]}\n\n### 修订参考草案\n沿用原有章节结构 ({headings_preview})，针对“{objective}”目标：\n- 在研究背景中补充对最新政策与指南的对照分析。\n- 在技术路线章节加入实验设计表格与关键里程碑。\n- 在临床转化/推广章节说明伦理合规、数据安全与可持续运营。\n\n### 待进一步查证\n- 核实当前数据资源的授权范围与外部合作限制。\n- 更新近一年高影响力期刊中的相关研究以避免同质化。\n- 对国内外资助项目或多中心协作机会进行调研。\n"""

    return textwrap.dedent(template)


def determine_output_path(plan_path: str, output_dir: Optional[str]) -> str:
    """Return the destination path for the optimized plan.

    If ``output_dir`` is ``None`` we place the file in the当前工作目录,
    满足“保存至本地工作文件夹”需求。"""

    target_dir = output_dir or os.getcwd()
    os.makedirs(target_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(plan_path))[0]
    return os.path.join(target_dir, f"{base_name}_optimized.md")


def run(
    plan_path: str,
    query: str,
    model: str,
    objective: str,
    api_key: Optional[str],
    offline: bool = False,
    output_dir: Optional[str] = None,
) -> None:
    if not os.path.exists(plan_path):
        raise FileNotFoundError(f"计划文件不存在: {plan_path}")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan_text = f.read()

    search_results: List[SearchResult] = []

    if offline:
        print("[INFO] Offline 模式开启, 跳过网络检索与GPT调用。")
        gpt_output = generate_offline_output(plan_text, objective)
    else:
        print("[INFO] Fetching web references...")
        search_results = fetch_duckduckgo_results(query)

        print("[INFO] Building prompt and contacting GPT...")
        config = GPTInteractionConfig(
            model=model,
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
        )
        if not config.api_key:
            raise EnvironmentError("未提供 OpenAI API Key, 请通过环境变量或参数设置。")

        prompt = build_prompt(plan_text=plan_text, results=search_results, objective=objective)
        gpt_output = call_gpt(config, prompt)

    output_path = determine_output_path(plan_path, output_dir)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(gpt_output)

    print("[INFO] 优化建议已生成 ->", output_path)
    print("\n===== GPT 建议 =====\n")
    print(gpt_output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="研究计划迭代优化工具")
    parser.add_argument("--plan", required=True, help="研究计划 Markdown 文件路径")
    parser.add_argument("--query", required=True, help="DuckDuckGo 检索关键词")
    parser.add_argument(
        "--objective",
        default="提升创新性、强化方法论可行性并指出潜在合作方向。",
        help="向GPT说明的优化目标",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI 模型名称 (例如 gpt-4o-mini, gpt-4.1 等)",
    )
    parser.add_argument("--api-key", help="OpenAI API Key, 优先级高于环境变量")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="无需网络与OpenAI依赖的离线模式, 将生成启发式建议",
    )
    parser.add_argument(
        "--output-dir",
        help="保存迭代计划的目标文件夹, 默认写入当前工作目录",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        plan_path=args.plan,
        query=args.query,
        model=args.model,
        objective=args.objective,
        api_key=args.api_key,
        offline=args.offline,
        output_dir=args.output_dir,
    )
