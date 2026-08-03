"""`secrets` — secret classification and boundaries.

Owning RFC: RFC-0009.
Responsibilities: deterministic secret classification (§3), redaction
    that fails closed (SC13/SC14), Secure Store abstraction (SC1, SC8,
    SC12).
Forbidden responsibilities: no value enters Context/View/Audit/
    extensions (SC2–SC5); exposure is compromise (SC15).
Layer 3 (blueprint §4.1). Imports: schema, trust.
"""
