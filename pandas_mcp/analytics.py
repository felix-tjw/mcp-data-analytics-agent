"""Exact calculations only: no eval, query strings, SQL or generated Python."""
import operator
import pandas as pd
from pandas.api.types import is_numeric_dtype
from services.datasets import load_dataset, metadata, clean
OPS = {'eq': operator.eq, 'ne': operator.ne, 'gt': operator.gt, 'ge': operator.ge,
       'lt': operator.lt, 'le': operator.le}
AGGS = {'count', 'sum', 'mean', 'min', 'max', 'size', 'nunique'}

def column(df, name):
    if name not in df.columns: raise ValueError(f'Unknown column {name!r}. Available: {list(df.columns)}')
    return df[name]

def validate_agg(df, name, function):
    if function not in AGGS: raise ValueError(f'Unsupported aggregation. Choose {sorted(AGGS)}')
    s = column(df, name)
    if function in {'sum', 'mean'} and not is_numeric_dtype(s):
        raise ValueError(f'{name!r} is not numeric. Clean the source data before using {function}.')

def filtered(df, conditions=None):
    if not isinstance(conditions, (list, type(None))) or len(conditions or []) > 20:
        raise ValueError('Supply at most 20 filter conditions joined by AND.')
    mask = pd.Series(True, index=df.index)
    for cond in conditions or []:
        if not isinstance(cond, dict): raise ValueError('Each condition must be an object.')
        s = column(df, cond.get('column')); op = cond.get('operator'); value = cond.get('value')
        if op == 'is_null': part = s.isna()
        elif op == 'not_null': part = s.notna()
        elif op == 'in':
            if not isinstance(value, list): raise ValueError('The in operator needs an array.')
            part = s.isin(value) & s.notna()
        elif op == 'contains':
            if not isinstance(value, str): raise ValueError('contains needs a string.')
            part = s.astype('string').str.contains(value, regex=False, case=False, na=False)
        elif op in OPS:
            if value is None: raise ValueError('Use is_null/not_null for missing values.')
            try: part = OPS[op](s, value) & s.notna()
            except (TypeError, ValueError) as exc: raise ValueError('Filter value has an incompatible type.') from exc
        else: raise ValueError(f'Unsupported filter operator: {op}')
        mask &= part.fillna(False)
    return df.loc[mask]

def get_dataset_info(dataset_id: str) -> dict:
    """Return name, row count, column names/types, null counts and preview."""
    return metadata(dataset_id)

def get_column_summary(dataset_id: str, column_name: str, conditions: list[dict] | None = None) -> dict:
    """Describe a column after optional AND filters; nulls are excluded from statistics."""
    df = filtered(load_dataset(dataset_id), conditions); s = column(df, column_name)
    return clean({'column': column_name, 'rows': len(df), 'missing': int(s.isna().sum()),
                  'statistics': s.describe().to_dict(),
                  'top_values': [{'value': k, 'count': int(v)} for k,v in s.value_counts(dropna=False).head(20).items()]})

def aggregate_data(dataset_id: str, function: str, column_name: str | None = None,
                   conditions: list[dict] | None = None) -> dict:
    """count without column counts rows; count with column excludes nulls. sum/mean require numeric data.
    For a binary survival column, sum counts survivors and mean computes survival rate.
    Filters use column/operator/value with eq, ne, gt, ge, lt, le, in, contains, is_null, not_null.
    """
    df = filtered(load_dataset(dataset_id), conditions)
    if column_name is None:
        if function not in {'count', 'size'}: raise ValueError('This aggregation requires a column.')
        value = len(df); missing = None
    else:
        validate_agg(df, column_name, function); s = df[column_name]; missing = int(s.isna().sum())
        if function == 'sum': value = s.sum(min_count=1)
        elif function == 'size': value = len(s)
        else: value = getattr(s, function)()
    return clean({'function': function, 'column': column_name, 'value': value, 'matched_rows': len(df), 'missing': missing})

def groupby_data(dataset_id: str, group_by: list[str], aggregations: dict[str, str],
                 conditions: list[dict] | None = None, limit: int = 100,
                 sort_by: str | None = None, descending: bool = True) -> dict:
    """Group by one or more columns. aggregations maps measure column to function.
    size counts rows including missing measures; count counts non-null measures. Null group keys are retained.
    Output measure columns are named COLUMN_FUNCTION. Optional sorting occurs before result limit.
    """
    df = filtered(load_dataset(dataset_id), conditions)
    if not group_by or len(group_by) > 5 or len(set(group_by)) != len(group_by): raise ValueError('Choose 1-5 unique grouping columns.')
    if not aggregations or len(aggregations) > 10: raise ValueError('Choose 1-10 measures.')
    for c in group_by: column(df,c)
    named = {}
    for c,f in aggregations.items():
        validate_agg(df,c,f)
        alias = f'{c}_{f}'
        if alias in group_by: raise ValueError('Measure alias conflicts with a grouping column.')
        named[alias] = pd.NamedAgg(column=c, aggfunc=(lambda s: s.sum(min_count=1)) if f == 'sum' else f)
    result = df.groupby(group_by, dropna=False, observed=True).agg(**named).reset_index()
    if sort_by:
        column(result,sort_by); result=result.sort_values(sort_by,ascending=not descending,na_position='last')
    if not 1 <= limit <= 1000: raise ValueError('limit must be 1-1000.')
    return clean({'rows': result.head(limit).to_dict('records'), 'total_groups': len(result),
                  'matched_rows': len(df), 'truncated': len(result)>limit,
                  'missing_policy': 'Null groups retained; numeric aggregates exclude nulls; all-null sums return null.'})

def filter_dataset(dataset_id: str, conditions: list[dict], columns: list[str] | None = None,
                   limit: int = 100, offset: int = 0) -> dict:
    """Return bounded records matching AND conditions and exact total matched count. Never use returned page length as total."""
    df = filtered(load_dataset(dataset_id), conditions)
    if not 1 <= limit <= 1000 or offset < 0: raise ValueError('Invalid limit or offset.')
    if columns:
        for c in columns: column(df,c)
        df = df[columns]
    return clean({'rows': df.iloc[offset:offset+limit].to_dict('records'), 'matched_rows': len(df),
                  'offset': offset, 'truncated': offset+limit<len(df)})

def compare_dates(dataset_id: str, planned_column: str, actual_column: str,
                  conditions: list[dict] | None = None, date_format: str = 'ISO8601',
                  limit: int = 100) -> dict:
    """Compare actual minus planned dates in days; positive means late. Missing/invalid dates remain unknown.
    Use this for actual start vs planned start, or actual end vs planned end. Default parses ISO dates;
    supply an explicit format such as %d/%m/%Y for ambiguous strings. Does not infer delay for unfinished tasks.
    """
    df = filtered(load_dataset(dataset_id), conditions)
    if not 1 <= limit <= 1000: raise ValueError('limit must be 1-1000.')
    if any(c in df for c in ('_delay_days', '_record')): raise ValueError('Reserved output column already exists.')
    planned = column(df, planned_column); actual = column(df, actual_column)
    if (is_numeric_dtype(planned) and planned.notna().any()) or (is_numeric_dtype(actual) and actual.notna().any()):
        raise ValueError('Numeric Excel serial dates must first be converted to date cells in the source workbook.')
    try:
        p = pd.to_datetime(planned, format=date_format, errors='coerce', utc=True)
        a = pd.to_datetime(actual, format=date_format, errors='coerce', utc=True)
    except (TypeError, ValueError) as exc: raise ValueError('Invalid date format.') from exc
    delay = (a-p).dt.total_seconds()/86400
    result = df.copy(); result['_record'] = df.index+1; result['_delay_days'] = delay
    result = result.sort_values('_delay_days', ascending=False, na_position='last')
    return clean({'rows': result.head(limit).to_dict('records'), 'matched_rows': len(df),
                  'valid_pairs': int(delay.notna().sum()), 'unknown_pairs': int(delay.isna().sum()),
                  'late_rows': int((delay>0).sum()), 'mean_delay_days': delay.mean(),
                  'truncated': len(df)>limit, 'definition': 'actual minus planned; positive = late'})
