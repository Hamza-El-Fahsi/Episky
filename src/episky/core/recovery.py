"""Failure ordering.

Owner: RFC-0002 §10.
Responsibility: recovery ordering — determinism, then disclosure,
    then decision, then action.
Forbidden responsibility: no recovery before disclosure of the
    failure (I-8).
"""
