"""法令一覧を全件取る。引数: asof 日付 (省略時は現時点)。"""
import sys, json, csv; sys.path.insert(0, 'scripts'); import egov
ASOF = sys.argv[1] if len(sys.argv) > 1 else None; LIM = 1000
rows, off, total = [], 0, None
while True:
    b = egov.get('/laws', {**({'asof': ASOF} if ASOF else {}), 'limit': LIM, 'offset': off, 'omit_current_revision_info': 'true'})
    assert b['_status'] == 200, b
    total = b['total_count']
    for x in b['laws']:
        li, ri = x['law_info'], x.get('revision_info') or {}
        rows.append({'law_id': li['law_id'], 'law_num': li['law_num'], 'law_type': li['law_type'],
                     'law_title': ri.get('law_title') or '', 'abbrev': ri.get('abbrev') or '',
                     'repeal_status': ri.get('repeal_status') or '', 'law_revision_id': ri.get('law_revision_id') or '',
                     'current_revision_status': ri.get('current_revision_status') or ''})
    off += b['count']
    if b['count'] == 0 or off >= total: break
with open(f'data/api/laws_asof_{ASOF or "current"}.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('total_count', total, '取得行数', len(rows), '異なる law_id', len({r["law_id"] for r in rows}))
import collections
print(collections.Counter(r['law_type'] for r in rows))
print(collections.Counter(r['repeal_status'] for r in rows))
