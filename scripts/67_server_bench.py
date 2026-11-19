"""oxigraph serve-read-only を手元で立て、立ち上がり・問い・DESCRIBE の時間とメモリの最大を測る。.venv の python(結果の数え直しに pyoxigraph を使う)。
引数: oxigraph の実行ファイル、店の場所、立ち上げの回数"""
import sys, os, time, json, glob, subprocess, signal, re, urllib.request, urllib.parse, io, pyoxigraph as ox
OXI, LOC, N = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3
URL = 'http://127.0.0.1:7878/query'
def get(q, accept, timeout=120):
    t0 = time.time(); r = urllib.request.urlopen(urllib.request.Request(URL + '?' + urllib.parse.urlencode({'query': q}), headers={'Accept': accept}), timeout=timeout)
    b = r.read(); return time.time() - t0, r.headers.get('Content-Type'), b
def start():
    p = subprocess.Popen(['/usr/bin/time', '-l', OXI, 'serve-read-only', '--location', LOC, '--bind', '127.0.0.1:7878'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    t0 = time.time()
    while True:
        try: get('ASK {}', 'application/sparql-results+json', timeout=5); return p, time.time() - t0
        except Exception:
            if p.poll() is not None: raise SystemExit(p.stderr.read())
            if time.time() - t0 > 120: raise SystemExit('立ち上がらない')
            time.sleep(0.02)
def stop(p):
    p.send_signal(signal.SIGINT); err = p.communicate(timeout=60)[1]
    m = re.search(r'(\d+)\s+maximum resident set size', err); return int(m.group(1)) if m else None
print(f'# oxigraph serve-read-only({subprocess.run([OXI, "--version"], capture_output=True, text=True).stdout.strip()})、店 {LOC}')
ups = []
for k in range(N):
    p, t = start(); ups.append(t)
    if k < N - 1: rss = stop(p); print(f'  立ち上げ {k+1}: 最初の答え(ASK {{}})まで {t:.3f} 秒 / メモリ最大 {rss/2**20:,.0f} MB')
print(f'  立ち上げ {N}: 最初の答え(ASK {{}})まで {ups[-1]:.3f} 秒(このまま問いを回す)')
PRE = open('queries/PREFIXES.rq').read()
print('\n# queries/ の問い(SPARQL 結果は JSON。1 回目・2 回目)')
for f in sorted(glob.glob('queries/q*.rq')):
    q = PRE + open(f).read(); ts = []
    for _ in range(2): t, ct, b = get(q, 'application/sparql-results+json'); ts.append(t)
    n = len(json.loads(b)['results']['bindings'])
    print(f'  {os.path.basename(f)}: {ts[0]:.3f} 秒 / {ts[1]:.3f} 秒 / 結果 {n} 件 / {len(b):,} バイト')
B = 'https://w3id.org/jp-procedure/'
T = [('手続 56737', B + 'procedure/56737'), ('条 関税法 第62条の15', B + 'provision/329AC0000000061/62_15'), ('改正の記録 地方自治法 第243条の2の8第8項', B + 'change/322AC0000000067/243_2_8/8/2025-11-01_2026-11-18')]
print('\n# DESCRIBE(1 回目・2 回目)')
for lab, u in T:
    for acc, fmt in [('text/turtle', ox.RdfFormat.TURTLE), ('application/ld+json', ox.RdfFormat.JSON_LD)]:
        ts = []
        for _ in range(2): t, ct, b = get(f'DESCRIBE <{u}>', acc); ts.append(t)
        n = sum(1 for _ in ox.parse(io.BytesIO(b), fmt))
        print(f'  {lab} / {acc}: {ts[0]:.3f} 秒 / {ts[1]:.3f} 秒 / 返った型 {ct} / {len(b):,} バイト / トリプル {n}')
        if acc == 'text/turtle' and lab.startswith('手続'): print('    返った Turtle の先頭:\n      ' + b.decode()[:700].replace('\n', '\n      '))
rss = stop(p); print(f'\n  この立ち上げのメモリ最大(/usr/bin/time -l の maximum resident set size): {rss/2**20:,.0f} MB')
