"""全行の根拠条項号を条・項・号に分け、2025-11-01 時点の本文で照合する(本文はキャッシュから読むだけ。新たに取らない)。"""
import sys, json, collections, pandas as pd
sys.path.insert(0, 'scripts'); import egov
from clause import parse_base, parse_ext, article_index, check, RULES
from common import jshape
from common_load import load
ASOF = '2025-11-01'
d = pd.read_csv('out/r7_law_id.csv', dtype=str, keep_default_na=False)
r7 = load('r7')[['手続ID', '総手続件数']]
d = d.merge(r7, on='手続ID', how='left')
assert len(d) == 76275
pb = d['根拠条項号'].map(parse_base)
pe = d['根拠条項号'].map(parse_ext)
d['分解_基本'] = pb.map(lambda p: json.dumps(p, ensure_ascii=False) if p else '')
d['分解_追加'] = pe.map(lambda x: json.dumps(x[0], ensure_ascii=False) if x[0] else '')
d['使った型'] = pe.map(lambda x: x[1]); d['準用する側'] = pe.map(lambda x: x[2])

out = {k: [''] * len(d) for k in ['結果_基本', '補足_基本', '注記_基本', '結果_追加', '補足_追加', '注記_追加', 'law_revision_id', '条キー']}
fail = {}
for lid, g in d.groupby('law_id'):
    if lid == '':
        for i in g.index:
            for s in ('基本', '追加'): out[f'結果_{s}'][i] = '法令IDが決まらない'
        continue
    b = egov.get(f'/law_data/{lid}', {'asof': ASOF, 'response_format': 'json', 'json_format': 'full'}, offline=True)
    if b.get('_status') != 200:
        fail[lid] = b.get('_status')
        for i in g.index:
            for s in ('基本', '追加'): out[f'結果_{s}'][i] = f'本文が取れない({b.get("_status")})'
        continue
    lb = [c for c in b['law_full_text']['children'] if isinstance(c, dict) and c['tag'] == 'LawBody'][0]
    idx = article_index(lb); rev = b['revision_info']['law_revision_id']; del b, lb
    for i in g.index:
        out['law_revision_id'][i] = rev
        for s, p in (('基本', pb[i]), ('追加', pe[i][0])):
            if p is None: out[f'結果_{s}'][i] = '分けられない'; continue
            r, note, memo = check(idx, p); out[f'結果_{s}'][i] = r; out[f'補足_{s}'][i] = note; out[f'注記_{s}'][i] = memo
            if s == '追加' and r != '法令はあるが条が無い':
                out['条キー'][i] = f"{lid}|{'附則' if p['附則'] else '本則'}|{p['条']}"
for k, v in out.items(): d[k] = v
print('本文が取れなかった法令', len(fail), fail)

order = ['号まで一致', '項まで', '条まで', '法令はあるが条が無い', '分けられない', '法令IDが決まらない']
print('\n# 照合結果(全 76,275 行)  基本=試行と同じ分け方 / 追加=型を足した後')
vb, ve = d['結果_基本'].value_counts(), d['結果_追加'].value_counts()
for k in order + sorted((set(vb.index) | set(ve.index)) - set(order)):
    print(f'  {k}: 基本 {vb.get(k,0)} ({vb.get(k,0)/len(d)*100:.2f}%) / 追加 {ve.get(k,0)} ({ve.get(k,0)/len(d)*100:.2f}%)')
for s in ('基本', '追加'):
    print(f'\n# 内訳({s})'); print(d.groupby([f'結果_{s}', f'補足_{s}']).size().to_string())

print('\n# 注記(追加)'); print(d.groupby(['結果_追加', '注記_追加']).size()[lambda x: x.index.get_level_values(1) != ''].to_string())
print('\n# 型を足す前と後: 「分けられない」の行数(法令IDの有無によらず、根拠条項号だけで数える)')
n = (pb.isna()).sum(); print(f'  基本: {n}')
t_counts = d['使った型'].value_counts()
for name, _ in RULES:
    c = int(t_counts.get(name, 0)); n -= c; print(f'  + {name}: {c} 行が分けられるようになった → 残り {n}')
print('\n# 型を足して分けられた行の照合結果(結果_追加)')
print(d[d['使った型'] != ''].groupby(['使った型', '結果_追加']).size().to_string())

for s, mask in (('基本', pb.isna()), ('追加', pe.map(lambda x: x[0] is None))):
    sh = d.loc[mask, '根拠条項号'].map(jshape).value_counts()
    sh.to_csv(f'out/full_unparsed_shapes_{s}.csv', header=['行数'])
    print(f'\n# 分けられない根拠条項号の型({s}): 行数 {int(mask.sum())}, 型の数 {len(sh)}。上位40')
    for k, v in sh.head(40).items(): print(f'  {v:5d}  {k}')
d.to_csv('out/full_check.csv', index=False)
