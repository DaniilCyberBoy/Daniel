"""Shape text with HarfBuzz (kerning included) and return glyph outlines as
path segments in font units, ready to be scaled into PDF coordinates."""
import uharfbuzz as hb
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

class Font:
    def __init__(self, path, wght=None):
        blob = hb.Blob.from_file_path(path)
        self.face = hb.Face(blob)
        self.font = hb.Font(self.face)
        if wght is not None:
            self.font.set_variations({'wght': wght})
        self.upem = self.face.upem
        tt = TTFont(path)
        self.cap = tt['OS/2'].sCapHeight
        self.xh = tt['OS/2'].sxHeight

    def outline(self, text, tracking=0):
        """Returns (subpaths, advance) in font units, baseline at y=0, x from 0."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        buf.language = 'tr'
        hb.shape(self.font, buf, {'kern': True, 'liga': True})
        x = 0
        subpaths = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            pen = RecordingPen()
            self.font.draw_glyph_with_pen(info.codepoint, pen)
            ox, oy = x + pos.x_offset, pos.y_offset
            cur = None
            for op, pts in pen.value:
                P = [(px + ox, py + oy) for px, py in pts]
                if op == 'moveTo':
                    cur = [('M',) + P[0]]; subpaths.append(cur)
                elif op == 'lineTo':
                    cur.append(('L',) + P[0])
                elif op == 'curveTo':
                    cur.append(('C',) + P[0] + P[1] + P[2])
                elif op == 'qCurveTo':
                    # convert quadratic spline (TrueType) to cubic segments
                    last = cur[-1][-2:]
                    qs = list(P)
                    # implied on-curve points between consecutive off-curve points
                    on = qs[-1]; offs = qs[:-1]
                    pts2 = []
                    for i, q in enumerate(offs):
                        if i < len(offs) - 1:
                            nxt = offs[i + 1]
                            end = ((q[0] + nxt[0]) / 2, (q[1] + nxt[1]) / 2)
                        else:
                            end = on
                        pts2.append((q, end))
                    p0 = last
                    for q, e in pts2:
                        c1 = (p0[0] + 2/3*(q[0]-p0[0]), p0[1] + 2/3*(q[1]-p0[1]))
                        c2 = (e[0] + 2/3*(q[0]-e[0]), e[1] + 2/3*(q[1]-e[1]))
                        cur.append(('C',) + c1 + c2 + e)
                        p0 = e
                elif op in ('closePath', 'endPath'):
                    cur.append(('Z',))
            x += pos.x_advance + tracking
        return subpaths, x - tracking
