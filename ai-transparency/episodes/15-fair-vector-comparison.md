# 15. Compare vector search at a fixed scan budget

**Recorded date:** 2026-11-22 09:08 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** The author asks whether a prototype can match or improve strong alternatives, in a separate worktree.

## Human request

> J'aimerai commencer a faire des tests pour voir si sur SPfresh on peut avoir des resultats equivalent que les meilleurs ou meme meilleur, ce serait un vrai plus. Pren ton temps et fait sur un worktree diffrement

Source: **Antigravity**, conversation `7c7ff249-3d7c-4daa-86e3-745fb41f3dec`, message `32`, 2026-11-22T08:08:19.661594+00:00. Excerpt `X028` in [the manifest](../excerpts.json).

## Assistant reply

> qui compare à **budget exact de vecteurs scannés** (0,5 %, 1 %, 2 %, 4 % des vecteurs vivants) face à **IVF statique**, en testant 6 leviers tous 100 % compatibles avec les colonnes `sum` d'Indexus et la règle d'adressage `growDown` :

Source: **Antigravity**, conversation `7c7ff249-3d7c-4daa-86e3-745fb41f3dec`, message `64`, 2026-11-22T08:12:14.626804+00:00. Excerpt `X029` in [the manifest](../excerpts.json).

## Why this mattered

The assistant turns a broad research direction into an ablation study with a fixed resource budget and a static-IVF comparator. The author supplies the research question and asks for an isolated experiment.

## What this does not establish

The excerpt describes the experiment being set up. It is not the final recall table, and early scoring ideas are not automatically the final winning configuration. Read the dated application results in the properties paper.

## Related papers

[Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf); [Development History and Authorship](../../60-history-and-authorship/indexus-history-and-authorship.pdf).

[Back to the archive](../README.md).
