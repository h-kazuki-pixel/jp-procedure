"""閲覧ページのはじめの画面と「府省庁ごと」の数を、queries/ の問い(q5・q6・q7・q3)で出して stats.json に書く。.venv の python(pyoxigraph)。
使い方: python3 scripts/75_make_stats.py <店(62_oxigraph_load.py が作るもの)> <stats.json> [データの置き場所(既定 rdf)]
何度流しても、同じデータなら同じ中身になる(日時は入れない。元にした RDF のファイルの SHA-256 を入れる)。
stats.json の隣に README.md・view.html があれば、その中の <!-- s:キー --> の数も書き込む(stats_text.py)。"""
import sys, os, json, glob, hashlib, time, resource, pyoxigraph as ox
store, out = sys.argv[1], sys.argv[2]; RDFDIR = sys.argv[3] if len(sys.argv) > 3 else os.environ.get('RDF_DIR', 'rdf')
QD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'queries')
P = open(f'{QD}/PREFIXES.rq', encoding='utf-8').read()
st = ox.Store.read_only(store)
def run(fn):
    t0 = time.time(); rows = [{k: (r[k].value if r[k] is not None else None) for k in [v.value for v in res.variables]} for res in [st.query(P + open(f'{QD}/{fn}', encoding='utf-8').read())] for r in res]
    print(f'  {fn}: {len(rows)} 行 / {time.time() - t0:.2f} 秒', flush=True); return rows
procs = int(run('q5_count_procedures.rq')[0]['procedures'])
per = {}
for r in run('q6_changes_by_period.rq'): per[(r['start'], r['end'])] = {'changes': int(r['changes']), 'notified': int(r['notified']), 'law_level': 0}
for r in run('q7_law_level_by_period.rq'): per.setdefault((r['start'], r['end']), {'changes': 0, 'notified': 0, 'law_level': 0})['law_level'] = int(r['law_level'])
# 根拠の法令が廃止・失効した記録(条文の文言の比べとは別に数える。0 の期間も置く)
for v in per.values(): v.update(law_status_laws=0, law_status_procedures=0)
for r in run('q8_law_status_by_period.rq'):
    v = per.setdefault((r['start'], r['end']), {'changes': 0, 'notified': 0, 'law_level': 0, 'law_status_laws': 0, 'law_status_procedures': 0})
    v['law_status_laws'] = int(r['laws']); v['law_status_procedures'] = int(r['procedures'])
# 府省庁ごと(q3。期間は問いの中に書いた 2025-11-01〜2026-11-18)。並びは問いのまま(変わった手続の多い順)に、同じ数は府省庁名で決める
mins = [{'ministry': r['ministry'], 'procedures': int(r['procedures']), 'changed': int(r['changed']), 'percent': float(r['percent'])} for r in run('q3_changed_by_ministry.rq')]
mins.sort(key=lambda x: (-x['changed'], x['ministry']))
files = sorted(glob.glob(f'{RDFDIR}/*.ttl.gz') + glob.glob(f'{RDFDIR}/weekly/*.ttl.gz'))
h = hashlib.sha256()
for f in files: h.update(os.path.relpath(f, RDFDIR).encode() + b'\0' + hashlib.sha256(open(f, 'rb').read()).digest())
S = {'procedures': procs,
     'periods': [{'start': s, 'end': e, **v, 'ratio': round(v['law_level'] / v['notified'], 1) if v['notified'] else None} for (s, e), v in sorted(per.items())],
     'ministries': {'start': '2025-11-01', 'end': '2026-11-18', 'rows': mins},
     'queries': {'procedures': 'queries/q5_count_procedures.rq', 'changes': 'queries/q6_changes_by_period.rq', 'notified': 'queries/q6_changes_by_period.rq', 'law_level': 'queries/q7_law_level_by_period.rq', 'law_status': 'queries/q8_law_status_by_period.rq', 'ministries': 'queries/q3_changed_by_ministry.rq'},
     'note': 'notified = 根拠の条・項・号が変わった手続(文言が変わった・別の番号へ移った・無くなった)の数。law_level = 根拠の法令に期間内の改正がある手続の数。changes = 改正の記録(条・項・号ごと)の数。ratio = law_level ÷ notified(小数第 1 位で丸めた)。law_status_laws・law_status_procedures = 根拠の法令が廃止・失効した記録の法令の数と、それを根拠に挙げる手続の数(notified とは別に数える。初めの期間の分は 2026-11-21 の補い)。ministries = 所管府省庁ごとの手続の数(procedures)・期間に根拠の条・項・号が変わった手続の数(changed)・割合(percent、%。小数第 2 位で丸めた)。scripts/75_make_stats.py が書いた',
     'data_sha256': h.hexdigest(), 'data_files': len(files)}
with open(out, 'w', encoding='utf-8') as f: json.dump(S, f, ensure_ascii=False, indent=1); f.write('\n')
# README の冒頭と閲覧ページの、JavaScript が無くても読める要約の数(<!-- s:キー -->)を、stats.json と同じ数で書き込む(stats_text.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import stats_text
V = stats_text.values(S)
for fn in ['README.md', 'view.html']:
    fp = os.path.join(os.path.dirname(os.path.abspath(out)), fn)
    if not os.path.exists(fp): continue
    src = open(fp, encoding='utf-8').read(); new, n = stats_text.fill(src, V, fn)
    if new != src: open(fp, 'w', encoding='utf-8').write(new)
    print(f'  {fn} の印 {n} か所を stats.json の数で書き込んだ')
print(json.dumps({k: S[k] for k in ['procedures', 'periods']}, ensure_ascii=False))
print(f"  府省庁 {len(mins)} 行 / 手続の和 {sum(x['procedures'] for x in mins):,} / 変わった手続の和 {sum(x['changed'] for x in mins):,}")
print(f'  メモリ最大 {(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)) / 2**20:,.0f} MB')
