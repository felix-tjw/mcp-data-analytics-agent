"""Validated ingestion and immutable, capability-addressed datasets shared across MCP processes."""
import io
import json
import re
import secrets
import zipfile
from pathlib import Path
import pandas as pd
from config import settings

ID = re.compile(r'^[a-f0-9]{64}$')

def dataset_dir(dataset_id):
    if not isinstance(dataset_id, str) or not ID.fullmatch(dataset_id):
        raise ValueError('Invalid dataset identifier.')
    return settings.UPLOAD_FOLDER / dataset_id

def clean(value):
    # Pandas converts NaN/NaT/inf to JSON null, including nested values.
    return json.loads(pd.Series([value], dtype=object).to_json(orient='values', date_format='iso'))[0]

def inspect_file(path):
    suffix = Path(path).suffix.lower()
    if suffix == '.csv':
        return {'sheets': ['CSV'], 'preview': {'CSV': clean(pd.read_csv(path, header=None, nrows=15).values.tolist())}}
    if suffix not in {'.xls', '.xlsx'}:
        raise ValueError('Only CSV, XLS and XLSX files are supported.')
    if suffix == '.xlsx':
        with zipfile.ZipFile(path) as z:
            if sum(i.file_size for i in z.infolist()) > 150 * 1024 * 1024:
                raise ValueError('Expanded workbook exceeds 150 MB.')
    with pd.ExcelFile(path) as book:
        if len(book.sheet_names) > 50:
            raise ValueError('A maximum of 50 worksheets is supported.')
        return {'sheets': book.sheet_names, 'preview': {
            s: clean(pd.read_excel(book, sheet_name=s, header=None, nrows=15).iloc[:, :20].values.tolist())
            for s in book.sheet_names}}

def read_table(path, sheet=None, header_row=1, forward_fill=None, scope_column=None, scope_value=None):
    if isinstance(header_row, bool) or not isinstance(header_row, int) or not 1 <= header_row <= 500:
        raise ValueError('Header row must be an integer from 1 to 500 (one-based).')
    kwargs = {'header': header_row - 1, 'nrows': settings.MAX_ROWS + 1}
    if Path(path).suffix.lower() == '.csv':
        df = pd.read_csv(path, **kwargs)
        headings = pd.read_csv(path, header=None, nrows=header_row).iloc[-1]
    else:
        df = pd.read_excel(path, sheet_name=sheet or 0, **kwargs)
        headings = pd.read_excel(path, sheet_name=sheet or 0, header=None, nrows=header_row).iloc[-1]
    labels = [str(c).strip() for c in headings if pd.notna(c)]
    if len(labels) != len(set(labels)):
        raise ValueError('Duplicate column headings. Rename them in the source file.')
    if len(df) > settings.MAX_ROWS or len(df.columns) > settings.MAX_COLUMNS:
        raise ValueError(f'Maximum {settings.MAX_ROWS:,} rows and {settings.MAX_COLUMNS} columns supported.')
    df = df.dropna(how='all').dropna(axis=1, how='all')
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty or not len(df.columns):
        raise ValueError('No data rows found. Select the correct worksheet and header row.')
    if df.columns.duplicated().any() or any(not c or c.startswith('Unnamed:') for c in df.columns):
        raise ValueError('Missing or duplicate column headings. Choose a complete header row.')
    # Whitespace-only cells are missing; never replace missing progress with zero.
    df = df.replace(r'^\s*$', None, regex=True)
    for col in forward_fill or []:
        if col not in df: raise ValueError(f'Unknown forward-fill column: {col}')
        df[col] = df[col].ffill()
    if scope_column:
        if scope_column not in df: raise ValueError('Project scope column does not exist.')
        df = df[df[scope_column].astype(str).str.strip() == str(scope_value).strip()]
        if df.empty: raise ValueError('The selected project scope matched no rows.')
    return df.reset_index(drop=True)

def save_dataset(df, metadata):
    dataset_id = secrets.token_hex(32)
    folder = dataset_dir(dataset_id)
    folder.mkdir(parents=True)
    (folder / 'table.json').write_text(df.to_json(orient='table', index=False, date_format='iso'), encoding='utf-8')
    info = {**metadata, 'dataset_id': dataset_id, 'rows': len(df), 'columns': list(df.columns),
            'dtypes': {c: str(t) for c,t in df.dtypes.items()}, 'preview': clean(df.head(20).to_dict('records')),
            'missing': {c: int(n) for c,n in df.isna().sum().items()}}
    (folder / 'metadata.json').write_text(json.dumps(info, ensure_ascii=False), encoding='utf-8')
    return info

def load_dataset(dataset_id):
    p = dataset_dir(dataset_id) / 'table.json'
    if not p.exists(): raise ValueError('Dataset not found. Upload and activate it first.')
    return pd.read_json(io.StringIO(p.read_text(encoding='utf-8')), orient='table')

def metadata(dataset_id):
    p = dataset_dir(dataset_id) / 'metadata.json'
    if not p.exists(): raise ValueError('Dataset not found.')
    return json.loads(p.read_text(encoding='utf-8'))
