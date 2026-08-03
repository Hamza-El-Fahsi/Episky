"""`verification` — Collect/Compare/Outcome.

Owning RFC: RFC-0006; authority per RFC-0004 §4.6 (Verify).
Responsibilities: the deterministic Collect→Normalize→Facts→Compare→
    Outcome process; comparison against declared Postconditions (V10);
    contradiction always wins (V7).
Forbidden responsibilities: never the LLM's or a Skill's assessment
    (V3); the Executor may not verify itself (RFC-0004 §4.9).
Layer 2 (blueprint §4.1). Imports: factlayer, schema, systemmodel.
"""
