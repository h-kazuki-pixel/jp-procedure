import re, unicodedata
KANJI_NUM = '〇一二三四五六七八九十百千'
def jshape(s):
    """条項号などの書き方の型: 半角数字列->N, 全角数字列->Ｎ, 漢数字列->漢, 改行->⏎"""
    s = re.sub(r'[0-9]+', 'N', s)
    s = re.sub(r'[０-９]+', 'Ｎ', s)
    s = re.sub(f'[{KANJI_NUM}]+', '漢', s)
    s = s.replace('\r\n', '⏎').replace('\n', '⏎')
    return s if len(s) <= 40 else s[:40] + '…(長文)'
LAW_ENDINGS = ['施行規則', '施行令', '施行法', '規則', '省令', '政令', '命令', '府令', '告示', '令', '法律', '法', '条例', '規程', '基準']
def lawshape(s):
    """法令名の書き方の型: 末尾の種別 + 区切り/括弧/改行/条番号混入の有無"""
    t = s.strip()
    end = 'その他'
    for e in LAW_ENDINGS:
        if t.endswith(e): end = e; break
    flags = []
    if re.search(r'[\n]', s): flags.append('改行')
    if re.search(r'[、，,・／/]|及び|並びに', t): flags.append('区切り候補')
    if re.search(r'[（(]', t): flags.append('括弧')
    if re.search(r'第[0-9０-９〇一二三四五六七八九十百千]+条', t): flags.append('条番号混入')
    if t != s: flags.append('前後空白')
    return f'末尾={end}' + (('|' + '+'.join(flags)) if flags else '')
def norm(s):
    return unicodedata.normalize('NFKC', s or '').strip()
