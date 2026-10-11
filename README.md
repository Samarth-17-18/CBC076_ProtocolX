Description & Vision: Overview of Synapse as an AI-powered text similarity, plagiarism detection, and academic integrity governance platform.
Feature Breakdown:
Student Portal (/): Multi-document uploading (.pdf, .docx, .txt), tracking verification status receipts without exposing confidential matrices.
Admin Governance Desk (/admin): 3-Node verification board (Evaluator 1 ➔ Evaluator 2 ➔ Head of Department), Side-by-Side forensic inspector (verbatim and paraphrase highlighting), corpus template/prompt exclusions, ML online learning stats, and audit trails.
Tech Stack:
Backend: FastAPI, Uvicorn, SQLAlchemy, SQLite, Python NLP heuristics (difflib, Jaccard tokenizers, semantic embeddings, python-docx, pypdf).
Frontend: Vanilla HTML5/CSS3 with brand design tokens (--acid, --pink, --sky, --card, --ink) and reactive ES6+ JavaScript.
Setup & Run Instructions:
Repository cloning, virtual environment creation (Windows PowerShell / macOS / Linux), and dependency installation.
Run command (python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload).
Portal endpoint URLs and default credentials (admin@protocolx / admin.123).
Project Architecture: Tree map illustrating directory and file layout.
