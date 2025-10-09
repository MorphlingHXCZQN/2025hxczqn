from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.run import execute_pipeline


def test_execute_pipeline(tmp_path):
    config_path = Path("configs/search.yml")

    # Redirect output root to temporary directory for isolated testing
    config_text = config_path.read_text(encoding="utf-8")
    adjusted = config_text.replace("D/计划", str(tmp_path))
    patched_config = tmp_path / "search.yml"
    patched_config.write_text(adjusted, encoding="utf-8")

    results = execute_pipeline(patched_config, output_root=tmp_path)
    assert len(results) == 4

    summary_csv = tmp_path / "data" / "processed" / "literature_summary.csv"
    assert summary_csv.exists()
    content = summary_csv.read_text(encoding="utf-8")
    assert "Multiparametric MRI radiomics" in content

    markdown = tmp_path / "文献自动总结.md"
    assert markdown.exists()

    word_doc = tmp_path / "文献自动总结.docx"
    assert word_doc.exists()
