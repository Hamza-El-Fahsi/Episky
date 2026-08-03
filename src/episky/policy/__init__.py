"""`policy` — Approval & Policy Engine.

Owning RFC: RFC-0008 §6–§8; RFC-0004 §4.7/§4.8; RFC-0002 invariant 7.
Responsibilities: deterministic risk classification (never the LLM's
    self-report); the gate per class; Approval Token mint/validate;
    the Operator-owned default-deny policy.
Forbidden responsibilities: never trusts the LLM's self-report
    (RFC-0002 invariant 7); no approval without a gate.
Layer 3 (blueprint §4.1). Imports: schema, trust, factlayer.
"""
