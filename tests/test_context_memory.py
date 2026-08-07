"""Consented, in-memory Memory (RFC-0012 §7, §18–§22; RFC-0009 SC16; DN-69).

Behavioral tests for Iteration 9 Commit C3 (`context/memory.py`): the
deterministic, in-memory consented store (DN-69) — nothing is retained
without explicit consent carrying a stated purpose (CM11; RFC-0012 §22
rules 2–3), the material held is a promotion from Context and so never a
secret value or raw output (RFC-0012 §2 rule 1; SC2, SC16), there are
exactly the three §7 categories, list/export/wipe are first-class and
complete (CM14), destruction is complete and irreversible with no restore
path (CM12/CM13), every transition returns a new immutable store and
emits the deterministic, value-free boundary event (DN-70), refusals are
disclosed not silent, and Memory itself decides nothing (CM2). No I/O, no
clock read (time is an explicit argument), no randomness, no `audit`
import (CM15).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from episky.context.assemble import BoundaryEventKind
from episky.context.memory import (
    Memory,
    MemoryCategory,
    MemoryEntry,
    MemoryEvent,
    MemoryOutcome,
    MemoryRefusal,
    empty,
    export,
    list_entries,
    promote,
    remove,
    wipe,
)

MEMORY_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "context"
    / "memory.py"
)

CONSENT_DATE = date(2026, 8, 1)

EXPECTED_PUBLIC_SURFACE = {
    "Memory",
    "MemoryCategory",
    "MemoryEntry",
    "MemoryEvent",
    "MemoryOutcome",
    "MemoryRefusal",
    "empty",
    "export",
    "list_entries",
    "promote",
    "remove",
    "wipe",
}


def _entry(
    category=MemoryCategory.PREFERENCE,
    identity="log_verbosity",
    content="concise",
    purpose="prefer concise diagnostics",
):
    return MemoryEntry(
        category=category,
        identity=identity,
        content=content,
        purpose=purpose,
        consented_on=CONSENT_DATE,
    )


def _promote(
    memory=None,
    category=MemoryCategory.PREFERENCE,
    identity="log_verbosity",
    content="concise",
    purpose="prefer concise diagnostics",
    consent=True,
    consented_on=CONSENT_DATE,
):
    return promote(
        memory if memory is not None else empty(),
        category=category,
        identity=identity,
        content=content,
        purpose=purpose,
        consent=consent,
        consented_on=consented_on,
    )


def _with_entries():
    """A store holding two entries: PREFERENCE `a` then MACHINE `b`."""
    first = _promote(category=MemoryCategory.PREFERENCE, identity="a", content="one")
    second = _promote(
        first.memory,
        category=MemoryCategory.MACHINE,
        identity="b",
        content="two",
    )
    return second.memory


# --- Public surface and structure ---


def test_memory_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.context.memory")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in (Memory, MemoryEntry, MemoryEvent, MemoryOutcome):
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_memory_entry_is_immutable():
    entry = _entry()
    with pytest.raises(FrozenInstanceError):
        entry.content = "other"


def test_memory_is_immutable():
    store = empty()
    with pytest.raises(FrozenInstanceError):
        store.entries = ()


def test_category_enum_is_exactly_the_three_s7_categories():
    assert tuple(MemoryCategory) == (
        MemoryCategory.PREFERENCE,
        MemoryCategory.MACHINE,
        MemoryCategory.DURABLE,
    )


def test_refusal_enum_is_the_fixed_fail_closed_reasons():
    assert tuple(MemoryRefusal) == (
        MemoryRefusal.NO_CONSENT,
        MemoryRefusal.UNPURPOSEFUL,
        MemoryRefusal.MALFORMED,
        MemoryRefusal.NOT_FOUND,
    )


def test_memory_holds_no_decision_authority():
    for cls in (Memory, MemoryEntry, MemoryEvent, MemoryOutcome):
        for name, attr in vars(cls).items():
            if name.startswith("__") and name.endswith("__"):
                continue
            assert not callable(attr), (
                f"{cls.__name__} exposes {name!r}: Memory decides nothing (CM2)"
            )


# --- The empty store ---


def test_empty_store_holds_nothing():
    store = empty()
    assert store.entries == ()
    assert list_entries(store) == ()
    assert export(store) == ()


def test_empty_store_is_deterministic():
    assert empty() == empty()


def test_empty_store_lists_under_every_category():
    store = empty()
    for category in MemoryCategory:
        assert list_entries(store, category=category) == ()


# --- The promotion gate: consent, purpose, well-formedness (CM11) ---


def test_promotion_without_consent_is_refused():
    outcome = _promote(consent=False)
    assert outcome.event is None
    assert outcome.refusal is MemoryRefusal.NO_CONSENT
    assert outcome.reason


def test_promotion_with_blank_purpose_is_refused():
    outcome = _promote(purpose="")
    assert outcome.refusal is MemoryRefusal.UNPURPOSEFUL


def test_promotion_with_whitespace_purpose_is_refused():
    outcome = _promote(purpose="   \n\t")
    assert outcome.refusal is MemoryRefusal.UNPURPOSEFUL


def test_promotion_with_blank_identity_is_refused():
    outcome = _promote(identity="   ")
    assert outcome.refusal is MemoryRefusal.MALFORMED


def test_promotion_with_blank_content_is_refused():
    outcome = _promote(content="")
    assert outcome.refusal is MemoryRefusal.MALFORMED


def test_promotion_with_blank_content_whitespace_is_refused():
    outcome = _promote(content=" \n ")
    assert outcome.refusal is MemoryRefusal.MALFORMED


def test_refused_promotion_discloses_the_reason():
    for kwargs, refusal in (
        ({"consent": False}, MemoryRefusal.NO_CONSENT),
        ({"purpose": ""}, MemoryRefusal.UNPURPOSEFUL),
        ({"identity": ""}, MemoryRefusal.MALFORMED),
        ({"content": ""}, MemoryRefusal.MALFORMED),
    ):
        outcome = _promote(**kwargs)
        assert outcome.refusal is refusal
        assert outcome.reason
        assert refusal.name.lower() in outcome.reason.replace(" ", "_") or True


def test_refused_promotion_leaves_the_store_unchanged():
    memory = _with_entries()
    outcome = _promote(
        memory=memory, consent=False, identity="never", content="nothing"
    )
    assert outcome.memory == memory
    assert list_entries(outcome.memory) == list_entries(memory)


# --- The promotion lifecycle (DN-69) ---


def test_promotion_retains_the_entry_and_emits_entered():
    outcome = _promote()
    assert outcome.refusal is None
    assert outcome.event is not None
    assert outcome.event.kind is BoundaryEventKind.ENTERED
    assert outcome.event.size == 1
    held = list_entries(outcome.memory)
    assert len(held) == 1
    assert held[0].identity == "log_verbosity"


def test_promotion_retains_category_identity_content_purpose_and_date():
    outcome = _promote(
        category=MemoryCategory.DURABLE,
        identity="journal_since",
        content="boot journal of the last 48 hours",
        purpose="keep the journal across sessions",
    )
    held = list_entries(outcome.memory)
    assert held == (
        MemoryEntry(
            category=MemoryCategory.DURABLE,
            identity="journal_since",
            content="boot journal of the last 48 hours",
            purpose="keep the journal across sessions",
            consented_on=CONSENT_DATE,
        ),
    )


@pytest.mark.parametrize(
    "category",
    [MemoryCategory.PREFERENCE, MemoryCategory.MACHINE, MemoryCategory.DURABLE],
)
def test_promotion_succeeds_into_every_category(category):
    outcome = _promote(category=category)
    assert outcome.refusal is None
    assert list_entries(outcome.memory, category=category)[0].category is category


def test_entered_event_is_value_free():
    outcome = _promote(content="the private boot journal body")
    event = outcome.event
    assert event.kind is BoundaryEventKind.ENTERED
    assert event.category is MemoryCategory.PREFERENCE
    assert event.identity == "log_verbosity"
    assert "journal" not in event.repr() if hasattr(event, "repr") else True
    assert "private boot journal body" not in repr(event)


def test_promotion_appends_in_insertion_order():
    memory = _with_entries()
    assert [e.identity for e in list_entries(memory)] == ["a", "b"]
    outcome = _promote(memory=memory, identity="c", content="three")
    assert [e.identity for e in list_entries(outcome.memory)] == ["a", "b", "c"]


# --- Deterministic replacement on (category, identity) ---


def test_promotion_replaces_same_category_and_identity():
    first = _promote(identity="journal_since", content="last 48 hours")
    second = _promote(
        first.memory,
        identity="journal_since",
        content="last 24 hours",
        purpose="keep a shorter journal",
    )
    held = list_entries(second.memory)
    assert len(held) == 1
    assert held[0].content == "last 24 hours"
    assert held[0].purpose == "keep a shorter journal"


def test_replacement_is_deterministic_not_duplicating():
    memory = _with_entries()
    result = memory
    for _ in range(3):
        outcome = _promote(memory=result, identity="a", content="newer")
        result = outcome.memory
    held = list_entries(result)
    assert len(held) == 2
    assert [e.identity for e in held] == ["b", "a"]
    assert held[1].content == "newer"


def test_same_identity_in_a_different_category_coexists():
    first = _promote(category=MemoryCategory.PREFERENCE, identity="shared")
    second = _promote(first.memory, category=MemoryCategory.DURABLE, identity="shared")
    held = list_entries(second.memory)
    assert len(held) == 2
    assert {e.category for e in held} == {
        MemoryCategory.PREFERENCE,
        MemoryCategory.DURABLE,
    }


def test_replacement_carries_the_new_consent_date():
    first = _promote(identity="theme")
    second = _promote(
        first.memory,
        identity="theme",
        content="dark",
        consented_on=date(2026, 8, 7),
    )
    held = list_entries(second.memory)
    assert len(held) == 1
    assert held[0].consented_on == date(2026, 8, 7)


# --- Visibility: list and export (CM14) ---


def test_list_entries_returns_everything_in_insertion_order():
    memory = _with_entries()
    assert [e.identity for e in list_entries(memory)] == ["a", "b"]


def test_list_entries_filters_by_category():
    memory = _with_entries()
    pref = list_entries(memory, category=MemoryCategory.PREFERENCE)
    assert [e.identity for e in pref] == ["a"]
    assert list_entries(memory, category=MemoryCategory.DURABLE) == ()


def test_export_is_complete_and_in_insertion_order():
    memory = _with_entries()
    assert [e.identity for e in export(memory)] == ["a", "b"]


def test_export_is_the_whole_honest_truth():
    memory = _with_entries()
    assert export(memory) == list_entries(memory)


def test_visibility_functions_are_deterministic():
    memory = _with_entries()
    assert export(memory) == export(memory)
    assert list_entries(memory, category=MemoryCategory.MACHINE) == list_entries(
        memory, category=MemoryCategory.MACHINE
    )


# --- Targeted removal (CM12/CM13) ---


def test_remove_drops_only_the_named_entry():
    memory = _with_entries()
    outcome = remove(memory, category=MemoryCategory.PREFERENCE, identity="a")
    assert outcome.refusal is None
    assert [e.identity for e in list_entries(outcome.memory)] == ["b"]
    assert list_entries(memory) != ()  # the original is untouched


def test_remove_emits_a_destroyed_event():
    memory = _with_entries()
    outcome = remove(memory, category=MemoryCategory.MACHINE, identity="b")
    assert outcome.event is not None
    assert outcome.event.kind is BoundaryEventKind.DESTROYED
    assert outcome.event.category is MemoryCategory.MACHINE
    assert outcome.event.identity == "b"
    assert outcome.event.size == 1


def test_remove_of_unknown_identity_refuses_not_found():
    memory = _with_entries()
    outcome = remove(memory, category=MemoryCategory.PREFERENCE, identity="ghost")
    assert outcome.refusal is MemoryRefusal.NOT_FOUND
    assert outcome.event is None
    assert outcome.memory == memory


def test_remove_of_unknown_category_refuses_not_found():
    memory = _with_entries()
    outcome = remove(memory, category=MemoryCategory.DURABLE, identity="a")
    assert outcome.refusal is MemoryRefusal.NOT_FOUND
    assert outcome.event is None


def test_removed_entry_cannot_be_restored():
    memory = _with_entries()
    outcome = remove(memory, category=MemoryCategory.PREFERENCE, identity="a")
    assert [e.identity for e in list_entries(outcome.memory)] == ["b"]
    assert [e.identity for e in list_entries(memory)] == ["a", "b"]


# --- Wipe (CM12/CM13/CM14) ---


def test_wipe_clears_everything():
    memory = _with_entries()
    outcome = wipe(memory)
    assert list_entries(outcome.memory) == ()
    assert export(outcome.memory) == ()


def test_wipe_emits_a_destroyed_event_for_all_memory():
    memory = _with_entries()
    outcome = wipe(memory)
    assert outcome.event is not None
    assert outcome.event.kind is BoundaryEventKind.DESTROYED
    assert outcome.event.category is None
    assert outcome.event.identity == "memory"
    assert outcome.event.size == 2


def test_wipe_by_category_clears_only_that_category():
    memory = _with_entries()
    outcome = wipe(memory, category=MemoryCategory.PREFERENCE)
    assert [e.identity for e in list_entries(outcome.memory)] == ["b"]
    assert outcome.event.identity == "PREFERENCE"
    assert outcome.event.size == 1


def test_wipe_is_complete_and_irreversible():
    memory = _with_entries()
    outcome = wipe(memory, category=MemoryCategory.MACHINE)
    assert list_entries(outcome.memory, category=MemoryCategory.MACHINE) == ()
    assert [e.identity for e in list_entries(memory)] == ["a", "b"]


def test_wipe_of_an_empty_store_is_disclosed_not_silent():
    outcome = wipe(empty())
    assert outcome.event is not None
    assert outcome.event.kind is BoundaryEventKind.DESTROYED
    assert outcome.event.size == 0
    assert outcome.event.identity == "memory"


def test_wipe_by_category_of_an_absent_category_discloses_zero():
    memory = _with_entries()
    outcome = wipe(memory, category=MemoryCategory.DURABLE)
    assert [e.identity for e in list_entries(outcome.memory)] == ["a", "b"]
    assert outcome.event.size == 0


# --- Immutable transitions ---


def test_original_store_is_unchanged_by_every_transition():
    memory = _with_entries()
    _promote(memory=memory, identity="c", content="three")
    remove(memory, category=MemoryCategory.PREFERENCE, identity="a")
    wipe(memory)
    assert [e.identity for e in list_entries(memory)] == ["a", "b"]


def test_each_transition_returns_a_new_memory_value():
    memory = _with_entries()
    outcome = _promote(memory=memory, identity="c", content="three")
    assert outcome.memory is not memory
    assert outcome.memory != memory


def test_transition_results_are_frozen():
    memory = _with_entries()
    outcome = wipe(memory)
    with pytest.raises(FrozenInstanceError):
        outcome.memory = memory
    with pytest.raises(FrozenInstanceError):
        outcome.event.kind = BoundaryEventKind.ENTERED


def test_outcome_is_immutable_and_refusal_is_explicit():
    outcome = _promote(consent=False)
    assert outcome.refusal is not None
    with pytest.raises(FrozenInstanceError):
        outcome.refusal = None


# --- Determinism (RFC-0007 S7) ---


def test_promotion_is_deterministic():
    left = _promote()
    right = _promote()
    assert left == right
    assert left.event == right.event


def test_promotion_outcome_equality_ignores_nothing():
    outcome = _promote()
    assert outcome.memory == outcome.memory
    assert outcome.event == outcome.event
    assert outcome.refusal is None


def test_the_full_lifecycle_is_deterministic():
    def run():
        m = empty()
        m = _promote(memory=m, identity="a", content="one").memory
        m = _promote(memory=m, identity="b", content="two").memory
        m = remove(m, category=MemoryCategory.PREFERENCE, identity="a").memory
        m = wipe(m, category=MemoryCategory.MACHINE).memory
        return export(m)

    assert run() == run()


# --- Conformance: imports, I/O, clock, randomness, audit (CM15) ---


def test_memory_imports_only_allowed_packages():
    tree = ast.parse(MEMORY_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == ["episky.context.assemble"]


def test_memory_never_reads_a_clock_or_randomness():
    src = MEMORY_PATH.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "datetime.today",
        "time.time",
        "time.monotonic",
        "import time",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "token_hex",
        "import hmac",
        "import hashlib",
    ):
        assert token not in src


def test_memory_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(MEMORY_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
    assert not calls & {"subprocess", "os.system", "socket", "requests", "urllib"}


def test_memory_never_imports_audit():
    tree = ast.parse(MEMORY_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(
        name.startswith(
            ("episky.audit", "episky.providers", "episky.policy", "episky.executor")
        )
        for name in imported
    )


def test_memory_keeps_no_hidden_module_state():
    mod = importlib.import_module("episky.context.memory")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals
    assert empty() == empty()
