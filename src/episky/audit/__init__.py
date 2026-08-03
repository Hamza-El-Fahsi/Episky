"""`audit` — Audit & Transcript.

Owning RFC: RFC-0013; authority per RFC-0004 §4.12.
Responsibilities: append-only, tamper-evident records of the §7
    categories, written before the consequence (AU8); transcript
    derived from the record (§8); reconciliation on failure (§22).
Forbidden responsibilities: holds records, never the material (RFC-0013
    §7 category 9, §10); no secret values recorded (SC4); no decision
    authority (RFC-0004 §4.12).
Layer 4 (blueprint §4.1). Imports: schema, secrets.
"""
