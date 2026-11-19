"""版(eli:LegalExpression)の ID と施行日を確かめる。版の ID(jpp:lawRevision)は e-Gov の法令履歴ID(law_revision_id)。.venv の python。"""
import csv, collections, re, pyoxigraph as ox
st = ox.Store.read_only('store/oxigraph')
P = 'PREFIX eli: <http://data.europa.eu/eli/ontology#> PREFIX jpp: <https://w3id.org/jp-procedure/def#> '
rows = list(st.query(P + 'SELECT ?e ?rid ?vd WHERE { ?e a eli:LegalExpression ; jpp:lawRevision ?rid . OPTIONAL { ?e eli:version_date ?vd } }'))
rev = {r['law_revision_id']: r for r in csv.DictReader(open('out/law_revisions.csv', encoding='utf-8'))}
c = collections.Counter(); ex = collections.defaultdict(list)
for s in rows:
    e, rid, vd = s['e'].value, s['rid'].value, (s['vd'].value if s['vd'] else None)
    c['版'] += 1; c['施行日あり' if vd else '施行日なし'] += 1
    c['URI の末尾 = 版の ID' if e.endswith('/version/' + rid) else 'URI の末尾 ≠ 版の ID'] += 1
    m = re.fullmatch(r'([0-9A-Za-z]+)_(\d{8})_([0-9A-Za-z]{15})', rid)
    if not m: c['ID の形が違う'] += 1; ex['ID の形が違う'].append(rid); continue
    c['ID の形 = 法令ID_YYYYMMDD_改正法令ID'] += 1
    if m.group(3) == '0' * 15: c['改正法令ID が 000000000000000(制定時か基準日)'] += 1
    d = f'{m.group(2)[:4]}-{m.group(2)[4:6]}-{m.group(2)[6:]}'
    if vd == d: c['施行日 = ID の YYYYMMDD'] += 1
    else: c['施行日 ≠ ID の YYYYMMDD'] += 1; ex['施行日 ≠ ID'].append((rid, vd))
    c['改正履歴にある' if rid in rev else '改正履歴に無い'] += 1
print(f'# 版の ID と施行日(store/oxigraph の eli:LegalExpression と、out/law_revisions.csv)')
for k, v in c.items(): print(f'  {k}: {v:,}')
for k, v in ex.items(): print(f'  例 {k}: {v[:5]}')
