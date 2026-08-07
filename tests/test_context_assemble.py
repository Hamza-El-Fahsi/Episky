"""Deterministic, bounded Context assembly (RFC-0012 §6, §8, §10–§12, §16,
§17, §33; RFC-0007 S7; RFC-0002 Q12/I-13).

Behavioral tests for Iteration 9 Commit C1 (`context/assemble.py`): the
deterministic assembly over the explicit boundary inputs (DN-66) — the
schema-shaped Goal value, the Fact current set from `factlayer` at its
freshness, bounded labeled history, labeled Evidence on
`schema.VerificationOutcome` (DN-74), sanitized Skill material, and the
routing-state marker (DN-71) — plus a stated purpose (CM5). The six §6
categories are explicit types (DN-73); the §12 composition order holds;
Stale/Expired/Unknown-freshness Facts are excluded or mark the set Stale
(CM7); the mark-stale function marks and records invalidation before use
(CM8, I-13); overflow consolidates transparently with a placeholder default
(CM6); the working set holds one Goal and never merges across sessions
(CM9); a lost set is rebuilt, never restored (CM13); assembly never returns
a truth verdict (CM1); and the deterministic, value-free context-boundary
events (DN-70) precede the material's use. No I/O, no provider call, no
`audit` import (CM15).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from episky.context.assemble import (
    DEFAULT_EVIDENCE_BOUND,
    DEFAULT_FACT_BOUND,
    DEFAULT_HISTORY_BOUND,
    DEFAULT_SKILL_BOUND,
    REASON_OVERFLOW,
    REASON_STALE_EXCLUDED,
    REASON_UNPURPOSEFUL,
    Assembly,
    BoundaryEvent,
    BoundaryEventKind,
    Context,
    ContextCategory,
    ContextState,
    Disclosure,
    EvidenceLabel,
    GoalValue,
    HistoryLabel,
    RoutingMarker,
    SkillMaterialItem,
    Supersession,
    TurnRecord,
    assemble,
    mark_stale,
    supersede_question,
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

ASSEMBLE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "context"
    / "assemble.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)

PURPOSE = "diagnose boot failure"

MACHINE_IDENTITY = MachineIdentity()

EXPECTED_PUBLIC_SURFACE = {
    "Assembly",
    "BoundaryEvent",
    "BoundaryEventKind",
    "Context",
    "ContextCategory",
    "ContextState",
    "DEFAULT_EVIDENCE_BOUND",
    "DEFAULT_FACT_BOUND",
    "DEFAULT_HISTORY_BOUND",
    "DEFAULT_SKILL_BOUND",
    "Disclosure",
    "EvidenceLabel",
    "GoalValue",
    "HistoryLabel",
    "REASON_OVERFLOW",
    "REASON_STALE_EXCLUDED",
    "REASON_UNPURPOSEFUL",
    "RoutingMarker",
    "SkillMaterialItem",
    "Supersession",
    "TurnRecord",
    "assemble",
    "mark_stale",
    "supersede_question",
}


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
    fact_bound=DEFAULT_FACT_BOUND,
    history_bound=DEFAULT_HISTORY_BOUND,
    evidence_bound=DEFAULT_EVIDENCE_BOUND,
    skill_bound=DEFAULT_SKILL_BOUND,
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


# --- Public surface and structure ---


def test_assemble_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.context.assemble")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in (
        Assembly,
        BoundaryEvent,
        Context,
        Disclosure,
        EvidenceLabel,
        GoalValue,
        RoutingMarker,
        SkillMaterialItem,
        Supersession,
        TurnRecord,
    ):
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_context_is_immutable():
    ctx = _assemble().context
    with pytest.raises(FrozenInstanceError):
        ctx.state = ContextState.STALE
    with pytest.raises(FrozenInstanceError):
        ctx.goal = _goal(statement="other")


# --- The six §6 categories (DN-73) ---


def test_context_category_is_exactly_the_six_s6_categories():
    assert tuple(ContextCategory) == (
        ContextCategory.GOAL,
        ContextCategory.FACTS,
        ContextCategory.HISTORY,
        ContextCategory.EVIDENCE,
        ContextCategory.SKILL_MATERIAL,
        ContextCategory.ROUTING_STATE,
    )


def test_context_carries_all_six_categories_as_explicit_fields():
    fields = set(Context.__dataclass_fields__)
    assert {
        "facts",
        "goal",
        "history",
        "evidence",
        "skill_material",
        "routing",
    } <= fields


def test_assembly_carries_each_supplied_category():
    result = _assemble(
        history=(_turn(),),
        evidence=(_evidence(),),
        skill_material=(_skill(),),
    )
    ctx = result.context
    assert len(ctx.facts) == 1
    assert ctx.history == (_turn(),)
    assert ctx.evidence == (_evidence(),)
    assert ctx.skill_material == (_skill(),)
    assert ctx.goal == _goal()
    assert ctx.routing == _routing()


# --- §12 composition order ---


def test_context_material_fields_follow_the_s12_composition_order():
    names = [field for field in Context.__dataclass_fields__ if field != "state"]
    assert names == [
        "facts",
        "goal",
        "history",
        "evidence",
        "skill_material",
        "routing",
    ]


def test_facts_enter_first_with_provenance_unchanged():
    fact = _fact()
    ctx = _assemble(store=_store(fact)).context
    assert ctx.facts == (fact,)
    assert ctx.facts[0].provenance == fact.provenance
    assert ctx.facts[0].status is FactStatus.OBSERVED
    assert ctx.facts[0].freshness.state is FreshnessState.CURRENT


def test_facts_are_carried_at_their_class_never_upgraded():
    fact = _fact(status=FactStatus.UNKNOWN)
    ctx = _assemble(store=_store(fact)).context
    assert ctx.facts[0].status is FactStatus.UNKNOWN
    assert ctx.facts[0] == fact


# --- Determinism (S7) ---


def test_same_inputs_purpose_and_bounds_yield_the_same_assembly():
    store = _store(_fact(), _fact(subject="sshd"))
    history = (_turn(), _turn(label=HistoryLabel.PROVIDER_REPLY))
    evidence = (_evidence(), _evidence(outcome=VerificationOutcome.UNKNOWN))
    skill = (_skill(),)
    first = assemble(
        goal=_goal(),
        fact_store=store,
        purpose=PURPOSE,
        history=history,
        evidence=evidence,
        skill_material=skill,
    )
    second = assemble(
        goal=_goal(),
        fact_store=store,
        purpose=PURPOSE,
        history=history,
        evidence=evidence,
        skill_material=skill,
    )
    assert first == second
    assert first.context == second.context
    assert first.events == second.events
    assert first.disclosures == second.disclosures


def test_store_insertion_order_does_not_change_the_assembled_context():
    earlier = _fact(subject="systemd", collected_at=NOW)
    later = _fact(subject="sshd", collected_at=NOW)
    a = assemble(
        goal=_goal(),
        fact_store=_store(earlier, later),
        purpose=PURPOSE,
    )
    b = assemble(
        goal=_goal(),
        fact_store=_store(later, earlier),
        purpose=PURPOSE,
    )
    assert a.context.facts == b.context.facts
    assert a == b


# --- Freshness gates (CM7) ---


def test_current_facts_are_carried_and_the_set_is_current():
    ctx = _assemble(store=_store(_fact())).context
    assert ctx.state is ContextState.CURRENT
    assert len(ctx.facts) == 1


def test_possibly_stale_facts_are_carried_with_caution_while_current():
    fact = _fact(freshness=FreshnessState.POSSIBLY_STALE)
    ctx = _assemble(store=_store(fact)).context
    assert ctx.facts == (fact,)
    assert ctx.state is ContextState.CURRENT


@pytest.mark.parametrize(
    "freshness",
    (FreshnessState.STALE, FreshnessState.EXPIRED, FreshnessState.UNKNOWN_FRESHNESS),
)
def test_a_stale_expired_or_unknown_fact_is_excluded_and_marks_the_set_stale(
    freshness,
):
    current = _fact()
    stale = _fact(subject="sshd", freshness=freshness)
    result = _assemble(store=_store(current, stale))
    ctx = result.context
    assert ctx.facts == (current,)
    assert ctx.state is ContextState.STALE


def test_the_stale_exclusion_is_disclosed_transparently():
    current = _fact()
    stale = _fact(subject="sshd", freshness=FreshnessState.STALE)
    result = _assemble(store=_store(current, stale))
    assert (
        Disclosure(
            category=ContextCategory.FACTS,
            reason=REASON_STALE_EXCLUDED,
            count=1,
        )
        in result.disclosures
    )


def test_a_stale_set_is_never_returned_as_current():
    stale = _fact(freshness=FreshnessState.EXPIRED)
    ctx = _assemble(store=_store(stale)).context
    assert ctx.state is ContextState.STALE
    assert ctx.facts == ()


def test_invalidation_is_recorded_before_the_stale_set_is_used():
    stale = _fact(subject="sshd", freshness=FreshnessState.STALE)
    result = _assemble(store=_store(stale))
    assert (
        BoundaryEvent(
            kind=BoundaryEventKind.INVALIDATED,
            category=ContextCategory.FACTS,
            identity=REASON_STALE_EXCLUDED,
            size=1,
        )
        in result.events
    )


# --- mark_stale (CM8) ---


def test_mark_stale_marks_the_set_stale_and_records_the_invalidation():
    ctx = _assemble().context
    stale, event = mark_stale(ctx, reason="freshness lapse (RFC-0005 §12)")
    assert stale.state is ContextState.STALE
    assert event == BoundaryEvent(
        kind=BoundaryEventKind.INVALIDATED,
        category=ContextCategory.FACTS,
        identity="freshness lapse (RFC-0005 §12)",
        size=len(ctx.facts),
    )


def test_mark_stale_returns_a_new_set_and_never_mutates_the_input():
    ctx = _assemble().context
    stale, _ = mark_stale(ctx, reason="state change (RFC-0002 §4.2)")
    assert ctx.state is ContextState.CURRENT
    assert stale is not ctx


def test_mark_stale_refuses_an_already_stale_set():
    ctx = _assemble(store=_store(_fact(freshness=FreshnessState.STALE))).context
    assert ctx.state is ContextState.STALE
    with pytest.raises(ValueError):
        mark_stale(ctx, reason="re-inspection (RFC-0005 §12)")


def test_mark_stale_refuses_a_blank_reason():
    ctx = _assemble().context
    with pytest.raises(ValueError):
        mark_stale(ctx, reason="   ")


def test_mark_stale_accepts_a_consolidated_set_like_current():
    consolidated = _assemble(
        store=_store(_fact(), _fact(subject="sshd")),
        fact_bound=1,
    ).context
    assert consolidated.state is ContextState.CONSOLIDATED
    stale, _ = mark_stale(consolidated, reason="reboot (RFC-0002 invariant 8)")
    assert stale.state is ContextState.STALE


# --- Bounds and transparent consolidation (CM6) ---


def test_overflow_consolidates_transparently_never_silently_grows():
    facts = (
        _fact(subject="systemd", collected_at=NOW),
        _fact(subject="sshd", collected_at=datetime(2026, 8, 7, 12, 0, 1)),
        _fact(subject="fstab", collected_at=datetime(2026, 8, 7, 12, 0, 2)),
        _fact(subject="grub", collected_at=datetime(2026, 8, 7, 12, 0, 3)),
    )
    result = _assemble(store=_store(*facts), fact_bound=2)
    ctx = result.context
    assert ctx.state is ContextState.CONSOLIDATED
    assert {f.scope.subject.name for f in ctx.facts} == {"fstab", "grub"}
    assert (
        Disclosure(
            category=ContextCategory.FACTS,
            reason=REASON_OVERFLOW,
            count=2,
        )
        in result.disclosures
    )


def test_history_keeps_the_most_recent_turns_on_overflow():
    old = _turn(content="old turn")
    recent = _turn(content="recent turn")
    result = _assemble(history=(old, recent), history_bound=1)
    assert result.context.history == (recent,)
    assert result.context.state is ContextState.CONSOLIDATED


def test_skill_material_keeps_the_head_on_overflow():
    first = _skill(content="first")
    second = _skill(content="second")
    result = _assemble(skill_material=(first, second), skill_bound=1)
    assert result.context.skill_material == (first,)
    assert result.context.state is ContextState.CONSOLIDATED


def test_within_bounds_there_is_no_consolidation():
    result = _assemble(store=_store(_fact(), _fact(subject="sshd")))
    assert result.context.state is ContextState.CURRENT
    assert result.disclosures == ()


def test_default_bounds_are_positive_placeholder_defaults():
    for bound in (
        DEFAULT_FACT_BOUND,
        DEFAULT_HISTORY_BOUND,
        DEFAULT_EVIDENCE_BOUND,
        DEFAULT_SKILL_BOUND,
    ):
        assert bound >= 1


def test_a_bound_below_one_is_refused():
    with pytest.raises(ValueError):
        _assemble(fact_bound=0)
    with pytest.raises(ValueError):
        _assemble(history_bound=0)


# --- Purpose limitation (CM5) ---


def test_assembly_refuses_without_a_stated_purpose():
    with pytest.raises(ValueError):
        _assemble(purpose="   ")
    with pytest.raises(ValueError):
        assemble(goal=_goal(), fact_store=_store(_fact()), purpose="")


def test_unpurposeful_material_is_excluded_and_refused():
    stray = _turn(purpose="recover deleted files")
    result = _assemble(history=(_turn(), stray))
    assert result.context.history == (_turn(),)
    assert (
        Disclosure(
            category=ContextCategory.HISTORY,
            reason=REASON_UNPURPOSEFUL,
            count=1,
        )
        in result.disclosures
    )


def test_unpurposeful_evidence_and_skill_are_refused():
    stray_evidence = _evidence(purpose="audit the session")
    stray_skill = _skill(purpose="print help text")
    result = _assemble(
        evidence=(_evidence(), stray_evidence),
        skill_material=(_skill(), stray_skill),
    )
    assert result.context.evidence == (_evidence(),)
    assert result.context.skill_material == (_skill(),)


def test_purposeful_material_is_admitted():
    result = _assemble(history=(_turn(),))
    assert result.context.history == (_turn(),)
    assert result.context.state is ContextState.CURRENT


# --- One Goal, no cross-session merge (CM9) ---


def test_the_working_set_holds_exactly_the_one_supplied_goal():
    result = _assemble(goal=_goal(statement="repair the network"))
    assert result.context.goal == _goal(statement="repair the network")
    assert result.context.goal.scope == "boot configuration"


def test_assembly_never_merges_material_across_sessions():
    first = _assemble(history=(_turn(content="session A turn"),)).context
    second = _assemble(history=(), goal=_goal(statement="session B goal")).context
    assert second.history == ()
    assert second.goal == _goal(statement="session B goal")
    assert first.history == (_turn(content="session A turn"),)


def test_assemble_never_mutates_its_inputs():
    store = _store(_fact(), _fact(subject="sshd"))
    history = (_turn(),)
    before = list(store.current.values())
    _assemble(store=store, history=history)
    assert list(store.current.values()) == before
    assert history == (_turn(),)


# --- Evidence on VerificationOutcome (DN-74) ---


@pytest.mark.parametrize("outcome", list(VerificationOutcome))
def test_evidence_is_labeled_material_on_any_verification_outcome(outcome):
    result = _assemble(evidence=(_evidence(outcome=outcome),))
    item = result.context.evidence[0]
    assert isinstance(item, EvidenceLabel)
    assert item.outcome is outcome


def test_evidence_is_never_a_decision_input_or_verification_power():
    result = _assemble(evidence=(_evidence(),))
    assert isinstance(result, Assembly)
    assert not hasattr(result.context.evidence[0], "decision")
    assert not hasattr(result.context, "verdict")
    assert not isinstance(result, bool)


def test_assembly_never_returns_a_truth_verdict():
    result = _assemble()
    assert isinstance(result, Assembly)
    assert isinstance(result.context, Context)
    assert not hasattr(result, "verdict")
    assert not hasattr(result, "conclusion")


# --- Routing state and §33 supersede-disclose (DN-71) ---


def test_the_routing_marker_is_carried_into_the_working_set():
    marker = _routing(outstanding_question="which service is failing?")
    ctx = _assemble(routing=marker).context
    assert ctx.routing == marker


def test_a_new_question_supersedes_and_discloses_the_old():
    marker = _routing(outstanding_question="old question")
    result = supersede_question(marker, "new question")
    assert result.replaced is True
    assert result.superseded == "old question"
    assert result.active.outstanding_question == "new question"
    assert result.active.current_decision == marker.current_decision


def test_a_reply_to_the_same_question_routes_unchanged():
    marker = _routing(outstanding_question="same question")
    result = supersede_question(marker, "same question")
    assert result.replaced is False
    assert result.superseded is None
    assert result.active == marker


def test_a_first_question_becomes_active_with_nothing_superseded():
    marker = _routing(outstanding_question=None)
    result = supersede_question(marker, "first question")
    assert result.replaced is False
    assert result.superseded is None
    assert result.active.outstanding_question == "first question"


def test_the_superseded_question_is_never_silently_dropped():
    marker = _routing(outstanding_question="old question")
    result = supersede_question(marker, "new question")
    assert result.superseded == "old question"


def test_supersede_question_refuses_a_blank_question():
    with pytest.raises(ValueError):
        supersede_question(_routing(), "   ")


# --- Context-boundary events (DN-70) ---


def test_assembly_emits_an_entered_event_per_carried_category_in_s12_order():
    result = _assemble(
        history=(_turn(),),
        evidence=(_evidence(),),
        skill_material=(_skill(),),
    )
    kinds = [event.kind for event in result.events]
    assert kinds == [BoundaryEventKind.ENTERED] * 6
    categories = [event.category for event in result.events]
    assert categories == [
        ContextCategory.FACTS,
        ContextCategory.GOAL,
        ContextCategory.HISTORY,
        ContextCategory.EVIDENCE,
        ContextCategory.SKILL_MATERIAL,
        ContextCategory.ROUTING_STATE,
    ]


def test_an_empty_category_emits_no_entered_event():
    result = _assemble(history=())
    assert not any(event.category is ContextCategory.HISTORY for event in result.events)


def test_events_are_value_free_and_carry_size_and_identity():
    result = _assemble(history=(_turn(), _turn(label=HistoryLabel.PROVIDER_REPLY)))
    history_event = next(
        event for event in result.events if event.category is ContextCategory.HISTORY
    )
    assert history_event.identity == PURPOSE
    assert history_event.size == 2
    for event in result.events:
        assert set(event.__dataclass_fields__) == {
            "kind",
            "category",
            "identity",
            "size",
        }
        assert event.identity == PURPOSE


# --- Recovery: rebuild, never restore (CM13) ---


def test_assemble_has_no_restore_path():
    mod = importlib.import_module("episky.context.assemble")
    assert not hasattr(mod, "restore")
    assert not hasattr(mod, "snapshot")
    assert "snapshot" not in Context.__dataclass_fields__


def test_a_rebuilt_set_is_assembled_from_inputs_never_a_previous_set():
    first = _assemble(history=(_turn(content="old"),)).context
    rebuilt = _assemble(history=(_turn(content="new"),)).context
    assert rebuilt is not first
    assert rebuilt.history == (_turn(content="new"),)


# --- Conformance: imports, I/O, clock, randomness, audit (CM15) ---


def test_assemble_imports_only_allowed_packages():
    tree = ast.parse(ASSEMBLE_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = [name for name in imported if name.startswith("episky")]
    assert sorted(episky_imports) == [
        "episky.factlayer.store",
        "episky.schema.fact",
        "episky.schema.outcome",
    ]


def test_assemble_never_reads_a_clock_or_randomness():
    src = ASSEMBLE_PATH.read_text(encoding="utf-8")
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
        "import hmac",
        "import hashlib",
    ):
        assert token not in src


def test_assemble_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(ASSEMBLE_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
    assert not calls & {"subprocess", "os.system", "socket", "requests", "urllib"}


def test_assemble_never_imports_audit():
    tree = ast.parse(ASSEMBLE_PATH.read_text(encoding="utf-8"))
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
