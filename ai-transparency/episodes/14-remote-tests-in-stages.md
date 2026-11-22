# 14. Qualify remote elasticity incrementally

**Recorded date:** 2026-11-21 16:47 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** The author asks for real-machine validation with an explicit experiment budget.

## Human request

> Essaie de deployer et test sur aws cli a cout moins de 20 doll s'il teplait, de facon incremental pour verifier ce que l'on souhaite.

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `378`, 2026-11-21T15:47:33.087363+00:00. Excerpt `X026` in [the manifest](../excerpts.json).

## Assistant reply

> 2. **Étape 2 (si Étape 1 verte)** : **Élasticité réelle multi-machines** (`RAMP_ELASTIC=1`, `RAMP_DOUBLES="120 60"`, 4 → jusqu'à 12 `i4i.xlarge` NVMe dédiés, `BUDGET=8`, `TTL=45`) pour qualifier notre handoff granulaire `FLIP-UNIT` + clôture paginée sous vrais splits distants. Coût estimé : **~2–3 \$**.

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `400`, 2026-11-21T15:50:18.004024+00:00. Excerpt `X027` in [the manifest](../excerpts.json).

## Why this mattered

The assistant plans a gated sequence: first establish a baseline, then test remote live elasticity, then expand if the previous stages pass. This separates a local experiment from a cluster claim.

## What this does not establish

The quote is an experiment plan and cost estimate. Completion, cleanup and measured throughput require run artifacts. The properties paper retains the original AWS workload scopes.

## Related papers

[Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf); [The Network](../../30-network/indexus-network.pdf).

[Back to the archive](../README.md).
