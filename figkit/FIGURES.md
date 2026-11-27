# Figures: the author's style (mandatory)

The author drew his 2024 figures in TikZiT. Every figure of the series must look
like them, be vector (zoomable), and be consistent with the others.

For a visual reference, render pages from the archived PDFs in
`client-algorithm/` and `p2p-protocol/` at 150 dpi. Their original TikZiT
drawings are also available as sources in `figkit/orig/`.

## Use
- `\usepackage{../figkit/ixfig}` (after `../common/indexus`).
- The author's figures: include his TikZ source, never the PNG:
  `\ixfig[12cm]{../figkit/orig/encoded.tikz}` (also tree, masks, collection,
  layers, p2p-network, p2p-routing, p2p-delegation-1/2/3). Do not edit them.
- New figures: generate them with `figkit/ixfig.py`
  (tree16, plane, table, box, arrow) or write TikZiT-style code by hand
  with the same styles, save as figures/NAME.tikz, include with
  `\ixnew{figures/NAME.tikz}` (fixed scale 0.62 cm per unit, constant tiny
  font and line widths across all figures). Never resizebox a new figure.

## The vocabulary of the author's drawings (keep exactly)
- Tree: the 16-leaf BASE4 tree, ultra thin grey lines, leaf labels in tiny,
  left leaves one row higher than right leaves (staggered), root at the top.
  A network shows only the branches of its nodes (p2p-network).
- A node: its path from the root drawn `thick` (black, very thick).
- A zone address: its path drawn `dashed edge`, from where it leaves a thick
  path down to its leaf (delegation figures).
- Space / zones: isometric planes (parallelograms), one plane per level,
  stacked vertically; a zone in use is a `surface` (light grey) tile;
  labels A, B, C, D or @ in the middle of a tile.
- Records: `item` (dark grey dots) on the lowest plane; dashed grid lines.
- Data: small thin-bordered two-column tables with tiny text (collection).
- New, only if needed: `arrow` (thin, small stealth head) for messages;
  `box` (thin rectangle, tiny label) for a client, a node, a disk.
  No rounded corners, no colours, no bold text, no shading other than the
  two greys (surface, dark surface), no legends inside the figure.
- One idea per figure. Few labels. Reuse the same network (AB, AC, AD, BC,
  CA, CC, DA, DB, DD) and the same collection BB everywhere, as the
  originals do, so that figures read as one story.
- Caption: "Figure N: short noun phrase", like "Figure 3: Network of nodes".
