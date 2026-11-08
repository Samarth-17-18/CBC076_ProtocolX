# Synapse — Forensic Text Similarity & Academic Integrity Governance Platform
**ProtocolX (CBC076)**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

Synapse is an institutional text similarity, plagiarism detection, and academic integrity governance platform designed for universities and academic review boards. It combines multi-tier NLP heuristic engines with side-by-side forensic visualization, explainable diagnostic categorization, and a 3-node institutional review workflow.

---

## 🌟 Key Features

### 1. 🎓 Student Submission Portal (`/`)
- **Drag-and-Drop Ingestion**: Natively processes `.pdf`, `.docx`, and `.txt` files with automated text sanitization and structure preservation.
- **Privacy-Preserving Digital Receipts**: Issues immutable submission tokens (`#SYN-RCPT-xxxx`) with non-confidential originality indicators without exposing cohort comparison matrices.
- **Student History Ledger**: Tracks document processing status, timestamps, and receipt records.

### 2. 🏛️ Admin Governance Desk (`/admin`)
- **Institutional Access Gate**: Role-based access control protecting governance operations and cohort records.
- **3-Node Verification Board**: Multistage arbitration workflow:
  $$\text{Evaluator 1} \longrightarrow \text{Evaluator 2} \longrightarrow \text{Head of Department (HOD)}$$
- **Forensic Inspector**:
  - **Side-by-Side Sentence Alignment**: Aligns document sentences directly with their closest matching source counterpart.
  - **4-Tier Color Coding**:
    - 🔴 **Verbatim Copy** (`pink` / `#f43f5e`): Direct word-for-word duplication without attribution ($\ge 75\%$ similarity).
    - 🟡 **Paraphrased** (`amber` / `#f59e0b`): Structural mimicry with synonym substitution ($45\% - 74\%$ similarity).
    - 🔵 **Template / Common Prompt** (`sky` / `#38bdf8`): Shared boilerplate, assignment instructions, or standardized questions excluded from plagiarism scores.
    - 🟢 **Independent / Cleared** (`emerald` / `#10b981`): Original, unshared student phrasing ($< 45\%$ similarity).
  - **Explainable Diagnostics**: Every flagged or cleared sentence displays an explicit reason and shared anchor keywords explaining the classification.
  - **⚡ Live Text Direct Compare Sandbox**: On-demand sandbox modal to paste and compare arbitrary text snippets in real time.
- **Batch Cohort Matrix**: Comprehensive queue with cross-pair similarity matrices, risk tags (`High Risk`, `Moderate`, `Clean`), and one-click case loading.
- **SGD Online Learning Monitor**: Dynamic weight adjustment tracking false-positive mitigation and model calibration over time.
- **Immutable Audit Ledger**: Granular event logging of all evaluations, approvals, dismissals, and sensitivity modifications.

---

## 🏗️ Architecture & Directory Layout

```
CBC076_ProtocolX/
├── backend/                        # FastAPI Application & Analysis Core
│   ├── database.py                 # SQLite engine, sessions, and initial seeding
│   ├── file_parser.py              # Native PDF, DOCX, and TXT document extractors
│   ├── main.py                     # API routes, admin auth, and static file mounts
│   ├── ml_learner.py               # SGD active learning and weight adaptation
│   ├── models.py                   # SQLAlchemy schema models and Pydantic DTOs
│   └── similarity_engine.py        # Tokenizers, n-gram diffing, and forensic matcher
├── demo_submissions/               # Standardized test submissions (student_A to F)
├── uiux/                           # Frontend Web Portals
│   ├── admin/
│   │   └── synapse_admin.html      # Institutional Governance Desk & Forensic Inspector
│   └── user/
│       └── synapse.html            # Student Submission Portal
├── synapse_plagiarism.db           # Pre-seeded SQLite database with demo comparisons
├── requirements.txt                # Python dependencies
├── .gitattributes                  # Repository attributes
├── .gitignore                      # Git ignore rules
└── README.md                       # Documentation
```

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Samarth-17-18/CBC076_ProtocolX.git
cd CBC076_ProtocolX
```

### 2. Set Up Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Synapse Server
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

---

## 🌐 Portal Endpoints & Access

| Portal | URL | Description | Credentials |
| :--- | :--- | :--- | :--- |
| **Student Portal** | [http://localhost:8001/](http://localhost:8001/) | Submission & Digital Receipts | Public / Student |
| **Admin Governance Desk** | [http://localhost:8001/admin](http://localhost:8001/admin) | Governance, Forensic Inspector & Review Board | `admin@protocolx` / `admin.123` |
| **Interactive API Docs** | [http://localhost:8001/docs](http://localhost:8001/docs) | Swagger UI for backend endpoints | Public |

### Evaluator Credentials
- **Master Admin / HOD**: `admin@protocolx` | `admin.123`
- **Lead Evaluator**: `evaluator.alpha@protocolx` | `admin.123`
- **Secondary Evaluator**: `evaluator.beta@protocolx` | `admin.123`

---

## 🧪 Demo Test Cases

Pre-seeded cohort submissions in `demo_submissions/`:
- **Case #20** (`student_A.txt` vs `student_B.txt`): **80.2% Overlap** — Verbatim plagiarism test case (6 word-for-word copy sentences).
- **Case #21** (`student_A.txt` vs `student_C.txt`): **59.3% Overlap** — Paraphrase attack test case (synonym swapping and structural mimicry).
- **Case #26** (`student_A.txt` vs `student_D.txt`): **28.7% Overlap** — Independent submission (cleared, 6 of 8 sentences have 0% overlap).
- **Case #27** (`student_A.txt` vs `student_E.txt`): **46.8% Overlap** — Partial reuse and mixed sentences.

---

## 📄 License
This project is licensed under the MIT License.
