"""`collectors` — built-in diagnostics registry.

Owning RFC: RFC-0005 §2; RFC-0003 §2.4 (Collector); RFC-0021
    (vocabulary).
Responsibilities: the registry of deterministic, read-only inspection
    procedures; each Collector answers one question and carries
    declared inputs and provenance behavior.
Forbidden responsibilities: no mutation of the machine; each Collector
    answers one question (RFC-0003 §2.4).
Layer 2 (blueprint §4.1). Imports: schema, systemmodel, trust.
"""
