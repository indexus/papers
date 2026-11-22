# Indexus papers

Indexus uses one binary tree for nodes, collections, zones and records. The
papers explain the original idea, its current implementation, measured results
and proposals. They are written in English by Remi Henriot and licensed under
**Creative Commons Attribution 4.0 International (CC BY 4.0)**.

Contact: **research@indexus.io**.

The goal is an **open protocol standard**: addressing, self-certifying `IXC1`
collection descriptors, `IXB2` / `IXRB` wire blocks, authority certificates and
conformance vectors that independent implementations can share.

## Reading order

Start with the manifesto for the motivation, then the whitepaper for one
end-to-end example. The client and network papers explain each side of that
example. The properties paper gives the algebra, experiments and applications;
the history paper records what changed and how the work was carried out.

| Paper | Read | Source |
| --- | --- | --- |
| 0. Data as a Commons | [Manifesto](00-manifesto/indexus-manifesto.pdf) | [LaTeX](00-manifesto/indexus-manifesto.tex) |
| 1. A Peer-to-Peer Data Indexing System | [Whitepaper](10-whitepaper/indexus-whitepaper.pdf) | [LaTeX](10-whitepaper/indexus-whitepaper.tex) |
| 2. The Client | [PDF](20-client/indexus-client.pdf) | [LaTeX](20-client/indexus-client.tex) |
| 3. The Network | [PDF](30-network/indexus-network.pdf) | [LaTeX](30-network/indexus-network.tex) |
| 4. Paying for Open Data | [Economics proposal](40-economics/indexus-4-economics.pdf) | [LaTeX](40-economics/indexus-4-economics.tex) |
| 5. Properties, Benchmarks, and Directions | [PDF](50-properties-and-applications/indexus-properties-and-applications.pdf) | [LaTeX](50-properties-and-applications/indexus-properties-and-applications.tex) |
| 6. Development History, Authorship, and Human–AI Collaboration | [PDF](60-history-and-authorship/indexus-history-and-authorship.pdf) | [LaTeX](60-history-and-authorship/indexus-history-and-authorship.tex) |

The two 2024 articles remain in `client-algorithm/` and `p2p-protocol/` at the
repository root, with their existing history and original figures. Their terms
*sets* and *items* became *zones* and *records*. The newer papers explicitly
compare that starting point with durable authority, granular hand-over,
versioned monoid summaries and optional replication. The original sources are
archives, not current implementation specifications.

## What is established

The cluster results, local fault tests, single-node application experiments and
research hypotheses have separate scopes. In particular:

- New vnodes serve installed lots before a whole region finishes copying.
  First service, each lot's pause and complete join are distinct measurements.
  The residual-region fence is described; a universal freeze bound is not claimed.
- Single-writer authority applies to the normal write path. Optional degraded
  fallback accepts concurrent record versions with deterministic reconciliation.
- An exact aggregate of received child versions can still lag a remote write.
  Arithmetic precision, propagation delay and cache freshness are separate.
- AWS results are kept with their original workload and audit scope. Optional
  replicated runtime tests at core snapshot `d689156` (22 November 2026) are
  local durable-store tests, not a replicated AWS fault campaign.
- Economics, verifiable aggregates and the proposed standard remain proposals.

The properties paper retains the SPFresh/LIRE 1M results, SIGReg/Epps–Pulley
formulas and continual-learning reproduction archive, DOI
[10.5281/zenodo.24404468](https://doi.org/10.5281/zenodo.24404468).

## Build and check

Install Python 3 and [Tectonic](https://tectonic-typesetting.github.io/). From the
repository root, or using an absolute path to the script:

```sh
python3 build.py
python3 build.py --check --legacy
```

The script regenerates every current figure and compiles all seven current
papers. `--check` verifies that figure generation does not change checked-in
TikZiT sources. Both modes reject compilation errors, unresolved references and
overfull boxes larger than 2 pt. `--legacy` also compiles the two historical
papers into temporary directories, leaving their archived PDFs unchanged.

Tectonic downloads its packages on first use, then reuses its cache. Generated
PDFs are versioned; auxiliary files and logs are ignored. A single paper can be
rebuilt with, for example:

```sh
tectonic 30-network/indexus-network.tex
```

`10-whitepaper/make_figures.py` also regenerates the shared network figures and
the client's sums example. The other generators resolve paths relative to their
own files, so no original author's machine path is required.

## Figures and editorial history

[Figure conventions](figkit/FIGURES.md) document the original black/grey TikZiT
vocabulary. Historical drawings are included as vectors without changing their
geometry. New figures use a common scale, tiny labels, plain boxes and thin
arrows. All current papers share `common/indexus.sty`: margins, title blocks,
section hierarchy, table spacing and typography.

[SERIES2.md](SERIES2.md) and `notes/` preserve earlier plans and construction
notes. They explain the development history; the reading table above identifies
the current papers and titles. The former H1/H2 labels are kept as outline
provenance, while the measured campaigns retain their November dates.

The 22 November 2026 revision adds worked examples before formal definitions,
progressive hand-over diagrams, an insert/delete learning diagram and a common
visual treatment of the manifesto and economics. See [the verification record](VERIFICATION.md)
for the build and page-review checks.
