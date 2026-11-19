"""2026-11-18 時点の版の本文を取得する(1 法令 1 回。キャッシュがあれば取らない)。"""
import sys, time, collections, pandas as pd; sys.path.insert(0, 'scripts'); import egov
NEW = '2026-11-18'
ids = pd.read_csv('out/20_targets.csv', dtype=str).law_id.tolist()
st, t0 = {}, time.time()
for i, lid in enumerate(ids, 1):
    b = egov.get(f'/law_data/{lid}', {'asof': NEW, 'response_format': 'json', 'json_format': 'full'})
    st[lid] = b.get('_status')
    if i % 100 == 0 or i == len(ids): print(f'{i}/{len(ids)} {time.time()-t0:.0f}s', flush=True)
pd.DataFrame({'law_id': list(st), 'status': list(st.values())}).to_csv('out/21_fetch_status.csv', index=False)
print('status', dict(collections.Counter(st.values())))
