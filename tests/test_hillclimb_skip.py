import importlib.util
from pathlib import Path
from types import SimpleNamespace


def load_module():
    spec = importlib.util.spec_from_file_location(
        "hillclimb", ".axel/hillclimb/scripts/axel.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skips_inaccessible_repo(monkeypatch, tmp_path, capsys):
    hc = load_module()

    def fake_load_yaml(path):
        if path == hc.CONFIG:
            return {
                "branch_prefix": "hc",
                "touch_budget": {"files_max": 1, "loc_max": 1},
                "labels": [],
                "pr": {},
            }
        if path == hc.REPOS:
            return {
                "repos": [
                    {
                        "slug": "missing/repo",
                        "default_branch": "main",
                        "enabled": True,
                    }
                ]
            }
        if Path(path).name == "card.yml":
            return {"key": "test", "acceptance_criteria": []}
        return {}

    card_dir = tmp_path / "cards"
    card_dir.mkdir()
    (card_dir / "card.yml").write_text("key: test\nacceptance_criteria: []\n")

    monkeypatch.setattr(hc, "CARDS_DIR", card_dir)
    monkeypatch.setattr(hc, "load_yaml", fake_load_yaml)
    monkeypatch.setattr(hc, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        hc,
        "ensure_clone",
        lambda slug, default_branch: (
            _ for _ in ()
        ).throw(RuntimeError("clone failed")),
    )

    args = SimpleNamespace(runs=1, card=None, execute=False)
    hc.cmd_hillclimb(args)
    out = capsys.readouterr().out
    assert "Skipping missing/repo" in out
