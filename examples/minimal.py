#!/usr/bin/env python3
"""The smallest thing that shows what refuse does.

    python3 examples/minimal.py

One verifier that works, one source that dies. Watch what comes back.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from refuse import run, Verdict, SourceDown, Claim

PEOPLE = [{"name": "Ada", "licence": "1234"},
          {"name": "Grace", "licence": None},
          {"name": "Kathleen", "licence": "5678"}]


def licence_on_file(cand):
    """A hard verifier. Contradiction drops the candidate, with a reason."""
    if cand["licence"]:
        return Verdict("licence on file", True, f"licence {cand['licence']}",
                       "the registry, 2026-09-12")
    return Verdict("licence on file", False, "no licence number on record",
                   "the registry, 2026-09-12")


def currently_practising(cand):
    """An honest unknown. No source answers this, so it says so and travels
    with the candidate all the way to the output."""
    return Verdict("currently practising", None,
                   "no public source holds this - call and ask", None)


print("A normal run\n" + "-" * 52)
out = run(lambda attempt: f"search pass {attempt + 1}",
          lambda strategy: PEOPLE,
          [licence_on_file, currently_practising],
          target_n=2)
print("status:", out.status)
for i in out.items:
    print("  kept   ", i.name)
for r in out.rejections:
    print("  dropped", r.candidate, "-", r.detail)
for q in out.open_questions:
    print("  unknown", q.check, "-", q.detail)

print("\nThe same run, but the source dies after the first name\n" + "-" * 52)
n = {"i": 0}
def flaky(cand):
    n["i"] += 1
    if n["i"] > 1:
        raise SourceDown("the registry")
    return licence_on_file(cand)

out = run(lambda a: "search", lambda s: PEOPLE, [flaky, currently_practising], target_n=2)
print("status:", out.status)
print("items :", len(out.items), "  <- not one. Zero.")
print(out.message)

print("\nAnd a claim that cannot render\n" + "-" * 52)
print("computed, no cite :", Claim("units", 40, "computed").renderable())
print("computed, cited   :", Claim("units", 40, "computed", "Gov. Code s65913.16(j)(2)(A)").renderable())
print("unknown           :", Claim("units", None, "unknown").renderable())
