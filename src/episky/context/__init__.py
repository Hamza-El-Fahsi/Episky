"""`context` — Context & Memory.

Owning RFC: RFC-0012 (assembly); authority per RFC-0004 §4.11;
    Provider View per RFC-0010 §3.
Responsibilities: deterministic Context composition from Facts, Goal,
    bounded history, and Skill material; boundary rules and secret-free
    assembly (SC2); consented Memory; the Provider View as the only
    outward channel (PR14).
Forbidden responsibilities: never the Audit (CM15); re-assembly never
    restores (CM13).
Layer 4 (blueprint §4.1). Imports: schema, factlayer, trust, secrets,
    systemmodel.
"""
