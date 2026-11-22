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

f = Fig()
for base, title in [(0,"separate indexes"),(12.4,"shared index")]:
    f.node(base + 4.6, 4.2, title, "tiny")
    for i in range(3):
        x = base + 1.2 + i * 3.4
        box(f,x,2.9,f"application {i+1}",w=2.7,h=.8)
        if base == 0:
            box(f,x,1.0,"own index",w=2.7,h=.8)
            arrow(f,(x,2.5),(x,1.4))
            arrow(f,(base+4.6,-.6),(x,.6))
        else:
            arrow(f,(x,1.4),(x,2.5))
    if base:
        box(f,base+4.6,1.0,"shared zones; independent hosts",w=9.5,h=.8)
        arrow(f,(base+4.6,-.6),(base+4.6,.6))
    box(f,base+4.6,-1.0,"producers",w=3,h=.8)
    f.node(base+4.6,-2.05,"copy into each index" if not base else "publish once; compose many views","tiny")
save("silos",f)
