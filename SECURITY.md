# Security Policy

Episky gives a model-controlled tooling access to inspect a Linux system and,
with explicit human approval, to change it. Security is not a feature of this
project; it is the point of the project. The security model is defined by
RFC-0001 (trust boundaries and security principles) and RFC-0002 (runtime
invariants).

## Reporting a vulnerability

**Do not open a public issue for a vulnerability.**

Report it privately:

- Open a GitHub Security Advisory on the repository ("Report a vulnerability"),
  or
- Contact the maintainers privately through GitHub.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce, where possible.
- Which behavior it violates (an RFC invariant, a trust boundary, or a security
  principle), if you know.

## What counts as a vulnerability here

- Any path by which untrusted input (model output, machine output, or skill
  content) can influence an approved action without deterministic confirmation.
- Violation of a runtime invariant in RFC-0002 §9.
- Secret leakage into provider context, transcripts, or the audit log.
- Execution of an action without a valid, scoped approval token.

If in doubt, report it. This project treats invariant violations as security
defects, not style issues.

## Scope and expectations

- This project is in the architecture phase; there is no stable release yet.
- Security-relevant fixes that change behavior are changes to the architecture
  and go through the RFC amendment process (RFC-0003).
- We will acknowledge reports, assess severity, and work toward a fix before
  public disclosure where possible.
