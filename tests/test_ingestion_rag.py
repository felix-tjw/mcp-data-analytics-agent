import pandas as pd
import pytest
from config import settings
from services.datasets import read_table,save_dataset,load_dataset,dataset_dir,inspect_file
from rag_mcp.vector_store import build,search,info

def test_workbook_layout_and_scope(storage):
    p=storage/'plan.xlsx'
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({'readme':['instructions']}).to_excel(w,sheet_name='START HERE',index=False)
        pd.DataFrame({'Project':['A','B','A'],'Completion':[1,None,0]}).to_excel(w,sheet_name='DevPlan',startrow=2,index=False)
    assert inspect_file(p)['sheets']==['START HERE','DevPlan']
    df=read_table(p,'DevPlan',3,scope_column='Project',scope_value='A')
    assert len(df)==2
    with pytest.raises(ValueError):read_table(p,'DevPlan',3,scope_column='Project',scope_value='Z')
    with pytest.raises(ValueError):read_table(p,'DevPlan',0)

def test_persistence_and_path_rejection(dataset):
    assert len(load_dataset(dataset))==4
    with pytest.raises(ValueError):dataset_dir('../../etc')

def test_retrieval_and_citations(dataset):
    assert not info(dataset)['indexed']
    assert build(dataset)['chunks']==4
    result=search(dataset,'Debt repayment',2)
    assert result['matches'][0]['record']==1
    assert result['matches'][0]['source']=='test.csv'
    assert search(dataset,'zzzzzzzzzzz')['matches']==[]
    assert search(dataset,'Debt',conditions=[{'column':'group','operator':'eq','value':'B'}])['matches']==[]
    assert info(dataset)['backend']=='tfidf'

def test_duplicate_headers(storage):
    p=storage/'duplicate.csv';p.write_text('a,a\n1,2\n')
    with pytest.raises(ValueError,match='Duplicate'):read_table(p)
