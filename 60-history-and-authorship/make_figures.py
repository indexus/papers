"""Paper 60 figures, using the unchanged 2024 TikZiT vocabulary."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "figkit"))
from ixfig import Fig, box, arrow


def lines(*parts):
    return r"\shortstack[c]{" + r"\\".join(parts) + "}"


os.makedirs(os.path.join(HERE, "figures"), exist_ok=True)
out = {}

# Two columns keep the dated stages legible at the series' fixed figure scale.
f = Fig()
for x, y, text in [
    (0, 4, lines("2014--2016: Ocurz", "Activity feed across geohash cells")),
    (12.8, 4, lines("2019--2021: Next prototypes", "Spatial filters and position ingestion")),
    (12.8, 0, lines("2023--2024: BitExplorer", "Go interfaces, simulation and manuscript")),
    (0, 0, lines("2024: Indexus", "Two papers and a JavaScript SDK")),
    (0, -4, lines("2025--2026: implementation", "Ownership transfer and visual clients")),
    (12.8, -4, lines("2026: DPIP series", "Authority, algebra and experiments"))]:
    box(f, x, y, text, w=9.8, h=2.4)
arrow(f, (4.9, 4), (7.9, 4))
arrow(f, (12.8, 2.8), (12.8, 1.2))
arrow(f, (7.9, 0), (4.9, 0))
arrow(f, (0, -1.2), (0, -2.8))
arrow(f, (4.9, -4), (7.9, -4))
out["timeline"] = f

# A four-step loop: message labels occupy the gaps, not the vertical arrows.
f = Fig()
box(f, 0, 3, lines("Author", "vision, primitives, questions"), w=7.5, h=1.5)
box(f, 13, 3, lines("Models", "formalize, simplify, implement"), w=8, h=1.5)
box(f, 13, -1, lines("Tests and benchmarks", "measure, reproduce, compare"), w=8, h=1.5)
box(f, 0, -1, lines("Author", "audit, decide, redirect"), w=7.5, h=1.5)
arrow(f, (3.75, 3), (9, 3))
f.node(6.4, 3.65, "direction", "tiny")
arrow(f, (13, 2.25), (13, -0.25))
f.node(15.4, 1, lines("code and", "proofs"), "tiny")
arrow(f, (9, -1), (3.75, -1))
f.node(6.4, -0.25, "measured facts", "tiny")
arrow(f, (0, -0.25), (0, 2.25))
f.node(-2.1, 1, lines("next", "iteration"), "tiny")
box(f, 6.5, -4.2, lines("Papers and selected exchanges available", "Fuller development collection proposed"), w=12, h=1.5)
arrow(f, (6.5, -1), (6.5, -3.45))
f.node(9.4, -2.4, lines("record each", "iteration"), "tiny")
out["loop"] = f

for name, fig in out.items():
    with open(os.path.join(HERE, "figures", f"{name}.tikz"), "w") as stream:
        stream.write(fig.code())
print("Generated:", sorted(out))
