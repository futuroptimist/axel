def test_init_run_as_script(tmp_path):
    import os
    import pathlib
    import subprocess
    import sys

    module_path = pathlib.Path("axel/__init__.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    result = subprocess.run(
        [sys.executable, str(module_path)], capture_output=True, env=env
    )
    assert result.returncode == 0
