"""Generate multi-iteration research planning artefacts."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .search import SearchResult


@dataclass
class IterationOutput:
    """Paths to the generated iteration artefacts."""

    log_path: Path
    final_plan_path: Path


class IterationPlanner:
    """Summarise literature insights across multiple improvement rounds."""

    def __init__(self, output_root: Path, iterations: int = 1):
        self.output_root = output_root
        self.iterations = max(1, iterations)
        self.log_path = output_root / "研究方案迭代日志.md"
        self.final_plan_path = output_root / "研究方案最终稿.md"

    def run(self, results: Sequence[SearchResult]) -> IterationOutput:
        ranked = self._rank_results(results)
        iteration_lines = self._build_iteration_log(ranked)
        final_plan_lines = self._build_final_plan(ranked)

        self._write(self.log_path, iteration_lines)
        self._write(self.final_plan_path, final_plan_lines)
        return IterationOutput(self.log_path, self.final_plan_path)

    def _rank_results(self, results: Sequence[SearchResult]) -> List[SearchResult]:
        return sorted(
            results,
            key=lambda item: (
                -item.citation_count,
                -item.year,
                item.journal.lower(),
                item.title.lower(),
            ),
        )

    def _build_iteration_log(self, ranked: Sequence[SearchResult]) -> List[str]:
        header = [
            "# 研究方案迭代日志",
            "",
            "以下 7 轮迭代演示如何逐步引入高引用度的医工交叉文献,",
            "以优化食管肿瘤 MRI/CT 融合研究方案。",
            "",
        ]

        if not ranked:
            return header + ["暂无文献记录可用于迭代。"]

        iterations = self.iterations
        top_refs = ranked[: iterations + 3]
        modality_counter = Counter(
            modality for item in ranked for modality in item.imaging_modality
        )

        for idx in range(1, iterations + 1):
            ref = top_refs[(idx - 1) % len(top_refs)]
            modal_focus = self._modal_focus(ref, modality_counter)
            header.extend(
                [
                    f"## 第{idx}轮：聚焦{modal_focus}",
                    (
                        f"- 核心文献：《{ref.title}》({ref.journal}, {ref.year})，"
                        f"引用 {ref.citation_count} 次，覆盖 {', '.join(ref.imaging_modality)}。"
                    ),
                    (
                        "- 行动要点：将该研究的特征提取/模型策略引入本地数据集，"
                        "验证在术前评估、放化疗疗效或随访复发预测中的可复现性。"
                    ),
                    (
                        "- 医工结合深化：联合影像工程特征、临床分期与疗效终点，"
                        "并同步准备可公开分享的特征工程流程。"
                    ),
                    "",
                ]
            )

        return header

    def _build_final_plan(self, ranked: Sequence[SearchResult]) -> List[str]:
        lines = [
            "# 食管肿瘤 MRI/CT 融合研究方案（第7轮定稿）",
            "",
            "## 研究目标",
            (
                "- 构建基于 MRI 与 CT 多模态影像的病理/疗效预测模型，"
                "针对食管癌患者的术前分期、放化疗反应及复发风险评估。"
            ),
            (
                "- 引入高引用度医工交叉成果中的影像工程、深度学习和多模态融合策略，"
                "形成可复现的临床决策支持工具。"
            ),
            "",
        ]

        if ranked:
            lines.extend(self._reference_section(ranked))
            lines.extend(self._data_needs_section())
            lines.extend(self._analysis_plan_section(ranked))
        else:
            lines.append("暂无文献信息，需先执行检索流程。")
        return lines

    def _reference_section(self, ranked: Sequence[SearchResult]) -> List[str]:
        lines = ["## 核心参考文献（按引用次数排序）", ""]
        for item in ranked[: min(10, len(ranked))]:
            lines.append(
                (
                    f"- 《{item.title}》，{item.journal} ({item.year})，引用 {item.citation_count} 次。"
                    f" 重点：{item.key_findings}"
                )
            )
        lines.append("")
        return lines

    def _data_needs_section(self) -> List[str]:
        return [
            "## 数据与特征需求",
            "",
            "- 影像：术前 CT、MRI（含 DWI、DCE 等功能序列），统一重采样与配准。",
            "- 临床：TNM/cT 分期、病理分型、放化疗方案、手术/随访结局。",
            "- 分子：若可获得，加入血液或组织分子标志物以支持多模态建模。",
            "- 工程特征：影像放射组学、深度学习特征向量、时序随访指标。",
            "",
        ]

    def _analysis_plan_section(self, ranked: Sequence[SearchResult]) -> List[str]:
        modality_clusters = defaultdict(list)
        for item in ranked:
            key = ", ".join(item.imaging_modality) or "未标注"
            modality_clusters[key].append(item)

        lines = ["## 分析路径", ""]
        lines.append(
            "1. 数据治理：执行图像标准化、去噪与器官分割，建立跨模态联合特征仓库。"
        )
        lines.append(
            "2. 特征工程：依据前述高引用研究复现 radiomics、深度学习嵌入及融合策略。"
        )
        lines.append(
            "3. 模型开发：采用交叉验证与外部验证集，比较传统机器学习与 Transformer 等方法。"
        )
        lines.append(
            "4. 临床验证：与放射科、胸外科联合评估模型对 cT 分期、疗效预测的增益。"
        )
        lines.append(
            "5. 可解释性：输出特征重要性、注意力热图，支撑医工协同决策。"
        )
        lines.append("")

        lines.append("### 模态专题")
        for modality, items in modality_clusters.items():
            exemplar = items[0]
            lines.append(
                (
                    f"- {modality}：参考《{exemplar.title}》（引用 {exemplar.citation_count} 次）"
                    "，设置与我们数据一致的预处理和模型超参数。"
                )
            )
        lines.append("")
        lines.append("### 迭代与交付")
        lines.append(
            "- 每轮迭代输出模型性能、重要特征和临床评审意见，持续对齐研究目标。"
        )
        lines.append(
            "- 第7轮后固化代码、文档与可复现脚本，准备投稿或开源发布。"
        )
        lines.append("")
        return lines

    def _modal_focus(self, ref: SearchResult, counter: Counter[str]) -> str:
        if not ref.imaging_modality:
            return "多模态策略"
        primary = ref.imaging_modality[0]
        if counter[primary] == 1 and len(counter) > 1:
            return f"补强{primary}特色"
        return f"{primary}与临床协同"

    def _write(self, path: Path, lines: Iterable[str]) -> None:
        with path.open("w", encoding="utf-8") as fp:
            fp.write("\n".join(lines))

