"""Reproducible TikZiT figures; run from any working directory."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "figkit"))
from ixfig import Fig, tree16, plane, table, box, arrow

def lines(*parts):
    return r"\shortstack[c]{" + r"\\".join(parts) + "}"

def save(name, f):
    target = HERE / "figures" / (name + ".tikz")
    target.parent.mkdir(exist_ok=True)
    target.write_text(f.code())
# Zoom: the same region at three zooms; the view is darker, the reader reads those zones.
f = Fig()
plane(f, x0=0, y0=8.4, div=1, shaded=[(0, 0)], labels={(0, 0): "@"})
plane(f, x0=0, y0=4.2, div=2, shaded=[(0, 0)], labels={(0, 1): "A", (1, 1): "B", (0, 0): "C", (1, 0): "D"})
plane(f, x0=0, y0=0, div=4, shaded=[(0, 0), (1, 0), (0, 1), (1, 1)],
      labels={(0, 1): "CA", (1, 1): "CB", (0, 0): "CC", (1, 0): "CD"})
f.node(12.2, 9.9, "zoom 0: read @", "tiny")
f.node(12.2, 5.7, "zoom 1: read C", "tiny")
f.node(12.2, 1.5, "zoom 2: read CA, CB, CC, CD", "tiny")
save("zoom", f)

# Compose: two collections cut the same cells with different letters.
f = Fig()
plane(f, x0=0, y0=4.2, div=2, shaded=[(0, 0)], labels={(0, 1): "D", (1, 1): "A", (0, 0): "B", (1, 0): "C"})
plane(f, x0=0, y0=0, div=2, shaded=[(0, 0)], labels={(0, 1): "B", (1, 1): "C", (0, 0): "D", (1, 0): "A"})
plane(f, x0=13, y0=2.1, div=2, shaded=[(0, 0)], labels={(0, 0): "cell (0,0)"})
f.node(5, 8.0, "first collection, offset B", "tiny")
f.node(5, -0.6, "second collection, offset D", "tiny")
f.node(18, 6.0, "same cell after removing offsets", "tiny")
save("compose", f)
# Three reads following one acknowledged insertion into a collection of sixty.
f = Fig()
for x, name in [(0, "client cache"), (7.0, "stored summary"), (14.0, "fresh server read")]:
    box(f, x, 1.2, name, w=5.6, h=1.15)
for x, label in [(0, "60"), (7.0, "60 or 61"), (14.0, "61 or unavailable")]:
    arrow(f, (x, .6), (x, -.6))
    f.node(x, -1.0, label, "tiny")
save("refresh", f)
print("client figures regenerated")
