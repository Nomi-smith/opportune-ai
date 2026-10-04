# 🚀 Opportune AI

### Personal Opportunity & Application Intelligence Agent

**Discover the right opportunities. Verify them. Understand your fit. Prepare to apply.**

Opportune AI is an AI-powered platform designed to help students, graduates, researchers, and professionals discover and prepare for **scholarships, jobs, internships, master's programs, admissions, and research opportunities** — all from one place.

Instead of manually searching dozens of websites, Opportune AI combines **multi-source discovery, web intelligence, verification, eligibility analysis, profile matching, and application preparation** into a single seamless workflow.

> **DISCOVER → VERIFY → MATCH → PREPARE**

---

## 💡 The Problem

Finding a good opportunity is rarely a simple search problem. Opportunities are scattered across:

- 🎓 University websites
- 💰 Government & private scholarship portals
- 💼 Job boards & company career pages
- 🔬 Research databases & laboratory portals
- 🌍 International education networks

Conventional search engines and aggregators frequently return expired listings, duplicate entries, incorrect classifications, or generic career pages. **Opportune AI transforms this fragmented process into a structured, verified opportunity pipeline.**

---

## 🧠 How It Works

```text
                    USER
                     │
                     ▼
             ┌──────────────┐
             │    INTENT    │
             │  & PROFILE   │
             └──────┬───────┘
                     ▼
             ┌──────────────┐
             │  DISCOVERY   │
             │ Multi-Source │
             └──────┬───────┘
                     ▼
             ┌──────────────┐
             │ NORMALIZE &  │
             │ DEDUPLICATE  │
             └──────┬───────┘
                     ▼
             ┌──────────────┐
             │    VERIFY    │
             │   & FILTER   │
             └──────┬───────┘
                     ▼
             ┌──────────────┐
             │    MATCH     │
             │ User ↔ Opp.  │
             └──────┬───────┘
                     ▼
             ┌──────────────┐
             │   PREPARE    │
             │ CV & Letters │
             └──────┬───────┘
                     ▼
                    USER
```

---

## ✨ Key Features

### 🔎 Discover
Find relevant opportunities tailored to your specific background:
- **Criteria:** Field of study, skills, degree level, target countries, keywords, and user profile.
- **Scope:** Combines structured source registries with live web discovery.

### 🛡️ Verify
Filter out clutter and ensure data integrity using multi-point checks:
- Source-page verification & classification
- Freshness and deadline validation
- Explicit eligibility and location signal analysis
- Funding and official application link verification

### 🎯 Match
Evaluate compatibility between the opportunity and your background:
- Analyzes education, skills, experience, projects, and career targets.
- Delivers a structured match assessment highlighting strengths and gaps.

### 📝 Prepare
Tailor application materials for specific positions:
- AI-assisted CV content extraction and optimization
- Custom Cover Letters, Motivation Letters, and Statements of Purpose (SOP)
- Application-specific response generation

---

## 🌍 Opportunity Categories

| Category | Description & Primary Sources |
| :--- | :--- |
| **🎓 Scholarships** | Curated international programs (DAAD, Chevening, Fulbright, MEXT, GKS, Erasmus+, Commonwealth, etc.) alongside global government/university grants. |
| **💼 Jobs** | Full-time, part-time, remote, hybrid, and on-site professional roles fetched via job platforms and web APIs. |
| **🧑‍💻 Internships** | Early-career, technical, and industry internships across international markets. |
| **🏫 Admissions** | Master's programs, PhD track admissions, and university entrance opportunities. |
| **🔬 Research Positions** | Academic openings, research groups, lab positions, and faculty openings integrated with academic databases (e.g., OpenAlex). |

---

## 🤖 AI + Deterministic Intelligence

Opportune AI follows a **Deterministic-First, AI-Second** engineering philosophy to maximize performance and reliability.

```text
Structured Data ──► Normalization ──► Deduplication ──► Rule-Based Verification ──► AI Reasoning ──► Profile Matching
```

- **Deterministic Logic:** Used for URL parsing, normalization, exact deduplication, freshness rules, and structured field extraction.
- **AI Reasoning:** Applied selectively for ambiguous classification, complex intent planning, semantic profile matching, and document drafting.

**Benefits:** High speed, low API costs, high predictability, and robust fallback behavior.

---

## 🏗️ Multi-Agent Architecture

```text
                        OPPORTUNE AI
                             │
                     ┌───────┴───────┐
                     │  ORCHESTRATOR │
                     └───────┬───────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
Opportunity             Eligibility           Application
  Agents                   Agent                 Agent
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             ▼
                     Intelligence Layer
                             │
                             ▼
                         Web & APIs
                             │
                             ▼
                           SQLite
```

### Agent Roles
- **Opportunity Agent:** Manages multi-source querying and discovery.
- **Eligibility Agent:** Evaluates hard constraints (nationality, degree, GPA, prerequisites).
- **Application Agent:** Generates tailored CVs, SOPs, and cover letters.
- **Document Agent:** Handles document parsing (PDF/DOCX) and information extraction.
- **Intelligence Agent & Chat Agent:** Provides contextual reasoning, Q&A, and conversational assistance.

---

## 🛠️ Project Structure

```text
opportune-ai/
│
├── app.py                     # Main Streamlit application entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Template for environment variables
├── README.md                  # Project documentation
│
├── agents/                    # Multi-agent orchestrators and implementations
│   ├── opportunity_agent.py
│   ├── eligibility_agent.py
│   ├── application_agent.py
│   ├── intelligence_agent.py
│   ├── document_agent.py
│   └── chat_agent.py
│
├── config/                    # Configuration settings & curated libraries
│   ├── settings.py
│   ├── opportunity_sources.json
│   └── scholarship_library.json
│
├── core/                      # Application state and core runtime context
├── database/                  # SQLite models and local persistence handlers
├── documents/                 # PDF/DOCX parsing and CV intelligence modules
├── intelligence/              # Pipeline stages (deduplication, matching, verification)
├── llm/                       # Provider adapters (Gemini, Groq, OpenRouter, Fallback)
├── models/                    # Pydantic schema definitions (User, Opportunity)
├── sources/                   # Source adapters (Jobs, Research, Scholarships)
├── tests/                     # Test suite
└── ui/                        # Streamlit pages and custom UI components
```

---

## ⚙️ Tech Stack & Integrations

- **Frontend / Interface:** Streamlit, Python
- **Data Persistence:** SQLite, Pydantic
- **Networking & Scraping:** HTTPX, BeautifulSoup4
- **Document Parsing:** PyPDF, python-docx
- **Academic Research Data:** OpenAlex API
- **LLM Providers:** Google Gemini, Groq, OpenRouter (with deterministic local fallback)

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Git

### 1. Clone & Setup

```bash
# Clone repository
git clone https://github.com/Nomi-smith/opportune-ai.git
cd opportune-ai

# Create virtual environment
# Windows:
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS:
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Set your preferred API keys in `.env` (the application degrades gracefully if certain keys are absent):

```env
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
SERPER_API_KEY=your_serper_key
```

### 3. Run Locally

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

### 4. Run Tests

```bash
pytest -q
```

---

## 🛡️ Trust & Responsible Automation

Opportune AI operates as an **assistant, not an automated proxy**:
- **No Direct Submissions:** The user reviews all materials and manually submits their own applications.
- **No Groundless Assumptions:** Missing information (deadlines, funding, eligibility) is explicitly marked as `Not stated / Unknown` rather than generated by AI.
- **Security First:** Never stores third-party login credentials, bypasses CAPTCHAs, or fabricates candidate qualifications.

---

## 👤 Author

**Noman Amjad**  
*Artificial Intelligence • AI Agents • Computer Vision • Software Development*

- **GitHub:** [@Nomi-smith](https://github.com/Nomi-smith)
- **Repository:** [Opportune AI](https://github.com/Nomi-smith/opportune-ai)

---

*Opportune AI — Discover. Verify. Match. Prepare.*