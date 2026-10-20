#!/usr/bin/env python3
"""GOBAGS Instagram Cover v2 — format-aware (feed/reel/story), Penpot layouts, brand grade.
Subcommands: frames | select | grades | layouts | overlays | export"""
VERSION = "2.2"
import argparse, json, os, subprocess, sys, urllib.request, datetime, tempfile, shutil
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

FORMATS = {  # size, area shown on the profile grid (None = n/a), text-safe zone note
 'feed':  dict(size=(1080, 1350), grid=(34, 0, 1046, 1350), guides=[]),
 'reel':  dict(size=(1080, 1920), grid=(34, 285, 1046, 1635), guides=[285, 1635]),
 'story': dict(size=(1080, 1920), grid=None, guides=[250, 1670]),
}
EMBER, BIRCH, INK, DARK = (223, 92, 38), (239, 236, 231), (26, 26, 26), (59, 59, 59)
REF = dict(L_med=36.0, a=3.3, b=11.6)   # measured from the team's 4 "Good" reference covers
FONT_DIR = os.path.expanduser('~/.cache/gobags-cover/fonts')
FONTS = {'head': 'barlowcondensed/BarlowCondensed-Black.ttf', 'semi': 'barlowcondensed/BarlowCondensed-SemiBold.ttf',
         'label': 'barlowcondensed/BarlowCondensed-Medium.ttf', 'body': 'barlow/Barlow-Medium.ttf', 'mono': 'dmmono/DMMono-Medium.ttf'}
GRADES = [('A', 'Light', 0.45), ('B', 'Signature', 0.85), ('C', 'Bold', 1.25)]
OVERLAYS = [('1', 'Subtle', 0.10, 0.30), ('2', 'Standard', 0.18, 0.48), ('3', 'Strong', 0.30, 0.62)]  # flat tint, band behind text
VIDEO_EXT = ('.mov', '.mp4', '.m4v', '.avi', '.mkv')

# Penpot "GOBAGS Design System / 10 Instagram" — [role, x, y, w, h, font, size, lineHeight, align, caps, color D/E/W]
LAYOUTS = json.loads(r'''{"Feed / 01 Section":[["handle",80,120,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,96,43,51,"label",42,1.2,"left",1,"E"],["num",80,459,47,51,"label",42,1.2,"left",1,"E"],["title",80,515,920,288,"head",120,1.2,"left",1,"D"],["sub",80,1203,273,51,"label",42,1.2,"left",1,"E"]],"Feed / 02 Cover":[["title",80,100,920,288,"head",120,1.2,"left",1,"D"],["sub",80,702,920,77,"semi",64,1.2,"left",1,"E"],["handle",80,1201,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,1177,43,51,"label",42,1.2,"left",1,"E"]],"Feed / 03 Long Statement":[["handle",80,120,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,96,43,51,"label",42,1.2,"left",1,"E"],["title",80,405,920,432,"head",120,1.2,"left",1,"D"],["sub",80,1203,273,51,"label",42,1.2,"left",1,"E"]],"Feed / 04 Headline":[["title",80,405,920,144,"head",120,1.2,"left",1,"D"],["sub",80,665,920,77,"semi",64,1.2,"left",1,"E"]],"Feed / 05 Body Copy":[["handle",80,120,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,96,43,51,"label",42,1.2,"left",1,"E"],["body",80,405,756,260,"body",36,1.2,"left",0,"D"]],"Feed / 06 Image + Caption":[["handle",80,120,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,96,43,51,"label",42,1.2,"left",1,"E"],["title",80,237,920,77,"semi",64,1.2,"center",1,"D"],["img",80,354,920,773],["body",140,1167,800,87,"body",36,1.2,"center",0,"D"]],"Feed / 07 Full Bleed Image":[["img",0,0,1080,1350],["handle",80,120,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,96,43,51,"label",42,1.2,"left",1,"E"],["title",80,1007,284,77,"semi",64,1.2,"left",1,"W"],["body",80,1100,702,87,"body",36,1.2,"left",0,"W"]],"Feed / 08 Centered Headline":[["title",80,100,920,144,"head",120,1.2,"center",1,"D"],["sub",80,370,920,51,"label",42,1.2,"center",1,"E"],["handle",80,1201,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,1177,43,51,"label",42,1.2,"left",1,"E"]],"Feed / 09 Two Images Bleed":[["img",0,0,1080,663],["img",0,687,1080,663]],"Feed / 10 Single Image":[["img",80,80,920,1190]],"Feed / 11 Two Images":[["img",80,80,920,575],["img",80,695,920,575]],"Reel / 01 Section":[["handle",80,244,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,220,43,51,"label",42,1.2,"left",1,"E"],["num",80,653,47,51,"label",42,1.2,"left",1,"E"],["title",80,709,920,288,"head",120,1.2,"left",1,"D"],["sub",80,1429,273,51,"label",42,1.2,"left",1,"E"]],"Reel / 02 Centered Headline":[["title",80,260,920,144,"head",120,1.2,"center",1,"D"],["sub",80,428,920,51,"label",42,1.2,"center",1,"E"],["handle",80,1447,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,1423,43,51,"label",42,1.2,"left",1,"E"]],"Reel / 03 Headline":[["title",80,576,920,144,"head",120,1.2,"left",1,"D"],["sub",80,836,920,77,"semi",64,1.2,"left",1,"E"]],"Reel / 04 Long Statement":[["handle",80,244,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,220,43,51,"label",42,1.2,"left",1,"E"],["title",80,576,920,432,"head",120,1.2,"left",1,"D"],["sub",80,1429,273,51,"label",42,1.2,"left",1,"E"]],"Story / 01 Section":[["handle",80,274,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,250,43,51,"label",42,1.2,"left",1,"E"],["num",80,653,47,51,"label",42,1.2,"left",1,"E"],["title",80,709,920,288,"head",120,1.2,"left",1,"D"],["sub",80,1599,273,51,"label",42,1.2,"left",1,"E"]],"Story / 02 Cover":[["title",80,290,920,288,"head",120,1.2,"left",1,"D"],["sub",80,998,920,77,"semi",64,1.2,"left",1,"E"],["handle",80,1617,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,1593,43,51,"label",42,1.2,"left",1,"E"]],"Story / 03 Long Statement":[["handle",80,274,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,250,43,51,"label",42,1.2,"left",1,"E"],["title",80,576,920,432,"head",120,1.2,"left",1,"D"],["sub",80,1599,273,51,"label",42,1.2,"left",1,"E"]],"Story / 04 Headline":[["title",80,576,920,144,"head",120,1.2,"left",1,"D"],["sub",80,836,920,77,"semi",64,1.2,"left",1,"E"]],"Story / 05 Body Copy":[["handle",80,274,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,250,43,51,"label",42,1.2,"left",1,"E"],["body",80,576,756,260,"body",36,1.2,"left",0,"D"]],"Story / 06 Image + Caption":[["handle",80,274,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,250,43,51,"label",42,1.2,"left",1,"E"],["title",80,391,920,77,"semi",64,1.2,"center",1,"D"],["img",80,508,920,1035],["body",140,1583,800,87,"body",36,1.2,"center",0,"D"]],"Story / 07 Full Bleed Image":[["img",0,0,1080,1920],["handle",80,274,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,250,43,51,"label",42,1.2,"left",1,"E"],["title",80,1470,284,77,"semi",64,1.2,"left",1,"W"],["body",80,1563,702,87,"body",36,1.2,"left",0,"W"]],"Story / 08 Centered Headline":[["title",80,290,920,144,"head",120,1.2,"center",1,"D"],["sub",80,458,920,51,"label",42,1.2,"center",1,"E"],["handle",80,1617,139,29,"mono",24,1.2,"left",1,"D"],["arrow",936,1593,43,51,"label",42,1.2,"left",1,"E"]],"Story / 09 Two Images Bleed":[["img",0,0,1080,948],["img",0,972,1080,948]],"Story / 10 Single Image":[["img",80,80,920,1760]],"Story / 11 Two Images":[["img",80,80,920,860],["img",80,980,920,860]]}''')

def _lin(c):
    c = np.asarray(c, np.float32) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def lum(rgb): l = _lin(rgb); return float(0.2126 * l[..., 0].mean() + 0.7152 * l[..., 1].mean() + 0.0722 * l[..., 2].mean())
def contrast(l1, l2): a, b = max(l1, l2), min(l1, l2); return (a + 0.05) / (b + 0.05)
L_WHITE, L_DARK, L_EMBER = 1.0, lum(np.array([[[59, 59, 59]]])), lum(np.array([[[223, 92, 38]]]))

def layouts_for(fmt):
    p = fmt.capitalize() + ' / '
    return {k[len(p):len(p) + 2]: (k[len(p):], v) for k, v in LAYOUTS.items() if k.startswith(p)}

def _log(*_): pass

def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit('ffmpeg/ffprobe failed:\n' + r.stderr[-1500:])
    return r.stdout

_fc = {}
def font(key, size):
    if (key, size) in _fc: return _fc[(key, size)]
    p = os.path.join(FONT_DIR, os.path.basename(FONTS[key]))
    if not os.path.exists(p):
        os.makedirs(FONT_DIR, exist_ok=True)
        url = 'https://github.com/google/fonts/raw/main/ofl/' + FONTS[key]
        try: urllib.request.urlretrieve(url, p)
        except Exception as e: sys.exit(f'Could not download brand font {url}: {e}. Put the TTF in {FONT_DIR}.')
    _fc[(key, size)] = ImageFont.truetype(p, size); return _fc[(key, size)]

# ---------- frames ----------
def probe(path):
    out = json.loads(sh(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
          'stream=color_transfer:format=duration', '-of', 'json', path]))
    return float(out['format'].get('duration', 0) or 0), (out.get('streams') or [{}])[0].get('color_transfer', '')

def vf(trc, w, h):
    fit = f'scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}'
    if trc in ('arib-std-b67', 'smpte2084'):   # iPhone HDR (HLG / Dolby Vision) -> SDR
        return (f'zscale=tin={trc}:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,'
                f'zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,{fit}')
    return fit

def load_rgb(path):
    if path.lower().endswith(('.heic', '.heif')):
        try: import pillow_heif; pillow_heif.register_heif_opener()
        except ImportError: sys.exit('HEIC needs pillow-heif: pip3 install --user pillow-heif (or export as JPG).')
    return ImageOps.exif_transpose(Image.open(path)).convert('RGB')

def fit(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * s)), max(h, round(im.height * s))), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))

def cmd_frames(a):
    W, H = FORMATS[a.format]['size']; os.makedirs(a.out, exist_ok=True)
    if not a.input.lower().endswith(VIDEO_EXT):   # photos: keep full frame, layouts crop per slot
        p = os.path.join(a.out, 'option_1.png'); fit(load_rgb(a.input), W, H).save(p)
        _log(json.dumps({'type': 'photo', 'frames': [p]})); return
    dur, trc = probe(a.input); tmp = tempfile.mkdtemp(prefix='gbscan_')
    fps = 4 if dur <= 60 else 2
    sh(['ffmpeg', '-v', 'error', '-y', '-i', a.input, '-vf', vf(trc, W // 4, H // 4) + f',fps={fps}', '-q:v', '3', os.path.join(tmp, '%04d.jpg')])
    files = sorted(f for f in os.listdir(tmp) if f.endswith('.jpg'))
    g = [cv2.imread(os.path.join(tmp, f), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255 for f in files]
    n = len(g); ts = np.array([(i + 0.5) / fps for i in range(n)])
    sharp = np.array([cv2.Laplacian(x, cv2.CV_32F).var() for x in g])
    motion = np.array([np.mean([np.abs(g[i] - g[j]).mean() for j in (i - 1, i + 1) if 0 <= j < n] or [0]) for i in range(n)])
    mean = np.array([x.mean() for x in g]); con = np.array([x.std() for x in g])
    clip = np.array([((x > .98) | (x < .02)).mean() for x in g])
    nz = lambda v: (v - v.min()) / (np.ptp(v) + 1e-9)
    score = .45 * nz(sharp) + .25 * (1 - nz(motion)) + .20 * (1 - np.clip(np.abs(mean - .42) * 2.2, 0, 1) - clip * 3) + .10 * nz(con)
    score[(ts < 0.3) | (ts > dur - 0.3)] -= 1
    gap = max(0.8, dur * 0.6 / max(a.count, 1)); picks = []
    for i in np.argsort(-score):
        if all(abs(ts[i] - ts[j]) >= gap for j in picks): picks.append(i)
        if len(picks) == a.count: break
    frames = []
    for k, i in enumerate(picks, 1):
        p = os.path.join(a.out, f'frame_{k}.png')
        sh(['ffmpeg', '-v', 'error', '-y', '-ss', f'{ts[i]:.3f}', '-i', a.input, '-frames:v', '1', '-vf', vf(trc, W, H), p])
        frames.append({'option': k, 'time_s': round(float(ts[i]), 2), 'path': p})
    shutil.rmtree(tmp, ignore_errors=True)
    sheet([Image.open(f['path']) for f in frames], [f"{f['option']}  ·  {f['time_s']}s" for f in frames], os.path.join(a.out, 'sheet_candidates.jpg'), a.format)
    _log(json.dumps({'type': 'video', 'format': a.format, 'frames': frames, 'sheet': os.path.join(a.out, 'sheet_candidates.jpg')}))

def cmd_select(a):
    res = []
    for k, n in enumerate(a.keep[:3], 1):
        dst = os.path.join(a.dir, f'option_{k}.png'); Image.open(os.path.join(a.dir, f'frame_{n}.png')).save(dst)
        res.append({'option': k, 'from_candidate': n, 'path': dst})
    sheet([Image.open(r['path']) for r in res], [str(r['option']) for r in res], os.path.join(a.dir, 'sheet_frames.jpg'), a.format)
    _log(json.dumps({'frames': res, 'sheet': os.path.join(a.dir, 'sheet_frames.jpg')}))

# ---------- grade ----------
def grade(im, s):
    rgb = np.asarray(im).astype(np.float32) / 255
    L, A, B = cv2.split(cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab))
    med = float(np.median(L)); tgt = med + s * (REF['L_med'] - med)
    Ln = 100 * (L / 100) ** np.clip(np.log(max(tgt, 1) / 100) / np.log(max(med, 1) / 100), 0.6, 1.8)
    x = Ln / 100; toe = x - s * 0.09 * np.sin(np.pi * np.clip(x / 0.5, 0, 1)) * (1 - x)
    Ln = np.clip(np.where(toe > 0.72, 0.72 + (toe - 0.72) * (1 - 0.40 * min(s, 1.2)), toe) * 100, 0, 100)
    hi = np.clip((Ln - 45) / 50, 0, 1)
    A = A + s * 0.7 * (REF['a'] - A.mean()) + s * 0.8 + s * 1.2 * hi
    B = B + s * 0.7 * (REF['b'] - B.mean()) + s * 3.0 + s * 4.0 * hi
    green = np.clip(1 - np.abs(np.degrees(np.arctan2(B, A)) % 360 - 150) / 60, 0, 1)
    k = (1 - 0.10 * s) * (1 - 0.35 * s * green); A, B = A * k, B * k + 2.5 * s * green
    out = cv2.cvtColor(cv2.merge([Ln.astype(np.float32), A.astype(np.float32), B.astype(np.float32)]), cv2.COLOR_Lab2RGB)
    yy, xx = np.mgrid[0:out.shape[0], 0:out.shape[1]].astype(np.float32)
    r = np.sqrt(((xx / out.shape[1]) - .5) ** 2 + ((yy / out.shape[0]) - .5) ** 2) / 0.707
    out = out * (1 - 0.14 * s * r[..., None] ** 2) + np.random.default_rng(7).normal(0, 0.012 * s, out.shape[:2])[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))

def cmd_grades(a):
    os.makedirs(a.out, exist_ok=True); im = Image.open(a.input).convert('RGB'); res = []
    for code, name, s in GRADES:
        p = os.path.join(a.out, f'grade_{code}.png'); grade(im, s).save(p); res.append({'option': code, 'name': name, 'path': p})
    sheet([Image.open(r['path']) for r in res], [f"{r['option']}  ·  {r['name']}" for r in res], os.path.join(a.out, 'sheet_grades.jpg'), a.format)
    _log(json.dumps({'grades': res, 'sheet': os.path.join(a.out, 'sheet_grades.jpg')}))

# ---------- layout rendering ----------
def wrap(text, f, maxw):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if f.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur)
    if len(lines) > 1 and len(lines[-1].split()) == 1 and len(lines[-2].split()) > 2:
        pw = lines[-2].split(); lines[-2] = ' '.join(pw[:-1]); lines[-1] = pw[-1] + ' ' + lines[-1]
    return lines

def set_text(el, text):
    """Fit text into a Penpot text box: keep size, allow the box's line count, shrink to 70% if needed."""
    role, x, y, w, h, fk, size, lh, align, caps, col = el
    if caps: text = text.upper()
    if w < 600 and role in ('title', 'sub'): w = 920 if align == 'left' else w   # auto-width boxes -> full measure
    maxl = max(1, round(h / (size * lh))) + (1 if role in ('body', 'sub') else 0)
    for sz in range(size, int(size * 0.7) - 1, -2):
        f = font(fk, sz); lines = wrap(text, f, w)
        if len(lines) <= maxl: return f, sz, lines, (x, y, w)
    raise ValueError(f'"{text}" is too long for this layout\'s {role} ({maxl} lines). Shorten it or pick a layout with more room.')

def render(fmt, code, photos, texts, overlay=None, bg='photo', handle=True, text_mode='auto'):
    """photos: list of graded PIL images. texts: dict title/sub/body/num. overlay: (flat, band) or None."""
    W, H = FORMATS[fmt]['size']; name, els = layouts_for(fmt)[code]
    has_slot = any(e[0] == 'img' for e in els)
    full_bleed = has_slot and any(e[0] == 'img' and e[3] == W and e[4] == H for e in els)
    on_photo = (not has_slot and bg == 'photo') or full_bleed
    canvas = fit(photos[0], W, H) if on_photo and not has_slot else Image.new('RGB', (W, H), BIRCH)
    slots = [e for e in els if e[0] == 'img']
    for i, e in enumerate(slots):
        src = photos[min(i, len(photos) - 1)]
        canvas.paste(fit(src, e[3], e[4]), (e[1], e[2]))
    # resolve text boxes first (colors decided after measuring the photo behind them)
    placed = []
    for e in els:
        role = e[0]
        if role == 'img': continue
        if role in ('handle', 'arrow') and not handle: continue
        t = {'handle': '@GOBAGS.US', 'arrow': '→', 'num': texts.get('num') or '',
             'title': texts.get('title') or '', 'sub': texts.get('sub') or '', 'body': texts.get('body') or texts.get('sub') or ''}[role]
        if not t: continue
        if role == 'arrow': placed.append(('ARROW', e, e[10])); continue
        f, sz, lines, (x, y, w) = set_text(e, t)
        placed.append((f, sz, e[7], e[8], lines, x, y, w, e[10]))
    def box(pl):
        if pl[0] == 'ARROW': e = pl[1]; return e[1], e[2], e[3], e[4]
        f, sz, lh, al, lines, x, y, w, _ = pl
        if al == 'center': w2 = max(f.getlength(t) for t in lines); x = x + (w - w2) / 2; w = w2
        else: w = max(f.getlength(t) for t in lines)
        return int(x), int(y), int(w), int(sz * lh * len(lines))
    arr = np.asarray(canvas)
    # light or dark text? (auto = whichever reads better on the photo behind the main text)
    mode = 'dark-bg'
    if on_photo:
        main = [box(p) for p in placed if p[0] != 'ARROW' and p[-1] != 'E'] or [box(p) for p in placed if p[0] != 'ARROW']
        if text_mode == 'light': mode = 'dark-bg'
        elif text_mode == 'dark': mode = 'light-bg'
        elif main:
            ls = [lum(arr[max(0, y):y + h, max(0, x):x + w]) for x, y, w, h in main if w > 0 and h > 0]
            bgl = float(np.mean(ls)) if ls else 0
            mode = 'light-bg' if contrast(bgl, L_DARK) > contrast(bgl, L_WHITE) * 1.15 else 'dark-bg'
    elif not full_bleed: mode = 'birch'
    # overlay: flat tint + soft band behind text, ink on dark photos, Birch on bright ones
    if on_photo and overlay:
        flat, band = overlay
        m = np.full((H, W), flat, np.float32); bm = np.zeros((H, W), np.float32)
        for pl in placed:
            if pl[0] == 'ARROW': continue
            x, y, w, h = box(pl)
            if pl[-1] == 'E' and len(pl[4][0]) <= 3: continue
            bm[max(0, y - 60):min(H, y + h + 60), max(0, x - 80):min(W, x + w + 80)] = 1
        bm = cv2.GaussianBlur(bm, (0, 0), 70) * band
        m = np.clip(m + bm * (1 - m), 0, 1)
        tint = BIRCH if mode == 'light-bg' else INK
        canvas = Image.composite(Image.new('RGB', (W, H), tint), canvas, Image.fromarray((m * 255).astype(np.uint8)))
        arr = np.asarray(canvas)
    main_fill = (255, 255, 255) if mode == 'dark-bg' else (DARK if mode in ('light-bg', 'birch') else (255, 255, 255))
    final = []
    for pl in placed:
        col = pl[-1]
        if not on_photo and full_bleed is False: fill = EMBER if col == 'E' else DARK
        elif not on_photo: fill = EMBER if col == 'E' else ((255, 255, 255) if col == 'W' else DARK)
        else: fill = main_fill
        if col == 'E':   # keep Ember accent only where it stays readable (WCAG 3:1 for large text)
            x, y, w, h = box(pl); reg = arr[max(0, y):y + max(h, 1), max(0, x):x + max(w, 1)]
            fill = EMBER if reg.size and contrast(lum(reg), L_EMBER) >= 3.0 else (main_fill if on_photo else DARK)
        elif col == 'W' and full_bleed:   # Full Bleed layout's white text also adapts
            x, y, w, h = box(pl); reg = arr[max(0, y):y + max(h, 1), max(0, x):x + max(w, 1)]
            fill = (255, 255, 255) if reg.size and contrast(lum(reg), L_WHITE) >= contrast(lum(reg), L_DARK) else DARK
        final.append(pl[:-1] + (fill,))
    placed = final
    light_text = on_photo and mode == 'dark-bg'
    txt = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    for pl in placed:
        if pl[0] == 'ARROW':
            e, fc = pl[1], pl[2]; cy = e[2] + e[4] // 2; x0, x1 = e[1] + 4, e[1] + e[3] - 4
            d.line([(x0, cy), (x1, cy)], fill=fc + (255,), width=4)
            d.line([(x1 - 14, cy - 12), (x1, cy), (x1 - 14, cy + 12)], fill=fc + (255,), width=4); continue
        f, sz, lh, al, lines, x, y, w, fill = pl
        asc, desc = f.getmetrics(); line_h = sz * lh
        for i, t in enumerate(lines):
            base = y + i * line_h + (line_h + asc - desc) / 2
            tx = x + (w - f.getlength(t)) / 2 if al == 'center' else x
            d.text((tx, base), t, font=f, fill=fill + (255,), anchor='ls')
    out = canvas.convert('RGBA')
    if light_text:   # soft shadow only under white text
        sh_ = txt.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.28))
        out.paste((0, 0, 0, 255), (0, 3), sh_)
    return Image.alpha_composite(out, txt).convert('RGB'), name

def texts_of(a): return {'title': a.title, 'sub': a.sub, 'body': a.body, 'num': a.num}

def cmd_layouts(a):
    os.makedirs(a.out, exist_ok=True)
    photos = [Image.open(p).convert('RGB') for p in a.input]
    ims, labs, res = [], [], []
    for code in sorted(layouts_for(a.format)):
        if a.only and code not in a.only: continue
        try: im, name = render(a.format, code, photos, texts_of(a), OVERLAYS[1][2:], a.bg, not a.no_handle)
        except ValueError as e: res.append({'layout': code, 'error': str(e)}); continue
        p = os.path.join(a.out, f'layout_{code}.png'); im.save(p)
        ims.append(im); labs.append(name); res.append({'layout': code, 'name': name, 'path': p})
    sheet(ims, labs, os.path.join(a.out, 'sheet_layouts.jpg'), a.format, cols=4 if len(ims) > 6 else 3)
    _log(json.dumps({'layouts': res, 'sheet': os.path.join(a.out, 'sheet_layouts.jpg')}))

def cmd_overlays(a):
    os.makedirs(a.out, exist_ok=True); photos = [Image.open(p).convert('RGB') for p in a.input]; res = []
    for code, name, flat, band in OVERLAYS:
        im, lname = render(a.format, a.layout, photos, texts_of(a), (flat, band), a.bg, not a.no_handle)
        p = os.path.join(a.out, f'overlay_{code}.png'); im.save(p); res.append({'option': code, 'name': name, 'path': p})
    sheet([Image.open(r['path']) for r in res], [f"{r['option']}  ·  {r['name']}" for r in res], os.path.join(a.out, 'sheet_overlays.jpg'), a.format)
    _log(json.dumps({'layout': lname, 'overlays': res, 'sheet': os.path.join(a.out, 'sheet_overlays.jpg')}))

def cmd_export(a):
    os.makedirs(a.out, exist_ok=True); stem = f"{datetime.date.today().isoformat()}-{a.name}-{a.format}"
    im = Image.open(a.input).convert('RGB'); res = {}
    res['cover'] = os.path.join(a.out, f'{stem}.jpg'); im.save(res['cover'], quality=95, subsampling=0)
    g = FORMATS[a.format]['grid']
    if g: res['grid_preview'] = os.path.join(a.out, f'{stem}-grid-preview.jpg'); im.crop(g).save(res['grid_preview'], quality=92)
    _log(json.dumps(res))

def sheet(ims, labels, out, fmt, cols=3):
    W, H = FORMATS[fmt]['size']; tw = 360 if cols == 3 else 280; th = round(tw * H / W); pad, bar = 24, 64
    cols = min(cols, len(ims)); rows = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (pad + cols * (tw + pad), pad + rows * (th + bar + pad)), BIRCH); d = ImageDraw.Draw(S)
    f = font('semi', 30 if cols > 3 else 34)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x = pad + (i % cols) * (tw + pad); y0 = pad + (i // cols) * (th + bar + pad)
        S.paste(im.resize((tw, th), Image.LANCZOS), (x, y0))
        for gy in FORMATS[fmt]['guides']:
            yy = y0 + gy * th // H
            for gx in range(x, x + tw, 12): d.line([(gx, yy), (gx + 6, yy)], fill=(255, 255, 255), width=1)
        d.text((x, y0 + th + 14), lab.upper(), font=f, fill=INK)
    S.save(out, quality=90)


# ---------- stateful front-end (short commands, one-line output = low token use) ----------
def rel(p): return os.path.relpath(p, os.path.expanduser('~/mnt')) if '/mnt/' in p else p
def load_state(work): return json.load(open(os.path.join(work, 'state.json')))
def save_state(work, st): json.dump(st, open(os.path.join(work, 'state.json'), 'w'))
class NS(dict): __getattr__ = dict.get

def review_sheet(paths, out, fmt):   # small, Claude-only: ~1/4 the tokens of a full sheet
    W, H = FORMATS[fmt]['size']; tw = 150; th = round(tw * H / W); pad = 8
    S = Image.new('RGB', (pad + 3 * (tw + pad), pad + ((len(paths) + 2) // 3) * (th + 30 + pad)), BIRCH); d = ImageDraw.Draw(S)
    for i, p in enumerate(paths):
        x = pad + (i % 3) * (tw + pad); y = pad + (i // 3) * (th + 30 + pad)
        S.paste(Image.open(p).resize((tw, th)), (x, y)); d.text((x, y + th + 4), str(i + 1), font=font('semi', 22), fill=INK)
    S.save(out, quality=70)

def has_text_slots(fmt, code): return any(e[0] in ('title', 'sub', 'body') for e in layouts_for(fmt)[code][1])

def f_start(a):
    work = os.path.join(os.path.dirname(os.path.abspath(a.input)), 'Covers', '_working', os.path.splitext(os.path.basename(a.input))[0])
    os.makedirs(work, exist_ok=True)
    st = dict(input=os.path.abspath(a.input), format=a.format, texts=texts_of(a), bg=a.bg, handle=not a.no_handle, text=a.text)
    save_state(work, st)
    if not a.input.lower().endswith(VIDEO_EXT):
        cmd_frames(NS(input=a.input, out=work, format=a.format, count=1, quiet=1))
        print(f'work={rel(work)} | photo -> run: look 1'); return
    cmd_frames(NS(input=a.input, out=work, format=a.format, count=6, quiet=1))
    review_sheet([os.path.join(work, f'frame_{k}.png') for k in range(1, 7) if os.path.exists(os.path.join(work, f'frame_{k}.png'))],
                 os.path.join(work, 'review.jpg'), a.format)
    print(f'work={rel(work)} | review={rel(os.path.join(work, "review.jpg"))}')

def f_pick(a):
    st = load_state(a.work); cmd_select(NS(dir=a.work, keep=a.keep, format=st['format'], quiet=1))
    print(f'sheet={rel(os.path.join(a.work, "sheet_frames.jpg"))}')

def f_look(a):
    st = load_state(a.work); fmt = st['format']; st['frame'] = a.frame
    for k in ('title', 'sub', 'body', 'num'):
        if getattr(a, k) is not None: st['texts'][k] = getattr(a, k)
    cmd_grades(NS(input=os.path.join(a.work, f'option_{a.frame}.png'), out=a.work, format=fmt, quiet=1))
    others = [os.path.join(a.work, f'option_{k}.png') for k in (1, 2, 3) if k != a.frame and os.path.exists(os.path.join(a.work, f'option_{k}.png'))]
    st['second'] = others[0] if others else None; save_state(a.work, st)
    photos = [Image.open(os.path.join(a.work, 'grade_B.png'))] + ([grade(Image.open(st['second']), 0.85)] if st['second'] else [])
    t = st['texts']; any_text = any(t.values()); ims, labs = [], []
    for code in sorted(layouts_for(fmt)):
        if any_text != has_text_slots(fmt, code) and not (any_text and code in ('09', '10', '11')): continue
        if code in ('09', '11') and len(photos) < 2: continue
        try: im, name = render(fmt, code, photos, t, OVERLAYS[1][2:], st['bg'], st['handle'], st.get('text', 'auto'))
        except ValueError: continue
        ims.append(im); labs.append(name)
    if not any_text: ims.insert(0, fit(photos[0], *FORMATS[fmt]['size'])); labs.insert(0, '00 Full frame')
    sheet(ims, labs, os.path.join(a.work, 'sheet_layouts.jpg'), fmt, cols=4 if len(ims) > 6 else 3)
    print(f'grades={rel(os.path.join(a.work, "sheet_grades.jpg"))} | layouts={rel(os.path.join(a.work, "sheet_layouts.jpg"))}')

def f_finish(a):
    st = load_state(a.work); fmt = st['format']; code = a.layout
    base = Image.open(os.path.join(a.work, f'grade_{a.grade}.png'))
    s = dict(GRADES_S)[a.grade]
    photos = [base] + ([grade(Image.open(st['second']), s)] if st.get('second') else [])
    if code == '00': final = fit(base, *FORMATS[fmt]['size'])
    else:
        on_photo = (not any(e[0] == 'img' for e in layouts_for(fmt)[code][1]) and st['bg'] == 'photo') or code == '07'
        if on_photo and has_text_slots(fmt, code) and not a.overlay:
            ims = []
            for c, n, flat, band in OVERLAYS:
                im, _ = render(fmt, code, photos, st['texts'], (flat, band), st['bg'], st['handle'], st.get('text', 'auto'))
                im.save(os.path.join(a.work, f'overlay_{c}.png')); ims.append(im)
            sheet(ims, [f'{c}  ·  {n}' for c, n, *_ in OVERLAYS], os.path.join(a.work, 'sheet_overlays.jpg'), fmt)
            print(f'overlays={rel(os.path.join(a.work, "sheet_overlays.jpg"))} | then: finish --overlay N'); return
        ov = next((o for o in OVERLAYS if o[0] == a.overlay), OVERLAYS[1])
        final, _ = render(fmt, code, photos, st['texts'], ov[2:], st['bg'], st['handle'], st.get('text', 'auto'))
    out = os.path.join(os.path.dirname(st['input']), 'Covers'); os.makedirs(out, exist_ok=True)
    stem = f"{datetime.date.today().isoformat()}-{a.name}-{fmt}"; cover = os.path.join(out, stem + '.jpg')
    final.save(cover, quality=95, subsampling=0); msg = f'cover={rel(cover)}'
    g = FORMATS[fmt]['grid']
    if g: gp = os.path.join(out, stem + '-grid-preview.jpg'); final.crop(g).save(gp, quality=92); msg += f' | grid={rel(gp)}'
    print(msg)

GRADES_S = [(c, s) for c, n, s in GRADES]

if __name__ == '__main__':
    p = argparse.ArgumentParser(); sp = p.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('start'); s.add_argument('input'); s.add_argument('--format', required=True, choices=list(FORMATS))
    for k in ('title', 'sub', 'body', 'num'): s.add_argument('--' + k, default='')
    s.add_argument('--bg', default='photo', choices=['photo', 'birch']); s.add_argument('--no-handle', action='store_true')
    s.add_argument('--text', default='auto', choices=['auto', 'light', 'dark'])
    s = sp.add_parser('pick'); s.add_argument('work'); s.add_argument('keep', type=int, nargs='+')
    s = sp.add_parser('look'); s.add_argument('work'); s.add_argument('frame', type=int)
    for k in ('title', 'sub', 'body', 'num'): s.add_argument('--' + k, default=None)
    s = sp.add_parser('finish'); s.add_argument('work'); s.add_argument('--grade', required=True, choices=['A', 'B', 'C'])
    s.add_argument('--layout', required=True); s.add_argument('--overlay', choices=['1', '2', '3']); s.add_argument('--name', default='cover')
    a = p.parse_args()
    if a.cmd in ('pick', 'look', 'finish'): a.work = os.path.expanduser(os.path.join('~/mnt', a.work)) if not a.work.startswith('/') else a.work
    try: {'start': f_start, 'pick': f_pick, 'look': f_look, 'finish': f_finish}[a.cmd](a)
    except ValueError as e: sys.exit(str(e))
