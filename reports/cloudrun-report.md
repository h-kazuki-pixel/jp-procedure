# Cloud Run へのデプロイと測定(2026-11-19)

プロジェクト `<PROJECT_ID>`(組織 <組織のドメイン> の下)に、読むだけの SPARQL(Oxigraph 0.5.13)を**認証つき**でデプロイし、立ち上がりの秒数とメモリを測った。公開(allUsers に呼び出しを許す)はしていない。push もしていない。

## 1. 公開の日に誰でも引ける形にできるか(組織の決まり)

**できる。** プロジェクト `<PROJECT_ID>` に実際に効いている決まり(effective policy)を、Organization Policy API(v2、`gcloud org-policies describe --effective`)で読んだ。

| 決まり | 何を縛るか | 効いている値 | 公開への影響 |
|---|---|---|---|
| `iam.allowedPolicyMemberDomains` | IAM で役割を与えられる相手のドメイン | `allowAll: true` | allUsers に与えられる |
| `iam.managed.allowedPolicyMembers` | 同じ(管理された決まりの版) | `enforce: false` | 縛りなし |
| `run.managed.requireInvokerIam` | Cloud Run の呼び出しの IAM 確認を外すこと | `enforce: false` | 縛りなし |
| `run.allowedIngress` | Cloud Run が受ける経路 | `allowAll: true` | インターネットから受けられる |

- 組織にもプロジェクトにも、じかに置かれた決まりは 0 件だった(`gcloud resource-manager org-policies list --organization` と `--project`)。上の値はすべて既定のまま。
- 旧い API(Resource Manager v1)で読んでも、`iam.allowedPolicyMemberDomains` と `run.allowedIngress` は `allValues: ALLOW` だった。
- 読むために、このプロジェクトで Organization Policy API(`orgpolicy.googleapis.com`)を有効にした。料金はかからない API。
- 決まりは組織の管理者があとから変えられる。**公開の日に、上の 4 つをもう一度読んでから** `--allow-unauthenticated` に変える。
- 試しに allUsers を付けてみることはしていない(公開になってしまうため)。

## 2. デプロイしたもの

`deploy.md` の手順 1〜4 のとおり。

| 項目 | 値 |
|---|---|
| サービス | `jp-procedure-sparql`(`asia-northeast1`)、リビジョン `jp-procedure-sparql-00001-jl6` |
| URL | `https://jp-procedure-sparql-<PROJECT_NUMBER>.asia-northeast1.run.app` |
| 設定 | 1 vCPU・1 GiB・最小 0 台・最大 1 台・要求の上限 30 秒・`--no-allow-unauthenticated`・ポート 8080 |
| イメージ | `asia-northeast1-docker.pkg.dev/<PROJECT_ID>/jp-procedure/sparql:20261119`(`sha256:146bf44d…0dff8`) |
| イメージの大きさ | 284,004,933 バイト(Artifact Registry の記録。圧縮した大きさ) |
| Cloud Build | 2 分 2 秒(送ったのは 12 ファイル、展開して 18.6 MiB) |
| 中のトリプル | 4,415,623(`COUNT(*)`)。手元の店 `store/oxigraph` と同じ数 |

- 有効にした API: `run`・`artifactregistry`・`cloudbuild`(と、1 の `orgpolicy`)。
- 1 回目の `gcloud builds submit` は「`serviceusage.services.use` の権限が無い」で止まった。持ち主はプロジェクトの owner なので、API を有効にした直後の反映の遅れと見て、90 秒おいて同じコマンドをやり直したら通った。役割は何も足していない。
- `sparql-host-report.md` で見積もった「送る大きさはおよそ 0.3 GB」は、284 MB で合っていた。
- build の記録: `out/cloudbuild_20261119.log`。

## 3. 測ったもの

`scripts/68_cloudrun_bench.py`(手元から ID トークンを付けて引く。時間は手元の Mac から見た往復を含む)と、`scripts/69_cloudrun_metrics.py`(Cloud Monitoring の指標を読む)。

### 3.1 認証

- 認証なしで引くと HTTP 403(3 回とも)。

### 3.2 立ち上がり

0 台から立ち上がったかどうかは、Cloud Run の記録(`Starting new instance. Reason: AUTOSCALING`)で確かめた。

| 回 | 時刻(日本時間) | 台の状態 | 最初の答え(ASK {})まで | コンテナの立ち上がり(Monitoring の `startup_latencies`) |
|---|---|---|---|---|
| 1 | 01:59:19 | デプロイで立った台(01:58:27 に立ち上がり) | 0.114 秒 | 267 ms(デプロイのとき) |
| 2 | 02:20:41 | 0 台から(02:20:42 に新しい台) | **0.402 秒** | 97 ms |
| 3 | 02:41:50 | 0 台から(02:41:51 に新しい台) | **0.627 秒** | 397 ms |

- 温まった台への ASK は 0.09〜0.10 秒。**0 台からの最初の答えは 0.40〜0.63 秒**(2 回)。そのうちコンテナの立ち上がりは 0.1〜0.4 秒。
- 回 3 は ASK と `COUNT(*)` だけを投げた(問いと DESCRIBE は回していない)。
- 最後の要求から 0 台になるまでは、Monitoring の台数で見て約 15 分だった(17:01 UTC まで動き、17:02〜17:15 は待ちの台が 1、17:16 に 0)。

### 3.3 問いと DESCRIBE(秒。1 回目 / 2 回目)

| 問い | 回 1(温まった台) | 回 2(0 台からの直後) | 手元(`sparql-host-report.md`、1 回目) |
|---|---|---|---|
| q1 手続ごとの根拠 | 0.358 / 0.121 | 0.179 / 0.107 | 0.032 |
| q2 区分ごとの数 | 0.306 / 0.132 | 0.207 / 0.143 | 0.328 |
| q3 府省庁ごとの数と割合 | 1.538 / 1.160 | 1.379 / 0.922 | 0.886 |
| q4 旧い文言と新しい文言 | 0.221 / 0.120 | 0.163 / 0.132 | 0.027 |
| `COUNT(*)` 全体 | 3.627 | 2.323 | – |

- `COUNT(*)` は回 3(0 台からの直後)で 3.852 秒。

| DESCRIBE | 形 | 回 1 | 回 2 | 大きさ |
|---|---|---|---|---|
| 手続 56737 | Turtle / JSON-LD | 0.104 / 0.092 | 0.107 / 0.104 | 766 / 910 バイト |
| 条 関税法 第62条の15 | Turtle / JSON-LD | 0.115 / 0.092 | 0.113 / 0.101 | 734 / 860 バイト |
| 改正の記録 地方自治法 第243条の2の8第8項 | Turtle / JSON-LD | 0.204 / 0.098 | 0.130 / 0.095 | 2,971 / 3,211 バイト |

- 返った型は、Accept に合わせて `text/turtle` と `application/ld+json`。大きさは手元と同じ。
- 結果の件数(19・10・25・2)も手元と同じ。
- 最も重い q3 は 1.6 秒以内。1 つの問いの上限 20 秒・要求の上限 30 秒には十分に収まる。
- 往復の時間は含んでいる。温まった台への ASK が 0.09 秒なので、その分が往復と見られる。

### 3.4 メモリ

Cloud Monitoring の `container/memory/utilizations`(上限 1 GiB に対する割合。1 分ごとの値)。

| 台 | 割合 | MiB に直すと |
|---|---|---|
| デプロイで立った台(16:59〜17:15 UTC) | 0.0313(立ち上がった直後)、問いを回したあと 0.2747〜0.2777 | 32、281〜284 |
| 0 台から立った台・回 2(17:21 UTC〜) | 0.2715〜0.2750 | 278〜282 |
| 0 台から立った台・回 3(17:43 UTC〜。ASK と `COUNT(*)` だけ) | 0.2582 | 264 |

- **最大は 1 GiB の 27〜28%(約 280 MiB)。** 分布の区間で見ても 0.27〜0.28 を超えた値は無かった。
- 手元の 60 MB より大きい。Cloud Run の数え方には、店のファイルを読んだときに乗る一時置き場(ページキャッシュ)が入っていると見ているが、確かめてはいない。
- 1 分ごとの値なので、1 分より短い山は見えていない可能性がある。
- 1 GiB で足りている。0.5 GiB に下げられるかは、重い問いを続けて投げて測らないと分からない(今は下げない)。

## 4. 費用

- このデプロイで使ったのは、Cloud Build 1 回(2 分)、Artifact Registry 284 MB、Cloud Run の数分。請求の額は、まだ請求の画面に出ていないので分からない。
- 最小 0 台なので、引かれないあいだは Cloud Run の CPU・メモリの料金はかからない。Artifact Registry の保管は続く。

## 5. 直したファイル

- `deploy.md`: 1〜5 を行ったこと、組織の決まりを確かめたこと、測った値、公開の日に決まりを読み直すこと。
- `scripts/68_cloudrun_bench.py`・`scripts/69_cloudrun_metrics.py`(新しく作った。公開用のリポジトリにも写した)。

## 6. まだのこと・決めていただきたいこと

- `deploy.md` の 6(毎週の追跡から入れ替える、Workload Identity 連携)は行っていない。持ち主が良いと言ってから。
- 公開(`--allow-unauthenticated`)は公開の日まで行わない。
- Artifact Registry に古いイメージが毎週たまる。消す決まり(新しい数個だけ残す)を付けるかどうか。
