# 08. A checker could report success with missing results

**Recorded date:** 2026-11-20 12:32 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** While preparing reproduction, Codex identifies a check that accepts absent recalculated outputs.

## Assistant reply

> J’ai trouvé un défaut dans `check.py` : il annonce « 0 écart » même quand tous les résultats recalculés sont absents. Je vais corriger ce contrôle dans la copie extraite. Le script doit aussi reproduire les 4 000 étapes présentes dans le résultat BGE d’origine, au lieu des 400 prévues actuellement. Les analyses restent inchangées.

Source: **Codex**, conversation `01a1f8b7-25c6-73a1-ae0c-d4f14496f840`, message `msg_00cf5ef70fb40784016b002fcbbca887d299dcc546c7ffe4ae`, 2026-11-20T11:32:27.687000+00:00. Excerpt `X015` in [the manifest](../excerpts.json).

## Why this mattered

Finding and fixing a false-positive verifier is distinct from improving the numerical result. It makes later success claims more demanding, not easier.

## What this does not establish

This is a reported intermediate defect and intended correction. It is not evidence of a successful reproduction by itself. The published study and its final comparison scope are separate sources.

## Related papers

[Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf); [Development History and Authorship](../../60-history-and-authorship/indexus-history-and-authorship.pdf).

[Back to the archive](../README.md).
