"""Shape primitives, transforms and a minimal CMYK vector PDF writer."""
import zlib, math

CM = 72 / 2.54
K = 0.5522847498

class Shape:
    def __init__(self, subpaths, color, rule='nonzero', name=''):
        self.subpaths, self.color, self.rule, self.name = subpaths, tuple(color), rule, name

    def bbox(self):
        xs, ys = [], []
        for sp in self.subpaths:
            for s in sp:
                xs += s[1::2]; ys += s[2::2]
        return min(xs), min(ys), max(xs), max(ys)

    def map(self, f):
        out = []
        for sp in self.subpaths:
            nsp = []
            for s in sp:
                if s[0] == 'Z':
                    nsp.append(s); continue
                pts = []
                for i in range(1, len(s), 2):
                    pts += f(s[i], s[i + 1])
                nsp.append((s[0],) + tuple(pts))
            out.append(nsp)
        return Shape(out, self.color, self.rule, self.name)

    def tr(self, dx, dy):
        return self.map(lambda x, y: (x + dx, y + dy))

    def sc(self, s, ox=0, oy=0):
        return self.map(lambda x, y: (ox + (x - ox) * s, oy + (y - oy) * s))

    def recolor(self, c):
        return Shape(self.subpaths, c, self.rule, self.name)


def group_bbox(shapes):
    bs = [s.bbox() for s in shapes]
    return min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)

def gmap(shapes, f):
    return [s.map(f) for s in shapes]

def gtr(shapes, dx, dy):
    return [s.tr(dx, dy) for s in shapes]

def gsc(shapes, s, ox=0, oy=0):
    return [x.sc(s, ox, oy) for x in shapes]

def place(shapes, x, y, scale=1.0, anchor='ll'):
    """Scale a group and put its bbox lower-left (or center: anchor='c') at x, y."""
    b = group_bbox(shapes)
    w, h = (b[2] - b[0]) * scale, (b[3] - b[1]) * scale
    if anchor == 'c':
        x, y = x - w / 2, y - h / 2
    return gmap(shapes, lambda px, py: (x + (px - b[0]) * scale, y + (py - b[1]) * scale))

def rect_sp(x, y, w, h):
    return [('M', x, y), ('L', x + w, y), ('L', x + w, y + h), ('L', x, y + h), ('Z',)]

def poly_sp(pts):
    return [('M',) + pts[0]] + [('L',) + p for p in pts[1:]] + [('Z',)]

def ellipse_sp(cx, cy, rx, ry):
    kx, ky = rx * K, ry * K
    return [('M', cx + rx, cy),
            ('C', cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry),
            ('C', cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy),
            ('C', cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry),
            ('C', cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy), ('Z',)]

def stadium_sp(x, y, w, h):
    r = h / 2; k = r * K
    return [('M', x + r, y), ('L', x + w - r, y),
            ('C', x + w - r + k, y, x + w, y + r - k, x + w, y + r),
            ('C', x + w, y + r + k, x + w - r + k, y + h, x + w - r, y + h),
            ('L', x + r, y + h),
            ('C', x + r - k, y + h, x, y + r + k, x, y + r),
            ('C', x, y + r - k, x + r - k, y, x + r, y), ('Z',)]


def _num(v):
    s = '%.3f' % v
    s = s.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s

def content_stream(shapes, clip=None):
    out = []
    if clip:
        out.append('q %s %s %s %s re W n' % tuple(_num(v) for v in clip))
    last = None
    for s in shapes:
        if s.color != last:
            out.append('%s k' % ' '.join(_num(c) for c in s.color)); last = s.color
        for sp in s.subpaths:
            for seg in sp:
                if seg[0] == 'M': out.append('%s %s m' % (_num(seg[1]), _num(seg[2])))
                elif seg[0] == 'L': out.append('%s %s l' % (_num(seg[1]), _num(seg[2])))
                elif seg[0] == 'C': out.append('%s c' % ' '.join(_num(v) for v in seg[1:]))
                elif seg[0] == 'Z': out.append('h')
        out.append('f*' if s.rule == 'evenodd' else 'f')
    if clip:
        out.append('Q')
    return '\n'.join(out).encode()

def _pdfstr(t):
    return '(' + t.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') + ')'

def write_pdf(path, pages, title):
    """pages: list of (width_pt, height_pt, shapes). Exact-size pages (Media=Trim=Bleed),
    CMYK fills only, clipped to the page."""
    objs = []
    def add(b):
        objs.append(b); return len(objs)
    cat = add(None); pages_id = add(None)
    kids = []
    for w, h, shapes in pages:
        data = zlib.compress(content_stream(shapes, clip=(0, 0, w, h)), 9)
        cid = add(b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(data) + data + b'\nendstream')
        box = '[0 0 %s %s]' % (_num(w), _num(h))
        pid = add(('<< /Type /Page /Parent %d 0 R /MediaBox %s /TrimBox %s /BleedBox %s /CropBox %s '
                   '/Resources << >> /Contents %d 0 R >>' % (pages_id, box, box, box, box, cid)).encode())
        kids.append(pid)
    objs[cat - 1] = ('<< /Type /Catalog /Pages %d 0 R >>' % pages_id).encode()
    objs[pages_id - 1] = ('<< /Type /Pages /Kids [%s] /Count %d >>' % (' '.join('%d 0 R' % k for k in kids), len(kids))).encode()
    info = add(('<< /Title %s /Creator (Sputnik stand layout) /Producer (vector build, CMYK) >>' % _pdfstr(title)).encode())
    out = bytearray(b'%PDF-1.6\n%\xe2\xe3\xcf\xd3\n')
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for o in offs:
        out += b'%010d 00000 n \n' % o
    out += b'trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, cat, info, xref)
    open(path, 'wb').write(out)
