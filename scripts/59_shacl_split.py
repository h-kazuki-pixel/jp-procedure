"""分けて通す SHACL の取りまとめ(system python3 でよい。各回は .venv の python で別プロセス)。
使い方: python3 -I scripts/59_shacl_split.py test   … 手続 2,000 件で、まとめて通す・分けて通すを比べる
        python3 -I scripts/59_shacl_split.py full   … 全件を分けて通す"""
import sys, os, json, subprocess, collections, time
MODE = sys.argv[1]; D = f'out/shacl_chunks/{MODE}'; R = f'{D}/results'; os.makedirs(R, exist_ok=True)
M = json.load(open(f'{D}/manifest.json'))
OWN = os.environ.get('SHAPES', 'rdf/shapes.ttl'); OFF = os.environ.get('CPSV_SHACL', 'data/vocab/cpsv-ap-3.2.0-SHACL.ttl')
PY = os.environ.get('PYTHON', '.venv/bin/python')
def go(tag, run, shapes):
    out = f'{R}/{tag}_{run["name"]}.json'
    if not os.path.exists(out):
        p = subprocess.run([PY, '-I', 'scripts/58_shacl_worker.py', D, json.dumps(run), out, shapes], capture_output=True, text=True)
        if p.returncode != 0: print(p.stderr[-3000:]); raise SystemExit(f'失敗: {tag} {run["name"]}')
    r = json.load(open(out))
    print(f'  {tag} {r["name"]}: トリプル {r["triples"]:,} / 結果 {len(r["results"]):,}(対象外として外した {r["dropped_outside_focus"]:,})/ 読み {r["load_s"]} 秒・照合 {r["validate_s"]} 秒 / メモリ最大 {r["maxrss"]/2**20:,.0f} MB', flush=True)
    return r
def kinds(rs):
    k = collections.Counter((x['sev'], x['cls'], x['shape'], x['path'], x['comp']) for r in rs for x in r['results']); return k
def keys(rs): return collections.Counter((x['focus'], x['shape'], x['path'], x['comp'], x['value']) for r in rs for x in r['results'])
def table(k, title):
    print(f'\n  {title}: 計 {sum(k.values()):,} 件、種類 {len(k)}')
    if k:
        print('  | 重さ | 対象の型 | 形 | 経路 | 制約 | 件数 |\n  |---|---|---|---|---|---:|')
        for (sev, cls, shp, path, comp), v in sorted(k.items(), key=lambda x: (-x[1], x[0])): print(f'  | {sev} | {cls} | {shp} | {path} | {comp} | {v:,} |')
def examples(rs, n=1):
    seen = collections.Counter()
    for r in rs:
        for x in r['results']:
            kk = (x['shape'], x['path'], x['comp'])
            if seen[kk] < n: seen[kk] += 1; print(f'    例 {x["shape"]} {x["path"]} {x["comp"]}: {x["focus"]} 値 {x["value"]} — {x["msg"]}')
t0 = time.time(); TOTAL = {}
for tag, shapes, runs in [('own', OWN, M['own']), ('official', OFF, M['official'])]:
    print(f'\n# {"自作の SHACL(rdf/shapes.ttl)" if tag == "own" else "CPSV-AP 3.2.0 の公式 SHACL"} — {MODE}', flush=True)
    split = [go(tag, r, shapes) for r in runs]
    ks = kinds(split)
    if MODE.startswith('test'):
        whole = go(tag + '_whole', dict(name='whole', data=M['whole'], focus=None, shapes=None), shapes)
        kw = kinds([whole])
        table(kw, 'まとめて通した'); table(ks, '分けて通した')
        same_kind = kw == ks; same_key = keys([whole]) == keys(split)
        print(f'\n  比べ: 種類ごとの件数が同じ → {same_kind} / 1 件ずつ(対象・形・経路・制約・値)が同じ → {same_key}')
        print(f'  メモリ最大: まとめて {whole["maxrss"]/2**20:,.0f} MB / 分けた回の最大 {max(r["maxrss"] for r in split)/2**20:,.0f} MB')
        if not (same_kind and same_key):
            a, b = keys([whole]), keys(split)
            print('  まとめてだけ:', list((a - b).items())[:10]); print('  分けてだけ:', list((b - a).items())[:10])
            raise SystemExit('違いがあった。ここで止める。')
    else:
        table(ks, '分けて通した')
        if sum(ks.values()): TOTAL[tag] = sum(ks.values())
        print(f'\n  回の数 {len(split)} / メモリ最大(回ごとの最大の最大) {max(r["maxrss"] for r in split)/2**20:,.0f} MB / 照合の合計 {sum(r["validate_s"] for r in split):,.0f} 秒')
    examples(split)
print(f'\n所要 {time.time()-t0:.0f} 秒')
if MODE == 'full' and TOTAL: print(f'違反あり: {TOTAL}'); sys.exit(2)
