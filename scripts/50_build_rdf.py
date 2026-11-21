"""RDF の 1 段目を Turtle(種類ごとに gzip)で書く。改正の記録・条文の本文はまだ入れない。本文はキャッシュから読むだけ(項の指定なしの号の項番号を確かめるため)。"""
import sys, os, gzip, json, hashlib, collections, datetime, pandas as pd
sys.path.insert(0, 'scripts')
from rdf_config import BASE, DEF, PREFIXES, SOURCE_R7
from common_load import load
import redact   # 調査の記録の自由記述から個人の連絡先を伏せる(redactions.csv)
from clause import kids
import egov
from clause import article_index
OUT = 'rdf'; os.makedirs(OUT, exist_ok=True)
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

def lit(s, lang=None, dt=None):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f'"{s}"' + (f'@{lang}' if lang else f'^^xsd:{dt}' if dt else '')
def iri(path): return f'<{BASE}{path}>'
class W:
    def __init__(self, name):
        self.name = name; self.f = gzip.open(f'{OUT}/{name}.ttl.gz', 'wt', encoding='utf-8'); self.n = 0
        for k, v in PREFIXES.items(): self.f.write(f'@prefix {k}: <{v}> .\n')
        self.f.write('\n')
    def s(self, subj, pos):
        """pos: [(述語, 目的語), ...]。目的語は既に Turtle の形。"""
        pos = [(p, o) for p, o in pos if o is not None]
        self.f.write(subj + ' ' + ' ;\n    '.join(f'{p} {o}' for p, o in pos) + ' .\n'); self.n += len(pos)
    def close(self): self.f.close(); return self.n

d = pd.read_csv('out/full_check.csv', dtype=str, keep_default_na=False)
r7 = load('r7'); assert len(r7) == len(d) == 76275 and (r7.手続ID == d.手続ID).all()
cols = list(r7.columns)
cnt = {}

# ---------- コード表(skos:Concept)
MATCH = [('item', '号まで', '号まで一致'), ('paragraph', '項まで', '項まで'), ('article', '条まで', '条まで'), ('no-article', '条が無い', '法令はあるが条が無い'),
         ('unparsed', '分けられない', '分けられない'), ('no-law-id', '法令IDが決まらない', '法令IDが決まらない'), ('no-text', '本文が取れない', '本文が取れない(404)')]
M = {src: code for code, lab, src in MATCH}
STAGE = {'a 法令番号': 'a', 'b 法令名完全一致': 'b', 'c1 表記ゆれ補正': 'c1', 'c2 現時点の題名(改題後)と一致': 'c2', '決まらない': 'none', '空欄': 'blank'}
RULES = sorted(set(d.使った型) - {''})
MIN = sorted(set(r7.所管府省庁) - {''}); TYPE = sorted(set(r7.手続類型) - {''})
def mcode(lst): return {v: f'{i+1:02d}' for i, v in enumerate(lst)}
MINC, TYPEC, RULEC = mcode(MIN), mcode(TYPE), mcode(RULES)
w = W('codes')
def scheme(sid, label, items):
    w.s(iri(f'code/{sid}'), [('a', 'skos:ConceptScheme'), ('skos:prefLabel', lit(label, 'ja'))])
    for code, lab, note in items:
        w.s(iri(f'code/{sid}/{code}'), [('a', 'skos:Concept'), ('skos:inScheme', iri(f'code/{sid}')), ('skos:notation', lit(code)), ('skos:prefLabel', lit(lab, 'ja')),
                                         ('skos:scopeNote', lit(note, 'ja') if note else None)])
scheme('match-result', '照合の結果', [(c, l, f'照合の区分(追加の分け方)での名前: {s}') for c, l, s in MATCH])
scheme('law-id-method', '法令IDの決め方', [(v, k, None) for k, v in STAGE.items()])
scheme('parse-rule', '条項号を分けるのに使った型', [('base', '基本(型を足す前の分け方で分けられた)', None)] + [(RULEC[r], r, None) for r in RULES])
scheme('ministry', '所管府省庁(R7 の表記)', [(MINC[v], v, None) for v in MIN])
scheme('procedure-type', '手続類型(R7 の表記)', [(TYPEC[v], v, None) for v in TYPE])
scheme('level', '条・項・号の別', [('article', '条', None), ('paragraph', '項', None), ('item', '号', None)])
cnt['codes'] = w.close()

# ---------- 語彙(独自)と R7 の列の性質
w = W('vocab')
w.s(f'<{DEF[:-1]}>', [('a', 'owl:Ontology'), ('rdfs:label', lit('行政手続LOD の独自の語彙', 'ja')),
    ('rdfs:comment', lit('附則の条は、制定附則(原始附則。e-Gov の本文で AmendLawNum の無い SupplProvision)だけを扱う。改正法の附則(改正附則)は照合の対象にしていない。'
                         '附則の条の URI は /provision/{法令ID}/suppl-{条}/{項}/{号}、本則は /provision/{法令ID}/{条}/{項}/{号}。条の番号の「の」は「_」。', 'ja')),
    ('rdfs:comment', lit('手続の dct:description は、調査の項目(手続類型・手続主体・手続の受け手・法令名・根拠条項号)から機械で作った文。元のデータに説明は無い。', 'ja')),
    ('rdfs:comment', lit('手続の dct:title と cv:hasCompetentAuthority は R7(2025-11-01 時点)の値。年度ごとに変わりうる値は、調査の記録(jpp:SurveyRecord)に残す。', 'ja')),
    ('rdfs:comment', lit('eli:LegalResourceSubdivision rdfs:subClassOf eli:LegalResource は、ELI の公式のオントロジー(http://data.europa.eu/eli/ontology)の定義を写したもの。SHACL の sh:class がデータの側の下位クラスの定義を見るために置く。', 'ja')),
    ('rdfs:comment', lit('府省庁の dct:spatial は日本(Geonames https://sws.geonames.org/1861060/)。CPSV-AP 3.2.0 の説明が勧める順(ATU、NUTS・LAU、NAL Place、Geonames)で選んだ。'
                         'ATU・NUTS・NAL Place には国としての日本が無かった(EU Vocabularies の SPARQL で確かめた)。LAU は確かめていない。', 'ja')),
    ('rdfs:comment', lit('https://sws.geonames.org/1861060/ に a dct:Location と書いたのは、こちらの言い方。Geonames 自身の RDF での型は gn:Feature。CPSV-AP の SHACL が dct:spatial の先に dct:Location を求めるので書き足した。', 'ja'))])
w.s(f'<{DEF[:-1]}>', [('rdfs:comment', lit('条・項・号の URI(/provision/{法令ID}/{条}/{項}/{号})は「法令の中の番号で指す位置」を表す。版をまたいで同じ番号なら同じ URI になる。'
                         '中身(本文)は版(eli:LegalExpression、URI は {条・項・号}/version/{law_revision_id})で持ち、jpp:asOf で確かめた日を付ける。'
                         '番号の位置の中身が版のあいだで変わったこと(文言の変化、入れ替わり、無くなったこと)は、改正の記録(jpp:ProvisionChange)で表す。'
                         '改正の記録の移った先・候補として足した条・項・号は 2026-11-18 版の番号で、同じ並びの URI に置く。', 'ja'))])
w.s('eli:LegalResourceSubdivision', [('rdfs:subClassOf', 'eli:LegalResource')])   # ELI の定義(data/vocab/eli.raw)
w.s('jpp:SurveyRecord', [('a', 'owl:Class'), ('rdfs:label', lit('調査の記録(R7 の 1 行)', 'ja')), ('rdfs:subClassOf', 'prov:Entity')])
w.s('jpp:LegalCitation', [('a', 'owl:Class'), ('rdfs:label', lit('根拠条項号の記載と照合の結果', 'ja'))])
w.s('jpp:ProvisionChange', [('a', 'owl:Class'), ('rdfs:label', lit('改正の記録(根拠の条・項・号 1 つ × 比べた期間 1 つ)', 'ja')), ('rdfs:subClassOf', 'prov:Entity'),
    ('rdfs:comment', lit('scripts/61_build_changes.py が作る(rdf/changes.ttl.gz)。区分は fix-report-5 の決まり。施行日は 1 つに決めず、期間内のその法令の改正を jpp:lawRevisionInPeriod で結ぶ。', 'ja'))])
w.s('jpp:Review', [('a', 'owl:Class'), ('rdfs:label', lit('改正の記録の区分を確かめた記録', 'ja')),
    ('rdfs:comment', lit('1 つの改正の記録に、別の AI(作った Claude Code とは別の会話の Claude)の記録と、人の記録の両方がありうる。どちらも消さずに残す。', 'ja'))])
w.s('jpp:LawRevision', [('a', 'owl:Class'), ('rdfs:label', lit('法令の改正(e-Gov の改正履歴の 1 版)', 'ja')),
    ('rdfs:comment', lit('比べた期間に施行期日がある改正は、改正の記録に結んだものだけでなく、このデータにある法令のものをすべて置く(scripts/61_build_changes.py)。根拠の法令に期間内の改正がある手続(法令の単位で知らせた場合の数)を、問いで数えられるようにするため。', 'ja'))])
for p, lab, kind in [('describes', '記録が説明する手続', 'Object'), ('hasCitation', '根拠条項号の記載', 'Object'), ('citationText', '原文の根拠条項号(文字のまま)', 'Datatype'),
                     ('citationLawName', '原文の法令名(文字のまま)', 'Datatype'), ('matchResult', '照合の結果', 'Object'), ('lawIdMethod', '法令IDの決め方', 'Object'),
                     ('parseRule', '条項号を分けるのに使った型', 'Object'), ('citedLaw', '照合した法令', 'Object'), ('citedProvision', '照合できた最も深い条・項・号', 'Object'),
                     ('sourceRow', 'Excel の行番号(1 始まり、見出し 2 行を含む)', 'Datatype'), ('sourceSheet', 'Excel のシート名', 'Datatype'), ('sha256', 'ファイルの SHA-256', 'Datatype'),
                     ('level', '条・項・号の別', 'Object'), ('text', '本文(e-Gov の本文から。ルビの読みは除く)', 'Datatype'), ('asOf', 'この版が施行されていた時点として確かめた日', 'Datatype'), ('lawRevision', 'e-Gov の版の ID(law_revision_id)', 'Datatype'), ('checkedRevision', '照合に使った版(law_revision_id、asof=2025-11-01)', 'Datatype'),
                     ('provision', '改正の記録が見た根拠の条・項・号', 'Object'), ('changeKind', '改正の記録の区分', 'Object'), ('oldVersion', '比べた旧い版', 'Object'), ('newVersion', '比べた新しい版(あれば)', 'Object'),
                     ('movedTo', '移った先の条・項・号', 'Object'), ('candidate', '移った先の候補(一つに決まらないとき、すべて)', 'Object'),
                     ('r0', '同じ番号の旧・新の近さ(条名・項番号・号名を除く)', 'Datatype'), ('r1', '別の番号で最も近いものの近さ(同じ測り方)', 'Datatype'),
                     ('affects', 'この改正の記録の条・項・号を根拠にする手続', 'Object'), ('lawRevisionInPeriod', '比べた期間に施行されたその法令の改正(改正履歴にあるもの)', 'Object'),
                     ('revisionOf', '改正された法令', 'Object'), ('enforcementDate', '改正の施行期日(改正履歴の amendment_enforcement_date)', 'Datatype'), ('amendmentLawNum', '改正法令の番号', 'Datatype'),
                     ('review', '改正の記録の区分を確かめた記録(jpp:Review)', 'Object'), ('reviewerType', '確かめた者の種類(コード表 code/reviewer-type: 別の AI・人)', 'Object'), ('reviewDate', '確かめた日', 'Datatype'), ('reviewResult', '確かめた結果(コード表 code/review-result: 区分を決めた・合う・合わない・分からない)', 'Object'), ('reviewReason', '区分を決めたときの理由', 'Datatype'), ('reviewNote', '確かめたときのメモ', 'Datatype'), ('reviewSampling', 'どの抜き取りで確かめたか', 'Datatype')]:
    w.s(f'jpp:{p}', [('a', f'owl:{kind}Property'), ('rdfs:label', lit(lab, 'ja'))])
COLP = {c: f'jpp:r7-c{i+1:02d}' for i, c in enumerate(cols)}
for i, c in enumerate(cols):
    obj = c in ('所管府省庁', '手続類型')
    w.s(COLP[c], [('a', 'owl:ObjectProperty' if obj else 'owl:DatatypeProperty'), ('rdfs:label', lit(c, 'ja')), ('rdfs:comment', lit(f'R7 調査結果の {i+1} 列目', 'ja')), ('rdfs:domain', 'jpp:SurveyRecord')])
w.s('jpp:lawRevision', [('rdfs:comment', lit('値は e-Gov の法令履歴ID で、{法令ID}_{YYYYMMDD}_{改正法令の法令ID} の形。YYYYMMDD は施行期日で、eli:version_date にも同じ日付を入れた。改正法令の部分が 000000000000000 の版(このデータで 1,360、scripts/66_check_versions.py)は、e-Gov の説明では初めの版か基準日の版で、その日付が施行期日か基準日かを、このデータでは見分けていない。', 'ja'))])
w.s('jpp:SurveyRecord', [('rdfs:comment', lit('元のデータ(デジタル庁の調査結果)から変えた点: 自由記述の列にあった個人の連絡先(個人の氏名・個人あての電話番号・メールアドレス)は「' + redact.MARK + '」に置き換えた。部署の名前や代表の窓口は残した。伏せた所の一覧(手続ID・列・位置。中身は書かない)は data/redactions.csv。人名は機械で拾いきれず残りうるので、見つけたら Issue で知らせてほしい。', 'ja'))])
# 毎週の追跡(scripts/70_weekly_track.py)が書くもの(第 2 版: 公開しているデータの文言と今の e-Gov を比べる)
for p, lab, kind in [('foundRevision', '見つけた改正(毎週の追跡。新しい文言の版の改正。法令番号・公布日・施行期日は e-Gov の値)', 'Object'),
                     ('foundOn', '改正の記録を見つけた日(毎週の追跡を流した日)', 'Datatype'),
                     ('enforcedBeforePeriod', '見つけた改正の施行期日が、比べた期間の始め以前(e-Gov が施行日より遅れて本文を載せた改正)', 'Datatype'),
                     ('promulgationDate', '改正法令の公布日(e-Gov の amendment_promulgate_date)', 'Datatype')]:
    w.s(f'jpp:{p}', [('a', f'owl:{kind}Property'), ('rdfs:label', lit(lab, 'ja'))])
w.s('jpp:enforcedBeforePeriod', [('rdfs:range', 'xsd:boolean'), ('rdfs:comment', lit('値は true だけを書く(施行期日が期間の中にあるときは書かない)。このときも改正の記録は見つけた週の期間に置き、施行期日が期間の外なので jpp:lawRevisionInPeriod には結ばない。', 'ja'))])
w.s('jpp:ProvisionChange', [('rdfs:comment', lit('毎週の追跡(scripts/70_weekly_track.py、data/rdf/weekly/)の記録は、公開しているデータの文言(jpp:oldVersion は公開しているデータの版を指す)と、その日の e-Gov の本文(jpp:newVersion)の違い。'
                                                  'e-Gov は施行日より遅れて本文を載せることがあるので、見つけた改正(jpp:foundRevision)の施行期日が期間の始め以前のことがある(jpp:enforcedBeforePeriod true)。'
                                                  'e-Gov が版の ID を変えずに本文を直したもの(版を変えない直し)は改正の記録にせず、data/tracking/egov_corrections.csv に残す。公開しているデータの文言は直さない。', 'ja'))])
# 足した日(dct:issued)。語彙は足すだけにする(今ある語の意味を変えない・消さない)
for t in ['jpp:foundRevision', 'jpp:foundOn', 'jpp:enforcedBeforePeriod', 'jpp:promulgationDate']:
    w.s(t, [('dct:issued', lit('2026-11-20', dt='date'))])
w.s('jpp:firstFoundOn', [('a', 'owl:DatatypeProperty'), ('rdfs:label', lit('改正を初めて見つけた日(毎週の追跡がその改正を初めてこのデータに足した日)', 'ja')),
    ('rdfs:comment', lit('改正(jpp:LawRevision)に付ける。初めのデータにある改正には付けない。この日が比べた期間の終わりより後の改正は、施行期日がその期間にあっても、その期間の「期間内の改正」に数えない(queries/q7_law_level_by_period.rq)。', 'ja')),
    ('rdfs:range', 'xsd:date'), ('dct:issued', lit('2026-11-21', dt='date'))])
w.s('jpp:recheckReason', [('a', 'owl:ObjectProperty'), ('rdfs:label', lit('あとで比べた理由(コード表 code/recheck-reason)', 'ja')),
    ('rdfs:comment', lit('初めのデータ(2025-11-01〜2026-11-18 の比べ)に新しい版が無かった条・項・号を、毎週の追跡があとで比べて改正の記録にしたときに付ける。', 'ja')),
    ('dct:issued', lit('2026-11-21', dt='date'))])
w.s(iri('code/recheck-reason'), [('a', 'skos:ConceptScheme'), ('skos:prefLabel', lit('あとで比べた理由', 'ja')), ('dct:issued', lit('2026-11-21', dt='date'))])
for k, lab, d in [('position-undetermined', '初めの比べで位置を決められなかった', '初めの比べで、2026-11-18 の版は取れたが、その条・項・号の位置(項の指定の無い号など)を決められなかった。'),
                  ('version-missing', '初めに版を取れなかった', '初めの比べで、その法令の 2026-11-18 の版を取れなかった(e-Gov が 404 を返した・取っていない)。')]:
    w.s(iri(f'code/recheck-reason/{k}'), [('a', 'skos:Concept'), ('skos:inScheme', iri('code/recheck-reason')), ('skos:notation', lit(k)), ('skos:prefLabel', lit(lab, 'ja')),
        ('skos:definition', lit(d, 'ja')), ('dct:issued', lit('2026-11-21', dt='date'))])
# 根拠の法令の廃止・失効(2026-11-21 に足した。足すだけ)
I = ('dct:issued', lit('2026-11-21', dt='date'))
w.s('jpp:LawStatusChange', [('a', 'owl:Class'), ('rdfs:label', lit('根拠の法令の廃止・失効の記録(法令 1 つ × 比べた期間 1 つ)', 'ja')), ('rdfs:subClassOf', 'prov:Entity'),
    ('rdfs:comment', lit('比べた期間の中で廃止・失効した根拠の法令の記録。区分は code/change-kind/law-repealed。その法令を根拠に挙げる(jpp:citedLaw)すべての手続を jpp:affects で結ぶ。条文の文言の比べ(jpp:ProvisionChange)とは別に数える。状態と日付は e-Gov 法令API v2 の法令一覧の revision_info(repeal_status・repeal_date)で、今の版の状態(current_revision_status)が Repeal のものだけ(scripts/law_status.py)。', 'ja')), I])
w.s('jpp:LawStatus', [('a', 'owl:Class'), ('rdfs:label', lit('法令の廃止・失効の状態(e-Gov の記録)', 'ja')),
    ('rdfs:comment', lit('比べた期間の始め以前に廃止・失効していた法令は、変化に数えず、この状態だけを持たせる。経過措置で効力が残る場合がある。', 'ja')), I])
for p, lab, kind in [('law', '廃止・失効した根拠の法令', 'Object'), ('statusOf', 'この状態の法令', 'Object'),
                     ('repealStatus', '廃止等の状態(コード表 code/repeal-status。e-Gov の repeal_status)', 'Object'), ('repealDate', '廃止等の日(e-Gov の repeal_date)', 'Datatype'),
                     ('checkedOn', 'e-Gov で状態を確かめた日', 'Datatype')]:
    w.s(f'jpp:{p}', [('a', f'owl:{kind}Property'), ('rdfs:label', lit(lab, 'ja')), I])
w.s(iri('code/change-kind/law-repealed'), [('a', 'skos:Concept'), ('skos:inScheme', iri('code/change-kind')), ('skos:notation', lit('law-repealed')),
    ('skos:prefLabel', lit('根拠の法令が廃止・失効した', 'ja')), ('skos:definition', lit('根拠の法令が、比べた期間の中で廃止・失効した(e-Gov の記録)。jpp:LawStatusChange に使う。', 'ja')), I])
w.s(iri('code/repeal-status'), [('a', 'skos:ConceptScheme'), ('skos:prefLabel', lit('廃止等の状態(e-Gov の repeal_status)', 'ja')), I])
for k, n, lab in [('repeal', 'Repeal', '廃止'), ('expire', 'Expire', '失効'), ('loss-of-effectiveness', 'LossOfEffectiveness', '効力を失った'), ('suspend', 'Suspend', '停止')]:
    w.s(iri(f'code/repeal-status/{k}'), [('a', 'skos:Concept'), ('skos:inScheme', iri('code/repeal-status')), ('skos:notation', lit(n)), ('skos:prefLabel', lit(lab, 'ja')), I])
w.s(iri('code/recheck-reason/law-status-not-checked'), [('a', 'skos:Concept'), ('skos:inScheme', iri('code/recheck-reason')), ('skos:notation', lit('law-status-not-checked')),
    ('skos:prefLabel', lit('初めの比べは法令の廃止を見ていなかった', 'ja')), ('skos:definition', lit('初めの比べ(2025-11-01〜2026-11-18)は条文の文言だけを見ていて、根拠の法令の廃止・失効を見ていなかった。2026-11-21 に別のファイルで補った。', 'ja')), I])
# 分類しない法令(2026-11-21 に足した。足すだけ)
w.s('jpp:LawStatusUnclear', [('a', 'owl:Class'), ('rdfs:label', lit('分類しない法令(e-Gov に廃止・失効の記録があるが、状態を確認できない)', 'ja')),
    ('rdfs:comment', lit('e-Gov 法令API v2 の法令一覧に廃止・失効の記録(repeal_status)があるが、今の版の状態(current_revision_status)が Repeal でない(施行前 UnEnforced と返るなど)か、日付が無い法令。廃止・失効したとも、していないとも分類しない。e-Gov が返した値だけを持たせる(scripts/law_status.py)。', 'ja')), I])
w.s('jpp:currentRevisionStatus', [('a', 'owl:DatatypeProperty'), ('rdfs:label', lit('今の版の状態(e-Gov の current_revision_status をそのまま)', 'ja')), ('rdfs:range', 'xsd:string'), I])
cnt['vocab'] = w.close()

# ---------- 出典(PROV-O)
sha = hashlib.sha256(open(SOURCE_R7['file'], 'rb').read()).hexdigest()
w = W('prov')
SRC, ACT, DS = iri('source/r7-xlsx'), iri(f'activity/build-rdf-1'), iri('dataset/r7')
w.s(SRC, [('a', 'prov:Entity'), ('dct:title', lit(os.path.basename(SOURCE_R7['file']))), ('rdfs:seeAlso', f'<{SOURCE_R7["url"]}>'), ('dct:source', f'<{SOURCE_R7["page"]}>'),
          ('jpp:sourceSheet', lit(SOURCE_R7['sheet'])), ('jpp:sha256', lit(sha)), ('dct:date', lit(open('data/raw/downloaded_at.txt').read().strip(), dt='dateTime')),
          ('rdfs:comment', lit('dct:date はダウンロードした日時', 'ja'))])
EGOV = iri('source/egov-law-api-v2')
w.s(EGOV, [('a', 'prov:Entity'), ('dct:title', lit('e-Gov 法令API v2(asof=2025-11-01 で取得した法令一覧と本文)', 'ja')), ('rdfs:seeAlso', '<https://laws.e-gov.go.jp/api/2/>')])
w.s(ACT, [('a', 'prov:Activity'), ('rdfs:label', lit('RDF の 1 段目の生成(scripts/50_build_rdf.py)', 'ja')), ('prov:used', SRC), ('prov:used', EGOV),
          ('prov:endedAtTime', lit(NOW, dt='dateTime'))])
w.s(DS, [('a', 'prov:Entity'), ('rdfs:label', lit('行政手続 R7 の RDF(1 段目)', 'ja')), ('prov:wasGeneratedBy', ACT), ('prov:wasDerivedFrom', SRC)])
cnt['prov'] = w.close()

# ---------- 所管府省庁(cv:PublicOrganisation)
JAPAN = '<https://sws.geonames.org/1861060/>'   # data/vocab/spatial/geonames_1861060.rdf で確かめた
w = W('organisations')
for v in MIN:
    w.s(iri(f'organisation/{MINC[v]}'), [('a', 'cv:PublicOrganisation'), ('skos:prefLabel', lit(v, 'ja')), ('dct:identifier', lit(MINC[v])),
                                         ('skos:exactMatch', iri(f'code/ministry/{MINC[v]}')), ('dct:spatial', JAPAN), ('rdfs:comment', lit('R7 の所管府省庁の表記から作った', 'ja'))])
w.s(JAPAN, [('a', 'dct:Location'), ('rdfs:label', lit('日本', 'ja')), ('rdfs:label', lit('Japan', 'en'))])   # Geonames の地名(feature code A.PCLI、国)
cnt['organisations'] = w.close()

# ---------- 法令
lawt = d[d.law_id != ''].drop_duplicates('law_id').set_index('law_id')
w = W('laws')
for lid, r in lawt.iterrows():
    w.s(iri(f'law/{lid}'), [('a', 'eli:LegalResource'), ('eli:id_local', lit(lid)), ('rdfs:label', lit(r.egov_law_title, 'ja')),
                            ('rdfs:seeAlso', f'<https://laws.e-gov.go.jp/law/{lid}>'), ('jpp:checkedRevision', lit(r.law_revision_id) if r.law_revision_id else None),
                            ('prov:wasDerivedFrom', EGOV)])
cnt['laws'] = w.close(); cnt['laws_n'] = len(lawt)

# ---------- 条・項・号
def seg_art(sup, num): return ('suppl-' if sup else '') + num
def lab_art(sup, num): s = num.split('_'); return ('附則' if sup else '') + f'第{s[0]}条' + ''.join(f'の{x}' for x in s[1:])
def lab_sub(num, kind): s = num.split('_'); return f'第{s[0]}{kind}' + ''.join(f'の{x}' for x in s[1:])
OKR = {'号まで一致': 3, '項まで': 2, '条まで': 1}
need_para = collections.defaultdict(list)   # 項の指定なしで号まで一致した行: 単一の項の番号を本文で確かめる
P = {}
for i, r in d[d.結果_追加.isin(OKR)].iterrows():
    p = json.loads(r.分解_追加)
    if OKR[r.結果_追加] == 3 and p['項'] is None: need_para[r.law_id].append(i)
    P[i] = p
para_of = {}
for lid, idxs in need_para.items():
    b = egov.get(f'/law_data/{lid}', {'asof': '2025-11-01', 'response_format': 'json', 'json_format': 'full'}, offline=True)
    lb = [c for c in b['law_full_text']['children'] if isinstance(c, dict) and c['tag'] == 'LawBody'][0]; idx = article_index(lb)
    for i in idxs:
        paras = kids(idx[(P[i]['附則'], P[i]['条'])], 'Paragraph'); assert len(paras) == 1; para_of[i] = paras[0]['attr'].get('Num')
nodes = {}   # path -> (level, parent_path or law, label, number)
deep = {}
for i, p in P.items():
    lid = d.law_id[i]; lv = OKR[d.結果_追加[i]]
    a = f'provision/{lid}/{seg_art(p["附則"], p["条"])}'
    nodes.setdefault(a, ('article', f'law/{lid}', lab_art(p['附則'], p['条']), p['条'])); cur = a
    if lv >= 2:
        pn = p['項'] or para_of[i]; q = f'{a}/{pn}'
        nodes.setdefault(q, ('paragraph', a, nodes[a][2] + lab_sub(pn, '項'), pn)); cur = q
        if lv == 3:
            it = f'{q}/{p["号"]}'; nodes.setdefault(it, ('item', q, nodes[q][2] + lab_sub(p['号'], '号'), p['号'])); cur = it
    deep[i] = cur
w = W('provisions')
for path, (lv, parent, lab, num) in nodes.items():
    w.s(iri(path), [('a', 'eli:LegalResourceSubdivision'), ('eli:is_part_of', iri(parent)), ('eli:number', lit(num)), ('rdfs:label', lit(lab, 'ja')),
                    ('jpp:level', iri(f'code/level/{lv}'))])
cnt['provisions'] = w.close(); cnt['provisions_n'] = collections.Counter(v[0] for v in nodes.values())

# ---------- 説明の文(型の文)
import re
def nocode(v): return re.sub(r'^[0-9]+(-[0-9]+)?\s+', '', v.strip())
def flat(v): return re.sub(r'\s+', ' ', v).strip()
FORMS = collections.Counter()
MARK = '(調査の項目から機械で作った説明)'
def describe(r):
    who, to, kind = nocode(r.手続主体), nocode(r.手続の受け手), nocode(r.手続類型)
    head = f'{who}が{to}に対して行う' if who and to else f'{who}が行う' if who else f'{to}に対して行う' if to else ''
    s1 = f'{head}「{kind}」の手続。' if kind else f'{head}手続。'
    law, art = flat(r.法令名), flat(r.根拠条項号)
    s2 = f'根拠は{law} {art}。' if law and art else f'根拠は{law}。' if law else f'根拠の条項は{art}。' if art else ''
    form = ('主体' if who else '') + ('受け手' if to else '') + ('類型' if kind else '') + '/' + ('法令名' if law else '') + ('条項' if art else '')
    return s1 + s2 + MARK, form

# ---------- 手続と根拠条項号の記載
w = W('procedures')
for i, r in d.iterrows():
    pid = r.手続ID; P_ = iri(f'procedure/{pid}'); C = iri(f'record/r7/{pid}/citation')
    target = iri(deep[i]) if i in deep else (iri(f'law/{r.law_id}') if r.law_id else None)
    desc, form = describe(r7.loc[i]); FORMS[form] += 1
    w.s(P_, [('a', 'cpsv:PublicService'), ('dct:identifier', lit(pid)), ('dct:title', lit(r7.手続名[i], 'ja')),
             ('cv:hasCompetentAuthority', iri(f'organisation/{MINC[r7.所管府省庁[i]]}') if r7.所管府省庁[i] else None),
             ('dct:description', lit(desc, 'ja')), ('jpp:hasCitation', C), ('cv:hasLegalResource', target)])
    w.s(C, [('a', 'jpp:LegalCitation'), ('jpp:citationText', lit(r.根拠条項号)), ('jpp:citationLawName', lit(r.法令名)),
            ('jpp:matchResult', iri(f'code/match-result/{M[r.結果_追加]}')), ('jpp:lawIdMethod', iri(f'code/law-id-method/{STAGE[r.段]}')),
            ('jpp:parseRule', iri(f'code/parse-rule/{RULEC[r.使った型]}') if r.使った型 else (iri('code/parse-rule/base') if r.分解_追加 else None)),
            ('jpp:citedLaw', iri(f'law/{r.law_id}') if r.law_id else None), ('jpp:citedProvision', iri(deep[i]) if i in deep else None),
            ('prov:wasDerivedFrom', iri(f'record/r7/{pid}'))])
cnt['procedures'] = w.close(); cnt['説明の文の形(どの項目があったか)'] = dict(FORMS.most_common())
cnt['説明の文の例'] = [describe(r7.loc[k])[0] for k in (0, 30558)]
cnt['hasLegalResource'] = {'条・項・号へ': len(deep), '法令へ(条・項・号が決まらない行)': int(((d.law_id != '') & ~d.index.isin(list(deep))).sum()), '無し(法令IDが決まらない)': int((d.law_id == '').sum())}

# ---------- 調査の記録(R7 の項目)
w = W('records')
for i, r in r7.iterrows():
    pos = [('a', 'jpp:SurveyRecord'), ('jpp:describes', iri(f'procedure/{r.手続ID}')), ('prov:wasDerivedFrom', SRC), ('prov:wasGeneratedBy', ACT),
           ('jpp:sourceRow', lit(i + 1 + SOURCE_R7['header_rows'], dt='integer'))]
    for c in cols:
        v = r[c]
        if v.strip() == '': continue
        if c == '所管府省庁': pos.append((COLP[c], iri(f'code/ministry/{MINC[v]}')))
        elif c == '手続類型': pos.append((COLP[c], iri(f'code/procedure-type/{TYPEC[v]}')))
        else: pos.append((COLP[c], lit(redact.apply(r.手続ID, COLP[c][len('jpp:'):], v))))
    w.s(iri(f'record/r7/{r.手続ID}'), pos)
cnt['records'] = w.close()
assert not redact.unused(), ('伏せる所の一覧に、当たらなかったものがある', redact.unused())
cnt['redacted_cells_n'] = len(redact.used)
print(json.dumps(cnt, ensure_ascii=False, default=dict, indent=1))
print('書いたトリプル(書き出し側で数えた)計', sum(v for k, v in cnt.items() if isinstance(v, int) and not k.endswith('_n')))
