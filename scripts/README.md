# 作り直しの手順

リポジトリの一番上で、上から順に動かします。

- Python 3(作ったときは 3.14)。必要なものは `../requirements.txt`。
- e-Gov 法令API v2 への取得は `egov.py` が 1 秒に 1 回までに抑え、取った結果を `data/api/cache/` に残します。残っているものは取り直しません。
- 出力は `out/`(途中のもの)と `rdf/`(RDF)に出ます。公開する形にするには、`rdf/*.ttl.gz` を `data/rdf/` に写します。
- 法令の「現時点」の一覧や改正履歴は取る日によって変わるので、同じ日に取らないと数は同じになりません。

| 順 | スクリプト | すること |
|---|---|---|
| 1 | `01_download_sources.sh` | デジタル庁の Excel(R7・R6)を `data/raw/` に取り、SHA-256 を確かめる |
| 2 | `00_convert.py data/raw/20260826_procedures_survey_result_outline_02.xlsx data/r7.csv`、同じく R6 → `data/r6.csv` | Excel を CSV に |
| 3 | `04a_fetch_laws.py 2025-11-01`、`04a_fetch_laws.py` | e-Gov の法令一覧(2025-11-01 と現時点) |
| 4 | `04b_match_laws.py` | 手続ごとに法令ID を決める |
| 5 | `11_fetch_all.py` | 法令の本文(asof=2025-11-01) |
| 6 | `12_full_check.py` | 根拠条項号を分けて、本文の条・項・号と照合する |
| 7 | `16_fetch_revisions.py`、`17_updated.py` | 法令ごとの改正履歴 |
| 8 | `20_estimate.py`、`21_fetch_new.py` | 比べる相手の本文(asof=2026-11-18) |
| 9 | `22_amend_compare.py` | 2025-11-01 版と 2026-11-18 版の文言を比べる |
| 10 | `30_moves.py`、`40_fix.py`〜`45_fix_rules5.py` | 区分の決まりを順に当てる(第 5 版まで。報告 `reports/fix-report*.md`) |
| 11 | `50_build_rdf.py`、`54_build_expressions.py`、`61_build_changes.py` | RDF(手続・記録・法令・条項号・本文の版・改正の記録) |
| 12 | `56_split_for_shacl.py test`、`59b_make_broken.py`、`59_shacl_split.py test`、`59_shacl_split.py testbad` | 手続 2,000 件で、まとめて通す・分けて通すを比べる |
| 13 | `56_split_for_shacl.py full`、`59_shacl_split.py full`、`57_count_checks.py` | 全件の SHACL(自作と公式 CPSV-AP 3.2.0)と全体の数 |
| 14 | `62_oxigraph_load.py`、`63_queries.py` | pyoxigraph に読み込み、`queries/` の問いを回す |
| 15 | `64_check_moved_text.py`、`65_check_rules_module.py`、`66_check_versions.py` | 移った先の本文があるか、`change_rules.py` が 45 までと同じ区分を出すか、版の ID と施行日 |
| 16 | `67_server_bench.py <oxigraph> <店>` | Oxigraph の読むだけのサーバーを手元で立てて測る |
| 17 | `ID_TOKEN=… 68_cloudrun_bench.py <URL>`、`ACCESS_TOKEN=… 69_cloudrun_metrics.py <PROJECT_ID> <サービス> <分>` | Cloud Run の SPARQL を測る(`../deploy.md`) |
| 18 | `73_check_min_bounds.py shapes/shapes.ttl` | 自作 SHACL で上限を外した所に、下限(1 つ以上)が効いているか(小さな壊したデータで) |
| 19 | `74_write_status.py --checks success\|skipped` | 毎週の追跡の結果を `status.json` に書き、README の「最後に確かめた日」の行を書き直す。週ごとに、根拠の条・項・号が変わった手続の数(`procedures`。70 の `last_run.json` から。無い週は `changed.json` から)も書く。閲覧ページのはじめの画面の「毎週の追跡」の札は、この数を使う |
| 20 | `75_make_stats.py <店> stats.json data/rdf` | 閲覧ページのはじめの画面の数を `queries/` の q5〜q7 で出して `stats.json` に書く。`STATS=stats.json 57_count_checks.py` で全体の数の確かめと比べる。stats.json の隣の README.md(冒頭)と view.html(JavaScript が無くても読める要約)の `<!-- s:キー -->` の数も、同じ数で書き込む(`stats_text.py`) |
| 21 | `81_scan_repo.py <公開用のフォルダ> [公開しない文字列の一覧]` | 公開用のフォルダに、プロジェクト ID・番号・組織・手元のパス・メールアドレスが残っていないかを、gzip の中まで探す |
| 22 | `78_make_human_check.py [店] [出力の場所]` | 人の抜き取り用のまとめ `human-check.csv`・`human-check.html`(別の AI が区分を決めた行と、固定の種で抜き取った 20 行)。HTML は手元で開いて、結果を CSV で書き出せる。移った行は、移った先の文言も出す(手元に残した e-Gov の 2026-11-18 版の本文から。2026-11-20 に直した。その日の抜き取りの用紙には出ていなかった) |
| 23 | `80_make_repo.py` | 作業フォルダから公開用のリポジトリの形を作る(何度流しても同じになる)。公開しない値の置き換えは、公開しないファイル(環境変数 `REPL_PRIVATE`)から読む |
| 24 | `82_make_changed_list.py <店> changed.json` | 閲覧ページの「変わった手続の一覧」と、違う所の短い抜き出し(作り方はスクリプトの先頭) |
| 25 | `83_write_readme_numbers.py <店> <公開用のリポジトリ>` | README の数(`<!-- n:キー -->…<!-- /n -->` の中)を、店への問いとファイルの大きさから書き直す。80 と毎週のワークフローが流す。`README=README.md 57_count_checks.py` で、SPARQL を使わずに数えた数と比べる。冒頭の例の文(`<!-- e:手続ID -->`)も、改正の記録の旧い文言・新しい文言と法令の状態から書く。隣の view.html の要約・meta description・og:description にも同じ文を書く(はじめの画面の大きな例は、要約の文を読んで出す)。57 が、文の額・日付・法令の名を、ファイルを直に読んだ値と比べる。数の断りの「名と府省庁が同じ組・件」(`same_name_groups`・`same_name_rows`)は、README と view.html の `<!-- n: -->` に書く |
| — | `redact.py` | 調査の記録の自由記述から個人の連絡先を伏せる(`50_build_rdf.py` が `data/redactions.csv` を当てる。作業フォルダでは `redactions.csv`) |

- 62 は `62_oxigraph_load.py <RDF の場所> <店の場所>`、63 は `63_queries.py <店の場所> <問いの場所>` のように、場所を引数で渡せる。
- 56・57・59・62 は、環境変数 `RDF_DIR`(既定 `rdf`)、`SHAPES`、`CPSV_SHACL`、`PYTHON`、`STORE`(62 の店の場所)で場所を変えられる。公開用のリポジトリでは `RDF_DIR=data/rdf SHAPES=shapes/shapes.ttl`。
- 公式 CPSV-AP 3.2.0 の SHACL は、`data/vocab/cpsv-ap-3.2.0-SHACL.ttl` に置いてから動かします(<https://semiceu.github.io/CPSV-AP/releases/3.2.0/shacl/cpsv-ap-SHACL.ttl>)。
- 別の AI(作った Claude Code とは別の会話の Claude)の読みで区分を決めた 3 件は、`42_fix_rules.py` の中に、日付と理由と一緒に書いてあります(作業の列の名前は「人の確認」のままですが、読んだのは別の AI です)。RDF では確かめの記録(`jpp:Review`)の確かめた者の種類が「別の AI」です。人の抜き取り(2026-11-20、23 件)の結果は `human-check-result.csv` から `61_build_changes.py` が読み、確かめた者の種類「人」の記録として足します。結果の CSV は、作った人が用紙(`human-check.html`)から書き出したものです。用紙と結果は区分の名前を変える前に作ったため、区分は古い名前「移った先なし」で出ます。データの中の確かめの記録のうち 5 か所(どの抜き取りかを書いた `jpp:reviewSampling` の、用紙の「選んだ理由」の引用)にも、同じ理由で古い名前が残っています。

## 毎週の追跡

`70_weekly_track.py` は、公開用のリポジトリの形(`data/rdf/`、`data/tracking/`)の上で動きます。使い方はスクリプトの先頭にあります。GitHub Actions のワークフローは `../.github/workflows/weekly-track.yml` です。

- 旧い側は、いつも公開しているデータの文言(`data/rdf` と `data/rdf/weekly/` の本文の版のうち最も新しいもの)です。e-Gov に前回の日付で取り直しません。区分を決めるのに要る旧い版の本文は、公開しているデータの版の ID で取ります(文言が違う条・項・号のある法令だけ)。
- 版の ID が同じで文言だけが違うもの(e-Gov の版を変えない直し)は記録にせず、`data/tracking/egov_corrections.csv` に足します。
- 更新データが取れなかった日は、法令API v1 の更新法令一覧を引き、0 件なら「更新法令なし(v1 の一覧で 0 件)」として外します(`last_run.json` の `days`・`no_update_days`)。取れた日も v1 の件数と比べます(`v1_mismatch`)。
- 取れなかった日・法令は `data/tracking/state.json` の `pending_days`・`failed_laws` に残し、次の実行で取り直します(取れなかった実行の比べ始めから比べる)。取れた分の記録は書き、確かめた日は進めます。
- 取れなかったもの・比べられなかった条項号の中身は `data/tracking/last_run.json`(`skipped`・`long_pending`)にあります。
- 根拠の法令の廃止・失効は `law_status.py`(e-Gov 法令API v2 の法令一覧を廃止等の状態で絞って引く。判定の決まりは先頭に書いた)。期間の中で廃止・失効した法令は区分「根拠の法令が廃止・失効した」の記録(`jpp:LawStatusChange`)に、期間より前のものは法令の状態(`jpp:LawStatus`)にする。分類しない法令は、初めの期間の補い(60)で e-Gov が返した値だけを `jpp:LawStatusUnclear` にする(毎週の追跡は last_run.json の law_status_unclear に出すだけ)。
- `60_law_status_supplement.py`: 初めの期間(2025-11-02〜2026-11-18)の廃止・失効を、別のファイル(`data/rdf/weekly/supplement_law-status_…`)で補う(2026-11-21 に一度流した。初めのファイルは変えない)。
- 試し: 作業フォルダの `88_test_weekly_failures.py` が、偽の e-Gov(500 の日、v1 の 0 件・取れない日・件数の合わない日、404 の法令、版を変えない直し、根拠の法令の廃止・失効)で上のとおりに動くことを確かめます(公開用には入れていない)。
