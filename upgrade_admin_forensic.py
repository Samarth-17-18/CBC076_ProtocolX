import os

with open('uiux/admin/synapse_admin.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update CSS
css_to_add = """
/* Enhanced Phrase blocks */
.phrase-item {
  background: rgba(255,255,255,0.02); border: 1.5px solid var(--border); border-radius: 12px;
  padding: 12px 14px; margin-bottom: 12px; transition: .18s; cursor: pointer;
}
.phrase-item:hover {
  background: rgba(255,255,255,0.05); border-color: var(--muted);
}
.phrase-item.active {
  box-shadow: 0 0 16px rgba(0,229,153,0.3) !important;
  border-color: #fff !important;
}
.phrase-item.hl-pink {
  border-left: 5px solid var(--pink); background: rgba(255,101,153,0.09);
}
.phrase-item.hl-warn {
  border-left: 5px solid var(--warn); background: rgba(255,180,67,0.09);
}
.phrase-item.hl-blue {
  border-left: 5px solid var(--blue); background: rgba(108,213,255,0.09);
}
.phrase-item.hl-green {
  border-left: 5px solid var(--green); background: rgba(0,229,153,0.06);
}
.phrase-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 11px; }
.phrase-text { font-size: 13px; line-height: 1.7; color: #d6e8e0; }

.pill.green { background: rgba(0,229,153,0.14); color: var(--green); border: 1px solid rgba(0,229,153,0.4); }
.pill.blue { background: rgba(108,213,255,0.14); color: var(--blue); border: 1px solid rgba(108,213,255,0.4); }
.pill.pink { background: rgba(255,101,153,0.14); color: var(--pink); border: 1px solid rgba(255,101,153,0.4); }
.pill.warn { background: rgba(255,180,67,0.14); color: var(--warn); border: 1px solid rgba(255,180,67,0.4); }
"""

# Inject CSS before </style>
style_end = '</style>'
html = html.replace(style_end, css_to_add + '\n' + style_end, 1)

# 2. Replace the forensic section HTML
old_forensic_start = '<!-- FORENSIC SIDE-BY-SIDE INSPECTOR -->'
old_queue_start = '<!-- COHORT BATCH QUEUE -->'

start_idx = html.find(old_forensic_start)
end_idx = html.find(old_queue_start)

new_forensic_section = """<!-- FORENSIC SIDE-BY-SIDE INSPECTOR -->
  <section id="forensic" class="page">
    <div class="panel">
      <div class="panel-head">
        <div>
          <div class="mono" style="color:var(--green);font-size:10px">FORENSIC INVESTIGATION &amp; ALIGNMENT</div>
          <h3 id="forensicHeader">Side-by-Side Text Comparison &amp; Phrase Inspector</h3>
        </div>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <label class="mono" style="font-size:11px;color:var(--muted)">SELECT CASE:</label>
          <select id="reportSelector" class="gate-input" style="width:auto;margin:0;padding:8px 14px;font-size:12px;background:#0d1614;color:var(--text);border-color:var(--green);font-weight:600" onchange="loadForensicReport(this.value)">
            <option value="20">Case #20: student_A.txt vs student_B.txt (80.2%)</option>
          </select>
          <button class="btn green small" onclick="openNodeActionModal()">Cast Workflow Vote ✍️</button>
        </div>
      </div>

      <!-- Color Legend Bar -->
      <div style="display:flex;gap:18px;margin-bottom:18px;font:600 11px var(--font-mono);flex-wrap:wrap;background:var(--card);padding:12px 18px;border-radius:12px;border:1px solid var(--border)">
        <span style="display:flex;align-items:center;gap:6px">
          <span style="display:inline-block;width:12px;height:12px;background:var(--pink);border-radius:3px"></span>
          <span style="color:#ff8ab4">VERBATIM COPY (&gt;85% Word-for-Word)</span>
        </span>
        <span style="display:flex;align-items:center;gap:6px">
          <span style="display:inline-block;width:12px;height:12px;background:var(--warn);border-radius:3px"></span>
          <span style="color:#ffd680">PARAPHRASED (Semantic Rewrite / Synonyms)</span>
        </span>
        <span style="display:flex;align-items:center;gap:6px">
          <span style="display:inline-block;width:12px;height:12px;background:var(--blue);border-radius:3px"></span>
          <span style="color:#8ee2ff">COMMON PROMPT / TEMPLATE (Suppressed)</span>
        </span>
        <span style="display:flex;align-items:center;gap:6px">
          <span style="display:inline-block;width:12px;height:12px;background:var(--green);border-radius:3px"></span>
          <span style="color:#9cffd7">INDEPENDENT / ORIGINAL (Cleared)</span>
        </span>
      </div>

      <!-- Live Diagnostic Inspector Banner -->
      <div id="inspectorBanner" style="background:#0e1715;border:1.5px solid var(--border);border-left:5px solid var(--green);border-radius:14px;padding:16px 20px;margin-bottom:18px;transition:.2s">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div class="mono" id="inspectorCategory" style="font-size:12px;font-weight:700;color:var(--green)">
            ACTIVE PHRASE DIAGNOSTIC
          </div>
          <span class="pill" id="inspectorScore">Select Any Sentence Below</span>
        </div>
        <p id="inspectorReason" style="font-size:13px;color:#e6f3ef;margin:0;line-height:1.7">
          Click any sentence in either Document A, Document B, or the comparison table to inspect why it was flagged or cleared.
        </p>
        <div id="inspectorTerms" class="mono" style="font-size:11px;color:var(--muted);margin-top:6px;display:none"></div>
      </div>

      <!-- Side-by-Side Dual-Pane Document View -->
      <div class="forensic-grid">
        <div class="forensic-pane" id="paneDocA" style="max-height:520px">
          <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:14px">
            <b id="titleDocA" style="color:var(--green);font-size:14px">Document A: Student Manuscript</b>
            <span class="mono" style="font-size:10px;color:var(--muted)">STUDENT DRAFT</span>
          </div>
          <div id="contentDocA">Loading document sentences...</div>
        </div>

        <div class="forensic-pane" id="paneDocB" style="max-height:520px">
          <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:14px">
            <b id="titleDocB" style="color:var(--blue);font-size:14px">Document B: Corpus / Peer Reference</b>
            <span class="mono" style="font-size:10px;color:var(--muted)">CORPUS MATCH</span>
          </div>
          <div id="contentDocB">Loading comparison reference...</div>
        </div>
      </div>

      <!-- Sentence-by-Sentence Comparison Table -->
      <div style="margin-top:24px;border-top:1.5px solid var(--border);padding-top:22px">
        <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px">
          <div>
            <div class="mono" style="color:var(--green);font-size:10px">PHRASE-BY-PHRASE FORENSIC AUDIT</div>
            <h3 style="margin:2px 0 0;font-size:18px">Sentence Level Alignment &amp; Reasoning Log</h3>
          </div>
          <span class="mono" id="phraseCountLabel" style="font-size:11px;color:var(--muted)">8 Sentences Analyzed</span>
        </div>

        <table class="table" id="phraseTable">
          <thead>
            <tr>
              <th style="width:40px">#</th>
              <th style="width:31%">Sentence in Document A (Manuscript)</th>
              <th style="width:31%">Matched Sentence in Document B (Corpus)</th>
              <th style="width:14%">Score &amp; Category</th>
              <th style="width:24%">Forensic Reason (Why Flagged or Cleared)</th>
            </tr>
          </thead>
          <tbody id="phraseTableBody">
            <tr><td colspan="5" style="text-align:center;padding:24px;color:var(--muted)">Loading phrase breakdown...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  """

html = html[:start_idx] + new_forensic_section + html[end_idx:]

# 3. Update JavaScript logic
js_replacement = """
let currentPhrases = [];
let activeFocusedIndex = null;

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function initForensicView() {
  const sel = document.getElementById('reportSelector');
  if (allReports.length && sel) {
    sel.innerHTML = allReports.map(r => `
      <option value="${r.id}">#CASE-${r.id}: ${r.doc_a_title} vs ${r.doc_b_title} (${r.overlap}%)</option>
    `).join('');

    // Prefer student_A vs student_B or report 20 if present
    const demoRep = allReports.find(r => r.id === 20 || (r.doc_a_title && r.doc_a_title.includes('student_A')));
    const targetId = demoRep ? demoRep.id : allReports[0].id;
    sel.value = targetId;
    loadForensicReport(targetId);
  }
}

async function loadForensicReport(reportId) {
  try {
    const res = await fetch(`${API_BASE}/api/reports/${reportId}`);
    if (res.ok) {
      const r = await res.json();
      document.getElementById('titleDocA').textContent = `Document A: ${r.doc_a_title || 'Manuscript'}`;
      document.getElementById('titleDocB').textContent = `Document B: ${r.doc_b_title || 'Corpus Match'}`;
      document.getElementById('forensicHeader').textContent = `#CASE-${r.id}: ${r.doc_a_title} vs ${r.doc_b_title} (${r.overall_similarity}% Overlap)`;

      currentPhrases = r.phrase_comparisons || [];
      document.getElementById('phraseCountLabel').textContent = `${currentPhrases.length} Sentences Analyzed`;

      // Render Document A sentences
      const paneA = document.getElementById('contentDocA');
      paneA.innerHTML = currentPhrases.map(p => {
        const cls = 'hl-' + p.color;
        return `
          <div class="phrase-item ${cls}" id="pA_${p.index}" onclick="focusPhrase(${p.index})">
            <div class="phrase-header">
              <span class="mono" style="font-weight:700">SENTENCE 0${p.index}</span>
              <span class="pill ${p.color}">${p.category} · ${p.score}%</span>
            </div>
            <div class="phrase-text">“${escapeHtml(p.sentence_a)}”</div>
          </div>
        `;
      }).join('');

      // Render Document B sentences
      const paneB = document.getElementById('contentDocB');
      paneB.innerHTML = currentPhrases.map(p => {
        const hasMatch = p.sentence_b && !p.sentence_b.includes('No matching passage');
        const cls = hasMatch ? ('hl-' + p.color) : 'hl-green';
        return `
          <div class="phrase-item ${cls}" id="pB_${p.index}" onclick="focusPhrase(${p.index})">
            <div class="phrase-header">
              <span class="mono" style="font-weight:700">MATCH 0${p.index}</span>
              <span class="pill ${hasMatch ? p.color : 'green'}">${hasMatch ? p.category : 'No Commonality'}</span>
            </div>
            <div class="phrase-text">“${escapeHtml(p.sentence_b)}”</div>
          </div>
        `;
      }).join('');

      // Render Sentence Comparison Table
      const tbody = document.getElementById('phraseTableBody');
      tbody.innerHTML = currentPhrases.map(p => {
        const bgRow = p.color === 'pink' ? 'rgba(255,101,153,0.06)' : (p.color === 'warn' ? 'rgba(255,180,67,0.06)' : (p.color === 'blue' ? 'rgba(108,213,255,0.06)' : 'transparent'));
        return `
          <tr id="row_${p.index}" style="background:${bgRow};cursor:pointer" onclick="focusPhrase(${p.index})">
            <td class="mono" style="font-weight:700">0${p.index}</td>
            <td><b>“${escapeHtml(p.sentence_a)}”</b></td>
            <td><span style="color:#c2d8cf">“${escapeHtml(p.sentence_b)}”</span></td>
            <td>
              <span class="pill ${p.color}">${p.category}</span>
              <div class="mono" style="font-size:11px;margin-top:4px;color:var(--text)">${p.score}% overlap</div>
            </td>
            <td>
              <div style="font-size:12px;line-height:1.55;color:#e8f4ef">
                ${escapeHtml(p.reason)}
              </div>
              ${p.shared_terms && p.shared_terms.length ? `<div class="mono" style="font-size:10px;color:var(--muted);margin-top:4px">Anchor keywords: ${p.shared_terms.slice(0,5).join(', ')}</div>` : ''}
            </td>
          </tr>
        `;
      }).join('');

      // Focus first flagged or verbatim sentence by default
      const firstTarget = currentPhrases.find(p => p.color === 'pink' || p.color === 'warn') || currentPhrases[0];
      if (firstTarget) {
        focusPhrase(firstTarget.index);
      }
    }
  } catch (e) {
    console.warn('Forensic load error:', e);
  }
}

function focusPhrase(idx) {
  activeFocusedIndex = idx;
  const p = currentPhrases.find(item => item.index === idx);
  if (!p) return;

  // Clear active styling
  document.querySelectorAll('.phrase-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('#phraseTable tr').forEach(el => el.style.outline = 'none');

  // Activate selected elements
  const elA = document.getElementById('pA_' + idx);
  const elB = document.getElementById('pB_' + idx);
  const elRow = document.getElementById('row_' + idx);

  if (elA) {
    elA.classList.add('active');
    elA.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  if (elB) {
    elB.classList.add('active');
    elB.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  if (elRow) {
    elRow.style.outline = '2px solid var(--accent)';
  }

  // Update live diagnostic banner
  const banner = document.getElementById('inspectorBanner');
  const catLabel = document.getElementById('inspectorCategory');
  const scoreBadge = document.getElementById('inspectorScore');
  const reasonText = document.getElementById('inspectorReason');
  const termsBox = document.getElementById('inspectorTerms');

  const borderColors = { pink: 'var(--pink)', warn: 'var(--warn)', blue: 'var(--blue)', green: 'var(--green)' };
  banner.style.borderLeftColor = borderColors[p.color] || 'var(--green)';

  catLabel.textContent = `SENTENCE 0${p.index} · ${p.category.toUpperCase()}`;
  catLabel.style.color = borderColors[p.color] || 'var(--green)';

  scoreBadge.className = 'pill ' + p.color;
  scoreBadge.textContent = `${p.score}% SIMILARITY`;

  reasonText.textContent = p.reason;

  if (p.shared_terms && p.shared_terms.length) {
    termsBox.style.display = 'block';
    termsBox.textContent = `Shared Domain Anchor Tokens: ${p.shared_terms.join(' · ')}`;
  } else {
    termsBox.style.display = 'none';
  }
}
"""

# Replace initForensicView and loadForensicReport with the new implementation
old_forensic_js_start = 'async function initForensicView() {'
old_batch_queue_start = 'async function loadBatchQueue() {'

js_start_idx = html.find(old_forensic_js_start)
js_end_idx = html.find(old_batch_queue_start)

html = html[:js_start_idx] + js_replacement + '\n\n' + html[js_end_idx:]

with open('uiux/admin/synapse_admin.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Successfully upgraded uiux/admin/synapse_admin.html with forensic inspector!')

