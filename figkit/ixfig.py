"""Generator of figures in the author's TikZiT style (see FIGURES.md).

Geometry is copied from the author's own figures:
- the 16-leaf BASE4 tree of encoded.tikz / p2p-network.tikz,
- the isometric planes of p2p-delegation-*.tikz,
- the small tables of collection.tikz.
Every function returns TikZ code using only the author's styles
(thin, thick, dashed edge, surface, item, tiny, normal) plus `arrow` and
`dark surface` defined in ixfig.sty. Write the result to a .tikz file and
include it with \\ixfig[width]{file}.
"""

ALPHA = "ABCD"


class Fig:
    def __init__(self):
        self.nodes, self.edges, self.n = [], [], 0

    def node(self, x, y, text="", style="none"):
        self.n += 1
        self.nodes.append(f"\t\t\\node [style={style}] ({self.n}) at ({x:g}, {y:g}) {{{text}}};")
        return self.n

    def edge(self, a, b, style="thin", extra=""):
        sa = f"({a})" if isinstance(a, str) else f"({a}.center)"
        sb = f"({b})" if isinstance(b, str) else f"({b}.center)"
        self.edges.append(f"\t\t\\draw [style={style}{extra}] {sa} to {sb};")

    def path(self, pts, style="thin", close=False):
        ids = [self.node(x, y) for x, y in pts]
        body = " to ".join(f"({i}.center)" for i in ids)
        if close:
            body += " to cycle"
        self.edges.append(f"\t\t\\draw [style={style}] {body};")

    def code(self):
        return ("\\begin{tikzpicture}\n\t\\begin{pgfonlayer}{nodelayer}\n" + "\n".join(self.nodes)
                + "\n\t\\end{pgfonlayer}\n\t\\begin{pgfonlayer}{edgelayer}\n" + "\n".join(self.edges)
                + "\n\t\\end{pgfonlayer}\n\\end{tikzpicture}\n")


# Tree positions of the author's 16-leaf tree. A vertex is named by its
# path of bits ("" root, "0", "01", ..., 4 bits = a leaf).
def _pos(bits, dx=0.0, dy=0.0):
    if bits == "":
        return (0 + dx, 0 + dy)
    d = len(bits)
    k = int(bits, 2)
    if d == 1:
        return ((-4 if k == 0 else 4) + dx, -1 + dy)
    if d == 2:
        return ((-6 + 4 * k) + dx, -2 + dy)
    if d == 3:
        return ((-7 + 2 * k) + dx, -4 + dy)
    # leaf: left child up (-5.5), right child down (-6.5), as in the originals
    parent_x = -7 + 2 * (k // 2)
    return ((parent_x - 0.5) if k % 2 == 0 else (parent_x + 0.5)) + dx, (-5.5 if k % 2 == 0 else -6.5) + dy


def leaf_bits(label):
    """'CB' -> '1001'."""
    return "".join(format(ALPHA.index(c), "02b") for c in label)


def tree16(fig=None, labels="all", thick=(), dashed=(), node_text=None, dx=0.0, dy=0.0,
           show=None):
    """The author's encoded tree.

    labels: "all", or an iterable of leaf labels to print (like p2p-network).
    show:   if given, only branches leading to these leaves are drawn (like
            p2p-network, which draws only the nodes of the network); default all.
    thick:  leaf labels whose path from the root is drawn thick (a node).
    dashed: leaf labels whose path from its divergence point is dashed (a zone
            address), drawn as in the delegation figures: the path is dashed
            from the deepest vertex shared with a thick path, or from the root.
    node_text: {bits: text} small labels written next to inner vertices
            (for instance sums), in style tiny.
    """
    fig = fig or Fig()
    leaves = [a + b for a in ALPHA for b in ALPHA]
    shown = set(show) if show is not None else set(leaves)
    thick_paths = {leaf_bits(l)[:i] for l in thick for i in range(1, 5)}
    vid = {}

    def v(bits):
        if bits not in vid:
            x, y = _pos(bits, dx, dy)
            vid[bits] = fig.node(x, y)
        return vid[bits]

    drawn = set()
    for leaf in leaves:
        if leaf not in shown:
            continue
        b = leaf_bits(leaf)
        x, y = _pos(b, dx, dy)
        lab = leaf if (labels == "all" or leaf in labels) else ""
        lid = fig.node(x, y, lab, "tiny")
        vid[b] = lid
        for i in range(4, 0, -1):
            child, parent = b[:i], b[:i - 1]
            if child in drawn:
                break
            drawn.add(child)
            style = "thick" if child in thick_paths else "thin"
            a = lid if i == 4 else v(child)
            fig.edges.append(f"\t\t\\draw [style={style}] ({a}{'' if i == 4 else '.center'}) to ({v(parent)}.center);")
    for leaf in dashed:
        b = leaf_bits(leaf)
        start = max((i for i in range(0, 5) if b[:i] in thick_paths or i == 0), default=0)
        pts = [b[:i] for i in range(start, 5)]
        if b not in vid:
            x, y = _pos(b, dx, dy)
            vid[b] = fig.node(x, y, leaf, "tiny")
        for p, c in zip(pts, pts[1:]):
            a = vid[c] if len(c) == 4 else v(c)
            fig.edges.append(f"\t\t\\draw [style=dashed edge] ({v(p)}.center) to ({a}{'' if len(c) == 4 else '.center'});")
    for bits, text in (node_text or {}).items():
        x, y = _pos(bits, dx, dy)
        side = -1 if x - dx > 0 else 1
        fig.node(x + side * 1.0, y + 0.3, text, "tiny")
    return fig


def plane(fig=None, x0=3.75, y0=-2.75, w=6.0, h=3.0, shear=4.0, div=1, shaded=(), labels=None,
          items=(), dashed_grid=False):
    """An isometric tile plane, as in the delegation and collection figures.

    (x0, y0) is the front-left corner. div = cells per side (1, 2, 4).
    shaded: cells (i, j) drawn with the grey surface, i = column from the
    left, j = row from the front. labels: {(i, j): text}. items: points
    (u, v) in [0, 1]^2 of the plane, drawn as the author's grey dots.
    """
    fig = fig or Fig()

    def p(u, v):  # u along the front edge, v towards the back
        return (x0 + u * w + v * shear, y0 + v * h)

    for (i, j) in shaded:
        c = [p(i / div, j / div), p((i + 1) / div, j / div), p((i + 1) / div, (j + 1) / div), p(i / div, (j + 1) / div)]
        fig.path(c, "surface", close=True)
    fig.path([p(0, 0), p(1, 0), p(1, 1), p(0, 1)], "thin", close=True)
    for k in range(1, div):
        st = "dashed edge" if dashed_grid else "thin"
        fig.path([p(k / div, 0), p(k / div, 1)], st)
        fig.path([p(0, k / div), p(1, k / div)], st)
    for (i, j), text in (labels or {}).items():
        x, y = p((i + 0.5) / div, (j + 0.5) / div)
        fig.node(x, y, text, "normal")
    for (u, v) in items:
        x, y = p(u, v)
        fig.node(x, y, "", "item")
    return fig


def table(fig, x, y, rows, title=None, w1=1.6, w2=0.6, rh=0.45):
    """A small two-column table, as in the collection figure."""
    if title:
        fig.node(x + (w1 + w2) / 2, y + 0.45, title, "tiny")
    n = len(rows)
    fig.path([(x, y), (x + w1 + w2, y), (x + w1 + w2, y - n * rh), (x, y - n * rh)], "thin", close=True)
    fig.path([(x + w1, y), (x + w1, y - n * rh)], "thin")
    for k, (a, b) in enumerate(rows):
        if k:
            fig.path([(x, y - k * rh), (x + w1 + w2, y - k * rh)], "thin")
        fig.node(x + w1 / 2, y - (k + 0.5) * rh, a, "tiny")
        fig.node(x + w1 + w2 / 2, y - (k + 0.5) * rh, b, "tiny")
    return fig


def box(fig, x, y, text, w=1.6, h=0.6):
    """A plain thin rectangle with a tiny label (a node, a client, a disk)."""
    fig.path([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)], "thin", close=True)
    return fig.node(x, y, text, "tiny")


def arrow(fig, a, b, text=None, above=True):
    """A thin arrow between two points, with an optional tiny label."""
    i, j = fig.node(*a), fig.node(*b)
    fig.edges.append(f"\t\t\\draw [style=arrow] ({i}.center) to ({j}.center);")
    if text:
        fig.node((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (0.25 if above else -0.25), text, "tiny")
    return fig


if __name__ == "__main__":
    # Self-check: the network of p2p-network.tikz with node CA thick and zone CB dashed.
    net = ["AB", "AC", "AD", "BC", "CA", "CC", "DA", "DB", "DD"]
    f = tree16(show=net + ["CB"], labels=net + ["CB"], thick=["CA"], dashed=["CB"])
    open("/tmp/kit/selfcheck.tikz", "w").write(f.code())
    g = plane(div=2, shaded=[(0, 0), (0, 1)], labels={(0, 1): "A", (1, 1): "B", (0, 0): "C", (1, 0): "D"})
    open("/tmp/kit/selfcheck-plane.tikz", "w").write(g.code())
    print("ok")
