#!/usr/bin/env python3
"""The three invariants. If any of these fail, the build is broken - not degraded.

Run:  python3 test_refuse.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from refuse import Claim, Verdict, Item, SourceDown, run

FAILURES = []

def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        FAILURES.append(name)


print("I1  a computed claim with no citation cannot render")
check("computed without cite is not renderable", Claim("units", 40, "computed").renderable() is False)
check("computed with cite renders", Claim("units", 40, "computed", "Gov. Code s65913.16(j)(2)").renderable())
check("asserted renders without a cite", Claim("owner", True, "asserted").renderable())
check("unknown renders without a cite", Claim("transit", None, "unknown").renderable())

print("I2  an item that did not come back from a verifier cannot exist")
check("no verdicts at all -> not renderable", Item("X", {}).renderable() is False)
check("only unknown verdicts -> not renderable",
      Item("X", {}, [Verdict("board", None, "no interface")]).renderable() is False)
check("one failing verdict overrides a passing one",
      Item("X", {}, [Verdict("npi", True, "active", "c"),
                     Verdict("leie", False, "excluded", "c")]).renderable() is False)
check("passing verdict renders",
      Item("X", {}, [Verdict("npi", True, "active", "c")]).renderable())

print("I3  a source that is DOWN produces no output at all")

def _down_after_two(strategy):
    return [{"name": "A"}, {"name": "B"}, {"name": "C"}]

def _v_ok(c):
    return Verdict("ok", True, "fine", "cite")

_calls = {"n": 0}
def _v_dies_on_third(c):
    _calls["n"] += 1
    if _calls["n"] == 3:
        raise SourceDown("TEST source of record")
    return Verdict("ok", True, "fine", "cite")

out = run(lambda a: "s", _down_after_two, [_v_ok, _v_dies_on_third], target_n=3)
check("status is refused_source_down", out.status == "refused_source_down")
check("ZERO items returned, not a partial two", len(out.items) == 0)
check("the refusal says which source died", "TEST source of record" in out.message)

def _search_dies(strategy):
    raise SourceDown("TEST directory")
out2 = run(lambda a: "s", _search_dies, [_v_ok], target_n=3)
check("a dead directory also refuses", out2.status == "refused_source_down" and not out2.items)

print()
if FAILURES:
    print(f"{len(FAILURES)} INVARIANT(S) BROKEN:")
    for f in FAILURES:
        print("   -", f)
    sys.exit(1)
print("all invariants hold")
