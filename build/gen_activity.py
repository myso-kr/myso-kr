#!/usr/bin/env python3
"""공개 저장소의 최근 커밋으로 '최근 활동' SVG를 만듭니다 (공개 저장소만, 비공개 이름/메시지는 절대 포함하지 않음)."""
import re, json, os, re, sys, urllib.request, datetime, html
USER = "myso-kr"
ORG = "modootoday"
COLORS = {}
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"
TOKEN = os.environ.get("GITHUB_TOKEN")
F = "Pretendard,'Apple SD Gothic Neo','Noto Sans KR',-apple-system,'Segoe UI',sans-serif"
M = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
def get(url):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "myso-kr-activity"}
    if TOKEN: h["Authorization"] = f"Bearer {TOKEN}"
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20))
def rel(dt, now):
    s = (now - dt).total_seconds()
    if s < 3600: return f"{int(s//60)}분 전"
    if s < 86400: return f"{int(s//3600)}시간 전"
    return f"{int(s//86400)}일 전"
items = []
# modootoday 조직의 공개·원본(포크/보관 제외) 저장소 중 최근 push 순 10개에서 myso-kr 가 작성한 커밋만. 개인 저장소와 비공개 저장소는 조회하지 않습니다.
_R = get(f"https://api.github.com/orgs/{ORG}/repos?type=public&sort=pushed&per_page=100")
REPOS = [x["name"] for x in _R if not x.get("private") and x.get("visibility", "public") == "public" and not x["fork"] and not x["archived"]][:10]
for r in REPOS:
    try:
        for c in get(f"https://api.github.com/repos/{ORG}/{r}/commits?author={USER}&per_page=3"):
            msg = c["commit"]["message"].splitlines()[0]
            if msg.startswith("Merge "): continue
            msg = re.sub("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\U0001D400-\U0001D7FF\u2190-\u21FF\u2B00-\u2BFF]", "", msg).strip()  # lint 규칙과 동일
            when = datetime.datetime.fromisoformat(c["commit"]["committer"]["date"].replace("Z", "+00:00"))
            items.append((when, r, msg))
    except Exception as e:
        print("skip", r, e, file=sys.stderr)
items.sort(reverse=True); items = items[:8]
now = datetime.datetime.now(datetime.timezone.utc)
T = {"light": dict(card="#FFFFFF", fg="#1A1A1F", mu="#5B616B", ln="#DDE1E6", p="#d94925"),
     "dark": dict(card="#161B22", fg="#F0F3F6", mu="#AAB3BD", ln="#3D444D", p="#F07450")}
def _rgb(h): return [int(h[i:i+2], 16)/255 for i in (1, 3, 5)]
def _lum(h): return sum(w*(v/12.92 if v <= .03928 else ((v+.055)/1.055)**2.4) for w, v in zip((.2126, .7152, .0722), _rgb(h)))
def _ratio(a, b):
    x, y = sorted((_lum(a), _lum(b)), reverse=True); return (x+.05)/(y+.05)
def dot(col, k, target=3.2):
    """다크 테마에서 저장소 색 점이 카드(#161B22) 위에서 3:1 이상 보이도록 같은 색조로 밝힙니다."""
    bg = "#FFFFFF" if k == "light" else "#161B22"
    if _ratio(col, bg) >= target or k == "light": return col
    r = _rgb(col)
    for i in range(1, 101):
        h = "#" + "".join(f"{round((v+(1-v)*i/100)*255):02x}" for v in r)
        if _ratio(h, bg) >= target: return h.upper()
    return "#FFFFFF"
STAMP = now.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
_EMO = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\U0001D400-\U0001D7FF\u2190-\u21FF\u2B00-\u2BFF]')
items = [(w, r, re.sub(r"\s+", " ", _EMO.sub("", m)).strip()) for (w, r, m) in items]
ALT = f"최근 활동 – 공개 저장소 커밋 · 기준 {STAMP} KST. " + " ".join(f"{i}) {r}: {m} ({rel(w, now)})." for i, (w, r, m) in enumerate(items, 1))
# README 의 alt 와 '텍스트로 보기' 목록에 쓰도록 src/data/alts.json 에 함께 기록합니다
_ap = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "data", "alts.json")
_alts = json.load(open(_ap)) if os.path.exists(_ap) else {}
_alts["activity"] = ALT
_alts["activity_items"] = [{"repo": r, "url": f"https://github.com/{ORG}/{r}", "msg": m, "when": rel(w, now)} for (w, r, m) in items]
_alts["activity_stamp"] = STAMP + " KST"
json.dump(dict(sorted(_alts.items())), open(_ap, "w"), ensure_ascii=False, indent=2)
ROW = 40; VIS = 5; H = 70 + ROW*VIS + 20
for k, c in T.items():
    rows = ""
    seq = items + items[:VIS]                     # 끊김 없는 순환 스크롤
    for i, (w, r, m) in enumerate(seq):
        y = i*ROW
        m = html.escape(m if len(m) <= 70 else m[:68] + "…")
        rows += (f'<g transform="translate(0 {y})"><circle cx="40" cy="-5" r="6" fill="{dot(COLORS.get(r, c["mu"]), k)}"/>'
                 f'<text x="58" y="0" class="m" font-size="14" fill="{c["fg"]}" font-weight="700">{r}</text>'
                 f'<text x="300" y="0" font-size="15" fill="{c["fg"]}">{m}</text>'
                 f'<text x="1160" y="0" text-anchor="end" font-size="13" fill="{c["mu"]}">{rel(w, now)}</text></g>')
    n = len(items); dur = max(n*3, 6)
    anim = (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {-n*ROW}" '
            f'dur="{dur}s" repeatCount="indefinite" calcMode="discrete"/>' if False else
            f'<animateTransform attributeName="transform" type="translate" from="0 0" to="0 {-n*ROW}" dur="{dur}s" repeatCount="indefinite"/>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{H}" viewBox="0 0 1200 {H}" role="img" aria-label="{html.escape(ALT, quote=True)}"><title>{html.escape(ALT)}</title>
<style>text{{font-family:{F}}} .m{{font-family:{M}}} @media (prefers-reduced-motion: reduce){{animateTransform{{display:none}}}}</style>
<defs><clipPath id="v"><rect x="0" y="62" width="1200" height="{ROW*VIS+6}"/></clipPath>
<linearGradient id="fd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c["card"]}"/><stop offset=".12" stop-color="{c["card"]}" stop-opacity="0"/><stop offset=".88" stop-color="{c["card"]}" stop-opacity="0"/><stop offset="1" stop-color="{c["card"]}"/></linearGradient></defs>
<rect x=".5" y=".5" width="1199" height="{H-1}" rx="20" fill="{c["card"]}" stroke="{c["ln"]}"/>
<circle cx="40" cy="36" r="5" fill="{"#1a7f37" if k == "light" else "#3FB950"}"><animate attributeName="opacity" values="1;.3;1" dur="2s" repeatCount="indefinite"/></circle>
<text x="56" y="42" font-size="17" font-weight="800" fill="{c["fg"]}">최근 활동</text>
<text x="140" y="42" font-size="13" fill="{c["mu"]}">공개 저장소 커밋 · 기준 {now.astimezone(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")} KST</text>
<g clip-path="url(#v)"><g transform="translate(0 92)"><g>{anim}{rows}</g></g></g>
<rect x="0" y="62" width="1200" height="{ROW*VIS+6}" fill="url(#fd)"/></svg>'''
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/activity-{k}.svg", "w").write(svg)
print(f"{len(items)} commits")
