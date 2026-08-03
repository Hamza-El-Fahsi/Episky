"""Deterministic Compare.

Owner: RFC-0006 §6 (V3, V7, V10).
Responsibility: compare Facts against declared Postconditions;
    deterministic; Postconditions fixed before Compare (V10);
    contradiction wins (V7).
Forbidden responsibility: never skips (V14), never stale (V4).
"""
