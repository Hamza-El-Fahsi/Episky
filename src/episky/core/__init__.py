"""`core` — Orchestration Core.

Owning RFC: RFC-0002.
Responsibilities: the session loop and state transitions; enforcement
    of the decision rules (RFC-0001 §5 Orchestration Core); keep the
    provider world separate from the machine world; consult components
    per §6; run failure recovery per §10.
Forbidden responsibilities: never re-implements a forbidden authority
    (classify, verify, approve, execute) — it routes (RFC-0002 §5;
    RFC-0004 §4.3).
Layer 6 (blueprint §4.1). Imports: all packages above (the conductor).
"""
