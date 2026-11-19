import pandas as pd
def load(year):
    d = pd.read_csv(f'data/{year}.csv', dtype=str, keep_default_na=False)
    empty = (d.apply(lambda c: c.str.strip()) == '').all(axis=1)
    return d[~empty].reset_index(drop=True)
