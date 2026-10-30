#!/usr/bin/env python3
"""WCAG 대비 검사 (표준 라이브러리만). assets 의 *-light.svg / *-dark.svg 를 읽고
각 글자·아이콘·선의 색을 '실제로 그 아래 깔린 배경'(앞서 그려진 불투명 rect/circle, 없으면 GitHub 캔버스)과 비교합니다.
기준: 본문 글자 4.5:1, 큰 글자(24px 이상 또는 18.66px 이상 굵게) 3:1, 아이콘·의미 있는 선 3:1,
장식선(테마 ln/grid/num 색) 1.25:1. 투명도(opacity, 애니메이션 최댓값)는 배경과 합성해서 계산합니다.
사용: python3 build/contrast.py [--all]  (--all 은 통과 항목도 출력). 기준 미달이 있으면 exit 1."""
import os, re, sys, glob
import xml.etree.ElementTree as ET
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
CANVAS = {'light': '#ffffff', 'dark': '#0d1117'}
DECOR = {'light': {'#dde1e6', '#1a1a1f', '#c9ced6', '#cdd3da'}, 'dark': {'#3d444d', '#ffffff', '#30363d', '#59616b'}}
DECOR_MIN = 1.25  # 테두리·구분선·큰 장식 숫자: GitHub 자체 테두리 수준
NS = '{http://www.w3.org/2000/svg}'
def hx(s):
    s = s.strip().lower()
    if re.fullmatch(r'#[0-9a-f]{3}', s): s = '#' + ''.join(ch*2 for ch in s[1:])
    return s if re.fullmatch(r'#[0-9a-f]{6}', s) else None
def rgb(h): return [int(h[i:i+2], 16)/255 for i in (1, 3, 5)]
def lum(h):
    return sum(w*(v/12.92 if v <= .03928 else ((v+.055)/1.055)**2.4) for w, v in zip((.2126, .7152, .0722), rgb(h)))
def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la+.05)/(lb+.05)
def blend(fg, bg, a):
    f, b = rgb(fg), rgb(bg); return '#' + ''.join(f'{round((x*a+y*(1-a))*255):02x}' for x, y in zip(f, b))
def num(v, d=0.0):
    try: return float(re.match(r'-?[\d.]+', str(v)).group())
    except Exception: return d
def eff_opacity(el):
    o = num(el.get('opacity', 1), 1)
    for a in el.findall(NS+'animate'):
        if a.get('attributeName') == 'opacity':
            o = max(num(x, 1) for x in a.get('values', '1').split(';'))   # 보이는 순간 기준
    return o
def audit(path, theme):
    root = ET.parse(path).getroot(); canvas = CANVAS[theme]
    grads = {}
    for g in root.iter():
        if g.tag in (NS+'linearGradient', NS+'radialGradient'):
            cols = [hx(s.get('stop-color', '')) for s in g.findall(NS+'stop') if num(s.get('stop-opacity', 1), 1) > .9]
            grads[g.get('id')] = [c for c in cols if c]
    bgs, out = [], []
    def color_list(v):
        if not v or v == 'none': return []
        m = re.match(r'url\(#(.+)\)', v)
        if m: return grads.get(m.group(1), [])
        h = hx(v); return [h] if h else []
    def bg_at(x, y):
        for (x0, y0, x1, y1, col) in reversed(bgs):
            if x0 <= x <= x1 and y0 <= y <= y1: return col
        return [canvas]
    def walk(el, inh, dx, dy, op, anchor):
        tag = el.tag.replace(NS, '')
        if tag in ('defs', 'clipPath', 'pattern', 'title', 'style', 'linearGradient', 'radialGradient', 'animate', 'animateMotion', 'animateTransform'): return
        inh = dict(inh)
        for k in ('fill', 'stroke', 'font-size', 'font-weight'):
            if el.get(k): inh[k] = el.get(k)
        tr = re.match(r'translate\(([-\d.]+)[ ,]+([-\d.]+)\)', el.get('transform', ''))
        if tr: dx += num(tr.group(1)); dy += num(tr.group(2))
        op *= eff_opacity(el)
        if tag == 'svg' and el is not root:
            anchor = anchor or (dx+num(el.get('x')), dy+num(el.get('y')), dx+num(el.get('x'))+num(el.get('width')), dy+num(el.get('y'))+num(el.get('height')))
        if op <= .02:  # 완전히 숨은 요소 (예: 마스크용)
            return
        if tag in ('rect', 'circle', 'ellipse') and anchor is None:
            fills = color_list(inh.get('fill') if el.get('fill') or tag != 'rect' else el.get('fill', '#000'))
            if el.get('fill') and fills and op > .95 and not el.get('clip-path'):
                if tag == 'rect':
                    x, y = dx+num(el.get('x')), dy+num(el.get('y')); w, h = num(el.get('width')), num(el.get('height'))
                else:
                    r = num(el.get('r', el.get('rx', 0))); x, y = dx+num(el.get('cx'))-r, dy+num(el.get('cy'))-r; w = h = 2*r
                if w > 30 and h > 20: bgs.append((x, y, x+w, y+h, fills))
        if tag == 'text':
            x, y = dx+num(el.get('x')), dy+num(el.get('y'))-5
            if el.get('text-anchor') == 'end': x -= 10
            elif el.get('text-anchor') == 'middle': pass
            else: x += 4
            fs = num(inh.get('font-size', 16), 16); fw = num(inh.get('font-weight', 400), 400)
            need = 3 if fs >= 24 or (fs >= 18.66 and fw >= 700) else 4.5
            under = [[hx(v) for v in el.get('data-bg').split(',')]] if el.get('data-bg') else None  # 물결 등 rect 가 아닌 배경 위 글자
            for fg in color_list(inh.get('fill', '#000')):
                role = 'decor-text' if fg in DECOR[theme] and fs >= 30 else 'text'
                for b in (under[0] if under else bg_at(x, y)):
                    out.append((role, fg, b, ratio(blend(fg, b, min(op, 1)), b), DECOR_MIN if role == 'decor-text' else need, (el.text or ''.join(el.itertext()))[:24].strip()))
            return
        if tag in ('path', 'polyline', 'line', 'circle', 'rect', 'ellipse'):
            pt = ((anchor[0]+anchor[2])/2, (anchor[1]+anchor[3])/2) if anchor else None
            if pt is None:
                if tag == 'rect': pt = (dx+num(el.get('x'))+2, dy+num(el.get('y'))+2)
                elif tag in ('circle', 'ellipse'): pt = (dx+num(el.get('cx')), dy+num(el.get('cy')))
                else:
                    m = re.findall(r'[-\d.]+', el.get('d', el.get('points', '')))
                    pt = (dx+num(m[0]), dy+num(m[1])) if len(m) > 1 else (dx, dy)
            # 다른 배경 위에 얹힌 요소는 바로 아래 배경과 비교 (자기 자신 제외)
            stroke = el.get('stroke', inh.get('stroke') if anchor else None)
            paints = [('stroke', s) for s in color_list(stroke)] if stroke and not el.get('stroke-opacity') and not re.match(r'url', stroke or '') else []
            if (tag in ('circle',) or anchor) and el.get('fill', inh.get('fill')) not in (None, 'none'):
                w = num(el.get('width', el.get('r', 0)))
                if anchor or tag == 'circle': paints += [('fill', f) for f in color_list(el.get('fill', inh.get('fill')))]
            for kind, col in paints:
                role = 'decor' if col in DECOR[theme] else 'icon'
                under = [b for b in bg_at(*pt)]
                if kind == 'stroke' and tag == 'rect' and el.get('fill') not in (None, 'none'):  # 카드 테두리: 캔버스 쪽 대비
                    under = [canvas]
                for b in under:
                    if b == col: continue
                    out.append((role, col, b, ratio(blend(col, b, min(op, 1)), b), DECOR_MIN if role == 'decor' else 3, f'{tag}.{kind}'))
        for ch in el: walk(ch, inh, dx, dy, op, anchor)
    walk(root, {}, 0, 0, 1, None)
    return out
def main():
    show_all = '--all' in sys.argv; bad = 0; total = 0; seen = set()
    for p in sorted(glob.glob(os.path.join(ROOT, '**', '*.svg'), recursive=True)):
        m = re.search(r'-(light|dark)\.svg$', p)
        if not m or '/icons/' in p: continue
        for role, fg, b, r, need, what in audit(p, m.group(1)):
            key = (os.path.basename(p), role, fg, b, what); total += 1
            if key in seen: continue
            seen.add(key)
            if r < need or show_all:
                print(f'{"FAIL" if r < need else "ok  "} {os.path.basename(p):32} {role:10} {fg} on {b}  {r:5.2f}:1 (need {need})  {what}')
                bad += r < need
    # 아이콘 파일 자체: 다크 아이콘은 다크 카드/캔버스, 라이트는 흰 배경 기준
    for p in sorted(glob.glob(os.path.join(ROOT, 'icons', '*.svg'))):
        th = 'dark' if p.endswith('-dark.svg') else 'light'
        for col in set(re.findall(r'stroke="(#[0-9a-fA-F]{3,6})"', open(p).read())):
            for b in ([CANVAS[th], '#161b22'] if th == 'dark' else [CANVAS[th], '#f6f8fa']):
                r = ratio(hx(col), b); total += 1
                if r < 3 or show_all:
                    print(f'{"FAIL" if r < 3 else "ok  "} icons/{os.path.basename(p):26} icon       {hx(col)} on {b}  {r:5.2f}:1 (need 3)'); bad += r < 3
    print(f'contrast: {total} checks, {bad} below threshold')
    sys.exit(1 if bad else 0)

# ---- --render: 실제 렌더링으로 글자 아래 가장 불리한 배경 픽셀을 찾습니다 (그라데이션·광원·이미지 포함) ----
# Playwright + Chromium 이 있을 때만 동작합니다. 애니메이션을 여러 시점에서 멈춰 보고,
# 글자를 숨긴 화면에서 글자 상자 안 픽셀마다 (글자색을 최대 불투명도로 합성한 색) 과의 대비를 계산해 최솟값을 씁니다.
JS = """async (t) => {
  const svg = document.querySelector('svg'); svg.pauseAnimations(); svg.setCurrentTime(t);
  document.getAnimations().forEach(a => { a.pause(); a.currentTime = t * 1000; });
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  return [...document.querySelectorAll('text')].map((el, i) => {
    let o = 1; for (let e = el; e && e.tagName !== 'svg'; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return { i, txt: el.textContent.trim().slice(0, 40), fill: cs.fill, op: o * parseFloat(cs.fillOpacity || 1),
             x: r.x, y: r.y, w: r.width, h: r.height, size: parseFloat(cs.fontSize), weight: parseInt(cs.fontWeight) };
  });
}"""
def render_audit(files, times=(0, 1.5, 3, 4.5, 6, 7.5, 9, 10.5)):
    from playwright.sync_api import sync_playwright
    from PIL import Image; import io
    out = []
    with sync_playwright() as p:
        exe = '/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
        br = p.chromium.launch(executable_path=exe, args=['--no-sandbox']) if exe else p.chromium.launch()
        pg = br.new_page()
        for f in files:
            theme = 'dark' if f.endswith('-dark.svg') else 'light'
            src = open(f, encoding='utf-8').read()
            if '<text' not in src: continue
            W, H = (int(num(v)) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src).groups())
            pg.set_viewport_size({'width': W, 'height': H})
            pg.set_content(f'<html><body style="margin:0;background:{CANVAS[theme]}">{src}</body></html>')
            best = {}
            for t in times:
                info = pg.evaluate(JS, t)
                pg.add_style_tag(content='text{visibility:hidden!important}')
                img = Image.open(io.BytesIO(pg.screenshot())).convert('RGB')
                pg.evaluate("document.querySelectorAll('style:last-of-type').forEach(s=>s.remove())")
                for d in info:
                    m = re.match(r'rgb\((\d+), (\d+), (\d+)', d['fill'])
                    if not m or d['w'] < 1: continue
                    fc = '#' + ''.join(f'{int(v):02x}' for v in m.groups())
                    if d['y'] + d['h'] <= 0 or d['y'] >= H or d['x'] >= W or d['x'] + d['w'] <= 0: continue  # 화면 밖(스크롤 중)
                    b = best.setdefault(d['i'], dict(d, op=0, worst=99, bgpx=None, fc=fc))
                    b['op'] = max(b['op'], d['op'])
                    box = img.crop((max(0, int(d['x'])), max(0, int(d['y'])), min(W, int(d['x'] + d['w']) + 1), min(H, int(d['y'] + d['h']) + 1)))
                    sm = box.resize((min(box.width, 60), min(box.height, 12))); raw = sm.tobytes()
                    for px in {tuple(raw[k:k+3]) for k in range(0, len(raw), 3)}:
                        bg = '#%02x%02x%02x' % px; b.setdefault('bgs', set()).add(bg)
            for b in best.values():
                if b['op'] < .05: continue
                for bg in b['bgs']:
                    r = ratio(blend(b['fc'], bg, min(1, b['op'])), bg)
                    if r < b['worst']: b['worst'], b['bgpx'] = r, bg
                large = b['size'] >= 24 or (b['size'] >= 18.66 and b['weight'] >= 700)
                need = DECOR_MIN if b['fc'] in DECOR[theme] else (3 if large else 4.5)
                out.append((os.path.relpath(f, ROOT), b['txt'], b['fc'], b['bgpx'], round(b['worst'], 2), need))
        br.close()
    return out
if __name__ == '__main__':
    if '--render' in sys.argv:
        pat = [a for a in sys.argv[1:] if not a.startswith('--')]
        files = sorted(glob.glob(os.path.join(ROOT, pat[0] if pat else '*-*.svg')))
        res = render_audit(files); bad = [r for r in res if r[4] < r[5]]
        for r in (res if '--all' in sys.argv else bad): print(('FAIL ' if r[4] < r[5] else 'ok   ') + f'{r[0]} "{r[1]}" {r[2]} on worst {r[3]} = {r[4]}:1 (need {r[5]})')
        print(f'contrast --render: {len(res)} texts, {len(bad)} below threshold'); sys.exit(1 if bad else 0)
    main()
