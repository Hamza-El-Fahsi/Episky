"""Fact storage, status, invalidation.

Owner: RFC-0005 §4, §7.
Responsibility: Fact storage, status, and invalidation; failed
    collection yields Unknown/Unavailable status (F11, §4).
Forbidden responsibility: Facts never carry permissions (F2),
    never execute (F3).
"""
