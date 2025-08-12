import sys
import types


def test_run_discord_bot(monkeypatch):
    """``run_discord_bot`` invokes ``discord_bot.run`` lazily."""
    called = []
    fake_module = types.ModuleType("axel.discord_bot")

    def fake_run():
        called.append(True)

    fake_module.run = fake_run
    monkeypatch.setitem(sys.modules, "axel.discord_bot", fake_module)
    from axel import run_discord_bot

    run_discord_bot()
    assert called
