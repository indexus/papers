# 12. Combine complementary work instead of benchmarking the wrong branch

**Recorded date:** 2026-11-21 14:49 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** The author brings two ongoing worktrees to another tool for review before unification.

## Human request

> J'aimerai que tu regardes le projet indexus et 2 worktree core en cours. Voici ce que l'on veut faire donne ton avis:

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `0`, 2026-11-21T13:49:59.299726+00:00. Excerpt `X020` in [the manifest](../excerpts.json).

## Assistant reply

> **En revanche, point critique avant de lancer la suite (section 7)** : les deux worktrees `core` actifs aujourd'hui résolvent en parallèle **deux moitiés complémentaires du même problème**, et lancer la qualification 16 → 32 → 64 vnodes directement sur `codex/granular-handoff` vous ferait retomber sur des goulots et bugs déjà résolus dans `feat/convergent-replication`.

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `45`, 2026-11-21T13:59:29.103567+00:00. Excerpt `X021` in [the manifest](../excerpts.json).

## Human request

> Propose une unification dans main en laissant granular handoff continuer de son coté s'il te plait et regarde bien proprement si le resultat est bon et meilleur s'il te plait - prend ton temps, fais le propermetn

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `46`, 2026-11-21T14:19:09.562347+00:00. Excerpt `X022` in [the manifest](../excerpts.json).

## Why this mattered

The author moves context between tools, asks for comparison, and authorizes a controlled unification. The assistant points out that each branch solves a different part of the problem.

## What this does not establish

A branch comparison is not proof that all changes compose safely. The later tests, commit history and workload definitions are needed. The pasted brief inside the human turn is not attributed wholesale to the author.

## Related papers

[The Network](../../30-network/indexus-network.pdf); [Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf); [Development History and Authorship](../../60-history-and-authorship/indexus-history-and-authorship.pdf).

[Back to the archive](../README.md).
