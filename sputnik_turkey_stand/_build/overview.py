"""Layout sheet (A3 landscape, 1:25) showing where every print file goes, plus a perspective preview."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build import *

OUTD = sys.argv[1]
GREY = (0, 0, 0, .35)
LIGHT = (0, 0, 0, .08)
INK = (0, 0, 0, 1)
S = 1 / 25.0
A3W, A3H = 42 * CM, 29.7 * CM

def label(s, size_cm, x, y, color=INK, anchor='l'):
    cap = size_cm * CM
    t, adv = text(s, cap, 0, 0, color)
    b = t.bbox()
    w = b[2] - b[0]
    dx = {'l': 0, 'c': -w / 2, 'r': -w}[anchor]
    return t.tr(x + dx - b[0], y)

def build_sheet(walls, top):
    sh = [Shape([rect_sp(0, 0, A3W, A3H)], (0, 0, 0, 0))]
    sh.append(label('SPUTNIK — Türkiye, stand 3 × 3 m (9 m²), U-shape, inside walls', .55, 1.5 * CM, A3H - 2.2 * CM))
    sh.append(label('9 panels 95 × 240 cm + top sign 195 × 40 cm · scale 1:1 print files, CMYK, text outlined · this sheet 1:25',
                    .3, 1.5 * CM, A3H - 3.0 * CM, GREY))
    y0 = A3H - 4.2 * CM - H * S
    x = 1.5 * CM
    names = {'L': 'LEFT WALL (inside)', 'C': 'BACK WALL (inside)', 'R': 'RIGHT WALL (inside)'}
    for key in 'LCR':
        wall = walls[key]
        wx = x
        for i, px in enumerate(PX):
            ps = panel_shapes(wall, px)
            sh += [s.map(lambda a, b, ox=wx + px * S: (ox + a * S, y0 + b * S)) for s in ps]
            sh.append(label('%s%d' % (key, i + 1), .38, wx + (px + PW / 2) * S, y0 - .75 * CM, INK, 'c'))
            sh.append(label('95 × 240', .22, wx + (px + PW / 2) * S, y0 - 1.25 * CM, GREY, 'c'))
        for gx in (PX[1] - GAP, PX[2] - GAP):
            sh.append(Shape([rect_sp(wx + gx * S, y0, GAP * S, H * S)], GREY))
        sh.append(label(names[key], .3, wx + WW * S / 2, y0 + H * S + .35 * CM, INK, 'c'))
        x += WW * S + 1.1 * CM
    # top sign
    ty = y0 - 2.4 * CM - TH * S
    tx = 1.5 * CM
    sh += [s.map(lambda a, b: (tx + a * S, ty + b * S)) for s in top]
    sh.append(label('TOP SIGN  195 × 40 cm', .3, tx + TW * S + .6 * CM, ty + TH * S / 2 - .15 * CM))
    # plan view
    px0, py0, sc = 1.5 * CM, 2.2 * CM, 1 / 60.0
    side = 300 * CM * sc
    th = 4 * CM * sc * 3
    sh.append(Shape([rect_sp(px0, py0, side, side)], LIGHT))
    sh.append(Shape([rect_sp(px0, py0, th, side), rect_sp(px0, py0 + side - th, side, th),
                     rect_sp(px0 + side - th, py0, th, side)], INK))
    sh.append(label('L1', .25, px0 + th + .25 * CM, py0 + .3 * CM))
    sh.append(label('L3', .25, px0 + th + .25 * CM, py0 + side - th - .6 * CM))
    sh.append(label('C1', .25, px0 + th + .9 * CM, py0 + side - th - .6 * CM))
    sh.append(label('C3', .25, px0 + side - th - .9 * CM, py0 + side - th - .6 * CM, INK, 'r'))
    sh.append(label('R1', .25, px0 + side - th - .25 * CM, py0 + side - th - 1.2 * CM, INK, 'r'))
    sh.append(label('R3', .25, px0 + side - th - .25 * CM, py0 + .3 * CM, INK, 'r'))
    sh.append(label('open side / aisle', .25, px0 + side / 2, py0 - .6 * CM, GREY, 'c'))
    sh.append(label("PLAN 1:60", .3, px0 + side + 1.2 * CM, py0 + side - .3 * CM))
    notes = ['Panels numbered left → right as seen from inside the stand.',
             'Grey bars = aluminium uprights (assumed 5 cm): artwork runs continuously',
             'behind them, so letters line up across panels.',
             'Outside of the walls: no print (closed by neighbouring stands).',
             'Reception counter: printed by the organisers (logo sent separately).',
             'QR → https://qrco.de/bh0UET (rebuilt as vector, scan-tested).']
    for i, n in enumerate(notes):
        sh.append(label(n, .26, px0 + side + 1.2 * CM, py0 + side - 1.3 * CM - i * .6 * CM, INK))
    return sh

if __name__ == '__main__':
    walls = {'L': left_wall(), 'C': back_wall(),
             'R': right_wall(cap=16 * CM, x0=19 * CM, base1=(170 - 16) * CM)}
    top, _ = top_sign(40 * CM, 40 * CM * 168.9 / 1417.3, 12 * CM, 6 * CM)
    write_pdf(os.path.join(OUTD, 'SPUTNIK_TR_Layout_A3.pdf'), [(A3W, A3H, build_sheet(walls, top))], 'Sputnik TR stand layout')
