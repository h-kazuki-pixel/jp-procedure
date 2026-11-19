# push の前の直しの報告(2026-11-19)

指示の A1・A2・B1〜B6・D を行い、点検を全部通し直して、Cloud Run も入れ替えた(認証つきのまま)。push はしていない。

## A1. 「人が確かめた」の書き方を事実に合わせた

**事実(指示で受け取ったもの)**
- 抜き取り(`review-sample.csv` の 80 行)と境目(`review-boundary-06.csv` の 30 行、`review-moves-090-095.csv` の 43 行)を読んだのは、作った Claude Code とは別の AI(別の会話の Claude)。
- e-Gov の本文(法令API)と照らしたのは 80 行のうち 11 行。10 行が一致し、1 行は取得に失敗した。
- 3 件の区分を「判定できない」にしたのも、その別の AI の読み。
- 作った人は、まだ行を読んでいない。

**データ**
- `jpp:humanReviewed`・`jpp:humanReviewDate`・`jpp:humanReviewReason` を、次の 4 つに変えた(`scripts/61_build_changes.py`)。
  - `jpp:reviewed`
  - `jpp:reviewerType`
  - `jpp:reviewDate`
  - `jpp:reviewReason`
- `jpp:reviewerType` のコード表 `code/reviewer-type` を新しく作った。中身は `other-ai`(別の AI)と `human`(人)。
- 3 件はすべて「別の AI」。
- 作り直す前と比べて、変わったのは次の所だけ。
  - 改正の記録: 3 件の性質の名前、コード表(概念 2 つと体系 1 つ)
  - 語彙: 性質の名前と説明、「(仮)」を取ったこと
  - 作成の時刻

**合わせて直した所**

| 所 | 直したこと |
|---|---|
| 語彙(`50_build_rdf.py` → `vocab.ttl.gz`) | 4 つの性質の名前と説明。`reviewerType` はコード表を指すと書いた |
| SHACL(`shapes/shapes.ttl`) | 改正の記録の形: `reviewed` があれば `reviewerType`・`reviewDate`・`reviewReason` が要る。`reviewerType` は 2 つのコードのどちらか |
| CSV(`data/csv/changes.csv`) | 列 `human_review_date`・`human_review_reason` を `reviewer_type`・`review_date`・`review_reason` にした(3 行に値) |
| 閲覧ページ | 「機械の判定のままでなく、別の AI(作った Claude Code とは別の会話の Claude)が読んで区分を決めた記録です」と出す |
| README の「作り方」 | 区分の行を読んだのは別の AI で、作った人はまだ読んでいないと書いた |
| README の「点検の分担」の表 | 抜き取り・境目を「別の AI」に直し、e-Gov と照らしたのは 11 行(10 一致、1 取得失敗)と書いた。決まりの直しは「作った人が指示し、Claude Code が決まりを書き、機械が当てる」にした。「人の抜き取り」(D のまとめ)を足し、人はまだ読んでいないと書いた |
| README の「確かめ方」 | 抜き取りの行を、同じ事実に直した |
| README の「元のデータから変えた点」 | 伏せる所を決めたのは Claude Code で、作った人はまだ見ていないと直した |
| `scripts/README.md` | 3 件は別の AI の読みと書いた。作業の列の名前は「人の確認」のままだと注記した |
| `scripts/42_fix_rules.py` | 節の見出しの注釈を直した(列の名前と動きは変えていない) |

**報告(`reports/`)の中の言い方**

公開用の reports/(作業フォルダの元の報告)を「人が確かめ」「人の確認」「人が見」「人が区分」「人が決め」「人が読」などで探した。

| 報告 | 当たった行 | したこと |
|---|---:|---|
| fix-report-2.md | 7 | 先頭に訂正の注記を足した(本文はそのまま) |
| fix-report-3.md | 2 | 同上 |
| fix-report-4.md | 2 | 同上 |
| fix-report-5.md | 2 | 同上 |
| rdf-report-4.md | 7 | 同上 |
| view-report.md | 3 | 同上 |
| fix-report.md | 1(「人が見る用」) | 直していない。ファイルがだれ向けかの言い方で、だれが確かめたかではないため |
| sparql-host-report.md | 1(「人が見るとき(HTML)」) | 直していない。ブラウザでの転送の説明のため |
| redact-report.md | 1(「人(このセッションの中)が見て決めた」) | 本文を直した。決めたのは Claude Code で、作った人はまだ見ていない。この報告は今の作業の記録なので、注記でなく本文で直した |

## A2. はじめの画面

- 一番上の見出しを「法令が改正されたとき、根拠の条文が本当に変わった手続だけが分かります」にした。
- 15.3 倍の札を、次の文に言い換えた。数は `stats.json` から読み、元の問いへのリンクを付けた。
  - 「この期間に、根拠の法令に改正があった手続は **47,352**。そのうち、根拠の条文そのものの文言が変わったのは **3,090**(約 15 分の 1)。」
  - 「15」は、ページの中で 47,352 ÷ 3,090 を丸めた数。
- 例を 1 つ置いた。
  - 手続ID 119637 の、旧い文言と新しい文言の違う所の前後だけを、小さな札で見せる(「…書面その他<del>内閣府</del><ins>防災庁</ins>令で定める書面…」)。
  - 押すと手続のページへ行く。
  - 例は 1 件の軽い問いで出す(`CONFIG.example`)。
- 入口を 3 つ置いた。
  - 変わった手続の一覧(新しく作った)
  - 府省庁ごと
  - 条文から探す
- 「重」の字は、ページに 0 回。コードの注釈の「重い問い」も「時間のかかる問い」に直した。

**変わった手続の一覧(`#/changed`)**
- 比べた期間の 3,090 行を、1 回の問いで読む。
- 区分・府省庁(どちらも件数つき)・手続名の一部で絞れる。100 件ずつのページにした。
- 区分「入れ替わった→移った」で絞ると 367 件(全 3,090 件)。区分ごとの数と同じ。

**画面の写し**(`out/view_shots3/`。手元の Oxigraph につないだもの)

| 画面 | パソコン(1280 px) | スマホ(390 px) |
|---|---|---|
| はじめ | `local_home_pc.png` | `local_home_sp.png` |
| 変わった手続の一覧 | `local_changed_pc.png` | `local_changed_sp.png` |
| 一覧(入れ替わった→移った で絞った) | `local_changed_moved_pc.png` | `local_changed_moved_sp.png` |
| 別の AI が区分を決めた手続(112875) | `local_p112875_pc.png` | `local_p112875_sp.png` |
| 手続ID 119637 | `local_p119637_pc.png` | `local_p119637_sp.png` |

- どの画面も、スマホの幅で横にはみ出さなかった。
- 一覧の区分の札が、パソコンの幅で細い列に折れて丸く見えたので、折り返さないようにして撮り直した。

## B. 公開の前の直し

### B1. w3id の .htaccess

- 書き直した。転送先は次の表のとおり。
- 手元の Apache 2.4.62(`/usr/sbin/httpd`)に、この `.htaccess` を置いて確かめた。前回「試していない」と書いた百分率符号も、ここで確かめた。

| 引いたもの | Accept | 転送 |
|---|---|---|
| `procedure/119637` | text/html(ブラウザ) | 303 → `view.html?uri=https://w3id.org/jp-procedure/procedure/119637` |
| `procedure/119637` | text/turtle・application/ld+json・`*/*`・Accept なし | 303 → `https://CLOUD_RUN_HOST/query?query=DESCRIBE%20%3Chttps://w3id.org/jp-procedure/procedure/119637%3E` |
| `provision/…`・`change/…`・`record/…`・`organisation/…`・`code/…`(`*/*` など) | | 同じく DESCRIBE へ 303 |
| `law/…` | text/html | view.html へ 303 |
| `def` | どれでも | 303 → `https://h-kazuki-pixel.github.io/jp-procedure/vocab.ttl` |
| 一番上・`period/…` など | | GitHub Pages へ 302 |

- 転送先の `CLOUD_RUN_HOST` を手元の Oxigraph に置き換えて、最後までたどった。

| Accept | 返ったもの |
|---|---|
| `*/*` | 200 `application/n-quads` |
| `text/turtle` | 200 `text/turtle` |
| `application/ld+json` | 200 `application/ld+json` |

- **Accept が `*/*` のとき、Oxigraph は Turtle でなく N-Quads を返す。**
  - DESCRIBE の結果にはグラフの名前が無いので、中身は N-Triples の形(Turtle の文法でも読める)。ただし Content-Type は `application/n-quads`。
  - Oxigraph 0.5.13 のサーバーには、URL で形を決める引数が無かった(`format=` を 4 通り試して、どれも効かなかった)。
- `def` の転送先として、語彙を gzip でないまま `vocab.ttl`(リポジトリの一番上)に置くようにした(80)。

### B2〜B6

- **B2:** README の「言えること・言えないこと」に書いた。
  - URI を機械が引いたときの行き先は Cloud Run で、止めると引けなくなる。
  - 閲覧ページも Cloud Run に問い合わせる。
  - データのファイルは止めても使える。
  - `deploy.md` に「止めるとき」の節を足した。`.htaccess` の DESCRIBE の行を一括ダウンロードの案内(README の「ファイル」の節)へ直す行・確かめ方・止めるコマンド・`DEPLOY_ENABLED` を書いた。
- **B3:** README のはじめに「何の役に立つか」を 4 行足した。
  - 府省庁・自治体で手続を受け持つ人
  - 手続を案内する人や事業者
  - 研究や報道
  - 機械
- **B4:** `62_oxigraph_load.py <RDF の場所> <店の場所>`、`63_queries.py <店の場所> <問いの場所>` で、場所を引数で受けるようにした。README の使い方と `scripts/README.md` を直した。
- **B5:** 語彙の名前を「行政手続LOD の独自の語彙」にした(「(仮)」を取った)。`rdf_config.py` の基点の注釈の「仮」も直した。公開用のフォルダで「(仮)」は、報告の外では 0。
- **B6:** 報告の中の英語の段落を探した(英字が 40 字以上で、かなと漢字が英字の 1 割以下の行。コードの囲みと表は除いた)。
  - 当たったのは 2 行で、どちらも `settings-report.md` の中の字下げしたコードの囲みの中(gcloud の条件と principal の値)だった。
  - 英語の文の段落は 0。README の先頭の英語の要約は、報告の外。

## D. 人の抜き取り用のまとめ

`scripts/78_make_human_check.py`(と、HTML のひな形 `scripts/human_check_template.html`)で作り、公開用の `reports/review/` に写した。

| ファイル | 大きさ | 中身 |
|---|---:|---|
| `human-check.csv` | 61,451 バイト | 23 行 × 16 列(UTF-8、BOM 付き) |
| `human-check.html` | 155,827 バイト | 手元で開いて使う 1 枚のページ(外のサイトは読まない) |

**入れた行**
- 別の AI が区分を決めた 3 行(手続ID 112873・112875・59390)。
- 抜き取り 20 行。固定の種は 20261119。`review-sample.csv` の手続と、上の 3 行の手続は除いた(除いたのは 83 手続)。
  - 文言が変わった 10(「番号の参照だけ」と「それ以外」から)
  - 移った 5(「入れ替わった→移った」と「無くなった→移った」から)
  - 移った先なし 5(「入れ替わった→移った先なし」と「無くなった→移った先なし」から)

**1 行ごとに入れたもの**
- 選んだ理由・手続名・所管・法令名・条項号・区分
- 旧い文言・新しい文言
  - 違う所に、CSV では〔-…-〕〔+…+〕、HTML では取り消し線と下線で印を付けた。
  - 「移った」は、移った先の文言と比べる。
- 移った先
- e-Gov の法令のページへのリンク
- 「合う/合わない/分からない」とメモの欄

**HTML の使い方**
- 選んだ結果とメモは、そのブラウザの中だけに残る(localStorage。使えないときは残らないだけで、動きは同じ)。
- 「CSV で書き出す」で、判定とメモの列を埋めた CSV(`human-check-result.csv`)を保存する。
- JavaScript の文法は node で確かめた。ボタンを押して書き出すところは、まだ試していない。

## 点検を全部通し直した

| 確かめ | 結果 | メモリの最大(1 回ごとの最大) |
|---|---|---|
| 50(語彙) | 書き直した | 328 MB |
| 61(改正の記録) | 48,012 トリプル | 293 MB |
| 自作 SHACL | 45 回、違反 0 件 | 1,356 MB |
| 公式 CPSV-AP 3.2.0 SHACL | 28 回、違反 0 件 | 368 MB |
| 店への読み込み(62) | 4,423,248 個(前より 15 多い。コード表と性質の名前の変化) | 1,037 MB |
| stats.json(75) | 76,275 / 2,064 / 3,090 / 47,352(前と同じ) | 82 MB |
| 全体の数(57、stats.json と比べる) | 54 項目すべて OK | 671 MB |

**公開用のフォルダ**
- 80 を 2 回続けて流し、2 回とも同じ 132 ファイルになった。
- 81 で、gzip 21 個の中まで探した。プロジェクト ID・番号・手元のパス・メールアドレス・公開しない文字列は、どれも 0。
- `humanReview` という名前は、データ・形・閲覧ページのどれにも残っていない(0)。

## Cloud Run の入れ替え

- イメージ `sparql:20261119d` を Cloud Build で作り(2 分 9 秒)、リビジョン `jp-procedure-sparql-00005-sbh` に入れ替えた。
  - 認証つきのまま。サービスの IAM は、入れ替え用のアカウントの `roles/run.developer` だけ。
- 確かめたこと(`out/68_cloudrun_prepush.txt`)
  - 認証なしは 403。
  - トリプルは 4,423,248(手元と同じ)。
  - 区分を確かめて決めた記録は「別の AI」3 件。前の名前(`humanReviewed` など)のトリプルは 0。
- 前のリビジョン `00004-mvz`・イメージ `20261119c`・Cloud Build に送った前の圧縮ファイルを消した。残りはそれぞれ 1 つずつ。

## 決めていただきたいこと

- **Accept が `*/*` のときの形:** Turtle でなく N-Quads(中身は Turtle でも読める N-Triples の形、Content-Type は `application/n-quads`)が返ります。どうするか。
  - このままにする(README に書く)。
  - Cloud Run の中で、Oxigraph の前に Accept を書き換える小さなものを置いて、Turtle を返す。
- **human-check の置き場所:** `human-check.csv`・`.html` を、公開用の `reports/review/` に置きました。公開するか、手元だけにするか。
