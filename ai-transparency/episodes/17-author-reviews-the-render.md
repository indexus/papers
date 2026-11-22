# 17. The author catches visual defects and redirects the work

**Recorded date:** 2026-11-22 12:21 CET (Europe/Paris). Original UTC timestamps are retained below.

**Context.** The author inspects the PDF, finds overlaps and asks for a hand-off to Codex.

## Human request

> Regarde le resultat je trouves que ce n'est pas aussi claire et le rendu il y a des choses superposé, fais un prompt pour que je passe par codex pour la mise en forme s'il te plait

Source: **Antigravity**, conversation `7c7ff249-3d7c-4daa-86e3-745fb41f3dec`, message `197`, 2026-11-22T11:21:55.367557+00:00. Excerpt `X032` in [the manifest](../excerpts.json).

## Assistant reply

> Voici un prompt prêt à copier-coller dans Codex pour reprendre proprement la mise en forme, la clarté et toutes les figures TikZiT avec vérification visuelle page par page :

Source: **Antigravity**, conversation `7c7ff249-3d7c-4daa-86e3-745fb41f3dec`, message `198`, 2026-11-22T11:21:55.503545+00:00. Excerpt `X033` in [the manifest](../excerpts.json).

## Why this mattered

The workflow includes human review of the rendered artifact, not just acceptance of generated LaTeX. A second tool receives explicit visual references and a page-by-page checking requirement. The resulting series revision is recorded by papers commit [a08f71a](https://github.com/indexus/papers/commit/a08f71af26973117e4fe642575dee11f7b4083fe).

## What this does not establish

This selection does not include the complete typesetting session. A successful compile alone would not establish good layout; the rendered-page review remains part of the verification record.

## Related papers

[Development History and Authorship](../../60-history-and-authorship/indexus-history-and-authorship.pdf); [Properties, Benchmarks, and Directions](../../50-properties-and-applications/indexus-properties-and-applications.pdf).

[Back to the archive](../README.md).
