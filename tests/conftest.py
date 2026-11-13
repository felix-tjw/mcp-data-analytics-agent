import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from config import settings
from services.datasets import save_dataset
@pytest.fixture
def storage(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'UPLOAD_FOLDER',tmp_path/'uploads')
    monkeypatch.setattr(settings,'VECTOR_STORE_PATH',tmp_path/'vectors')
    monkeypatch.setattr(settings,'RAG_BACKEND','tfidf')
    return tmp_path
@pytest.fixture
def dataset(storage):
    df=pd.DataFrame({'group':['A','A','B',None], 'age':[20,40,60,None], 'value':[10,30,None,None],
                     'survived':[1,0,1,0], 'task':['Debt repayment','Debt schedule','API service','Audit UI']})
    return save_dataset(df,{'name':'test.csv'})['dataset_id']
