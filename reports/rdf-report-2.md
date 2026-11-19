# 行政手続LOD RDF の直し(2 回目)

- 数字は次の出力から写した。
  - `out/50_build_rdf.txt`、`out/54_build_expressions.txt`
  - `out/55_check_rdf2_stopped.txt`(止めた点検。前半の読み直しは終わっていた)
  - `out/56_split_full.txt`、`out/57_count_checks.txt`
  - `out/59_shacl_test.txt`、`out/59_shacl_testbad.txt`、`out/59_shacl_full.txt`、`out/59c_subclass_try.txt`
- 法令API は新たに呼んでいない。本文は保存済みのものを読んだ。
- ネットに取りに行ったのは、CPSV-AP 3.2.0 の公式 SHACL 1 件と、言語の URI の確かめ 1 件だけ(`data/vocab/fetched.txt`、`data/vocab/language_JPN_check.txt`)。

## 1. 手続に名前と所管を置いた

`cpsv:PublicService` に次の 2 つを足した。

| 性質 | 値 |
|---|---|
| `dct:title` | R7 の手続名(`@ja`) |
| `cv:hasCompetentAuthority` | 所管府省庁の組織 `/organisation/{府省庁の符号}` |

- 組織は `cv:PublicOrganisation` として 25 作った(`rdf/organisations.ttl.gz`、125 トリプル)。
  - それぞれに `skos:prefLabel`(`@ja`)と `dct:identifier` を付けた。
  - コード表の府省庁の符号には、`skos:exactMatch` でつないだ。
- 年ごとに変わりうる値(総手続件数、オンライン化の状況など)は、前のとおり調査の記録(`jpp:SurveyRecord`)の側に残した。
- 名前と所管は R7 の値。どの年の値かは、語彙(`rdf/vocab.ttl.gz`)の `rdfs:comment` に書いた。

## 2. 説明(dct:description)

手続ごとに 1 つ、調査の項目から機械で文を作った。

**ひな形:**

```
主体   = 手続主体     から先頭の符号(「5 」「4-3 」など)を外したもの
受け手 = 手続の受け手 から同じく符号を外したもの
類型   = 手続類型     から同じく符号を外したもの

1 文目 = 「{主体}が{受け手}に対して行う「{類型}」の手続。」
         主体が無ければ「{受け手}に対して行う…」、受け手が無ければ「{主体}が行う…」、類型が無ければ「…行う手続。」
2 文目 = 「根拠は{法令名} {根拠条項号}。」
         法令名が無ければ「根拠の条項は{根拠条項号}。」、条項号が無ければ「根拠は{法令名}。」、両方無ければ書かない
         空白・改行は 1 つの空白にまとめる
最後   = 「(調査の項目から機械で作った説明)」
```

どの項目があったかで分けた、文の形ごとの手続の数:

| あった項目 | 手続 |
|---|---:|
| 主体・受け手・類型 / 法令名・条項号 | 67,959 |
| 主体・類型 / 法令名・条項号 | 8,145 |
| 主体・受け手・類型 / 条項号 | 159 |
| 主体・類型 / 条項号 | 11 |
| (なし) / 法令名・条項号 | 1 |
| 計 | 76,275 |

例:

- 「国民等が国に対して行う「申請等」の手続。根拠は国家公務員法 第106条の24。(調査の項目から機械で作った説明)」
- 「民間事業者等が国に対して行う「申請等」の手続。根拠は職業安定法 第33条の2第1項。(調査の項目から機械で作った説明)」

- 元のデータに説明文は無いことも、語彙の `rdfs:comment` に書いた。

## 3. 附則の扱いを語彙に書いた

語彙(`<https://w3id.org/jp-procedure/def>`、`owl:Ontology`)の `rdfs:comment` に、次のことを書いた。

> 附則の条は、制定附則(原始附則。e-Gov の本文で AmendLawNum の無い SupplProvision)だけを扱う。改正法の附則(改正附則)は照合の対象にしていない。附則の条の URI は /provision/{法令ID}/suppl-{条}/{項}/{号}、本則は /provision/{法令ID}/{条}/{項}/{号}。条の番号の「の」は「_」。

## 4. 条・項・号の本文の版(eli:LegalExpression)

照合できた最も深い条・項・号(55,924)のそれぞれに、2025-11-01 の版と 2026-11-18 の版の本文を足した(`rdf/expressions.ttl.gz`)。保存済みの本文から作り、取り直してはいない。

- URI は `{条・項・号}/version/{law_revision_id}`。
- 1 つの版に付けたもの:
  - `a eli:LegalExpression`
  - `eli:realizes`(条・項・号へ)。逆向きの `eli:is_realized_by` も条・項・号の側に付けた。
  - `eli:version_date`(`xsd:date`)。改正履歴(`out/law_revisions.csv`)の、その版の施行期日。90,970 版すべてで、改正履歴から取れた。
  - `jpp:lawRevision`(e-Gov の版の ID)
  - `eli:language` `<http://publications.europa.eu/resource/authority/language/JPN>`(取りに行って 200 を確かめた)
  - `jpp:text`(本文、`@ja`)
    - 要素の文字をつないだもので、ルビの読みは除いた。
    - ELI には本文そのものを入れる性質が無いので、独自の性質にした。
  - `jpp:asOf`(その版を確かめた日。2025-11-01 と 2026-11-18 のどちらか、または両方)
- 2 つの日で版が同じなら、版は 1 つにして `jpp:asOf` を 2 つ付けた。
- 版の数は **90,970**。足したトリプルは 748,282。

2026-11-18 版の取り方(条・項・号の数):

| 場合 | 条・項・号 |
|---|---:|
| 取得した 2026-11-18 版、版が 2025-11-01 と違う | 35,046 |
| 2025-11-02〜2026-11-18 に施行された改正が無く、施行中の版が 2025-11-01 版と同じ | 18,713 |
| 取得した 2026-11-18 版、版が同じ | 1,809 |
| 2026-11-18 版にその条・項・号が無い | 279 |
| 2026-11-18 版が 404 | 57 |
| 2026-11-18 版を取っておらず、改正履歴に施行中(CurrentEnforced)の版が無い | 20 |
| 計 | 55,924 |

- 下の 3 つ(計 356)には、2026-11-18 の版を付けていない。
  - 「改正履歴に施行中の版が無い」20 は、ほとんどが廃止された法令。

## 5. 自作の SHACL を分けて通した

### 5.1 前回の実行を止めた

- 全部のデータ(約 240 万トリプル)を 1 つのグラフに読んで通そうとして、2 時間 17 分たっても終わらなかった。
- そのとき Python は約 5 GB 使っていて、そのうち 4.2 GB が圧縮されていた。スワップは 15.4 GB のうち 13.9 GB が使われていた。この機械のメモリは 8 GB。
- 止めた時点の出力は `out/55_check_rdf2_stopped.txt`。各ファイルの読み直し(7 節の表)までは終わっていた。

### 5.2 形の定義を 2 つに分けた

**1 件の中で閉じる形**(`rdf/shapes.ttl`、159 トリプル、4,339 バイト):

| 形 | 確かめること |
|---|---|
| ProcedureShape(手続) | dct:identifier、dct:title、dct:description、cv:hasCompetentAuthority(組織)、照合の結果、原文の条項号が 1 つずつ。cv:hasLegalResource は 1 つまで |
| CitationShape(記載) | 照合の結果が 7 つの符号のどれか 1 つ、原文の条項号と法令ID の決め方が 1 つ |
| SubdivisionShape(条・項・号) | eli:is_part_of が 1 つで、先が法令か条・項・号。jpp:level が 1 つ |
| LawShape(法令) | eli:id_local が 1 つ |
| ExpressionShape(本文の版) | realizes、version_date、jpp:text、lawRevision が 1 つずつ。asOf が 1〜2 |
| CitedProvisionShape(照合できた最も深い条・項・号) | 版が 1〜2 あり、2025-11-01 の版がちょうど 1 つ |
| RecordShape(記録) | jpp:describes、jpp:sourceRow が 1 つずつ、prov:wasDerivedFrom がある |

- 前の `rdf/shapes-records.ttl` は RecordShape を `shapes.ttl` に移したので、外した。
- 分ける前の版は `out/shapes_v2.ttl.txt` と `out/shapes-records_v1.ttl.txt` に残した。

**全体の数を見る形**は SHACL から外し、数えるスクリプト `scripts/57_count_checks.py` で確かめた。30 項目すべて合った。

| 確かめたこと | 数 |
|---|---:|
| 切り分けたファイルのトリプルの和 = 元のファイルを丸ごと読んだ数(8 ファイル) | すべて一致 |
| cpsv:PublicService | 76,275 |
| dct:identifier の重なりの無い数 | 76,275 |
| jpp:LegalCitation、jpp:hasCitation(重なり無し) | 76,275 / 76,275 |
| 照合の結果の数の合計 = 手続の数 | 76,275 |
| jpp:SurveyRecord | 76,275 |
| 記録が指す手続の集合 = 手続の集合 | 一致 |
| cv:PublicOrganisation、所管が組織の中にある | 25、すべてある |
| 照合した法令が法令の中にある、is_part_of の先がある | すべてある |
| cv:hasLegalResource: 条・項・号へ / 法令へ / 無し | 74,544 / 1,035 / 696 |
| 照合できた最も深い条・項・号 | 55,924 |
| eli:LegalExpression | 90,970 |
| 版がある条・項・号 = 照合できた最も深い条・項・号 | 一致(55,924) |
| realizes と is_realized_by が逆向きで一致 | 一致 |
| asOf 2025-11-01 / 2026-11-18 | 55,924 / 55,568(= 55,924 − 279 − 57 − 20) |

- 照合の結果の内訳:

  | 結果 | 手続 |
  |---|---:|
  | paragraph | 54,444 |
  | article | 17,718 |
  | item | 2,382 |
  | no-law-id | 696 |
  | no-article | 568 |
  | unparsed | 466 |
  | no-text | 1 |

- 1 回目は 1 項目が合わなかった。cv:hasLegalResource の先を条・項・号だけで確かめていたためで、これは確かめの書き方の誤り。
  - 手続のうち 1,035 は、設計どおり法令そのものを指している(条・項・号が決まらない行)。
  - 先を「条・項・号か法令」に直し、その 3 つの数(74,544 / 1,035 / 696)も確かめるように足した。

### 5.3 分け方

切り分けは `scripts/56_split_for_shacl.py`。

- 50・54 が書く Turtle は、行頭の `<` から主語ごとのかたまりになっている。そのかたまりを、rdflib を使わずに振り分けた。
- 振り分けたファイルは `out/shacl_chunks/full/` に置いた(53 MB)。

| 種類 | 回 | 分け方 | 一緒に読むもの | 形 |
|---|---:|---|---|---|
| 手続(手続と記載のかたまり) | 10 | 手続ID の範囲。約 7,628 件ずつ | 型の索引 | ProcedureShape、CitationShape |
| 記録 | 10 | 手続と同じ手続ID の範囲 | なし | RecordShape |
| 条・項・号 | 4 | 法令ID の範囲 | 型の索引 | SubdivisionShape |
| 法令 | 1 | 全部 | なし | LawShape |
| 本文の版 | 10 | 法令ID の範囲 | その範囲の照合した条項号への参照、型の索引 | ExpressionShape、CitedProvisionShape |

- **型の索引**は、コード表・組織・法令・条・項・号の `rdf:type` だけを集めたもの(84,639 行)。`sh:class` を確かめるために入れた。
- 一緒に読んだもの(型の索引など)の上で出た結果は、その回の結果に数えない。その回の主のかたまりの主語(本文の版の回では、照合した条・項・号も)が対象のものだけを数えた。
  - 例えば条・項・号の回では、型の索引にある型だけの条・項・号が、1 回あたり約 12 万 2 千件の違反を出す。これは外している。
- 1 回ずつ別のプロセスで動かし、そのプロセスのメモリの最大(`ru_maxrss`)を記録した。

### 5.4 先に手続 2,000 件で比べた

手続ID の並びで最初の 2,000 件と、それにつながる記録・法令 175・条・項・号・本文の版を切り出した(`out/shacl_chunks/test/`)。同じデータを、まとめて 1 回でも、分けても通した。

| | まとめて通した | 分けて通した |
|---|---:|---:|
| 自作の SHACL の違反 | 0 | 0 |
| 公式 SHACL の違反 | 1,958(2 種類) | 1,958(2 種類) |
| メモリの最大(自作) | 346 MB | 188 MB(14 回のうち最大) |
| メモリの最大(公式) | 328 MB | 79 MB(7 回のうち最大) |

- 種類ごとの件数も、1 件ずつ(対象・形・経路・制約・値)も同じだった。
- 自作の形は違反 0 で比べる材料が無いので、わざと 6 か所を壊したデータ(`scripts/59b_make_broken.py`)でも比べた。
  - 壊したところ:
    - 手続の名前を 1 つ消す
    - 照合の結果を一覧に無い値にする
    - is_part_of を 2 つにする
    - 本文を 1 つ消す
    - 2025-11-01 の印を 1 つ消す
    - 記録の行番号を 1 つ消す
  - 自作の SHACL では、まとめても分けても 6 件(6 種類)の違反が出た。1 件ずつも同じだった。
  - 公式 SHACL では、どちらも 1,959 件で、消した名前の 1 件が増えた。
- 違いは無かったので、全件に進んだ。

### 5.5 全件の結果(自作の SHACL)

| 種類 | 回 | 1 回のトリプル | 違反 | 1 回の照合の時間 | 1 回のメモリの最大 |
|---|---:|---:|---:|---:|---:|
| 手続 | 10 | 205,558〜206,542 | 0 | 2.5〜3.0 秒 | 300〜353 MB |
| 記録 | 10 | 188,154〜205,944 | 0 | 0.5〜0.7 秒 | 261〜292 MB |
| 条・項・号 | 4 | 165,867〜166,495 | 0 | 32.4〜34.4 秒 | 991〜1,240 MB |
| 法令 | 1 | 17,885 | 0 | 0.1 秒 | 75 MB |
| 本文の版 | 10 | 164,665〜168,456 | 0 | 2.6〜2.9 秒 | 256〜325 MB |
| **計** | **35** | | **0 件** | 照合の合計 193 秒 | 最大 1,240 MB |

- **違反は 0 件。** 回ごとの数字は `out/59_shacl_full.txt` にある。
- 条・項・号の回だけ重いのは、型の索引にある約 8 万の条・項・号がすべて SubdivisionShape の対象になり、その回で外す結果まで計算しているため。

## 6. CPSV-AP 3.2.0 の公式 SHACL

### 6.1 あるか

ある。SEMIC が公開している。

- URL: `https://semiceu.github.io/CPSV-AP/releases/3.2.0/shacl/cpsv-ap-SHACL.ttl`(200、`text/turtle`、96,431 バイト)
- 保存先: `data/vocab/cpsv-ap-3.2.0-SHACL.ttl`。1,064 トリプル、対象のクラスは 31。
- 今回のデータで対象になるのは、PublicService、PublicOrganisation、eli:LegalResource、skos:Concept の 4 つ。
- PublicService で最小 1 つ(`sh:minCount 1`)とされているのは、dct:identifier、dct:description、dct:title、cv:hasCompetentAuthority の 4 つ。

**`rdf-report.md` の訂正:** rdf-report の 4 節では、CPSV-AP の HTML の表を読んで「name(dct:title)は Optional」と書いた。公式 SHACL では、dct:title は最小 1 つ(必須)になっている。表の読み取りが誤っていたか、表と SHACL が食い違っているかは確かめていない。今回は dct:title を入れたので、どちらでも違反にはならない。

### 6.2 通し方

5 節と同じ切り分けで、手続 10 回、組織・法令・コード表それぞれ 1 回の計 13 回通した。どの回も、主のかたまりのほかに型の索引を一緒に読んだ。

- 記録と本文の版は、公式 SHACL が対象にするクラスを含まないので通していない。2,000 件で比べたときは、まとめて通す側に記録と本文の版も入っていた。それでも結果は分けた場合と同じだった。
- 推論なし(`inference='none'`)。
- 1 回のメモリの最大は 401 MB。照合の合計は 99 秒。

### 6.3 結果(違反の種類ごと)。まだ直していない

| 重さ | 対象 | 性質 | 制約 | 件数 |
|---|---|---|---|---:|
| Violation | cpsv:PublicService | cv:hasLegalResource | sh:class eli:LegalResource | 74,544 |
| Violation | cv:PublicOrganisation | dct:spatial | sh:minCount 1 | 25 |
| **計** | | | | **74,569** |

- **cv:hasLegalResource(74,544 件)**: 先が eli:LegalResourceSubdivision(条・項・号)の手続すべてで出た。数は、条・項・号を指す手続の数 74,544 と同じ。法令そのものを指す 1,035 件には出ていない。
  - ELI の語彙では、LegalResourceSubdivision は LegalResource の下位クラス(`rdfs:subClassOf`)と定められている(`data/vocab/eli.raw`)。
  - 一方、SHACL の `sh:class` は、データの側にある `rdfs:subClassOf` しか見ない。今回のデータにはこの 1 行が無い。
  - **試し:** 手続 2,000 件の 4 回分に、この 1 行(`eli:LegalResourceSubdivision rdfs:subClassOf eli:LegalResource`)を足して通した。違反は 1,933 件から 0 件になった(`out/59c_subclass_try.txt`)。`rdf/` は変えていない。
- **dct:spatial(25 件)**: 組織 25 すべてに、管轄の地域(dct:spatial)が無い。
- 手続の必須の 4 つ(identifier、description、title、hasCompetentAuthority)では、違反は出ていない。
- 公式 SHACL の結果の表記では、dct が `dc1:` と出ている。結果のグラフの接頭辞の付け方によるもので、同じ `http://purl.org/dc/terms/`。

## 7. 出力(rdf/)と大きさ

トリプル数は、各ファイルを rdflib で丸ごと読み直して数えたもの(`out/55_check_rdf2_stopped.txt`)。書き出し側で数えた数(50 の計 3,626,875 と 54 の 748,282、合わせて 4,375,157)と合った。切り分けたファイルの和とも合った(5.2)。

| ファイル | 中身 | トリプル | gzip | 展開すると |
|---|---|---:|---:|---:|
| `codes.ttl.gz` | コード表 | 239 | 1,744 | 13,356 |
| `vocab.ttl.gz` | 独自の語彙 | 228 | 2,289 | 11,367 |
| `prov.ttl.gz` | 出典と生成の作業 | 20 | 906 | 2,014 |
| `organisations.ttl.gz` | 組織 25(新) | 125 | 972 | 7,588 |
| `laws.ttl.gz` | 法令 2,981 | 17,885 | 128,694 | 1,220,719 |
| `provisions.ttl.gz` | 条・項・号 81,572 | 407,860 | 942,322 | 24,485,215 |
| `expressions.ttl.gz` | 本文の版 90,970(新) | 748,282 | 8,624,277 | 115,777,160 |
| `procedures.ttl.gz` | 手続と記載 76,275 ずつ | 1,216,776 | 4,674,654 | 100,862,490 |
| `records.ttl.gz` | 調査の記録 76,275 | 1,983,742 | 4,986,958 | 101,650,322 |
| **計** | | **4,375,157** | **19,362,816** | **344,030,231** |

- 大きさの単位はバイト。
- 前回(rdf-report)の計は 3,397,914 トリプル、gzip 8,608,990 バイトだった。
  - 手続は 987,951 から 1,216,776 に増えた。差は 228,825 = 76,275 × 3(題名・所管・説明)。
  - 語彙は 217 から 228 に増えた(新しい性質と注記)。
  - 増えた分の大半は本文の版(gzip 8.6 MB)。
- 形の定義 `rdf/shapes.ttl` は 4,339 バイト(gzip なし)。

## 8. 分からないこと・決めていないこと

- **公式 SHACL の違反を直すか、どう直すかは決めていない。** 選べる道は次のとおり。
  - cv:hasLegalResource の違反には、次の道がある。
    - データに ELI の下位クラスの 1 行を入れる
    - 照合の側で使う語彙(ELI のオントロジー)を一緒に読ませる
    - 手続を法令(LegalResource)につなぎ、条・項・号へは別の性質でつなぐ
  - dct:spatial には、組織に日本国の地域(例えば EU の国の典拠表の JPN)を付けることになる。どの URI にするかは確かめていない。
- HTML の表と公式 SHACL で dct:title の必須の扱いが違って見えた理由(6.1)は、確かめていない。
- 2026-11-18 の版を付けていない条・項・号が 356 ある(4 節)。
- jpp:text は、要素の文字(ルビの読みを除く)をつないで、前後の空白だけを除いたもの。中の空白・改行は除いていない。
  - 比べ(fix-report の近さ)で使った文言(空白・改行を除いたもの)とは、形が違う。
  - 表や図(TableStruct など)の中の文字も、そのままつないでいる。
- 分けて通した結果が全件でもまとめた場合と同じかは、2,000 件でしか確かめていない。全件をまとめて通すことは、この機械のメモリでは前回できなかった。
- 基点の URI(w3id.org)は仮。登録はしていない(前回と同じ)。

## 9. スクリプト

| スクリプト | 内容 | 出力 |
|---|---|---|
| `scripts/50_build_rdf.py` | 手続・記録・組織・法令・条・項・号・コード表・語彙・出典(system python3) | `rdf/*.ttl.gz`、`out/50_build_rdf.txt` |
| `scripts/54_build_expressions.py` | 本文の版(取得なし) | `rdf/expressions.ttl.gz`、`out/54_build_expressions.txt` |
| `scripts/55_check_rdf2.py` | 読み直しと、まとめての SHACL(途中で止めた) | `out/55_check_rdf2_stopped.txt` |
| `scripts/56_split_for_shacl.py` | SHACL のための切り分け(`test` / `full`) | `out/shacl_chunks/`、`out/56_split_*.txt` |
| `scripts/57_count_checks.py` | 全体の数の確かめ(.venv) | `out/57_count_checks.txt` |
| `scripts/58_shacl_worker.py` | 1 回分の SHACL(.venv、1 回ずつ別プロセス) | `out/shacl_chunks/*/results/` |
| `scripts/59_shacl_split.py` | 分けて通す取りまとめと、2,000 件での比べ | `out/59_shacl_test.txt`、`out/59_shacl_full.txt` |
| `scripts/59b_make_broken.py` | 比べのために壊したデータを作る | `out/shacl_chunks/testbad/`、`out/59_shacl_testbad.txt` |
