"""人の抜き取り用のまとめ(human-check.csv と human-check.html)を作る。.venv の python(pyoxigraph)。
使い方: python3 scripts/78_make_human_check.py [店の場所] [出力の場所]   既定は store/oxigraph と .(手元だけに置く。80 は公開用のフォルダへ写さない)
入れる行:
  - 別の AI(作った Claude Code とは別の会話の Claude)が区分を決めた記録(jpp:reviewerType)の手続の行 すべて
  - 抜き取り 20 行(固定の種 20261119): 文言が変わった 10、移った 5、移った先なし 5。
    review-sample.csv(前の抜き取り)の手続と、上の行の手続は除く。比べた期間は 2025-11-01〜2026-11-18。
旧い文言・新しい文言の違う所は、CSV では〔-…-〕〔+…+〕、HTML では取り消し線と下線で印を付ける(文字の単位、difflib)。
human-check.html は手元で開き、「合う/合わない/分からない」とメモを付けて、CSV で書き出せる(外のサイトは読まない)。"""
import os, sys, csv, json, random, difflib, html, re, pyoxigraph as ox
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moves_lib import load      # 手元に残した e-Gov の本文(取得はしない)
from clause import kids, text
STORE = sys.argv[1] if len(sys.argv) > 1 else 'store/oxigraph'
OUT = sys.argv[2] if len(sys.argv) > 2 else '.'
SEED = 20261119
os.makedirs(OUT, exist_ok=True)
st = ox.Store.read_only(STORE)
P = open('queries/PREFIXES.rq', encoding='utf-8').read()
def q(s): res = st.query(P + s); vs = [v.value for v in res.variables]; return [{v: (r[v].value if r[v] is not None else '') for v in vs} for r in res]
rows = q('''SELECT ?ch ?ps ?id ?title ?org ?lawId ?lawLabel ?provLabel ?kind ?kindLabel ?oldText ?newText ?mv ?movedLabel ?reviewer ?reviewDate ?reviewReason WHERE {
  ?ch a jpp:ProvisionChange ; dct:temporal ?per ; jpp:changeKind ?kind ; jpp:affects ?ps ; jpp:provision ?prov .
  ?per dcat:startDate "2025-11-01"^^xsd:date ; dcat:endDate "2026-11-18"^^xsd:date .
  ?kind skos:prefLabel ?kindLabel . ?prov rdfs:label ?provLabel .
  ?ps dct:identifier ?id ; dct:title ?title ; jpp:hasCitation/jpp:citedLaw ?law . ?law rdfs:label ?lawLabel ; eli:id_local ?lawId .
  OPTIONAL { ?ps cv:hasCompetentAuthority/skos:prefLabel ?org }
  OPTIONAL { ?ch jpp:oldVersion/jpp:text ?oldText } OPTIONAL { ?ch jpp:newVersion/jpp:text ?newText }
  OPTIONAL { ?ch jpp:movedTo ?mv . ?mv rdfs:label ?movedLabel }
  OPTIONAL { ?ch jpp:review ?rv . ?rv jpp:reviewerType <https://w3id.org/jp-procedure/code/reviewer-type/other-ai> ; jpp:reviewerType/skos:prefLabel ?reviewer ; jpp:reviewDate ?reviewDate ; jpp:reviewReason ?reviewReason }
} ORDER BY ?id''')
prev = {r['手続ID'] for r in csv.DictReader(open('review-sample.csv', encoding='utf-8-sig'))}
reviewed = [r for r in rows if r['reviewer']]
skip = prev | {r['id'] for r in reviewed}
GROUPS = [('文言が変わった', ('wording-numref', 'wording-other'), 10), ('移った', ('swapped-moved', 'removed-moved'), 5), ('移った先が見つからない', ('swapped-nodest', 'removed-nodest'), 5)]
rnd = random.Random(SEED); picked = []
for name, kinds, n in GROUPS:
    pool = sorted([r for r in rows if r['kind'].rsplit('/', 1)[-1] in kinds and r['id'] not in skip], key=lambda r: (r['id'], r['ch']))
    for r in rnd.sample(pool, n): picked.append({**r, '選んだ理由': f'抜き取り({name}、種 {SEED}、母数 {len(pool):,})'})
for r in reviewed: r['選んだ理由'] = f'{r["reviewer"]}が区分を決めた記録({r["reviewDate"]}。{r["reviewReason"]})'
items = reviewed + picked
_idx = {}
def moved_text(uri):
    """移った先の条・項・号の 2026-11-18 版の文言(手元に残した e-Gov の本文から。無ければ空)"""
    if not uri: return ''
    seg = uri.split('/provision/')[1].split('/'); lid = seg[0]; art = seg[1]; sup = art.startswith('suppl-'); art = art.replace('suppl-', '')
    if lid not in _idx: _idx[lid] = load(lid, '2026-11-18')
    ix = _idx[lid]
    if ix is None: return ''
    el = ix.get((sup, art))
    if el is not None and len(seg) >= 3: el = next((p for p in kids(el, 'Paragraph') if p['attr'].get('Num') == seg[2]), None)
    if el is not None and len(seg) >= 4: el = next((i for i in kids(el, 'Item') if i['attr'].get('Num') == seg[3]), None)
    return text(el).strip() if el is not None else ''
for r in items: r['movedText'] = moved_text(r['mv'])   # 抜き取った行だけ
def marks(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False); A = B = ''; HA = HB = ''
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        x, y = a[i1:i2], b[j1:j2]
        if op == 'equal': A += x; B += y; HA += html.escape(x); HB += html.escape(y)
        else:
            if x: A += f'〔-{x}-〕'; HA += f'<del>{html.escape(x)}</del>'
            if y: B += f'〔+{y}+〕'; HB += f'<ins>{html.escape(y)}</ins>'
    return A, B, HA, HB
COLS = ['番号', '選んだ理由', '手続ID', '手続名', '所管', '法令名', '法令ID', '条項号', '区分(機械の判定)', '旧い文言(2025-11-01、違う所に〔-…-〕)', '新しい文言(2026-11-18、違う所に〔+…+〕)', '移った先', '移った先の文言', 'e-Gov の法令のページ', '判定(合う/合わない/分からない)', 'メモ']
out = []; hrows = []
for k, r in enumerate(items, 1):
    new = r['movedText'] if r['movedLabel'] else r['newText']   # 「移った」は移った先の文言と比べる
    A, Bm, HA, HB = marks(r['oldText'], new) if r['oldText'] and new else (r['oldText'], new, html.escape(r['oldText']), html.escape(new))
    egov = f'https://laws.e-gov.go.jp/law/{r["lawId"]}'
    out.append([k, r['選んだ理由'], r['id'], r['title'], r['org'], r['lawLabel'], r['lawId'], r['provLabel'], r['kindLabel'], A, Bm if not r['movedLabel'] else r['newText'], r['movedLabel'], Bm if r['movedLabel'] else '', egov, '', ''])
    hrows.append({'n': k, 'why': r['選んだ理由'], 'id': r['id'], 'title': r['title'], 'org': r['org'], 'law': r['lawLabel'], 'lawId': r['lawId'], 'prov': r['provLabel'], 'kind': r['kindLabel'],
                  'old': HA, 'new': HB, 'newPlain': html.escape(r['newText']), 'moved': r['movedLabel'], 'egov': egov, 'csv': [str(x) for x in out[-1]]})
with open(f'{OUT}/human-check.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f); w.writerow(COLS); w.writerows(out)
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'human_check_template.html'), encoding='utf-8').read()
open(f'{OUT}/human-check.html', 'w', encoding='utf-8').write(tpl.replace('/*DATA*/[]', json.dumps(hrows, ensure_ascii=False)).replace('/*COLS*/[]', json.dumps(COLS, ensure_ascii=False)).replace('/*SEED*/0', str(SEED)))
print(f'別の AI が区分を決めた行 {len(reviewed)} / 抜き取り {len(picked)}(除いた手続 {len(skip)})/ 計 {len(items)} 行')
for r in items: print(f"  {r['id']}\t{r['kindLabel']}\t{r['lawLabel']} {r['provLabel']}")
