"""Minimal content-stream interpreter: extracts filled/stroked vector paths
with absolute coordinates and CMYK colors from the Illustrator reference PDFs."""
import pypdf
from pypdf.generic import ContentStream

def mul(a, b):
    # 2D affine [a b c d e f] composition: a then b
    return [a[0]*b[0]+a[1]*b[2], a[0]*b[1]+a[1]*b[3],
            a[2]*b[0]+a[3]*b[2], a[2]*b[1]+a[3]*b[3],
            a[4]*b[0]+a[5]*b[2]+b[4], a[4]*b[1]+a[5]*b[3]+b[5]]

def apply(m, x, y):
    return (m[0]*x+m[2]*y+m[4], m[1]*x+m[3]*y+m[5])

def extract(path, include_xobjects=False):
    r = pypdf.PdfReader(path)
    page = r.pages[0]
    res = page['/Resources']
    out = []
    def run(content_ops, res, ctm0):
        gs = {'ctm': list(ctm0), 'fill': (0,0,0,1), 'stroke': (0,0,0,1), 'alpha': 1.0, 'lw': 1.0}
        stack = []
        cur = []      # list of subpaths; subpath = list of segments ('M',x,y)/('L',x,y)/('C',x1,y1,x2,y2,x3,y3)/('Z',)
        for operands, op in content_ops:
            op = op.decode() if isinstance(op, bytes) else op
            o = [float(v) if isinstance(v, (int, float)) or hasattr(v, 'as_numeric') else v for v in operands]
            m = gs['ctm']
            if op == 'q': stack.append(dict(gs, ctm=list(gs['ctm'])))
            elif op == 'Q': gs = stack.pop()
            elif op == 'cm': gs['ctm'] = mul([float(v) for v in operands], gs['ctm'])
            elif op == 'k': gs['fill'] = tuple(float(v) for v in operands)
            elif op == 'K': gs['stroke'] = tuple(float(v) for v in operands)
            elif op == 'g': gs['fill'] = (0,0,0,1-float(operands[0]))
            elif op == 'w': gs['lw'] = float(operands[0])
            elif op == 'gs':
                e = res['/ExtGState'][operands[0]]
                gs['alpha'] = float(e.get('/ca', 1))
            elif op == 'm': cur.append([('M',)+apply(m, *map(float, operands))])
            elif op == 'l': cur[-1].append(('L',)+apply(m, *map(float, operands)))
            elif op == 'c':
                v = list(map(float, operands))
                cur[-1].append(('C',)+apply(m,v[0],v[1])+apply(m,v[2],v[3])+apply(m,v[4],v[5]))
            elif op == 'v':
                v = list(map(float, operands)); last = cur[-1][-1][-2:]
                cur[-1].append(('C',)+last+apply(m,v[0],v[1])+apply(m,v[2],v[3]))
            elif op == 'y':
                v = list(map(float, operands)); p3 = apply(m,v[2],v[3])
                cur[-1].append(('C',)+apply(m,v[0],v[1])+p3+p3)
            elif op == 'h': cur[-1].append(('Z',))
            elif op == 're':
                x,y,w,h = map(float, operands)
                cur.append([('M',)+apply(m,x,y),('L',)+apply(m,x+w,y),('L',)+apply(m,x+w,y+h),('L',)+apply(m,x,y+h),('Z',)])
            elif op in ('f','F','f*','B','B*','b','b*','S','s'):
                kind = 'stroke' if op in ('S','s') else 'fill'
                out.append({'subpaths': cur, 'rule': 'evenodd' if '*' in op else 'nonzero',
                            'color': gs['stroke'] if kind=='stroke' else gs['fill'], 'alpha': gs['alpha'],
                            'kind': kind, 'lw': gs['lw']*abs(m[0]) if kind=='stroke' else 0})
                cur = []
            elif op == 'n': cur = []
            elif op == 'Do':
                xo = res['/XObject'][operands[0]]
                if include_xobjects:
                    mtx = [float(v) for v in xo.get('/Matrix', [1,0,0,1,0,0])]
                    run(ContentStream(xo, r).operations, xo['/Resources'], mul(mtx, gs['ctm']))
                else:
                    out.append({'xobject': operands[0], 'alpha': gs['alpha']})
        return out
    run(ContentStream(page.get_contents(), r).operations, res, [1,0,0,1,0,0])
    return out, [float(v) for v in page.mediabox]

def bbox(el):
    xs=[];ys=[]
    for sp in el['subpaths']:
        for s in sp:
            pts = s[1:]
            xs += pts[0::2]; ys += pts[1::2]
    return (min(xs),min(ys),max(xs),max(ys)) if xs else None
