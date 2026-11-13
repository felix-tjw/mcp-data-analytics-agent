const $ = id => document.getElementById(id);
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let active = null, uploaded = null;
async function api(path, options={}) {
  const response = await fetch(path, {...options, headers:{'X-CSRF-Token':csrf,...(options.headers||{})}});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Request failed.');
  return body;
}
const post = (path, data) => api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
function notice(text){$('notice').textContent=text;$('notice').classList.toggle('hidden',!text);}
function table(container, rows){
  if(!rows.length){const p=document.createElement('p');p.textContent='No matching records.';container.append(p);return;}
  const cols=[...new Set(rows.flatMap(row=>Object.keys(row)))];
  const el=document.createElement('table'),head=document.createElement('thead'),tr=document.createElement('tr');
  cols.forEach(c=>{const th=document.createElement('th');th.textContent=c;tr.append(th)});head.append(tr);el.append(head);
  const tbody=document.createElement('tbody');rows.forEach(row=>{const tr=document.createElement('tr');cols.forEach(c=>{const td=document.createElement('td');td.textContent=row[c]===null||row[c]===undefined?'—':typeof row[c]==='object'?JSON.stringify(row[c]):row[c];td.title=td.textContent;tr.append(td)});tbody.append(tr)});el.append(tbody);container.append(el);
}
function renderResult(container,result){
  let value=result;
  if(Array.isArray(value)&&value[0]?.type==='text'){try{value=JSON.parse(value[0].text)}catch{}}
  if(value&&typeof value==='object'){
    const rows=value.rows||value.matches||value.preview;
    if(Array.isArray(rows)&&(!rows.length||typeof rows[0]==='object')){const wrap=document.createElement('div');wrap.className='table-scroll';table(wrap,rows);container.append(wrap);}
  }
  const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='View complete JSON result';pre.textContent=JSON.stringify(value,null,2);details.append(summary,pre);container.append(details);
  if(value?.value!==undefined){const p=document.createElement('p');p.textContent=`${value.function}: ${value.value===null?'unknown / no non-null values':value.value} · ${value.matched_rows} matched rows`;container.prepend(p);}
}
async function status(){
  $('connection').textContent='Checking services…';
  try{const s=await api('/api/status');$('connection').textContent=s.aggregator?'● MCP connected':'○ MCP offline';$('connection').classList.toggle('online',s.aggregator);$('services').textContent=`${s.tools.length} tools available · RAG: ${s.rag_backend} · Web: ${s.web_configured?'configured':'off'}`;$('chat-caption').textContent=s.llm_configured?'Answers use your configured AI provider. Review the supporting evidence.':'Set MODEL and your API key in .env for AI chat. Direct tools work without a key.';}catch(e){notice(e.message)}
}
function showDataset(data){active=data;$('dataset-info').classList.toggle('hidden',!data);$('dataset-empty').classList.toggle('hidden',!!data);if(!data)return;
  $('dataset-name').textContent=data.name+(data.sheet?' / '+data.sheet:'');$('row-count').textContent=data.rows.toLocaleString();$('column-count').textContent=data.columns.length;$('missing-count').textContent=Object.values(data.missing).reduce((a,b)=>a+b,0).toLocaleString();$('schema').replaceChildren();
  data.columns.forEach(c=>{const row=document.createElement('div');row.className='schema-row';const name=document.createElement('strong'),type=document.createElement('span');name.textContent=c;type.textContent=`${data.dtypes[c]} · ${data.missing[c]}`;row.append(name,type);$('schema').append(row)});$('data-preview').replaceChildren();table($('data-preview'),data.preview);
}
async function upload(file){if(!file)return;notice('Reading your file…');const form=new FormData();form.append('file',file);
 try{uploaded=await api('/api/upload',{method:'POST',body:form});$('import-name').textContent=uploaded.name;$('sheet').replaceChildren();uploaded.sheets.forEach(s=>{const opt=document.createElement('option');opt.value=s;opt.textContent=s;$('sheet').append(opt)});$('import-options').classList.remove('hidden');rawPreview();notice('Choose the worksheet and header row, then activate your dataset.');}catch(e){notice(e.message)}
}
function rawPreview(){const rows=uploaded.preview[$('sheet').value]||[];$('raw-preview').replaceChildren();table($('raw-preview'),rows.map((row,i)=>Object.fromEntries([['Row',i+1],...row.map((v,j)=>['Column '+(j+1),v])])));}
$('file').addEventListener('change',e=>upload(e.target.files[0]));$('sheet').addEventListener('change',rawPreview);
$('drop-zone').addEventListener('dragover',e=>{e.preventDefault();$('drop-zone').classList.add('drag')});$('drop-zone').addEventListener('dragleave',()=>$('drop-zone').classList.remove('drag'));$('drop-zone').addEventListener('drop',e=>{e.preventDefault();$('drop-zone').classList.remove('drag');upload(e.dataTransfer.files[0])});
$('activate').onclick=async()=>{$('activate').disabled=true;try{const d=await post('/api/activate',{sheet:$('sheet').value,header_row:Number($('header').value),forward_fill:$('ffill').value.split(',').map(s=>s.trim()).filter(Boolean),scope_column:$('scope-column').value||null,scope_value:$('scope-value').value||null});showDataset(d.dataset);$('import-options').classList.add('hidden');$('messages').querySelectorAll('.message').forEach(m=>m.remove());$('welcome').classList.remove('hidden');notice('Dataset activated. Analytics are ready; retrieval indexes on first use.');}catch(e){notice(e.message)}finally{$('activate').disabled=false}};
function message(role,text,error=false){$('welcome').classList.add('hidden');const el=document.createElement('div');el.className='message '+role+(error?' error':'');const label=document.createElement('div'),body=document.createElement('div');label.className='role';label.textContent=role==='user'?'You':'Agent';body.className='body';body.textContent=text;el.append(label,body);$('messages').append(el);$('messages').scrollTop=$('messages').scrollHeight;return el;}
$('chat-form').onsubmit=async e=>{e.preventDefault();const q=$('question').value.trim();if(!q)return;if(!active){notice('Upload and activate a dataset first.');return;}$('send').disabled=true;$('activate').disabled=true;message('user',q);$('question').value='';const pending=message('assistant','Analysing your question…');try{const result=await post('/api/chat',{question:q});pending.remove();const el=message('assistant',result.answer);result.tool_results.forEach(t=>{const d=document.createElement('details'),s=document.createElement('summary');s.textContent='Evidence · '+t.tool;d.append(s);renderResult(d,t.result);el.append(d)});}catch(e){pending.remove();message('assistant',e.message,true)}finally{$('send').disabled=false;$('activate').disabled=false;$('messages').scrollTop=$('messages').scrollHeight}};
$('question').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!$('send').disabled){e.preventDefault();$('chat-form').requestSubmit()}});
document.querySelectorAll('[data-question]').forEach(b=>b.onclick=()=>{$('question').value=b.dataset.question;$('question').focus()});
const examples={pandas_get_dataset_info:{},pandas_get_column_summary:{column_name:'age'},pandas_aggregate_data:{function:'count'},pandas_groupby_data:{group_by:['pclass'],aggregations:{fare:'mean'}},pandas_filter_dataset:{conditions:[{column:'age',operator:'gt',value:50},{column:'survived',operator:'eq',value:1}]},pandas_compare_dates:{planned_column:"Planned End",actual_column:"Actual End"},rag_rag_load_dataset:{},rag_rag_search_dataset:{query:'Debt Management',top_k:5},rag_rag_get_dataset_info:{}};
$('tool-select').onchange=()=>{$('tool-args').value=JSON.stringify(examples[$('tool-select').value],null,2)};
$('run-tool').onclick=async()=>{if(!active){notice('Upload and activate a dataset first.');return;}$('run-tool').disabled=true;try{const data=await post('/api/tool',{tool:$('tool-select').value,arguments:JSON.parse($('tool-args').value)});$('tool-output').replaceChildren();renderResult($('tool-output'),data.result);notice('');}catch(e){notice(e.message)}finally{$('run-tool').disabled=false}};
$('refresh-status').onclick=status;status();api('/api/dataset').then(d=>showDataset(d.dataset)).catch(e=>notice(e.message));
