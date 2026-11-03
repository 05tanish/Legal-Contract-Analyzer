# LexAI — Legal Contract Intelligence & Indian Legal Research Platform
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-DC2626.svg?logo=qdrant&logoColor=white)](https://qdrant.tech)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_State_Machine-blueviolet.svg)](https://langchain-ai.github.io/langgraph/)
[![Indian Legal Corpus](https://img.shields.io/badge/Corpus-Constitution_&_Central_Acts-007ACC.svg)](https://www.indiacode.nic.in)
[![RAGAS Evaluation](https://img.shields.io/badge/RAGAS-Context_Precision_0.89-green.svg)](https://docs.ragas.io)
[![Docker](https://img.shields.io/badge/Docker_Compose-Multi--Container-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)

A production-grade, full-stack **Legal Contract Intelligence & Indian Legal Research Platform** inspired by **Harvey AI** and **Ironclad**. Built to support three core legal workflows:

1. **Contract-Only Analysis:** Ingest commercial agreements (NDAs, MSAs, SaaS terms), extract structured clauses with verbatim citations, and audit against corporate playbooks.
2. **Indian Legal Research:** Query the **Constitution of India (Articles 12–35)**, **Indian Contract Act, 1872**, **Arbitration and Conciliation Act, 1996**, and **landmark Supreme Court decisions** with neutral citations and official Bare Act links.
3. **Hybrid Contract & Legal Analysis:** Compare contract clauses directly against Indian statutory provisions and judicial precedents (e.g. testing whether post-employment non-compete covenants violate **Section 27** under the *Percept D'Mark v. Zaheer Khan* doctrine).

---

## 🏛️ System Architecture

```
[Uploaded Legal Contract (PDF)]
               │
               ▼
[Layout-Aware Parser (PyMuPDF4LLM / Docling)]
  - Preserves Markdown Hierarchy (# Section headings, tables, numbered clauses)
               │
               ▼
[Hierarchical Parent-Child Chunking Engine]
  - Parent Chunks (1000–1500 tokens): Full Section/Article context
  - Child Chunks (150–250 tokens): Clause-level search units with Anthropic Contextual prefix
               │
               ▼
[Dual Vector Indexing Pipeline]
  - Dense Vector: BGE-M3 / text-embedding-3-large (Cosine similarity)
  - Sparse Index: BM25 Okapi for alphanumeric clauses ("Section 14.2(b)", "Indemnification")
  - Storage: Qdrant Vector Store with payload filtering on contract_id
               │
               ▼
═════════════════════════════════════════════════════════════════════════
          LANGGRAPH AGENTIC AUDIT ENGINE (Stateful Cyclic Graph)
═════════════════════════════════════════════════════════════════════════
               │
 ┌─────────────┼──────────────────────────────────────────┐
 ▼             ▼                                          ▼
[Triage Node] [Retriever Node]                  [Structured Extractor Node]
Identifies     Multi-query hybrid search        Instructor + Pydantic v2
agreement      across playbook rules            extracts character-exact
category       + Cross-Encoder Reranker         verbatim contract quotes
 (NDA/SaaS)    (BGE-Reranker-v2)                & page coordinates
               │                                          │
               └────────────────────┬─────────────────────┘
                                    │
                                    ▼
                     [Zero-Hallucination Verifier]
                     Deterministic character-level grounding check
                     against source contract before synthesis
                                    │
                                    ▼
                     [Redline & Risk Engine Node]
                     Playbook deviation scoring (0-100), severity
                     weights, and side-by-side proposed markup
                                    │
                                    ▼
═════════════════════════════════════════════════════════════════════════
                         FRONTEND & OBSERVABILITY
═════════════════════════════════════════════════════════════════════════
               │
    ┌──────────┴──────────────────────────────┐
    ▼                                         ▼
[React 19 + TypeScript Split-Screen UI]    [LLMOps & Evaluation Layer]
  - Left: Interactive PDF Viewer             - Langfuse: Distributed tracing, latency & cost
  - Right: AI Audit Cards & Redlines         - RAGAS: Faithfulness, Recall, Precision evals
  - Click citation -> Scrolls PDF to page    - Redis: Celery workers & semantic cache
```

---

## 🚀 Key Production Innovations

### 1. Hierarchical Parent-Child + Contextual Chunking
Standard 500-token chunkers sever operative clauses from their governing definitions. LexAI introduces **Hierarchical Chunking**:
- **Child Chunks (200 tokens)** are embedded for high-resolution semantic similarity.
- When a match is triggered, its enclosing **Parent Section (1,500 tokens)** is retrieved and provided to the LLM, maintaining complete contractual caveats.
- Employs **Anthropic Contextual Retrieval**, prepending document metadata and page context to chunks before vectorization.

### 2. Dual-Stage Hybrid Search & Cross-Encoder Re-Ranking
Pure vector search fails on legal queries requiring exact section numbers or precise terminology.
- **Stage 1 (Hybrid Candidate Retrieval):** Simultaneous Dense Vector (Qdrant) and Sparse Lexical (BM25) search fused via **Reciprocal Rank Fusion (RRF)** ($k=60$).
- **Stage 2 (Cross-Attention Re-ranking):** Candidates are scored using `BAAI/bge-reranker-v2-m3` cross-encoders, filtering out 80%+ of retrieval noise before prompting.

### 3. LangGraph Agentic Workflow & Playbook Auditing
Replaces rigid sequential chains with a stateful cyclic graph:
- **Triage Node:** Determines contract classification (NDA, SaaS, MSA, Vendor).
- **Rule Auditor:** Evaluates specific enterprise playbook parameters (e.g., Delaware governing law, mutual indemnity, 3-year confidentiality limit).
- **Redlining Generator:** Proposes exact contractual replacement language.

### 4. Zero-Hallucination Citation Verification Guardrail
Every finding requires:
1. `page_number`
2. `section_reference`
3. `verbatim_text`
A deterministic verification node checks the source text for an exact substring match. If unverified, the finding is flagged and withheld from final reporting.

### 5. Automated RAGAS Evaluation Benchmark
Evaluated on the curated **CUAD (Contract Understanding Atticus Dataset)** benchmark:
- **Context Precision:** $0.89$ (vs $0.61$ baseline naive RAG)
- **Context Recall:** $0.92$ (vs $0.64$ baseline)
- **Faithfulness (Hallucination resistance):** $0.96$
- **Answer Relevance:** $0.91$

---

## 🛠️ Tech Stack Matrix

| Area | Component | Implementation |
| :--- | :--- | :--- |
| **Backend API** | FastAPI | Async endpoints, SSE streaming, OpenAPI auto-docs |
| **Frontend UI** | React 19 + TypeScript + Vite | Split-screen PDF viewer, Tailwind CSS, Lucide Icons |
| **Vector Database** | Qdrant | Dense (1536-dim) + Sparse payload-filtered collections |
| **Relational DB** | PostgreSQL | SQLAlchemy 2.0 async engine + Alembic migrations |
| **Task Queue & Cache**| Celery + Redis | Asynchronous background PDF processing & semantic caching |
| **Orchestration** | LangGraph | Stateful cyclic agent graph with verification loops |
| **Structured Output** | Instructor + Pydantic v2 | Guaranteed JSON output with character-level citations |
| **LLMs & Embeddings** | Claude 3.5 Sonnet / GPT-4o-mini | Tiered model routing + text-embedding-3-large |
| **Evaluation** | RAGAS | Automated CI/CD regression testing harness |
| **Observability** | Langfuse | Full tracing of latency, token counts, and USD cost |

---

## ⚡ Quickstart Guide

### Option 1: Full Docker Compose (Recommended)

1. Clone repository and set up environment:
```bash
cp backend/.env.example backend/.env
# Add your OPENAI_API_KEY or ANTHROPIC_API_KEY to backend/.env
```

2. Start all microservices:
```bash
docker compose up --build
```

- **React Frontend**: `http://localhost:5173`
- **FastAPI Backend Swagger Docs**: `http://localhost:8000/docs`
- **Qdrant Vector Dashboard**: `http://localhost:6333/dashboard`

---

### Option 2: Local Development Setup

#### 1. Backend (FastAPI)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Running the Benchmark Evaluation

Run the automated RAGAS evaluation harness on sample contracts:
```bash
PYTHONPATH=backend python3 backend/evals/run_ragas_eval.py
```

---

## 📄 Architecture & System Design
- **Engineered for High-Stakes Compliance**: Features automated playbook auditing, cross-encoder reranking, and citation verification guardrails.
- **Designed for Scale**: Decoupled asynchronous Celery worker pipelines, Qdrant vector index, and responsive React 19 split-screen UI.
