# 10. The new vnode should help before the regional copy ends

**Recorded date:** 2026-11-21 13:43 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** The author states the desired authority movement and asks to simplify an unstable scaling path.

## Human request

> C'est la partie sur les blocages de splits qui m'interesse et la strategie d'elasticité qui a été ajouté, le scale n'est pas encore stable, et la partie transferts. Je veux revenir a un etat plus simple et stable. Le but c'est que le transfert decale des zones l'autorité le plus vite possible pour eviter des gros freezes, on veut decaler les zones granulairement le plus vite possible pour que le nouveau vnode prenne la responsabilité des sous zones et commence a recevoir les ecritures

Source: **Codex**, conversation `01a1fe13-7fde-79a3-bb8a-e51bfa026f3b`, message `01a1fe21-d7f0-77d0-8b21-7bdb55e1ce8d`, 2026-11-21T12:43:13.270000+00:00. Excerpt `X017` in [the manifest](../excerpts.json).

## Assistant reply

> **Oui. L’objectif devrait être : le nouveau vnode commence à absorber les écritures dès les premières zones transférées, pendant que les autres continuent à vivre sur le donneur.**

Source: **Codex**, conversation `01a1fe13-7fde-79a3-bb8a-e51bfa026f3b`, message `msg_0070f0ef72e9f4f0016b019205859487d29a8df6c5a301cdcb`, 2026-11-21T12:43:49.456000+00:00. Excerpt `X018` in [the manifest](../excerpts.json).

## Why this mattered

The author supplies the performance goal and the authority constraint. The assistant maps that goal to per-lot activation while the donor keeps serving the remaining zones.

## What this does not establish

The exchange records intent and diagnosis. Earlier 512-zone proposals are historical candidates; the later integrated planner uses the smaller lot limits documented in the papers. No universal freeze bound follows from the quote.

## Related papers

[The Network](../../30-network/indexus-network.pdf); [Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf).

[Back to the archive](../README.md).
