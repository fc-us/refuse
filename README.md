# refuse

**An output that cannot be traced to a source of record does not render.**

A ~250-line dependency-free Python module for systems where being confidently wrong lands
on a person: clinical referrals, statutory findings, pastoral care, anything where
"verified" currently means "I read a directory."

```python
from refuse import run, Verdict, SourceDown, Claim
```

## Three provenance states, and only three

| State | Meaning |
|---|---|
| `computed` | a source of record answered, and the citation is attached |
| `asserted` | a human told us, and we say so |
| `unknown` | no source can answer this. A human must. We do not guess |

The third one is the whole point. Most systems have no way to say it, so they say
something else instead.

## Three invariants, each with a test that fails the build

1. **A `computed` claim with no citation cannot render.**
2. **An output item that did not come back from a verifier cannot exist.** The model
   cannot write a licence number it was not handed.
3. **A source of record that is DOWN produces no output at all** — and anything already
   verified in that run is discarded. A partial result is indistinguishable from a
   complete one once it is printed, and that is the failure mode that gets someone hurt.

```
python3 tests/test_refuse.py
python3 examples/minimal.py
```

Invariant 3 was written after invariant 3 was broken. The first test run caught a
candidate that had passed every verifier sitting in the results when a later source died,
so the refusal returned two names where three were expected and nothing on screen said so.

## Verdicts are tri-state on purpose

```python
Verdict("licence on file",      True,  "TX licence 77466", "the state board")
Verdict("licence on file",      False, "no number on record", "the state board")
Verdict("currently practising", None,  "no public source holds this - call and ask")
```

`None` is not an error and not a failure. It is a question that travels with the item all
the way to the page, so the person reading it knows exactly which forty-five seconds of
work are still theirs.

## Why it exists

Three projects invented the same shape independently — a clinical referral agent, a
California housing-statute engine, and a Scripture tool that withholds — and the shape
turned out to be the interesting part, not any of the three domains.

Built for the Gloo AI Hackathon 2026 by Frontier Commons. Used by:

- **Referral Rounds** — source of record: the CMS NPI Registry and the HHS OIG exclusion list
- **By Right** — source of record: California Gov. Code §65913.16
- **No Verse For This** — source of record: a chaplain-authored refusal taxonomy

Stdlib only. Python 3.10+. MIT.
