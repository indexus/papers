# 09. Stop publication when a reproduction check fails

**Recorded date:** 2026-11-20 13:18 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** A subsequent check reports disagreement. The assistant stops rather than rewriting the original analysis to force a pass.

## Assistant reply

> Le contrôle final n’atteint pas « 0 écart ». Les comparaisons de prédictions dans `zonelog` donnent bien 100 % d’accord, mais les comptes d’égalité au bit près avec la référence ont changé, et plusieurs scores dépassent la tolérance prévue. Je m’arrête donc avant reconstruction et dépôt. Je prépare le diagnostic sans modifier les analyses ni les résultats d’origine.

Source: **Codex**, conversation `01a1f8b7-25c6-73a1-ae0c-d4f14496f840`, message `msg_00cf5ef70fb40784016b003a97ea7c87d292fc47535b6bd252`, 2026-11-20T12:18:32.005000+00:00. Excerpt `X016` in [the manifest](../excerpts.json).

## Why this mattered

The workflow includes negative results and a stopping decision. Prediction agreement, bitwise equality and tolerance-based numerical comparison are treated as different checks.

## What this does not establish

This is an intermediate failed check, not the final publication verdict. Later reproduction claims have their own scope in the properties paper and the Zenodo archive. No private access or storage details from the surrounding conversation are included.

## Related papers

[Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf); [Development History and Authorship](../../60-history-and-authorship/indexus-history-and-authorship.pdf).

[Back to the archive](../README.md).
