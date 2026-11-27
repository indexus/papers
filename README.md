# Indexus papers

**Distributed Prefix Index Protocol (DPIP)** is the proposed standard. Indexus
is the brand and the project that originated its specification. In French:
*protocole d’indexation distribuée par préfixes*. Peers share responsibility for
the index. Within a collection, extending a location prefix takes a reader from
one zone to a more detailed view.

The seven 2026 papers carry the credit **Rémi Henriot · AI Co-authored**. Each
closes with a contribution note. The [development history](60-history-and-authorship/indexus-history-and-authorship.pdf#nameddest=ix:ai)
dates the documented work with OpenAI, Anthropic’s Claude, Cursor and Antigravity.
Rémi Henriot wrote the two 2024 papers. The papers are licensed under
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
The economics paper uses a map to explain a proposed way to pay hosts and
producers. Its worked prices are illustrative.

| Paper | Read | Source |
| --- | --- | --- |
| 0. Data as a Commons | [Manifesto](00-manifesto/indexus-manifesto.pdf) | [LaTeX](00-manifesto/indexus-manifesto.tex) |
| 1. Distributed Prefix Index Protocol (DPIP) — Multiscale Aggregation over a Peer-to-Peer Index | [Whitepaper](10-whitepaper/indexus-whitepaper.pdf) | [LaTeX](10-whitepaper/indexus-whitepaper.tex) |
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

[Watch the archived layer search](https://indexus.io/papers/animations/search-algorithm.gif) · [Provenance and licence](animations/README.md)

## How the papers connect

Companion-paper names and bibliography entries in the PDFs are clickable.
Selected links go to stable named sections, such as authority, granular hand-over,
summary freshness and benchmark definitions. For offline reading, keep the
repository's neighboring PDF folders together.

| Question | Start here | Then read |
| --- | --- | --- |
| Why a shared index? | [Manifesto](00-manifesto/indexus-manifesto.pdf) | [Whitepaper](10-whitepaper/indexus-whitepaper.pdf) |
| How do maps and feeds read it? | [Client](20-client/indexus-client.pdf) | [Network summaries](30-network/indexus-network.pdf#nameddest=ix:summaries) |
| How can parent and child address the same peer? | [Whitepaper, collection](10-whitepaper/indexus-whitepaper.pdf#nameddest=ix:collection) | [Network](30-network/indexus-network.pdf) |
| How do collections meet across coordinate systems? | [Client, combining collections](20-client/indexus-client.pdf#nameddest=ix:composition) | [Anglet, sales and weather](50-properties-and-applications/indexus-properties-and-applications.pdf#nameddest=ix:anglet) |
| Where did the search algorithm come from? | [History, Ocurz and the prototypes](60-history-and-authorship/indexus-history-and-authorship.pdf#nameddest=ix:chronology) | [Rémi's retrospective](https://remi.news/articles/2024-08-07-the-beginnings-of-the-protocol/) |
| When may a new vnode accept writes? | [Network hand-over](30-network/indexus-network.pdf#nameddest=ix:handoff) | [Properties and measurements](50-properties-and-applications/indexus-properties-and-applications.pdf#nameddest=ix:benchmarks) |
| Did adding a vnode relieve its machine? | [AWS placement experiment](50-properties-and-applications/indexus-properties-and-applications.pdf#nameddest=ix:elasticity) | [Run record, traces and replay](https://github.com/indexus/core/blob/e4b9072/docs/benchmarks/aws-placement-100-20261127/granular50/aws-pair.md) |
| What is implemented versus proposed? | [Properties and limits](50-properties-and-applications/indexus-properties-and-applications.pdf#nameddest=ix:limits) | [Economics](40-economics/indexus-4-economics.pdf) |
| What did the author and AI tools each do? | [History](60-history-and-authorship/indexus-history-and-authorship.pdf) | [Selected discussion archive](ai-transparency/README.md) |

## AI collaboration and source discussions

The [transparency archive](ai-transparency/README.md) contains **18 annotated
episodes and 35 exact excerpts**, covering ChatGPT, Codex, Claude Code,
Antigravity and Cursor. It includes requests, corrections, failed checks and
cross-tool hand-offs. This is a curated sample, not a complete set of logs or
an independent certification of authorship.

For a simple account in French of how the author worked, read
[Parcours de travail avec les IA](ai-transparency/PARCOURS.fr.md).
[Method and limits](ai-transparency/METHOD.md) distinguish original requests,
forwarded text, assistant claims and checks against other artifacts.

## What is established

The cluster results, local fault tests, single-node application experiments and
research hypotheses have separate scopes. In particular:

- New vnodes serve installed lots before a whole region finishes copying.
  First service, each lot's pause and complete join are distinct measurements.
  The residual-region fence is described; a universal freeze bound is not claimed.
- The current protocol transfers authority between the donor and the receiver
  using durable tickets. A routing hint can shorten a later write to the same
  zone. Only the installed owner can acknowledge an ordinary write.
- Replica logs, degraded reads and peer repair have local runtime evidence.
  The reference write path currently has no producer of fallback writes.
- Refreshed normal reads capture page data and required receivers together
  (`core` commit `6a3015e`), returning an explicit error if coverage is unavailable.
  This is not a global snapshot of concurrent writes.
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

For a structural check of compiled PDF destinations and local Markdown links,
install the optional `pypdf` package and run `python3 check_links.py` after the
build. The check covers actual remote-PDF actions and named sections.

For the time series in the elasticity section, the [dated AWS report](https://github.com/indexus/core/blob/e4b9072/docs/benchmarks/aws-placement-100-20261127/granular50/aws-pair.md)
links the two anonymized traces. The [extractor](50-properties-and-applications/data/extract_service.py)
counts each donor–target pair once at its first request and once when a
confirmed receiver has written. The figure reads a [local copy of the 10-second series](50-properties-and-applications/data/service-a.csv),
so rebuilding the diagrams requires no access to AWS.

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

The 24 November review documented the separation of writes from the older
Knowledge mechanism. Subsequent commits introduced the local ticket hand-off.
On 27 November two independent AWS fleets exercised the same sequence of
writes with different placement retry policies. The properties paper reports
time to first service, physical host relief and the scope of the final audit.
The history paper explains why the immediate-retry policy was retained. The
[verification record](VERIFICATION.md) preserves the dated editorial checks.
