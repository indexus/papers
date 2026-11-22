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

# The same spatial cells, three independently published collections.
f=Fig()
for y, label, private in [(8.4,"land registry: public",False),(4.2,"weather: public; fresh hour paid",False),(0,"user notes: private",True)]:
    plane(f,x0=0,y0=y,w=6,h=3,shear=4,div=2,shaded=[(0,0)],labels={(0,0):"AB"})
    f.node(15,y+1.5,label,"tiny")
f.node(10,-1,"same Space; independent collections", "tiny")
save("layers",f)

f=Fig()
for x,name in [(0,"producer"),(6,"host"),(12,"application"),(18,"user")]:
    box(f,x,0,name,w=3.4,h=1)
for x,label in [(0,"signed records"),(6,"zone totals"),(12,"view")]:
    arrow(f,(x+1.7,0),(x+4.3,0),label)
f.node(9,-1.8,"one party may play several roles; no role owns the shared index", "tiny")
save("roles",f)

f=Fig()
box(f,0,0,"map",w=3,h=.9);box(f,17,0,"host",w=3,h=.9)
f.path([(0,-.45),(0,-8.2)],"dashed edge");f.path([(17,-.45),(17,-8.2)],"dashed edge")
for y, forward, label in [(-1.7,True,"1. ask: weather of zone AB, last hour"),(-3.7,False,"2. price: 3 sat and an invoice"),(-5.7,True,"3. ask again with proof of payment"),(-7.7,False,"4. receive the answer and receipt")]:
    arrow(f,(0,y) if forward else (17,y),(17,y) if forward else (0,y),label)
save("pay",f)

f=Fig()
for x,name in [(0,"map"),(8,"host"),(16,"producer")]:box(f,x,0,name,w=3.5,h=1)
arrow(f,(1.75,0),(6.25,0),"3 sat");arrow(f,(9.75,0),(14.25,0),"2 sat")
f.node(8,-1.6,"keeps 1 sat", "tiny");f.node(16,-1.6,"receives 2 sat", "tiny")
f.node(8,-3,lines("alternative: the map pays each party directly", "both arrangements are proposals"),"tiny")
save("split",f)

f=Fig()
plane(f,x0=0,y0=0,w=7,h=4,shear=3,div=2,shaded=[(0,1)],labels={(1,1):"ABB",(0,0):"ABC",(1,0):"ABD"})
# Records are symbolic; the exact example counts are in the answer table.
f.node(3.9,3.65,"ABA","tiny")
for u,v in [(.10,.58),(.20,.65),(.32,.60),(.12,.74),(.38,.73),(.28,.80)]:
    f.node(u*7+v*3,v*4,"","item")
arrow(f,(10.8,2),(14,2),"read AB")
table(f,14.5,3.5,[("ABA","9412"),("ABB","2"),("ABC","1"),("ABD","14")],title="total: 9429",w1=2.2,w2=1.8,rh=.8)
f.node(9,-1,"four child rows, whether the zone is empty or holds millions of records", "tiny")
save("zoneprice",f)

f=Fig()
for y,agency,count in [(3,"agency 1",20),(0,"agency 2",15),(-3,"agency 3",7)]:
    box(f,0,y,lines(agency,f"{count} flats"),w=4,h=1.4)
    arrow(f,(2,y),(7.5,0))
box(f,10,0,lines("shared collection", "42 flats; total rent 39900"),w=5,h=1.6)
arrow(f,(12.5,0),(17,0),"one zone read")
box(f,19,0,lines("reader", "average rent 950"),w=4,h=1.6)
save("agencies",f)

f=Fig()
for y,name,task in [(6,"Yjs","edit drafts together"),(3,"Indexus","sign, index and read records"),(0,"IPFS","store heavy files"),(-3,"Lightning / Bitcoin","pay for reads; no Indexus token")]:
    box(f,2,y,name,w=5,h=1.2)
    f.node(13,y,task,"tiny")
save("stack",f)

f=Fig()
box(f,0,3,lines("public", "specification"),w=4,h=1.5)
box(f,8,3,lines("conformance", "tests"),w=4,h=1.5)
arrow(f,(2,3),(6,3),"defines")
for x,label in [(0,"reference node"),(8,"second node"),(16,"client library")]:
    box(f,x,-1,label,w=4,h=1.2)
    # Three lanes leave the bottom of the tests; none crosses a box.
    f.path([(8,2.25),(8,1),(x,1),(x,-.4)],"arrow")
f.node(8,-3,"implementations agree on the specification, not on one program", "tiny")
save("standard",f)
print("eight economics figures regenerated")
