"""Cloud Run の SPARQL(認証つき)を測る。標準ライブラリだけ。
引数: サービスの URL。環境変数 ID_TOKEN に `gcloud auth print-identity-token` の値を入れる。
1. 認証なしで引いて 403 になるか
2. 最初の答え(ASK {})までの秒数(0 台からなら立ち上がりを含む)
3. 全体のトリプルの数
4. queries/ の 4 つの問い(1 回目・2 回目)
5. DESCRIBE(手続・条・改正の記録、Turtle と JSON-LD。1 回目・2 回目)
"""
import glob, json, os, sys, time, urllib.error, urllib.parse, urllib.request

BASE = sys.argv[1].rstrip('/') + '/query'
TOKEN = os.environ['ID_TOKEN']


def get(q, accept, auth=True, timeout=60):
    h = {'Accept': accept}
    if auth: h['Authorization'] = 'Bearer ' + TOKEN
    req = urllib.request.Request(BASE + '?' + urllib.parse.urlencode({'query': q}), headers=h)
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout); b = r.read(); st = r.status; ct = r.headers.get('Content-Type')
    except urllib.error.HTTPError as e:
        b = e.read(); st = e.code; ct = e.headers.get('Content-Type')
    return time.time() - t0, st, ct, b


print(f'# {time.strftime("%Y-%m-%d %H:%M:%S")}  {BASE}')
t, st, _, _ = get('ASK {}', 'application/sparql-results+json', auth=False)
print(f'  認証なし: HTTP {st}({t:.3f} 秒)')
t, st, _, b = get('ASK {}', 'application/sparql-results+json')
print(f'  最初の答え(ASK {{}}): HTTP {st} / {t:.3f} 秒 / {b.decode()[:60]}')
for _ in range(2):
    t, st, _, b = get('ASK {}', 'application/sparql-results+json')
    print(f'  続けて ASK {{}}: {t:.3f} 秒')
t, st, _, b = get('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }', 'application/sparql-results+json')
print(f'  全体のトリプル: {json.loads(b)["results"]["bindings"][0]["n"]["value"]}({t:.3f} 秒)')
if '--quick' in sys.argv: sys.exit(0)

PRE = open('queries/PREFIXES.rq').read()
print('\n# queries/ の問い(1 回目・2 回目)')
for f in sorted(glob.glob('queries/q*.rq')):
    q = PRE + open(f).read(); ts = []
    for _ in range(2):
        t, st, _, b = get(q, 'application/sparql-results+json'); ts.append(t)
    n = len(json.loads(b)['results']['bindings']) if st == 200 else f'HTTP {st}'
    print(f'  {os.path.basename(f)}: {ts[0]:.3f} 秒 / {ts[1]:.3f} 秒 / 結果 {n} 件 / {len(b):,} バイト')

B = 'https://w3id.org/jp-procedure/'
T = [('手続 56737', B + 'procedure/56737'), ('条 関税法 第62条の15', B + 'provision/329AC0000000061/62_15'),
     ('改正の記録 地方自治法 第243条の2の8第8項', B + 'change/322AC0000000067/243_2_8/8/2025-11-01_2026-11-18')]
print('\n# DESCRIBE(1 回目・2 回目)')
for lab, u in T:
    for acc in ['text/turtle', 'application/ld+json']:
        ts = []
        for _ in range(2):
            t, st, ct, b = get(f'DESCRIBE <{u}>', acc); ts.append(t)
        print(f'  {lab} / {acc}: {ts[0]:.3f} 秒 / {ts[1]:.3f} 秒 / HTTP {st} / 返った型 {ct} / {len(b):,} バイト')
