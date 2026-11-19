"""閲覧ページの「変わった手続の一覧」に使う changed.json を作る。.venv の python(pyoxigraph)。
使い方: python3 scripts/82_make_changed_list.py <店の場所> <changed.json>
- 1 行 = 改正の記録 × 手続(すべての期間)。手続ID・手続名・所管・法令名・条項号・区分・違う所の短い抜き出し。
- 抜き出しの作り方(区分ごと):
  - 文言が変わった・大きく書き換わった・入れ替わった→移った先が見つからない: 旧い文言と新しい文言を文字の単位で比べ(difflib)、
    最初に違う所の、旧い文字と新しい文字を、前後 4 文字と一緒に出す。違う所が 2 か所以上あれば「ほか n か所」。
    1 か所の文字が 16 文字を超えるときは、16 文字で切って「…」を付ける。
  - 移った(入れ替わった→移った・無くなった→移った): 「第○条… → 第○条…」(同じ番号 → 移った先)
  - 移った先が一つに決まらない: 「第○条… → 候補 n 件」
  - 無くなった→移った先が見つからない・判定できない: 「同じ番号の要素が無い」
- 並びは、区分の順(文言が変わった: それ以外、大きく書き換わった、文言が変わった: 番号の参照だけ、入れ替わった…、無くなった…)、法令名、条項号、手続ID。
- 何度流しても、同じデータなら同じ中身になる(日時は入れない)。"""
import sys, json, difflib, pyoxigraph as ox
STORE, OUT = sys.argv[1], sys.argv[2]
st = ox.Store.read_only(STORE)
P = open('queries/PREFIXES.rq', encoding='utf-8').read()
def q(s): res = st.query(P + s); vs = [v.value for v in res.variables]; return [{v: (r[v].value if r[v] is not None else '') for v in vs} for r in res]
ORDER = ['wording-other', 'rewritten', 'wording-numref', 'swapped-moved', 'swapped-ambiguous', 'swapped-nodest', 'removed-moved', 'removed-ambiguous', 'removed-nodest', 'removed-undetermined']
chs = {r['ch']: r for r in q('''SELECT ?ch ?start ?end ?kind ?kindLabel ?prov ?provLabel ?oldText ?newText ?movedLabel (COUNT(DISTINCT ?cand) AS ?ncand) WHERE {
  ?ch a jpp:ProvisionChange ; dct:temporal ?per ; jpp:changeKind ?kind ; jpp:provision ?prov . ?per dcat:startDate ?start ; dcat:endDate ?end .
  ?kind skos:prefLabel ?kindLabel . ?prov rdfs:label ?provLabel .
  OPTIONAL { ?ch jpp:oldVersion/jpp:text ?oldText } OPTIONAL { ?ch jpp:newVersion/jpp:text ?newText }
  OPTIONAL { ?ch jpp:movedTo/rdfs:label ?movedLabel } OPTIONAL { ?ch jpp:candidate ?cand }
} GROUP BY ?ch ?start ?end ?kind ?kindLabel ?prov ?provLabel ?oldText ?newText ?movedLabel''')}
CTX, CUT = 4, 16
def cut(s): return s if len(s) <= CUT else s[:CUT] + '…'
def snip(c):
    k = c['kind'].rsplit('/', 1)[-1]
    if k.endswith('-moved') and c['movedLabel']: return {'type': 'moved', 'from': c['provLabel'], 'to': c['movedLabel']}
    if k.endswith('-ambiguous'): return {'type': 'ambiguous', 'from': c['provLabel'], 'candidates': int(c['ncand'])}
    if k.startswith('removed'): return {'type': 'gone', 'text': '同じ番号の要素が無い'}
    a, b = c['oldText'], c['newText']
    if not a or not b: return {'type': 'none'}
    ops = [o for o in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if o[0] != 'equal']
    if not ops: return {'type': 'none'}
    _, i1, i2, j1, j2 = ops[0]
    return {'type': 'diff', 'before': a[max(0, i1 - CTX):i1], 'old': cut(a[i1:i2]), 'new': cut(b[j1:j2]), 'after': a[i2:i2 + CTX], 'more': len(ops) - 1}
SN = {ch: snip(c) for ch, c in chs.items()}
rows = q('''SELECT ?ch ?ps ?id ?title ?org ?lawLabel WHERE {
  ?ch a jpp:ProvisionChange ; jpp:affects ?ps . ?ps dct:identifier ?id ; dct:title ?title .
  OPTIONAL { ?ps cv:hasCompetentAuthority/skos:prefLabel ?org } OPTIONAL { ?ps jpp:hasCitation/jpp:citedLaw/rdfs:label ?lawLabel } }''')
out = []
for r in rows:
    c = chs[r['ch']]; k = c['kind'].rsplit('/', 1)[-1]
    out.append({'id': r['id'], 'ps': r['ps'], 'title': r['title'], 'org': r['org'], 'law': r['lawLabel'], 'prov': c['prov'], 'provLabel': c['provLabel'],
                'kind': k, 'kindLabel': c['kindLabel'], 'start': c['start'], 'end': c['end'], 'snip': SN[r['ch']]})
out.sort(key=lambda x: (ORDER.index(x['kind']), x['law'], x['provLabel'], x['id']))
S = {'note': '根拠の条・項・号が変わった手続(文言が変わった・別の番号へ移った・無くなった)の一覧(閲覧ページの #/changed)。scripts/82_make_changed_list.py が店から作った。抜き出しの作り方はスクリプトの先頭に書いた',
     'kinds': ORDER, 'rows': out}
with open(OUT, 'w', encoding='utf-8') as f: json.dump(S, f, ensure_ascii=False, separators=(',', ':')); f.write('\n')
import collections
print(f'行 {len(out):,} / 改正の記録 {len(chs):,} / 抜き出しの種類 {dict(collections.Counter(s["type"] for s in SN.values()))}')
print('期間ごと:', dict(collections.Counter((x['start'], x['end']) for x in out)))
for x in [x for x in out if x['id'] in ('119637', '3549', '112875', '222279', '50387')]: print(' ', x['id'], x['kindLabel'], x['snip'])
