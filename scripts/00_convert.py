"""Excel -> CSV(全セル文字列)。ヘッダー2行目を列名に使う。"""
import sys, csv, openpyxl
src, dst = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(src, read_only=True)
ws = wb.worksheets[0]
with open(dst, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0: continue  # 1行目は項目番号
        w.writerow(['' if v is None else str(v) for v in row])
print(src, 'sheet=', ws.title, 'max_row=', ws.max_row, 'max_col=', ws.max_column)
