# 行政手続LOD

日本の国の行政手続(令和7年度 行政手続等の棚卸調査結果の <!-- n:procedures -->76,275<!-- /n --> 件)と、その根拠の条・項・号、2025-11-01 から 2026-11-18 までの条文の変化を、Linked Open Data(RDF)にしたものです。

> **English summary.** *Gyosei Tetsuzuki LOD* is Linked Open Data about <!-- n:procedures -->76,275<!-- /n --> administrative procedures of the Government of Japan (from the Digital Agency's FY2025 inventory survey). It links each procedure to the article, paragraph or item of the law that is its legal basis (via the e-Gov Law API v2), keeps the text of those provisions as of 2025-11-01 and 2026-11-18, and records how each provision changed between the two dates. The text comparison is mechanical: it does not judge how important a change is. Vocabularies: CPSV-AP 3.2.0, ELI, PROV-O, SKOS. Data: CC BY 4.0. Code: MIT. This is an independent work, not an official dataset of the Government of Japan.

**何の役に立つか**

- **府省庁・自治体で手続を受け持つ人**が、法令が改正されたとき、自分の手続の根拠の条文が本当に変わったかを、条・項・号の単位で確かめられます(法令の単位で調べるより、見直す手続がずっと少なくなります)。
- **手続を案内する人や事業者**が、ある条文を根拠にする手続の一覧を引けます。
- **研究や報道**で、府省庁ごとに、どれだけの手続の根拠が変わったかを数えられます。
- **機械**が、手続・条文・改正の記録の URI を引いて、RDF(Turtle・JSON-LD)で受け取れます。

- <!-- status -->最後に確かめた日: **2026-11-21**。直近の週(2026-11-18〜2026-11-21)に足した改正の記録: 16 件。(`status.json` から書いた行)<!-- /status -->
- 識別子の基点は `https://w3id.org/jp-procedure/`。**まだ登録していません**(下書きは `w3id/`)。
- 国やデジタル庁が作ったデータではありません。作った人が、公開されているデータを加工して作りました。

## 何が入っているか

| もの | 数 | クラス |
|---|---:|---|
| 手続 | <!-- n:procedures -->76,275<!-- /n --> | `cpsv:PublicService`(名前・所管・説明・根拠) |
| 調査の記録(R7 の 1 行) | <!-- n:records -->76,275<!-- /n --> | `jpp:SurveyRecord`(46 列の値と、元の行番号) |
| 所管府省庁 | <!-- n:organisations -->25<!-- /n --> | `cv:PublicOrganisation` |
| 法令 | <!-- n:laws -->2,981<!-- /n --> | `eli:LegalResource` |
| 条・項・号 | <!-- n:subdivisions_base -->81,572<!-- /n -->(ほかに、移った先として <!-- n:subdivisions_added -->542<!-- /n -->) | `eli:LegalResourceSubdivision` |
| 条・項・号の本文の版 | <!-- n:expressions -->91,044<!-- /n --> | `eli:LegalExpression`(2025-11-01・2026-11-18 の本文) |
| 改正の記録 | <!-- n:changes -->2,080<!-- /n -->(当たる手続の行 <!-- n:change_rows -->3,112<!-- /n -->) | `jpp:ProvisionChange` |
| 期間内の法令の改正 | <!-- n:revisions -->2,840<!-- /n -->(法令 <!-- n:revision_laws -->1,252<!-- /n -->。改正の記録に結んだのは <!-- n:revisions_linked -->1,317<!-- /n -->) | `jpp:LawRevision`(e-Gov の改正履歴で施行期日が 2025-11-02〜2026-11-18 のもの) |

- 条・項・号の URI(`/provision/{法令ID}/{条}/{項}/{号}`)は、「法令の中の番号で指す位置」です。版をまたいでも、同じ番号は同じ URI になります。
- 中身(本文)は版(`{条・項・号}/version/{版のID}`)で持ちます。番号の位置の中身が変わったことは、改正の記録で表します。
- 改正の記録の区分は 10 個です。

  | 区分 | 改正の記録 | 手続の行 |
  |---|---:|---:|
  | 文言が変わった: 番号の参照だけ | <!-- n:kind_rec:wording-numref -->145<!-- /n --> | <!-- n:kind_rows:wording-numref -->284<!-- /n --> |
  | 文言が変わった: それ以外 | <!-- n:kind_rec:wording-other -->1,153<!-- /n --> | <!-- n:kind_rows:wording-other -->1,838<!-- /n --> |
  | 大きく書き換わった | <!-- n:kind_rec:rewritten -->155<!-- /n --> | <!-- n:kind_rows:rewritten -->204<!-- /n --> |
  | 入れ替わった→移った | <!-- n:kind_rec:swapped-moved -->306<!-- /n --> | <!-- n:kind_rows:swapped-moved -->367<!-- /n --> |
  | 入れ替わった→移った先が一つに決まらない | <!-- n:kind_rec:swapped-ambiguous -->10<!-- /n --> | <!-- n:kind_rows:swapped-ambiguous -->14<!-- /n --> |
  | 入れ替わった→移った先が見つからない | <!-- n:kind_rec:swapped-nodest -->19<!-- /n --> | <!-- n:kind_rows:swapped-nodest -->30<!-- /n --> |
  | 無くなった→移った | <!-- n:kind_rec:removed-moved -->123<!-- /n --> | <!-- n:kind_rows:removed-moved -->152<!-- /n --> |
  | 無くなった→移った先が一つに決まらない | <!-- n:kind_rec:removed-ambiguous -->12<!-- /n --> | <!-- n:kind_rows:removed-ambiguous -->16<!-- /n --> |
  | 無くなった→移った先が見つからない | <!-- n:kind_rec:removed-nodest -->76<!-- /n --> | <!-- n:kind_rows:removed-nodest -->112<!-- /n --> |
  | 無くなった→判定できない | <!-- n:kind_rec:removed-undetermined -->65<!-- /n --> | <!-- n:kind_rows:removed-undetermined -->73<!-- /n --> |

  決め方は `reports/fix-report-5.md` にあります。

  - **「移った先が見つからない」**(入れ替わった→・無くなった→ の 2 つ)は、近い文言が別の番号に見つからなかった、という意味です。決まりが無くなったとは限りません。条文が組み替えられて、文言が大きく変わったときもこの区分になります(コードの URI は `…/swapped-nodest`・`…/removed-nodest` のまま)。
  - 例: 気象業務法施行規則 第50条第1項第4号(手続ID 33393)。今の第50条は組み替えられ、許可を受けた者の報告は第2項・第3項に移っていますが、旧い文言に近い文言が見つからないため、機械はこの区分にしました。

## ファイル

すべて 1 ファイル 100 MB 未満です(大きさはバイト)。

| ファイル | 中身 | 大きさ |
|---|---|---:|
| `data/rdf/procedures.ttl.gz` | 手続と根拠の記載 | <!-- n:size:data/rdf/procedures.ttl.gz -->4,674,654<!-- /n --> |
| `data/rdf/records.ttl.gz` | 調査の記録(個人の連絡先は伏せた) | <!-- n:size:data/rdf/records.ttl.gz -->4,986,910<!-- /n --> |
| `data/rdf/organisations.ttl.gz` | 所管府省庁 | <!-- n:size:data/rdf/organisations.ttl.gz -->1,044<!-- /n --> |
| `data/rdf/laws.ttl.gz` | 法令 | <!-- n:size:data/rdf/laws.ttl.gz -->128,694<!-- /n --> |
| `data/rdf/provisions.ttl.gz` | 条・項・号 | <!-- n:size:data/rdf/provisions.ttl.gz -->942,322<!-- /n --> |
| `data/rdf/expressions.ttl.gz` | 本文の版 | <!-- n:size:data/rdf/expressions.ttl.gz -->8,624,277<!-- /n --> |
| `data/rdf/changes.ttl.gz` | 改正の記録、期間内の改正、移った先の条・項・号、区分のコード表、判定のやり方 | <!-- n:size:data/rdf/changes.ttl.gz -->174,405<!-- /n --> |
| `data/rdf/codes.ttl.gz` | コード表 | <!-- n:size:data/rdf/codes.ttl.gz -->1,744<!-- /n --> |
| `data/rdf/vocab.ttl.gz` | 独自の語彙(`jpp:`)とその説明 | <!-- n:size:data/rdf/vocab.ttl.gz -->5,875<!-- /n --> |
| `data/rdf/prov.ttl.gz` | 出典と作成の作業 | <!-- n:size:data/rdf/prov.ttl.gz -->906<!-- /n --> |
| `data/jsonld/*.jsonld.gz` | 上と同じ中身の JSON-LD(展開形)。トリプル数が同じことを確かめた | 計 <!-- n:size:jsonld_total -->21,842,590<!-- /n --> |
| `data/csv/procedures_provisions.csv` | 手続と根拠の条・項・号(1 行 = 1 手続、<!-- n:csv_rows:procedures_provisions.csv -->76,275<!-- /n --> 行) | <!-- n:size:data/csv/procedures_provisions.csv -->22,889,721<!-- /n --> |
| `data/csv/changes.csv` | 改正の記録(1 行 = 1 記録、<!-- n:csv_rows:changes.csv -->2,064<!-- /n --> 行) | <!-- n:size:data/csv/changes.csv -->1,091,935<!-- /n --> |
| `data/redactions.csv` | 調査の記録から伏せた個人の連絡先の一覧(手続ID・列・位置・種類・理由。中身は書かない) | <!-- n:size:data/redactions.csv -->430<!-- /n --> |
| `stats.json`・`changed.json` | 閲覧ページのはじめの画面の数と、根拠の条・項・号が変わった手続(文言が変わった・別の番号へ移った・無くなった)の一覧(違う所の抜き出しつき)。データから機械で作る | — |

- RDF は計 <!-- n:triples_total -->4,424,933<!-- /n --> トリプルです(閲覧ページ・SPARQL サーバーの店に読み込んだ数。重なりを除く)。
- 語彙(`data/rdf/vocab.ttl.gz`・`vocab.ttl`)には、毎週の追跡が書く語を足すことがあります。足すだけで、今ある語の意味は変えず、消しません。足した語には足した日(`dct:issued`)を付けています。
- 毎週の追跡が動くと、`data/rdf/weekly/` に改正の記録と、その週に施行期日がある改正(このデータの法令のもの)が足されます。
- `data/tracking/` は、追跡に使う改正履歴と状態です。
- 一括ダウンロードの更新データが取れなかった日(土日・祝日などは HTTP 500 が返ります)は、法令API v1 の更新法令一覧を引きます。「取得結果が０件」なら「更新法令なし(v1 の一覧で 0 件)」として `status.json` に書き、取り直しの対象から外します。v1 も取れない日と、本文を取れなかった法令は、「確かめられなかった」ものとして `data/tracking/state.json` に残し、次の実行でもう一度取ります。数は `status.json` と閲覧ページに出ます(0 のときは出しません)。取れないままが 4 週続いたものは Issue にします。
- 毎週の追跡は、根拠に挙がる法令の廃止・失効も見ます。e-Gov 法令API v2 の法令一覧取得API を `repeal_status=Repeal,Expire,Suspend,LossOfEffectiveness`(`limit=1000`、`omit_current_revision_info=true`)で毎回引き、各法令の `revision_info` の `repeal_status`(廃止等の状態)・`repeal_date`(その日)・`current_revision_status`(今の版の状態)を使います(`scripts/law_status.py`)。
  - 今の版の状態が `Repeal` で日付のある法令だけを「廃止・失効した」とみなします。廃止の版が `UnEnforced` と返るものや、日付の無いものは分類せず、`data/tracking/last_run.json` の `law_status_unclear` に出します。
  - 比べる期間の中で廃止・失効した法令は、区分「根拠の法令が廃止・失効した」の記録(`jpp:LawStatusChange`)にして、その法令を根拠に挙げるすべての手続に付けます(状態・日付・出典つき)。条文の文言の比べとは別に数えます。
  - 期間より前に廃止・失効していた法令は、変化に数えず、法令の状態(`jpp:LawStatus`)として持たせるだけにします。
- 更新データが取れた日も、v1 の一覧の件数と更新データの行数を毎回比べ、`status.json` に書きます(合わなければ Issue にします)。
- e-Gov が版を変えずに本文を直したもの(版の ID が公開しているデータと同じで、文言だけが違うもの)は、改正の記録にせず、[`data/tracking/egov_corrections.csv`](data/tracking/egov_corrections.csv)(法令ID、条・項・号、版の ID、見つけた日、違う所)に残します。公開しているデータの文言は直しません。

## 元のデータ

- デジタル庁「行政手続等の棚卸調査結果」(令和7年度、調査時点 令和7年11月1日。<https://www.digital.go.jp/resources/procedures-survey-results>)
- デジタル庁「行政手続等の悉皆調査結果」(令和6年度。同じページ)。法令番号を引き継ぐためだけに使いました。
- e-Gov 法令検索の法令データ(e-Gov 法令API Version 2、<https://laws.e-gov.go.jp/api/2/>)
  - 法令一覧と本文(asof=2025-11-01、asof=2026-11-18)、改正履歴
  - 2026-11-17〜18 に取得

## 元のデータから変えた点

- **調査の記録の自由記述にあった、個人の連絡先を伏せました。**
  - 伏せたのは、個人の氏名・個人あての電話番号・メールアドレスです。部署の名前や代表の窓口は残しました。個人あてか分からないものは、伏せる側に倒しました。
  - 伏せた所は「(個人の連絡先のため伏せた)」に置き換えました(`jpp:SurveyRecord` の値。Turtle・JSON-LD とも)。
  - 伏せた所の一覧は `data/redactions.csv` です。手続ID・列・位置・種類・理由だけを書き、伏せた中身は書いていません。
  - 探し方: 調査の記録のすべての列とほかのファイルで、メールアドレスと電話番号の形、「担当」「氏名」「連絡先」などの語や敬称のそばの人名の形を機械で探し、当たったものを Claude Code が 1 つずつ見て決めました(作った人は、まだ見ていません)。
  - **人名は機械で拾いきれず、残っているかもしれません。** 見つけたら、Issue で知らせてください(Issue には、その人名を書かず、手続ID と列だけを書いてください)。
- 元のデータ(デジタル庁の Excel)そのものは変えていません。作り直すときは `scripts/redact.py` が `data/redactions.csv` を当てます。

## 作り方

題材・設計・判定の決まりは、作った人が、作った Claude Code とは別の AI(別の会話の Claude)と相談して決めました。案の多くはその AI が出し、採るかどうかを作った人が決めました。スクリプトと報告(`reports/`)は Claude Code(Anthropic の、AI でプログラムを書く道具)が書きました。**区分の行を読んで確かめたのは、主にその別の AI です。作った人は、人の抜き取りの 23 件を読みました(2026-11-20)。**

`scripts/README.md` に、動かす順と中身を書きました。経緯と数は `reports/` にあります。

**点検の分担**

| 点検 | だれが | 中身 |
|---|---|---|
| 抜き取りの点検 | 別の AI | 抜き取った 80 行(`reports/review/review-sample.csv`)を読んだ。そのうち 11 行を e-Gov の本文(法令API)と照らし、10 行が一致、1 行は本文の取得に失敗した。残りの 69 行は e-Gov と照らしていない |
| 境目の行の読み直し | 別の AI | 区分の境目に近い行を読んだ。近さ r0 が 0.5〜0.7 の 30 行(`review-boundary-06.csv`)、「移った」の近さが 0.90〜0.95 の 43 行(`review-moves-090-095.csv`) |
| 判定の決まりの直し | 別の AI が決まりの案を出し、作った人が採ると決め、Claude Code が書き、機械が当てる | 読み直しで見つかった区分の誤りから、決まりを第 5 版まで直した(`reports/fix-report*.md`)。決まりで決められず、別の AI の読みで区分を「判定できない」にしたのが 3 件(確かめの記録 `jpp:Review` に、別の AI の記録として、日付と理由を入れた。人の抜き取りの記録と並べて残す) |
| 人の抜き取り(2026-11-20) | 人(作った人) | 作った人が23件(別の AI が区分を決めた3件すべて、文言が変わった10、移った5、移った先が見つからない5。種 20261119)を用紙で読み、23件とも「合う」と付けた。用紙には移った先の文言が出ていなかったため、移った5件は、作った人が e-Gov で移った先の条文を開いて確かめた。抜き取りが小さいので、誤りの割合は言えない(0件/10件のとき、上限は約26%)。同じ23件のうち16件を、別の AI が e-Gov の API で引き直し、14件で今の条文と合うことを見た。2件は取得できなかった。用紙と結果は `reports/review/human-check.html`・`human-check-result.csv`。用紙と結果は区分の名前を変える前に作ったため、「移った先が見つからない」は古い名前「移った先なし」で出ます。用紙では、移った5件の「移った先の文言」の欄に「(なし。この番号は新しい版に無い)」と出ていた。これは用紙を作るスクリプトの誤りで(移った先の文言を入れていなかった)、手続ID 109644・50387 は同じ番号が今もある。用紙は書き換えず、スクリプトは直した。結果はデータの確かめの記録(`jpp:Review`、確かめた者の種類「人」)に入れた |
| 自作の SHACL | 機械 | `shapes/shapes.ttl`。分けて通し、違反を数える |
| 公式の SHACL | 機械 | CPSV-AP 3.2.0(SEMIC)。分けて通し、違反を数える |
| 全体の数の確かめ | 機械 | `scripts/57_count_checks.py`。手続・改正の記録などの数が、元の表と合うか |

- 人が読んだのは、人の抜き取りの 23 件だけです。別の AI が読んだのも上の行だけです。ほかの行の区分は、機械の判定のままです。

1. 手続ごとに、法令ID を決めます(法令番号 → 法令名 → 表記のゆれを直した法令名)。
2. 根拠条項号を条・項・号に分け、2025-11-01 時点の本文で照合します。
3. 照合できた最も深い条・項・号について、2025-11-01 版と 2026-11-18 版の文言を比べます。
4. 決まり(第 5 版)で区分を付けます。「移った」先は、同じ法令の中で文言が近い要素を探して決めます。
5. CPSV-AP 3.2.0・ELI・PROV-O・SKOS で RDF にします。

## 確かめ方

| 確かめ | 結果 |
|---|---|
| 自作の SHACL(`shapes/shapes.ttl`。1 件の中で閉じる形) | 45 回に分けて通し、違反 0 件。上限を外した所に下限(1 つ以上)が効いていることを、小さな壊したデータで確かめた(`scripts/73_check_min_bounds.py`) |
| CPSV-AP 3.2.0 の公式 SHACL(SEMIC、<https://semiceu.github.io/CPSV-AP/releases/3.2.0/shacl/cpsv-ap-SHACL.ttl>) | 28 回に分けて通し、違反 0 件 |
| まとめて通す・分けて通すの比べ | 手続 2,000 件で、わざと 10 か所壊したデータも含め、違反が 1 件ずつ同じ |
| 全体の数(`scripts/57_count_checks.py`) | 110 項目すべて合う(README の数 51 項目、区分を確かめた記録 4 項目を含む。手続 <!-- n:procedures -->76,275<!-- /n -->、改正の記録の手続の行 <!-- n:change_rows -->3,112<!-- /n -->、法令の単位で知らせた場合の手続 <!-- n:law_level -->47,352<!-- /n -->、`stats.json` の数 など) |
| 判定のモジュール(`scripts/change_rules.py`) | 決まりを順に当てた結果と、<!-- n:law_level -->47,352<!-- /n --> 行すべてで同じ区分 |
| 抜き取りの点検 | 別の AI が 80 行と境目の 73 行を読んだ(e-Gov の本文と照らしたのは 11 行。10 行が一致、1 行は取得に失敗)。区分を変えたのは 3 件で、別の AI の読み(確かめの記録 `jpp:Review`)。人の抜き取り 23 件(2026-11-20)は、23 件とも「合う」 |

## 言えること・言えないこと

- **文言の比べは機械的です。**
  - 空白・改行を除いた文字列が同じかどうかと、`difflib` の近さで分けています。
  - 変更の重さ(手続の中身が変わるかどうか)は判断していません。「番号の参照だけ」は、変わったのが条・項・号を指す番号だけだった、という意味です。
- **旧い版で指す先が一つに決まる引用は、その条・項・号の URI で追います。** たとえば「第18条第1号」は、2025-11-01 の版で第18条の項が 1 つだったので、第18条第1項第1号(`…/18/1/1`)として追います。新しい版で項が増えても、この URI で比べます(毎週の追跡。初めの比べでは、このような号を「比べられない」とした行が 3 行あります)。
- **「移った」は、文言が近い要素が別の番号にある、という意味です。** 法令上の繰上げ・繰下げだと確かめたわけではありません。改正法の本文は見ていません。
- **どの改正で変わったかは、条の単位では分かりません。** 改正の記録には、期間内に施行されたその法令の改正(改正履歴にあるもの)をすべて結んでいます。そのうちどれがその条・項・号を変えたかは分かりません。
- **このデータは、取った時点の e-Gov の中身です。** e-Gov は、施行日より遅れて本文を載せることがあり(2026-11-18 施行の改正の本文が、同じ日の 10 時すぎに載った例があります)、版(law_revision_id)を変えずに本文を直すこともあります(「令和六年法律第号」が「令和六年法律第十八号」に直った例があります)。初めの比べ(2025-11-01〜2026-11-18)の新しい側の文言は、2026-11-18 の朝に取った本文です。
- **初めの比べは条文の文言だけを見ていて、法令の廃止・失効を見ていませんでした。** 2026-11-21 に、比べた期間(2025-11-02〜2026-11-18)の中で廃止・失効した根拠の法令 13・その手続 207 を、別のファイル(`data/rdf/weekly/supplement_law-status_2025-11-01_2026-11-18.ttl.gz`、`scripts/60_law_status_supplement.py`)で補いました。初めのファイルは変えていません。閲覧ページのはじめの画面では、初めの比べの数(根拠の条文が変わった手続 3,090)と補いの数を分けて出します。
- **「期間内の改正が無い」は、2026-11-18 に取った改正履歴に、期間内の改正が無かったという意味です。** そのあと e-Gov に載った改正は入っていません(毎週の追跡で見つけたときに足します)。
- **初めのデータには、e-Gov が改正を載せている途中に取ったために新しい版が取れず、比べていない行が 57 行あります**(5 法令。2026-11-18 の朝に、その時点の本文を取ったら 404 が返った)。このほか、新しい版を取っていない行が 20 行、新しい版で号の位置を決められなかった行が 3 行あります。初めのデータは書き換えず、毎週の追跡で、これらの条・項・号を毎回比べ、版と改正の記録を足しています(文言が同じなら版だけを足し、違えば改正の記録にします)。
- **毎週の追跡が初めて足した改正(`jpp:LawRevision`)には、初めて見つけた日(`jpp:firstFoundOn`)を付けます。** その日が比べた期間の終わりより後の改正は、施行期日がその期間にあっても、その期間の「期間内の改正」(法令の単位で知らせた場合の数)に数えません(`queries/q7_law_level_by_period.rq`)。
- **毎週の追跡は、公開しているデータの文言と、その日の e-Gov の本文の違いを記録します。** 前回の日付で e-Gov から取り直すことはしません。
  - 遅れて載った改正も、見つけた週の記録にします。改正(`jpp:foundRevision`)は e-Gov の法令番号・公布日・施行期日のまま結び、見つけた日は `jpp:foundOn` に持ちます。改正そのものを週の追跡が初めて足し、その施行期日が比べた期間の始め以前のときだけ、遅れて載った印(`jpp:enforcedBeforePeriod true`)を付けます。
  - 初めのデータに新しい版が無かった条・項・号をあとで比べて記録にしたときは、あとで比べた理由(`jpp:recheckReason`。初めの比べで位置を決められなかった・初めに版を取れなかった)を付けます。この理由は、公開しているデータから決めています(その法令に 2026-11-18 の版が 1 つでもあれば「位置を決められなかった」、無ければ「版を取れなかった」)。e-Gov への取得の記録そのものではありません。改正が初めのデータにあるときは、遅れて載った印は付けません。
  - `jpp:foundRevision` は新しい文言の版の改正です。その条・項・号を変えた改正とは限りません(あいだに別の改正があることもあります)。
  - 版を変えない直しは改正の記録にせず、`data/tracking/egov_corrections.csv` に残します。
- **更新の無い日の扱いは、e-Gov の説明に明記がありません。** 一括ダウンロードの更新データが取れず、法令API v1 の更新法令一覧が 0 件(「取得結果が０件でした」)の日を、「更新法令なし」とみなしています。e-Gov が、その日に更新が無いと書いているわけではありません。
- **附則は、制定附則(原始附則)だけを扱っています。** 改正法の附則は照合していません。
- **法令ID を決められなかった手続(696 件)と、条・項・号まで照合できなかった手続があります。** 照合の結果は手続ごとに入れています(`jpp:matchResult`)。
- **説明(`dct:description`)は、調査の項目から機械で作った文です。** 末尾に「(調査の項目から機械で作った説明)」と付けています。
- **府省庁の地域(`dct:spatial`)は、すべて国としての日本です**(Geonames の URI)。
- **改正法令の部分が 0 の版(<!-- n:versions_zero -->1,360<!-- /n -->)は、日付が施行期日か基準日かを見分けていません。** 版の ID は e-Gov の法令履歴ID(`{法令ID}_{日付}_{改正法令の法令ID}`)で、改正法令の部分が `000000000000000` の版は、e-Gov の説明では初めの版か基準日の版です。`eli:version_date` には、その日付をそのまま入れました(語彙の `jpp:lawRevision` の説明にも書きました)。

- **URI を機械が引いたときの行き先は、Cloud Run の SPARQL サーバーです。** `https://w3id.org/jp-procedure/procedure/…` などを、HTML 以外で引くと、Cloud Run の DESCRIBE に転送されます。Cloud Run を止めると、機械からは引けなくなります(そのときは、w3id の転送を一括ダウンロードの案内に直します。`deploy.md` の「止めるとき」)。ブラウザで引いたときの閲覧ページも、Cloud Run に問い合わせます。データのファイル(`data/`)は、Cloud Run を止めても使えます。

- **URI を機械が引いたとき、Accept が `*/*`(や Accept なし)だと、返る形は N-Quads(Content-Type `application/n-quads`)です。** DESCRIBE の結果にはグラフの名前が無いので、中身は N-Triples の形で、Turtle としても読めます。`Accept: text/turtle` を付ければ Turtle、`Accept: application/ld+json` を付ければ JSON-LD で返ります(Oxigraph 0.5.13 のサーバーの決まり。URL で形を選ぶ引数はありません)。

## 使い方(問いの例)

`queries/` に SPARQL の例を置きました。接頭辞は `queries/PREFIXES.rq` にまとめてあります。

| ファイル | 問い |
|---|---|
| `q1_procedures_by_provision.rq` | ある条文(関税法 第62条の15)を根拠にする手続 |
| `q2_changed_by_kind.rq` | 期間内に根拠の条・項・号が変わった手続を、区分ごとに数える |
| `q3_changed_by_ministry.rq` | 所管府省庁ごとの、根拠の条・項・号が変わった手続の数と割合 |
| `q4_old_new_text.rq` | ある手続(手続ID 119637)の根拠の条文の、旧い文言と新しい文言 |
| `q5_count_procedures.rq` | 手続の数(閲覧ページのはじめの画面) |
| `q6_changes_by_period.rq` | 期間ごとの、改正の記録と、知らせる手続(根拠の条・項・号が変わった手続(文言が変わった・別の番号へ移った・無くなった))の数(同) |
| `q7_law_level_by_period.rq` | 期間ごとの、法令の単位で知らせた場合の手続の数(同) |

pyoxigraph(0.5.13)で試すなら、次のようにします。

```sh
pip install pyoxigraph==0.5.13
python3 scripts/62_oxigraph_load.py data/rdf store/oxigraph    # RDF の場所と店の場所
python3 scripts/63_queries.py store/oxigraph queries           # 店の場所と問いの場所
```

手元で試したときは、全部を読み込むのに約 20 秒、ディスクの店は約 663 MB、`queries/` の q1〜q4 の 4 つの問いは、それぞれ 1 秒未満でした(`reports/rdf-report-4.md`。q5〜q7 はそのあとに足したもので、この測りには入っていない。q7 は手元で約 4.7 秒)。

## 閲覧ページ(`view.html`)

GitHub Pages に置く 1 枚のページです。SPARQL の行き先に問い合わせて、手続・条文・府省庁ごとの数を見せます。

公開している場所: <https://h-kazuki-pixel.github.io/jp-procedure/view.html>

**手続・条文・探す・問いを試す のページは、Cloud Run の SPARQL サーバーに問い合わせます。** サーバーに問い合わせられないとき(止めたときなど)は、エラーでなく「SPARQL サーバーに問い合わせられません。データのファイル(data/)は使えます」と出ます。はじめの画面の数・府省庁ごとの数・変わった手続の一覧は、`stats.json`・`changed.json` から出るので、サーバーに問い合わせられなくても見られます。

- 数(手続、根拠の条文の変化、根拠の条文が変わった手続(文言が変わった・別の番号へ移った・無くなった)、法令の単位で知らせた場合との差)は、データを作るとき(毎週の追跡を含む)に `queries/` の q5〜q7 で出して `stats.json` に置いたものを読みます(`scripts/75_make_stats.py`)。「府省庁ごと」の数も、同じときに q3 で出して `stats.json` に置いたものを読みます。開くたびに重い問いは回しません。数の横に、元の問いへのリンクがあります。
- `stats.json` の数(府省庁ごとの数を含む)は、全体の数の確かめ(`scripts/57_count_checks.py`)が SPARQL を使わずに数えた数と比べてあります。
- 最後に確かめた日は `status.json` から読みます。
- 「変わった手続の一覧」は、データを作るとき(毎週の追跡を含む)に `scripts/82_make_changed_list.py` が作った `changed.json` を読みます。開くたびに問いは回しません。
  - 期間(初めの期間・毎週の追跡の週・すべて)で絞れます。初めは、初めに比べた期間を出します。
  - 週の記録には、区分の下に見つけた改正(新しい文言の版の改正の法令番号)を出します。遅れて載った改正は「施行は ○ 年 ○ 月 ○ 日(比べた期間より前)。e-Gov に載ったのを見つけたのは ○ 月 ○ 日」と出します(施行日が期間の始めの日と同じときは「比べた期間の始めの日」と出します)。あとで比べた記録は「この改正は初めのデータにあります。この条・項・号は初めの比べで位置を決められず、○ に比べ直しました」のように、理由ごとに出します。手続のページでも同じです。旧い文言・新しい文言の見出しの日付は、出している版の確かめた日(`jpp:asOf`)から作ります。
  - 1 行 = 改正の記録 × 手続。区分の順(文言が変わった: それ以外、大きく書き換わった、文言が変わった: 番号の参照だけ、入れ替わった…、無くなった…)に並べます。
  - 違う所の抜き出し: 文言が変わった行は、旧い文言と新しい文言を文字の単位で比べ(`difflib`)、最初に違う所の旧い文字と新しい文字を前後 4 文字と一緒に出し、ほかにもあれば「ほか n か所」と付けます(1 か所が 16 文字を超えるときは切ります)。移った行は「第○条… → 第○条…」、移った先が一つに決まらない行は「→ 候補 n 件」、無くなった行は「同じ番号の要素が無い」です。抜き出しも機械で作ったものです。
- 下の欄に、e-Gov が版を変えずに本文を直したものの一覧(`data/tracking/egov_corrections.csv`)へのリンクがあります。
- SPARQL の行き先は、ページの先頭の `CONFIG.endpoint` の 1 か所で変えます。
- 読むだけです。解析のタグや利用者の記録は入れていません。外のサイトからスクリプトや書体を読み込みません。
- 手元で試すには、Oxigraph を読むだけで立て、リポジトリの一番上をウェブで出します。
  ```sh
  oxigraph serve-read-only --location <店> --bind 127.0.0.1:7878 --cors
  python3 -m http.server 8765 --bind 127.0.0.1    # http://127.0.0.1:8765/view.html
  ```

## SPARQL サーバー

Oxigraph を読むだけのサーバーとして Cloud Run で動かしていて、だれでも引けます(`deploy/`、手順は [deploy.md](deploy.md))。

- 行き先: `https://jp-procedure-sparql-5psr6o4zja-an.a.run.app/query`(GET か POST。`query=` に SPARQL)
- 読むだけです。書き込みは断ります。
- 小さく動かしています: 最大 1 台(引かれないときは 0 台)、1 vCPU・1 GiB、要求は 30 秒まで、1 つの問いは 20 秒まで。0 台からの最初の答えは、2026-11-20 に測ったとき約 1 秒でした。重い問いを続けて投げると、待たされたり断られたりします。
- まとめて使うときは、データのファイル(`data/`)を使ってください。

## ライセンス

- データ(`data/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)。詳しくは [LICENSE-DATA.md](LICENSE-DATA.md)。
- コード(`scripts/`、`queries/`、`shapes/`、`.github/`): [MIT](LICENSE)

## 出典の表示

このデータは、次のデータを加工して作成しました。作成したのは橋本一輝で、国・デジタル庁が作成したものではありません。

- 「行政手続等の棚卸調査結果」(デジタル庁)(<https://www.digital.go.jp/resources/procedures-survey-results>)を加工して作成
- 「行政手続等の悉皆調査結果」(デジタル庁)(<https://www.digital.go.jp/resources/procedures-survey-results>)を加工して作成
- 出典:e-Gov法令検索(<https://laws.e-gov.go.jp/>)(2026年11月18日に利用)。法令API Version 2(<https://laws.e-gov.go.jp/api/2/>)で取得した法令データを加工して作成

元のデータの利用条件は、次のページで確かめました。

- デジタル庁のコンテンツは「公共データ利用規約(第1.0版)」(PDL1.0)が適用され、編集・加工した場合は、出典とは別に、加工したことと加工した者を書くこと(<https://www.digital.go.jp/copyright-policy>)
- e-Gov(e-gov.go.jp とそのサブドメイン)のコンテンツにも PDL1.0 が適用され、出典の書き方の例が示されていること(<https://www.e-gov.go.jp/terms>)
- PDL1.0 は CC BY 4.0 と互換性があること(<https://www.digital.go.jp/resources/open_data/public_data_license_v1.0>)
