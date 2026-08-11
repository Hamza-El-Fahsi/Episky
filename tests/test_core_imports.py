"""Layer-6 import conformance (blueprint §4.1/§4.2; design-review §13).

Iteration 11 Commit C5 conformance oracle. `core` is the highest internal
layer and the single authority-router: it may import only its own modules,
`schema` (data types), and `factlayer` (Fact/provenance types) — never the
authority-bearing or implementation packages (audit, policy, executor,
verification, providers, skills, context, secrets, collectors, trust,
systemmodel) and never `cli`. Those are the injected responders' homes
(DN-94), and `core` routes to them only through the `Loop` seams, so no
`core` file may name them. Conversely, only `cli` may import `core`: `core`
is consumed by the TUI alone; every other package is a dependency of `core`,
not a consumer. The stdlib surface is a closed allowlist — types only
(`collections.abc`, `dataclasses`, `datetime`, `enum`, `types`, `typing`,
`__future__`); no clock, no network, no filesystem, no subprocess, no
randomness (DN-55, DN-94, RFC-0007 S7). Source-level I/O tokens are scanned
so a single accidental `import os` cannot slip through the edge check.
Deterministic (RFC-0007 S7), I/O-free (DN-94).
"""

import ast
import pathlib
import re

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
CORE_DIR = PACKAGE_ROOT / "core"

#: The intra-episky packages `core` may import (design-review §13; DN-94).
#: ``replan.py`` reaches ``schema.fact`` and ``factlayer.provenance`` as the
#: submodules the top-level packages already own, so the comparison is made on
#: the top-level package name.
SANCTIONED_INTRA = frozenset({"episky.core", "episky.schema", "episky.factlayer"})

#: The packages `core` must never name: the injected responders' homes and
#: the presentation layer. `core` routes to these only through `Loop` seams.
FORBIDDEN_INTRA = frozenset(
    {
        "episky.audit",
        "episky.policy",
        "episky.executor",
        "episky.verification",
        "episky.providers",
        "episky.skills",
        "episky.context",
        "episky.secrets",
        "episky.collectors",
        "episky.trust",
        "episky.systemmodel",
        "episky.cli",
    }
)

#: The closed stdlib allowlist: pure types only, no I/O, no clock, no
#: randomness. `datetime` appears only for the pure `datetime`/`timedelta`
#: types used by replan/recovery; the clock-read tokens are banned separately.
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

#: Source tokens that would betray I/O, a clock, randomness, or network use
#: (DN-55, DN-94; RFC-0007 S7). The import forms are resolved structurally
#: (AST, below); the call forms are matched on word boundaries so a name like
#: ``reopen(`` cannot trip the ``open(`` check.
IO_TOKENS = (
    "import os",
    "import sys",
    "import io",
    "import socket",
    "import subprocess",
    "import time",
    "import random",
    "import uuid",
    "import hmac",
    "import hashlib",
    "import secrets",
    "import json",
    "import requests",
    "import urllib",
    "import pathlib",
    "import threading",
    "import multiprocessing",
    "import asyncio",
)
IO_TOKEN_PATTERNS = (
    r"\btime\.time\(",
    r"\btime\.monotonic\(",
    r"\bperf_counter\(",
    r"\bdatetime\.now\(",
    r"\bdatetime\.utcnow\(",
    r"\butcnow\(",
    r"\brandom\.",
    r"\bos\.urandom\(",
    r"\buuid4\(",
    r"\bsecrets\.token",
    r"\bopen\(",
    r"\bprint\(",
    r"\b\.run\(",
    r"\bsocket\.",
)
_IO_TOKEN_RE = re.compile("|".join(IO_TOKEN_PATTERNS))


def _core_files():
    return sorted(CORE_DIR.glob("*.py"))


def _import_names(source: str) -> set[str]:
    """The full module names imported by ``source`` (Import and ImportFrom)."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _top_package(module: str) -> str:
    """The top-level episky package of a module name, or the module itself.

    ``episky.core.state_machine`` → ``episky.core``; ``episky.schema.fact`` →
    ``episky.schema``; a bare stdlib module maps to itself.
    """
    if module == "episky" or module.startswith("episky."):
        parts = module.split(".")
        return parts[0] + "." + parts[1]
    return module


def _episky_top_packages(source: str) -> set[str]:
    """The top-level episky packages imported by ``source``."""
    return {
        _top_package(m)
        for m in _import_names(source)
        if m == "episky" or m.startswith("episky.")
    }


# --- `core` may import only its sanctioned intra-episky set ---------------


@pytest.mark.parametrize("path", sorted(CORE_DIR.glob("*.py")))
def test_core_imports_only_sanctioned_intra_episky_packages(path):
    for module in _import_names(path.read_text(encoding="utf-8")):
        if not module.startswith("episky"):
            continue
        assert _top_package(module) in SANCTIONED_INTRA, (
            f"{path.name} imports {module}, outside the sanctioned intra-episky "
            "set (design-review §13; DN-94)"
        )


def test_core_import_surface_is_exactly_the_documented_set():
    observed = set()
    for path in _core_files():
        observed |= _episky_top_packages(path.read_text(encoding="utf-8"))
    assert observed == SANCTIONED_INTRA


@pytest.mark.parametrize("path", sorted(CORE_DIR.glob("*.py")))
def test_core_never_imports_an_authority_or_implementation_package(path):
    for module in _import_names(path.read_text(encoding="utf-8")):
        if not module.startswith("episky"):
            continue
        assert module not in FORBIDDEN_INTRA, (
            f"{path.name} imports {module}: authority/implementation packages "
            "are reached only through the injected Loop seams (DN-94)"
        )


# --- `core` may import only the closed stdlib allowlist -------------------


@pytest.mark.parametrize("path", sorted(CORE_DIR.glob("*.py")))
def test_core_stdlib_imports_are_on_the_closed_allowlist(path):
    for module in _import_names(path.read_text(encoding="utf-8")):
        if module.startswith("episky"):
            continue
        assert module in SANCTIONED_STDLIB, (
            f"{path.name} imports stdlib {module!r}, outside the closed "
            "allowlist (no I/O, no clock, no randomness; DN-55, DN-94)"
        )


# --- source-level I/O / clock / randomness / network ban ------------------


@pytest.mark.parametrize("path", sorted(CORE_DIR.glob("*.py")))
def test_core_source_contains_no_io_clock_random_or_network_tokens(path):
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


# --- only `cli` imports `core` ---------------------------------------------


def _episky_modules():
    for path in PACKAGE_ROOT.rglob("*.py"):
        if path.parts[-2] == "episky":
            continue
        if path.parts[-2] == "core":
            continue
        yield path


@pytest.mark.parametrize("path", sorted(_episky_modules()))
def test_only_cli_imports_core(path):
    source_pkg = path.parts[-2]
    if source_pkg == "cli":
        return  # cli is the sole sanctioned consumer of core
    for module in _import_names(path.read_text(encoding="utf-8")):
        assert not (module == "episky.core" or module.startswith("episky.core.")), (
            f"{path.relative_to(PACKAGE_ROOT)} imports episky.core; only the "
            "TUI (cli) may consume core (blueprint §4.1; design-review §13)"
        )


# --- the allowed edge from the dependency rules stays consistent -----------

#: Blueprint §4.1 ALLOWED for `core` names every subpackage; the conformance
#: here narrows that to the three packages `core` actually and lawfully
#: imports (DN-94). This test keeps the two views aligned: anything the
#: §4.1 edge table allows for `core` must still exist as a package, and the
#: sanctioned set must be a subset of it.
from tests.test_dependency_rules import ALLOWED  # noqa: E402

ALL_EPISKY_PACKAGES = frozenset(ALLOWED)


def test_sanctioned_intra_packages_exist_and_are_allowed_by_blueprint():
    for pkg in ("core", "schema", "factlayer"):
        assert pkg in ALL_EPISKY_PACKAGES
    for pkg in ("schema", "factlayer"):
        assert pkg in ALLOWED["core"], f"blueprint §4.1 must allow core -> {pkg}"


def test_forbidden_intra_packages_are_never_in_the_sanctioned_set():
    for pkg in FORBIDDEN_INTRA:
        assert pkg not in SANCTIONED_INTRA
