import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os
import secrets
import threading
import time
from pathlib import Path
from flask import Flask, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from config import settings
from services.datasets import inspect_file, read_table, save_dataset, metadata
from agent import mcp_client
from agent.ai_agent import answer, ConfigurationError

ALLOWED_TOOLS = {'pandas_get_dataset_info', 'pandas_get_column_summary', 'pandas_aggregate_data',
                 'pandas_groupby_data', 'pandas_filter_dataset', 'pandas_compare_dates', 'rag_rag_load_dataset',
                 'rag_rag_search_dataset', 'rag_rag_get_dataset_info'}

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    app.config.update(MAX_CONTENT_LENGTH=settings.MAX_UPLOAD_MB*1024*1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                      SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true')
    settings.UPLOAD_FOLDER.mkdir(parents=True,exist_ok=True)
    (settings.ROOT/'logs').mkdir(exist_ok=True)
    handler = RotatingFileHandler(settings.ROOT/'logs/app.log',maxBytes=1_000_000,backupCount=2)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    app.logger.addHandler(handler)
    histories = {}; history_lock = threading.Lock()

    @app.before_request
    def protection():
        session.setdefault('sid', secrets.token_hex(32))
        session.setdefault('csrf', secrets.token_hex(32))
        if request.method in {'POST','DELETE','PUT'}:
            if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''), session['csrf']):
                return jsonify(error='Request expired. Reload the page and try again.'),403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(Exception)
    def errors(exc):
        if isinstance(exc,HTTPException): return jsonify(error=exc.description),exc.code
        if isinstance(exc,(ValueError,ConfigurationError)): return jsonify(error=str(exc)),400
        if isinstance(exc,TimeoutError): return jsonify(error='The service timed out. Try a smaller request or check the aggregator.'),504
        app.logger.error('Request failed')
        return jsonify(error='Service unavailable. Check the aggregator, API configuration and logs/app.log.'),503

    def active():
        if not session.get('dataset_id'): raise ValueError('Upload and activate a dataset first.')
        return session['dataset_id']

    @app.get('/')
    def index(): return render_template('index.html',csrf=session['csrf'],max_mb=settings.MAX_UPLOAD_MB)

    @app.get('/api/status')
    def status():
        try:
            names=asyncio.run(mcp_client.health()); online=True
        except Exception:
            names=[];online=False
        return jsonify(aggregator=online, tools=names,
                       llm_configured=bool((os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')) and os.getenv('MODEL')),
                       web_configured=bool(os.getenv('WEB_SEARCH_MCP_URL')),rag_backend=settings.RAG_BACKEND)

    @app.get('/api/dataset')
    def current():
        return jsonify(dataset=metadata(session['dataset_id']) if session.get('dataset_id') else None)

    @app.post('/api/upload')
    def upload():
        file=request.files.get('file')
        if not file or not file.filename: raise ValueError('Choose a dataset file.')
        name=secure_filename(file.filename)
        suffix=Path(name).suffix.lower()
        if suffix not in {'.csv','.xls','.xlsx'}: raise ValueError('Choose a CSV, XLS or XLSX file.')
        staging=settings.UPLOAD_FOLDER/'staging';staging.mkdir(exist_ok=True)
        p=staging/(secrets.token_hex(32)+suffix)
        file.save(p)
        try: details=inspect_file(p)
        except Exception as exc:
            p.unlink(missing_ok=True)
            raise ValueError('Unable to read file. Check its format, encoding (UTF-8 for CSV), workbook size and password protection.') from exc
        old=session.get('pending')
        if old: (staging/old['token']).unlink(missing_ok=True)
        session['pending']={'token':p.name,'name':name}
        return jsonify(name=name,**details)

    @app.post('/api/activate')
    def activate():
        pending=session.get('pending')
        if not pending: raise ValueError('Upload a file first.')
        body=request.get_json(silent=True) or {}
        path=settings.UPLOAD_FOLDER/'staging'/pending['token']
        fills=body.get('forward_fill',[])
        if not isinstance(fills,list) or not all(isinstance(c,str) for c in fills): raise ValueError('Forward fill must be an array of column names.')
        sheet=body.get('sheet')
        if sheet is not None and not isinstance(sheet,str): raise ValueError('Worksheet must be a name.')
        df=read_table(path,sheet,body.get('header_row',1),fills,body.get('scope_column'),body.get('scope_value'))
        info=save_dataset(df,{'name':pending['name'],'sheet':sheet,'header_row':body.get('header_row',1),
                              'scope':{'column':body.get('scope_column'),'value':body.get('scope_value')},'forward_fill':fills})
        session['dataset_id']=info['dataset_id']
        with history_lock: histories.pop(session['sid'],None)
        return jsonify(dataset=info)

    @app.post('/api/tool')
    def tool():
        dataset_id=active(); body=request.get_json(silent=True) or {}
        name=body.get('tool'); arguments=body.get('arguments',{})
        if name not in ALLOWED_TOOLS: raise ValueError('Unsupported direct tool.')
        if not isinstance(arguments,dict): raise ValueError('Arguments must be an object.')
        arguments['dataset_id']=dataset_id
        return jsonify(result=asyncio.run(mcp_client.call(name,arguments)))

    @app.post('/api/chat')
    def chat():
        dataset_id=active(); body=request.get_json(silent=True) or {}; question=body.get('question','')
        if not isinstance(question,str) or not question.strip() or len(question)>8000:
            raise ValueError('Enter a question of 1-8,000 characters.')
        sid=session['sid']
        with history_lock:
            now=time.time()
            for key in list(histories):
                if now-histories[key]['time']>3600: histories.pop(key)
            if sid not in histories:
                if len(histories)>=1000: histories.pop(next(iter(histories)))
                histories[sid]={'time':now,'messages':[],'busy':False,'dataset_id':dataset_id}
            state=histories[sid]
            if state['busy']: return jsonify(error='A question is already running in this session.'),409
            state['busy']=True
            history=list(state['messages']) if state['dataset_id']==dataset_id else []
        try:
            result=asyncio.run(answer(question,dataset_id,history))
            with history_lock:
                state['messages']=(history+[{'role':'user','content':question},{'role':'assistant','content':result['answer']}])[-12:]
                state['time']=time.time();state['dataset_id']=dataset_id
            return jsonify(result)
        finally:
            with history_lock: state['busy']=False
    return app

if __name__ == '__main__':
    create_app().run(host=os.getenv('FLASK_HOST','127.0.0.1'),port=int(os.getenv('FLASK_PORT','5000')),
                     debug=os.getenv('FLASK_DEBUG','false').lower()=='true', use_reloader=False)
