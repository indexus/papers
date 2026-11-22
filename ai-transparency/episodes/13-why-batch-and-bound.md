# 13. Record why a performance fix was introduced

**Recorded date:** 2026-11-21 18:50 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** An Antigravity recap explains the pressure that led to batch reads and a bounded warm drain.

## Human request

> Explique ce que tu as fait e pourquoi aussi

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `624`, 2026-11-21T17:50:12.437097+00:00. Excerpt `X023` in [the manifest](../excerpts.json).

## Assistant reply

> `Store.Snapshots(ctx, zones, maxBytes)` lit tout le lot en **une seule transaction `s.view`** bornée en octets

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `625`, 2026-11-21T17:50:12.652881+00:00. Excerpt `X024` in [the manifest](../excerpts.json).

## Assistant reply

> Plafonné les vagues de nouvelles zones (`maxWarmCloseDrains` + `ForceFreezeRegion`) pour éviter la famine de clôture sous création continue de zones.

Source: **Antigravity**, conversation `bf35cccf-c9dd-4aca-9d78-a260d145bc1f`, message `625`, 2026-11-21T17:50:12.652881+00:00. Excerpt `X025` in [the manifest](../excerpts.json).

## Why this mattered

The assistant describes both the mechanism and its reason: reduce read-transaction contention and ensure closure progresses under continuing zone creation. Related source changes can be inspected in core commits [d55ffe2](https://github.com/indexus/core/commit/d55ffe26b6fc9282e70bff34ec23dc7a8aa22d24) and [7181cad](https://github.com/indexus/core/commit/7181cada4ab37f6a34a4d756bdcb441e6af915d8).

## What this does not establish

This is a generated recap, not a newly rerun benchmark. ForceFreezeRegion is a liveness fallback with a residual freeze cost, not a proof that pauses have disappeared at every data size.

## Related papers

[The Network](../../30-network/indexus-network.pdf); [Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf).

[Back to the archive](../README.md).
