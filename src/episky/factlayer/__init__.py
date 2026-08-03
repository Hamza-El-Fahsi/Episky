"""`factlayer` — Diagnostics & Fact Layer.

Owning RFC: RFC-0005 (pipeline); authority per RFC-0004 §4.5/§4.6.
Responsibilities: normalize Observations into canonical Facts; carry
    status, provenance, freshness; own Fact storage and invalidation.
Forbidden responsibilities: never mutates; never consumes secrets into
    long-term context (RFC-0001 §5); Facts are provider-independent
    (F6).
Layer 2 (blueprint §4.1). Imports: collectors, schema, systemmodel,
    trust.
"""
