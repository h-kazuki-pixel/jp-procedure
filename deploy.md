# デプロイの手順(Cloud Run、読むだけの SPARQL)

行政手続LOD の RDF を Oxigraph(読むだけ)に入れて、Cloud Run で動かす手順です。だれが動かしても同じになるように、人やプロジェクトによって変わる値は、次の置き換え文字にしてあります。

| 置き換え文字 | 中身 | 調べ方 |
|---|---|---|
| `<PROJECT_ID>` | Google Cloud のプロジェクト ID | `gcloud config get-value project` |
| `<PROJECT_NUMBER>` | プロジェクト番号 | `gcloud projects describe <PROJECT_ID> --format='value(projectNumber)'` |
| `<BUDGET>` | 月の予算の額 | 自分で決める |
| `<OWNER>` / `<REPO>` | GitHub のリポジトリの持ち主と名前 | |
| `<OWNER_ID>` | GitHub の持ち主の数の ID | `gh api users/<OWNER> --jq .id` |
| `<REPO_ID>` | GitHub のリポジトリの数の ID | `gh api repos/<OWNER>/<REPO> --jq .id`(リポジトリを作ったあと) |
| `<TAG>` | イメージの札(日付など) | 例: `$(date +%Y%m%d)` |

サービス名・アカウント名・バケット名は、下のとおりに決めてあります(変えるなら、`.github/workflows/weekly-track.yml` も合わせて直す)。バケット名は世界で一つなので、使われていれば `<PROJECT_ID>-build-source` などに変えます。

## 決めてあること

| 項目 | 値 | 理由 |
|---|---|---|
| 地域 | `asia-northeast1`(東京) | |
| 台数 | 最小 0 台・最大 1 台 | 使わないときは 0 台にして、料金を抑える |
| CPU・メモリ | 1 vCPU・1 GiB | 測った値は `reports/cloudrun-report.md`(メモリの最大は 1 GiB の 27〜28%) |
| 要求の時間の上限 | 30 秒(Cloud Run)。1 つの問いの上限は 20 秒(Oxigraph の `--timeout-s`) | 下の「上限の決め方」 |
| 認証 | 認証つき(`--no-allow-unauthenticated`)。公開の日まで | |
| ポート | 8080 | `deploy/Dockerfile` で `--bind 0.0.0.0:8080` |
| CORS | 許す(`--cors`) | GitHub Pages の閲覧ページ `view.html` から問い合わせるため |
| イメージ | 中身をイメージに入れる形(`deploy/Dockerfile`) | `reports/sparql-host-report.md` で比べた |
| サービス | `jp-procedure-sparql` | |
| イメージの置き場所 | Artifact Registry `asia-northeast1-docker.pkg.dev/<PROJECT_ID>/jp-procedure/sparql` | |
| 実行用のアカウント | `jp-procedure-sparql-run`(役割なし) | 既定のアカウント(`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`)はプロジェクトの Editor を持つので使わない |
| 入れ替え用のアカウント | `jp-procedure-deployer`(GitHub Actions が使う。鍵のファイルは作らない) | |
| build に送るものの置き場所 | バケット `jp-procedure-build-source`(7 日で消える) | |

**上限の決め方:**

- 最も重い問い(府省庁ごとの数と割合、`queries/q3_changed_by_ministry.rq`)は、手元(Apple シリコンの Mac)で 1 回目 0.886 秒、Cloud Run(1 vCPU)で 1 回目 1.379〜1.538 秒だった(`reports/cloudrun-report.md`)。
- 1 つの問いは 20 秒で打ち切り、要求全体は 30 秒を上限にする。

## 持ち主が手で行うこと

1. **Google Cloud のプロジェクトを作る。**
2. **支払い(請求先アカウント)を有効にする。** そのプロジェクトに請求先アカウントをつなぐ。
3. **予算の知らせを付ける。**
   - 「お支払い」→「予算とアラート」で、月 `<BUDGET>` の予算を作る。
   - 知らせの割合は 50%・90%・100% など。
   - 予算の知らせは、使いすぎを知らせるだけで、止めはしない。
4. **gcloud を入れて、ログインする。**
   - Google Cloud CLI を入れる(公式の説明: <https://cloud.google.com/sdk/docs/install>)。
   ```sh
   gcloud auth login
   gcloud config set project <PROJECT_ID>
   ```

## コマンドで行うこと

各段の前に、使うコマンドと費用の出どころを確かめてから進める。

**0. 組織の決まりを確かめる(デプロイの前に)。** 公開の日に allUsers に呼び出しを許せるかを見る。どれかが縛っていれば(`allowAll` でない、`enforce: true` など)、ここで止めて持ち主が決める。

```sh
gcloud services enable orgpolicy.googleapis.com
for c in iam.allowedPolicyMemberDomains iam.managed.allowedPolicyMembers run.managed.requireInvokerIam run.allowedIngress; do
  gcloud org-policies describe $c --project=<PROJECT_ID> --effective
done
```

1. **使う API を有効にする**
   ```sh
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
     iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com
   ```
2. **イメージの置き場所を作り、古いイメージを消す決まりを付ける**
   ```sh
   gcloud artifacts repositories create jp-procedure --repository-format=docker --location=asia-northeast1
   gcloud artifacts repositories set-cleanup-policies jp-procedure --location=asia-northeast1 \
     --policy=deploy/ar-cleanup-policy.json --no-dry-run
   ```
   - `deploy/ar-cleanup-policy.json` は、すべてを消す対象にし(`delete-all`)、新しい 4 つだけを残す(`keep-newest-4`)。「残す」だけでは何も消えないので、2 つを組にする。
   - 古いイメージは手で消さない。この決まりが新しい 4 つを残し、5 つ目より古いものだけを消す(入れ替えの前のイメージに戻せるように)。
3. **イメージを作る(Cloud Build)**
   - 送るのは `deploy/` と `data/rdf/` だけ(`.gcloudignore`。約 19.5 MB)。Turtle から店を作るのは、Cloud Build の中で行う。
   ```sh
   IMAGE=asia-northeast1-docker.pkg.dev/<PROJECT_ID>/jp-procedure/sparql
   gcloud builds submit --region asia-northeast1 --config deploy/cloudbuild.yaml --substitutions _IMAGE=$IMAGE,_TAG=<TAG> .
   ```
   - API を有効にした直後は「`serviceusage.services.use` の権限が無い」で止まることがある。1〜2 分おいてやり直す。
4. **実行用のアカウントを作り、Cloud Run にデプロイする(認証つき)**
   ```sh
   gcloud iam service-accounts create jp-procedure-sparql-run --display-name "jp-procedure-sparql 実行用"
   gcloud run deploy jp-procedure-sparql --image $IMAGE:<TAG> --region asia-northeast1 \
     --service-account jp-procedure-sparql-run@<PROJECT_ID>.iam.gserviceaccount.com \
     --port 8080 --cpu 1 --memory 1Gi --min-instances 0 --max-instances 1 --timeout 30 \
     --no-allow-unauthenticated
   ```
5. **確かめる**
   - 自分の ID トークンを付けて、0 台からの最初の答えまでの秒数、`queries/` の 4 つの問い、DESCRIBE の時間を測る。
   - 測るスクリプト: `scripts/68_cloudrun_bench.py`(時間)、`scripts/69_cloudrun_metrics.py`(Cloud Monitoring のメモリ・立ち上がり・台数)。
   ```sh
   URL=$(gcloud run services describe jp-procedure-sparql --region asia-northeast1 --format 'value(status.url)')
   ID_TOKEN=$(gcloud auth print-identity-token) python3 scripts/68_cloudrun_bench.py "$URL"
   ACCESS_TOKEN=$(gcloud auth print-access-token) python3 scripts/69_cloudrun_metrics.py <PROJECT_ID> jp-procedure-sparql 60
   ```
6. **毎週の追跡から入れ替えられるようにする(Workload Identity 連携)**
   - 入れ替え用のアカウントと、build に送るものの置き場所を作る。
   ```sh
   P=<PROJECT_ID>; D=serviceAccount:jp-procedure-deployer@$P.iam.gserviceaccount.com
   gcloud iam service-accounts create jp-procedure-deployer --display-name "jp-procedure 入れ替え(GitHub Actions)"
   gcloud storage buckets create gs://jp-procedure-build-source --location asia-northeast1 --uniform-bucket-level-access --public-access-prevention
   echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":7}}]}' > /tmp/lifecycle.json
   gcloud storage buckets update gs://jp-procedure-build-source --lifecycle-file=/tmp/lifecycle.json
   ```
   - 役割を付ける。できるだけ、そのものに付ける。

     | 役割 | 付けた先 | 何のため |
     |---|---|---|
     | `roles/run.developer` | サービス `jp-procedure-sparql` だけ | 入れ替え(`gcloud run deploy`) |
     | `roles/iam.serviceAccountUser` | `jp-procedure-sparql-run` だけ | 入れ替えた Cloud Run を実行用アカウントで動かす |
     | `roles/iam.serviceAccountUser` | `jp-procedure-deployer` 自身 | build を自分のアカウントとして動かす |
     | `roles/cloudbuild.builds.editor` | プロジェクト | build を始める(Cloud Build はプロジェクトにしか付けられない) |
     | `roles/logging.logWriter` | プロジェクト | build のログを書く |
     | `roles/artifactregistry.writer` | リポジトリ `jp-procedure` だけ | イメージを入れる |
     | `roles/storage.objectAdmin`、`roles/storage.legacyBucketReader` | バケット `jp-procedure-build-source` だけ | build に送るものを置く・読む |

   ```sh
   gcloud run services add-iam-policy-binding jp-procedure-sparql --region asia-northeast1 --member=$D --role=roles/run.developer
   gcloud iam service-accounts add-iam-policy-binding jp-procedure-sparql-run@$P.iam.gserviceaccount.com --member=$D --role=roles/iam.serviceAccountUser
   gcloud iam service-accounts add-iam-policy-binding jp-procedure-deployer@$P.iam.gserviceaccount.com --member=$D --role=roles/iam.serviceAccountUser
   gcloud projects add-iam-policy-binding $P --member=$D --role=roles/cloudbuild.builds.editor --condition=None
   gcloud projects add-iam-policy-binding $P --member=$D --role=roles/logging.logWriter --condition=None
   gcloud artifacts repositories add-iam-policy-binding jp-procedure --location asia-northeast1 --member=$D --role=roles/artifactregistry.writer
   gcloud storage buckets add-iam-policy-binding gs://jp-procedure-build-source --member=$D --role=roles/storage.objectAdmin
   gcloud storage buckets add-iam-policy-binding gs://jp-procedure-build-source --member=$D --role=roles/storage.legacyBucketReader
   ```
   - 信頼する相手を、GitHub の `<OWNER>/<REPO>` の main だけに絞る。プロバイダの条件と、`roles/iam.workloadIdentityUser` を付ける subject の二重で絞る。
   ```sh
   gcloud iam workload-identity-pools create github --location global --display-name "GitHub Actions"
   gcloud iam workload-identity-pools providers create-oidc jp-procedure-main --location global --workload-identity-pool github \
     --issuer-uri https://token.actions.githubusercontent.com \
     --attribute-mapping 'google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner_id=assertion.repository_owner_id,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref' \
     --attribute-condition "assertion.repository_owner_id == '<OWNER_ID>' && assertion.repository == '<OWNER>/<REPO>' && assertion.ref == 'refs/heads/main'"
   gcloud iam service-accounts add-iam-policy-binding jp-procedure-deployer@$P.iam.gserviceaccount.com --role roles/iam.workloadIdentityUser \
     --member "principal://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github/subject/repo:<OWNER>/<REPO>:ref:refs/heads/main"
   ```
   - 持ち主の数の ID(`<OWNER_ID>`)を条件に入れるのは、持ち主が名前を変えたあとに別の人が同じ名前を取っても、通らないようにするため。
   - ワークフローで `environment:` を使うと subject の形が変わって通らなくなる。今のワークフローは使っていない。
   - 付いた権限は、Policy Troubleshooter で確かめられる(`gcloud services enable policytroubleshooter.googleapis.com` のあと、`gcloud policy-intelligence troubleshoot-policy iam <資源> --principal-email=jp-procedure-deployer@$P.iam.gserviceaccount.com --permission=<権限>`)。
7. **GitHub にリポジトリを作った直後に、リポジトリの ID を信頼の条件に足す**
   - 同じ名前のリポジトリを消して作り直したときに、古い条件のまま通らないようにするため。
   ```sh
   gh api repos/<OWNER>/<REPO> --jq .id     # これが <REPO_ID>
   gcloud iam workload-identity-pools providers update-oidc jp-procedure-main --location global --workload-identity-pool github \
     --attribute-condition "assertion.repository_owner_id == '<OWNER_ID>' && assertion.repository_id == '<REPO_ID>' && assertion.repository == '<OWNER>/<REPO>' && assertion.ref == 'refs/heads/main'"
   gcloud iam workload-identity-pools providers describe jp-procedure-main --location global --workload-identity-pool github --format='value(attributeCondition)'
   ```
   - 条件の中の `assertion.repository_id` は、GitHub のトークンの値をそのまま見るので、`--attribute-mapping` を変えなくてよい。
8. **GitHub の設定を入れる**(リポジトリの Settings → Secrets and variables → Actions)
   - Secrets: `GCP_WIF_PROVIDER` = `projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github/providers/jp-procedure-main`、`GCP_SERVICE_ACCOUNT` = `jp-procedure-deployer@<PROJECT_ID>.iam.gserviceaccount.com`
   - Variables: `GCP_PROJECT_ID` = `<PROJECT_ID>`、`DEPLOY_ENABLED` = `false`(9 で試すときだけ `true` にする)
9. **公開の日より前に、GitHub Actions で入れ替えを一度試す**
   - `DEPLOY_ENABLED` を `true` にする。
   - Actions の weekly-track を「Run workflow」で、main を選び、`deploy_only` に印を付けて動かす。追跡はせず、今の main の `data/rdf/` からイメージを作り直して入れ替える段だけが動く。
   ```sh
   gh workflow run weekly-track.yml -R <OWNER>/<REPO> --ref main -f deploy_only=true
   gh run watch -R <OWNER>/<REPO>
   ```
   - 確かめること:
     - deploy ジョブが通ったか。通らなければ、ログで権限が足りない所を見て、6 の表の範囲で直す(表に無い役割は、足す前に持ち主が決める)。
     - Cloud Run に新しいリビジョンができ、イメージの札が今日の日付になったか(`gcloud run services describe jp-procedure-sparql --region asia-northeast1 --format='value(status.latestReadyRevisionName,spec.template.spec.containers[0].image)'`)。
     - 認証の形が変わっていないか(認証なしで 403 のまま)。
     - 5 の測るスクリプトで、トリプルの数と問いの時間が前と同じか。
   - 試したあと、毎週の入れ替えを続けるなら `DEPLOY_ENABLED` を `true` のままにする。続けないなら `false` に戻す。
   - ワークフローの入れ替えでは、認証の形(`--allow` / `--no-allow-unauthenticated`)を指定しない。公開の日に変えた形を毎週戻さないため。入れ替え用のアカウントは、呼び出しの IAM を変えられない。

## 公開の日に行うこと

- 手順 0 の組織の決まりを、もう一度読む。縛りが増えていたら止める。
- 持ち主が決めてから、`gcloud run services add-iam-policy-binding jp-procedure-sparql --region asia-northeast1 --member=allUsers --role=roles/run.invoker` で、だれでも引けるようにする。
- w3id の `.htaccess`(`w3id/.htaccess`)の `CLOUD_RUN_HOST` を、Cloud Run の URL のホスト名に置き換え、w3id に pull request を出す。
- `view.html` の `CONFIG.endpoint` を Cloud Run の URL(`https://<ホスト名>/query`)に変え、GitHub Pages(main の一番上)に置く。

## 止めるとき

Cloud Run を止める(サービスを消す、または引けないようにする)と、URI を機械が引いたときの転送先(DESCRIBE)と、閲覧ページの問い合わせが使えなくなります。止める前に、w3id の転送を一括ダウンロードの案内に直します。

1. `w3id/.htaccess` の「それ以外はすべて DESCRIBE」の行を、次に置き換える(リポジトリの README の「ファイル」の節へ 302)。
   ```apache
   RewriteRule ^((procedure|provision|law|change|record|organisation|code)/.+)$ https://github.com/<OWNER>/<REPO>#ファイル [R=302,L,NE]
   ```
   HTML の行(閲覧ページ)も、閲覧ページが Cloud Run に問い合わせるので、同じ行先にするか、閲覧ページに「今は問い合わせできません」と出すようにする。
2. w3id に pull request を出し、取り込まれたのを確かめる(`curl -I -H 'Accept: text/turtle' https://w3id.org/jp-procedure/procedure/119637` の転送先)。
3. Cloud Run を止める。
   ```sh
   gcloud run services delete jp-procedure-sparql --region asia-northeast1
   ```
   毎週の追跡の入れ替えを止めるため、リポジトリの変数 `DEPLOY_ENABLED` を `false` にする。
4. README の「SPARQL サーバー」と「言えること・言えないこと」を、止めたことに合わせて直す。
