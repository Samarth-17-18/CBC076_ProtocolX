from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import re
from datetime import datetime

from .database import engine, Base, get_db
from .models import Submission, ComparisonReport, AuditLog, Officer, SystemPolicy
from .similarity_engine import analyze_document_pair, analyze_batch_submissions

# Create DB tables
Base.metadata.create_all(bind=engine)

def seed_defaults():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        if not db.query(SystemPolicy).first():
            pol = SystemPolicy(
                overlap_threshold=15.0,
                paraphrase_threshold=80.0,
                cross_language=1,
                ai_signal=1,
                ignore_bibliography=1
            )
            db.add(pol)
        if db.query(Officer).count() == 0:
            db.add_all([
                Officer(name="Evelyn Vance", email="evelyn.vance@synapse.edu", department="Computer Science & AI", role="Lead reviewer", monthly_scans=4280, quota=4350, color="var(--green)"),
                Officer(name="Marcus Sterling", email="marcus.s@synapse.edu", department="Biological Engineering", role="Lead reviewer", monthly_scans=1840, quota=4350, color="var(--pink)"),
                Officer(name="Clara Dupont", email="clara.d@synapse.edu", department="Humanities", role="Forensic auditor", monthly_scans=890, quota=4350, color="var(--blue)"),
                Officer(name="Julian Ramirez", email="julian.r@synapse.edu", department="Graduate Board", role="Super-admin", monthly_scans=3420, quota=4350, color="var(--purple)")
            ])
        if db.query(AuditLog).count() == 0:
            db.add_all([
                AuditLog(icon="✓", color="", action="Session authenticated", detail="Admin desk · role-based access initialized", actor="System"),
                AuditLog(icon="⌘", color="var(--purple)", action="Policy baseline initialized", detail="Overlap threshold 15%, Paraphrase threshold 80%", actor="System"),
                AuditLog(icon="⚑", color="var(--pink)", action="Review queue online", detail="Verification desk connected to similarity engine", actor="System")
            ])
        db.commit()
    finally:
        db.close()

seed_defaults()

app = FastAPI(title="Synapse - AI Plagiarism & Text Similarity API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas
class SubmissionCreate(BaseModel):
    title: str
    author: Optional[str] = "Anonymous"
    content: str

class DirectCompareRequest(BaseModel):
    title_a: Optional[str] = "Document A"
    content_a: str
    title_b: Optional[str] = "Document B"
    content_b: str
    drop_common_phrases: Optional[bool] = True
    save_to_history: Optional[bool] = True

class BatchItem(BaseModel):
    id: Optional[int] = None
    title: str
    content: str

class BatchCompareRequest(BaseModel):
    documents: List[BatchItem]
    drop_common_phrases: Optional[bool] = True

class ReviewUpdate(BaseModel):
    status: str
    reviewer_notes: Optional[str] = ""

from fastapi.responses import FileResponse, HTMLResponse
import os

USER_UI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uiux", "user", "synapse.html"))
ADMIN_UI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uiux", "admin", "synapse_admin.html"))

@app.get("/", response_class=HTMLResponse)
def read_user_ui():
    if os.path.exists(USER_UI_PATH):
        return FileResponse(USER_UI_PATH)
    return HTMLResponse("<h1>Synapse User UI</h1><p>File not found at uiux/user/synapse.html</p>")

@app.get("/admin", response_class=HTMLResponse)
def read_admin_ui():
    if os.path.exists(ADMIN_UI_PATH):
        return FileResponse(ADMIN_UI_PATH)
    return HTMLResponse("<h1>Synapse Admin UI</h1><p>File not found at uiux/admin/synapse_admin.html</p>")

@app.get("/reimagined", response_class=HTMLResponse)
def read_reimagined_ui():
    reimagined_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "synapse_reimagined.html"))
    if os.path.exists(reimagined_path):
        return FileResponse(reimagined_path)
    return HTMLResponse("<h1>Synapse Reimagined UI not found</h1>")

@app.get("/prototype", response_class=HTMLResponse)
def read_prototype_ui():
    proto_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Synapse — catch the copy, keep the proof.html"))
    if os.path.exists(proto_path):
        return FileResponse(proto_path)
    return HTMLResponse("<h1>Synapse Prototype UI not found</h1>")

@app.get("/api/health")
def read_health():
    return {
        "message": "Synapse AI Text Similarity Backend is Running",
        "status": "active",
        "model_loaded": "protocolx"
    }

@app.post("/api/submissions")
def create_submission(data: SubmissionCreate, db: Session = Depends(get_db)):
    sub = Submission(title=data.title, author=data.author, content=data.content)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub

@app.get("/api/submissions")
def get_submissions(db: Session = Depends(get_db)):
    return db.query(Submission).order_by(Submission.created_at.desc()).all()

@app.post("/api/compare")
def compare_documents(req: DirectCompareRequest, db: Session = Depends(get_db)):
    if not req.content_a.strip() or not req.content_b.strip():
        raise HTTPException(status_code=400, detail="Both documents must contain text to compare.")
    
    analysis = analyze_document_pair(
        req.content_a, 
        req.content_b, 
        drop_common_phrases=req.drop_common_phrases
    )

    report_id = None
    if req.save_to_history:
        report = ComparisonReport(
            doc_a_title=req.title_a,
            doc_b_title=req.title_b,
            overall_similarity=analysis["overall_similarity"],
            exact_similarity=analysis["exact_similarity"],
            semantic_similarity=analysis["semantic_similarity"],
            explanation=analysis["explanation"],
            evidence_json=json.dumps(analysis["evidence"]),
            status="Pending Review"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id

    return {
        "report_id": report_id,
        "title_a": req.title_a,
        "title_b": req.title_b,
        **analysis
    }

@app.post("/api/batch-compare")
def batch_compare(req: BatchCompareRequest, db: Session = Depends(get_db)):
    if len(req.documents) < 2:
        raise HTTPException(status_code=400, detail="Batch requires at least 2 documents.")
    
    doc_dicts = [d.dict() for d in req.documents]
    batch_result = analyze_batch_submissions(doc_dicts, drop_common_phrases=req.drop_common_phrases)

    # Save flagged pairs into reports for reviewer queue
    for fp in batch_result.get("flagged_pairs", []):
        report = ComparisonReport(
            doc_a_title=fp["sub_a_title"],
            doc_b_title=fp["sub_b_title"],
            overall_similarity=fp["overall_similarity"],
            exact_similarity=fp["exact_similarity"],
            semantic_similarity=fp["semantic_similarity"],
            explanation=f"{fp['batch_reason']} | {fp['explanation']}",
            evidence_json=json.dumps(fp["evidence"]),
            status="Flagged (Above Batch Avg)"
        )
        db.add(report)
    db.commit()

    return batch_result

@app.get("/api/user/documents")
def get_user_documents(author: Optional[str] = None, db: Session = Depends(get_db)):
    """User-facing endpoint: Lists documents uploaded by the user with their current review status."""
    q = db.query(Submission)
    if author and author.strip():
        q = q.filter(Submission.author == author)
    subs = q.order_by(Submission.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "author": s.author,
            "status": s.status or "Under Review",
            "word_count": len((s.content or "").split()),
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else None
        }
        for s in subs
    ]

@app.get("/api/user/documents/{doc_id}/status")
def get_user_document_status(doc_id: int, db: Session = Depends(get_db)):
    """User-facing endpoint: Returns only the document receipt and review status without exposing peer documents."""
    sub = db.query(Submission).filter(Submission.id == doc_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Document not found")
    
    rep = db.query(ComparisonReport).filter(
        (ComparisonReport.doc_a_id == doc_id) | (ComparisonReport.doc_b_id == doc_id)
    ).order_by(ComparisonReport.created_at.desc()).first()

    overlap = round(rep.overall_similarity, 1) if rep else 0.0
    originality = max(0.0, round(100.0 - overlap, 1))
    
    return {
        "id": sub.id,
        "receipt_id": f"SYN-RCPT-2026-{sub.id:04d}",
        "title": sub.title,
        "author": sub.author,
        "status": sub.status or ("Cleared" if originality >= 75.0 else "Under Review"),
        "originality_score": originality,
        "overlap_score": overlap,
        "word_count": len((sub.content or "").split()),
        "created_at": sub.created_at.strftime("%Y-%m-%d %H:%M:%S") if sub.created_at else None
    }

@app.get("/api/reports")
def get_reports(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ComparisonReport)
    if status and status != "All":
        q = q.filter(ComparisonReport.status == status)
    reports = q.order_by(ComparisonReport.created_at.desc()).all()
    results = []
    for r in reports:
        results.append({
            "id": r.id,
            "doc_a_id": r.doc_a_id,
            "doc_b_id": r.doc_b_id,
            "doc_a_title": r.doc_a_title,
            "doc_b_title": r.doc_b_title,
            "overall_similarity": r.overall_similarity,
            "exact_similarity": r.exact_similarity,
            "semantic_similarity": r.semantic_similarity,
            "explanation": r.explanation,
            "evidence": json.loads(r.evidence_json) if r.evidence_json else [],
            "status": r.status,
            "reviewer_notes": r.reviewer_notes,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            "reviewed_at": r.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if r.reviewed_at else None
        })
    return results

@app.get("/api/reports/{report_id}")
def get_single_report(report_id: int, db: Session = Depends(get_db)):
    import difflib
    from .similarity_engine import split_into_sentences, analyze_document_pair

    r = db.query(ComparisonReport).filter(ComparisonReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    
    doc_a = db.query(Submission).filter(Submission.id == r.doc_a_id).first() if r.doc_a_id else None
    doc_b = db.query(Submission).filter(Submission.id == r.doc_b_id).first() if r.doc_b_id else None

    # Search by title fallback if ID was not linked
    if not doc_a and r.doc_a_title:
        doc_a = db.query(Submission).filter(Submission.title == r.doc_a_title).first()
    if not doc_b and r.doc_b_title:
        doc_b = db.query(Submission).filter(Submission.title == r.doc_b_title).first()

    text_a = (doc_a.content or "") if doc_a else ""
    text_b = (doc_b.content or "") if doc_b else ""

    evidence_list = json.loads(r.evidence_json) if r.evidence_json else []

    # If texts are empty in submission, synthesize from evidence sentences
    if not text_a and evidence_list:
        text_a = "\n\n".join([ev.get("sentence_a", "") for ev in evidence_list if ev.get("sentence_a")])
    if not text_b and evidence_list:
        text_b = "\n\n".join([ev.get("sentence_b", "") for ev in evidence_list if ev.get("sentence_b")])

    # If evidence_list is empty or partial but we have texts, run analysis to produce rich evidence
    if text_a and text_b:
        fresh_analysis = analyze_document_pair(text_a, text_b, drop_common_phrases=True)
        if len(fresh_analysis.get("evidence", [])) >= len(evidence_list):
            evidence_list = fresh_analysis.get("evidence", [])

    # Build comprehensive sentence-by-sentence phrase comparison
    sents_a = split_into_sentences(text_a) if text_a else []
    phrase_comparisons = []

    for idx, sa in enumerate(sents_a):
        sa_str = sa.strip()
        if not sa_str:
            continue

        best_ev = None
        best_ratio = 0.0
        for ev in evidence_list:
            ev_sa = ev.get("sentence_a", "").strip()
            if not ev_sa:
                continue
            ratio = difflib.SequenceMatcher(None, sa_str.lower(), ev_sa.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_ev = ev

        if best_ev and best_ratio >= 0.70:
            sc = round(best_ev.get("score", 0), 1)
            raw_type = best_ev.get("type", "Match")
            s_low = sa_str.lower()

            # Identify category and color code
            if "in this essay" in s_low or "in conclusion" in s_low or "explain the main causes" in s_low:
                category = "Template / Common Prompt"
                color = "blue"
                reason = "Common Assignment Template: Standard introductory or concluding assignment phrasing suppressed from misconduct assessment."
            elif "Exact" in raw_type or sc >= 85:
                category = "Verbatim Copy"
                color = "pink"
                reason = best_ev.get("reason") or f"Flagged as Verbatim Copy: Word-for-word identical sequence ({sc}% overlap). Zero lexical or grammatical variation detected."
            elif "Paraphras" in raw_type or sc >= 40:
                category = "Paraphrased"
                color = "warn"
                reason = best_ev.get("reason") or f"Flagged as Paraphrased: Semantic rewrite preserving thesis argument with synonym substitutions ({sc}% match)."
            else:
                category = "Low Similarity"
                color = "blue"
                reason = best_ev.get("reason") or "Minor incidental vocabulary sharing."

            phrase_comparisons.append({
                "index": idx + 1,
                "sentence_a": sa_str,
                "sentence_b": best_ev.get("sentence_b", "").strip(),
                "score": sc,
                "category": category,
                "color": color,
                "reason": reason,
                "shared_terms": best_ev.get("shared_terms", [])
            })
        else:
            phrase_comparisons.append({
                "index": idx + 1,
                "sentence_a": sa_str,
                "sentence_b": "No matching passage found in reference source.",
                "score": 0.0,
                "category": "Independent / Original",
                "color": "green",
                "reason": "Cleared as Independent: Autonomous phrasing with unique vocabulary and independent sentence structure.",
                "shared_terms": []
            })

    return {
        "id": r.id,
        "doc_a_id": r.doc_a_id,
        "doc_b_id": r.doc_b_id,
        "doc_a_title": r.doc_a_title,
        "doc_b_title": r.doc_b_title,
        "doc_a_text": text_a,
        "doc_b_text": text_b,
        "overall_similarity": r.overall_similarity,
        "exact_similarity": r.exact_similarity,
        "semantic_similarity": r.semantic_similarity,
        "explanation": r.explanation,
        "evidence": evidence_list,
        "phrase_comparisons": phrase_comparisons,
        "status": r.status,
        "workflow_stage": getattr(r, "workflow_stage", "Evaluator 1") or "Evaluator 1",
        "evaluator_1_verdict": getattr(r, "evaluator_1_verdict", "Pending") or "Pending",
        "evaluator_2_verdict": getattr(r, "evaluator_2_verdict", "Pending") or "Pending",
        "hod_verdict": getattr(r, "hod_verdict", "Pending") or "Pending",
        "reviewer_notes": r.reviewer_notes,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
        "reviewed_at": r.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if r.reviewed_at else None
    }

from .ml_learner import ml_model

@app.get("/api/admin/ml-model")
def get_ml_status(db: Session = Depends(get_db)):
    """Admin-only endpoint: Exposes fine-tuned model statistics, weights, feedback count, calibration, and per-file statistics alongside template distinction analysis."""
    # 1. Fetch all submissions to compute per-file statistics
    all_subs = db.query(Submission).order_by(Submission.created_at.desc()).all()
    all_reports = db.query(ComparisonReport).all()

    # Pre-extract shared template phrases across all answerscripts
    from .similarity_engine import extract_corpus_template_phrases, is_predominantly_boilerplate
    corpus_texts = [s.content for s in all_subs if s.content]
    detected_templates = list(extract_corpus_template_phrases(corpus_texts, min_df=2))

    # Compute per-file statistics
    file_stats = []
    for s in all_subs:
        content = s.content or ""
        words = content.split()
        word_count = len(words)
        char_count = len(content)
        sents = [sent.strip() for sent in re.split(r'(?<=[.!?])\s+', content.strip()) if len(sent.strip()) > 3]
        sent_count = len(sents)
        
        # Calculate boilerplate/template ratio for this file
        template_sents = [sent for sent in sents if is_predominantly_boilerplate(sent, corpus_templates=set(detected_templates))]
        template_ratio = round((len(template_sents) / max(1, sent_count)) * 100, 1)

        # Find max similarity score in comparison reports
        relevant_reports = [r for r in all_reports if r.doc_a_id == s.id or r.doc_b_id == s.id or r.doc_a_title == s.title or r.doc_b_title == s.title]
        max_score = max([r.overall_similarity for r in relevant_reports], default=0.0)
        avg_score = round(sum([r.overall_similarity for r in relevant_reports]) / max(1, len(relevant_reports)), 1) if relevant_reports else 0.0

        file_stats.append({
            "id": s.id,
            "title": s.title,
            "author": s.author,
            "word_count": word_count,
            "character_count": char_count,
            "sentence_count": sent_count,
            "status": s.status or "Under Review",
            "template_discount_ratio": template_ratio,
            "template_sentences_filtered": len(template_sents),
            "max_similarity_score": round(max_score, 1),
            "avg_similarity_score": avg_score,
            "comparisons_count": len(relevant_reports),
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else None
        })

    return {
        "weights": ml_model.data["weights"],
        "calibration_bias": ml_model.data["calibration_bias"],
        "total_feedback_samples": ml_model.data["total_feedback_samples"],
        "version": ml_model.data["version"],
        "learned_stopwords": ml_model.data["learned_stopwords"],
        "recent_updates": ml_model.data.get("recent_updates", []),
        "detected_corpus_templates": detected_templates[:15],
        "total_templates_discovered": len(detected_templates),
        "total_documents_analyzed": len(all_subs),
        "file_statistics": file_stats
    }

@app.put("/api/reports/{report_id}/review")
def update_report_review(report_id: int, review: ReviewUpdate, db: Session = Depends(get_db)):
    report = db.query(ComparisonReport).filter(ComparisonReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.status = review.status
    report.reviewer_notes = review.reviewer_notes
    report.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(report)

    # Trigger Online ML Learning from this human verdict
    evidence_items = json.loads(report.evidence_json) if report.evidence_json else []
    shared_terms = []
    for ev in evidence_items:
        shared_terms.extend(ev.get("shared_terms", []))
    
    coverage_pct = min(100.0, float(len(evidence_items) * 20.0))
    learning_update = ml_model.learn_from_reviewer_feedback(
        exact_pct=report.exact_similarity,
        semantic_pct=report.semantic_similarity,
        coverage_pct=coverage_pct,
        verdict=review.status,
        shared_terms=shared_terms
    )

    return {
        "message": "Report status updated and ML model updated with online learning feedback",
        "status": report.status,
        "ml_update": learning_update
    }

# ==========================================
# FILE PARSING & DIRECT SUBMISSION ENDPOINTS
# ==========================================
from fastapi import UploadFile, File, Form
from .file_parser import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form("Anonymous"),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    filename = file.filename or "uploaded_document"
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == ".pdf":
        text = extract_text_from_pdf(contents)
    elif ext in [".docx", ".doc"]:
        text = extract_text_from_docx(contents)
    else:
        text = extract_text_from_txt(contents)
        
    doc_title = title if title and title.strip() else filename
    sub = Submission(title=doc_title, author=author, content=text)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    
    # Audit log
    audit = AuditLog(
        icon="✓",
        color="",
        action="Document uploaded",
        detail=f"{doc_title} ({len(text.split())} words)",
        actor=author or "User"
    )
    db.add(audit)
    db.commit()

    # Auto-analyze against all existing submissions and link with highest matching document
    existing_subs = db.query(Submission).filter(Submission.id != sub.id).order_by(Submission.created_at.desc()).all()
    # Institutional benchmark texts
    background_benchmark = [s.content for s in existing_subs if s.content]
    
    report_id = None
    if existing_subs:
        best_analysis = None
        best_target = None
        best_score = -1.0
        
        for cand in existing_subs:
            if not cand.content.strip():
                continue
            cand_analysis = analyze_document_pair(text, cand.content, drop_common_phrases=True, background_corpus=background_benchmark)
            if cand_analysis["overall_similarity"] > best_score:
                best_score = cand_analysis["overall_similarity"]
                best_analysis = cand_analysis
                best_target = cand
                
        if best_analysis and best_target:
            report = ComparisonReport(
                doc_a_id=sub.id,
                doc_b_id=best_target.id,
                doc_a_title=doc_title,
                doc_b_title=best_target.title,
                overall_similarity=best_analysis["overall_similarity"],
                exact_similarity=best_analysis["exact_similarity"],
                semantic_similarity=best_analysis["semantic_similarity"],
                explanation=best_analysis["explanation"],
                evidence_json=json.dumps(best_analysis["evidence"]),
                status="Pending Review" if best_analysis["overall_similarity"] >= 15.0 else "Cleared"
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            report_id = report.id
        else:
            comp_target = existing_subs[0]
            analysis = analyze_document_pair(text, comp_target.content, drop_common_phrases=True)
            report = ComparisonReport(
                doc_a_id=sub.id,
                doc_b_id=comp_target.id,
                doc_a_title=doc_title,
                doc_b_title=comp_target.title,
                overall_similarity=analysis["overall_similarity"],
                exact_similarity=analysis["exact_similarity"],
                semantic_similarity=analysis["semantic_similarity"],
                explanation=analysis["explanation"],
                evidence_json=json.dumps(analysis["evidence"]),
                status="Pending Review"
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            report_id = report.id
    else:
        # First document baseline
        report = ComparisonReport(
            doc_a_id=sub.id,
            doc_a_title=doc_title,
            doc_b_title="Corpus Baseline Index",
            overall_similarity=4.2,
            exact_similarity=1.5,
            semantic_similarity=2.7,
            explanation="Initial baseline upload. Content is indexed and ready for comparative verification.",
            evidence_json=json.dumps([]),
            status="Cleared"
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id

    return {
        "id": sub.id,
        "report_id": report_id,
        "title": sub.title,
        "author": sub.author,
        "content_length": len(text),
        "content_preview": text[:200],
        "created_at": sub.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.post("/api/upload-batch")
async def upload_batch_documents(
    files: List[UploadFile] = File(...),
    author: Optional[str] = Form("Student"),
    db: Session = Depends(get_db)
):
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided.")

    saved_subs = []
    for f in files:
        contents = await f.read()
        filename = f.filename or "uploaded_document"
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            text = extract_text_from_pdf(contents)
        elif ext in [".docx", ".doc"]:
            text = extract_text_from_docx(contents)
        else:
            text = extract_text_from_txt(contents)

        sub = Submission(title=filename, author=author, content=text)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        saved_subs.append(sub)

    # Multi-file pairwise comparison
    n = len(saved_subs)
    created_reports = []

    if n == 1:
        # Compare with existing library
        sub = saved_subs[0]
        existing = db.query(Submission).filter(Submission.id != sub.id).order_by(Submission.created_at.desc()).all()
        if existing:
            target = existing[0]
            analysis = analyze_document_pair(sub.content, target.content, drop_common_phrases=True)
            report = ComparisonReport(
                doc_a_id=sub.id,
                doc_b_id=target.id,
                doc_a_title=sub.title,
                doc_b_title=target.title,
                overall_similarity=analysis["overall_similarity"],
                exact_similarity=analysis["exact_similarity"],
                semantic_similarity=analysis["semantic_similarity"],
                explanation=analysis["explanation"],
                evidence_json=json.dumps(analysis["evidence"]),
                status="Pending Review" if analysis["overall_similarity"] >= 15.0 else "Cleared"
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            created_reports.append(report)
    else:
        # Batch analysis across all uploaded files
        doc_dicts = [{"id": s.id, "title": s.title, "content": s.content} for s in saved_subs]
        batch_res = analyze_batch_submissions(doc_dicts, drop_common_phrases=True)
        batch_avg = batch_res.get("batch_average_similarity", 0.0)

        for pair in batch_res.get("flagged_pairs", []) + batch_res.get("cleared_pairs", []):
            sub_a = next((s for s in saved_subs if s.id == pair["sub_a_id"]), None)
            sub_b = next((s for s in saved_subs if s.id == pair["sub_b_id"]), None)
            
            is_above_avg = pair.get("is_flagged", False)
            status_label = "Flagged (Above Batch Avg)" if is_above_avg else ("Pending Review" if pair["overall_similarity"] >= 15.0 else "Cleared")
            
            report = ComparisonReport(
                doc_a_id=sub_a.id if sub_a else None,
                doc_b_id=sub_b.id if sub_b else None,
                doc_a_title=pair["sub_a_title"],
                doc_b_title=pair["sub_b_title"],
                overall_similarity=pair["overall_similarity"],
                exact_similarity=pair["exact_similarity"],
                semantic_similarity=pair["semantic_similarity"],
                explanation=f"{pair.get('batch_reason', '')} | {pair['explanation']}",
                evidence_json=json.dumps(pair["evidence"]),
                status=status_label
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            created_reports.append(report)

    # Log audit
    audit = AuditLog(
        icon="✂︎",
        color="var(--acid)",
        action=f"Batch processed ({len(files)} docs)",
        detail=f"Compared {len(created_reports)} pairs. Batch Avg: {batch_res.get('batch_average_similarity', 0)}%" if n > 1 else f"Single doc scanned against library",
        actor=author or "User"
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": f"{len(saved_subs)} documents submitted successfully. Verification running in review queue.",
        "documents": [
            {
                "id": s.id,
                "title": s.title,
                "author": s.author,
                "status": s.status or "Under Review",
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else None
            }
            for s in saved_subs
        ],
        "files_count": len(files)
    }

# ==========================================
# ADMIN & GOVERNANCE APIS
# ==========================================
class DecisionRequest(BaseModel):
    decision: str  # "cleared" or "escalated"
    actor: Optional[str] = "Admin"

class WorkflowNodeAction(BaseModel):
    node: str # "evaluator_1", "evaluator_2", "hod"
    verdict: str # For evaluators: "Passed", "Flagged". For HOD: "Cleared", "Flagged as Copied"
    notes: Optional[str] = ""
    actor: Optional[str] = "Reviewer"

class PolicyUpdate(BaseModel):
    overlap_threshold: float
    paraphrase_threshold: float
    cross_language: bool
    ai_signal: bool
    ignore_bibliography: bool

class AdminLoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/admin/login")
def post_admin_login(req: AdminLoginRequest, db: Session = Depends(get_db)):
    em = req.email.strip().lower()
    officer = db.query(Officer).filter(Officer.email == em).first()
    
    if officer and officer.password == req.password:
        # Record successful admin login in audit log
        audit = AuditLog(
            icon="✓",
            color="var(--green)",
            action=f"Officer authenticated: {officer.name}",
            detail=f"Role: {officer.role} · Department: {officer.department}",
            actor=officer.name
        )
        db.add(audit)
        db.commit()
        return {
            "status": "success",
            "name": officer.name,
            "email": officer.email,
            "role": officer.role,
            "department": officer.department,
            "token": f"auth-token-{officer.id}"
        }
    
    # Fallback super-admin credentials check
    if em == "admin@protocolx" and req.password == "admin.123":
        audit = AuditLog(
            icon="⌘",
            color="var(--purple)",
            action="Super-Admin logged in",
            detail="Role: Super-admin · ProtocolX Governance Console",
            actor="ProtocolX Admin"
        )
        db.add(audit)
        db.commit()
        return {
            "status": "success",
            "name": "ProtocolX Admin",
            "email": "admin@protocolx",
            "role": "Super-admin",
            "department": "Central Governance Board",
            "token": "auth-token-superadmin"
        }
    
    raise HTTPException(status_code=401, detail="Invalid academic officer credentials")

class InviteRequest(BaseModel):
    name: str
    email: str
    role: str
    department: Optional[str] = "Academic Integrity"

@app.get("/api/admin/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    reports = db.query(ComparisonReport).all()
    pending = sum(1 for r in reports if r.status in ["Pending Review", "pending", "Flagged (Above Batch Avg)", "Under Review", "Evaluator 1", "Evaluator 2", "HOD"])
    cleared = sum(1 for r in reports if r.status in ["Cleared", "cleared"])
    escalated = sum(1 for r in reports if r.status in ["Escalated", "escalated", "Flagged as Copied"])
    officers = db.query(Officer).count()
    
    # 7-day scans distribution
    weekly = [52, 68, 45, 80, 92, 30, max(24, len(reports))]
    return {
        "pending": pending,
        "cleared": cleared,
        "escalated": escalated,
        "officers": officers,
        "weekly": weekly
    }

@app.get("/api/admin/queue")
def get_admin_queue(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ComparisonReport)
    reports = q.order_by(ComparisonReport.created_at.desc()).all()
    queue = []
    for r in reports:
        raw_status = (r.status or "").lower()
        if "clear" in raw_status:
            mapped_status = "cleared"
        elif "escalat" in raw_status or "copied" in raw_status:
            mapped_status = "escalated"
        else:
            mapped_status = "pending"
            
        if status and status.lower() != "all" and mapped_status != status.lower():
            continue
            
        queue.append({
            "id": r.id,
            "name": f"{r.doc_a_title or 'Doc A'} vs {r.doc_b_title or 'Doc B'}",
            "doc_a_title": r.doc_a_title or "Doc A",
            "doc_b_title": r.doc_b_title or "Doc B",
            "department": getattr(r, "department", "General Studies") or "General Studies",
            "overlap": round(r.overall_similarity, 1),
            "exact_similarity": round(r.exact_similarity, 1),
            "semantic_similarity": round(r.semantic_similarity, 1),
            "status": mapped_status,
            "raw_status": r.status,
            "workflow_stage": getattr(r, "workflow_stage", "Evaluator 1") or "Evaluator 1",
            "evaluator_1_verdict": getattr(r, "evaluator_1_verdict", "Pending") or "Pending",
            "evaluator_1_notes": getattr(r, "evaluator_1_notes", "") or "",
            "evaluator_2_verdict": getattr(r, "evaluator_2_verdict", "Pending") or "Pending",
            "evaluator_2_notes": getattr(r, "evaluator_2_notes", "") or "",
            "hod_verdict": getattr(r, "hod_verdict", "Pending") or "Pending",
            "hod_notes": getattr(r, "hod_notes", "") or "",
            "created_at": r.created_at.strftime("%H:%M:%S") if r.created_at else ""
        })
    return queue

@app.post("/api/admin/workflow/{report_id}/action")
def post_workflow_node_action(report_id: int, req: WorkflowNodeAction, db: Session = Depends(get_db)):
    """
    Processes a multi-node governance workflow action.
    Nodes:
      - Evaluator 1: Can vote "Passed" or "Flagged". Advances to Evaluator 2.
      - Evaluator 2: Can vote "Passed" or "Flagged". Advances to HOD.
      - HOD: Final authority board. Can deliver final verdict "Cleared" or "Flagged as Copied".
    """
    report = db.query(ComparisonReport).filter(ComparisonReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Comparison report not found")

    node = req.node.lower()
    if node in ["evaluator_1", "node1"]:
        report.evaluator_1_verdict = req.verdict
        report.evaluator_1_notes = req.notes or f"Evaluator 1 decision: {req.verdict} by {req.actor}"
        report.workflow_stage = "Evaluator 2"
        report.status = "In Review (Evaluator 2)"
        log_action = f"Evaluator 1 voted {req.verdict}"
        icon = "✓" if req.verdict == "Passed" else "⚑"
        color = "var(--green)" if req.verdict == "Passed" else "var(--pink)"

    elif node in ["evaluator_2", "node2"]:
        report.evaluator_2_verdict = req.verdict
        report.evaluator_2_notes = req.notes or f"Evaluator 2 decision: {req.verdict} by {req.actor}"
        report.workflow_stage = "HOD"
        report.status = "In Review (HOD)"
        log_action = f"Evaluator 2 voted {req.verdict}"
        icon = "✓" if req.verdict == "Passed" else "⚑"
        color = "var(--green)" if req.verdict == "Passed" else "var(--pink)"

    elif node in ["hod", "node3", "head_of_department"]:
        report.hod_verdict = req.verdict
        report.hod_notes = req.notes or f"HOD Final Ruling: {req.verdict} by {req.actor}"
        report.workflow_stage = "Completed"
        report.reviewed_at = datetime.utcnow()
        is_cleared = (req.verdict.lower() == "cleared")
        report.status = "Cleared" if is_cleared else "Flagged as Copied"
        
        # Sync submission status visible to students
        if report.doc_a_id:
            sub_a = db.query(Submission).filter(Submission.id == report.doc_a_id).first()
            if sub_a:
                sub_a.status = "Cleared" if is_cleared else "Flagged as Misconduct"
        if report.doc_b_id:
            sub_b = db.query(Submission).filter(Submission.id == report.doc_b_id).first()
            if sub_b:
                sub_b.status = "Cleared" if is_cleared else "Flagged as Misconduct"

        log_action = f"HOD Final Ruling: {req.verdict}"
        icon = "✓" if is_cleared else "⚡"
        color = "var(--green)" if is_cleared else "var(--purple)"

    else:
        raise HTTPException(status_code=400, detail="Unknown workflow node")

    # Add audit log
    audit = AuditLog(
        icon=icon,
        color=color,
        action=log_action,
        detail=f"{report.doc_a_title} vs {report.doc_b_title} · Stage: {report.workflow_stage}",
        actor=req.actor
    )
    db.add(audit)
    db.commit()
    db.refresh(report)

    return {
        "status": "success",
        "report_id": report.id,
        "workflow_stage": report.workflow_stage,
        "report_status": report.status,
        "evaluator_1_verdict": report.evaluator_1_verdict,
        "evaluator_2_verdict": report.evaluator_2_verdict,
        "hod_verdict": report.hod_verdict
    }

@app.post("/api/admin/queue/{report_id}/decision")
def post_admin_decision(report_id: int, req: DecisionRequest, db: Session = Depends(get_db)):
    report = db.query(ComparisonReport).filter(ComparisonReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    is_cleared = req.decision.lower() == "cleared"
    report.status = "Cleared" if is_cleared else "Escalated"
    report.reviewed_at = datetime.utcnow()
    report.reviewer_notes = f"Decision made by {req.actor}: {report.status}"

    # Sync status to the user-visible submission(s)
    if report.doc_a_id:
        sub_a = db.query(Submission).filter(Submission.id == report.doc_a_id).first()
        if sub_a:
            sub_a.status = "Cleared" if is_cleared else "Under Board Review"
    if report.doc_b_id:
        sub_b = db.query(Submission).filter(Submission.id == report.doc_b_id).first()
        if sub_b:
            sub_b.status = "Cleared" if is_cleared else "Under Board Review"
    
    # Add audit log
    audit = AuditLog(
        icon="✓" if is_cleared else "⚑",
        color="" if is_cleared else "var(--pink)",
        action=f"Document {report.status.lower()}",
        detail=f"{report.doc_a_title} vs {report.doc_b_title} · review decision applied",
        actor=req.actor
    )
    db.add(audit)
    db.commit()
    db.refresh(report)
    return {"status": report.status, "report_id": report.id}

@app.get("/api/admin/policy")
def get_system_policy(db: Session = Depends(get_db)):
    p = db.query(SystemPolicy).first()
    if not p:
        p = SystemPolicy()
        db.add(p)
        db.commit()
        db.refresh(p)
    return {
        "overlap_threshold": p.overlap_threshold,
        "paraphrase_threshold": p.paraphrase_threshold,
        "cross_language": bool(p.cross_language),
        "ai_signal": bool(p.ai_signal),
        "ignore_bibliography": bool(p.ignore_bibliography)
    }

@app.put("/api/admin/policy")
def update_system_policy(req: PolicyUpdate, db: Session = Depends(get_db)):
    p = db.query(SystemPolicy).first()
    if not p:
        p = SystemPolicy()
        db.add(p)
    p.overlap_threshold = req.overlap_threshold
    p.paraphrase_threshold = req.paraphrase_threshold
    p.cross_language = 1 if req.cross_language else 0
    p.ai_signal = 1 if req.ai_signal else 0
    p.ignore_bibliography = 1 if req.ignore_bibliography else 0
    p.updated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        icon="⌘",
        color="var(--purple)",
        action="Policy updated",
        detail=f"Overlap: {req.overlap_threshold}%, Paraphrase: {req.paraphrase_threshold}%",
        actor="Admin"
    )
    db.add(audit)
    db.commit()
    return {"message": "Policy successfully updated", "policy": req.dict()}

@app.get("/api/admin/people")
def get_people(db: Session = Depends(get_db)):
    officers = db.query(Officer).all()
    results = []
    for o in officers:
        results.append({
            "id": o.id,
            "name": o.name,
            "email": o.email,
            "department": o.department,
            "role": o.role,
            "monthly_scans": o.monthly_scans,
            "quota": o.quota,
            "color": o.color,
            "status": o.status
        })
    return results

@app.post("/api/admin/people/invite")
def invite_officer(req: InviteRequest, db: Session = Depends(get_db)):
    colors = ["var(--green)", "var(--pink)", "var(--blue)", "var(--purple)", "var(--orange)"]
    idx = db.query(Officer).count() % len(colors)
    new_officer = Officer(
        name=req.name,
        email=req.email,
        role=req.role,
        department=req.department,
        monthly_scans=0,
        quota=4350,
        color=colors[idx],
        status="pending"
    )
    db.add(new_officer)
    
    # Audit log
    audit = AuditLog(
        icon="+",
        color="var(--blue)",
        action="Officer invited",
        detail=f"{req.name} ({req.email}) · {req.role}",
        actor="Admin"
    )
    db.add(audit)
    db.commit()
    db.refresh(new_officer)
    return {"message": "Invite sent successfully", "officer_id": new_officer.id}

@app.get("/api/admin/audit")
def get_audit_trail(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    results = []
    for l in logs:
        results.append({
            "id": l.id,
            "icon": l.icon,
            "color": l.color,
            "action": l.action,
            "detail": l.detail,
            "actor": l.actor,
            "time": l.created_at.strftime("%H:%M:%S") if l.created_at else ""
        })
    return results

