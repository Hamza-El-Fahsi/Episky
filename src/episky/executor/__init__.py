"""`executor` — Action Execution.

Owning RFC: RFC-0004 §4.9 (authority); RFC-0002 §2.8 (state);
    RFC-0001 §8.6.
Responsibilities: run the one approved Action under a valid,
    unexpired, state-consistent token; scoping, timeouts, output
    capture; explicit scoped elevation.
Forbidden responsibilities: may decide only how, never what (RFC-0004
    §4.9); never verifies its own work (V1).
Layer 4 (blueprint §4.1). Imports: schema, audit, secrets.
"""
