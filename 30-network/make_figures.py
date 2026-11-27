"""Build the network paper's local figures. Run from any directory."""
from pathlib import Path
import sys

PAPER = Path(__file__).resolve().parent
sys.path.insert(0, str(PAPER.parent / "figkit"))

from ixfig import Fig, arrow, box


def timeline():
    fig = Fig()
    for x, text in ((3.2, "source S"), (13.5, "receiver R")):
        box(fig, x, 0, text, w=3.7, h=0.9)
        fig.path([(x, -0.5), (x, -8.05)], "dashed edge")
    events = [
        (-1.65, True, "first copy with ticket"),
        (-3.10, False, "ticket and staging confirmed"),
        (-5.15, True, "last changes, seal and permission"),
        (-6.75, False, "installation acknowledged"),
    ]
    for y, outgoing, message in events:
        a, b = (3.2, 13.5) if outgoing else (13.5, 3.2)
        arrow(fig, (a, y), (b, y))
        fig.node(8.35, y + 0.44, message, "tiny")
    fig.node(0.75, -1.65, "serves Q", "tiny")
    fig.node(0.75, -4.75, "fences Q", "tiny")
    fig.node(16.35, -3.10, "stages Q", "tiny")
    fig.node(16.35, -5.90, "mounts Q", "tiny")
    fig.node(16.35, -7.05, "serves Q", "tiny")
    return fig


def routes():
    fig = Fig()
    for x, text in ((1.6, "entry E"), (8.7, "donor S"), (15.8, "receiver R")):
        box(fig, x, 0, text, w=3.2, h=1.0)
    arrow(fig, (3.2, 0), (7.1, 0))
    arrow(fig, (10.3, 0), (14.2, 0))
    fig.node(5.15, 0.52, "old route", "tiny")
    fig.node(12.25, 0.52, "forward Q", "tiny")
    fig.path([(1.6, -0.52), (1.6, -1.85), (15.8, -1.85)], "thin")
    arrow(fig, (15.8, -1.85), (15.8, -0.52))
    fig.node(8.7, -2.43, "next write to Q, after learning R from its acknowledgement", "tiny")
    return fig


if __name__ == "__main__":
    for name, figure in (("ticket-lot", timeline()), ("learned-route", routes())):
        (PAPER / "figures" / (name + ".tikz")).write_text(figure.code(), encoding="utf-8")
