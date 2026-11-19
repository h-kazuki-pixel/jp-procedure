# 行政手続LOD RDF の 1 段目と、点検用の抜き出し

- 改正の記録と条文の本文は、まだ RDF に入れていない。
- 数字は次の出力から写した。
  - `out/41_numref_boundary.txt`
  - `out/50_build_rdf.txt`
  - `out/51_check_rdf.txt`、`out/51b_shacl.txt`
  - `out/52_text_size.txt`
  - `out/53_vocab_check.txt`
- 法令API は新たに呼んでいない。本文は保存済みのものを読んだ。
- ネットに取りに行ったのは、語彙の定義 4 件だけ(4 節)。
- RDF の読み書きと SHACL のために、作業フォルダの中に `.venv` を作り、rdflib 7.6.0 と pySHACL 0.40.2 を入れた。

## A. 点検用

### 1. 「番号の参照だけ」の数え直し

新しい条件は、変わった漢数字のすべてについて、旧・新の両側とも直後の語が「条」「項」「号」であること。語の分け方と差の取り方は、前回(`fix-report.md` 2 節)と同じにした。

| | 番号の参照だけ | それ以外 |
|---|---:|---:|
| 前(fix-report) | 437 | 1,702 |
| 後 | **284** | **1,855** |

- 「それ以外」へ移したのは 153 行(異なる要素 77)。
- 前に「数の変更の疑い」とした 21 行は、すべて「それ以外」へ移った。
- 枝番号の付け替えも「それ以外」に入る。例: 「第百四十五条の[五→十三]において」。漢数字の直後が「に」「第」などになるため。
- 第三十四条の九の四のように、参照の中に枝番号を含む挿入も「それ以外」に入る。
- 後の 284 行のうち 1 行は、漢数字の差がない行(「及び→から」や「、」の出入りだけ)。漢数字の条件に当たらないので、そのまま残した。

移した例(各要素の最初の違う箇所):

| 法令・条項号 | 違う箇所 |
|---|---|
| 一般職の職員の給与に関する法律 第22条第1項 | …三万[四千七百→五千七百]円… |
| 地方税法 第53条 | …第百四十五条の[五→十三]において準用する… |
| 電気通信番号規則 第13条第1項 | …法第五十条の[十→十一]第一号… |
| 電気通信事業法 第128条第1項 | …以下この節[→及び第百四十三条の二第一項]において… |
| 金融機能の強化のための特別措置に関する法律 第27条第2項 | …以下この章[→、第三十四条の九の四第四項及び第四十八条第二項第二号]において… |

A1 の後の改正の追跡の表(47,352 に対する比):

| 区分 | 行 | 比 |
|---|---:|---:|
| 文言が同じ | 44,196 | 93.34% |
| 文言が変わった: 番号の参照だけ | 284 | 0.60% |
| 文言が変わった: それ以外 | 1,855 | 3.92% |
| 入れ替わった→移った | 353 | 0.75% |
| 入れ替わった→消えた | 119 | 0.25% |
| 入れ替わった→判定できない | 126 | 0.27% |
| 無くなった→移った | 155 | 0.33% |
| 無くなった→消えた | 112 | 0.24% |
| 無くなった→判定できない | 86 | 0.18% |
| 比べられない | 66 | 0.14% |
| 計 | 47,352 | 100.00% |

行ごとの区分は `out/fix2_compare.csv`(「A1後」の列)にある。

### 2. 境目の抜き取り `review-boundary-06.csv`

- 対象は、同じ番号の旧・新の近さ(入れ替わりの判定に使った値)が 0.5 以上 0.7 未満の行。母数は 142 行で、0.6 未満(入れ替わった)が 42、0.6 以上が 100。
- そこから種 20261118 で 30 行を抜き取った(22 法令)。
- 区分の内訳(A1 の後): 文言が変わった: それ以外 22、入れ替わった→消えた 6、入れ替わった→判定できない 2。
- 列は `review-sample.csv` と同じ 13 列。
  - 「近さ」は同じ番号の旧・新の近さ。
  - 入れ替わった行は、移った先の近さを「備考」に書いた。
  - 文言は、照合した深さの要素の全文。番号を含み、空白・改行を除いている。

## B. RDF の 1 段目

### 3. 基点の URI

- 基点の URI は `scripts/rdf_config.py` の `BASE = 'https://w3id.org/jp-procedure/'` の 1 か所で決めている(仮)。
- 独自の語彙は `BASE + 'def#'`(接頭辞 `jpp:`)。
- 接頭辞の一覧と出典ファイルの情報も、同じファイルにまとめた。

### 4. 作ったもの

| URI | クラス | 中身 |
|---|---|---|
| `/procedure/{手続ID}` | cpsv:PublicService | dct:identifier、jpp:hasCitation(記載へ)、cv:hasLegalResource(条・項・号か法令へ) |
| `/record/r7/{手続ID}` | jpp:SurveyRecord(rdfs:subClassOf prov:Entity) | R7 の 46 列(空欄は書かない)、jpp:describes(手続へ)、出典(下記) |
| `/record/r7/{手続ID}/citation` | jpp:LegalCitation | 原文の根拠条項号(jpp:citationText)、原文の法令名、照合の結果、法令IDの決め方、使った型、照合した法令・条項号 |
| `/law/{法令ID}` | eli:LegalResource | eli:id_local、rdfs:label(e-Gov の題名)、rdfs:seeAlso(e-Gov の法令ページ)、照合に使った版 |
| `/provision/{法令ID}/{条}/{項}/{号}` | eli:LegalResourceSubdivision | eli:is_part_of(1 つ上へ。条は法令へ)、eli:number、rdfs:label、jpp:level |
| `/code/{表}/{符号}` | skos:Concept(表は skos:ConceptScheme) | 照合の結果、法令IDの決め方、使った型、所管府省庁、手続類型、条・項・号の別 |
| `/source/r7-xlsx` ほか | prov:Entity / prov:Activity | Excel ファイル(ダウンロード元 URL、シート名、SHA-256、ダウンロード日時)、e-Gov 法令API、生成の作業 |

#### 例(職業安定法 第33条の2第1項を根拠にする手続 45535)

```turtle
<https://w3id.org/jp-procedure/procedure/45535> a cpsv:PublicService ;
    dct:identifier "45535" ;
    jpp:hasCitation <https://w3id.org/jp-procedure/record/r7/45535/citation> ;
    cv:hasLegalResource <https://w3id.org/jp-procedure/provision/322AC0000000141/33_2/1> .
<https://w3id.org/jp-procedure/record/r7/45535/citation> a jpp:LegalCitation ;
    jpp:citationText "第33条の2第1項" ;
    jpp:citationLawName "職業安定法" ;
    jpp:matchResult <https://w3id.org/jp-procedure/code/match-result/paragraph> ;
    jpp:lawIdMethod <https://w3id.org/jp-procedure/code/law-id-method/a> ;
    jpp:parseRule <https://w3id.org/jp-procedure/code/parse-rule/base> ;
    jpp:citedLaw <https://w3id.org/jp-procedure/law/322AC0000000141> ;
    jpp:citedProvision <https://w3id.org/jp-procedure/provision/322AC0000000141/33_2/1> ;
    prov:wasDerivedFrom <https://w3id.org/jp-procedure/record/r7/45535> .
<https://w3id.org/jp-procedure/provision/322AC0000000141/33_2/1> a eli:LegalResourceSubdivision ;
    eli:is_part_of <https://w3id.org/jp-procedure/provision/322AC0000000141/33_2> ;
    eli:number "1" ; rdfs:label "第33条の2第1項"@ja ;
    jpp:level <https://w3id.org/jp-procedure/code/level/paragraph> .
<https://w3id.org/jp-procedure/record/r7/45535> a jpp:SurveyRecord ;
    jpp:describes <https://w3id.org/jp-procedure/procedure/45535> ;
    prov:wasDerivedFrom <https://w3id.org/jp-procedure/source/r7-xlsx> ;
    jpp:sourceRow "30561"^^xsd:integer ;
    jpp:r7-c03 "学校等の行う無料職業紹介事業の開始の届出" ; …
```

#### 照合の結果と原文の条項号

- 照合の結果は、すべての手続(76,275)が記載ノードを 1 つ持ち、そこに 1 つずつ付けた(SHACL で確かめた。6 節)。
- 区分は前回の「追加」(型を足した後)の分け方。7 つの符号の対応は次のとおり。

| 符号 | 区分 |
|---|---|
| item | 号まで |
| paragraph | 項まで |
| article | 条まで |
| no-article | 条が無い |
| unparsed | 分けられない |
| no-law-id | 法令IDが決まらない |
| no-text | 本文が取れない |

- 行数は `full-report.md` 2 節の追加の列と同じ。
- 原文の条項号は、文字のまま(改行も含む)literal で入れた。R7 で根拠条項号が空の行は 0 だった。

#### cv:hasLegalResource の行き先

| 行き先 | 行 |
|---|---:|
| 条・項・号へ(照合できた最も深い節) | 74,544 |
| 法令へ(条が無い・分けられない・本文が取れない) | 1,035 |
| 付けない(法令IDが決まらない) | 696 |

#### 条・項・号

- 節の数は、条 36,902、項 42,920、号 1,750。照合できた行の節と、その上の節だけを作った。
- URI の条の部分は、e-Gov の Num のまま(「の」は「_」)。例: `15_2`。
- **附則の条は、URI の条の部分を `suppl-{番号}` にした。** 本則と附則で同じ番号の条があるため。照合できた行のうち附則の行は 88。指示の形 `/{条}/{項}/{号}` から変えたのはこの点だけ。
- 項の指定がないまま号まで一致した 429 行は、URI の項の部分にその条のただ一つの項の番号を入れた。保存した本文で確かめてある。

#### 出典(PROV-O)

- 各記録に `prov:wasDerivedFrom <source/r7-xlsx>` と `prov:wasGeneratedBy <activity/build-rdf-1>` を付けた。
- Excel の何行目かは `jpp:sourceRow`(1 始まり、見出し 2 行を含む)に入れた。
  - 行番号は「CSV の行(0 始まり)+ 3」で、Excel の 5 か所の行と手続ID が合うことを確かめた。
  - PROV-O には行番号の性質がないので、独自の性質にした。
- Excel の実体は、ダウンロード元 URL、シート名「R7調査結果」、SHA-256、ダウンロード日時で示した。

#### コード表

- 所管府省庁と手続類型は skos:Concept にし、R7 の表記のままを prefLabel にした。
- そのほかの列(事務区分、オンライン化の実施状況など)は、今回は文字列のまま。

#### 語彙の確かめ

ダウンロードした定義ファイルは `data/vocab/` に、確かめた結果は `out/53_vocab_check.txt` にある。

| 語 | 確かめた定義 | 結果 |
|---|---|---|
| cpsv:PublicService | http://purl.org/vocab/cpsv(→ https://interoperable-europe.ec.europa.eu/sites/default/files/distribution/2013-11/cpsv_101.ttl) | あり |
| **cpsv:hasLegalResource** | 同上 | **無し** |
| cv:hasLegalResource | http://data.europa.eu/m8g/(→ https://SEMICeu.github.io/uri.semic.eu-puris/releases/m8g/m8g.ttl) | あり(owl:ObjectProperty) |
| (使い方) | CPSV-AP 3.2.0 https://semiceu.github.io/CPSV-AP/releases/3.2.0/ | has legal resource = `http://data.europa.eu/m8g/hasLegalResource`、域 cpsv:PublicService、値域 Legal Resource、0..* |
| eli:LegalResource | http://data.europa.eu/eli/ontology(→ publications.europa.eu の cellar、ELI 1.5) | あり |
| eli:LegalResourceSubdivision | 同上 | あり(eli:LegalResource の下位クラス) |
| eli:is_part_of、eli:id_local、eli:number | 同上 | あり |
| eli:title | 同上 | あり。ただし域は eli:Expression なので使わず、題名は rdfs:label にした |

- **指示と違う点:** 指示の「cpsv:hasLegalResource」は cpsv の名前空間に定義がなかった。CPSV-AP 3.2.0 の定めに従い、`cv:hasLegalResource`(http://data.europa.eu/m8g/hasLegalResource)を使った。
- cpsv_101.ttl は rdflib では構文エラーで読めなかったので、文字列で探した。
- 使っていない cv のクラス・性質を、データに入れてはいない。
- ほかに使ったのは dct、skos、prov、rdfs、owl、xsd の標準の語。どれも一般に使われている語なので、定義の取得まではしていない。

#### CPSV-AP の必須項目について

CPSV-AP 3.2.0 の性質の表(`data/vocab/cpsv-ap-3.2.0.html`)では、PublicService の必須(Mandatory)は次の 3 つ。name(dct:title)は Optional になっている。

| 性質 | 今回のデータ |
|---|---|
| identifier(dct:identifier) | 入れた |
| description(dct:description) | 無い |
| has competent authority(cv:hasCompetentAuthority) | 無い |

- 今回は指示どおり、手続名・所管府省庁などを記録(SurveyRecord)の側に置いたので、手続の側には description と has competent authority が無い。
- CPSV-AP に合わせるなら、所管府省庁を Public Organisation として作り、cv:hasCompetentAuthority でつなぐことになる。その場合、所管府省庁は skos:Concept ではなく組織として扱う。
- 表を文字列で読み取ったので、表のどの段に spatial が入るかなど、読み取りが不確かなところがある。

### 5. 条文の本文を入れた場合の大きさ(見積もり。入れていない)

- 本文は 2025-11-01 版。ルビの読みと前後の空白を除いた。
- 1 行 1 トリプル(N-Triples に近い形)で書いた場合の大きさを、実際に組み立てて数えた。ファイルには書き出していない。

| 入れ方 | トリプル | 文字 | 展開すると | gzip |
|---|---:|---:|---:|---:|
| (a) 条・項・号のすべての節に、その範囲の本文を入れる(条の本文に項・号の本文も含まれ、重なる) | 81,572 | 27,458,822 | 91,495,359 バイト | 11,186,328 バイト |
| (b) 照合できた最も深い節にだけ入れる | 55,924 | 10,646,597 | 38,220,176 バイト | 5,611,388 バイト |

今の RDF 全体は gzip で 8,608,990 バイト(7 節)。(a) を足すとその 2 倍あまり、(b) を足すと 1.65 倍ほどになる。

### 6. SHACL

形の定義は `rdf/shapes.ttl`(手続・記載・条項号・法令・件数)と `rdf/shapes-records.ttl`(記録・件数)。

| 確かめること | 形 |
|---|---|
| 手続が 76,275 件 | SHACL-SPARQL で cpsv:PublicService を数える |
| 手続ごとに照合の結果が 1 つ | 経路 `jpp:hasCitation / jpp:matchResult` が 1 つちょうど |
| 手続ごとに原文の条項号が 1 つ | 経路 `jpp:hasCitation / jpp:citationText` が 1 つちょうど |
| 記載ごとに照合の結果が 1 つ | 7 つの符号のどれか |
| 条・項・号ごとに eli:is_part_of が 1 つ | 1 つちょうど。行き先は eli:LegalResource か eli:LegalResourceSubdivision |
| 法令ごとに eli:id_local が 1 つ | 1 つちょうど |
| 記録ごとに jpp:describes と jpp:sourceRow が 1 つ | 1 つちょうど |
| 記録が 76,275 件 | SHACL-SPARQL で jpp:SurveyRecord を数える |

pySHACL 0.40.2、推論なし(`inference='none'`)。結果は次のとおり。

| 対象 | トリプル | 結果 | 違反 | 時間 |
|---|---:|---|---:|---:|
| 手続・記載・法令・条項号・コード表・出典 | 1,413,955 | 適合 | **0 件** | 167 秒 |
| 調査の記録・出典 | 1,983,762 | 適合 | **0 件** | 358 秒 |

経緯と、形の定義が違反を拾えることの確かめ:

- 1 回目は、形の定義を 1 つのファイルにまとめて、データを 2 つに分けて通した(`out/51_check_rdf_run1.txt`)。
  - それぞれに、もう一方の件数の形が「0 件」とする違反が 1 件ずつ出た。データに無いものを数えたためで、データの誤りではない。
  - そこで形の定義をデータの分け方に合わせて 2 つに分け、通し直したのが上の結果。
- わざと壊したデータでも試した。手続・記載・法令・条項号を対象に、次の 4 つの誤りを入れた。
  - 照合の結果を 1 つ消す
  - 照合の結果を 2 つにする
  - is_part_of を 1 つ消す
  - 中身のない手続を 1 件足す
- このときの違反は 11 件だった。4 つの誤りに当たる違反に加え、上と同じ理由で記録の件数の違反(0 件)が出ている。
  - 照合の結果: 記載の形と手続の経路の形の両方で出た。
  - is_part_of: 1 件出た。
  - 足した手続: 識別子と記載がないことと、手続の件数が 76,275 でないことが出た。

### 7. 出力(rdf/)

トリプル数は、各ファイルを rdflib で読み直して数えたもの。書き出し側で数えた数(計 3,397,914)と合った。

| ファイル | 中身 | トリプル | gzip | 展開すると |
|---|---|---:|---:|---:|
| `codes.ttl.gz` | コード表 6 つ | 239 | 1,744 | 13,356 |
| `vocab.ttl.gz` | 独自の語彙と R7 の 46 列の性質 | 217 | 1,801 | 10,133 |
| `prov.ttl.gz` | 出典と生成の作業 | 20 | 906 | 2,014 |
| `laws.ttl.gz` | 法令 2,981 | 17,885 | 128,694 | 1,220,719 |
| `provisions.ttl.gz` | 条・項・号 81,572 | 407,860 | 942,322 | 24,485,215 |
| `procedures.ttl.gz` | 手続と根拠条項号の記載 76,275 ずつ | 987,951 | 2,546,565 | 70,538,694 |
| `records.ttl.gz` | 調査の記録 76,275 | 1,983,742 | 4,986,958 | 101,650,322 |
| 計 | | **3,397,914** | **8,608,990** | 197,920,453 |

大きさの単位はバイト。形の定義(gzip なし)は `shapes.ttl` 2,871 バイト、`shapes-records.ttl` 1,247 バイト。

## 8. 分からないこと・決めていないこと

- 基点の URI(w3id.org)は仮。登録はしていない。
- 附則の URI(`suppl-`)と、独自の語彙(`jpp:`)の名前は私が決めた。決め直す余地がある。
- 照合の結果は前回の「追加」の分け方だけを入れた。「基本」の結果は入れていない。
- 調査の記録の列は、所管府省庁と手続類型の 2 つ以外は文字列のまま。数(総手続件数など)も文字列。
- CPSV-AP の必須項目のうち、description と has competent authority は手続の側にない(4 節)。
- 条文の本文と、改正の記録(2026-11-18 版との比べ)は、まだ入れていない。

## 9. スクリプト

| スクリプト | 内容 |
|---|---|
| `scripts/41_numref_boundary.py` | A1・A2 |
| `scripts/rdf_config.py` | 基点の URI・接頭辞・出典の設定 |
| `scripts/50_build_rdf.py` | Turtle を書く(system の python3) |
| `scripts/51_check_rdf.py` | 読み直し・数え・SHACL の 1 回目と、壊したデータでの試し(.venv) |
| `scripts/51b_shacl.py` | SHACL の本番(.venv) |
| `scripts/52_text_size.py` | 本文の大きさの見積もり |
| `scripts/53_vocab_check.py` | 語彙の確かめ(保存した定義を読むだけ。.venv) |
