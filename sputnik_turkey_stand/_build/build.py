"""Builds the Sputnik Turkey stand print files (inside walls 3x3 panels 95x240 cm + top sign 195x40 cm)
from the vector elements of the China/Tunisia Illustrator files."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from pdfparse import extract
from textpath import Font
from geom import *

# REF_DIR: folder with the China/Tunisia Illustrator PDFs; FONT: Montserrat variable TTF (OFL, Google Fonts)
UP = os.environ.get('REF_DIR', '/root/.claude/uploads/7dee4b10-b218-5f4f-ac83-68808b1795e9/').rstrip('/') + '/'
SCR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.environ.get('FONT', os.path.join(SCR, 'fonts', 'Montserrat[wght].ttf'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCR, 'out')
os.makedirs(OUT, exist_ok=True)

# ---- colors (CMYK, as in the reference files) ----
ORANGE = (0, .45, 1, 0)        # background orange
TRI = (0, .496, 1, 0)          # logo triangle orange
BLACK = (0, 0, 0, 1)
WHITE = (0, 0, 0, 0)
DOT = (0, .27, .6, 0)          # = white dots at 40% opacity over ORANGE, flattened
QRBLACK = (.746, .676, .668, .898)

# ---- geometry ----
H = 240 * CM
PW = 95 * CM                   # panel width
GAP = 5 * CM                   # aluminium upright between panels (art under it is not printed)
WW = 3 * PW + 2 * GAP          # continuous wall canvas, 295 cm
BAND = 40 * CM
PX = [i * (PW + GAP) for i in range(3)]          # panel left edges on the wall canvas
PC = [x + PW / 2 for x in PX]                    # panel centers

# ---- reference elements ----
def shapes_of(els, idx):
    return [Shape(els[i]['subpaths'], els[i]['color'], els[i]['rule']) for i in idx]

L, _ = extract(UP + 'b68837d1-Inside_left_1.pdf')
C, _ = extract(UP + '62331ded-Inside_center_2.pdf')
T, _ = extract(UP + 'd47d5400-Upside_center_7.pdf')
REF_W = 8503.937

logo_small = shapes_of(T, range(1, 9))           # white letters + orange triangle
band_left_logos = shapes_of(L, range(27, 51))    # rotated logos for a band at x 0..40 cm
band_right_logos = shapes_of(C, range(27, 51))   # rotated logos for a band at the right edge of a 300 cm wall
logo_big = shapes_of(C, range(51, 59))           # black wordmark + triangle
qr_ring = shapes_of(L, [334])[0]
qr_inner = shapes_of(L, [335])[0]
qr_logo = shapes_of(L, range(340, 348))
arrowhead_left = shapes_of(L, [349])[0]
globe = shapes_of(L, [351, 352])
arrowhead_right = shapes_of(T, [10])[0]

LOGO_SMALL_W = group_bbox(logo_small)[2] - group_bbox(logo_small)[0]

FONT = Font(FONT_PATH, 680)

def text(s, cap, x, base, color, tracking=0):
    sp, adv = FONT.outline(s, tracking)
    k = cap / FONT.cap
    sh = Shape(sp, color).map(lambda px, py: (x + px * k, base + py * k))
    return sh, adv * k

def text_ink(s, cap):
    """ink extents (xmin, xmax) relative to pen start, at the given cap height"""
    sh, adv = text(s, cap, 0, 0, BLACK)
    b = sh.bbox()
    return b, adv

def dots(x0, y0, x1, y1, exclude=()):
    """Dot pattern of the reference (pitch 96.43 x 98.61 pt, dot 15.32 x 15.67 pt), only dots fully
    inside [x0,x1]x[y0,y1] and outside the exclusion rects. One compound path."""
    rx, ry = 15.32 / 2, 15.67 / 2
    sps = []
    i = 0
    while True:
        cx = 56.69 + i * 96.43
        if cx > x1: break
        i += 1
        if cx - rx < x0 or cx + rx > x1: continue
        for j in range(80):
            cy = 18.1 + j * 98.61
            if cy - ry < y0 or cy + ry > y1: continue
            if any(ex[0] - rx < cx < ex[2] + rx and ex[1] - ry < cy < ex[3] + ry for ex in exclude): continue
            sps.append(ellipse_sp(cx, cy, rx, ry))
    return Shape(sps, DOT, name='dots')

def top_logos(centers):
    out = []
    b = group_bbox(logo_small)
    for c in centers:
        out += place(logo_small, c, H - BAND / 2, anchor='c')
    return out

PILL_K = 1.2

# =============== LEFT WALL: QR + "BİZİ TAKİP EDİN" ===============
def left_wall():
    sh = [Shape([rect_sp(0, 0, WW, H)], ORANGE)]
    # QR block, centered in panel 2, same height as in the reference
    box = shapes_of(L, [51])[0]
    bb = box.bbox(); bw = bb[2] - bb[0]
    bx = PC[1] - bw / 2; by = bb[1]
    box = box.tr(bx - bb[0], 0)
    # pill
    k = PILL_K
    cap = 98.6 * k
    t_ink, t_adv = text_ink('BİZİ TAKİP EDİN', cap)
    ph = 387.6 * k
    pill_w = (50.5 + 292.6 + 75.7 + 126.5) * k + (t_ink[2] - t_ink[0])
    pill_x = PC[2] - pill_w / 2
    pill_cy = (bb[1] + bb[3]) / 2
    pill_y = pill_cy - ph / 2
    exclude = [box.bbox(), (pill_x, pill_y, pill_x + pill_w, pill_y + ph)]
    sh.append(dots(BAND, 0, WW, H - BAND, exclude))
    sh.append(Shape([poly_sp([(0, 0), (BAND, 0), (BAND, H - BAND), (WW, H - BAND), (WW, H), (0, H)])], BLACK))
    sh += band_left_logos
    sh += top_logos([PC[1], PC[2]])
    sh.append(box)
    sh += qr_block(bx + 197.7, bb[3] - 197.7)
    # arrow: tip 229.4 pt right of the QR box (as in the reference), line runs under the pill
    tip = bx + bw + 229.4
    ah = arrowhead_left; ab = ah.bbox()
    ah = ah.tr(tip - ab[0], pill_cy - (ab[1] + ab[3]) / 2)
    line_y = pill_cy - 22.5
    sh.append(Shape([rect_sp(tip + 36.4, line_y, pill_x + ph / 2 - (tip + 36.4), 45)], BLACK))  # ends under the pill
    sh.append(ah)
    sh.append(Shape([stadium_sp(pill_x, pill_y, pill_w, ph)], BLACK))
    sh += place(globe, pill_x + 50.5 * k, pill_cy - 292.6 * k / 2, scale=k)
    tx = pill_x + (50.5 + 292.6 + 75.7) * k - t_ink[0]
    t, _ = text('BİZİ TAKİP EDİN', cap, tx, pill_cy - cap / 2, ORANGE)
    sh.append(t)
    return sh

def qr_block(qx, qtop):
    """Rebuilds the supplied QR (https://qrco.de/bh0UET) in the reference dot style."""
    M = json.load(open(os.path.join(os.path.dirname(__file__), 'qr_matrix.json')))
    N = len(M); m = 1457.8 / 29
    out = []
    finders = [(0, 0), (N - 7, 0), (0, N - 7)]
    def in_finder(r, c):
        return any(fr <= r < fr + 7 and fc <= c < fc + 7 for fc, fr in finders)
    sps = []
    for r in range(N):
        for c in range(N):
            if M[r][c] and not in_finder(r, c):
                sps.append(ellipse_sp(qx + (c + .5) * m, qtop - (r + .5) * m, m / 2, m / 2))
    out.append(Shape(sps, QRBLACK))
    rb = qr_ring.bbox()
    for fc, fr in finders:
        dx = qx + fc * m - rb[0]; dy = qtop - fr * m - rb[3]
        out.append(qr_ring.tr(dx, dy).recolor(QRBLACK))
        out.append(qr_inner.tr(dx, dy).recolor(QRBLACK))
    # center logo at the position/size it has in the supplied PNG (triangle bbox in module units)
    lb = group_bbox(qr_logo)
    s = (6.565 * m) / (lb[2] - lb[0])
    out += place(qr_logo, qx + 10.98 * m, qtop - 17.82 * m, scale=s)
    return out

# =============== BACK WALL: big logo ===============
def back_wall():
    sh = [Shape([rect_sp(0, 0, WW, H)], ORANGE)]
    b = group_bbox(logo_big)
    big = place(logo_big, WW / 2, (b[1] + b[3]) / 2, anchor='c')
    sh.append(dots(0, 0, WW, H - BAND))
    sh.append(Shape([rect_sp(0, H - BAND, WW, BAND)], BLACK))
    sh += top_logos(PC)
    sh += big
    return sh

# =============== RIGHT WALL: slogan ===============
SLOGAN = ('Anlatılmayanları', 'anlatıyoruz')
def right_wall(cap=None, x0=None, base1=None):
    sh = [Shape([rect_sp(0, 0, WW, H)], ORANGE)]
    sh.append(dots(0, 0, WW - BAND, H - BAND))
    sh.append(Shape([poly_sp([(0, H - BAND), (WW - BAND, H - BAND), (WW - BAND, 0), (WW, 0), (WW, H), (0, H)])], BLACK))
    sh += gtr(band_right_logos, WW - REF_W, 0)
    sh += top_logos([PC[0], PC[1]])
    lead = cap / 0.7 * 1.08
    for i, line in enumerate(SLOGAN):
        ink, _ = text_ink(line, cap)
        t, _ = text(line, cap, x0 - ink[0], base1 - i * lead, BLACK)
        sh.append(t)
    return sh

# =============== TOP SIGN 195 x 40 ===============
TW, TH = 195 * CM, 40 * CM
def top_sign(logo_w, cap, margin, gap):
    sh = [Shape([rect_sp(0, 0, TW, TH)], BLACK)]
    lg = place(logo_small, margin, TH / 2, scale=logo_w / LOGO_SMALL_W)
    lb = group_bbox(lg)
    lg = gtr(lg, 0, TH / 2 - (lb[1] + lb[3]) / 2)
    sh += lg
    line = 'Anlatılmayanları anlatıyoruz'
    ink, _ = text_ink(line, cap)
    tx_end = TW - margin
    tx = tx_end - (ink[2] - ink[0])
    t, _ = text(line, cap, tx - ink[0], TH / 2 - cap / 2, WHITE)
    # arrow between logo and text (reference proportions: 45 pt line, head 152 x 297.5 pt)
    k = cap / 193.7
    a0 = group_bbox(lg)[2] + gap
    a1 = tx - gap
    ah = arrowhead_right; ab = ah.bbox()
    ah = place([ah], a1, TH / 2, scale=k, anchor='ll')
    hb = group_bbox(ah)
    ah = gtr(ah, -(hb[2] - hb[0]), TH / 2 - (hb[1] + hb[3]) / 2)
    sh.append(Shape([rect_sp(a0, TH / 2 - 22.5 * k, a1 - a0 - 30 * k, 45 * k)], WHITE))
    sh += ah
    sh.append(t)
    return sh, (a1 - a0) / CM

def _clip_poly_x(pts, x0, x1):
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            if inside(b):
                if not inside(a): out.append(inter(a, b))
                out.append(b)
            elif inside(a):
                out.append(inter(a, b))
        return out
    def ix(xv):
        return lambda a, b: (xv, a[1] + (b[1] - a[1]) * (xv - a[0]) / (b[0] - a[0]))
    pts = clip(pts, lambda p: p[0] >= x0, ix(x0))
    return clip(pts, lambda p: p[0] <= x1, ix(x1)) if pts else pts

def panel_shapes(wall, x):
    """Shapes of one panel, moved to panel coordinates; straight-edged areas are cut exactly at
    the panel edges, compound patterns keep only the subpaths that touch the panel."""
    out = []
    for s in wall:
        b = s.bbox()
        if b[2] <= x or b[0] >= x + PW: continue
        if all(seg[0] in 'MLZ' for sp in s.subpaths for seg in sp):
            sps = []
            for sp in s.subpaths:
                pts = [seg[1:] for seg in sp if seg[0] != 'Z']
                c = _clip_poly_x(pts, x, x + PW)
                if len(c) >= 3: sps.append(poly_sp(c))
            if sps: out.append(Shape(sps, s.color, s.rule, s.name).tr(-x, 0))
        elif s.name == 'dots':
            sps = [sp for sp in s.subpaths
                   if max(v for seg in sp for v in seg[1::2]) > x and min(v for seg in sp for v in seg[1::2]) < x + PW]
            if sps: out.append(Shape(sps, s.color, s.rule, s.name).tr(-x, 0))
        else:
            out.append(s.tr(-x, 0))
    return out

WALLS = [('L', 'Inside_left', left_wall), ('C', 'Inside_center', back_wall), ('R', 'Inside_right', right_wall)]

def build_all(top_variant='2lines'):
    walls = {}
    walls['L'] = left_wall()
    walls['C'] = back_wall()
    walls['R'] = right_wall(cap=16 * CM, x0=19 * CM, base1=(170 - 16) * CM)
    files = []
    n = 0
    for key, name, _ in WALLS:
        for i, x in enumerate(PX):
            n += 1
            fn = 'SPUTNIK_TR_%s%d_95x240cm.pdf' % (key, i + 1)
            write_pdf(os.path.join(OUT, fn), [(PW, H, panel_shapes(walls[key], x))], 'Sputnik TR %s%d 95x240 cm' % (key, i + 1))
            files.append(fn)
    top, _ = top_sign(40 * CM, 40 * CM * 168.9 / 1417.3, 12 * CM, 6 * CM)
    fn = 'SPUTNIK_TR_Top_195x40cm.pdf'
    write_pdf(os.path.join(OUT, fn), [(TW, TH, top)], 'Sputnik TR top sign 195x40 cm')
    files.append(fn)
    return walls, top, files

if __name__ == '__main__':
    walls, top, files = build_all()
    # full-wall previews (continuous canvas incl. 5 cm uprights) for checking
    for k, w in walls.items():
        write_pdf(os.path.join(OUT, '_wall_%s.pdf' % k), [(WW, H, w)], 'wall ' + k)
    print(files)
