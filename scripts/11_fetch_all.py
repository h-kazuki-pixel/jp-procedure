"""法令本文を法令ごとに1回だけ取る(asof=2025-11-01)。取得済みはキャッシュから読むので再取得しない。"""
import sys, time, pandas as pd; sys.path.insert(0, 'scripts'); import egov
d = pd.read_csv('out/r7_law_id.csv', dtype=str, keep_default_na=False)
ids = sorted(set(d.law_id) - {''}); t0 = time.time(); st = {}
for i, lid in enumerate(ids, 1):
    b = egov.get(f'/law_data/{lid}', {'asof': '2025-11-01', 'response_format': 'json', 'json_format': 'full'})
    st[lid] = b.get('_status')
    if i % 100 == 0 or i == len(ids): print(f'{i}/{len(ids)} {time.time()-t0:.0f}s', flush=True)
pd.Series(st, name='status').to_csv('out/11_fetch_status.csv', index_label='law_id')
print('status', pd.Series(st).value_counts().to_dict())
