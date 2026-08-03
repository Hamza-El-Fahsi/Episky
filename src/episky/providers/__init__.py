"""`providers` — Provider adapters.

Owning RFC: RFC-0010; RFC-0001 §5 (Providers).
Responsibilities: one uniform interface to all vendors; structured
    output validation (§4, §8); consume exactly the Provider View
    (§3, PR14).
Forbidden responsibilities: never creates Facts (F1, F6), never
    executes / verifies / approves (RFC-0010 §2), never receives
    secrets (SC3); output is untrusted data, never instructions
    (RFC-0007 T4).
Layer 5 (blueprint §4.1). Imports: schema, trust, context.
"""
