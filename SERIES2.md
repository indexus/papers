# Indexus series, third version: concepts, then construction

Code: /home/claude/code/core (Go, branch main, read only) and /home/claude/code/sdk
(JavaScript client, read only). Docs: /home/claude/code/core/docs (some docs are
older than the code: when they disagree, the code wins, and say so in the notes).
The author's own 2024 papers: /home/claude/papers2/original/ (content to keep:
one binary tree for nodes, collections and records; BASE4 examples; incremental
nearby search; delegation; the feed as the motivating picture).

## Series

0. Manifesto (exists).
1. Whitepaper — "Indexus: A Peer-to-Peer Index of Exact Sums". The concepts,
   end to end, in the manner of the Bitcoin paper. Written by the lead.
2. Construction papers, one per part of the code base, each following the
   packages it describes:
   - C1 Addresses and plans: internal/tree, internal/protocol (+ sdk/src/tree
     for Spaces, masks, offsets, cells).
   - C2 Storage: internal/zonelog, internal/storage, internal/prep (bulk).
   - C3 Authority and network: internal/causal, internal/mesh, internal/auth,
     indexus (write/read routing, membership), internal/replication.
   - C4 Sums and reads: internal/summary, internal/wire, read/query paths in
     indexus, sdk/src (walk, store, wire, gpu, map).
3. Economics — proposal, no code (exists as draft; to be restyled).

## Style: the Bitcoin paper

- Numbered sections: "1. Introduction", "2. ...". Short. Each section opens
  with the problem it solves, in one or two sentences, then the mechanism.
- First person plural, plain declarative sentences, no adjectives of praise,
  no rhetorical questions, no marketing. Precise words, each defined the first
  time it is used and then never changed.
- Few figures, very simple: boxes, arrows, a small tree. Black on white.
  The author's original PNG figures (original/*/*.png) may be reused where the
  concept is unchanged.
- Formulas where they make a rule exact (owner(z) = argmin_v XOR(z, v)).
- One "Calculations" section when something can be computed (rounds of
  gossip, size of a proof, cost of a read, load balance), with a short worked
  computation or a few lines of code, as Bitcoin does for the attacker.
- Construction papers: for each part, concept first (what and why, a few
  lines), then construction: the data structures, the algorithm in short
  pseudocode, the rule it guarantees, and the package/file that implements it
  as a small footnote-like mention (e.g. "internal/zonelog"), never long code.
- 8 to 12 pages each. Numbered references [1], [2] at the end.
- English.
