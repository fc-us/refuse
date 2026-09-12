#!/usr/bin/env python3
"""refuse - the primitive all three Frontier Commons entries are built on.

    An output that cannot be traced to a source of record does not render.

Two programs in this repo family already independently invented this: a statutory
housing engine and a clinical referral agent. Same shape, different source of record.
This is that shape, named once.

THREE PROVENANCE STATES, AND ONLY THREE
    computed  - a source of record answered, and the citation is attached
    asserted  - a human told us; we did not verify it, and we say so
    unknown   - no source of record can answer this. A human must. We do not guess.

THREE INVARIANTS, each with a test that fails the build (see test_refuse.py)
    I1  A `computed` Claim with no cite cannot render.
    I2  An output item that did not come back from a verifier cannot exist.
    I3  A source of record that is DOWN produces no output at all - never a
        silent partial. A two-of-three that looks like a three-of-three is the
        failure mode that gets someone hurt.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal, Callable, Any
import datetime

Provenance = Literal["computed", "asserted", "unknown"]


class SourceDown(Exception):
    """A source of record is unreachable. Never caught and swallowed - I3."""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


@dataclass
class Claim:
    """A fact plus where it came from. Renderers refuse Claims without a cite."""
    label: str
    value: Any
    provenance: Provenance
    cite: Optional[str] = None
    note: Optional[str] = None
    observed_at: str = field(default_factory=_now)

    def renderable(self) -> bool:
        if self.provenance == "computed":
            return self.cite is not None      # I1
        return True


@dataclass
class Verdict:
    """What one verifier concluded about one candidate.

    passed is deliberately tri-state:
        True   - the source of record affirmed it
        False  - the source of record contradicted it   -> candidate is dropped
        None   - no source of record can answer         -> becomes an open question
                 that travels with the candidate all the way to the page
    """
    check: str
    passed: Optional[bool]
    detail: str
    cite: Optional[str] = None
    observed_at: str = field(default_factory=_now)

    def as_claim(self, label: str) -> Claim:
        if self.passed is None:
            return Claim(label, None, "unknown", None, self.detail)
        return Claim(label, self.passed, "computed", self.cite, self.detail)


@dataclass
class Rejection:
    candidate: str
    check: str
    detail: str
    cite: Optional[str] = None
    observed_at: str = field(default_factory=_now)


@dataclass
class Item:
    """A candidate that survived. Carries its whole evidence trail, always."""
    name: str
    data: dict
    verdicts: list = field(default_factory=list)

    @property
    def open_questions(self) -> list:
        return [v for v in self.verdicts if v.passed is None]

    def renderable(self) -> bool:
        # I2: nothing reaches output without at least one affirming verdict,
        # and never with a contradicting one.
        if any(v.passed is False for v in self.verdicts):
            return False
        return any(v.passed is True for v in self.verdicts)


@dataclass
class Outcome:
    status: str            # ok | short | refused_source_down | refused_policy
    items: list = field(default_factory=list)
    rejections: list = field(default_factory=list)
    plan: list = field(default_factory=list)
    trace: list = field(default_factory=list)
    message: str = ""
    open_questions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "message": self.message,
            "plan": self.plan,
            "items": [{"name": i.name, **i.data,
                       "verdicts": [asdict(v) for v in i.verdicts],
                       "open_questions": [asdict(v) for v in i.open_questions]}
                      for i in self.items],
            "rejections": [asdict(r) for r in self.rejections],
            "open_questions": [asdict(v) for v in self.open_questions],
            "trace": self.trace,
        }


def screen(verdicts: list) -> tuple[bool, list, list]:
    """Split a candidate's verdicts into (survives, failures, unknowns)."""
    fails = [v for v in verdicts if v.passed is False]
    unks = [v for v in verdicts if v.passed is None]
    return (not fails and any(v.passed is True for v in verdicts)), fails, unks


def _refuse(out: "Outcome", e: Exception) -> "Outcome":
    """I3, and the reason this function exists at all.

    Anything already verified is DISCARDED. A run that was going to return three
    names and lost its source of record after two must not hand over two - a
    partial sheet is indistinguishable from a complete one once it is printed,
    and that is the failure mode that gets someone hurt.
    """
    kept = len(out.items)
    out.items = []
    out.open_questions = []
    out.status = "refused_source_down"
    out.message = (f"{e} is unreachable. No sheet produced"
                   + (f", and the {kept} name(s) already verified in this run have "
                      f"been discarded" if kept else "")
                   + ". An unverified sheet is worse than none.")
    out.trace.append({"t": _now(), "step": "SOURCE DOWN",
                      "detail": f"{e} - discarded {kept} already-verified item(s)"})
    return out


def run(
    plan_strategy: Callable[[int], str],
    search: Callable[[str], list],
    verifiers: list,
    target_n: int = 3,
    max_attempts: int = 4,
    trace: Optional[list] = None,
    on_event: Optional[Callable[[dict], None]] = None,
) -> Outcome:
    """The loop. Plan, search, verify, re-plan on failure, fail loud on DOWN.

    This is an agent and not a filter because:
      1. a candidate reaches output only via a Verdict - the model cannot write
         a licence number it was not handed;
      2. verification failure re-enters search with a revised strategy, so the
         loop length is not known at design time;
      3. a source being DOWN stops everything, rather than degrading quietly.
    """
    out = Outcome(status="short", trace=trace if trace is not None else [])
    seen: set = set()

    class _Trace(list):
        """Appending to the trace emits it, so the page watches the run happen
        rather than replaying a recording of it afterwards."""
        def append(self, ev):
            super().append(ev)
            if on_event:
                on_event(ev)

    out.trace = _Trace(out.trace)

    for attempt in range(max_attempts):
        strategy = plan_strategy(attempt)
        out.plan.append(strategy)
        out.trace.append({"t": _now(), "step": "plan", "detail": strategy.get("label", str(strategy)) if isinstance(strategy, dict) else str(strategy)})

        try:
            candidates = search(strategy)
        except SourceDown as e:
            return _refuse(out, e)                                  # I3

        out.trace.append({"t": _now(), "step": "search",
                          "detail": f"{len(candidates)} candidates"})

        for cand in candidates:
            key = cand.get("name")
            if key in seen:
                continue
            seen.add(key)

            verdicts = []
            for v in verifiers:
                try:
                    verdict = v(cand)
                except SourceDown as e:
                    return _refuse(out, e)                          # I3
                verdicts.append(verdict)
                out.trace.append({"t": _now(), "step": "verify",
                                  "detail": f"{key} :: {verdict.check} :: "
                                            f"{ {True:'PASS',False:'FAIL',None:'UNKNOWN'}[verdict.passed] }"
                                            f" - {verdict.detail}"})
                if verdict.passed is False:
                    break

            survives, fails, unks = screen(verdicts)
            if not survives:
                f = fails[0] if fails else Verdict("no affirming source", False,
                                                   "nothing confirmed this candidate")
                out.rejections.append(Rejection(key, f.check, f.detail, f.cite))
                continue

            item = Item(name=key, data=cand, verdicts=verdicts)
            if not item.renderable():                               # I2, belt and braces
                out.rejections.append(Rejection(key, "render guard",
                                                "no affirming verdict"))
                continue
            out.items.append(item)
            for u in unks:
                if u.check not in {q.check for q in out.open_questions}:
                    out.open_questions.append(u)

            if len(out.items) >= target_n:
                out.status = "ok"
                return out

    out.status = "ok" if out.items else "short"
    if len(out.items) < target_n:
        out.message = (f"Found {len(out.items)} of {target_n} after "
                       f"{len(out.plan)} strategies. Stating the gap rather than filling it.")
    return out
