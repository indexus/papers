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
NET = ["AB", "AC", "AD", "BC", "CA", "CC", "DA", "DB", "DD"]
out = {}

# Ownership: zone C of collection BB has address CB; closest node CA (thick), address dashed.
out["owner"] = tree16(show=NET + ["CB"], labels=NET + ["CB"], thick=["CA"], dashed=["CB"])

# Sums: the collection of the 2024 paper, level @ and level 1, with its table.
f = Fig()
plane(f, x0=0, y0=4.2, div=1, shaded=[(0, 0)], labels={(0, 0): "@"})
plane(f, x0=0, y0=0, div=2, shaded=[(0, 1), (0, 0), (1, 0)],
      labels={(0, 1): "A", (1, 1): "B", (0, 0): "C", (1, 0): "D"})
table(f, 11.2, 6.6, [("A", "15"), ("B", "3"), ("C", "33"), ("D", "9")], title="Zone @  =  60", w2=.9, rh=.7)
table(f, 11.2, 2.6, [("at C", "4"), ("CB", "9"), ("CC", "10"), ("CD", "10")], title="Zone C  =  33", w2=.9, rh=.7)
out["sums"] = f

# Hot split: donor CA, newcomer CB = CA with one bit flipped (guard respected).
out["split"] = tree16(show=NET + ["CB"], labels=NET + ["CB"], thick=["CA", "CB"])

# Authority: a chain of certificates from genesis, each consuming one token.
f = Fig()
box(f, 0, 0, "genesis: all  \\textrightarrow{}  BC", w=3.4)
box(f, 5.2, 0, "certificate 1", w=2.4)
box(f, 10.2, 0.8, "0\\ldots{}  \\textrightarrow{}  AB", w=2.6)
box(f, 10.2, -0.8, "1\\ldots{}  \\textrightarrow{}  BC", w=2.6)
box(f, 15.2, -0.8, "certificate 2", w=2.4)
box(f, 20.2, 0.0, "10\\ldots{}  \\textrightarrow{}  CA", w=2.6)
box(f, 20.2, -1.6, "11\\ldots{}  \\textrightarrow{}  BC", w=2.6)
arrow(f, (1.7, 0), (4.0, 0), "consumes")
arrow(f, (6.4, 0.15), (8.9, 0.8)); arrow(f, (6.4, -0.15), (8.9, -0.8))
arrow(f, (11.5, -0.8), (14.0, -0.8), "consumes")
arrow(f, (16.4, -0.65), (18.9, 0.0)); arrow(f, (16.4, -0.95), (18.9, -1.6))
out["authority"] = f

# Store order: a zone is one key range, its children consecutive sub-ranges.
f = Fig()
xs = [0, 2.2, 6.2, 10.2, 14.2, 18.2]
names = ["C", "CA", "CB", "CC", "CD"]
f.path([(0, 0), (18.2, 0), (18.2, 0.7), (0, 0.7)], "thin", close=True)
for x in xs[1:-1]:
    f.path([(x, 0), (x, 0.7)], "thin")
for i, n in enumerate(names):
    f.node((xs[i] + xs[i + 1]) / 2, 0.35, n, "tiny")
# pages below with their sums
for k in range(9):
    x = 2.2 + k * 1.778
    f.path([(x, -1.2), (x + 1.6, -1.2), (x + 1.6, -0.7), (x, -0.7)], "surface", close=True)
f.node(0.5, -0.95, "pages", "tiny")
f.node(9.1, 1.25, "one zone = one contiguous range of keys; its children follow each other", "tiny")
f.node(10.2, -1.75, "each page stores the sums of its rows: a zone sum adds page sums, not records", "tiny")
out["keys"] = f

# Handoff timeline: writes accepted by the donor, nobody, then the receiver.
f = Fig()
f.node(-1.2, 1.0, "donor", "tiny"); f.node(-1.2, 0.0, "receiver", "tiny")
f.path([(0, 0.8), (7.0, 0.8), (7.0, 1.2), (0, 1.2)], "surface", close=True)
f.path([(13.0, -0.2), (17, -0.2), (17, 0.2), (13.0, 0.2)], "surface", close=True)
f.path([(0, -0.7), (17.5, -0.7)], "arrow")
for x, t in [(0.2, "copy"), (7.0, "freeze"), (9.0, "stage"), (11.0, "emit"), (13.0, "install")]:
    f.path([(x, -0.8), (x, 1.5)], "dashed edge")
    f.node(x, 1.8, t, "tiny")
f.node(3.5, 1.0, "accepts writes", "tiny"); f.node(15.0, 0.0, "accepts writes", "tiny")
f.node(10.0, 0.5, "no writer", "tiny"); f.node(17.5, -1.0, "time", "tiny")
out["handoff"] = f

# Summary: zone C on CA pushes its total to the holder of the parent @ (BC).
f = tree16(show=NET + ["BB", "CB"], labels=NET + ["BB", "CB"], thick=["CA", "BC"], dashed=["BB", "CB"],
           node_text={"": "@ = 60", "10": "C = 33"})
out["summary"] = f


# A join becomes useful one installed lot at a time. Each cell is a lot,
# not a fixed duration or a fixed amount of client traffic.
f = Fig()
for base,moved,title in [(0,0,"before join"),(7.7,1,"first lot installed"),(15.4,3,"later lots installed")]:
    f.node(base+2.7,3.4,title,"tiny")
    f.node(base,2.4,"lot","tiny");f.node(base+3.4,2.4,"accepting writes","tiny")
    for i,zone in enumerate("ABCD"):
        y=1.4-i*1.5
        box(f,base,y,zone,w=1.1,h=.7)
        box(f,base+3.4,y,"new vnode" if i<moved else "old vnode",w=3.2,h=.7)
        arrow(f,(base+.55,y),(base+1.8,y))
    f.node(base+2.7,-4.1,f"{4-moved} lots on old; {moved} on new","tiny")
out["progressive"] = f
for name, fig in out.items():
    save(name, fig)
    if name in {"owner", "keys", "split", "handoff", "summary", "progressive"}:
        target = HERE.parent / "30-network" / "figures" / (name + ".tikz")
        target.parent.mkdir(exist_ok=True)
        target.write_text(fig.code())
# The client uses exactly the same sums example.
(HERE.parent / "20-client" / "figures" / "sums.tikz").write_text(out["sums"].code())
print("whitepaper, client sums and network figures regenerated")
