import sys
sys.path.insert(0, "/home/claude/papers2/figkit")
from ixfig import Fig, plane, table

# Zoom: the same region at three zooms; the view is darker, the reader reads those zones.
f = Fig()
plane(f, x0=0, y0=8.4, div=1, shaded=[(0, 0)], labels={(0, 0): "@"})
plane(f, x0=0, y0=4.2, div=2, shaded=[(0, 0)], labels={(0, 1): "A", (1, 1): "B", (0, 0): "C", (1, 0): "D"})
plane(f, x0=0, y0=0, div=4, shaded=[(0, 0), (1, 0), (0, 1), (1, 1)],
      labels={(0, 1): "CA", (1, 1): "CB", (0, 0): "CC", (1, 0): "CD"})
f.node(12.2, 9.9, "zoom 0: read @", "tiny")
f.node(12.2, 5.7, "zoom 1: read C", "tiny")
f.node(12.2, 1.5, "zoom 2: read CA, CB, CC, CD", "tiny")
open("figures/zoom.tikz", "w").write(f.code())

# Compose: two collections cut the same cells with different letters.
f = Fig()
plane(f, x0=0, y0=4.2, div=2, shaded=[(0, 0)], labels={(0, 1): "B", (1, 1): "C", (0, 0): "D", (1, 0): "A"})
plane(f, x0=0, y0=0, div=2, shaded=[(0, 0)], labels={(0, 1): "D", (1, 1): "A", (0, 0): "B", (1, 0): "C"})
plane(f, x0=14, y0=2.1, div=2, shaded=[(0, 0)], labels={(0, 0): "cell (0,0)"})
f.node(11.5, 5.7, "houses, offset B: D", "tiny")
f.node(11.5, 1.5, "weather, offset D: B", "tiny")
f.node(24.0, 3.6, "same cell", "tiny")
open("figures/compose.tikz", "w").write(f.code())
print("ok")
