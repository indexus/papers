"""Paper 50 figures, using the unchanged 2024 TikZiT vocabulary."""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "figkit"))
from ixfig import Fig, tree16, box, arrow


def lines(*parts):
    return r"\shortstack[c]{" + r"\\".join(parts) + "}"


os.makedirs(os.path.join(HERE, "figures"), exist_ok=True)
out = {}

# The original BASE4 tree stays unchanged; equations sit below its paths.
f = tree16()
f.node(0, 0.65, r"$@ = 60$", "tiny")
f.path([(-8.2, -2.8), (8.2, -2.8)], "dashed edge")
f.node(-10, -2.8, "coarse cut", "tiny")
f.path([(-8.2, -3.65), (0, -3.65), (0, -7.25),
        (4, -7.25), (4, -3.65), (8.2, -3.65)], "dashed edge")
f.node(-10, -3.65, "mixed cut", "tiny")
f.node(0, -8.2, r"$A=15,\quad B=3,\quad C=33,\quad D=9$", "tiny")
f.node(0, -9.05, r"$A\circ B\circ C\circ D = A\circ B\circ(CA\circ CB\circ CC\circ CD)\circ D = 60$", "tiny")
out["monoid-cut"] = f

# A short bus collects descriptor fields; hashing and naming have their own space.
f = Fig()
fields = [(4, lines("geometry", r"$(c,W)$")),
          (2, lines("space", "axes and mask")),
          (0, lines("schema", "sum, min, affine, ...")),
          (-2, lines("nonce", "16 bytes")),
          (-4, lines("record depths", r"$[lo,hi]$"))]
for y, text in fields:
    box(f, 0, y, text, w=4.2, h=1.35)
    f.path([(2.1, y), (3.2, y)], "thin")
f.path([(3.2, -4), (3.2, 4)], "thin")
box(f, 6.5, 0, lines("IXC1", "canonical bytes"), w=4.8, h=1.8)
box(f, 13.5, 0, lines("SHA-256", "first 96 bits"), w=4.4, h=1.8)
box(f, 13.5, -3.8, lines("collection name", "16 characters"), w=4.8, h=1.6)
arrow(f, (3.2, 0), (4.1, 0))
arrow(f, (8.9, 0), (11.3, 0))
arrow(f, (13.5, -0.9), (13.5, -3.0))
f.node(6.8, -6.1, "Every node and reader verifies the description against the name.", "tiny")
out["ixc1-cert"] = f

# Distinct parent and leaf rows leave all beam edges outside text boxes.
f = Fig()
box(f, 8, 5, lines("subtree statistics", r"$n,\ \Sigma x,\ \Sigma\|x\|^2$"), w=6.4, h=1.5)
for x, i in [(0, 0), (8, 1), (16, 2)]:
    box(f, x, 1.5, lines(f"zone {i}", rf"$\mu_{i},\ \sigma_{i}^2$"), w=5, h=1.5)
for a, b in [((5.3, 4.25), (0, 2.25)), ((8, 4.25), (8, 2.25)),
             ((10.7, 4.25), (16, 2.25))]:
    arrow(f, a, b)
for x, text in [(-1.6, "leaf 00"), (2.5, "leaf 01"),
                (6.1, "leaf 10"), (10.2, "leaf 11")]:
    box(f, x, -2, text, w=3.0, h=1.1)
for a, b in [((-0.8, 0.75), (-1.6, -1.45)), ((0.8, 0.75), (2.5, -1.45)),
             ((7.2, 0.75), (6.1, -1.45)), ((8.8, 0.75), (10.2, -1.45))]:
    arrow(f, a, b)
f.node(16, -2, "pruned", "tiny")
f.node(7.5, -4.15, lines(r"$\mathrm{score}(q,Z)=\|q-\mu_Z\|^2+0.5\,\sigma_Z^2$",
                         r"one extra sum column: $\Sigma\|x\|^2$"), "tiny")
out["lire-tree"] = f

# Two columns, a clear middle corridor, separate lanes for opposite messages.
f = Fig()
for x, title, summary, records in [
    (0, "Collection G (geo)", lines("zone summary", r"$n$, PCA centroid"),
     "leaf records: (id, coords)"),
    (16, "Collection V (vectors)", lines("zone summary", "centroid, 64 map sums"),
     "leaf records: (id, embedding)")]:
    box(f, x, 4, title, w=5.6, h=1.3)
    box(f, x, 1, summary, w=5.6, h=1.5)
    box(f, x, -2, records, w=5.6, h=1.3)
    arrow(f, (x, 3.35), (x, 1.75))
    arrow(f, (x, 0.25), (x, -1.35))
arrow(f, (2.8, 1.5), (13.2, 1.5))
f.node(8, 2.35, lines(r"exact count $n$", "chooses the plan"), "tiny")
arrow(f, (13.2, 0.5), (2.8, 0.5))
f.node(8, -0.35, lines("map sums", "prune V"), "tiny")
arrow(f, (2.8, -2), (13.2, -2))
f.node(8, -1.45, "shared record ID", "tiny")
out["parallel-descent"] = f

# A folded path avoids squeezing four long labels into a horizontal strip.
f = Fig()
box(f, 0, 3.5, r"embedding $h$", w=4.8, h=1.4)
box(f, 10, 3.5, lines(r"$M=64$ random projections", r"$z_m=\langle a_m,h\rangle$"), w=6.8, h=1.6)
box(f, 10, 0, lines(r"$\cos(t_kz_m),\ \sin(t_kz_m)$", r"$K=8$ positive frequencies"), w=6.8, h=1.6)
box(f, 0, 0, lines("1025", "sum columns"), w=4.8, h=1.6)
arrow(f, (2.4, 3.5), (6.6, 3.5))
arrow(f, (10, 2.7), (10, 0.8))
arrow(f, (6.6, 0), (2.4, 0))
f.path([(0, -0.8), (0, -2.0), (10, -2.0)], "thin")
for x in [0, 10]:
    arrow(f, (x, -2), (x, -2.65))
box(f, 0, -3.5, lines(r"zone A: $\mathcal{L}_{\mathrm{EP}}=0.02$", "Gaussian"), w=6.5, h=1.7)
box(f, 10, -3.5, lines(r"zone C: $\mathcal{L}_{\mathrm{EP}}=1.85$", "local collapse"), w=6.5, h=1.7)
f.node(5, -5.5, lines("Empirical characteristic-function sums fold up the tree",
                       "without rescanning records."), "tiny")
out["sigreg-zone"] = f

# Pedagogical summary of the measured fixed-encoder workflow.
f = Fig()
box(f,0,2,lines("insert record", "fixed features x, label y"),w=5,h=1.5)
box(f,0,-2,lines("delete record", "same features and label"),w=5,h=1.5)
box(f,9,0,lines("zone sufficient statistics", "count and additive", "feature totals"),w=6,h=2.2)
box(f,18.5,0,lines("read the region's totals", "solve the linear model", "on demand"),w=6,h=2.2)
f.path([(2.5,2),(4.7,2),(4.7,.6),(6,.6)], "arrow")
f.path([(2.5,-2),(4.7,-2),(4.7,-.6),(6,-.6)], "arrow")
f.node(4.3,3.0,lines("add", "contribution"), "tiny")
f.node(4.3,-3.0,lines("subtract", "contribution"), "tiny")
arrow(f,(12,0),(15.5,0),"read totals")
f.node(9,-4.4,"the encoder stays fixed; only the additive statistics change", "tiny")
out["learn-forget"] = f

# Each ordinate counts distinct donor/target episodes observed by the sample time.
with open(os.path.join(HERE, "data", "service-a.csv"), newline="") as stream:
    series = list(csv.DictReader(stream))
f = Fig()
width, height = 17, 5.6
for tick in (0, 80, 160, 240, 320):
    y = height * tick / 320
    f.path([(-0.2, y), (0, y)], "thin")
    f.node(-0.86, y, str(tick), "tiny")
for tick in range(0, 401, 100):
    x = width * tick / 400
    f.path([(x, -0.15), (x, 0)], "thin")
    f.node(x, -0.62, str(tick), "tiny")
f.path([(0, height), (0, 0), (width, 0)], "thin")
f.node(width / 2, -1.35, "seconds since load began", "tiny")
f.node(2.0, height + 0.75, "donor--target pairs", "tiny")
for field, style, title, x in [
    ("requested_pairs", "thick", "first request", 7.1),
    ("pairs_with_receiver_write", "dashed edge", "first receiver write", 13.1),
]:
    points = [(width * int(row["seconds"]) / 400, height * int(row[field]) / 320)
              for row in series]
    f.path(points, style)
    key_y = height + 0.75
    f.path([(x - 1.45, key_y), (x - 0.3, key_y)], style)
    f.node(x + 1.3, key_y, title, "tiny")
    f.node(width + 0.85, points[-1][1], series[-1][field], "tiny")
out["placement-service"] = f

# Lengths use a common zero and show measured proportions, not throughput.
f = Fig()
for percent in (0, 25, 50, 75, 100):
    x = percent * 0.13
    f.path([(x, -0.3), (x, 0)], "thin")
    f.node(x, -0.85, rf"{percent}\%", "tiny")
f.path([(0, 0), (13, 0)], "thin")
for y, name, numerator, denominator, style in [
    (4.8, "A  donor vnode", 99, 99, "dark surface"),
    (3.75, "A  donor host", 48, 99, "surface"),
    (2.35, "B  donor vnode", 109, 112, "dark surface"),
    (1.3, "B  donor host", 61, 112, "surface"),
]:
    end = 13 * numerator / denominator
    f.node(-2.4, y, name, "tiny")
    f.path([(0, y - 0.26), (end, y - 0.26), (end, y + 0.26),
            (0, y + 0.26), (0, y - 0.26)], style)
    f.node(14.45, y, f"{numerator}/{denominator}", "tiny")
out["placement-relief"] = f

for name, fig in out.items():
    with open(os.path.join(HERE, "figures", f"{name}.tikz"), "w") as stream:
        stream.write(fig.code())
print("Generated:", sorted(out))
