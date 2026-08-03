"""`skills` — Skill Runtime.

Owning RFC: RFC-0011; authority per RFC-0004 §4.10.
Responsibilities: load and authenticate Skill packages (§22),
    activation lifecycle (§23), and gate participation — every Skill
    Action passes the full gate, never approved as a unit (SK4).
Forbidden responsibilities: Skill holds Propose/Infer only (RFC-0004
    §4.10); never receives a secret (SC5).
Layer 5 (blueprint §4.1). Imports: schema, collectors, trust, policy,
    factlayer.
"""
