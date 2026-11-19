"""照合できた最も深い条・項・号に、2025-11-01 版と 2026-11-18 版の本文を eli:LegalExpression として入れる。保存した本文から作り、取り直さない。"""
import sys, gzip, json, collections, pandas as pd
sys.path.insert(0, 'scripts')
import egov
from clause import article_index, kids, text
from rdf_config import BASE, PREFIXES
OLD, NEW = '2025-11-01', '2026-11-18'
d = pd.read_csv('out/full_check.csv', dtype=str, keep_default_na=False)
R = pd.read_csv('out/law_revisions.csv', dtype=str, keep_default_na=False)
REV = R.set_index('law_revision_id')
cur = R[R.current_revision_status == 'CurrentEnforced'].groupby('law_id').law_revision_id.agg(list)
e = R.amendment_enforcement_date; W = set(R[(e >= '2025-11-02') & (e <= '2026-11-18')].law_id)
OKR = {'号まで一致': 3, '項まで': 2, '条まで': 1}
X = d[d.結果_追加.isin(OKR)]
def lit(s, lang=None, dt=None):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f'"{s}"' + (f'@{lang}' if lang else f'^^xsd:{dt}' if dt else '')
def iri(p): return f'<{BASE}{p}>'
def body(lid, asof):
    b = egov.get(f'/law_data/{lid}', {'asof': asof, 'response_format': 'json', 'json_format': 'full'}, offline=True)
    st = b.get('_status')
    if st != 200: return None, st, ''
    lb = [c for c in b['law_full_text']['children'] if isinstance(c, dict) and c['tag'] == 'LawBody'][0]
    return article_index(lb), 200, b['revision_info']['law_revision_id']
def elem(idx, p, lv):
    a = idx.get((p['附則'], p['条']))
    if a is None: return None, None
    seg = ('suppl-' if p['附則'] else '') + p['条']
    if lv == 1: return a, seg
    paras = kids(a, 'Paragraph')
    pp = [x for x in paras if x['attr'].get('Num') == p['項']] if p['項'] else (paras if len(paras) == 1 else [])
    if not pp: return None, None
    pn = pp[0]['attr'].get('Num')
    if lv == 2: return pp[0], f'{seg}/{pn}'
    it = [x for x in kids(pp[0], 'Item') if x['attr'].get('Num') == p['号']]
    return (it[0], f'{seg}/{pn}/{p["号"]}') if it else (None, None)
def vdate(rev):
    if rev in REV.index and REV.amendment_enforcement_date.get(rev, ''):
        v = REV.amendment_enforcement_date[rev]; return (v.iloc[0] if hasattr(v, 'iloc') else v), '改正履歴の施行期日'
    t = rev.split('_')[1]; return f'{t[:4]}-{t[4:6]}-{t[6:]}', '版の ID の日付'
f = gzip.open('rdf/expressions.ttl.gz', 'wt', encoding='utf-8')
for k, v in PREFIXES.items(): f.write(f'@prefix {k}: <{v}> .\n')
f.write('\n')
n = 0; st = collections.Counter(); vd = collections.Counter(); seen = set(); nodes = 0
for lid, g in X.groupby('law_id'):
    oi, _, orev = body(lid, OLD)
    if lid in W or egov.get(f'/law_data/{lid}', {'asof': NEW, 'response_format': 'json', 'json_format': 'full'}, offline=True).get('_status') != '未取得':
        ni, nst, nrev = body(lid, NEW); how = '取得した 2026-11-18 版' if ni is not None else f'2026-11-18 版が {nst}'
    else:
        c = cur.get(lid, [])
        if c == [orev]: ni, nrev, how = oi, orev, '2025-11-02〜2026-11-18 に施行された改正が無く、施行中の版が 2025-11-01 版と同じ'
        elif not c: ni, nrev, how = None, '', '2026-11-18 版を取っておらず、改正履歴に施行中(CurrentEnforced)の版が無い'
        else: ni, nrev, how = None, '', f'2026-11-18 版を取っておらず、施行中の版が違う({c})'
    for i, r in g.iterrows():
        p = json.loads(r.分解_追加); lv = OKR[r.結果_追加]
        oe, path = elem(oi, p, lv); assert oe is not None
        key = f'provision/{lid}/{path}'
        if key in seen: continue
        seen.add(key); nodes += 1
        vers = {}   # rev -> (要素, [asof...])
        vers.setdefault(orev, [oe, []])[1].append(OLD)
        if ni is None: st[how] += 1
        else:
            ne, _ = elem(ni, p, lv)
            if ne is None: st['2026-11-18 版にその条・項・号が無い'] += 1
            else:
                st[how + (' / 版が同じ' if nrev == orev else ' / 版が違う')] += 1
                vers.setdefault(nrev, [ne, []])[1].append(NEW)
        for rev, (el, asofs) in vers.items():
            dt, src = vdate(rev); vd[src] += 1
            E = iri(f'{key}/version/{rev}')
            pos = [('a', 'eli:LegalExpression'), ('eli:realizes', iri(key)), ('eli:version_date', lit(dt, dt='date')), ('jpp:lawRevision', lit(rev)),
                   ('eli:language', '<http://publications.europa.eu/resource/authority/language/JPN>'), ('jpp:text', lit(text(el).strip(), 'ja'))]
            pos += [('jpp:asOf', lit(a, dt='date')) for a in asofs]
            f.write(E + ' ' + ' ;\n    '.join(f'{p_} {o}' for p_, o in pos) + ' .\n')
            f.write(f'{iri(key)} eli:is_realized_by {E} .\n'); n += len(pos) + 1
f.close()
print(f'本文を入れた節(照合できた最も深い条・項・号): {nodes:,}')
print('2026-11-18 版の扱い(節の数):'); [print(f'  {k}: {v:,}') for k, v in st.most_common()]
print('版の施行日(eli:version_date)の出どころ(版の数):', dict(vd))
print(f'書いたトリプル {n:,}')
