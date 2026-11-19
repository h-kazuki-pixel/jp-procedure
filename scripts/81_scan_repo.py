"""公開用のフォルダに、プロジェクト ID・プロジェクト番号・組織のドメイン・手元のパス・メールアドレスが残っていないかを探す。
.gz は中を展開して探す。.git は見ない。標準ライブラリだけ。
使い方: python3 scripts/81_scan_repo.py <公開用のフォルダ> [公開しない文字列の一覧]   見つかれば終わりの状態 1。
公開しない文字列(プロジェクト番号・組織のドメイン・手元の利用者名など)は、このファイルに書かず、別のファイル(1 行に 1 つ。公開しない)で渡す。"""
import os, re, sys, gzip, zipfile, collections
ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
ALLOW_MAIL = {'41898282+github-actions[bot]@users.noreply.github.com'}   # GitHub Actions の bot(ワークフローの commit に使う)
PAT = {
    'プロジェクト ID(gcloud・URL の形)': re.compile(r'(?:pkg\.dev/|projects/|--project[ =]|gs://)jp-procedure(?![-\w])|@jp-procedure\.iam\.gserviceaccount|プロジェクト `jp-procedure`'),
    'プロジェクト番号の形(12 桁)': re.compile(r'(?:projects/|jp-procedure-sparql-|^|[^0-9])[0-9]{12}-compute@|jp-procedure-sparql-[0-9]{9,}'),
    '手元のパス': re.compile(r'/Users/[A-Za-z]|/private/tmp/claude|/home/[a-z][a-z0-9_-]*/|~/work/'),
    'メールアドレス': re.compile(r'[A-Za-z0-9][A-Za-z0-9._%+\-\[\]]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}'),
}
if len(sys.argv) > 2:
    for k, w in enumerate(x.strip() for x in open(sys.argv[2], encoding='utf-8') if x.strip()):
        PAT[f'公開しない文字列 {k + 1}'] = re.compile(re.escape(w), re.I)
SELF = os.path.abspath(__file__)
hits = collections.defaultdict(list); nfiles = 0; ngz = 0; nbytes = 0
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [x for x in dns if x != '.git']
    for fn in sorted(fns):
        p = os.path.join(dp, fn); rel = os.path.relpath(p, ROOT)
        me = os.path.abspath(p) == SELF or rel in (os.path.join('scripts', '81_scan_repo.py'), os.path.join('scripts', '80_make_repo.py'))   # 置き換えや探す形を書いた 80・81 は、公開しない文字列だけを探す
        raw = open(p, 'rb').read()
        if fn.endswith('.gz'): raw = gzip.decompress(raw); ngz += 1
        elif fn.endswith('.zip'): raw = b''.join(zipfile.ZipFile(p).read(n) for n in zipfile.ZipFile(p).namelist())
        nfiles += 1; nbytes += len(raw)
        t = raw.decode('utf-8', errors='ignore')
        for k, rx in PAT.items():
            if me and not k.startswith('公開しない'): continue
            for m in rx.finditer(t):
                if k == 'メールアドレス' and (m.group(0) in ALLOW_MAIL or t[max(0, m.start() - 17):m.start()].endswith('<PROJECT_NUMBER>-')): continue   # 置き換え文字のアカウント名
                hits[k].append((rel, m.group(0)))
print(f'# {ROOT}: ファイル {nfiles}(うち gzip を展開して探したもの {ngz})、展開後 {nbytes:,} バイト')
for k in PAT:
    h = hits.get(k, [])
    show = (lambda b: b) if not k.startswith('公開しない') else (lambda b: '(伏せる)')
    print(f'  {k}: {len(h)} 件' + ('' if not h else '  例: ' + ', '.join(f'{a}「{show(b)}」' for a, b in h[:5])))
sys.exit(1 if hits else 0)
