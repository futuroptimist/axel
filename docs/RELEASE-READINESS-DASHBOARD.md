<!-- BEGIN: AXEL HILLCLIMB -->
Release‑Readiness Dashboard (Aug–Sep 2025)
Legend: [ ] = not started · [x] = done

Definition of Done for v0.1
- [ ] Tag v0.1.0 and publish Release notes (What’s new, Try it in 60s, Roadmap next)
- [ ] 1‑click install path (pipx / docker compose / brew or scoop, as applicable)
- [ ] 90‑second demo video/GIF linked at top of README
- [x] Quickstart (≤60s) at top of README (guarded by
  `tests/test_release_readiness.py::test_release_dashboard_marks_quickstart_complete`)
- [x] Mini architecture: 3 bullets + 1 diagram (see README#architecture and tests/test_readme.py::test_readme_includes_architecture_section_with_diagram)
- [ ] CI green on default branch; coverage badge visible
- [ ] Security: CodeQL + credential scanning + Dependabot
- [x] Docs: FAQ, Known issues/Footguns, Status: Alpha badge (see
  `tests/test_release_readiness_dashboard.py`)
- [ ] Community: CONTRIBUTING, CoC, Issue/PR templates, ≥3 good first issues

Summary Table
Repo v0.1 tag Release notes 1‑click install Demo Landing page CI green Coverage badge Security scans Arch doc
token.place [ ] [ ] [x] [ ] [ ] [ ] [ ] [ ] [ ]
f2clipboard [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
flywheel [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
gitshelves [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
sugarkube [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
sigma [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]
dspace [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ]

<!-- END: AXEL HILLCLIMB -->
