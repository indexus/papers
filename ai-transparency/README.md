# Indexus: AI collaboration and selected source discussions

This archive shows how Remi Henriot worked with AI tools to develop Indexus.
It contains **18 annotated episodes and 35 verbatim excerpts** from **nine
conversation records**, spanning March 2025 to November 2026. The applications
represented are **ChatGPT, Codex, Claude Code, Antigravity and Cursor**.

For a straightforward account in French, start with
[Comment Rémi a travaillé avec les IA](PARCOURS.fr.md).
The [history paper](../60-history-and-authorship/indexus-history-and-authorship.pdf)
provides the broader chronology; [method and limits](METHOD.md) explain the sources.

## Read the exchanges, not just the retrospective

The selection includes the author's goals, requests for simpler explanations,
pressure to challenge tests, cross-tool reviews, corrections and an intermediate
failed reproduction. Each episode pairs the quotations with context, why the
step mattered, what it does not establish, and links to related papers.

Original spelling and language are retained. Dates on episode pages use
Europe/Paris, with the recorded UTC timestamp alongside each quote. Titles are
editorial topic labels. A human turn may contain a forwarded brief; it is not
all attributed to the human merely because it occupies a human message slot.

This is **a curated sample**, not a complete chat export, an independent
certification of priority or a percentage allocation of invention. The original
[2024 papers](../README.md) are primary evidence for the initial concepts.
An assistant's praise of the author's contribution is kept as a historical
statement, not used as proof.

## Catalogue

| Date | Tool | Episode |
| --- | --- | --- |
| 2025-03-18 | ChatGPT | [01. Ask for sources before accepting a description](episodes/01-ask-for-sources.md) |
| 2026-09-16 | Cursor | [02. The author sets the scaling objective](episodes/02-author-scale-objectives.md) |
| 2026-09-17 | Cursor | [03. A demand for a concrete explanation](episodes/03-demand-understandable-examples.md) |
| 2026-09-20 | Cursor | [04. Return to a simple placement rule](episodes/04-return-to-xor.md) |
| 2026-09-21 | Cursor | [05. Tests must challenge the implementation](episodes/05-challenge-the-tests.md) |
| 2026-11-14 | ChatGPT | [06. ChatGPT states the limit of its retrieved context](episodes/06-chatgpt-context-limit.md) |
| 2026-11-16 | Claude Code | [07. Claude Code records what it actually checked](episodes/07-claude-code-audit.md) |
| 2026-11-20 | Codex | [08. A checker could report success with missing results](episodes/08-checker-missing-results.md) |
| 2026-11-20 | Codex | [09. Stop publication when a reproduction check fails](episodes/09-stop-on-reproduction-failure.md) |
| 2026-11-21 | Codex | [10. The new vnode should help before the regional copy ends](episodes/10-granular-relief.md) |
| 2026-11-21 | Codex | [11. Revise an optimistic freeze estimate](episodes/11-revise-freeze-estimate.md) |
| 2026-11-21 | Antigravity | [12. Combine complementary work instead of benchmarking the wrong branch](episodes/12-cross-tool-integration.md) |
| 2026-11-21 | Antigravity | [13. Record why a performance fix was introduced](episodes/13-why-batch-and-bound.md) |
| 2026-11-21 | Antigravity | [14. Qualify remote elasticity incrementally](episodes/14-remote-tests-in-stages.md) |
| 2026-11-21 | Antigravity | [18. Attribution is checked against dated artifacts](episodes/18-attribution-is-not-a-vote.md) |
| 2026-11-22 | Antigravity | [15. Compare vector search at a fixed scan budget](episodes/15-fair-vector-comparison.md) |
| 2026-11-22 | Antigravity | [16. Preserve the original style and aim at independent implementations](episodes/16-style-and-standard.md) |
| 2026-11-22 | Antigravity | [17. The author catches visual defects and redirects the work](episodes/17-author-reviews-the-render.md) |

## Coverage of the located sources

| Application | Excerpts | What this sample actually covers |
| --- | ---: | --- |
| ChatGPT | 4 | An early request for sources and a later recap acknowledging its context limit. |
| Codex | 5 | A reproduction checker, an intermediate stopping decision, granular authority transfer and a corrected freeze estimate. |
| Claude Code | 2 | One located read-only fact-sheet audit, including its stated checking limits. |
| Antigravity | 16 | Cross-tool integration, reasons for performance fixes, staged remote testing, vector ablation design, paper direction and a hand-off for visual correction. |
| Cursor | 8 | Scaling goals, a demand for a concrete example, a return to the XOR rule and an explicit challenge to the tests. |

These tools are not interchangeable with model names. The archive does not
infer the model used for an unlabelled message. It also does not claim to have
recovered every Claude-assisted research discussion or a full ChatGPT data export.

## Reading the project alongside the discussions

- [Whitepaper](../10-whitepaper/indexus-whitepaper.pdf): the conceptual mechanism.
- [Client](../20-client/indexus-client.pdf): maps, search, composition and freshness.
- [Network](../30-network/indexus-network.pdf): installed authority and granular hand-over.
- [Properties and applications](../50-properties-and-applications/indexus-properties-and-applications.pdf): algebra, experiment scope, results and limits.
- [History and authorship](../60-history-and-authorship/indexus-history-and-authorship.pdf): roles and chronology.

The discussion excerpts describe historical steps. An old batch size, an early
scoring idea or an estimated freeze is not automatically the current contract.
Follow the paper's stated version and experiment scope when interpreting it.

## Integrity and continuation

[`excerpts.json`](excerpts.json) records source IDs, roles, timestamps, character
ranges and SHA-256 hashes. [`verify.py`](verify.py) checks the published strings
and can compare selected local records when those are available. A hash detects
a changed quotation; it does not independently attest authorship or date.

```sh
python3 ai-transparency/verify.py
python3 ai-transparency/verify.py --local-sources
```

Only selected user-visible text is published. Credentials, unrelated personal
or business material, tool payloads, attachments and private reasoning are
excluded. Broader transcript publication remains an extension of this initial
archive, as described in the history paper.

The editorial notes are licensed under CC BY 4.0, consistently with the papers.
Quoted passages retain their source attribution; this notice does not purport
to alter a source service's terms. Contact: **research@indexus.io**.
