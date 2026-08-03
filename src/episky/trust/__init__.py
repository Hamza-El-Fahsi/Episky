"""`trust` — trust classes and sanitization.

Owning RFC: RFC-0007.
Responsibilities: trust classes T1–T12 (§10), sanitization S1–S8
    (§11), Hostile quarantine and fail-closed failure behavior (§15).
Forbidden responsibilities: trust never upgrades via sanitize (T9);
    consumed at every boundary toward the LLM, the Operator terminal,
    and any interpreter.
Layer 1 (blueprint §4.1). Imports: schema.
"""
