with open('uiux/admin/synapse_admin.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add direct compare button next to reportSelector
target_btn = '<button class="btn green small" onclick="openNodeActionModal()">Cast Workflow Vote ✍️</button>'
replacement_btn = '''<button class="btn green small" onclick="openNodeActionModal()">Cast Workflow Vote ✍️</button>
          <button class="btn small" style="background:var(--card);border-color:var(--border-light)" onclick="openDirectCompareModal()">⚡ Compare Custom Pair</button>'''

if target_btn in html:
    html = html.replace(target_btn, replacement_btn, 1)

# 2. Add Direct Compare Modal HTML right before </body>
modal_html = """
<!-- DIRECT COMPARE MODAL -->
<div id="directCompareModal" style="display:none;position:fixed;inset:0;background:rgba(10,16,14,0.92);z-index:1500;padding:24px;overflow-y:auto;backdrop-filter:blur(14px)">
  <div style="max-width:850px;margin:20px auto;background:var(--surface);border:1.5px solid var(--border-light);border-radius:22px;padding:30px;box-shadow:0 25px 60px rgba(0,0,0,0.7)">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div>
        <div class="mono" style="color:var(--green);font-size:10px">ON-DEMAND ARBITRATION</div>
        <h3 class="display" style="font-size:24px;margin:2px 0 0">Direct Pairwise Comparison Sandbox</h3>
      </div>
      <button class="btn small" onclick="document.getElementById('directCompareModal').style.display='none'">✕ Close</button>
    </div>
    <p style="font-size:13px;color:var(--muted);margin:0 0 20px">
      Paste or type two text passages to analyze word-for-word copy, structural paraphrase, and common academic templates in real time.
    </p>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
      <div>
        <label class="mono" style="font-size:11px;color:var(--green);font-weight:700">DOCUMENT A (STUDENT DRAFT)</label>
        <input id="customTitleA" class="gate-input" placeholder="Title A (e.g. Student Submission)" value="Student A Draft" style="margin-bottom:8px">
        <textarea id="customTextA" class="gate-input" style="min-height:180px;resize:vertical;font-size:13px;line-height:1.6" placeholder="Paste Document A text here..."></textarea>
      </div>
      <div>
        <label class="mono" style="font-size:11px;color:var(--blue);font-weight:700">DOCUMENT B (CORPUS / PEER SOURCE)</label>
        <input id="customTitleB" class="gate-input" placeholder="Title B (e.g. Reference Paper)" value="Source Reference" style="margin-bottom:8px">
        <textarea id="customTextB" class="gate-input" style="min-height:180px;resize:vertical;font-size:13px;line-height:1.6" placeholder="Paste Document B text here..."></textarea>
      </div>
    </div>

    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:20px;padding-top:16px;border-top:1px solid var(--border)">
      <div style="display:flex;gap:8px">
        <button type="button" class="btn small" style="background:#182823" onclick="loadSampleDemo('copy')">Sample: Direct Copy</button>
        <button type="button" class="btn small" style="background:#182823" onclick="loadSampleDemo('para')">Sample: Paraphrase</button>
        <button type="button" class="btn small" style="background:#182823" onclick="loadSampleDemo('honest')">Sample: Independent</button>
      </div>
      <button class="btn green" style="padding:12px 24px;font-size:13px" onclick="executeCustomCompare()">Run Forensic Comparison ↗</button>
    </div>
  </div>
</div>
"""

body_end = '</body>'
html = html.replace(body_end, modal_html + '\n' + body_end, 1)

# 3. Add JS functions for direct compare
js_to_add = """
function openDirectCompareModal() {
  document.getElementById('directCompareModal').style.display = 'block';
}

function loadSampleDemo(type) {
  if (type === 'copy') {
    document.getElementById('customTitleA').value = 'Student Submission A';
    document.getElementById('customTextA').value = "The system of alliances divided Europe into two armed camps, the Triple Entente and the Triple Alliance, so a small conflict could quickly involve many countries. Militarism led the great powers to build huge armies and navies, and Germany's naval race with Britain increased the tension.";
    document.getElementById('customTitleB').value = 'Peer Submission B';
    document.getElementById('customTextB').value = "The system of alliances divided Europe into two armed camps, the Triple Entente and the Triple Alliance, so a small conflict could quickly involve many countries. Militarism caused the great powers to build enormous armies and navies, and Germany's naval race with Britain raised the tension.";
  } else if (type === 'para') {
    document.getElementById('customTitleA').value = 'Student Manuscript C';
    document.getElementById('customTextA').value = "Europe was split into two heavily armed blocs, the Triple Entente and the Triple Alliance, which meant a minor dispute could draw in numerous nations. The major powers expanded their armies and fleets, and the naval competition between Germany and Britain made relations even more strained.";
    document.getElementById('customTitleB').value = 'Source Reference A';
    document.getElementById('customTextB').value = "The system of alliances divided Europe into two armed camps, the Triple Entente and the Triple Alliance, so a small conflict could quickly involve many countries. Militarism led the great powers to build huge armies and navies, and Germany's naval race with Britain increased the tension.";
  } else {
    document.getElementById('customTitleA').value = 'Honest Student D';
    document.getElementById('customTextA').value = "This essay looks at why a murder in the Balkans turned into a world war. Germany, Austria-Hungary and Italy were bound together by treaties, while France, Russia and Britain had their own agreements, so a quarrel between two countries could spread.";
    document.getElementById('customTitleB').value = 'Historical Textbook';
    document.getElementById('customTextB').value = "Imperial rivalry over colonies in Africa and Asia created suspicion and competition between the European empires. Nationalism was especially strong in the Balkans, where Slavic groups wanted freedom from Austria-Hungary.";
  }
  toast('Sample passages loaded into sandbox.');
}

async function executeCustomCompare() {
  const titleA = document.getElementById('customTitleA').value.trim() || 'Document A';
  const textA = document.getElementById('customTextA').value.trim();
  const titleB = document.getElementById('customTitleB').value.trim() || 'Document B';
  const textB = document.getElementById('customTextB').value.trim();

  if (!textA || !textB) {
    toast('Please enter text for both documents');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title_a: titleA,
        content_a: textA,
        title_b: titleB,
        content_b: textB,
        drop_common_phrases: true,
        save_to_history: true
      })
    });

    if (res.ok) {
      const data = await res.json();
      document.getElementById('directCompareModal').style.display = 'none';
      toast('Comparison complete! Loading forensic view...');
      
      // Refresh cases and inspect
      await loadBoardData();
      const reportId = data.report_id || (allReports.length ? allReports[0].id : null);
      if (reportId) {
        inspectReport(reportId);
      }
    } else {
      toast('Comparison failed: ' + res.statusText);
    }
  } catch(e) {
    console.error('Custom compare error:', e);
    toast('Error connecting to backend API');
  }
}
"""

script_end = '</script>'
# Find the last </script>
last_script_idx = html.rfind(script_end)
html = html[:last_script_idx] + js_to_add + '\n' + html[last_script_idx:]

with open('uiux/admin/synapse_admin.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Successfully added Direct Compare Sandbox to uiux/admin/synapse_admin.html')
