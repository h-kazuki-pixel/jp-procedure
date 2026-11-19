# 行政手続LOD RDF の直し(3 回目): 公式 CPSV-AP の違反の直し

- 数字は次の出力から写した。
  - `out/50_build_rdf.txt`
  - `out/56_split_full.txt`、`out/57_count_checks.txt`
  - `out/59_shacl_test.txt`、`out/59_shacl_testbad.txt`、`out/59_shacl_full.txt`
  - `out/60_sizes_v3.txt`
  - 比べで違いが出たときの出力: `out/59_shacl_test_v3_mismatch.txt`、`out/59_shacl_testbad_v3_mismatch.txt`
- e-Gov への取得はしていない。
- ネットに取りに行ったのは、地名の URI を選ぶための確かめだけ。SPARQL が 6 回、直接の取得が 2 回(`data/vocab/spatial/`、一覧は同じフォルダの `fetched.txt`)。

## 1. 下位クラスの定義を語彙に入れた

**ELI の公式のオントロジーにある定義:**

- URL: `http://data.europa.eu/eli/ontology`
  - 2026-11-18 に取得済みのもの(`data/vocab/eli.raw`)を見た。取得のときは `http://publications.europa.eu/resource/cellar/917d16b5-28f6-11e8-b5fe-01aa75ed71a1.0001.01/DOC_1` へ転送された(`data/vocab/fetched.txt`)。
- `eli.raw` の 2326〜2328 行目:

  ```
  <owl:Class rdf:about="http://data.europa.eu/eli/ontology#LegalResourceSubdivision">
      <rdfs:subClassOf rdf:resource="http://data.europa.eu/eli/ontology#LegalResource"/>
      <rdfs:subClassOf rdf:resource="http://data.europa.eu/eli/ontology#WorkSubdivision"/>
  ```

**語彙(`rdf/vocab.ttl.gz`)に入れたもの:**

- `eli:LegalResourceSubdivision rdfs:subClassOf eli:LegalResource .` の 1 行。ELI の定義のうち、この 1 つだけを写した。WorkSubdivision は写していない。
- 語彙の `rdfs:comment` に、ELI の定義を写したもので、出どころは上の URL だと書いた。

## 2. 府省庁に dct:spatial を入れた

### 2.1 CPSV-AP 3.2.0 が勧める地名の URI

CPSV-AP 3.2.0 の説明(`https://semiceu.github.io/CPSV-AP/releases/3.2.0/`、保存は `data/vocab/cpsv-ap-3.2.0.html`)には、次のことが書かれている。

- **Public Organisation の spatial(1..\*):** 地域の URI は、権威ある地域の一覧のものを使う。欧州では、EU 出版局の ATU(Administrative Territorial Units)の一覧になるだろう、とある。
- **Public Service の spatial:** EU 出版局の ATU の URI を勧める。ATU が合わなければ、NUTS か LAU、NAL Place、Geonames の順に使う。それでも足りなければ、自分でコード表を作る。
- 説明が示しているリンク:
  - ATU `https://op.europa.eu/en/web/eu-vocabularies/dataset/-/resource?uri=http://publications.europa.eu/resource/dataset/atu`
  - NUTS `…/dataset/nuts`
  - LAU `https://ec.europa.eu/eurostat/web/nuts/local-administrative-units`
  - NAL Place `…/dataset/place`
  - Geonames `http://www.geonames.org`
- Country の一覧(`…/dataset/country`)も説明の中に出てくる。ただし住所の「行政単位 第 1 層」(locn:adminUnitL1、文字)についてで、spatial の勧めには入っていない。

**勧めの順に、国としての日本があるかを確かめた**(EU Vocabularies の SPARQL `https://publications.europa.eu/webapi/rdf/sparql`):

| 一覧 | 概念の数 | 日本 |
|---|---:|---|
| ATU | 3,504 | 英語の名前に Japan を含むもの: 無し |
| NUTS(`http://data.europa.eu/nuts`) | 3,417 | Japan・Nippon を含むもの: 無し |
| LAU | — | EU の地方の行政単位の一覧で、URI の一覧としては確かめていない |
| NAL Place | — | Japan・Tokyo で始まるもの: `place/JPN_TYO`(Tokyo、都市)だけ。国は無い |
| Geonames | — | `https://sws.geonames.org/1861060/`。名前 Japan、feature code `A.PCLI`(独立した政治単位 = 国)、国の符号 JP |

- Geonames の URI は `https://sws.geonames.org/1861060/about.rdf` を取得して確かめた(200、`rdf:about="https://sws.geonames.org/1861060/"`)。
- 参考に、Country の一覧の `http://publications.europa.eu/resource/authority/country/JPN` も 200 を確かめた(名前 Japan / 日本)。使ってはいない。

### 2.2 入れたもの

勧めの順で、国としての日本が最初に見つかったのは Geonames だった。そこで次のようにした。

- 府省庁 25 のすべてに `dct:spatial <https://sws.geonames.org/1861060/>` を付けた。
- 同じ URI に `a dct:Location` と `rdfs:label "日本"@ja, "Japan"@en` を書いた(`rdf/organisations.ttl.gz`)。
  - 公式 SHACL は、dct:spatial の先に `sh:class dct:Location` を求めるため。
  - 型を書いたのは、Geonames の地名を dct:Location とみなす、というこちらの言い方。
- 語彙の `rdfs:comment` に、Geonames を選んだ理由を書いた。

## 3. 下位クラスの定義を入れたことで起きたこと

SHACL の `sh:targetClass` は、データにある下位クラスの定義をたどる。そのため、`eli:LegalResource` を対象にする形が、条・項・号(81,572)にも当たるようになった。

- 手続 2,000 件の比べで、このことが分かった。まとめて通すと、自作の LawShape(「法令ごとに eli:id_local が 1 つ」)が条・項・号にも当たり、10,130 件の違反が出た。分けて通すと 0 件だった(`out/59_shacl_test_v3_mismatch.txt`)。
  - 分けて通すと 0 件になったのは、法令の回に条・項・号が入っていないため。
  - 分けて通す決め方の穴で、データの誤りではない。
- 直したことは 2 つ。
  1. **LawShape を、条・項・号には当たらないようにした。** 形の狙いは「法令ごと」なので、`sh:or ( [ sh:class eli:LegalResourceSubdivision ] [ id_local が 1 つ ] )` にした。前の版は `out/shapes_v3_before_lawfix.ttl.txt`。
  2. **分けて通すとき、条・項・号の回でも LegalResource の形を通すようにした。** 自作は LawShape を足し、公式は LegalResourceShape(条・項・号の 4 回)を足した。
- 直した後の比べ:
  - 手続 2,000 件では、自作も公式も、まとめて通しても分けて通しても 0 件で、1 件ずつも同じだった。
  - 壊したデータでも比べた。前の 6 か所に、法令の eli:id_local を 1 つ消すのを足して 7 か所にした。自作では、まとめても分けても 7 件(7 種類)出て、1 件ずつ同じだった。公式では、どちらも 1 件(消した名前)だった。

| 2,000 件 | まとめて | 分けて(回の最大) |
|---|---:|---:|
| 自作のメモリの最大 | 370 MB | 199 MB |
| 公式のメモリの最大 | 346 MB | 94 MB |

## 4. 分けて通し直した結果(全件)

### 4.1 公式 CPSV-AP 3.2.0 SHACL

**違反 0 件**(前回は 74,569 件)。17 回。

| 回 | 数 | 1 回のトリプル | 違反 | 1 回の照合 | 1 回のメモリの最大 |
|---|---:|---:|---:|---:|---:|
| 手続 | 10 | 205,790〜206,774 | 0 | 10.6〜13.5 秒 | 305〜368 MB |
| 組織 | 1 | 84,998 | 0 | 2.7 秒 | 207 MB |
| 法令 | 1 | 99,775 | 0 | 2.9 秒 | 210 MB |
| コード表 | 1 | 85,049 | 0 | 2.6 秒 | 191 MB |
| 条・項・号 | 4 | 166,099〜166,727 | 0 | 2.6〜2.7 秒 | 266〜290 MB |

- 照合の合計は 135 秒、メモリの最大は 368 MB。
- 組織の回には日本の地名(dct:Location)も入っていて、公式の Location の形でも違反は出なかった。

### 4.2 自作の SHACL

**違反 0 件**。35 回。

| 回 | 数 | 1 回のトリプル | 違反 | 1 回の照合 | 1 回のメモリの最大 |
|---|---:|---:|---:|---:|---:|
| 手続 | 10 | 205,790〜206,774 | 0 | 2.5〜4.7 秒 | 284〜336 MB |
| 記録 | 10 | 188,385〜206,175 | 0 | 0.6〜1.2 秒 | 250〜273 MB |
| 条・項・号 | 4 | 166,099〜166,727 | 0 | 41.0〜47.4 秒 | 954〜1,106 MB |
| 法令 | 1 | 18,116 | 0 | 0.3 秒 | 81 MB |
| 本文の版 | 10 | 164,897〜168,688 | 0 | 2.3〜2.7 秒 | 276〜325 MB |

- 照合の合計は 244 秒、メモリの最大は 1,106 MB。
- どの回にも語彙(`vocab.ttl.gz`)を一緒に読ませた。`sh:class` が下位クラスの定義を見るため。

### 4.3 全体の数(`scripts/57_count_checks.py`)

32 項目すべて合った(前回の 30 項目に 2 つ足した)。

- 足した項目:
  - dct:spatial を持つ組織が 25
  - dct:spatial の先がすべて dct:Location
- 切り分けたファイルのトリプルの和は、元のファイルと合った。
  - 変わった小さいファイル(codes 239、prov 20、organisations 153、laws 17,885)は、このスクリプトの中で読み直した。
  - 大きい 4 つは前回の読み直しの値を使った。中身が変わっていないことは、展開した中身の md5 が前と同じことで確かめた(`out/rdf_v2_md5/`)。

## 5. 作り直したファイルと大きさ

`scripts/50_build_rdf.py` を動かし直した。書き出し側で数えたトリプルは 3,626,906 で、前より 31 増えた。

- 語彙 +3: 下位クラスの 1 行と注記 2 つ
- 組織 +28: dct:spatial 25 と、日本の地名の 3 つ
- 展開した中身が変わったのは vocab、organisations、prov の 3 つだけ。
  - prov は、作業の終わった時刻(prov:endedAtTime)だけが変わった。
  - ほかの 6 つ(codes、laws、provisions、expressions、procedures、records)は md5 が前と同じ。

| ファイル | トリプル | gzip | 展開すると |
|---|---:|---:|---:|
| `codes.ttl.gz` | 239 | 1,744 | 13,356 |
| `vocab.ttl.gz` | 231 | 2,560 | 11,978 |
| `prov.ttl.gz` | 20 | 906 | 2,014 |
| `organisations.ttl.gz` | 153 | 1,044 | 9,048 |
| `laws.ttl.gz` | 17,885 | 128,694 | 1,220,719 |
| `provisions.ttl.gz` | 407,860 | 942,322 | 24,485,215 |
| `expressions.ttl.gz` | 748,282 | 8,624,277 | 115,777,160 |
| `procedures.ttl.gz` | 1,216,776 | 4,674,654 | 100,862,490 |
| `records.ttl.gz` | 1,983,742 | 4,986,958 | 101,650,322 |
| **計** | **4,375,188** | **19,363,159** | **344,032,302** |

- 大きさの単位はバイト。
- 形の定義 `rdf/shapes.ttl` は 166 トリプル、4,525 バイト。

## 6. 分からないこと・決めていないこと

- **府省庁の地域は、すべて国としての日本にした。** 府省庁は国の機関なので国全体とみなした。地方支分部局の管轄などは見ていない。
- **Geonames は、EU の一覧ではない。** 勧めの順に従った結果として選んだ。Country の一覧(`country/JPN`)を使う道もあるが、CPSV-AP の説明では spatial の勧めに入っていない。どちらがよいかは決めていない。
- **LAU は URI の一覧として確かめていない。** EU の地方の行政単位なので、日本は無いと見ている。
- **Geonames の地名に `a dct:Location` と書いたのは、こちらの言い方。** Geonames 自身の RDF での型は `gn:Feature`。
- **下位クラスの定義を入れると、`eli:LegalResource` を対象にするほかの道具でも、条・項・号が法令として数えられる。** 例えば、「eli:LegalResource の数」を推論ありで数えると 2,981 ではなくなる。57 の確かめは推論なしで数えている。
- 分けて通した結果がまとめた場合と同じかは、今回も手続 2,000 件でしか確かめていない。
