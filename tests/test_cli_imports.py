"""Layer-7 import conformance (blueprint §4.1/§4.2; design-review §14 C4).

Iteration 12 Commit C4 conformance oracle. `cli` is the top presentation
layer: it may import only `core`, `audit`, `context`, and `schema` — the
four packages the blueprint §4.1 edge table allows (``ALLOWED["cli"]``) —
and never an authority-bearing or implementation package (policy, executor,
factlayer, providers, skills, secrets, collectors, trust, systemmodel,
verification), which are reached only through injected seams, never by
import. The stdlib surface is the closed types-only allowlist (no clock, no
network, no filesystem, no subprocess, no randomness — DN-55, DN-97,
RFC-0007 S7). Source-level I/O tokens are scanned so a single accidental
`import os` cannot slip through the edge check. Deterministic (RFC-0007 S7),
I/O-free (DN-103).
"""

import pathlib

import pytest

from tests.test_core_imports import (
    _IO_TOKEN_RE,
    IO_TOKENS,
    _episky_top_packages,
    _import_names,
    _top_package,
)
from tests.test_dependency_rules import ALLOWED

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
CLI_DIR = PACKAGE_ROOT / "cli"

#: The intra-episky packages `cli` may import (blueprint §4.1 §4.3; DN-99).
#: The comparison is made on the top-level package name.
SANCTIONED_INTRA = frozenset(
    {"episky.cli", "episky.core", "episky.audit", "episky.context", "episky.schema"}
)

#: The packages `cli` must never name: the authority-bearing and
#: implementation packages, reached only through injected seams (DN-99).
FORBIDDEN_INTRA = frozenset(
    {
        "episky.policy",
        "episky.executor",
        "episky.factlayer",
        "episky.providers",
        "episky.skills",
        "episky.secrets",
        "episky.collectors",
        "episky.trust",
        "episky.systemmodel",
        "episky.verification",
    }
)

#: The closed stdlib allowlist: pure types only, no I/O, no clock, no
#: randomness (DN-55; RFC-0007 S7).
SANCTIONED_STDLIB = frozenset(
    {
        "__future__",
        "collections",
        "collections.abc",
        "dataclasses",
        "datetime",
        "enum",
        "types",
        "typing",
    }
)


def _cli_files():
    return sorted(CLI_DIR.glob("*.py"))


# --- `cli` may import only its sanctioned intra-episky set ----------------


@pytest.mark.parametrize("path", _cli_files())
def test_cli_imports_only_sanctioned_intra_episky_packages(path):
    for module in _import_names(path.read_text(encoding="utf-8")):
        if not module.startswith("episky"):
            continue
        assert _top_package(module) in SANCTIONED_INTRA, (
            f"{path.name} imports {module}, outside the sanctioned intra-episky "
            "set (blueprint §4.1; DN-99)"
        )


def test_cli_import_surface_is_within_the_documented_set():
    observed = set()
    for path in _cli_files():
        observed |= _episky_top_packages(path.read_text(encoding="utf-8"))
    assert observed <= SANCTIONED_INTRA
    # The CLI actually reaches core, audit, and context today; schema is
    # sanctioned but unused. Assert the consumed set stays honest.
    assert observed == {"episky.core", "episky.audit", "episky.context"}


@pytest.mark.parametrize("path", _cli_files())
def test_cli_never_imports_an_authority_or_implementation_package(path):
    for module in _import_names(path.read_text(encoding="utf-8")):
        if not module.startswith("episky"):
            continue
        assert module not in FORBIDDEN_INTRA, (
            f"{path.name} imports {module}: authority/implementation packages "
            "are reached only through injected seams (DN-99)"
        )


# --- `cli` may import only the closed stdlib allowlist ---------------------


@pytest.mark.parametrize("path", _cli_files())
def test_cli_stdlib_imports_are_on_the_closed_allowlist(path):
    for module in _import_names(path.read_text(encoding="utf-8")):
        if module.startswith("episky"):
            continue
        assert module in SANCTIONED_STDLIB, (
            f"{path.name} imports stdlib {module!r}, outside the closed "
            "allowlist (no I/O, no clock, no randomness; DN-55, DN-97)"
        )


# --- source-level I/O / clock / randomness / network ban ------------------


@pytest.mark.parametrize("path", _cli_files())
def test_cli_source_contains_no_io_clock_random_or_network_tokens(path):
    src = path.read_text(encoding="utf-8")
    for module in _import_names(src):
        if module.startswith("episky"):
            continue
        assert module not in IO_TOKENS, (
            f"{path.name} imports banned stdlib module {module!r}"
        )
    assert not _IO_TOKEN_RE.search(src), (
        f"{path.name} contains a banned I/O/clock/random/network call token"
    )


# --- the allowed edge from the dependency rules stays consistent -----------

ALL_EPISKY_PACKAGES = frozenset(ALLOWED)


def test_sanctioned_cli_intra_packages_exist_and_are_allowed_by_blueprint():
    for pkg in ("core", "audit", "context", "schema"):
        assert pkg in ALL_EPISKY_PACKAGES
        assert pkg in ALLOWED["cli"], f"blueprint §4.1 must allow cli -> {pkg}"


def test_forbidden_cli_intra_packages_are_never_in_the_sanctioned_set():
    for pkg in FORBIDDEN_INTRA:
        assert pkg not in SANCTIONED_INTRA
