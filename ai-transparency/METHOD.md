# Method, provenance and limits

## What is being published

This archive is an editorial selection of **user-visible discussion excerpts**
about Indexus. It is not a dump of account history. The quotes retain their
original language, spelling and punctuation. The JSON manifest is the exact
character-level quotation; Markdown rendering normalizes trailing whitespace. Explanatory prose outside the
block quotes was written for this archive on 22 November 2026.

The catalogue has 18 episodes and 35 excerpts from nine conversation records.
Some episodes contain several excerpts from one message. Topic titles are
editorial labels; source conversation IDs and message IDs identify the records.
Dates displayed on episode pages use Europe/Paris. The machine manifest keeps
the recorded UTC timestamps. These are application records, not independently
signed timestamps. ChatGPT supplied turn-level start times, not a separate
assistant-message time; that basis is explicit in the manifest. Other sources
retain their item, bubble, message or step creation timestamps.

## Retrieval and selection

| Source | Record used | Included text | Limits |
| --- | --- | --- | --- |
| ChatGPT | Connected app history, selected conversations | Human requests and returned assistant text | One returned recap is truncated; the quoted passage is inside the returned window. A retrospective recap is not direct access to Codex or the repository. |
| Codex | Local projected conversation history | `userMessage` and `agentMessage` text | Selected historical records; no claim that the projection contains all later turns. |
| Claude Code | Located Indexus JSONL session | User content and assistant blocks of type `text` | The located session is a read-only audit. It does not substantiate every Claude-assisted implementation or research step. |
| Cursor | Project-scoped conversation headers and message records | Human message text and visible assistant `text` | The selected parent conversations are not subagent task prompts. System notifications, thinking blocks, tools and attachments are excluded. |
| Antigravity | Local conversation SQLite records | User-input text and final/visible response text | Read-only base-database snapshots were used; live WAL updates are not included. The extractor distinguishes visible response text from separate reasoning and tool fields. |

Platform names identify the application, not necessarily the model. A model can
be used through several applications. Model identity is therefore not inferred
from writing style, a conversation title or a retrospective claim. The Claude
Code messages retain their recorded model label where available; that label is
metadata, not independent identity attestation.

For Antigravity, the selected SQLite rows use step type 14, payload field
`19.2` for the human input, and step type 15, payload field `20.1` for the
visible response. The separate response field `20.3` is **not** exported;
neither are tool fields or generated reasoning. The small verification reader
only accesses the selected text fields. This is a documented local format
observation, not a vendor-supported export specification.

## What a quote establishes

A quote can show that a goal was requested, a mechanism proposed, a limitation
acknowledged or an experiment reported. It does not by itself establish that
code ran, that a benchmark was fair or that a mathematical claim is true.

Episode annotations therefore separate:

1. the human request or forwarded brief;
2. the assistant's user-facing contribution;
3. the editorial explanation of why the step mattered;
4. the checks or artifacts needed to substantiate a result;
5. the limits and current relevance of the historical wording.

A human turn can contain a copied analysis from another tool. Only the direct
request is treated as the author's wording unless another provenance is
explicitly stated. Conversely, the assistant's favorable opinion about the
author's contribution is not an independent authorship assessment.

The preserved [2024 papers](../README.md) are stronger primary records of the
original concepts than a later model's praise. Concrete later requests and code
history help show how the work evolved. Message counts, line counts and hashes
do not quantify a percentage of invention or replace that comparison.

## Omissions

Only selected project-related text is included. Credentials, private operational
information, unrelated personal or business discussions, raw tool payloads,
attachments and private reasoning are not published. Surrounding text can be
omitted by selecting a contiguous passage; no deletion is concealed inside a
quoted passage. Each passage records its character offsets in the retrieved
source text. Quotes from the same message are separate records when needed.

The selection includes corrections, a false-positive checker, an intermediate
reproduction failure and an estimate revised after further code inspection.
It remains a selection, with editorial bias and incomplete coverage. No complete
ChatGPT data export or full archive of every Claude-assisted research session
was used. The index is an initial contribution to the broader transcript
publication promised in the history paper.

## Integrity and verification

[`excerpts.json`](excerpts.json) contains the quoted text, source IDs, role,
recorded timestamp, character range, SHA-256 of the retrieved source text and
SHA-256 of the excerpt. A truncated retrieval is explicitly marked. The source
hash commits to the **retrieved text window**, not to an unavailable full chat.
A hash detects a changed quotation; it does not independently prove who wrote
it or when.

```sh
# Portable: verify the published excerpts and catalogue consistency.
python3 ai-transparency/verify.py

# On the author's machine: also compare against the selected local records.
python3 ai-transparency/verify.py --local-sources

# Optional: compare ChatGPT entries against a saved read_thread capture.
python3 ai-transparency/verify.py --local-sources --chatgpt-capture /path/to/capture.json
```

The optional capture is a JSON list of conversation records containing `id`
and `turns`, as returned by the connected history reader. It is kept outside the
repository. The verifier prints counts and source IDs on failure, never source
message bodies. Missing local applications or unavailable source records are
reported as unavailable, rather than silently treated as a match.
