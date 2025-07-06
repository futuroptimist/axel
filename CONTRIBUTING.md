# Contributing

Thank you for helping improve **axel**!

## Setup

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install pre-commit
pre-commit install
```

Run all checks before committing:

```bash
pre-commit run --all-files
```

## Pull Requests

- Add tests for new functionality.
- Keep the [roadmap](README.md#roadmap) updated when you close an item.
- By submitting a PR you agree to license your work under the MIT license.

For additional tips see [CONTRIBUTING.md](CONTRIBUTING.md).
