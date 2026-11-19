"""change_rules.classify が、40〜45 を順に通した結果(out/fix6_compare.csv)と同じ区分を出すかを、全 47,352 行で確かめる。取得しない。"""
import sys, json, time, collections, pandas as pd
sys.path.insert(0, 'scripts')
from moves_lib import load
from change_rules import classify
t0 = time.time()
c = pd.read_csv('out/fix6_compare.csv', dtype=str, keep_default_na=False)
got = {}; cache_r = {}
for lid, g in c[c.区分 != '比べられない'].groupby('law_id'):
    oi, ni = load(lid, '2025-11-01'), load(lid, '2026-11-18'); cache = {}
    for i, r in g.iterrows():
        key = (r.深さ, r.分解_追加)
        if key not in cache_r.setdefault(lid, {}):
            p = json.loads(r.分解_追加)
            if oi is None or ni is None: cache_r[lid][key] = {'kind': '比べられない'}
            else:
                x = classify(oi, ni, p, r.深さ, cache); cache_r[lid][key] = x or {'kind': '文言が同じ'}
        got[i] = cache_r[lid][key]['kind']
c['module'] = c.index.map(lambda i: got.get(i, '比べられない'))
human = c.人の確認日 != ''
same = (c.module == c.新区分) | human
print(f'# change_rules.classify と fix6(45 まで)の区分の比べ(全 {len(c):,} 行、人の確認 {int(human.sum())} 行は比べない)')
print(f'  同じ: {int(same.sum()):,} / 違う: {int((~same).sum()):,} / 所要 {time.time()-t0:.0f} 秒')
d = c[~same]
if len(d): print(d.groupby(['新区分', 'module']).size().to_string()); print(d[['手続ID', '法令名', '根拠条項号', '深さ', '新区分', 'module']].head(20).to_string())
print('  人の確認の行のモジュールの区分:', c[human].module.tolist())
