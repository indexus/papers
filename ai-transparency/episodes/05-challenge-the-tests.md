# 05. Tests must challenge the implementation

**Recorded date:** 2026-09-21 21:21 CEST (Europe/Paris). Original UTC timestamps are retained below.

**Context.** The author explicitly asks whether the tests objectively establish the promised guarantees.

## Human request

> Challenge les tests et reverifie que les tests sont valides et pas seulement la pour arrnager les resultats. Regarde s'ils sont objectifs, prend ton temps

Source: **Cursor**, conversation `78146794-5463-497f-af6f-9736cf727828`, message `daf44b80-3b8b-4e3d-8176-b2a679fc08fe`, 2026-09-21T19:21:52.922Z. Excerpt `X009` in [the manifest](../excerpts.json).

## Assistant reply

> Je vais relire les tests ajoutés contre le code qu’ils appellent, pour voir lesquels prouvent vraiment l’invariant et lesquels ne font que confirmer le chemin déjà écrit.

Source: **Cursor**, conversation `78146794-5463-497f-af6f-9736cf727828`, message `e5146c3a-cae3-42b7-bff4-1f6b315dc9a2`, 2026-09-21T19:21:59.780Z. Excerpt `X010` in [the manifest](../excerpts.json).

## Why this mattered

The assistant is asked to compare tests against the code path they exercise, rather than treating passing tests as sufficient evidence.

## What this does not establish

The quoted reply is a commitment to review. Its success requires the resulting tests, reports and source changes; the message alone proves no invariant.

## Related papers

[The Network](../../30-network/indexus-network.pdf); [Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf); [Development History and Authorship](../../60-history-and-authorship/indexus-history-and-authorship.pdf).

[Back to the archive](../README.md).
