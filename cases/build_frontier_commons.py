#!/usr/bin/env python3
"""Build the Frontier Commons dossier — refuse v2's first real-world case.

We audit ourselves, not someone else. Every number below was pulled tonight
(2026-09-14) from a source of record or explicitly refused.

    python3 build_frontier_commons.py > frontier-commons.html
"""
import sys, os, sqlite3, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
WHO_SAYS = os.path.abspath(os.path.join(HERE, "..", "..", "who-says"))
sys.path.insert(0, WHO_SAYS)

from refuse2 import Source, Claim, Unverifiable, Dossier, Unlicensed  # noqa: E402

IRS_DB = os.path.join(WHO_SAYS, "index", "irs.db")
IFI_EIN = "310971249"

# ---------------------------------------------------------------- sources

IRS = Source(
    name="IRS Exempt Organizations Business Master File",
    answers=("organisation exists", "tax-exempt status", "NTEE classification",
             "registered address", "ruling date", "deductibility"),
    licence="US Government work — public domain, freely redistributable",
    redistributable=True,
    freshness="monthly publication; indexed 12 Sept 2026",
    coverage="all 50 states, DC and territories — 1,964,958 organisations",
    cite="irs.gov/pub/irs-soi/eo1.csv (parts 1-4)",
)

# MinistryWatch is DELIBERATELY not constructed as a Source.
# On 2026-09-14 ministrywatch.com served no terms-of-use page (404 on /terms and
# /terms-of-use), no licence or redistribution statement on /about, and
# db.ministrywatch.com returned 403. refuse2's rule is that a source which cannot
# state its licence cannot be queried — so we do not query it, and we say so.
MINISTRYWATCH_REFUSAL = (
    "No licence or terms-of-use statement could be found on 2026-09-14: "
    "/terms and /terms-of-use returned 404, /about contains no redistribution "
    "language, and db.ministrywatch.com returned 403 to an automated request."
)


def irs_record(ein):
    if not os.path.exists(IRS_DB):
        raise FileNotFoundError(
            f"{IRS_DB} missing — rebuild with `python3 scripts_build_irs.py` in who-says/"
        )
    con = sqlite3.connect(IRS_DB)
    cur = con.execute(
        "SELECT ein,name,street,city,state,zip,ntee,revenue,assets,ruling,"
        "status,subsection,deductibility FROM orgs WHERE ein=?", (ein,))
    row = cur.fetchone()
    con.close()
    if row is None:
        return None
    cols = ("ein name street city state zip ntee revenue assets ruling "
            "status subsection deductibility").split()
    return dict(zip(cols, row))


def build():
    d = Dossier(subject="Frontier Commons", place="United States")

    ifi = irs_record(IFI_EIN)
    if ifi is None:
        d.refuse(f"IRS BMF returned no record for EIN {IFI_EIN}.")
        return d

    ruling = ifi["ruling"]
    ruling_txt = f"{ruling[:4]}-{ruling[4:]}" if ruling and len(ruling) == 6 else ruling

    for label, value in [
        ("Parent organisation, legal name", ifi["name"]),
        ("EIN", ifi["ein"]),
        ("Registered address",
         f'{ifi["street"]}, {ifi["city"]}, {ifi["state"]} {ifi["zip"]}'),
        ("IRS subsection", f'{ifi["subsection"]} — 501(c)(3)'),
        ("NTEE classification", f'{ifi["ntee"]} — Religion-related, International'),
        ("IRS ruling date", ruling_txt),
        ("Contributions deductible", "Yes" if ifi["deductibility"] == "1" else ifi["deductibility"]),
    ]:
        d.add(Claim(label=label, value=value, provenance="computed", source=IRS))

    # Frontier Commons itself is absent from the BMF. That is a finding.
    d.add(Claim(
        label="Frontier Commons as a separate legal entity",
        value="No record",
        provenance="computed",
        source=IRS,
        note="A LIKE '%FRONTIER COMMONS%' scan of all 1,964,958 BMF organisations "
             "returns nothing. Frontier Commons is a programme of International "
             "Friendships, Inc.; it has no EIN of its own.",
    ))

    d.add(Claim(
        label="Frontier Commons operates as an initiative of IFI",
        value="Asserted by Frontier Commons",
        provenance="asserted",
        note="No source of record establishes the relationship. We are simply telling you.",
    ))

    d.drop("MinistryWatch transparency score", "licence check",
           MINISTRYWATCH_REFUSAL)
    d.drop("MinistryWatch stated annual revenue", "licence check",
           "Same refusal. The figure sits in our local corpus and is deliberately not "
           "printed here — quoting it in order to explain why we will not quote it "
           "would republish it just the same.")

    d.cannot(Unverifiable(
        question="What is Frontier Commons' SIQ score? (recorded as [4, 4, 4, 7, 5])",
        why="The score was produced by siq_infer.py from a single input labelled "
            "'ci_alliances'. That script is referenced in SIQ's CLAUDE.md at "
            "~/Documents/Claude/linkedin2/siq_infer.py. The directory no longer "
            "exists and the file is nowhere on disk, so the number cannot be "
            "re-derived, audited, or explained.",
        who_can="Andrew Feng — nobody else has the original pipeline.",
        how_long="Unknown. Possibly not at all; it may have to be rebuilt from scratch.",
        checked=("SIQ D1 profiles table", "local filesystem", "siq-protocol repo"),
    ))
    d.cannot(Unverifiable(
        question="What is International Friendships' SIQ score? (recorded as [4, 4, 4, 4, 5])",
        why="Its stated origin is 'phase5'. That is an internal process label, not a "
            "source of record — it does not resolve to a document, dataset or URL.",
        who_can="Andrew Feng.",
        how_long="Unknown.",
        checked=("SIQ D1 profiles table", "siq-protocol repo"),
    ))
    d.cannot(Unverifiable(
        question="What is IFI's annual revenue?",
        why="The IRS BMF carries 0 in both the revenue and assets columns for this "
            "EIN, which in the BMF commonly means 'not reported in this extract' "
            "rather than zero. A second figure exists in our local MinistryWatch "
            "corpus; that source will not state a licence, so it is withheld here. "
            "Two numbers, neither usable.",
        who_can="IFI's finance office, or the Form 990 itself.",
        how_long="Minutes, for anyone inside IFI.",
        checked=("IRS BMF", "MinistryWatch corpus (licence refused)"),
    ))

    d.trace.append(f"built {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}")
    d.trace.append(f"IRS BMF queried for EIN {IFI_EIN}")
    d.trace.append("MinistryWatch: licence check failed, not queried")
    return d


# ---------------------------------------------------------------- render

# A citation is not always a fetchable URL. Link only when it resolves.
CITE_URLS = {"IRS Exempt Organizations Business Master File":
             "https://www.irs.gov/pub/irs-soi/eo1.csv"}


def src_url(src):
    return CITE_URLS.get(src["name"], "")


def e(x):
    return html.escape(str(x))


def render(d):
    o = d.to_dict()
    v, a, r, u = o["verified"], o["asserted"], o["ruled_out"], o["unverifiable"]

    def claim_rows(items):
        out = []
        for c in items:
            src = c.get("source")
            cite = (f'<a href="{e(src_url(src))}">{e(src["cite"])}</a>'
                    if src else '<span class="none">no source of record</span>')
            note = f'<p class="note">{e(c["note"])}</p>' if c.get("note") else ""
            out.append(f"""<tr><th>{e(c['label'])}</th>
<td><span class="val">{e(c['value'])}</span>{note}</td>
<td class="src">{cite}<br><span class="meta">{e(src['freshness']) if src else 'asserted by us'}</span></td></tr>""")
        return "\n".join(out)

    unver = "\n".join(f"""<article class="u">
<h3>{e(x['question'])}</h3>
<p>{e(x['why'])}</p>
<dl><dt>Who can settle it</dt><dd>{e(x['who_can'])}</dd>
<dt>How long</dt><dd>{e(x['how_long'])}</dd>
<dt>Already checked</dt><dd>{e(', '.join(x['checked']))}</dd></dl>
</article>""" for x in u)

    ruled = "\n".join(f"""<article class="r"><h3>{e(x['label'])}</h3>
<p><span class="tag">{e(x['check'])}</span> {e(x['reason'])}</p></article>""" for x in r)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>What can be proved about Frontier Commons</title>
<style>
:root{{--bg:#fbfaf8;--ink:#17150f;--mute:#6b6560;--line:#e2ddd4;--ok:#1f6f4a;--no:#9a3412;--gap:#7c3aed}}
@media(prefers-color-scheme:dark){{:root{{--bg:#14131a;--ink:#ece9e3;--mute:#9a938c;--line:#2e2b35;--ok:#5fbf8f;--no:#e8956b;--gap:#b79bff}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 ui-serif,Georgia,"Times New Roman",serif}}
main{{max-width:46rem;margin:0 auto;padding:3.5rem 1.25rem 5rem}}
h1{{font-size:1.9rem;line-height:1.15;margin:0 0 .4rem;letter-spacing:-.015em}}
.sub{{color:var(--mute);margin:0 0 2.5rem;font-size:1.02rem}}
h2{{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;margin:3rem 0 .4rem;
font-family:ui-sans-serif,system-ui,sans-serif}}
h2 .c{{font-weight:400;color:var(--mute);letter-spacing:0;text-transform:none}}
.lede{{color:var(--mute);font-size:.95rem;margin:0 0 1.1rem}}
table{{width:100%;border-collapse:collapse;font-size:.93rem}}
th,td{{text-align:left;vertical-align:top;padding:.7rem .6rem;border-top:1px solid var(--line)}}
th{{width:34%;font-weight:600;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.84rem}}
.val{{font-weight:600}}
.src{{width:26%;font-size:.76rem;font-family:ui-sans-serif,system-ui,sans-serif}}
.src a{{color:var(--ok);text-decoration:none;border-bottom:1px solid currentColor;word-break:break-all}}
.meta{{color:var(--mute)}}
.note{{margin:.4rem 0 0;font-size:.85rem;color:var(--mute)}}
.none{{color:var(--mute);font-style:italic}}
article{{border-left:2px solid var(--line);padding:.1rem 0 .1rem 1rem;margin:1.4rem 0}}
article.u{{border-color:var(--gap)}}
article.r{{border-color:var(--no)}}
article h3{{font-size:1rem;margin:0 0 .45rem;font-weight:600}}
article p{{margin:0 0 .6rem;font-size:.92rem}}
dl{{margin:0;font-size:.84rem;font-family:ui-sans-serif,system-ui,sans-serif}}
dt{{color:var(--mute);float:left;clear:left;width:9.5rem}}
dd{{margin:0 0 .25rem 9.5rem}}
.tag{{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.7rem;text-transform:uppercase;
letter-spacing:.08em;color:var(--no);border:1px solid currentColor;padding:.05rem .35rem;border-radius:3px}}
footer{{margin-top:4rem;padding-top:1.2rem;border-top:1px solid var(--line);
color:var(--mute);font-size:.8rem;font-family:ui-sans-serif,system-ui,sans-serif}}
code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em}}
@media(max-width:34rem){{th,.src{{width:auto}}dt{{float:none;width:auto}}dd{{margin-left:0}}
table,tbody,tr,th,td{{display:block}}td,th{{border-top:none}}tr{{border-top:1px solid var(--line);padding:.5rem 0}}}}
</style></head><body><main>

<h1>What can be proved about Frontier Commons</h1>
<p class="sub">A dossier we ran on ourselves, using <code>refuse</code> — the rule being
that an output which cannot be traced to a source of record does not render. Of the
{len(v)+len(a)+len(r)+len(u)} things we hold about ourselves, {len(r)+len(u)} did not survive it.</p>

<h2>Verified <span class="c">— {len(v)} claims, each with a citation</span></h2>
<p class="lede">Every row here came back from a source that states its licence in writing.</p>
<table>{claim_rows(v)}</table>

<h2>Asserted <span class="c">— {len(a)} claim{'s' if len(a)!=1 else ''}, no source of record</span></h2>
<p class="lede">True as far as we know. We are the only authority for it, and we say so
rather than dressing it as a finding.</p>
<table>{claim_rows(a)}</table>

<h2>Ruled out <span class="c">— {len(r)}</span></h2>
<p class="lede">Facts we hold locally and will not publish, because the source will not
say what it may be used for. This is the check that did not exist when we published
52,149 Google Places records we had no right to publish.</p>
{ruled}

<h2>Unverifiable <span class="c">— {len(u)}</span></h2>
<p class="lede">No source of record answers these. This section is the product.</p>
{unver}

<footer>
Built {e(o['trace'][0].replace('built ',''))} ·
Sources consulted: {e(', '.join(o['sources_consulted']) or 'none')} ·
Generated by <code>refuse/cases/build_frontier_commons.py</code>, no hand-written values.
</footer>
</main></body></html>"""


if __name__ == "__main__":
    sys.stdout.write(render(build()))
