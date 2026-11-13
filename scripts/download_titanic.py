"""Download the original public exercise dataset (no credentials needed)."""
from pathlib import Path
import requests
url='https://raw.githubusercontent.com/mwaskom/seaborn-data/master/titanic.csv'
r=requests.get(url,timeout=30);r.raise_for_status()
if not r.text.startswith('survived,pclass,'): raise ValueError('Unexpected Titanic CSV format.')
p=Path(__file__).resolve().parents[1]/'data/titanic.csv'
p.write_text(r.text,encoding='utf-8'); print(f'Saved {p}')
