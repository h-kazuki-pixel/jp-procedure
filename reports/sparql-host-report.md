# 行政手続LOD SPARQL サーバーの準備

- 数字は次の出力から写した。
  - `out/66_check_versions.txt`
  - `out/67_server_bench.txt`、`out/67_server_bench_cliload.txt`、`out/68_store_sizes.txt`
  - `out/56_split_synth.txt`、`out/59_shacl_synth.txt`、`out/57_count_synth.txt`
  - `out/59_shacl_test.txt`、`out/59_shacl_testbad.txt`
- e-Gov 法令API への取得はしていない。
- ネットに取りに行ったのは、公式の説明のページと、Oxigraph CLI 0.5.13 の導入(PyPI)、公式イメージのレジストリの情報だけ(`data/terms/`、記録は `data/terms/fetched.txt`)。
- 公開用のリポジトリ(``)に、次を足した・直した。
  - 足した: `deploy/Dockerfile`、`deploy/cloudbuild.yaml`、`.gcloudignore`、`deploy.md`
  - 直した: `w3id/.htaccess`、`w3id/README.md`、`.github/workflows/weekly-track.yml`、`shapes/shapes.ttl`、スクリプト 56・57・59・62 と、足した 66・67

## 0. 前回の問いへの答え

### 0.1 版の URI は `/version/{版のID}` のまま

**版の ID は、e-Gov の「法令履歴ID」(`law_revision_id`)。**

- e-Gov の説明(「法令の改正と履歴」<https://laws.e-gov.go.jp/docs/law-data-basic/da91fe9-law-revisions/>)によると、法令履歴ID は「法令ID に、どの時点の改正版(リビジョン)かの情報を付加したもの」。形は `[法令ID]_YYYYMMDD_[改正法令の法令ID]` で、YYYYMMDD は改正規定の施行期日。
- 改正法令の法令ID が `000000000000000` になるのは、次の 2 つの場合。
  - 法令が最初に公布されたときの版(YYYYMMDD は法令の施行期日)
  - データ整備のときに、基準日の時点の版を入れた場合(YYYYMMDD は基準日)
- 法令API v2 の仕様書(`data/api/spec/lawapi-v2.yaml`)でも、`law_revision_id` は「法令履歴ID」と書かれている。

**すべての版に施行日があることを確かめた**(`scripts/66_check_versions.py`):

| | 版 |
|---|---:|
| 版(eli:LegalExpression) | 90,970 |
| 施行日(eli:version_date)がある | **90,970** |
| URI の末尾が版の ID と同じ | 90,970 |
| 版の ID が `法令ID_YYYYMMDD_改正法令ID` の形 | 90,970 |
| 施行日 = 版の ID の YYYYMMDD | 90,970 |
| 改正履歴(`out/law_revisions.csv`)にある | 90,970 |
| 改正法令ID が `000000000000000`(制定時か基準日) | 1,360 |

- 改正法令ID が `000000000000000` の 1,360 版では、YYYYMMDD は施行期日か基準日のどちらか。どちらなのかは版ごとに見分けていない。
  - 施行日(eli:version_date)は改正履歴の `amendment_enforcement_date` から入れていて、それが ID の YYYYMMDD とすべて同じだった。基準日の版では、施行日として基準日が入っている。

### 0.2 毎週の追跡は main へ直接入れる(確かめが通ったときだけ)

ワークフロー(`.github/workflows/weekly-track.yml`)を、次の順に直した。**まだ動かしていない。**

1. 追跡する(前と同じ)。
2. 足した記録があれば、確かめを 3 つ通す。
   - 自作 SHACL と公式 CPSV-AP SHACL(`59_shacl_split.py full`。違反があれば 2 で終わる)
   - 全体の数(`57_count_checks.py`。合わない項目があれば 3 で終わる)
   - 公式 SHACL は、毎回 SEMIC の URL から取る。
3. **確かめが通らなければ、main には入れず、Issue「毎週の追跡: 確かめが通らなかった」を立てる。**
4. 通ったら main に push する。
5. **足した記録がある週は、その週の差分(`data/rdf/weekly/changes_…_{終わりの日}.ttl.gz` と `last_run.json`)を Release `weekly-{日付}` に出す。** 足した記録が 0 の週は、Release を出さない。
6. Cloud Run を入れ替える(6 節)。
7. 2 週続けて失敗したら Issue を立てる(前と同じ)。

**週ごとの記録が入っても確かめが通るように、直したこと:**

- **点検のスクリプトが `data/rdf/weekly/` も読むようにした。**
  - データの場所は環境変数 `RDF_DIR` で変えられる。
  - 週ごとの版と「条・項・号 → 版」の線は、本文の版の回へ回すようにした。
- **形(`shapes/shapes.ttl`)から、週ごとに増えると引っかかる上限を外した。**
  - 版の確かめた日(jpp:asOf)の「2 つまで」
  - 条・項・号の版の数の「2 つまで」
  - 期間内の改正の施行期日の幅(2025-11-01〜2026-11-18)。この幅は、全体の数の確かめで「その記録の期間の中にあるか」として確かめる。
- **全体の数の確かめを、2 つに分けた。**
  - 2025-11-01〜2026-11-18 の分: 今までの数(2,064 件、3,090 行など)
  - 週ごとの分: 一般の決まり。手続への線、同じ期間に同じ手続が 2 回出ないこと、旧・新の版が期間の始め・終わりの版であること、改正の施行期日が期間の中にあること
- 直す前の形は `out/shapes_v5_before_weekly.ttl.txt`。

**確かめたこと:**

- 作り直しの確かめで出た 17 件を、期間 2026-11-18〜2026-11-25 の記録に書き換えた作り物を作り、データに足して全件の確かめを通した。
  - 自作 SHACL: 45 回で違反 0 件
  - 公式 SHACL: 28 回で違反 0 件
  - 全体の数: 53 項目すべて合った(週ごとの分 8 項目を含む)
  - 1 回のメモリの最大は、自作 1,383 MB、公式 385 MB
- 1 回目は違反が 34 件出た(`out/59_shacl_synth_run1.txt`)。
  - 週ごとのファイルにある「条・項・号 → 版」の線が改正の記録の回に入り、その条・項・号が、本体(is_part_of など)の無い回で調べられたため。
  - 切り分けの穴なので、それを直した。
  - 同じ 1 回目では、全体の数の確かめが名前の重なりの誤りで止まった(`out/57_count_synth_run1.txt`)。データの場所に付けた名前を、rdflib の `RDF` と重ならないものに直した。
- 切り分けを変えたので、手続 2,000 件でまとめて通す・分けて通すの比べもやり直した。
  - 壊していないデータ: 自作・公式とも 0 件で同じ
  - 壊した 10 か所: 自作 10 件・公式 1 件で、1 件ずつ同じ

### 0.3 w3id の連絡先にメールアドレスは必須か

**必須ではない。必須なのは GitHub のユーザー名。**

- w3id の決まり `meta/maintainer-github-username`(<https://raw.githubusercontent.com/perma-id/w3id.org/master/docs/rules/meta/maintainer-github-username.md>)には、次のことが書かれている。
  - どの識別子にも、管理する人の記録と、少なくとも 1 つの GitHub ユーザー名が要る。
  - 理由として「メールアドレスだけでは、pull request を出したアカウントに変更の権利があるかを確かめられない」とある。
- 手順の説明(<https://raw.githubusercontent.com/perma-id/w3id.org/master/docs/guides/create-an-id.md>)の例には、名前とメールアドレスも書かれている。ただし決まりとしては求められていない。README では「メールアドレスと GitHub のユーザー名は、名前で始まる項目の中に入れ子にする」ことが勧められている。
- 下書きには、メールアドレスを入れていない。

## 1. Oxigraph を「読むだけ」のサーバーとして動かす方法

- **Oxigraph CLI に `serve-read-only` がある。** `oxigraph serve-read-only --location <店> --bind <ホスト:ポート>` で動く。
- 確かめたところ
  - Oxigraph CLI 0.5.13 の `oxigraph --help` と `oxigraph serve-read-only --help`(PyPI の `oxigraph` パッケージ、<https://pypi.org/project/oxigraph/>)。`--help` には「Start Oxigraph HTTP server in read-only mode」と出る。
  - 同じ版のソース(<https://raw.githubusercontent.com/oxigraph/oxigraph/v0.5.13/cli/src/main.rs>)。`ServeReadOnly` は店を `Store::open_read_only` で開き、書き込みの要求には 403「The server is read-only」を返す。
  - CLI の説明(<https://raw.githubusercontent.com/oxigraph/oxigraph/main/cli/README.md>)。問いは `/query`(SPARQL 1.1 Protocol)で受ける。公式の Docker イメージは `ghcr.io/oxigraph/oxigraph`。
- 選べる指定は `--cors`、`--union-default-graph`、`--timeout-s`(1 つの問いの上限の秒数)。
- `oxigraph load` は `.gz` のファイルをそのまま読める(ソースの `MultiGzDecoder`)。

## 2. 手元でサーバーを立てて測った

- 測り方
  - Oxigraph CLI 0.5.13 で、pyoxigraph 0.5.13 が作った店(`store/oxigraph`、663 MB)を `serve-read-only` で開いた(`scripts/67_server_bench.py`)。
  - 機械は Apple シリコンの Mac(arm64、メモリ 8 GB)。
  - 時間は、同じ要求を 2 回送った 1 回目と 2 回目。

**立ち上がってから最初の答えまで**(`ASK {}` が返るまで。3 回):

| 回 | 秒 | メモリの最大 |
|---|---:|---:|
| 1 | 0.042 | 20 MB |
| 2 | 0.023 | 20 MB |
| 3 | 0.026 | (下の問いを回したあと 60 MB) |

**4 つの問い**(結果は SPARQL の JSON):

| 問い | 1 回目 | 2 回目 | 結果 |
|---|---:|---:|---:|
| q1 ある条文を根拠にする手続 | 0.032 秒 | 0.002 秒 | 19 件 |
| q2 区分ごとの数 | 0.328 秒 | 0.027 秒 | 10 件 |
| q3 府省庁ごとの数と割合 | 0.886 秒 | 0.538 秒 | 25 件 |
| q4 旧い文言と新しい文言 | 0.027 秒 | 0.020 秒 | 2 件 |

**DESCRIBE:**

| 引いたもの | 形 | 1 回目 | 2 回目 | 返った型 | 大きさ | トリプル |
|---|---|---:|---:|---|---:|---:|
| 手続 56737 | Turtle | 0.002 秒 | 0.000 秒 | text/turtle | 766 バイト | 7 |
| 手続 56737 | JSON-LD | 0.001 秒 | 0.000 秒 | application/ld+json | 910 バイト | 7 |
| 条 関税法 第62条の15 | Turtle | 0.001 秒 | 0.000 秒 | text/turtle | 734 バイト | 7 |
| 条 関税法 第62条の15 | JSON-LD | 0.000 秒 | 0.000 秒 | application/ld+json | 860 バイト | 7 |
| 改正の記録 地方自治法 第243条の2の8第8項 | Turtle | 0.004 秒 | 0.000 秒 | text/turtle | 2,971 バイト | 27 |
| 改正の記録 地方自治法 第243条の2の8第8項 | JSON-LD | 0.000 秒 | 0.000 秒 | application/ld+json | 3,211 バイト | 27 |

- DESCRIBE は、その URI を主語とするトリプルを返した。
  - 手続では、題名・所管・説明・根拠・記載への線の 7 つ。
  - 記載の中身(照合の結果など)は、別の URI(`/record/r7/56737/citation`)を引かないと出ない。
- Accept に合わせて、Turtle と JSON-LD が返った。

**メモリの最大**(`/usr/bin/time -l` の maximum resident set size):

- 問いを回したあとで 60 MB、立ち上げただけでは 20 MB。
- macOS では、店のファイルの読み込みは OS のファイルの一時置き場(ページキャッシュ)に乗り、この値には入らない。また、店のファイルは前の作業で読んだばかりだった。どちらも、Cloud Run での値とは違いうる。

**CLI の `oxigraph load` で作った店でも測った**(`out/67_server_bench_cliload.txt`、`out/68_store_sizes.txt`):

| 店 | 大きさ | q3 の 1 回目 | 作るのにかかった時間 |
|---|---:|---:|---|
| pyoxigraph で作り optimize した店(上の測定) | 663,252,992 バイト | 0.886 秒 | 15.5 秒(pyoxigraph、optimize を含む) |
| CLI の load だけ(optimize なし) | 465,518,592〜493,346,816 バイト | 1.315 秒 | 24.10 秒(メモリの最大 1,430 MB) |
| CLI の load のあと optimize | 663,445,504 バイト | (測っていない) | optimize 1.54 秒 |

- optimize をしないと店は小さいが、q3 は遅かった。
- optimize をしない店の大きさは、作るたびに少し違った(465,518,592 と 493,346,816)。
- Dockerfile では optimize をする形にした。

## 3. Cloud Run で動かすための形

**手元に Docker は無い**(`docker` コマンドが無い)。そのため、イメージは作っていない。イメージの大きさも、Cloud Run での立ち上がりの秒数も、測っていない。測れたものと公式の説明から比べた。

**公式のイメージ `ghcr.io/oxigraph/oxigraph:0.5.13`(linux/amd64):**

- 層は 19 で、圧縮した大きさの和は 17,603,337 バイト(レジストリの manifest から)。
- build の記録(イメージの history)を見ると、シェルを入れていない。ENTRYPOINT は `/usr/local/bin/oxigraph`、CMD は `serve --location /data --bind 0.0.0.0:7878`。

| | A. 中身をイメージに入れる(`deploy/Dockerfile`) | B. 外の置き場所(Cloud Storage)から読む |
|---|---|---|
| イメージの大きさ | 公式イメージ(圧縮 17.6 MB)+ 店 663 MB(展開時)。店を gzip -1 にすると 287,823,662 バイト(手元で測った)なので、送る大きさはおよそ 0.3 GB と見ている(イメージは作っていない) | 公式イメージのまま(圧縮 17.6 MB) |
| 立ち上がり | 店はイメージの中にあり、開くだけ。手元では開いて最初に答えるまで 0.02〜0.04 秒。Cloud Run がイメージを取る時間は測っていない | (1) Cloud Storage を volume としてつなぐ形と、(2) 立ち上がりのときに店を写して開く形がある。(2) では、手元で tar.gz を展開するのに 1.1 秒、作るのに 7.1 秒。Cloud Storage から 288 MB を取る時間は測っていない |
| メモリ(1 GiB) | 店はイメージの中のファイルとして読むだけ。イメージの中のファイルを読むことがメモリに数えられるかは、公式の説明に書かれていない(デプロイのあとに測る) | (2) は写した 663 MB が、メモリの上のファイルシステムに乗る。公式の説明に「書き込むとインスタンスのメモリを使う」とあり(<https://cloud.google.com/run/docs/container-contract>)、1 GiB の 6 割強を使う |
| 動きの確かさ | ふつうのファイルとして RocksDB が開く | (1) は Cloud Storage FUSE で、「完全には POSIX に沿わない」「ファイルの鍵(ロック)の制御が無い」と書かれている(<https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts>)。RocksDB が細かく読むときの速さも分からない |
| データの入れ替え | イメージを作り直す(Cloud Build で、送るのは約 19.5 MB。店はその中で作る) | 置き場所のファイルを入れ替え、立ち上げ直す |

**A を選んだ。** 理由は 3 つ。

- 店を開くまでが手元で 0.04 秒以内で、外から取ってくる時間が要らない。
- B の (2) は 1 GiB のメモリの多くを店の写しに使う。B の (1) は、公式の説明に RocksDB に合わないかもしれない点が書かれている。
- 毎週の入れ替えも、イメージの作り直しで済む。

イメージが 0.3 GB ほどになるので、Cloud Run がそれを取る時間で、0 台からの立ち上がりが遅くなるかもしれない。デプロイのあとに測る。

**作ったファイル(公開用のリポジトリ):**

- **`deploy/Dockerfile`**
  - 1 段目(debian:bookworm-slim に公式イメージの oxigraph を写したもの)で、`data/rdf` と `data/rdf/weekly` の Turtle を `oxigraph load` し、`oxigraph optimize` する。
  - 2 段目(公式イメージ)には、店だけを写す。
  - 起動は `serve-read-only --location /data --bind 0.0.0.0:8080 --timeout-s 20`。
  - **一度も build していない。** 1 段目で oxigraph が動くのに要るライブラリ(libgomp1、libssl3)は、公式イメージの作りから見当を付けたもの。
- **`deploy/cloudbuild.yaml`**: Cloud Build で Dockerfile を build し、Artifact Registry に置く。
- **`.gcloudignore`**: Cloud Build に送るのを `deploy/` と `data/rdf/` だけにする。

## 4. w3id の .htaccess の下書き(`w3id/.htaccess`)

中身の交渉の書き方は、w3id の説明(<https://raw.githubusercontent.com/perma-id/w3id.org/master/docs/guides/content-negotiation.md>)に合わせた。

- 細かい条件を上に、条件の無い既定を一番下に置く。
- 文書へ転送するときは 303 を使う。
- `+` は `\+` と書く。

```apache
RewriteEngine on

# 人が見るとき(HTML)
RewriteCond %{HTTP_ACCEPT} text/html [OR]
RewriteCond %{HTTP_ACCEPT} application/xhtml\+xml
RewriteRule ^(.+)$ https://h-kazuki-pixel.github.io/jp-procedure/view.html?uri=https://w3id.org/jp-procedure/$1 [R=303,L,NE]

# 機械が読むとき(Turtle)
RewriteCond %{HTTP_ACCEPT} text/turtle
RewriteRule "^(.+)$" "https://CLOUD_RUN_HOST/query?query=DESCRIBE <https://w3id.org/jp-procedure/$1>" [R=303,L]

# 機械が読むとき(JSON-LD)
RewriteCond %{HTTP_ACCEPT} application/ld\+json
RewriteRule "^(.+)$" "https://CLOUD_RUN_HOST/query?query=DESCRIBE <https://w3id.org/jp-procedure/$1>" [R=303,L]

# それ以外
RewriteRule ^(.*)$ https://h-kazuki-pixel.github.io/jp-procedure/$1 [R=302,L]
```

- `CLOUD_RUN_HOST` は仮の置き換え文字。デプロイのあとに Cloud Run の URL のホスト名にする。
- 転送された機械は、同じ Accept で Cloud Run に問い合わせる。2 節のとおり、Oxigraph は Accept に合わせて Turtle か JSON-LD を返す。
- **DESCRIBE の問いの空白と `<`・`>` の書き方は、まだ試していない。**
  - 置き換え文字の中に `%3C` のように書くと、`%3` が RewriteCond の後方参照(`%N`)として読まれるおそれがある(Apache の説明 <https://httpd.apache.org/docs/2.4/mod/mod_rewrite.html>)。そのため、文字をそのまま書き、置き換え文字を引用符で囲んだ。
  - Apache の説明(<https://httpd.apache.org/docs/2.4/rewrite/flags.html>)には、外への転送では安全な文字以外を百分率符号にする、`[NE]` を付けるとそれをしない、と書かれている。DESCRIBE の 2 行には `[NE]` を付けていない。
  - 問い合わせ文字列(`?` より後)まで百分率符号になるかは確かめていない。
  - w3id の点検の道具(`tools/check`)と、手元の Apache(`tools/server`)で試してから出す必要がある。
- HTML の行の `view.html?uri=…` には `%` を含めていないので、`[NE]` を付けた。
- **公開の日までは Cloud Run が認証つきなので、機械向けの転送先は 403 を返す。**

## 5. デプロイの手順書(`deploy.md`)

公開用のリポジトリの一番上に書いた。

| 項目 | 値 |
|---|---|
| 地域 | asia-northeast1 |
| 台数 | 最小 0 台・最大 1 台 |
| CPU・メモリ | 1 vCPU・1 GiB |
| ポート | 8080 |
| 要求の時間の上限 | 30 秒(`--timeout 30`) |
| 1 つの問いの上限 | 20 秒(Oxigraph の `--timeout-s 20`) |
| 認証 | 認証つき(`--no-allow-unauthenticated`)。公開の日まで |

- **要求の時間の上限の決め方:**
  - 2 節で最も重い問い(q3)が 0.886 秒、optimize をしない店では 1.315 秒だった。
  - Cloud Run の 1 vCPU で何倍遅くなるかは分からないので、10 倍でも収まる 20 秒で問いを打ち切り、要求全体は 30 秒にした。Cloud Run の既定は 5 分(<https://cloud.google.com/run/docs/configuring/request-timeout>)。
  - デプロイのあとに測り直して見直す。
- **持ち主が手で行うこと:**
  1. プロジェクトを作る
  2. 支払いを有効にする
  3. 予算の知らせを月 500 円で付ける。止める仕組みではないことも書いた。
  4. gcloud を入れて `gcloud auth login` する
- **そのあと Claude Code が行うこと:**
  1. API を有効にする
  2. Artifact Registry を作る
  3. Cloud Build でイメージを作る
  4. Cloud Run に認証つきでデプロイする
  5. 立ち上がり・問い・DESCRIBE を測る
  6. 毎週の入れ替えのためのサービスアカウントと、Workload Identity 連携を作る(持ち主が良いと言ってから)
- コマンドは、行う前に公式の説明で確かめ直す、と書いた。費用は確かめていない。

## 6. 毎週の追跡に、Cloud Run を入れ替える段を足した(まだ動かさない)

ワークフローに `deploy` のジョブを足した。

- **動く条件:** 追跡のジョブが確かめを通して main に push したときで、かつリポジトリの変数 `DEPLOY_ENABLED` が `true` のとき。
- **やること:**
  - Workload Identity 連携で Google Cloud に入る(`google-github-actions/auth@v2`。鍵のファイルは使わない)。
  - `gcloud builds submit` でイメージを作り直す。
  - `gcloud run deploy` で入れ替える。設定は 5 節と同じ。
- **要るもの:** Secrets の `GCP_WIF_PROVIDER`・`GCP_SERVICE_ACCOUNT` と、Variables の `GCP_PROJECT_ID`。まだ作っていない。
- `deploy` が失敗したときも、2 週続けての失敗の数に入る。

## 7. 分からないこと・決めていないこと

- **Docker が無いので、測れなかったものがある。**
  - Dockerfile は一度も build していない。
  - イメージの大きさ、Cloud Run での立ち上がりの秒数、Cloud Run の 1 vCPU での問いの時間とメモリは、デプロイのあとに測る。
- **手元のメモリの値(60 MB)は、Cloud Run での値と違いうる。** macOS のページキャッシュに乗った分は入っていない。
- **w3id の DESCRIBE の転送は、まだ試していない。** 空白と `<`・`>` が百分率符号にされるかが分からない(4 節)。
- **週ごとの記録を入れた確かめは、作り物のデータでしか通していない。** 本当の週ごとの記録は、追跡を動かしたときに初めて出る。
- **手続 2,000 件の比べ(まとめて・分けて)には、週ごとの記録が入っていない。** その 2,000 件の法令に、作り物の 17 件の法令が入っていないため。週ごとの記録を含む比べはしていない。
- **Release は、足した記録が 0 の週には出さない形にした。** 毎週必ず出すかは決めていない。
- **費用は確かめていない。** Cloud Run、Cloud Build、Artifact Registry に、イメージ約 0.3 GB と毎週の作り直しでどれだけかかるか。予算の知らせ(月 500 円)は、使いすぎを知らせるだけ。
- **`deploy.md` は公開用のリポジトリに入れた。** 指示どおり「持ち主が行うこと」「Claude Code が行うこと」と書いてあるので、公開してよいか見てほしい。
