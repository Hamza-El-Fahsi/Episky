"""Append-only durable store.

Owner: RFC-0013 §1, §11, §21.
Responsibility: append-only durable store; a failed write blocks
    the consequence and is disclosed (AU8).
Forbidden responsibility: never overwritten; never written after
    the consequence.
"""
