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

import requests

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - 用于提醒用户安装依赖
    raise SystemExit(
        "需要安装 openai Python SDK (pip install openai>=1.0)."
    ) from exc


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

    client = OpenAI(api_key=config.api_key)
    response = client.responses.create(
        model=config.model,
        input=[{"role": "user", "content": prompt}],
        temperature=config.temperature,
        max_output_tokens=config.max_tokens,
    )
    return response.output_text


def run(plan_path: str, query: str, model: str, objective: str, api_key: Optional[str]) -> None:
    if not os.path.exists(plan_path):
        raise FileNotFoundError(f"计划文件不存在: {plan_path}")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan_text = f.read()

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

    output_path = f"{plan_path.rsplit('.', 1)[0]}_optimized.md"
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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        plan_path=args.plan,
        query=args.query,
        model=args.model,
        objective=args.objective,
        api_key=args.api_key,
    )
