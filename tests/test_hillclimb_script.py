import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "hillclimb_axel", Path('.axel/hillclimb/scripts/axel.py')
)
axel_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(axel_script)


def test_read_missing_file_returns_empty(tmp_path):
    missing = tmp_path / 'missing.md'
    assert axel_script.read(missing) == ""


def test_create_task_markdown_no_prompts(tmp_path, monkeypatch):
    monkeypatch.setattr(axel_script, 'PROMPTS_DIR', tmp_path)
    card = {"title": "Test", "key": "t", "acceptance_criteria": []}
    cfg = {"touch_budget": {"files_max": 1, "loc_max": 1}}
    result = axel_script.create_task_markdown('o/r', card, 1, cfg, tmp_path)
    assert "AXEL TASK" in result
