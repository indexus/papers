# Series verification — 27 November 2026

This edition uses the 24 November working sources and compares the protocol
with core `e4b9072`. The earlier verification entries below describe the
snapshots available to their respective reviewers. For example, the former
uncommitted read and route changes later became `b2d3dea` and `bfb8432`.

| Current paper | Pages | Main subject of this revision |
| --- | ---: | --- |
| Manifesto | 4 | Motivation, principles and the status of proposals |
| Whitepaper | 10 | One listing from encoding through transfer to a map |
| Client | 7 | Cache, summary propagation and a fresh read after an ACK |
| Network | 10 | Local tickets, per-lot installation, routes and failure recovery |
| Economics | 9 | Worked pricing example, cost of service and the scope of the proposal |
| Properties and applications | 16 | Dated authority models, paired AWS trials, host relief and audit coverage |
| History and authorship | 6 | From the original XOR drawings to a documented placement decision |

All 62 pages were inspected from renders at 150 dpi. The seven current
papers and both 2024 source archives compile with Tectonic and reproducibly
generated current TikZiT sources. The logs report zero overfull horizontal
boxes and zero unresolved references. The dedicated PDF check found 32 local
actions, 73 companion actions and 175 local Markdown targets. The seven
distinct pinned paths into the core repository also resolve in that checkout.

The 2024 source trees and original drawings match the saved edition byte for
byte. The discussion archive passes its internal integrity check for 35
excerpts in 18 episodes. This checks the published text and identifiers.

The service curve in paper 5 was regenerated directly from the anonymized
AWS trace; its final point counts 316 donor–target pairs requested and 152
with an observed receiver write. Paper 5 gives the deadline denominators,
traffic-share definition, one trial per policy and limits of the key audits.
The experiment predates this editorial pass.

---

# Series verification — 22 November 2026

This revision covers all seven current papers. The two 2024 articles remain
historical archives; their tracked sources, figures and PDFs are unchanged.

## Build

The full series and both archives compile with Tectonic. Current figures are
regenerated with the local Python generators; a further generation produces
identical `.tikz` files. The build script can be invoked from any directory.

```sh
python3 build.py --check --legacy
```

| Paper | Pages | TeX errors | Overfull hboxes |
| --- | ---: | ---: | ---: |
| Manifesto | 4 | 0 | 0 |
| Whitepaper | 10 | 0 | 0 |
| Client | 7 | 0 | 0 |
| Network | 9 | 0 | 0 |
| Economics | 9 | 0 | 0 |
| Properties and applications | 13 | 0 | 0 |
| History and authorship | 6 | 0 | 0 |
| Historical search article | 10 | 0 | 0 |
| Historical protocol article | 6 | 0 | 0 |

All current cross-references resolve. Some TeX packages emit cache/encoding
warnings, and a paragraph in the history paper has an underfull-box warning;
these are distinct from overflows or compilation errors.

## Visual and content review

All 58 pages of the current series were rendered at 150 dpi and reviewed,
including the title blocks, tables, captions, equations and section transitions.
The 16 historical pages were also rendered and reviewed for comparison. Detailed
figure crops were checked where labels, routes or box boundaries needed revision.

The current PDFs have vector diagrams throughout, without embedded raster images.
The original TikZiT coordinates and `figkit` vocabulary are preserved. New
figures use the common 0.62 cm/unit scale. Automated text-bound checks find no
words outside the page margins. Plain diagram boxes were checked for text
padding; arrow labels were reviewed visually. Generated PDFs and sources are
published together.

The displayed equations, benchmark figures, continual-learning DOI
`10.5281/zenodo.24404468`, SPFresh/LIRE 1M measurements and SIGReg/Epps–Pulley
material are retained. Mathematical definitions and worked examples explain
those statements before their formal treatment. Model-family restrictions,
arithmetic precision and experimental scopes remain explicit.

Historical outline titles and H1/H2 phase labels are recorded as provenance,
rather than presented as the current table of contents or execution dates.
Optional replication is dated against core snapshot `d689156`; its local runtime
checks are distinguished from the earlier AWS measurements. This editorial
pass does not constitute a new distributed benchmark or a new proof.

## Clarifications made during alignment

- Routing predicts a destination; installed authority permits a commit.
- Installed lots serve traffic before the complete join. Copy time, lot pause
  and join completion are separate, and residual region fencing remains visible.
- Normal authority and degraded concurrent fallback have different write contracts.
- An exact aggregate of received versions may lag remote writes; a cache can add
  another delay. Exact arithmetic and floating-point agreement are distinguished.
- The economics diagram pads four children for illustration. Current reads omit
  empty children and may include direct records, for a maximum of 65 rows.
- Payment receipts do not prove aggregate correctness. Pricing, verification and
  governance remain proposals.
- The shared style, figure generators and reading guide replace machine-specific
  build paths, while the original plans remain in the historical notes.

All papers retain CC BY 4.0, `research@indexus.io`, and the goal of an open
protocol standard with independent implementations and shared conformance tests.

## Companion links and discussion archive

The added links were checked as compiled PDF actions, including both ordinary
companion-file links and named section destinations. The check distinguishes
PDF remote destinations from browser `nameddest=` URL fragments. Local citation
numbers now link to their bibliography entries, whose companion-paper titles
link to the corresponding PDFs.

`check_links.py` reports 31 local PDF actions, 59 companion PDF actions and
172 local Markdown targets resolved for this revision. It requires the optional
`pypdf` package and does not fetch external websites.

The side archive contains 18 annotated episodes and 35 verbatim excerpts from
nine ChatGPT, Codex, Claude Code, Antigravity and Cursor conversation records.
All 35 passages were compared against the retrieved source text, including
record hashes and character ranges: 35 matches, zero unavailable records and
zero mismatches in the author's verification run. ChatGPT comparison used a
private saved history capture; no raw account dump is part of the repository.
The verifier also rejects an empty evidence collection.

Each episode distinguishes the request, the assistant reply, its relevance and
its evidential limit. A French reading guide explains the workflow. Coverage,
forwarded text, intermediate failures, timestamp bases and selection limits are
recorded explicitly. The hashes protect quotation integrity rather than
independently attesting authorship or date. No new distributed benchmark is
claimed by publishing these excerpts.

## Guarantee review — 24 November 2026

The current series was compared with core `6a3015e`, the earlier Knowledge
changes and the locally tested SUM-4 working-copy correction. That correction
had no separate commit at review time. The earlier verification records above
remain historical records, not retroactive claims about this revision.

This pass distinguishes normal single-writer authority, refreshed inventory
coverage, derived-summary consistency and freshness. Page data and required
receivers share a snapshot (READ-1); local sum corrections share a version
(SUM-4). Neither establishes a global instantaneous snapshot. Compact writes
and prepared cutovers avoid synchronous global Knowledge transport. A timed-out
control follower may still send a second full bundle. Adaptive lots start at
64 zones; 150 ms is a target, not a freeze deadline. Early receiver service,
direct-route learning and completion of the join remain separate events.

All seven current papers and both historical archives compile with
`python3 build.py --check --legacy`: zero errors, zero overfull hboxes and no
unresolved references. Figure regeneration is reproducible. The new Knowledge
and inventory-coverage figures use the existing vector TikZiT vocabulary.

| Current paper | Pages |
| --- | ---: |
| 00-manifesto | 4 |
| 10-whitepaper | 10 |
| 20-client | 7 |
| 30-network | 11 |
| 40-economics | 9 |
| 50-properties-and-applications | 14 |
| 60-history-and-authorship | 6 |

All 61 current pages were rendered at 150 dpi and inspected on contact sheets;
new figures and changed arithmetic paragraphs were checked at full-page scale.
The page-bound safety check found no text within the outer 20 pt border.
Local core documentation/architecture checks passed. `check_links.py` reports
31 local PDF actions, 63 companion actions and 172 Markdown targets valid.

The properties paper's benchmark section and all subsequent material, including
SPFresh/LIRE, SIGReg/Epps--Pulley, the unlearning DOI, equations and references,
are byte-identical in source to the preceding revision. The two 2024 source
archives, PDFs and original figures are unchanged. No new AWS experiment,
replicated-cluster validation, universal freeze bound or formal proof is claimed.

### Concurrent local update observed during the review

The working copy subsequently added WRITE-HINT-1: a shared, bounded exact-zone
cache at the entry service, plus derived-total store reads outside the summary
lock. These remain local uncommitted changes, not part of `6a3015e`. The network,
properties and history papers were updated accordingly. The reported three-run
local routing comparison is not treated as statistical evidence of better p99.

The entry-hint and source-inventory-cut tests passed five repetitions with
`-race`; the root collection-cut, bulk join and continuous-read tests passed one
additional combined `-race` run. Earlier full-suite qualification is retained
with its earlier scope, not attributed to every concurrent edit. The final
seven-paper build, link checks and 61-page rendering were repeated after this
editorial update.
