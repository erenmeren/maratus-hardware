#!/usr/bin/env python3
"""Dimensioned drawing of the Core's cover lens, to send with a request for a quotation.
  out/tools/cadenv/bin/python tools/lens_drawing.py      (after tools/enclosure.py; needs rsvg-convert)
Reads mechanical/core/maratus-core-lens.dxf and writes maratus-core-lens-drawing.pdf beside it: A4 landscape, 1 : 1,
seen from the front. The sizes on the sheet are measured from the DXF, so the sheet cannot disagree with the file
that goes with it; thickness and seat come from tools/enclosure.py. What only a maker can say (glass type, inks,
print tolerance, edge finish) is asked for on the sheet, not stated."""
import datetime
import subprocess

import ezdxf
from ezdxf import path as dxfpath

import enclosure as e

DXF = e.BASE / "maratus-core-lens.dxf"
PDF = e.BASE / "maratus-core-lens-drawing.pdf"
LX, LY = 45.0, 58.0         # the lens's top left corner on the sheet, mm
# The mark's colour: owner, 2026-11-16, trial glass for the Yellow of out/maratus-core-colours.pdf
# (value from out/case-colours/options.json).
YELLOW = "#f7c200"


def hdim(xa, xb, y, text, cls=""):
    return (f'<path d="M{xa:.2f} {y:.2f}H{xb:.2f}M{xa:.2f} {y - 1.5:.2f}v3M{xb:.2f} {y - 1.5:.2f}v3"/>'
            f'<text class="{cls}" x="{(xa + xb) / 2:.2f}" y="{y - 0.9:.2f}" text-anchor="middle">{text}</text>')


def vdim(x, ya, yb, text, cls=""):
    return (f'<path d="M{x:.2f} {ya:.2f}V{yb:.2f}M{x - 1.5:.2f} {ya:.2f}h3M{x - 1.5:.2f} {yb:.2f}h3"/>'
            f'<text class="{cls}" transform="translate({x - 0.9:.2f} {(ya + yb) / 2:.2f}) rotate(-90)" text-anchor="middle">{text}</text>')


def main():
    lines, radius = {}, {}
    for ent in ezdxf.readfile(DXF).modelspace():
        lines.setdefault(ent.dxf.layer, []).append([(v.x, v.y) for v in dxfpath.make_path(ent).flattening(0.01)])
        if ent.dxftype() == "ARC":
            radius[ent.dxf.layer] = ent.dxf.radius
    box = {}
    for layer, segs in lines.items():
        xs, ys = [x for s in segs for x, _ in s], [y for s in segs for _, y in s]
        box[layer] = (min(xs), min(ys), max(xs), max(ys))
    ox0, oy0, ox1, oy1 = box["outline"]
    sx, sy = lambda x: LX + x - ox0, lambda y: LY + oy1 - y         # DXF (y up) -> sheet (y down)
    w, h = ox1 - ox0, oy1 - oy0
    wx0, wy0, wx1, wy1 = box["window"]
    ww, wh = wx1 - wx0, wy1 - wy0
    left, right, top, bottom = wx0 - ox0, ox1 - wx1, oy1 - wy1, wy0 - oy0
    assert abs(left - right) < 0.005, "the window is not centred"
    mx0, my0, mx1, my1 = box["mark"]
    seat = (e.OX1 - e.OX0 - 2 * e.RIM, e.OY1 - e.OY0 - 2 * e.RIM)
    play = (seat[0] - w) / 2
    assert abs(play - (seat[1] - h) / 2) < 0.005

    rect = lambda b, r, fill: (f'<rect x="{sx(b[0]):.2f}" y="{sy(b[3]):.2f}" width="{b[2] - b[0]:.2f}" height="{b[3] - b[1]:.2f}" '
                               f'rx="{r:.2f}" style="fill:{fill}"/>')
    mark = "".join('<path class="mark" d="M' + "L".join(f"{sx(x):.2f} {sy(y):.2f}" for x, y in s) + '"/>' for s in lines["mark"])
    cx = LX + w / 2
    draw = [rect(box["outline"], radius["outline"], "#dcdcdc"), rect(box["window"], radius["window"], "#fff"), mark,
            hdim(LX, LX + w, LY + h + 9, f"{w:.2f}"), vdim(LX - 8, LY, LY + h, f"{h:.2f}"),
            hdim(sx(wx0), sx(wx1), sy(wy1) + 16, f"{ww:.2f}"), vdim(sx(wx0) + 16, sy(wy1), sy(wy0), f"{wh:.2f}"),
            hdim(LX, sx(wx0), LY + h / 2, f"{left:.2f}", "s"), hdim(sx(wx1), LX + w, LY + h / 2, f"{right:.2f}", "s"),
            vdim(cx + 20, LY, sy(wy1), f"{top:.2f}", "s"), vdim(cx + 26, sy(wy0), LY + h, f"{bottom:.2f}", "s"),
            f'<text x="{LX + w + 3:.2f}" y="{LY + 2:.2f}">R{radius["outline"]:g} (4x)</text>',
            f'<text x="{sx(wx1) - 3:.2f}" y="{sy(wy1) + 7:.2f}" text-anchor="end">R{radius["window"]:g} (4x)</text>',
            f'<text class="s" x="{cx:.2f}" y="{sy(wy1) + 30:.2f}" text-anchor="middle">clear window</text>',
            f'<text class="s" x="{cx:.2f}" y="{LY + h + 16:.2f}" text-anchor="middle">grey area: black print on the rear face</text>']
    notes = [
        f"1  Outline {w:.2f} x {h:.2f}, four corners R{radius['outline']:g}. It lies in a seat of",
        f"    {seat[0]:.2f} x {seat[1]:.2f} ({play:.1f} play on every side): outline tolerance +/-0.10.",
        f"2  Thickness {e.LENS_T:.1f}.",
        "3  Trial part: clear cast acrylic (PMMA), cut to the outline, no print.",
        "4  Final part: clear glass, chemically strengthened. Glass type: your proposal.",
        "5  Print (final part only) on the rear face, the one towards the display:",
        "    opaque black everywhere outside the window.",
        f"6  Window {ww:.2f} x {wh:.2f}, corners R{radius['window']:g}, clear. Border: {left:.2f} left and right,",
        f"    {top:.2f} top, {bottom:.2f} bottom. Print position to the outline: please state yours.",
        f"7  Mark \"maratus\" in the bottom border, {mx1 - mx0:.2f} x {my1 - my0:.2f}, centred left to right,",
        f"    its middle {(my0 + my1) / 2 - oy0:.2f} above the bottom edge. Second colour: yellow, near {YELLOW}",
        "    (to be approved on a sample). Letter outlines: DXF layer \"mark\".",
        "8  Edges ground, small chamfer on both faces: please state your standard.",
        "9  Front face: no print. Anti-fingerprint coating: please quote as an option.",
        "10 File: maratus-core-lens.dxf, layers outline / window / mark, millimetres.",
        "11 Glass: 5 pieces. Please state tooling or screen charges, lead time,",
        "    your minimum order quantity and your minimum order value.",
    ]
    text = [f'<text class="t" x="20" y="24">Maratus Core cover lens</text>',
            f'<text x="20" y="31">Drawing for a quotation, {datetime.date.today().isoformat()}. Seen from the front. Scale 1 : 1 on A4. Millimetres.</text>',
            '<text class="s" x="20" y="196">Draft: not released for production. No part has been made from it yet.</text>']
    text += [f'<text x="158" y="{60 + 5.6 * i:.1f}" xml:space="preserve">{n.replace(chr(34), "&quot;")}</text>' for i, n in enumerate(notes)]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 297 210"><style>'
           'text{font:3px "Noto Sans";fill:#000;stroke:none} .s{font-size:2.4px} .t{font-size:7px;font-weight:600} '
           'path,rect{stroke:#000;stroke-width:.15;fill:none} .mark{stroke-width:.1}</style>'
           '<rect x="0" y="0" width="297" height="210" style="fill:#fff;stroke:none"/>' + "".join(draw + text) + "</svg>")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(PDF)], input=svg.encode(), check=True)
    print(f"lens {w:.2f} x {h:.2f} x {e.LENS_T:g}, R{radius['outline']:g}; window {ww:.2f} x {wh:.2f}, R{radius['window']:g}; border "
          f"{left:.2f} / {top:.2f} / {bottom:.2f}; mark {mx1 - mx0:.2f} x {my1 - my0:.2f} -> {PDF.name}")


if __name__ == "__main__":
    main()
