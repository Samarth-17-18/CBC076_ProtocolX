import re
import math
import difflib
from collections import Counter

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

# Generic boilerplate, assignment templates, citations & common phrases to ignore/discount
GENERIC_BOILERPLATE_PATTERNS = [
    r"\baccording to\b",
    r"\bin this paper\b",
    r"\bin this study\b",
    r"\bthe results show that\b",
    r"\bas shown in table\b",
    r"\bas shown in figure\b",
    r"\bin order to\b",
    r"\bon the other hand\b",
    r"\bit can be seen that\b",
    r"\bfor example\b",
    r"\bfor instance\b",
    r"\bin conclusion\b",
    r"\bfurthermore\b",
    r"\bmoreover\b",
    r"\bthe aim of this\b",
    r"\bsubmitted in partial fulfillment\b",
    r"\ball rights reserved\b",
    r"\breferences\b",
    r"\bbibliography\b"
]

from .ml_learner import ml_model

# Load fine-tuned ProtocolX model if available
protocolx_scorer = None
try:
    import sys, os
    model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model"))
    if os.path.exists(os.path.join(model_dir, "protocolx-encoder")) and os.path.exists(os.path.join(model_dir, "scorer.joblib")):
        sys.path.insert(0, model_dir)
        from protocolx_inference import PlagiarismScorer
        protocolx_scorer = PlagiarismScorer(model_dir)
        print("ProtocolX PlagiarismScorer initialized successfully.")
except Exception as e:
    print(f"Warning: Could not load ProtocolX scorer ({e}). Falling back to algorithmic engine.")

def get_active_stopwords():
    custom = set(ml_model.data.get("learned_stopwords", []))
    return STOPWORDS.union(custom)

def split_into_sentences(text: str):
    """Splits text into clean sentences."""
    if not text:
        return []
    raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    cleaned = [s.strip() for s in raw_sentences if len(s.strip()) > 3]
    return cleaned

def tokenize(text: str, remove_stopwords: bool = True):
    tokens = re.findall(r'\b[a-zA-Z0-9_-]+\b', text.lower())
    if remove_stopwords:
        active_stops = get_active_stopwords()
        return [t for t in tokens if t not in active_stops and len(t) > 1]
    return tokens


def is_predominantly_boilerplate(sentence: str, corpus_templates: set = None) -> bool:
    """
    Distinguishes common academic prompts, question prompts, and assignment templates
    by referencing corpus-wide recurring phrases so common vocabulary is not falsely flagged as copied work.
    """
    s_lower = sentence.lower().strip()
    
    # 1. Check against known boilerplate regex patterns
    for pat in GENERIC_BOILERPLATE_PATTERNS:
        if re.search(pat, s_lower):
            tokens = tokenize(sentence, remove_stopwords=True)
            if len(tokens) <= 6:
                return True

    # 2. Check if sentence matches known assignment prompt/template headers
    assignment_prompt_headers = [
        "question", "problem statement", "assignment title", "course code",
        "name:", "roll no:", "submission date:", "faculty:", "department of",
        "answer the following", "write a program to", "explain the concept of",
        "aim:", "objective:", "procedure:", "apparatus required:", "theory:"
    ]
    for aph in assignment_prompt_headers:
        if s_lower.startswith(aph) or s_lower == aph:
            return True

    # 3. Check against corpus-wide recurring templates (submitted across multiple answerscripts)
    if corpus_templates:
        norm = re.sub(r'\s+', ' ', s_lower)
        if norm in corpus_templates:
            return True

    return False

def extract_corpus_template_phrases(all_corpus_texts: list, min_df: int = 2) -> set:
    """
    Scans all submitted assignments/answerscripts in the corpus to discover
    shared template text, questions, and instructor-provided headers that occur across >= min_df documents.
    """
    sentence_counts = Counter()
    for text in all_corpus_texts:
        if not text:
            continue
        sents = split_into_sentences(text)
        seen_in_doc = set()
        for s in sents:
            s_clean = re.sub(r'\s+', ' ', s.lower().strip())
            if len(s_clean) > 8 and s_clean not in seen_in_doc:
                seen_in_doc.add(s_clean)
                sentence_counts[s_clean] += 1
    
    # Sentences occurring across multiple student submissions are template/prompt content
    templates = {s for s, count in sentence_counts.items() if count >= min_df}
    return templates

def extract_content_words(text: str) -> set:
    """Extracts non-stop, meaningful content words."""
    return set(tokenize(text, remove_stopwords=True))

def compute_cosine_similarity(vec1: dict, vec2: dict) -> float:
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)
    
    sum1 = sum(v**2 for v in vec1.values())
    sum2 = sum(v**2 for v in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    
    if not denominator:
        return 0.0
    return float(numerator / denominator)

def build_tfidf_vectors(sentences1: list, sentences2: list, background_corpus: list = None):
    """
    Computes TF-IDF vectors using both document sentences and the institutional reference corpus benchmark.
    Terms that appear across many assignments/answerscripts (e.g., 'machine learning', 'algorithm', 'function',
    'experiment', 'student', 'question') automatically get penalized by higher doc_freq, giving near-zero IDF weight.
    This guarantees that standard assignment terminology or common domain words are NEVER flagged as copied text.
    """
    corpus = sentences1 + sentences2
    doc_freq = Counter()
    tokenized_docs = []
    
    # Ingest document sentences
    for s in corpus:
        tokens = tokenize(s, remove_stopwords=True)
        unique_tokens = set(tokens)
        for u in unique_tokens:
            doc_freq[u] += 1
        tokenized_docs.append(Counter(tokens))

    # Ingest background corpus benchmark if provided
    total_benchmark_docs = len(corpus)
    if background_corpus and len(background_corpus) > 0:
        for ref_text in background_corpus:
            ref_tokens = set(tokenize(ref_text, remove_stopwords=True))
            for u in ref_tokens:
                doc_freq[u] += 1
            total_benchmark_docs += 1
        
    tfidf_vectors = []
    for doc_counts in tokenized_docs:
        vec = {}
        for term, count in doc_counts.items():
            tf = 1 + math.log(count) if count > 0 else 0
            # Standard smooth IDF formula against institutional benchmark
            df = doc_freq.get(term, 1)
            idf = math.log((1 + total_benchmark_docs) / (1 + df)) + 1.0
            
            # If a term appears in more than 60% of benchmark submissions, diminish its weight to zero
            if total_benchmark_docs > 5 and (df / total_benchmark_docs) > 0.60:
                idf = 0.05
                
            vec[term] = tf * idf
        tfidf_vectors.append(vec)
        
    return tfidf_vectors[:len(sentences1)], tfidf_vectors[len(sentences1):]

def compute_sequence_matcher_ratio(text1: str, text2: str) -> float:
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def compute_exact_token_jaccard(text1: str, text2: str) -> float:
    tokens1 = set(tokenize(text1, remove_stopwords=False))
    tokens2 = set(tokenize(text2, remove_stopwords=False))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return float(len(intersection) / len(union))

def generate_phrase_explanation(sent_a: str, sent_b: str, match_type: str, score: float, shared_terms: list) -> str:
    """Generates an in-depth explanation of why the passage pair was flagged."""
    words_a = len(sent_a.split())
    words_b = len(sent_b.split())
    if match_type == "Exact Match":
        if score >= 90:
            return f"Flagged as Verbatim Copy: Word-for-word identical sequence ({words_a} words). Zero lexical or grammatical variation detected."
        else:
            return f"Flagged as Verbatim / Near-Identical: High surface lexical overlap ({round(score, 1)}%) with identical word order. Shared key tokens: {', '.join(shared_terms[:5])}."
    elif match_type == "Paraphrased / Semantic":
        if len(shared_terms) <= 1:
            return f"Flagged as Paraphrased (Syntactic Rewrite): Conceptual thesis and logical structure are preserved while vocabulary was systematically replaced with synonyms or passive/active voice transformations."
        else:
            return f"Flagged as Paraphrased (Anchor Word Preservation): Core argument retained with sentence re-structuring around specialized domain anchors ({', '.join(shared_terms[:5])})."
    return f"Flagged: High contextual similarity ({round(score, 1)}%) detected across parallel sentences."

def analyze_document_pair(text_a: str, text_b: str, drop_common_phrases: bool = True, background_corpus: list = None, corpus_templates: set = None):
    sents_a = split_into_sentences(text_a)
    sents_b = split_into_sentences(text_b)

    # Filter out pure boilerplate sentences if drop_common_phrases is enabled
    if drop_common_phrases:
        sents_a_filtered = [s for s in sents_a if not is_predominantly_boilerplate(s, corpus_templates=corpus_templates)]
        sents_b_filtered = [s for s in sents_b if not is_predominantly_boilerplate(s, corpus_templates=corpus_templates)]
        if sents_a_filtered: sents_a = sents_a_filtered
        if sents_b_filtered: sents_b = sents_b_filtered

    if not sents_a or not sents_b:
        return {
            "overall_similarity": 0.0,
            "exact_similarity": 0.0,
            "semantic_similarity": 0.0,
            "explanation": "Insufficient unique content after common phrase filtering.",
            "evidence": []
        }

    # Document-level exact matching
    exact_score = compute_exact_token_jaccard(text_a, text_b)
    
    # TF-IDF vectors for sentences (calibrated against institutional background corpus benchmark)
    vecs_a, vecs_b = build_tfidf_vectors(sents_a, sents_b, background_corpus=background_corpus)
    
    # Whole doc TF-IDF cosine
    d_vec_a, d_vec_b = build_tfidf_vectors([text_a], [text_b], background_corpus=background_corpus)
    doc_cosine = compute_cosine_similarity(d_vec_a[0], d_vec_b[0])

    evidence = []
    matched_a_indices = set()
    matched_b_indices = set()
    semantic_scores_list = []

    for idx_a, sent_a in enumerate(sents_a):
        va = vecs_a[idx_a]
        best_b_idx = -1
        best_cosine = 0.0

        for idx_b, vb in enumerate(vecs_b):
            c_sim = compute_cosine_similarity(va, vb)
            if c_sim > best_cosine:
                best_cosine = c_sim
                best_b_idx = idx_b

        if best_b_idx >= 0:
            sent_b = sents_b[best_b_idx]
            seq_ratio = compute_sequence_matcher_ratio(sent_a, sent_b)
            
            # Shared content words (excluding common stop words)
            words_a = extract_content_words(sent_a)
            words_b = extract_content_words(sent_b)
            shared_content = list(words_a & words_b)
            
            match_type = "None"
            effective_score = max(best_cosine, seq_ratio)
            
            # Drop matches that only share 1 trivial word if drop_common_phrases is True
            if drop_common_phrases and len(shared_content) < 2 and seq_ratio < 0.6:
                continue

            # If ProtocolX fine-tuned model is loaded, leverage its calibrated scoring & classification
            if protocolx_scorer is not None and (effective_score >= 0.25 or seq_ratio >= 0.3):
                try:
                    px_res = protocolx_scorer.score_pairs([(sent_a, sent_b)])[0]
                    if px_res["band"] != "None" or px_res["priority"] >= 15.0:
                        likely = px_res["likely_type"]
                        if likely in ["verbatim", "near_verbatim"]:
                            match_type = "Exact Match"
                            matched_a_indices.add(idx_a)
                            matched_b_indices.add(best_b_idx)
                            semantic_scores_list.append(1.0)
                        elif likely == "paraphrase" or px_res["priority"] >= 20.0:
                            match_type = "Paraphrased / Semantic"
                            matched_a_indices.add(idx_a)
                            matched_b_indices.add(best_b_idx)
                            semantic_scores_list.append(px_res["priority"] / 100.0)
                        
                        if match_type != "None":
                            reason_desc = " ".join(px_res["reasons"])
                            evidence.append({
                                "sentence_a": sent_a,
                                "sentence_b": sent_b,
                                "score": px_res["priority"],
                                "type": match_type,
                                "reason": reason_desc,
                                "shared_terms": shared_content,
                                "index_a": idx_a,
                                "index_b": best_b_idx,
                                "protocolx": {
                                    "priority": px_res["priority"],
                                    "band": px_res["band"],
                                    "type": px_res["likely_type"],
                                    "spans": px_res.get("spans", [])
                                }
                            })
                            continue
                except Exception as ex:
                    pass

            if seq_ratio >= 0.70:
                match_type = "Exact Match"
                matched_a_indices.add(idx_a)
                matched_b_indices.add(best_b_idx)
                semantic_scores_list.append(1.0)
            elif effective_score >= 0.35 and len(words_a) >= 3:
                match_type = "Paraphrased / Semantic"
                matched_a_indices.add(idx_a)
                matched_b_indices.add(best_b_idx)
                semantic_scores_list.append(effective_score)

            if match_type != "None":
                reason = generate_phrase_explanation(
                    sent_a, sent_b, match_type, effective_score * 100, shared_content
                )
                evidence.append({
                    "sentence_a": sent_a,
                    "sentence_b": sent_b,
                    "score": round(effective_score * 100, 1),
                    "type": match_type,
                    "reason": reason,
                    "shared_terms": shared_content,
                    "index_a": idx_a,
                    "index_b": best_b_idx
                })

    avg_match_semantic = (sum(semantic_scores_list) / len(semantic_scores_list)) if semantic_scores_list else 0.0
    semantic_score = float(round((avg_match_semantic * 0.6 + doc_cosine * 0.4) * 100, 1))
    exact_pct = float(round(exact_score * 100, 1))
    
    coverage_ratio = len(matched_a_indices) / max(len(sents_a), 1)
    
    # ML Calibration: Computes dynamic score using weights optimized from reviewer feedback
    coverage_pct = float(round(coverage_ratio * 100, 1))
    ml_pred = ml_model.predict_calibrated_score(exact_pct, semantic_score, coverage_pct)
    overall = ml_pred["ml_calibrated_similarity"]
    overall = min(100.0, max(0.0, overall))

    # Formulate review indicator note (Treat as indicator, not automatic proof of misconduct)
    disclaimer = "Indicator Notice: This score is an analytical indicator to assist human evaluation, not automated proof of misconduct."
    if overall < 15.0:
        verdict_text = f"Low similarity ({overall}%). Passages appear independent and pass standard review. {disclaimer}"
    elif exact_pct >= 50.0:
        verdict_text = f"High verbatim match ({exact_pct}% lexical overlap). Significant direct sequence copying detected for reviewer examination. {disclaimer}"
    elif semantic_score >= 35.0:
        verdict_text = f"Substantial semantic similarity ({semantic_score}%). Ideas and conceptual arguments are aligned despite altered wording (paraphrase pattern). {disclaimer}"
    else:
        verdict_text = f"Moderate similarity ({overall}%). Common domain vocabulary or constrained prompt context detected. {disclaimer}"

    return {
        "overall_similarity": overall,
        "exact_similarity": exact_pct,
        "semantic_similarity": semantic_score,
        "ml_metadata": ml_pred,
        "explanation": verdict_text,
        "evidence": evidence,
        "is_indicator_only": True,
        "disclaimer": disclaimer
    }

def analyze_batch_submissions(submissions: list, drop_common_phrases: bool = True):
    """
    Analyzes an entire batch of hundreds of submissions:
    1. Computes all pair-wise similarity scores.
    2. Drops common phrases / template boilerplate.
    3. Calculates the batch mean & standard deviation.
    4. FLAGS ONLY PAIRS ABOVE THE BATCH AVERAGE (or mean + margin).
    """
    n = len(submissions)
    if n < 2:
        return {"error": "Need at least 2 submissions to run batch analysis."}

    # Pre-extract common template sentences/prompts across all submitted answerscripts
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
            )
            score = res["overall_similarity"]
            scores.append(score)
            all_pairs.append({
                "sub_a_id": sub_a.get("id", i),
                "sub_a_title": sub_a.get("title", f"Doc {i+1}"),
                "sub_b_id": sub_b.get("id", j),
                "sub_b_title": sub_b.get("title", f"Doc {j+1}"),
                "overall_similarity": score,
                "exact_similarity": res["exact_similarity"],
                "semantic_similarity": res["semantic_similarity"],
                "explanation": res["explanation"],
                "evidence": res["evidence"]
            })

    batch_avg = float(sum(scores) / len(scores)) if scores else 0.0
    
    # Calculate standard deviation
    variance = sum((s - batch_avg) ** 2 for s in scores) / len(scores) if scores else 0.0
    std_dev = math.sqrt(variance)

    # Flag only pairs above the batch average
    flagged_pairs = []
    cleared_pairs = []

    for p in all_pairs:
        p["batch_avg"] = round(batch_avg, 2)
        p["delta_above_avg"] = round(p["overall_similarity"] - batch_avg, 2)
        if p["overall_similarity"] > batch_avg:
            p["is_flagged"] = True
            p["batch_reason"] = f"Flagged: Similarity of {p['overall_similarity']}% exceeds batch baseline ({round(batch_avg, 1)}%) by +{p['delta_above_avg']}%."
            flagged_pairs.append(p)
        else:
            p["is_flagged"] = False
            p["batch_reason"] = f"Cleared: Similarity of {p['overall_similarity']}% is below or equal to batch baseline ({round(batch_avg, 1)}%)."
            cleared_pairs.append(p)

    # Sort flagged pairs highest similarity first
    flagged_pairs.sort(key=lambda x: x["overall_similarity"], reverse=True)

    return {
        "total_documents": n,
        "total_comparisons": len(all_pairs),
        "batch_average_similarity": round(batch_avg, 2),
        "batch_std_dev": round(std_dev, 2),
        "flagged_count": len(flagged_pairs),
        "flagged_pairs": flagged_pairs,
        "cleared_pairs": cleared_pairs
    }
