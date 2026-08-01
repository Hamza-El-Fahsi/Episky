# Episky

> Safe, human-approved, LLM-driven Linux troubleshooting — in your terminal.

Episky is an open-source terminal (TUI) assistant that helps Linux beginners
diagnose and repair their own systems. You bring your preferred LLM (OpenAI,
Anthropic, Gemini, or a local model); Episky brings controlled, audited access
to inspect the machine and run only the commands you approve.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## Why Episky

- **Safety before automation.** Nothing state-changing happens without your
  explicit approval. There is no unattended mode.
- **The AI proposes; deterministic tooling verifies.** The model forms
  hypotheses; facts come from the machine, never from a guess.
- **Bring your own LLM.** Hosted or local, through a uniform provider boundary.
- **Community skills.** Reusable, reviewed troubleshooting procedures packaged
  for beginners.

## Current status

**Architecture phase.** There is no product code yet. The design is defined by
an accepted RFC series, which is the contract every future contribution builds
on.

| RFC | Title | Status |
| --- | --- | --- |
| RFC-0000 | Architectural Roadmap (index) | Accepted |
| RFC-0001 | Architecture & Design Foundations | Accepted |
| RFC-0002 | Runtime Architecture & Session State Machine | Accepted |
| RFC-0003 | Project Vocabulary and Governance | Accepted |

## Read this first

- [`rfc/RFC-0001-architecture.md`](rfc/RFC-0001-architecture.md) — what Episky
  is, and — just as importantly — what it is not.
- [`rfc/RFC-0003-vocabulary-and-governance.md`](rfc/RFC-0003-vocabulary-and-governance.md) —
  the project's dictionary and constitution.
- [`rfc/RFC-0000-architectural-roadmap.md`](rfc/RFC-0000-architectural-roadmap.md) —
  what gets designed next, and in what order.

## Contributing

Contributions are welcome. Before contributing, read
[`CONTRIBUTING.md`](CONTRIBUTING.md) — it defines the RFC process and the
mandatory development workflow (issues, branches, Conventional Commits, pull
requests).

## Security

Episky's security model is its reason to exist. If you find a vulnerability,
see [`SECURITY.md`](SECURITY.md) and do not open a public issue.

## License

MIT — see [`LICENSE`](LICENSE).
