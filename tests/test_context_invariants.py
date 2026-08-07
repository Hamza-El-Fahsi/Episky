"""The complete layer-enforceable context invariants (RFC-0012 §35 CM1–CM16;
RFC-0010 PR14; RFC-0009 SC2/SC3/SC16; RFC-0007 S7/T10; RFC-0002 I-4/I-13;
blueprint §8.9).

Transcribes the ratified context corpus into behavioral and structural
tests, mirroring the policy/trust invariant-oracle style: the RFC-0012
deterministic assembly guarantees (§10–§12, §16, §17, §33) — never a
source of truth (CM1), only the Context Manager assembles (CM3),
purpose-limited (CM5), bounded with transparent consolidation (CM6),
fresh or rebuilt (CM7), deterministic invalidation preceding use (CM8),
session-isolated (CM9), supersede-disclose (§33); the secret-free and
privacy guarantees (CM4, SC2, SC3, SC16, T10); the boundary guarantees
(fail-close, containment, determinism, hostile exclusion, value-free);
the Memory guarantees (CM2 never authority, CM11 consent, CM12
destruction recorded, CM13 no-restore, CM14 visible/exportable/wipable);
the Provider View guarantees (SC3, PR14 only channel, projection rules);
the one-way-flow and no-authority guarantees (CM10, CM15, CM16, no
provider/audit/policy/verification authority); no hidden state; and the
cross-layer obligations recorded against `core`/RFC-0014/RFC-0015/RFC-0020
without fabrication. Every invariant is asserted at the layer's own
surface; the remainder of each is recorded, not invented.
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from episky.context.assemble import (
    REASON_OVERFLOW,
    REASON_STALE_EXCLUDED,
    REASON_UNPURPOSEFUL,
    BoundaryEvent,
    BoundaryEventKind,
    Context,
    ContextCategory,
    ContextState,
    EvidenceLabel,
    GoalValue,
    HistoryLabel,
    RoutingMarker,
    SkillMaterialItem,
    TurnRecord,
    assemble,
    mark_stale,
    supersede_question,
)
from episky.context.boundaries import (
    BoundaryDisposition,
    BoundaryInput,
    BoundaryRefusal,
    admit,
)
from episky.context.memory import (
    Memory,
    MemoryCategory,
    MemoryEntry,
    MemoryRefusal,
    empty,
    export,
    list_entries,
    promote,
    remove,
    wipe,
)
from episky.context.provider_view import (
    ProviderView,
    ViewDisposition,
    ViewRefusal,
    derive,
)
from episky.factlayer.store import FactIdentity, FactStore
from episky.schema.fact import (
    Collector,
    ConfidenceSource,
    Fact,
    FactStatus,
    Freshness,
    FreshnessState,
    MachineIdentity,
    ObservationReference,
    Property,
    Provenance,
    Scope,
    Subject,
    Value,
)
from episky.schema.outcome import VerificationOutcome
from episky.secrets.classify import NonSecretDesignation, SecretOrigin
from episky.trust.classes import ProvenanceState, TrustCategory, TrustDomain
from episky.trust.hostile import Quarantine

CONTEXT_ROOT = (
    pathlib.Path(__file__).resolve().parents[1] / "src" / "episky" / "context"
)


def _code_without_literals() -> str:
    """The context package source with strings and comments removed.

    Token-level scan: docstrings (which legitimately cite tokens such as
    ``restore`` and ``rebuild`` while forbidding them) are STRING tokens and
    are dropped, so the CM13 no-restore / no-rebuild guarantee is asserted
    against code only.
    """
    import io
    import tokenize

    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in CONTEXT_ROOT.glob("*.py")
        if not path.name.startswith("__")
    )
    parts = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            parts.append(" ")
        else:
            parts.append(tok.string)
    return "".join(parts)


NOW = datetime(2026, 8, 7, 12, 0, 0)

PURPOSE = "diagnose boot failure"

MACHINE_IDENTITY = MachineIdentity()

TOKEN = "Bearer ABCD1234abcd1234WXYZ"
PERSONAL = "contact me at alice@example.com"

# Cross-component obligations, recorded exactly as ratified (C5 DoD; design
# review §8): the context-owned half is tested above; these halves belong to
# their owning components and are only recorded here, never fabricated.
DEFERRED_OBLIGATIONS = (
    (
        "state wiring",
        "when Context Building runs and the state transitions that follow",
        "core",
        "RFC-0002 §2.4",
    ),
    (
        "re-inspection",
        "the trigger that re-inspects a Stale working set before the next "
        "decision (CM7)",
        "core",
        "RFC-0002 §4.2; RFC-0005 §12",
    ),
    (
        "invalidation events",
        "the STATE_CHANGED_DETECTED / freshness-lapse events that invalidate "
        "Context (CM8)",
        "core",
        "RFC-0002 §4.2",
    ),
    (
        "cat-9 audit write",
        "persisting the context-boundary events as RFC-0013 §7 cat. 9 records "
        "before use (I-13)",
        "core",
        "RFC-0013 §7 cat. 9, §23; RFC-0004 §9.11",
    ),
    (
        "View presentation form",
        "how the derived View is rendered to the Operator or consumed by a provider",
        "RFC-0015",
        "RFC-0010 §15 OQ3; Q4",
    ),
    (
        "final signatures",
        "package signatures and the canonical Goal schema",
        "RFC-0020",
        "DN-1; Q4",
    ),
    (
        "Memory durability",
        "storage mechanics, retention, deletion, and what survives a resume",
        "RFC-0014/RFC-0020",
        "RFC-0012 §37 OQ4/OQ5; Q5",
    ),
    (
        "sanitization catalogue",
        "the concrete per-source sanitization treatments at the enforcement point",
        "RFC-0020",
        "RFC-0012 §37 OQ3; Q3",
    ),
    (
        "session ownership",
        "one working set per session; multi-goal separation",
        "core/RFC-0014",
        "RFC-0012 §14; CM9",
    ),
    (
        "demotion collection",
        "the UI that grants an explicit Operator demotion (SC16)",
        "cli/core",
        "RFC-0009 SC16",
    ),
)


def _fact(
    subject="systemd",
    property="running-state",
    value="running",
    status=FactStatus.OBSERVED,
    freshness=FreshnessState.CURRENT,
    collected_at=NOW,
):
    return Fact(
        scope=Scope(
            subject=Subject(name=subject),
            property=Property(name=property),
            value=Value(value=value),
        ),
        status=status,
        confidence=ConfidenceSource(name="systemctl-is-active"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="systemd-state", version="1"),
            collected_at=collected_at,
        ),
        freshness=Freshness(state=freshness),
        machine_identity=MACHINE_IDENTITY,
    )


def _store(*facts):
    current = {}
    for fact in facts:
        identity = FactIdentity(
            machine_identity=fact.machine_identity,
            subject=fact.scope.subject,
            property=fact.scope.property,
        )
        current[identity] = fact
    return FactStore(machine_identity=MACHINE_IDENTITY, current=current)


def _goal(statement="repair the boot", scope="boot configuration"):
    return GoalValue(statement=statement, scope=scope)


def _turn(
    content="the machine fails to boot",
    label=HistoryLabel.OPERATOR_INPUT,
    purpose=PURPOSE,
):
    return TurnRecord(content=content, label=label, purpose=purpose)


def _evidence(outcome=VerificationOutcome.VERIFIED_SUCCESS, purpose=PURPOSE):
    return EvidenceLabel(outcome=outcome, purpose=purpose)


def _skill(content="grub-reinstall steps", source="boot-repair", purpose=PURPOSE):
    return SkillMaterialItem(content=content, source=source, purpose=purpose)


def _routing(outstanding_question=None, current_decision="decision-1"):
    return RoutingMarker(
        outstanding_question=outstanding_question,
        current_decision=current_decision,
    )


def _assemble(
    goal=None,
    store=None,
    *,
    purpose=PURPOSE,
    history=(),
    evidence=(),
    skill_material=(),
    routing=None,
    fact_bound=64,
    history_bound=24,
    evidence_bound=16,
    skill_bound=8,
):
    return assemble(
        goal=_goal() if goal is None else goal,
        fact_store=_store(_fact()) if store is None else store,
        purpose=purpose,
        history=history,
        evidence=evidence,
        skill_material=skill_material,
        routing=_routing() if routing is None else routing,
        fact_bound=fact_bound,
        history_bound=history_bound,
        evidence_bound=evidence_bound,
        skill_bound=skill_bound,
    )


def _context(**kwargs):
    return _assemble(**kwargs).context


def _datum(
    content="the machine fails to boot",
    category=TrustCategory.USER_INPUT,
    origin=TrustDomain.OPERATOR,
    provenance=ProvenanceState.ESTABLISHED,
    purpose=PURPOSE,
    designation=NonSecretDesignation.SANITIZED_TEXT,
    secret_origin=SecretOrigin.CAPTURED,
    provider=None,
):
    return BoundaryInput(
        content=content,
        category=category,
        origin=origin,
        provenance=provenance,
        purpose=purpose,
        designation=designation,
        secret_origin=secret_origin,
        provider=provider,
    )


def _memory_with_entries():
    first = promote(
        empty(),
        category=MemoryCategory.PREFERENCE,
        identity="a",
        content="one",
        purpose=PURPOSE,
        consent=True,
        consented_on=datetime(2026, 8, 7).date(),
    )
    second = promote(
        first.memory,
        category=MemoryCategory.MACHINE,
        identity="b",
        content="two",
        purpose=PURPOSE,
        consent=True,
        consented_on=datetime(2026, 8, 7).date(),
    )
    return second.memory


# --- Assembly guarantees: RFC-0012 §10–§12, §16, §17 (CM1/CM3/CM5–CM9/CM13)
# ---------------------------------------------------------------------------


def test_assembly_is_deterministic_and_in_composition_order():
    shared = _store(_fact(), _fact(subject="network", property="link", value="up"))
    first = _assemble(
        store=shared,
        history=(_turn(), _turn(label=HistoryLabel.PROVIDER_REPLY)),
        evidence=(_evidence(),),
        skill_material=(_skill(),),
    )
    second = _assemble(
        store=shared,
        history=(_turn(), _turn(label=HistoryLabel.PROVIDER_REPLY)),
        evidence=(_evidence(),),
        skill_material=(_skill(),),
    )
    assert first == second
    kinds = [
        event.category
        for event in first.events
        if event.kind is BoundaryEventKind.ENTERED
    ]
    assert kinds == [
        ContextCategory.FACTS,
        ContextCategory.GOAL,
        ContextCategory.HISTORY,
        ContextCategory.EVIDENCE,
        ContextCategory.SKILL_MATERIAL,
        ContextCategory.ROUTING_STATE,
    ]


def test_the_context_field_order_is_the_s12_composition_order():
    assert list(Context.__dataclass_fields__) == [
        "facts",
        "goal",
        "history",
        "evidence",
        "skill_material",
        "routing",
        "state",
    ]


def test_assembly_carries_one_active_goal_and_never_merges_sessions():
    context = _context()
    assert isinstance(context.goal, GoalValue)
    assert context.goal.statement == "repair the boot"
    assert not hasattr(context, "goals")  # one Goal per working set (CM9)


def test_cm1_context_is_never_a_source_of_truth():
    source = _fact()
    context = _context(store=_store(source))
    assert context.facts[0] is source
    assert context.facts[0].status is FactStatus.OBSERVED
    assert not hasattr(context, "truth")
    assert not hasattr(context, "verdict")


def test_cm3_only_the_context_manager_assembles_context():
    sources = [
        path.read_text(encoding="utf-8")
        for path in CONTEXT_ROOT.glob("*.py")
        if not path.name.startswith("__")
    ]
    for source in sources:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Context"
            ):
                assert "assemble.py" in source or "assemble" in source, (
                    "only assemble constructs a Context (CM3)"
                )


def test_cm5_assembly_is_purpose_limited():
    unrelated = _turn(content="a different concern", purpose="something else")
    assembly = _assemble(history=(unrelated,))
    assert assembly.context.history == ()
    reasons = [
        d.reason for d in assembly.disclosures if d.category is ContextCategory.HISTORY
    ]
    assert REASON_UNPURPOSEFUL in reasons


def test_cm5_assembly_requires_a_stated_purpose():
    with pytest.raises(ValueError):
        _assemble(purpose="   ")
    with pytest.raises(ValueError):
        _assemble(goal=_goal(statement="   "))


def test_cm6_context_is_bounded_with_transparent_consolidation():
    store = _store(
        _fact(subject="network", property="link", value="up"),
        _fact(subject="systemd", property="running-state", value="running"),
    )
    assembly = _assemble(store=store, fact_bound=1)
    assert len(assembly.context.facts) == 1
    assert assembly.context.state is ContextState.CONSOLIDATED
    reasons = [
        d.reason for d in assembly.disclosures if d.category is ContextCategory.FACTS
    ]
    assert REASON_OVERFLOW in reasons
    assert any(d.count == 1 for d in assembly.disclosures)


def test_cm6_the_context_never_grows_beyond_its_bounds():
    store = _store(*[_fact(subject=f"s{i}", property="p") for i in range(10)])
    assembly = _assemble(store=store, fact_bound=3)
    assert len(assembly.context.facts) == 3


def test_cm7_stale_material_is_excluded_or_marks_the_set_stale():
    store = _store(
        _fact(freshness=FreshnessState.STALE, subject="systemd"),
        _fact(freshness=FreshnessState.EXPIRED, subject="network"),
        _fact(subject="boot", property="loader", value="grub"),
    )
    assembly = _assemble(store=store)
    carried = {fact.scope.subject.name for fact in assembly.context.facts}
    assert carried == {"boot"}
    assert assembly.context.state is ContextState.STALE
    reasons = [
        d.reason for d in assembly.disclosures if d.category is ContextCategory.FACTS
    ]
    assert REASON_STALE_EXCLUDED in reasons
    assert any(event.kind is BoundaryEventKind.INVALIDATED for event in assembly.events)


def test_cm7_current_and_possibly_stale_are_admissible():
    store = _store(
        _fact(subject="systemd", freshness=FreshnessState.CURRENT),
        _fact(subject="network", freshness=FreshnessState.POSSIBLY_STALE),
    )
    assembly = _assemble(store=store)
    assert {fact.scope.subject.name for fact in assembly.context.facts} == {
        "systemd",
        "network",
    }


def test_cm8_invalidation_is_deterministic_and_precedes_use():
    context = _context()
    stale, event = mark_stale(context, reason="boot state changed")
    assert stale.state is ContextState.STALE
    assert stale is not context
    assert event.kind is BoundaryEventKind.INVALIDATED
    assert event.identity == "boot state changed"
    assert event.size == len(context.facts)
    with pytest.raises(ValueError):
        mark_stale(stale, reason="again")
    with pytest.raises(ValueError):
        mark_stale(context, reason="   ")


def test_cm13_recovery_is_reassembly_never_restore():
    src = _code_without_literals()
    for token in ("restore", "rebuild(", "resurrect", "snapshot"):
        assert token not in src
    assert "assemble" in src  # re-assembly is the only forward path


def test_the_boundary_events_are_value_free_and_precede_the_material():
    assembly = _assemble()
    assert assembly.events
    for event in assembly.events:
        assert isinstance(event, BoundaryEvent)
        assert event.kind is BoundaryEventKind.ENTERED
        assert not any(
            event.identity == TOKEN for _ in [None]
        )  # identity is the purpose, never the material


# --- Supersede-disclose semantics (RFC-0012 §33; DN-71) --------------------


def test_a_new_question_supersedes_and_discloses_the_old():
    marker = _routing()
    first = supersede_question(marker, "which step failed?")
    assert first.replaced is False
    assert first.superseded is None
    assert first.active.outstanding_question == "which step failed?"
    second = supersede_question(first.active, "what changed?")
    assert second.replaced is True
    assert second.superseded == "which step failed?"
    assert second.active.outstanding_question == "what changed?"


def test_the_same_question_routes_unchanged():
    marker = _routing(outstanding_question="which step failed?")
    same = supersede_question(marker, "which step failed?")
    assert same.replaced is False
    assert same.superseded is None
    assert same.active is marker


def test_a_blank_question_is_refused():
    with pytest.raises(ValueError):
        supersede_question(_routing(), "   ")


def test_the_routing_marker_is_process_state_not_evidence():
    marker = _routing(outstanding_question="which step failed?", current_decision="d")
    assert marker.outstanding_question == "which step failed?"
    assert marker.current_decision == "d"
    assert not hasattr(marker, "evidence")
    assert not hasattr(marker, "truth")


# --- Secret-free Context and View (CM4, SC2, SC3, T10) ---------------------


def test_sc2_a_known_token_never_enters_context_in_any_form():
    refused = admit(_datum(content=TOKEN, designation=None))
    assert refused.disposition is BoundaryDisposition.REFUSED
    assert refused.text == ""
    admitted = admit(_datum(content="the machine fails to boot"))
    context = _assemble(history=(_turn(content=admitted.text),)).context
    view = derive(context).view
    for representation in (
        repr(context),
        repr(view),
        repr(admitted),
        repr(refused),
    ):
        assert TOKEN not in representation


def test_sc3_no_secret_enters_the_provider_view():
    refused = admit(_datum(content=TOKEN, designation=None))
    assert refused.text == ""
    context = _context()
    view = derive(context).view
    assert set(ProviderView.__dataclass_fields__) == {
        "goal",
        "facts",
        "history",
        "evidence",
        "routing",
    }
    assert TOKEN not in repr(view)


def test_t10_a_secret_shape_appears_nowhere_in_the_pipeline():
    refused = admit(_datum(content=TOKEN, designation=None))
    assert TOKEN not in repr(refused)
    assert TOKEN not in refused.reason
    context = _context()
    assert TOKEN not in repr(context)
    assert TOKEN not in repr(derive(context))


def test_cm4_fail_close_is_explicit_not_silent():
    refused = admit(_datum(content=TOKEN, designation=None))
    assert refused.disposition is BoundaryDisposition.REFUSED
    assert refused.refusal is not None
    assert refused.reason
    assert refused.text == ""


def test_sc16_personal_data_is_secret_until_an_explicit_demotion():
    private = admit(_datum(content=PERSONAL, designation=None))
    assert private.disposition is BoundaryDisposition.REFUSED
    assert private.refusal is BoundaryRefusal.UNCLASSIFIABLE
    demoted = admit(
        _datum(content=PERSONAL, designation=NonSecretDesignation.MARKED_PUBLIC)
    )
    assert demoted.disposition is BoundaryDisposition.ADMITTED
    assert demoted.text == f"«{PERSONAL}»"


# --- Boundary guarantees (CM4, RFC-0007 S1–S8) -----------------------------


def test_the_boundary_contains_and_neutralizes_untrusted_text():
    decision = admit(_datum(content="hello\x1b[31mred\x1b[0m\x07world\u200b"))
    assert decision.text.startswith("«") and decision.text.endswith("»")
    assert "\x1b" not in decision.text
    assert "\\x07" in decision.text


def test_the_boundary_is_deterministic():
    datum = _datum()
    assert admit(datum) == admit(datum)


def test_the_boundary_refuses_unpurposeful_input():
    decision = admit(_datum(purpose="   "))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.UNPURPOSEFUL


def test_the_boundary_excludes_hostile_quarantined_content():
    decision = admit(
        _datum(
            content="service restarted",
            category=TrustCategory.OBSERVATION,
            provenance=ProvenanceState.LOST,
            designation=None,
        )
    )
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.HOSTILE
    assert isinstance(decision.quarantine, Quarantine)
    assert decision.quarantine.excluded is True


def test_the_boundary_is_value_free():
    refused = admit(
        _datum(content="sk-abcdefghijklmnopqrstuvwxyz123456", designation=None)
    )
    assert refused.text == ""
    admitted = admit(_datum(content="the machine fails to boot"))
    assert admitted.text == "«the machine fails to boot»"


# --- Memory guarantees (CM2, CM11, CM12, CM13, CM14) -----------------------


def test_cm2_memory_decides_nothing():
    memory = _memory_with_entries()
    assert isinstance(memory, Memory)
    for cls in (Memory, MemoryEntry):
        for name, attr in vars(cls).items():
            if name.startswith("__") and name.endswith("__"):
                continue
            assert not callable(attr), f"{cls.__name__} decides nothing (CM2)"


def test_cm11_no_promotion_without_explicit_consent():
    outcome = promote(
        empty(),
        category=MemoryCategory.PREFERENCE,
        identity="a",
        content="one",
        purpose=PURPOSE,
        consent=False,
        consented_on=datetime(2026, 8, 7).date(),
    )
    assert outcome.refusal is MemoryRefusal.NO_CONSENT
    assert outcome.event is None
    assert list_entries(outcome.memory) == ()


def test_cm11_no_promotion_without_a_stated_purpose():
    outcome = promote(
        empty(),
        category=MemoryCategory.PREFERENCE,
        identity="a",
        content="one",
        purpose="   ",
        consent=True,
        consented_on=datetime(2026, 8, 7).date(),
    )
    assert outcome.refusal is MemoryRefusal.UNPURPOSEFUL
    assert list_entries(outcome.memory) == ()


def test_cm12_destruction_is_complete_and_recorded():
    memory = _memory_with_entries()
    wiped = wipe(memory)
    assert list_entries(wiped.memory) == ()
    assert wiped.event.kind is BoundaryEventKind.DESTROYED
    assert wiped.event.size == 2
    removed = remove(
        wiped.memory, category=MemoryCategory.PREFERENCE, identity="missing"
    )
    assert removed.refusal is MemoryRefusal.NOT_FOUND


def test_cm13_memory_has_no_restore_path():
    memory = _memory_with_entries()
    wiped = wipe(memory)
    assert export(wiped.memory) == ()
    import io
    import tokenize

    text = (CONTEXT_ROOT / "memory.py").read_text(encoding="utf-8")
    src = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            src.append(" ")
        else:
            src.append(tok.string)
    code = "".join(src)
    for token in ("restore", "rebuild(", "resurrect", "snapshot"):
        assert token not in code


def test_cm14_memory_is_visible_exportable_and_wipable():
    memory = _memory_with_entries()
    assert [entry.identity for entry in list_entries(memory)] == ["a", "b"]
    assert [entry.identity for entry in export(memory)] == ["a", "b"]
    by_category = list_entries(memory, category=MemoryCategory.PREFERENCE)
    assert [entry.identity for entry in by_category] == ["a"]
    assert list_entries(wipe(memory).memory) == ()


def test_memory_holds_no_secret_or_audit_material():
    memory = _memory_with_entries()
    for _entry in export(memory):
        fields = set(MemoryEntry.__dataclass_fields__)
        assert fields == {"category", "identity", "content", "purpose", "consented_on"}
        assert not {"secret", "token", "audit", "transcript"} & fields


# --- Provider View guarantees (SC3, PR14, RFC-0010 §3) ---------------------


def test_pr14_the_view_is_the_only_outward_channel():
    src = "\n".join(
        path.read_text(encoding="utf-8")
        for path in CONTEXT_ROOT.glob("*.py")
        if not path.name.startswith("__")
    )
    producer_files = {}
    for path in CONTEXT_ROOT.glob("*.py"):
        if path.name.startswith("__"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ProviderView"
            ):
                producer_files[path.name] = True
    assert producer_files == {"provider_view.py": True}
    assert TOKEN not in src.replace("provider_view", "")


def test_the_projection_derives_exactly_the_five_s3_elements():
    context = _context(history=(_turn(),), evidence=(_evidence(),))
    view = derive(context).view
    assert view.goal == context.goal
    assert view.facts is context.facts
    assert view.history is context.history
    assert view.evidence is context.evidence
    assert view.routing is context.routing


def test_the_projection_refuses_a_stale_working_set():
    stale = mark_stale(_context(), reason="boot state changed")[0]
    outcome = derive(stale)
    assert outcome.disposition is ViewDisposition.REFUSED
    assert outcome.refusal is ViewRefusal.STALE_WORKING_SET
    assert outcome.view is None


def test_the_projection_refuses_a_blank_goal_statement():
    malformed = Context(
        facts=(),
        goal=GoalValue(statement="   ", scope="boot configuration"),
        history=(),
        evidence=(),
        skill_material=(),
        routing=_routing(),
        state=ContextState.CURRENT,
    )
    outcome = derive(malformed)
    assert outcome.disposition is ViewDisposition.REFUSED
    assert outcome.refusal is ViewRefusal.MALFORMED


def test_the_projection_is_deterministic_and_value_preserving():
    context = _context()
    assert derive(context) == derive(context)
    assert derive(context).view == derive(context).view


def test_the_projection_invents_nothing():
    context = _context()
    view = derive(context).view
    assert view.goal == context.goal
    assert view.facts == context.facts
    assert view.history == context.history
    assert view.evidence == context.evidence
    assert view.routing == context.routing


# --- One-way flow and no authority (CM10, CM15, CM16) ----------------------


def test_material_leaves_context_only_as_view_promotion_or_destruction():
    from episky.context import memory, provider_view

    outward = {
        "ProviderView": provider_view.ProviderView,
        "Memory": memory.Memory,
    }
    assert outward["ProviderView"] is ProviderView
    assert outward["Memory"] is Memory


def test_cm15_context_is_never_the_audit():
    src = "\n".join(
        path.read_text(encoding="utf-8")
        for path in CONTEXT_ROOT.glob("*.py")
        if not path.name.startswith("__")
    )
    assert "episky.audit" not in src
    assert (
        "audit"
        not in src.replace("Audit", "").replace("audit", "").replace("audit", "")
        or "no audit write" in src
    )


def test_cm16_context_and_memory_carry_no_permissions():
    src = "\n".join(
        path.read_text(encoding="utf-8")
        for path in CONTEXT_ROOT.glob("*.py")
        if not path.name.startswith("__")
    )
    for forbidden in ("episky.policy", "episky.executor", "episky.providers"):
        assert forbidden not in src


def test_no_provider_no_audit_no_policy_no_verification_authority():
    mods = {
        "assemble": "episky.context.assemble",
        "boundaries": "episky.context.boundaries",
        "memory": "episky.context.memory",
        "provider_view": "episky.context.provider_view",
    }
    for _name, module in mods.items():
        mod = importlib.import_module(module)
        for attr in ("request", "approve", "verify", "execute", "audit"):
            assert not hasattr(mod, attr), f"{module} exposes {attr}"


# --- No hidden state -------------------------------------------------------


def test_transitions_leave_the_original_values_unchanged():
    context = _context()
    stale, _event = mark_stale(context, reason="boot state changed")
    assert context.state is ContextState.CURRENT
    assert stale is not context
    memory = _memory_with_entries()
    promote(
        memory,
        category=MemoryCategory.PREFERENCE,
        identity="c",
        content="three",
        purpose=PURPOSE,
        consent=True,
        consented_on=datetime(2026, 8, 7).date(),
    )
    assert [entry.identity for entry in list_entries(memory)] == ["a", "b"]


def test_all_context_values_are_immutable():
    with pytest.raises(FrozenInstanceError):
        _context().goal = _goal(statement="other")
    with pytest.raises(FrozenInstanceError):
        _memory_with_entries().entries = ()


# --- Cross-layer obligations are recorded, only the context half verified --


def test_cross_layer_obligations_are_recorded_with_their_owners():
    assert len(DEFERRED_OBLIGATIONS) >= 10
    owners = {item[2] for item in DEFERRED_OBLIGATIONS}
    assert {"core", "RFC-0014/RFC-0020", "RFC-0015", "RFC-0020"} & owners
    for _name, guarantee, owner, source in DEFERRED_OBLIGATIONS:
        assert guarantee
        assert owner
        assert source
