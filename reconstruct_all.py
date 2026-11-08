import os
import re
import glob
import json

def extract_code_from_view(file_path):
    lines = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.match(r'^\s*(\d+):\s?(.*)$', line)
            if m:
                line_no = int(m.group(1))
                content = m.group(2)
                lines.append((line_no, content))
    return lines

def reconstruct_file_parser():
    p1 = extract_code_from_view('fp_view_119.txt')
    p2 = extract_code_from_view('fp_view_368.txt')
    
    line_dict = {}
    for lno, content in p1:
        line_dict[lno] = content
    for lno, content in p2:
        line_dict[lno] = content
    
    sorted_lines = [line_dict[k] for k in sorted(line_dict.keys())]
    return '\n'.join(sorted_lines)

def reconstruct_ml_learner():
    p1 = extract_code_from_view('ml_view_763.txt')
    p2 = extract_code_from_view('ml_view_765.txt')
    
    line_dict = {}
    for lno, content in p1:
        line_dict[lno] = content
    for lno, content in p2:
        line_dict[lno] = content
        
    sorted_lines = [line_dict[k] for k in sorted(line_dict.keys())]
    return '\n'.join(sorted_lines)

def reconstruct_similarity_engine():
    p1 = extract_code_from_view('sim_101.txt')
    p2 = extract_code_from_view('sim_115.txt')
    p3 = extract_code_from_view('sim_117.txt')
    p4 = extract_code_from_view('sim_250.txt')
    
    line_dict = {}
    for p in [p1, p2, p3, p4]:
        for lno, content in p:
            line_dict[lno] = content
            
    base_code = '\n'.join([line_dict[k] for k in sorted(line_dict.keys())])
    
    patches = sorted(glob.glob('sim_patch_*.json'), key=lambda x: int(re.search(r'\d+', x).group()))
    for p in patches:
        with open(p, 'r', encoding='utf-8') as f:
            pdata = json.load(f)
        target = pdata.get('TargetContent')
        repl = pdata.get('ReplacementContent')
        if target and target in base_code:
            base_code = base_code.replace(target, repl, 1)
            print(f'Applied {p}')
        elif '839' in p:
            old_str = 'def analyze_document_pair(text_a: str, text_b: str, drop_common_phrases: bool = True, background_corpus: list = None):'
            new_str = 'def analyze_document_pair(text_a: str, text_b: str, drop_common_phrases: bool = True, background_corpus: list = None, corpus_templates: set = None):'
            if old_str in base_code:
                base_code = base_code.replace(old_str, new_str, 1)
                # Also replace filtering calls to pass corpus_templates
                old_filter = 'sents_a_filtered = [s for s in sents_a if not is_predominantly_boilerplate(s)]\n        sents_b_filtered = [s for s in sents_b if not is_predominantly_boilerplate(s)]'
                new_filter = 'sents_a_filtered = [s for s in sents_a if not is_predominantly_boilerplate(s, corpus_templates=corpus_templates)]\n        sents_b_filtered = [s for s in sents_b if not is_predominantly_boilerplate(s, corpus_templates=corpus_templates)]'
                base_code = base_code.replace(old_filter, new_filter, 1)
                print(f'Applied {p} (adapted for background_corpus)')
            else:
                print(f'Could not apply 839')
        elif '843' in p:
            old_block = '''    all_pairs = []
    scores = []
    # Collect all submission contents to form the batch benchmark reference corpus
    batch_benchmark_texts = [sub["content"] for sub in submissions if sub.get("content")]

    for i in range(n):
        for j in range(i + 1, n):
            sub_a = submissions[i]
            sub_b = submissions[j]
            # Provide batch benchmark corpus to discount assignment-wide common terms
            res = analyze_document_pair(
                sub_a["content"], 
                sub_b["content"], 
                drop_common_phrases=drop_common_phrases,
                background_corpus=batch_benchmark_texts
            )'''
            new_block = '''    # Pre-extract common template sentences/prompts across all submitted answerscripts
    corpus_templates = set()
    if drop_common_phrases:
        all_texts = [sub.get("content", "") for sub in submissions]
        corpus_templates = extract_corpus_template_phrases(all_texts, min_df=2)

    all_pairs = []
    scores = []
    # Collect all submission contents to form the batch benchmark reference corpus
    batch_benchmark_texts = [sub["content"] for sub in submissions if sub.get("content")]

    for i in range(n):
        for j in range(i + 1, n):
            sub_a = submissions[i]
            sub_b = submissions[j]
            # Provide batch benchmark corpus to discount assignment-wide common terms
            res = analyze_document_pair(
                sub_a["content"], 
                sub_b["content"], 
                drop_common_phrases=drop_common_phrases,
                background_corpus=batch_benchmark_texts,
                corpus_templates=corpus_templates
            )'''
            if old_block in base_code:
                base_code = base_code.replace(old_block, new_block, 1)
                print(f'Applied {p} (adapted for batch benchmark)')
            else:
                print('Could not apply 843')
        else:
            norm_target = target.replace('\r\n', '\n')
            norm_base = base_code.replace('\r\n', '\n')
            if norm_target in norm_base:
                base_code = norm_base.replace(norm_target, repl.replace('\r\n', '\n'), 1)
                print(f'Applied {p} (normalized)')
            else:
                print(f'Failed {p}')
    return base_code

def reconstruct_main():
    p1 = extract_code_from_view('step_97_raw.txt')
    p2 = extract_code_from_view('step_99_raw.txt')
    
    line_dict = {}
    for lno, content in p1:
        line_dict[lno] = content
    for lno, content in p2:
        line_dict[lno] = content
        
    base_code = '\n'.join([line_dict[k] for k in sorted(line_dict.keys())])
    
    patches = sorted(glob.glob('main_patch_*.json'), key=lambda x: int(re.search(r'\d+', x).group()))
    for p in patches:
        with open(p, 'r', encoding='utf-8') as f:
            pdata = json.load(f)
        target = pdata.get('TargetContent')
        repl = pdata.get('ReplacementContent')
        if target and target in base_code:
            base_code = base_code.replace(target, repl, 1)
            print(f'Applied {p}')
        elif '859' in p:
            p1_pos = base_code.find('@app.get("/api/admin/ml-model")')
            p2_pos = base_code.find('@app.put("/api/reports/{report_id}/review")')
            if p1_pos != -1 and p2_pos != -1:
                base_code = base_code[:p1_pos] + repl + '\n\n' + base_code[p2_pos:]
                print(f'Applied {p} via slice logic')
            else:
                print(f'Failed {p} slice logic')
        else:
            norm_target = target.replace('\r\n', '\n')
            norm_base = base_code.replace('\r\n', '\n')
            if norm_target in norm_base:
                base_code = norm_base.replace(norm_target, repl.replace('\r\n', '\n'), 1)
                print(f'Applied {p} (normalized)')
            else:
                print(f'Failed {p}')
    return base_code

if __name__ == '__main__':
    os.makedirs('backend', exist_ok=True)
    
    fp_code = reconstruct_file_parser()
    with open('backend/file_parser.py', 'w', encoding='utf-8') as f:
        f.write(fp_code)
    print('Wrote backend/file_parser.py, lines:', len(fp_code.splitlines()))
    
    ml_code = reconstruct_ml_learner()
    with open('backend/ml_learner.py', 'w', encoding='utf-8') as f:
        f.write(ml_code)
    print('Wrote backend/ml_learner.py, lines:', len(ml_code.splitlines()))
    
    sim_code = reconstruct_similarity_engine()
    with open('backend/similarity_engine.py', 'w', encoding='utf-8') as f:
        f.write(sim_code)
    print('Wrote backend/similarity_engine.py, lines:', len(sim_code.splitlines()))
    
    main_code = reconstruct_main()
    with open('backend/main.py', 'w', encoding='utf-8') as f:
        f.write(main_code)
    print('Wrote backend/main.py, lines:', len(main_code.splitlines()))
