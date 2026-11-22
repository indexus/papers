# 04. Return to a simple placement rule

**Recorded date:** 2026-09-20 20:32 CEST (Europe/Paris). Original UTC timestamps are retained below.

**Context.** During an earlier placement redesign, the author pushes back against accumulated exceptions.

## Human request

> Enfait le plan est trop compliqué et surtout, une zone doit automatiquement obtenir ce qui est XOR le plus proche pas d'exception, pas de bloquage. Donc il faut vraiment trouver une méthode de depouillement successif qui garantisse les choses.

Source: **Cursor**, conversation `31fffcc4-0dfa-4d7c-ad85-be394ba48a0f`, message `eaa813e7-9332-48a2-8464-e86cb9e5e83d`, 2026-09-20T18:32:21.574Z. Excerpt `X007` in [the manifest](../excerpts.json).

## Assistant reply

> Tu as raison : si XOR est la loi, on ne doit plus « bloquer » une zone. Je repars du dépouillement XOR — planter un ID, pas vetoer un owner.

Source: **Cursor**, conversation `31fffcc4-0dfa-4d7c-ad85-be394ba48a0f`, message `ca154362-ee5f-441b-b520-4a08fa1c1dd0`, 2026-09-20T18:33:42.438Z. Excerpt `X008` in [the manifest](../excerpts.json).

## Why this mattered

The author keeps the XOR placement law as a design constraint; the assistant returns to choosing vnode addresses instead of adding placement vetoes.

## What this does not establish

The historical phrase “not block a zone” concerns placement. It is not permission to bypass durable authority, freeze barriers or installation checks. Those remain required in the current normal write path.

## Related papers

[The Network](../../30-network/indexus-network.pdf); [The Whitepaper](../../10-whitepaper/indexus-whitepaper.pdf).

[Back to the archive](../README.md).
