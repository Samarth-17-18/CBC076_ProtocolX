<script>
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const API_BASE = window.location.origin.includes('8000') ? '' : 'http://127.0.0.1:8000';
let tt,filter='all',dirty=false,admin=null;

let queue=[];
let people=[];
let events=[];
let summaryStats={pending:0,cleared:0,escalated:0,officers:0,weekly:[52,68,45,80,92,30,24]};

function go(id){
  if(!admin&&id!=='login'&&id!=='bye')id='login';
  document.body.classList.toggle('auth',!admin);
  $$('.page').forEach(p=>p.classList.toggle('active',p.id===id));
  $$('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.page===id));
  scrollTo({top:0,behavior:'smooth'});
  if(admin){
    refreshAllData();
  }
}

function toast(m){
  const t=$('#toast');t.textContent=m;t.classList.add('show');
  clearTimeout(tt);tt=setTimeout(()=>t.classList.remove('show'),2600);
}

async function refreshAllData(){
  await Promise.all([
    fetchSummary(),
    fetchQueue(),
    fetchPeople(),
    fetchAudit(),
    fetchPolicy()
  ]);
  draw();
}

async function fetchSummary(){
  try{
    const res=await fetch(`${API_BASE}/api/admin/summary`);
    if(res.ok) summaryStats = await res.json();
  }catch(e){console.warn('Summary API error:',e);}
}

async function fetchQueue(){
  try{
    const res=await fetch(`${API_BASE}/api/admin/queue`);
    if(res.ok){
      const data=await res.json();
      queue=data.map(d=>({
        id:d.id,
        n:d.name,
        d:d.department,
        o:d.overlap,
        s:d.status
      }));
    }
  }catch(e){console.warn('Queue API error:',e);}
}

async function fetchPeople(){
  try{
    const res=await fetch(`${API_BASE}/api/admin/people`);
    if(res.ok){
      const data=await res.json();
      people=data.map(p=>({
        id:p.id,
        n:p.name,
        d:p.department,
        r:p.role,
        u:p.monthly_scans,
        c:p.color || 'var(--green)'
      }));
    }
  }catch(e){console.warn('People API error:',e);}
}

async function fetchAudit(){
  try{
    const res=await fetch(`${API_BASE}/api/admin/audit?limit=25`);
    if(res.ok){
      const data=await res.json();
      events=data.map(ev=>[
        ev.icon || '✓',
        ev.color || '',
        ev.action,
        ev.detail,
        ev.time
      ]);
    }
  }catch(e){console.warn('Audit API error:',e);}
}

async function fetchPolicy(){
  try{
    const res=await fetch(`${API_BASE}/api/admin/policy`);
    if(res.ok){
      const p=await res.json();
      if($('#t1')) $('#t1').value = p.overlap_threshold;
      if($('#rt1')) $('#rt1').textContent = p.overlap_threshold + '%';
      if($('#t2')) $('#t2').value = p.paraphrase_threshold;
      if($('#rt2')) $('#rt2').textContent = p.paraphrase_threshold + '%';
      if($('#sw1')) $('#sw1').classList.toggle('on', p.cross_language);
      if($('#sw2')) $('#sw2').classList.toggle('on', p.ai_signal);
      if($('#sw3')) $('#sw3').classList.toggle('on', p.ignore_bibliography);
      dirty = false;
      if($('#dirty')) $('#dirty').textContent = 'Loaded from server policy.';
    }
  }catch(e){console.warn('Policy API error:',e);}
}

const cnt=s=>queue.filter(q=>q.s===s).length;

function draw(){
  $('#ostats').innerHTML=`<div class="stat"><label>Waiting for review</label><strong>${String(summaryStats.pending || cnt('pending')).padStart(2,'0')}</strong><small>Need a human decision</small></div><div class="stat"><label>Cleared</label><strong>${String(summaryStats.cleared || cnt('cleared')).padStart(2,'0')}</strong><small>Seal applied</small></div><div class="stat"><label>Escalated</label><strong>${String(summaryStats.escalated || cnt('escalated')).padStart(2,'0')}</strong><small>Sent to the board</small></div><div class="stat"><label>Active officers</label><strong>${String(summaryStats.officers || people.length).padStart(2,'0')}</strong><small>Across departments</small></div>`;
  
  const weekly = summaryStats.weekly || [52,68,45,80,92,30,24];
  $('#chart').innerHTML=weekly.map(h=>`<div class="bar" style="height:${Math.min(100,h)}%"></div>`).join('');
  
  const w=queue.filter(q=>q.s==='pending').slice(0,3);
  $('#wait').innerHTML=w.length?w.map(q=>`<div class="audit-item"><div class="audit-icon" style="background:var(--pink)">⚑</div><div style="flex:1"><b>${q.n}</b><p>${q.d} · ${q.o}% overlap</p></div></div>`).join(''):'<p class="note">All caught up. Nice.</p>';
  
  $('#seg').innerHTML=['all','pending','cleared','escalated'].map(f=>`<button class="${f===filter?'on':''}" onclick="filter='${f}';draw()">${f[0].toUpperCase()+f.slice(1)}</button>`).join('');
  
  const L=queue.map((q,i)=>[q,i]).filter(([q])=>filter==='all'||q.s===filter);
  $('#qlist').innerHTML=L.length?L.map(([q,i])=>`<div class="qrow"><div class="ov">${q.o}%</div><div class="who"><b>${q.n}</b><p>${q.d}</p></div><span class="status ${q.s==='cleared'?'':'warn'}">${q.s[0].toUpperCase()+q.s.slice(1)}</span>${q.s==='pending'?`<button class="btn small" onclick="dec(${q.id},'cleared')">Clear</button><button class="btn light small" onclick="dec(${q.id},'escalated')">Escalate</button>`:''}</div>`).join(''):'<p class="note">Nothing here.</p>';
  
  $('#plist').innerHTML=people.map(p=>`<div class="person"><div class="pa" style="background:${p.c}">${p.n[0]}</div><h3>${p.n}</h3><span class="muted" style="font-size:12px">${p.d}</span><div style="margin-top:14px"><span class="chipr">${p.r}</span></div><div class="quota"><div class="mono muted" style="font-size:10px">MONTHLY SCANS</div><div class="meter"><i style="width:${Math.min(100,p.u/43.5)}%;background:${p.c}"></i></div><small>${p.u.toLocaleString()} of 4,350</small></div></div>`).join('');
  
  $('#ec').textContent=(events.length).toLocaleString();
  $('#evl').innerHTML=events.map(e=>`<div class="audit-item"><div class="audit-icon" ${e[1]?`style="background:${e[1]}"`:''}>${e[0]}</div><div style="flex:1"><b>${e[2]}</b><p>${e[3]}</p></div><span class="mono muted" style="font-size:10px">${e[4]}</span></div>`).join('');
}

async function dec(reportId, s){
  try{
    const res = await fetch(`${API_BASE}/api/admin/queue/${reportId}/decision`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({decision: s, actor: admin || 'Admin'})
    });
    if(res.ok){
      toast(s==='cleared'?'Cleared and recorded to audit ledger.':'Escalated to board and recorded.');
      await refreshAllData();
    } else {
      toast('Failed to record decision');
    }
  }catch(err){
    console.error('Decision error:', err);
    toast('Error connecting to backend');
  }
}

function setP(n,v){
  $('#r'+n).textContent=v+'%';
  dirty=true;
  $('#dirty').textContent='You have unsaved changes.';
}

function tg(b){
  b.classList.toggle('on');
  dirty=true;
  $('#dirty').textContent='You have unsaved changes.';
}

async function savePol(){
  const payload = {
    overlap_threshold: parseFloat($('#t1') ? $('#t1').value : 15),
    paraphrase_threshold: parseFloat($('#t2') ? $('#t2').value : 80),
    cross_language: $('#sw1') ? $('#sw1').classList.contains('on') : true,
    ai_signal: $('#sw2') ? $('#sw2').classList.contains('on') : true,
    ignore_bibliography: $('#sw3') ? $('#sw3').classList.contains('on') : true
  };

  try{
    const res = await fetch(`${API_BASE}/api/admin/policy`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    if(res.ok){
      dirty=false;
      $('#dirty').textContent='No unsaved changes. (Saved to backend)';
      toast('Policy saved and written to audit trail.');
      await fetchAudit();
      draw();
    }
  }catch(e){
    toast('Error saving policy');
  }
}

async function invite(){
  const n=$('#in').value.trim(),e=$('#ie').value.trim(),r=$('#ir').value;
  if(!n||!e){toast('Add a name and an email first.');return;}
  
  try{
    const res = await fetch(`${API_BASE}/api/admin/people/invite`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name: n, email: e, role: r, department: 'Academic Integrity'})
    });
    if(res.ok){
      $('#in').value=$('#ie').value='';
      $('#inv').classList.add('hide');
      toast('Invite registered and logged in audit ledger.');
      await refreshAllData();
    }
  }catch(err){
    toast('Error sending invite');
  }
}

function signIn(e){
  e.preventDefault();
  const em=$('#ae').value.trim(),pw=$('#ap').value,a=$('#aa');
  if(!em||!pw){
    a.textContent='Enter an email and a password, or tap Try the demo.';
    a.classList.add('show');
    return false;
  }
  enter(em.split('@')[0]);
  return false;
}

function enter(n){
  admin=n[0].toUpperCase()+n.slice(1);
  $('#aa').classList.remove('show');
  $('#av').textContent=admin[0];
  toast('Welcome, '+admin+'. Governance desk ready.');
  go('overview');
}

function out(){
  admin=null;
  go('bye');
}

draw();
</script>