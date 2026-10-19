"""Simple perspective preview of the inside of the U-shaped stand (for approval only)."""
import sys, os, subprocess
import numpy as np, cv2

FIN, PREV = sys.argv[1], sys.argv[2]
PPCM = 10
def render(pdf, name):
    subprocess.run(['pdftoppm', '-r', str(int(PPCM * 2.54)), '-png', '-singlefile', pdf, os.path.join(PREV, name)], check=True)
    return cv2.imread(os.path.join(PREV, name + '.png'))

ALU = (196, 196, 192)
walls = {}
for k in 'LCR':
    im = render(os.path.join(FIN, '_wall_%s.pdf' % k), 'tex_' + k)
    for g in (95, 195):   # uprights
        cv2.rectangle(im, (int(g * PPCM * 2.54 / 2.54), 0), (int((g + 5) * PPCM), im.shape[0]), ALU, -1)
    walls[k] = im
top = render(os.path.join(FIN, 'SPUTNIK_TR_Top_195x40cm.pdf'), 'tex_top')

Wd, Hd = 1800, 1350

def view(cam, yaw_deg, f=1250.0):
    cam = np.array(cam); yaw = np.radians(yaw_deg)
    cx, cy = Wd / 2, Hd * 0.5
    def P(x, y, z):
        dx, dy, dz = x - cam[0], y - cam[1], z - cam[2]
        xc = dx * np.cos(yaw) - dz * np.sin(yaw)
        zc = dx * np.sin(yaw) + dz * np.cos(yaw)
        return (cx + f * xc / zc, cy - f * dy / zc)
    canvas = np.zeros((Hd, Wd, 3), np.uint8)
    for yy in range(Hd):
        v = int(236 - 26 * yy / Hd)
        canvas[yy, :] = (v, v, v - 4)
    hz = int(P(0, cam[1], 50)[1])
    cv2.fillPoly(canvas, [np.int32([(0, hz), (Wd, hz), (Wd, Hd), (0, Hd)])], (208, 208, 204))
    cv2.fillPoly(canvas, [np.int32([P(-1.5, 0, 0), P(1.5, 0, 0), P(1.5, 0, 3), P(-1.5, 0, 3)])], (72, 70, 68))
    def warp(tex, quad):
        nonlocal canvas
        h, w = tex.shape[:2]
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        M = cv2.getPerspectiveTransform(src, np.float32(quad))
        out = cv2.warpPerspective(tex, M, (Wd, Hd), flags=cv2.INTER_AREA)
        mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), M, (Wd, Hd), flags=cv2.INTER_AREA)
        a = (mask.astype(np.float32) / 255)[..., None]
        canvas = (canvas * (1 - a) + out * a).astype(np.uint8)
    warp(walls['C'], [P(-1.5, 2.4, 3), P(1.5, 2.4, 3), P(1.5, 0, 3), P(-1.5, 0, 3)])
    warp(walls['L'], [P(-1.5, 2.4, 0), P(-1.5, 2.4, 3), P(-1.5, 0, 3), P(-1.5, 0, 0)])
    warp(walls['R'], [P(1.5, 2.4, 3), P(1.5, 2.4, 0), P(1.5, 0, 0), P(1.5, 0, 3)])
    for x in (-1.5, 1.5):
        cv2.fillPoly(canvas, [np.int32([P(x - .025, 2.45, 0), P(x + .025, 2.45, 0), P(x + .025, 0, 0), P(x - .025, 0, 0)])], ALU)
    cv2.fillPoly(canvas, [np.int32([P(-1.525, 2.45, 0), P(1.525, 2.45, 0), P(1.525, 2.4, 0), P(-1.525, 2.4, 0)])], ALU)
    warp(top, [P(-.975, 2.4, 0), P(.975, 2.4, 0), P(.975, 2.0, 0), P(-.975, 2.0, 0)])
    return canvas

a = view((1.55, 1.6, -2.3), -24)    # from front-right: left wall (QR) + back wall
b = view((-1.55, 1.6, -2.3), 24)    # from front-left: back wall + right wall (slogan)
both = np.concatenate([a, np.full((Hd, 16, 3), 255, np.uint8), b], axis=1)
cv2.imwrite(os.path.join(FIN, 'SPUTNIK_TR_Preview.jpg'), both, [cv2.IMWRITE_JPEG_QUALITY, 88])
