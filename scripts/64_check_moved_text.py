"""移った先・候補として足した条・項・号(rdf/changes.ttl.gz の rdfs:comment 付きのもの)に、保存済みの 2026-11-18 版の本文があるかを確かめる。取得しない。"""
import sys, re, gzip, collections
sys.path.insert(0, 'scripts')
from rdf_config import BASE
from moves_lib import load
from clause import kids, text
cur = None; nodes = {}
for line in gzip.open('rdf/changes.ttl.gz', 'rt', encoding='utf-8'):
    m = re.match(r'^<' + re.escape(BASE) + r'(provision/[^>]+)> a eli:LegalResourceSubdivision', line)
    if m: cur = m.group(1); nodes[cur] = None; continue
    if line.startswith('<'): cur = None; continue
    m = re.match(r'\s+jpp:level <[^>]+/level/(\w+)>', line)
    if m and cur: nodes[cur] = m.group(1)
print(f'# 移った先・候補として足した条・項・号: {len(nodes):,}  深さ {dict(collections.Counter(nodes.values()))}')
res = collections.Counter(); bad = []; idx = {}
for path, lv in nodes.items():
    seg = path.split('/')[1:]; lid = seg[0]; art = seg[1]; sup = art.startswith('suppl-'); art = art.replace('suppl-', '')
    if lid not in idx: idx[lid] = load(lid, '2026-11-18')
    ix = idx[lid]
    if ix is None: res['2026-11-18 版の本文が無い'] += 1; bad.append(path); continue
    a = ix.get((sup, art))
    el = a
    if el is not None and len(seg) >= 3: el = next((p for p in kids(a, 'Paragraph') if p['attr'].get('Num') == seg[2]), None)
    if el is not None and len(seg) >= 4: el = next((i for i in kids(el, 'Item') if i['attr'].get('Num') == seg[3]), None)
    if el is None: res['2026-11-18 版にその番号が無い'] += 1; bad.append(path); continue
    t = re.sub(r'\s+', '', text(el))
    res['本文あり' if t else '本文が空'] += 1
    if not t: bad.append(path)
print(f'  法令 {len(idx):,}')
for k, v in res.items(): print(f'  {k}: {v:,}')
for b in bad[:10]: print('  無い例:', b)
