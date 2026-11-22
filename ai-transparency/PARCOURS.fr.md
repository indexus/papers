# Comment Rémi a travaillé avec les IA sur Indexus

Ce dossier montre une manière de travailler, à partir d'extraits datés. Ce n'est
ni l'intégralité des discussions, ni une tentative de calculer un pourcentage
d'invention entre une personne et des modèles. Les citations restent dans leur
langue d'origine, avec leurs formulations et leurs fautes. Les explications
autour sont rétrospectives.

Les deux [articles de 2024](../README.md) constituent le point de départ : un
même arbre pour les nœuds et les données, des espaces encodés par subdivisions,
la recherche progressive et la délégation selon la proximité XOR. Les échanges
retenus ici montrent ensuite comment Rémi a utilisé plusieurs outils pour
formaliser, construire, simplifier, mesurer et expliquer ce projet.

## 1. Fixer le résultat attendu avant de choisir la mécanique

La demande récurrente n'est pas simplement « écris du code ». En septembre,
Rémi demande déjà un scale qui absorbe la charge rapidement, sans faire
exploser le nombre de vnodes. En novembre, il reformule le résultat attendu :
le nouveau vnode doit commencer à recevoir les écritures des premières zones
transférées, pendant que le donneur continue à servir les autres.

Cette direction vient des demandes humaines visibles. Les assistants cherchent
ensuite les blocages dans les chemins existants et proposent des mécanismes.

À lire : [objectif de scale](episodes/02-author-scale-objectives.md) et
[transfert granulaire](episodes/10-granular-relief.md).

## 2. Demander à comprendre, et refuser les explications trop abstraites

Rémi demande des exemples, des simulations et des représentations. Quand une
explication utilise trop de vocabulaire, il le dit. L'assistant reprend alors
le raisonnement avec des adresses et des cartons.

Ce détour pédagogique a une fonction technique : vérifier que le problème, le
mécanisme proposé et l'effet attendu peuvent être décrits clairement. Une
illustration aide à poser une garantie ; elle ne suffit pas à la démontrer.

À lire : [demande d'un exemple concret](episodes/03-demand-understandable-examples.md)
et [retour à la règle XOR](episodes/04-return-to-xor.md).

## 3. Faire travailler les outils les uns contre les angles morts des autres

Un raisonnement passe de ChatGPT à Cursor ; plus tard, le travail granulaire de
Codex est présenté dans Antigravity avec une autre branche du moteur. Rémi
demande une comparaison avant d'unifier. Les propositions peuvent ainsi être
relues dans un autre contexte et confrontées au code réel.

Le simple fait d'utiliser deux outils ne rend pas un résultat indépendant :
ils peuvent reprendre la même hypothèse ou le même texte. Les extraits
indiquent donc les briefs transmis et distinguent la relecture d'une vraie
reproduction exécutée.

À lire : [limites du contexte ChatGPT](episodes/06-chatgpt-context-limit.md),
[audit Claude Code](episodes/07-claude-code-audit.md) et
[unification entre outils](episodes/12-cross-tool-integration.md).

## 4. Demander des tests qui pourraient réellement faire échouer la proposition

Rémi demande explicitement de challenger les tests et de vérifier qu'ils ne
servent pas seulement à arranger les résultats. Les assistants relisent alors
les invariants, les chemins de code exercés et les éléments encore non prouvés.

Deux extraits montrent pourquoi cette exigence compte. Codex repère un contrôle
qui peut annoncer « zéro écart » alors que les résultats à comparer sont
absents. Plus tard, une reproduction signale un désaccord numérique et la
publication est arrêtée à cette étape. Ces événements intermédiaires sont
conservés, même si le projet a ensuite avancé.

À lire : [tests objectifs](episodes/05-challenge-the-tests.md),
[contrôle incomplet](episodes/08-checker-missing-results.md) et
[arrêt sur un échec](episodes/09-stop-on-reproduction-failure.md).

## 5. Accepter qu'une estimation soit corrigée par le code ou les mesures

Une petite mesure locale ne donne pas automatiquement la latence d'un cluster.
Dans un échange sur les gros volumes, Codex reconnaît que son estimation de
freeze était trop optimiste : une étape postérieure au gel renvoyait encore les
snapshots complets du lot. L'important est la correction de l'hypothèse, puis
la qualification du chemin réel.

Les campagnes distantes sont ensuite organisées par étapes. Les comparaisons
de recherche vectorielle ont elles aussi un budget explicite de vecteurs
scannés. Cela rend les résultats plus interprétables qu'une simple annonce
« plus rapide » ou « meilleur ».

À lire : [estimation corrigée](episodes/11-revise-freeze-estimate.md),
[raison des correctifs](episodes/13-why-batch-and-bound.md),
[tests distants progressifs](episodes/14-remote-tests-in-stages.md) et
[comparaison vectorielle](episodes/15-fair-vector-comparison.md).

## 6. Garder la responsabilité du produit et du rendu final

Rémi précise le style attendu : prolonger les premiers papiers, rester simple,
conserver les figures TikZiT, rendre les explications accessibles et viser un
standard permettant plusieurs implémentations. Il relit également les PDF,
repère les superpositions et demande une reprise de la mise en forme par un
autre outil.

À lire : [style et standard ouvert](episodes/16-style-and-standard.md) et
[relecture visuelle et passage à Codex](episodes/17-author-reviews-the-render.md).

## Ce que l'on peut attribuer à chacun dans cette sélection

| Contribution humaine visible | Contribution des assistants visible |
| --- | --- |
| Le point de départ conceptuel, conservé dans les articles de 2024 | La reformulation et l'exploration de mécanismes dans les échanges ultérieurs |
| Les objectifs de débit, d'élasticité et de transfert progressif | La lecture des chemins de code et la recherche de blocages |
| Les contraintes de simplicité, de garanties et de comparaison | Les propositions de tests, de corrections et de bancs d'ablation |
| Le choix des directions et les demandes de vérification | La collecte de preuves, les diagnostics et les comptes rendus de mesures |
| Le jugement sur la clarté, l'utilité et le rendu des papiers | L'aide à la rédaction, aux figures et à la mise en forme |

Ces contributions se recouvrent et s'influencent. Une bonne idée peut être
reformulée par plusieurs outils ; un correctif peut révéler un défaut dans le
raisonnement initial ; une demande de simplicité peut modifier l'architecture.
La source d'une contribution s'évalue passage par passage et changement par
changement, pas en demandant à un assistant de distribuer les mérites.

[L'épisode sur l'attribution](episodes/18-attribution-is-not-a-vote.md) conserve
justement une réponse favorable de l'IA tout en rappelant sa limite : cette
réponse n'est pas une preuve indépendante. Les sources datées, les changements
et les expériences sont les éléments à confronter.

[Catalogue des extraits](README.md) · [Méthode et limites](METHOD.md) ·
[Papier sur l'histoire et les contributions](../60-history-and-authorship/indexus-history-and-authorship.pdf).
