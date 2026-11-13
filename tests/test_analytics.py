import json
import pytest
from pandas_mcp.analytics import *

def test_counts_and_nulls(dataset):
    assert aggregate_data(dataset,'count')['value']==4
    assert aggregate_data(dataset,'count','age')['value']==3
    assert aggregate_data(dataset,'mean','value')['value']==20
    assert aggregate_data(dataset,'sum','value',[{'column':'group','operator':'eq','value':'B'}])['value'] is None
    assert aggregate_data(dataset,'sum','survived')['value']==2

def test_filter_exact_count_and_pagination(dataset):
    result=filter_dataset(dataset,[{'column':'age','operator':'gt','value':30}],limit=1)
    assert result['matched_rows']==2 and result['truncated']
    assert result['rows'][0]['age']==40
    assert filter_dataset(dataset,[{'column':'group','operator':'is_null'}])['matched_rows']==1
    assert filter_dataset(dataset,[{'column':'task','operator':'contains','value':'.*'}])['matched_rows']==0

def test_groupby(dataset):
    result=groupby_data(dataset,['group'],{'value':'mean','task':'size'},sort_by='task_size')
    assert result['total_groups']==3
    assert result['rows'][0]['value_mean']==20
    assert result['rows'][0]['task_size']==2
    assert any(r['group'] is None for r in result['rows'])
    json.dumps(result,allow_nan=False)

def test_summary_empty(dataset):
    r=get_column_summary(dataset,'age',[{'column':'age','operator':'gt','value':999}])
    assert r['rows']==0 and r['statistics']['mean'] is None

@pytest.mark.parametrize('func,args',[
 (aggregate_data,('execute','value')),
 (aggregate_data,('sum','task')),
 (get_column_summary,('missing',)),
 (filter_dataset,([{'column':'age','operator':'eval','value':'__import__("os")'}],)),
 (filter_dataset,([{'column':'age','operator':'gt','value':'twenty'}],)),
])
def test_validation(dataset,func,args):
    with pytest.raises(ValueError):func(dataset,*args)

def test_date_comparison(storage):
    from services.datasets import save_dataset
    frame=pd.DataFrame({'planned':['2026-01-01','2026-01-03','2026-01-01'],
                        'actual':['2026-01-03','2026-01-02',None]})
    identifier=save_dataset(frame,{'name':'dates.csv'})['dataset_id']
    result=compare_dates(identifier,'planned','actual')
    assert result['late_rows']==1 and result['valid_pairs']==2 and result['unknown_pairs']==1
    assert result['mean_delay_days']==.5
