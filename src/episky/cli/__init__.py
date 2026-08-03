"""`cli` — Presentation (TUI).

Owning RFC: RFC-0001 §5 (Presentation); interface per RFC-0015
    (future).
Responsibilities: render conversation and state; present evidence and
    proposals legibly; collect approvals, refusals, and input; expose
    the audit log and context view on demand.
Forbidden responsibilities: risk tone is presentation only, never policy
    (RFC-0001 §5); never classifies, executes, or holds secrets.
Layer 7 (blueprint §4.1). Imports: core, audit, context, schema.
"""
