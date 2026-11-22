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
| History and authorship | 5 | 0 | 0 |
| Historical search article | 10 | 0 | 0 |
| Historical protocol article | 6 | 0 | 0 |

All current cross-references resolve. Some TeX packages emit cache/encoding
warnings, and a paragraph in the history paper has an underfull-box warning;
these are distinct from overflows or compilation errors.

## Visual and content review

All 57 pages of the current series were rendered at 150 dpi and reviewed,
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
