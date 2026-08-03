"""Sanctioned Action runner.

Owner: RFC-0002 §2.8 (I-1, I-11).
Responsibility: run one approved Action under a valid,
    unexpired, state-consistent token.
Forbidden responsibility: never starts without approval (I-1);
    no untrusted text interpolated (I-5).
"""
