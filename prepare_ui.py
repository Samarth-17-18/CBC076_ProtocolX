import os

with open('synapse_reimagined.html', 'r', encoding='utf-8') as f:
    base_html = f.read()

# Replace the script section in synapse_reimagined.html with live API enabled JS
old_script_start = '<script>'
old_script_end = '</script>'
start_idx = base_html.find(old_script_start)

html_head_and_body = base_html[:start_idx]

enhanced_script = """<script>
const API_BASE = (window.location.origin && (window.location.origin.includes('8001') || window.location.origin.includes('8000'))) ? '' : 'http://127.0.0.1:8001';
let selectedRole = 'user', chosenFile = null, toastTimer;
let currentReports = [];
let currentQueue = [];

function go(id){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === id));
  document.querySelectorAll('.nav button').forEach(b => b.classList.toggle('active', b.dataset.page === id));
  window.scrollTo({top: 0, behavior: 'smooth'});
  if(!['home','dashboard','submit','admin','audit'].includes(id)) {
    document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
  }
  if(id === 'dashboard') loadDashboardData();
  if(id === 'admin') loadAdminData();
  if(id === 'audit') loadAuditData();
}

function toast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2800);
}

function chooseRole(role){
  selectedRole = role;
  document.getElementById('userRole').classList.toggle('selected', role === 'user');
  document.getElementById('adminRole').classList.toggle('selected', role === 'admin');
}

function loginDemo(){
  const em = document.getElementById('email').value.trim();
  const pw = document.getElementById('password').value;
  const a = document.getElementById('loginAlert');
  a.classList.add('show');
  if(em === 'admin@protocolx' && pw === 'admin.123') {
    a.textContent = 'Authenticated as ProtocolX Super-Admin! Directing to Governance Desk...';
    selectedRole = 'admin';
  } else {
    a.textContent = 'Signed in successfully. Entering workspace...';
  }
  setTimeout(() => go(selectedRole === 'admin' ? 'admin' : 'dashboard'), 600);
}

function pickedFile(input){
  chosenFile = input.files && input.files[0];
  showFile();
}

function showFile(){
  if(!chosenFile) return;
  const p = document.getElementById('filePill');
  p.style.display = 'block';
  p.textContent = '↳ ' + chosenFile.name + ' · ' + (chosenFile.size / 1024 / 1024).toFixed(2) + ' MB';
  if(!document.getElementById('docTitle').value) {
    document.getElementById('docTitle').value = chosenFile.name.replace(/\\.[^.]+$/, '');
  }
}

function dropFile(e){
  e.preventDefault();
  document.getElementById('dropzone').classList.remove('drag');
  const f = e.dataTransfer.files[0];
  if(f){
    chosenFile = f;
    showFile();
  }
}

async function startScan(){
  const a = document.getElementById('uploadAlert');
  if(!chosenFile){
    a.textContent = 'Choose or drop a file first to begin analysis.';
    a.classList.add('show');
    return;
  }
  a.classList.remove('show');
  const title = document.getElementById('docTitle').value || chosenFile.name;
  document.getElementById('receivedText').textContent = '“' + title + '” is running through NLP sentence embeddings and corpus comparison...';
  document.getElementById('scanProgress').style.width = '45%';
  document.getElementById('progressLabel').textContent = '45% · TOKENIZING & EMBEDDING';
  go('received');

  const formData = new FormData();
  formData.append('file', chosenFile);
  formData.append('title', title);
  formData.append('author', 'Researcher');

  try {
    document.getElementById('scanProgress').style.width = '75%';
    document.getElementById('progressLabel').textContent = '75% · CORPUS BENCHMARKING';
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData
    });

    if(res.ok){
      const data = await res.json();
      document.getElementById('scanProgress').style.width = '100%';
      document.getElementById('progressLabel').textContent = '100% · ANALYSIS COMPLETE';
      toast('Similarity analysis complete!');
      setTimeout(() => {
        if(data.report_id) {
          openReport(data.report_id);
        } else {
          go('results');
        }
      }, 500);
    } else {
      document.getElementById('scanProgress').style.width = '100%';
      toast('Upload processed in demo mode');
      setTimeout(() => go('results'), 500);
    }
  } catch(err) {
    console.warn('API upload error, using local simulation:', err);
    document.getElementById('scanProgress').style.width = '100%';
    document.getElementById('progressLabel').textContent = '100% · LOCAL DEMO RESULT';
    setTimeout(() => go('results'), 500);
  }
}

function finishScan(){
  document.getElementById('scanProgress').style.width = '100%';
  document.getElementById('progressLabel').textContent = '100% · DEMO COMPLETE';
  go('results');
}

async function loadDashboardData(){
  try {
    const res = await fetch(`${API_BASE}/api/reports`);
    if(res.ok){
      const data = await res.json();
      currentReports = data;
      renderRecentSubmissions(data);
    }
  } catch(e) {
    console.warn('Reports fetch error:', e);
  }
  try {
    const res = await fetch(`${API_BASE}/api/admin/summary`);
    if(res.ok){
      const sum = await res.json();
      // Update weekly bars if available
      if(sum.weekly && sum.weekly.length){
        const maxVal = Math.max(...sum.weekly);
        const bars = document.querySelectorAll('.chart .bar');
        sum.weekly.slice(0, bars.length).forEach((val, idx) => {
          if(bars[idx]) bars[idx].style.height = Math.round((val / maxVal) * 90 + 10) + '%';
        });
      }
    }
  } catch(e) {}
}

function renderRecentSubmissions(reports){
  const tbody = document.querySelector('#dashboard .table tbody');
  if(!tbody || !reports || !reports.length) return;
  tbody.innerHTML = reports.slice(0, 6).map(r => {
    const overlap = Math.round(r.overall_similarity || 0);
    const badgeCls = overlap > 25 ? 'status warn' : (overlap > 15 ? 'status pink' : 'status');
    const badgeText = overlap > 25 ? 'High Overlap' : (overlap > 15 ? 'Needs Context' : 'Cleared');
    const title = r.doc_a_title || 'Document';
    const dateStr = r.created_at ? r.created_at.slice(0, 10) : 'Today';
    return `<tr style="cursor:pointer" onclick="openReport(${r.id})">
      <td><b>${title}</b><br><span class="muted">Report #SYN-${r.id} vs ${r.doc_b_title || 'Corpus'}</span></td>
      <td>${dateStr}</td>
      <td><b>${overlap}%</b></td>
      <td><span class="${badgeCls}">${badgeText}</span></td>
    </tr>`;
  }).join('');
}

async function openReport(reportId){
  try {
    const res = await fetch(`${API_BASE}/api/reports/${reportId}`);
    if(res.ok){
      const det = await res.json();
      document.getElementById('resultTitle').textContent = det.doc_a_title || 'Manuscript Report';
      const score = Math.round(det.overall_similarity || 0);
      document.getElementById('resultScore').innerHTML = `${score}<span>%</span>`;
      
      const ring = document.querySelector('.result-ring');
      if(ring){
        ring.style.background = `conic-gradient(var(--green) 0 ${score}%, #e6e9df ${score}% 100%)`;
      }
      
      // Update evidence items
      const passageReview = document.querySelector('#results .panel:last-child');
      if(passageReview && det.evidence && det.evidence.length){
        passageReview.innerHTML = det.evidence.map((ev, i) => {
          const type = ev.type || 'Overlap';
          const sentA = ev.sentence_a || '';
          const sentB = ev.sentence_b || '';
          const sc = Math.round(ev.score || 0);
          return `<div class="audit-item">
            <div class="audit-icon" style="background:${sc > 80 ? 'var(--pink)' : 'var(--blue)'}">0${i+1}</div>
            <div style="flex:1">
              <b>${type} Match (${sc}% similarity)</b>
              <p style="margin:4px 0"><b>Manuscript:</b> “${sentA}”</p>
              ${sentB ? `<p style="margin:4px 0;color:var(--muted)"><b>Source Match:</b> “${sentB}”</p>` : ''}
              <span class="status ${sc > 80 ? 'warn' : ''}">${ev.reason || 'Similarity detected'}</span>
            </div>
          </div>`;
        }).join('');
      }
    }
  } catch(e) {
    console.warn('Report fetch error:', e);
  }
  go('results');
}

async function loadAdminData(){
  try {
    const res = await fetch(`${API_BASE}/api/admin/queue`);
    if(res.ok){
      currentQueue = await res.json();
      renderAdminQueue(currentQueue);
    }
  } catch(e) {}
  try {
    const res = await fetch(`${API_BASE}/api/admin/policy`);
    if(res.ok){
      const pol = await res.json();
      if(document.getElementById('threshold')){
        document.getElementById('threshold').value = pol.overlap_threshold;
        document.getElementById('thresholdLabel').textContent = pol.overlap_threshold + '%';
      }
      if(document.getElementById('paraLabel')){
        document.getElementById('paraLabel').textContent = pol.paraphrase_threshold + '%';
      }
    }
  } catch(e) {}
}

function renderAdminQueue(queue){
  const tbody = document.querySelector('#admin .table tbody');
  if(!tbody || !queue || !queue.length) return;
  tbody.innerHTML = queue.slice(0, 8).map(q => {
    const stage = q.workflow_stage || 'Evaluator 1';
    const isCleared = (q.status || '').toLowerCase() === 'cleared';
    const isEscalated = (q.status || '').toLowerCase() === 'escalated';
    const badgeCls = isCleared ? 'status' : (isEscalated ? 'status pink' : 'status warn');
    return `<tr style="cursor:pointer" onclick="openReport(${q.id})">
      <td><b>${q.name}</b><br><span class="muted">${q.department} · Stage: ${stage}</span></td>
      <td><b>${q.overlap}%</b></td>
      <td><span class="${badgeCls}">${q.raw_status || q.status}</span></td>
    </tr>`;
  }).join('');
}

async function loadAuditData(){
  try {
    const res = await fetch(`${API_BASE}/api/admin/audit?limit=15`);
    if(res.ok){
      const logs = await res.json();
      const container = document.querySelector('#audit .panel');
      if(container && logs.length){
        const items = logs.map(l => `<div class="audit-item">
          <div class="audit-icon" style="background:${l.color || 'var(--green)'}">${l.icon || '✓'}</div>
          <div style="flex:1"><b>${l.action}</b><p>${l.detail || ''} · Actor: ${l.actor || 'System'}</p></div>
          <span class="mono muted" style="font-size:10px">${l.time || ''}</span>
        </div>`).join('');
        container.innerHTML = `<div class="panel-head"><h3>Recent system events</h3><span class="status">Ledger healthy</span></div>` + items;
      }
    }
  } catch(e) {}
}

function changeMood(m){
  const r = document.documentElement;
  if(m === 'night'){
    r.style.setProperty('--paper','#17211f');
    r.style.setProperty('--white','#202d29');
    r.style.setProperty('--ink','#f3f4ec');
    r.style.setProperty('--muted','#b4c0b7');
    r.style.setProperty('--line','#394943');
    document.body.style.color = 'var(--ink)';
    document.querySelectorAll('.topbar').forEach(x => x.style.background = 'rgba(23,33,31,.9)');
  } else if(m === 'peach'){
    r.style.setProperty('--paper','#fff0e6');
    r.style.setProperty('--white','#fffaf5');
    r.style.setProperty('--ink','#3a2423');
    r.style.setProperty('--muted','#806b66');
    r.style.setProperty('--line','#f0d7ca');
    document.body.style.color = 'var(--ink)';
    document.querySelectorAll('.topbar').forEach(x => x.style.background = 'rgba(255,240,230,.9)');
  } else {
    r.style.setProperty('--paper','#f4f3ed');
    r.style.setProperty('--white','#fffef9');
    r.style.setProperty('--ink','#17221f');
    r.style.setProperty('--muted','#66716b');
    r.style.setProperty('--line','#dce1d7');
    document.body.style.color = 'var(--ink)';
    document.querySelectorAll('.topbar').forEach(x => x.style.background = 'rgba(244,243,237,.88)');
  }
  toast('Theme updated');
}

// Check initial path: if /admin was requested, navigate to admin desk
window.addEventListener('DOMContentLoaded', () => {
  if(window.location.pathname.includes('admin') || window.location.hash.includes('admin')) {
    go('admin');
  } else {
    loadDashboardData();
  }
});
</script>
</body></html>
"""

full_html = html_head_and_body + enhanced_script

# Write user UI
with open('uiux/user/synapse.html', 'w', encoding='utf-8') as f:
    f.write(full_html)
print('Wrote uiux/user/synapse.html')

# Write admin UI
admin_html = full_html.replace(
    "if(window.location.pathname.includes('admin') || window.location.hash.includes('admin')) {",
    "if(true) {"
)
with open('uiux/admin/synapse_admin.html', 'w', encoding='utf-8') as f:
    f.write(admin_html)
print('Wrote uiux/admin/synapse_admin.html')

