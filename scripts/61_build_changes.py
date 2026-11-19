"""改正の記録の RDF(rdf/changes.ttl.gz)。1 件 = 根拠の条・項・号 1 つ × 比べた期間 1 つ。取得はしない(system python3)。
区分は fix-report-5(out/fix6_compare.csv)。旧い版・新しい版は rdf/expressions.ttl.gz の版を指す。"""
import sys, re, gzip, json, collections, datetime, pandas as pd
sys.path.insert(0, 'scripts')
from rdf_config import BASE, PREFIXES
OLD, NEW = '2025-11-01', '2026-11-18'; PER = f'{OLD}_{NEW}'
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
def lit(s, lang=None, dt=None):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f'"{s}"' + (f'@{lang}' if lang else f'^^xsd:{dt}' if dt else '')
def iri(path): return f'<{BASE}{path}>'
KIND = {'文言が変わった: 番号の参照だけ': 'wording-numref', '文言が変わった: それ以外': 'wording-other', '大きく書き換わった': 'rewritten',
        '入れ替わった→移った': 'swapped-moved', '入れ替わった→移った先が一つに決まらない': 'swapped-ambiguous', '入れ替わった→移った先なし': 'swapped-nodest',
        '無くなった→移った': 'removed-moved', '無くなった→移った先が一つに決まらない': 'removed-ambiguous', '無くなった→移った先なし': 'removed-nodest', '無くなった→判定できない': 'removed-undetermined'}
c = pd.read_csv('out/fix6_compare.csv', dtype=str, keep_default_na=False)
c = c[c.新区分.isin(KIND)].copy(); assert len(c) == 3090, len(c)
# 手続 → 照合できた最も深い条・項・号(procedures.ttl.gz から)
cited = {}; cur = None
for line in gzip.open('rdf/procedures.ttl.gz', 'rt', encoding='utf-8'):
    m = re.match(r'^<' + re.escape(BASE) + r'record/r7/([^/>]+)/citation>', line)
    if m: cur = m.group(1); continue
    if line.startswith('<'): cur = None; continue
    m = re.match(r'\s+jpp:citedProvision <' + re.escape(BASE) + r'([^>]+)>', line)
    if m and cur: cited[cur] = m.group(1)
level = {}; prov_subj = set()
for line in gzip.open('rdf/provisions.ttl.gz', 'rt', encoding='utf-8'):
    m = re.match(r'^<' + re.escape(BASE) + r'([^>]+)>', line)
    if m: cur = m.group(1); prov_subj.add(cur); continue
    m = re.match(r'\s+jpp:level <[^>]+/level/(\w+)>', line)
    if m: level[cur] = m.group(1)
ver = collections.defaultdict(dict)   # 条・項・号 → {asOf: 版}
for line in gzip.open('rdf/expressions.ttl.gz', 'rt', encoding='utf-8'):
    m = re.match(r'^<' + re.escape(BASE) + r'([^>]+/version/[^>]+)> a eli:LegalExpression', line)
    if m: cur = m.group(1); prov_of = cur.split('/version/')[0]; continue
    if line.startswith('<'): cur = None; continue
    m = re.match(r'\s+jpp:asOf "([\d-]+)"', line)
    if m and cur: ver[prov_of][m.group(1)] = cur
c['prov'] = c.手続ID.map(cited); assert c.prov.notna().all(), int(c.prov.isna().sum())
LV = {'条': 'article', '項': 'paragraph', '号': 'item'}
bad_lv = c[[level.get(p) != LV[d] for p, d in zip(c.prov, c.深さ)]]
print(f'# 対象: 知らせる行 {len(c):,}。照合できた最も深い条・項・号の深さと、比べた深さが違う行: {len(bad_lv)}')
assert len(bad_lv) == 0
g = c.groupby('prov')
for k in ['新区分', 'r0_4', 'r1_4', 'cand_pos_4', '移った先の位置', '人の確認日', '当てた決まり4']:
    n = int((g[k].nunique() > 1).sum()); assert n == 0, (k, n)
print(f'  改正の記録(条・項・号): {g.ngroups:,}')
# 期間内の改正(改正履歴)
rv = pd.read_csv('out/law_revisions.csv', dtype=str, keep_default_na=False)
rv = rv[(rv.amendment_enforcement_date > OLD) & (rv.amendment_enforcement_date <= NEW)]
rev_by_law = rv.groupby('law_id')
LAWS = set(re.findall(r'<' + re.escape(BASE) + r'law/([0-9A-Za-z]+)> a eli:LegalResource', gzip.open('rdf/laws.ttl.gz', 'rt', encoding='utf-8').read()))
# 条・項・号の URI(50 と同じ並び)
def seg_art(sup, num): return ('suppl-' if sup else '') + num
def lab_art(sup, num): s = num.split('_'); return ('附則' if sup else '') + f'第{s[0]}条' + ''.join(f'の{x}' for x in s[1:])
def lab_sub(num, kind): s = num.split('_'); return f'第{s[0]}{kind}' + ''.join(f'の{x}' for x in s[1:])
newnodes = {}
def node_for(lid, pos):
    sup, art, pn, it = pos
    a = f'provision/{lid}/{seg_art(sup, art)}'
    if a not in prov_subj: newnodes.setdefault(a, ('article', f'law/{lid}', lab_art(sup, art), art))
    cur = a
    if pn is not None:
        q = f'{a}/{pn}'
        if q not in prov_subj: newnodes.setdefault(q, ('paragraph', a, lab_art(sup, art) + lab_sub(pn, '項'), pn))
        cur = q
        if it is not None:
            r = f'{q}/{it}'
            if r not in prov_subj: newnodes.setdefault(r, ('item', q, lab_art(sup, art) + lab_sub(pn, '項') + lab_sub(it, '号'), it))
            cur = r
    return cur
f = gzip.open('rdf/changes.ttl.gz', 'wt', encoding='utf-8'); ntrip = 0
for k, v in PREFIXES.items(): f.write(f'@prefix {k}: <{v}> .\n')
f.write('@prefix dcat: <http://www.w3.org/ns/dcat#> .\n\n')
def s(subj, pos):
    global ntrip
    pos = [(p, o) for p, o in pos if o is not None]; f.write(subj + ' ' + ' ;\n    '.join(f'{p} {o}' for p, o in pos) + ' .\n'); ntrip += len(pos)
# 区分のコード表・期間・作業
SCH = iri('code/change-kind')
s(SCH, [('a', 'skos:ConceptScheme'), ('skos:prefLabel', lit('改正の記録の区分', 'ja'))])
# 表示名(コードの URI と、判定の作業の中の名前は変えない)。「移った先なし」は「移った先が見つからない」と表示する
DISPLAY = {'swapped-nodest': '入れ替わった→移った先が見つからない', 'removed-nodest': '無くなった→移った先が見つからない'}
DEFN = {'swapped-nodest': '同じ番号の中身が別のものに入れ替わり、旧い文言に近い文言が別の番号に見つからなかった。決まりが無くなったとは限らない(組み替えられて、文言が大きく変わったこともある)。',
        'removed-nodest': '同じ番号の要素が無くなり、旧い文言に近い文言が別の番号に見つからなかった。決まりが無くなったとは限らない(組み替えられて、文言が大きく変わったこともある)。'}
for lab, slug in KIND.items(): s(iri(f'code/change-kind/{slug}'), [('a', 'skos:Concept'), ('skos:inScheme', SCH), ('skos:notation', lit(slug)), ('skos:prefLabel', lit(DISPLAY.get(slug, lab), 'ja')),
                                     ('skos:definition', lit(DEFN[slug], 'ja') if slug in DEFN else None)])
RVT = iri('code/reviewer-type')   # 区分を決めた(または確かめた)のは、だれか
s(RVT, [('a', 'skos:ConceptScheme'), ('skos:prefLabel', lit('区分を確かめた者の種類', 'ja'))])
for slug, lab in [('other-ai', '別の AI(作った Claude Code とは別の会話の Claude)'), ('human', '人')]:
    s(iri(f'code/reviewer-type/{slug}'), [('a', 'skos:Concept'), ('skos:inScheme', RVT), ('skos:notation', lit(slug)), ('skos:prefLabel', lit(lab, 'ja'))])
RVR = iri('code/review-result')   # 確かめた結果
s(RVR, [('a', 'skos:ConceptScheme'), ('skos:prefLabel', lit('区分を確かめた結果', 'ja'))])
for slug, lab in [('decided', '区分を決めた(機械の判定を変えた)'), ('agree', '合う'), ('disagree', '合わない'), ('unknown', '分からない')]:
    s(iri(f'code/review-result/{slug}'), [('a', 'skos:Concept'), ('skos:inScheme', RVR), ('skos:notation', lit(slug)), ('skos:prefLabel', lit(lab, 'ja'))])
# 人の抜き取りの結果(human-check-result.csv。作った人が 2026-11-20 に用紙で付けたもの)。手続ID → (判定, メモ, 選んだ理由)
import csv as _csv
HUMAN_DATE = '2026-11-20'; RES = {'合う': 'agree', '合わない': 'disagree', '分からない': 'unknown'}
HUMAN = {}
for row in _csv.reader(open('human-check-result.csv', encoding='utf-8-sig')):
    if row[0] == '番号': hd = row; continue
    HUMAN[row[2]] = (RES[row[-2]], row[-1], row[1])
used_h = set()
PERIOD = iri(f'period/{PER}')
s(PERIOD, [('a', 'dct:PeriodOfTime'), ('dcat:startDate', lit(OLD, dt='date')), ('dcat:endDate', lit(NEW, dt='date')), ('rdfs:label', lit(f'{OLD} から {NEW}', 'ja'))])
PLAN, AGENT, ACT = iri('plan/change-rules/5'), iri('agent/45_fix_rules5'), iri('activity/judge-changes-5')
s(PLAN, [('a', 'prov:Plan'), ('rdfs:label', lit('判定の決まり 第 5 版(fix-report-5.md)', 'ja')), ('owl:versionInfo', lit('5')),
         ('dct:description', lit('近さは difflib の ratio(autojunk=False)。条名・項番号・号名を除き、文の中の参照の番号は残す。'
                                 '入れ替わった: (1) r0≥0.90 なら入れ替わりにしない (2) r1≥0.90 かつ r1−r0≥0.05 なら移った。ただし最も近い候補が旧版でも同じ番号に近い文言なら移った先にしない。最も近い候補との差が 0.01 未満の候補がほかにあれば、移った先が一つに決まらない '
                                 '(3) 条の見出しが変わり見出しの近さ<0.5 なら移った先が見つからない (4) それ以外は r0<0.6 で大きく書き換わった、r0≥0.6 で文言が変わった。'
                                 '無くなった: 最も近い候補≥0.90 で、旧版でも同じ番号に近い文言なら判定できない、候補が並べば一つに決まらない、そうでなければ移った。<0.60 は移った先が見つからない、その間は判定できない。', 'ja'))])
s(AGENT, [('a', 'prov:SoftwareAgent'), ('rdfs:label', lit('scripts/45_fix_rules5.py と scripts/61_build_changes.py'))])
s(ACT, [('a', 'prov:Activity'), ('rdfs:label', lit('改正の記録の判定(2025-11-01 版と 2026-11-18 版の比べ)', 'ja')), ('prov:used', iri('source/egov-law-api-v2')),
        ('prov:qualifiedAssociation', f'[ a prov:Association ; prov:agent {AGENT} ; prov:hadPlan {PLAN} ]'), ('prov:endedAtTime', lit(NOW, dt='dateTime'))])
# 期間内の改正
revs_used = set()
cnt = collections.Counter(); nrev = collections.Counter()
for pv, gg in g:
    r = gg.iloc[0]; lid = r.law_id
    kind = KIND[r.新区分]; ch = 'change/' + pv[len('provision/'):] + f'/{PER}'
    old = ver[pv].get(OLD); new = ver[pv].get(NEW)
    if new == old: new = None   # 版が同じなら「新しい版」は置かない(数える)
    mv = None; cands = []
    if r.新区分.endswith('→移った'): mv = node_for(lid, json.loads(r.移った先の位置)[0][1])
    if r.新区分.endswith('一つに決まらない'): cands = [node_for(lid, x[1]) for x in json.loads(r.cand_pos_4)]
    revs = [] if lid not in rev_by_law.groups else list(rev_by_law.get_group(lid).law_revision_id)
    revs_used.update((lid, x) for x in revs); nrev[len(revs) > 0] += 1
    hr = r.人の確認日 != ''
    def dec(x): return lit(f'{float(x):.6f}', dt='decimal') if x not in ('', None) else None
    pos = [('a', 'jpp:ProvisionChange'), ('jpp:provision', iri(pv)), ('dct:temporal', PERIOD), ('jpp:changeKind', iri(f'code/change-kind/{kind}')),
           ('jpp:oldVersion', iri(old) if old else None), ('jpp:newVersion', iri(new) if new else None), ('jpp:movedTo', iri(mv) if mv else None)]
    pos += [('jpp:candidate', iri(x)) for x in dict.fromkeys(cands)]
    pos += [('jpp:r0', dec(r.r0_4)), ('jpp:r1', dec(r.r1_4)), ('prov:wasGeneratedBy', ACT)]
    pos += [('jpp:lawRevisionInPeriod', iri(f'law/{lid}/revision/{x}')) for x in revs]
    pos += [('jpp:affects', iri(f'procedure/{p}')) for p in sorted(gg.手続ID)]
    # 作業の列の名前は「人の確認」だが、区分を決めたのは、作った Claude Code とは別の AI(別の会話の Claude)の読み。作った人は、まだ行を読んでいない
    # 確かめの記録(jpp:Review)。1 つの改正の記録に、別の AI の記録と人の記録の両方がありうる
    reviews = []
    if hr: reviews.append((f'{ch}/review/other-ai-{r.人の確認日}', [('a', 'jpp:Review'), ('jpp:reviewerType', iri('code/reviewer-type/other-ai')), ('jpp:reviewDate', lit(r.人の確認日, dt='date')),
                                                                ('jpp:reviewResult', iri('code/review-result/decided')), ('jpp:reviewReason', lit(r.人の確認の理由, 'ja'))]))
    hs = [(p, HUMAN[p]) for p in sorted(gg.手続ID) if p in HUMAN]
    if hs:
        assert len({h for _, h in hs}) == 1 or len({h[0] for _, h in hs}) == 1, ('同じ改正の記録の行で、人の判定が違う', ch, hs)
        res, note, why = hs[0][1]; notes = sorted({h[1] for _, h in hs if h[1]}); used_h.update(p for p, _ in hs)
        reviews.append((f'{ch}/review/human-{HUMAN_DATE}', [('a', 'jpp:Review'), ('jpp:reviewerType', iri('code/reviewer-type/human')), ('jpp:reviewDate', lit(HUMAN_DATE, dt='date')),
                       ('jpp:reviewResult', iri(f'code/review-result/{res}')), ('jpp:reviewNote', lit(' / '.join(notes), 'ja') if notes else None),
                       ('jpp:reviewSampling', lit(f'人の抜き取り(種 20261119)。用紙で選んだ理由: {why}', 'ja'))]))
    pos += [('jpp:review', iri(x)) for x, _ in reviews]
    s(iri(ch), pos)
    for x, rp in reviews: s(iri(x), rp)
    cnt['review'] += len(reviews)
    cnt[('rec', r.新区分)] += 1; cnt[('rows', r.新区分)] += len(gg); cnt['old'] += bool(old); cnt['new'] += bool(new); cnt['same_ver'] += (ver[pv].get(NEW) == old and old is not None)
    cnt['human'] += hr; cnt['cands'] += len(set(cands)); cnt['moved'] += bool(mv)
# 改正の節点は、改正の記録に結んだものだけでなく、期間内に施行期日がある改正をすべて置く(このデータにある法令のもの)。
# 「法令の単位で知らせた場合」の手続の数(根拠の法令に期間内の改正がある手続)を、問いで数えられるようにするため。
assert set(rv.law_id) <= LAWS, sorted(set(rv.law_id) - LAWS)[:5]
assert revs_used <= set(zip(rv.law_id, rv.law_revision_id))
assert used_h == set(HUMAN), ('人の抜き取りの行で、改正の記録に当たらなかったもの', sorted(set(HUMAN) - used_h))
for lid, x in sorted(zip(rv.law_id, rv.law_revision_id)):
    rr = rv[(rv.law_id == lid) & (rv.law_revision_id == x)].iloc[0]
    s(iri(f'law/{lid}/revision/{x}'), [('a', 'jpp:LawRevision'), ('dct:identifier', lit(x)), ('jpp:revisionOf', iri(f'law/{lid}')),
                                         ('jpp:enforcementDate', lit(rr.amendment_enforcement_date, dt='date')), ('jpp:amendmentLawNum', lit(rr.amendment_law_num) if rr.amendment_law_num else None)])
for path, (lv, parent, lab, num) in newnodes.items():
    s(iri(path), [('a', 'eli:LegalResourceSubdivision'), ('eli:is_part_of', iri(parent)), ('eli:number', lit(num)), ('rdfs:label', lit(lab, 'ja')), ('jpp:level', iri(f'code/level/{lv}')),
                  ('rdfs:comment', lit('改正の記録の移った先・候補として足した条・項・号(2026-11-18 版の番号)', 'ja'))])
f.close()
print(f'\n# 区分ごと\n| 区分 | 改正の記録(条・項・号) | 手続の行 |\n|---|---:|---:|')
for lab in KIND: print(f'| {lab} | {cnt[("rec", lab)]:,} | {cnt[("rows", lab)]:,} |')
R = sum(cnt[("rec", l)] for l in KIND); W = sum(cnt[("rows", l)] for l in KIND)
print(f'| 計 | {R:,} | {W:,} |\n  確かめ: 手続の行 {W} = 3090 → {W == 3090}')
print(f'  旧い版あり {cnt["old"]:,} / 新しい版あり {cnt["new"]:,} / 新しい版が旧い版と同じ版(置かなかった) {cnt["same_ver"]} / 移った先 {cnt["moved"]} / 候補(重なり無し、延べ) {cnt["cands"]} / 別の AI が区分を決めた {cnt["human"]} / 確かめの記録 {cnt["review"]}(人の抜き取りの手続 {len(used_h)})')
print(f'  期間内の改正を結んだ記録 {nrev[True]:,} / 結ぶ改正が改正履歴に無い記録 {nrev[False]:,} / 記録に結んだ改正 {len(revs_used):,} / 改正の節点(期間内のすべて) {len(rv):,}・法令 {rv.law_id.nunique():,}')
print(f'  移った先・候補として足した条・項・号 {len(newnodes):,}(provisions.ttl.gz に無かったもの)')
print(f'  書いたトリプル {ntrip:,}')
