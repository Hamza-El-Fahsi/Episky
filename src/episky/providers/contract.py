"""Structured output validation.

Owner: RFC-0010 §4, §8.
Responsibility: validate the finite structured outputs; degrade,
    never crash (PR11).
Forbidden responsibility: output is never a Fact (F6); never
    accepted as instructions.
"""
