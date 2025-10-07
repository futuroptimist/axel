# Issue 0004: Adopt Flywheel Template

[`flywheel`](https://github.com/futuroptimist/flywheel) provides a GitHub template with preconfigured linting, testing and docs checks. Integrate it into new projects listed in `repos.txt` so they start with consistent CI pipelines.

- [x] mention flywheel in README and AGENTS guidelines
- [x] ensure repos.txt includes the flywheel repo
- [x] evaluate existing repos for alignment with flywheel's lint and test setup (use
  `python -m axel.flywheel` with coverage in `tests/test_flywheel.py`)
