# 設定の報告(2026-11-19)

指示の 1〜3 を行った。push はしていない。`DEPLOY_ENABLED` は作っていない(GitHub にリポジトリがまだ無いので、変数も Secrets も入れていない)。公開(allUsers)はしていない。

## 1. `CLAUDE.md`

試しの作業フォルダの `CLAUDE.md` と同じ 5 つの決まりを置いた。

- 変えたのは 1 か所だけ。「push しない(持ち主が決めるまで)」を「push しない(リポジトリの持ち主が決めるまで)」にした。公開用のリポジトリでは、作った人の名前は帰属・ライセンス・w3id の連絡先だけに出す決まりのため。
- 名前・メールアドレス・組織のドメイン・手元のパスは入っていない(grep で確かめた)。
- `.gitignore` で外していないので、リポジトリに入る。まだ commit していない。

## 2. Artifact Registry の古いイメージを消す決まり

`deploy/ar-cleanup-policy.json` を `gcloud artifacts repositories set-cleanup-policies … --no-dry-run` で付けた。

- 「残す」の決まりだけでは何も消えない。そこで「すべてを消す対象にする」決まりと「新しい 4 つは残す」決まりを組にした。「残す」のほうが先に効く。

付けたあとに読み出した決まり(`gcloud artifacts repositories describe jp-procedure`):

```yaml
cleanupPolicies:
  delete-all:
    action: DELETE
    condition:
      tagState: ANY
    id: delete-all
  keep-newest-4:
    action: KEEP
    id: keep-newest-4
    mostRecentVersions:
      keepCount: 4
```

- 読み出しに `cleanupPolicyDryRun` は出なかった。試しの形ではなく、本当に消す形になっている。
- 今のイメージは 1 つ(`20261119`、284.009 MB)。4 つより少ないので、消えるものはまだ無い。
- 決まりがどの間隔で動くかは確かめていない。

## 3. Workload Identity 連携(`deploy.md` の手順 6)

### 3.1 作ったもの

| 種類 | 名前 | 中身 |
|---|---|---|
| サービスアカウント | `jp-procedure-deployer@<PROJECT_ID>.iam.gserviceaccount.com` | 入れ替え専用。鍵は作っていない |
| サービスアカウント | `jp-procedure-sparql-run@<PROJECT_ID>.iam.gserviceaccount.com` | Cloud Run の実行用。役割なし |
| バケット | `gs://jp-procedure-build-source` | build に送るものを置く。`asia-northeast1`、一律のアクセス制御、公開の禁止を強制、7 日で消える |
| プール | `github`(global) | |
| プロバイダ | `jp-procedure-main`(OIDC、`https://token.actions.githubusercontent.com`) | 下の条件 |
| 有効にした API | `iam`・`iamcredentials`・`sts`・`policytroubleshooter` | 最後のものは、下の 3.4 の確かめに使った |

**実行用アカウントを別に作った理由**

- 今までは、Cloud Run の実行も build も、既定のアカウント(`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`)で動いていた。
- このアカウントは、プロジェクトの Editor を持っている。
- 入れ替え用のアカウントに「このアカウントとして動く」権限を与えると、実質 Editor を渡すことになる。
- そこで、役割なしの `jp-procedure-sparql-run` を作り、Cloud Run をそれで動かすように変えた(`gcloud run services update --service-account`)。
  - 新しいリビジョンは `jp-procedure-sparql-00002-2qv`。イメージは同じ。
  - 変えたあとも、認証なしは 403、ASK は 0.105 秒、トリプルは 4,415,623 で、前と同じだった。

### 3.2 `jp-procedure-deployer` に付けた役割(読み出した値)

| 役割 | 付けた先 | 何のため |
|---|---|---|
| `roles/run.developer` | サービス `jp-procedure-sparql` だけ | jp-procedure-sparql の入れ替え |
| `roles/iam.serviceAccountUser` | `jp-procedure-sparql-run` だけ | 入れ替えた Cloud Run を実行用アカウントで動かす |
| `roles/iam.serviceAccountUser` | `jp-procedure-deployer` 自身 | build を自分のアカウントとして動かす(既定のアカウントを使わないため) |
| `roles/cloudbuild.builds.editor` | プロジェクト | Cloud Build で build を始める。Cloud Build の役割はプロジェクトにしか付けられない |
| `roles/logging.logWriter` | プロジェクト | build が自分のアカウントで動くと、ログを書く権限が要る |
| `roles/artifactregistry.writer` | リポジトリ `jp-procedure` だけ | Artifact Registry への書き込み |
| `roles/storage.objectAdmin` | バケット `jp-procedure-build-source` だけ | build に送るものを置く・build が読む |
| `roles/storage.legacyBucketReader` | バケット `jp-procedure-build-source` だけ | `gcloud builds submit` がバケットの有無を確かめる(`storage.buckets.get`) |

- 実行用アカウント `jp-procedure-sparql-run` には、プロジェクトの役割は何も付いていない(読み出して 0 件)。
- サービスに付いている IAM は、上の `roles/run.developer` 1 つだけ。

**もっと絞れるところ(まだしていない)**

- `roles/run.developer` には、サービスを消す権限(`run.services.delete`)も入っている。
- `roles/cloudbuild.builds.editor` は、プロジェクトのほかの build も止められる。
- どちらも、要る権限だけのカスタムロールにすれば、さらに絞れる。決まった役割の中では、これが最も小さいと見ている。

### 3.3 信頼する相手

二重に絞った。

1. **プロバイダの条件:** この条件に合わないトークンは、交換の段で断られる。
   ```
   assertion.repository_owner_id == '<OWNER_ID>'
   && assertion.repository == 'h-kazuki-pixel/jp-procedure'
   && assertion.ref == 'refs/heads/main'
   ```
2. **`roles/iam.workloadIdentityUser`:** `jp-procedure-deployer` に対して、次の 1 つの subject だけに付けた。
   ```
   principal://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github/subject/repo:h-kazuki-pixel/jp-procedure:ref:refs/heads/main
   ```

- `<OWNER_ID>` は GitHub のユーザー `h-kazuki-pixel` の ID(`gh api users/h-kazuki-pixel` で読んだ)。名前を変えたあとに別の人が同じ名前を取っても、通らないようにするため。
- リポジトリ `h-kazuki-pixel/jp-procedure` は、GitHub にまだ無い(`gh api` で 404)。作ったら、その ID(`assertion.repository_id`)も条件に足すのがよい。
- ワークフローで `environment:` を使うと、subject の形が変わって通らなくなる。今のワークフローは使っていない。

### 3.4 確かめたこと

- **入れ替え用のアカウントとして動かす確かめは、していない。** 動かすには、持ち主のアカウントにトークンを作る役割(`roles/iam.serviceAccountTokenCreator`)を足す必要があり、指示に無いので足さなかった(`--impersonate-service-account` は `iam.serviceAccounts.getAccessToken` が無いと断られた)。
- 代わりに Policy Troubleshooter(`gcloud policy-intelligence troubleshoot-policy iam`)で、権限ごとに許可の側を調べた。

| 権限 | 付けた先 | 許可の側 |
|---|---|---|
| `run.services.get`・`run.services.update` | サービス | GRANTED |
| `iam.serviceAccounts.actAs` | `jp-procedure-sparql-run` | GRANTED |
| `iam.serviceAccounts.actAs` | `jp-procedure-deployer` 自身 | GRANTED |
| `cloudbuild.builds.create`・`logging.logEntries.create` | プロジェクト | GRANTED |
| `artifactregistry.repositories.uploadArtifacts` | リポジトリ | GRANTED |
| `storage.buckets.get`・`storage.objects.create`・`storage.objects.get` | バケット | GRANTED |
| `run.services.setIamPolicy`(呼び出しの IAM を変える) | サービス | NOT_GRANTED |
| `iam.serviceAccounts.actAs` | 既定のアカウント(Editor) | NOT_GRANTED |
| `artifactregistry.repositories.deleteArtifacts` | リポジトリ | NOT_GRANTED |
| `run.services.create` | プロジェクト | NOT_GRANTED |
| `resourcemanager.projects.setIamPolicy` | プロジェクト | NOT_GRANTED |

- 拒否の側は、どれも「分からない」(UNKNOWN_INFO)と出た。
  - プロジェクトに付いた拒否ポリシーは 0 件だった。
  - 組織の拒否ポリシーは、読む権限が無くて確かめられなかった(`iam.denypolicies` の読み出しが断られた)。
- `serviceusage.services.use`(前回、持ち主の build で一度出たエラー)は付けていない。サービスアカウントが自分のプロジェクトの API を呼ぶときは要らないと見ているが、確かめていない。
- **本当に通るかは、最初の GitHub Actions の実行で分かる。**

### 3.5 直したファイル(``)

- `.github/workflows/weekly-track.yml` の deploy ジョブ
  - build を `jp-procedure-deployer` として動かす(`--service-account`)。
  - 送る置き場所を `gs://jp-procedure-build-source/source` にする。
  - ログはここでは流さない(`--suppress-logs`)。
  - Cloud Run を `jp-procedure-sparql-run` で動かす。
  - `--no-allow-unauthenticated` を外した。公開の日に変えた形を、毎週の入れ替えで戻さないため。
- `deploy/cloudbuild.yaml`: `options.logging: CLOUD_LOGGING_ONLY` を足した。自分のアカウントで動かす build には、これが要る。
- `deploy/ar-cleanup-policy.json`(新しく作った)。
- `deploy.md`
  - 手順 4 に `--service-account` を足した。
  - 手順 6 を、行ったことと付けた役割の表に書き直した。
  - 手順 7(古いイメージを消す)を足した。
- YAML として読めることを確かめた(Python の yaml で 2 つとも読めた)。
- `gcloud builds submit --help` に、使ったフラグがあることを確かめた。

## 4. 費用

- 足したもの(サービスアカウント・プール・API・バケット)は、それ自体には料金がかからない。
- バケットは、置いたものの大きさの分だけかかる(1 回 19 MB ほど、7 日で消える)。
- Cloud Run のリビジョンを 1 つ足した。最小 0 台なので、引かれないあいだは料金はかからない。

## 5. 4(閲覧ページ)は止めた

- 指示の 4 にある「前に渡した指示の 1〜7」は、この会話の記録にもまとめにも見当たらない。
  - 中身は、status.json、deploy.md の書き直し、README の作り方、語彙の注記、SHACL の下限の確かめ、view.html、view-report.md。
- 細かい指定(status.json に何を入れるか、SHACL の下限とは何か、view.html に何を出すか など)が分からない。推測で作らずに止めた。
- 指示の本文を、もう一度貼っていただけますか。
