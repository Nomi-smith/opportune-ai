# 🚀 Opportune AI

### Personal Opportunity & Application Intelligence Agent

**Opportune AI** is an AI-assisted opportunity discovery and application intelligence platform designed to help users discover relevant **jobs, internships, scholarships, master's programs, research opportunities, and professor/lab leads** from multiple public sources.

Instead of relying on a single job board or database, Opportune AI combines multiple discovery providers, normalizes their results, filters outdated opportunities, compares opportunities with the user's profile, and helps organize the application process.

---

## ✨ What Opportune AI Does

### 🔎 Global Opportunity Discovery

Search across multiple opportunity categories:

- 💼 Jobs
- 🧑‍💻 Internships
- 🎓 Master's / Admissions
- 💰 Scholarships
- 🔬 Research opportunities
- 👨‍🏫 Professors, labs, and research groups

Search can be driven by:

- Role or opportunity type
- Country / multiple countries
- Academic field
- Research area
- Custom search terms
- Saved user profile

The discovery layer is designed for broad public-web coverage rather than restricting users to a fixed list of websites.

---

## 🌐 Multi-Source Search

Opportune AI uses multiple search and data sources so that one provider does not become a single point of failure.

| Source | Purpose |
|---|---|
| **Serper / Google Search** | Direct Google web-search results |
| **OpenRouter Web Search** | Additional live web discovery |
| **Gemini Google Search Grounding** | AI-assisted grounded web discovery |
| **Arbeitnow** | Job discovery |
| **OpenAlex** | Research and academic discovery signals |
| **Public Web Discovery** | Additional lightweight web fallback |

### Provider Failover

If one provider fails or reaches a quota limit, the system can continue using other available providers.

For example:

```text
Gemini Search
     ↓
429 / unavailable
     ↓
Serper + OpenRouter
     ↓
Continue discovery
```

This prevents a single AI/API provider from stopping the entire discovery process.

---

## 🎯 Current-Opportunity Filtering

Opportune AI is designed to prioritize **actionable, current opportunities**.

The discovery pipeline filters and evaluates:

- Expired deadlines
- Historical application cycles
- Current/open application signals
- Future deadlines
- Rolling applications
- Opportunity type
- Country
- Search relevance

Historical pages are not treated as current opportunities simply because they contain matching keywords.

---

## 🧠 Opportunity Intelligence

Discovered pages are normalized into a common opportunity structure.

Each opportunity can contain:

- Title
- Organization
- Opportunity type
- Country
- City
- Description
- Requirements
- Eligibility
- Deadline
- Funding
- Tuition
- Compensation
- Duration
- Application URL
- Source URL
- Source name
- Verification status
- Last verified timestamp
- Additional metadata

This allows results from very different websites to be compared consistently.

---

## 👤 Personal Profile Intelligence

Users can maintain a structured profile containing information such as:

- Education
- Degree
- GPA / CGPA
- Skills
- Tools
- Languages
- Certifications
- Experience
- Projects
- Research interests
- Location preferences
- Career interests
- Tests and scores
- Documents

The profile is used to help interpret and match opportunities.

### Project Management

Projects can be added and removed individually.

The system avoids treating arbitrary CV headings such as `Leadership`, `Coursework`, or `Experience` as projects.

---

## 📄 Documents & CV Intelligence

Opportune AI supports document-oriented workflows for:

- CV/resume information
- Project information
- Application documents
- PDF extraction
- DOCX extraction
- Profile information

The system is designed to distinguish between:

```text
Information found in a document
            ↓
Structured profile information
            ↓
Opportunity matching
```

Unsupported information should not automatically become a permanent user skill or qualification.

---

## 📌 Application Tracker

Users can maintain an application pipeline with statuses such as:

- Saved
- Interested
- Preparing
- Applied
- Interview
- Offer
- Rejected
- Closed

Each application can be updated individually.

Individual records can also be removed without affecting other applications.

---

## 🤖 LLM Architecture

Opportune AI uses an abstraction layer for multiple LLM providers.

Current provider structure:

```text
                 LLM Manager
                     │
          ┌──────────┼──────────┐
          ↓          ↓          ↓
       Gemini      Groq     OpenRouter
          │          │          │
          └──────────┼──────────┘
                     ↓
             Deterministic fallback
```

LLMs are used for tasks such as:

- Search planning
- Query expansion
- Opportunity understanding
- Requirement extraction
- Profile matching
- Multilingual interpretation
- Application assistance
- Agent-style interactions

API availability is treated as variable. The application should continue using deterministic or alternative provider paths when an LLM provider is unavailable.

---

## 🏗️ Architecture

```text
USER
  │
  ▼
STREAMLIT UI
  │
  ▼
ORCHESTRATOR
  ├── Intent / Query Planner
  ├── Parallel Task Runner
  └── State Manager
  │
  ▼
DISCOVERY SOURCES
  ├── Google / Serper
  ├── OpenRouter Web Search
  ├── Gemini Search Grounding
  ├── Arbeitnow
  ├── OpenAlex
  └── Public Web
  │
  ▼
INTELLIGENCE PIPELINE
  ├── Normalization
  ├── Deduplication
  ├── Currentness Filtering
  ├── Verification
  ├── Eligibility
  ├── Matching
  └── Evidence / Source Tracking
  │
  ▼
PROFILE + APPLICATION SYSTEM
  ├── User Profile
  ├── Documents
  ├── Projects
  ├── Applications
  └── Roadmaps
  │
  ▼
SQLITE DATABASE
```

---

## ⚡ Performance Philosophy

Discovery uses parallel source calls where possible.

The architecture is designed to:

- Avoid depending on one search provider
- Use bounded requests
- Apply timeouts to external calls
- Deduplicate URLs and opportunities
- Avoid unnecessary repeated work
- Separate fast discovery from deeper opportunity analysis

The long-term goal is:

```text
SEARCH
  ↓
FAST DISCOVERY
  ↓
FILTER
  ↓
SHOW CURRENT RESULTS
  ↓
DEEP ANALYSIS WHEN NEEDED
```

rather than deeply analyzing every result before showing anything.

---

## 🛡️ Safety & Trust

Opportune AI is designed around evidence and transparency.

### The system should:

- Preserve source URLs
- Identify the source provider
- Distinguish verified and unverified information
- Prefer official opportunity pages for final verification
- Avoid inventing missing values
- Use `N/A` when a source does not provide a value
- Treat community/forum content as leads rather than authoritative proof
- Avoid storing passwords, MFA secrets, or CAPTCHA information
- Keep the user responsible for final application submission

### Important principle

> **If the source does not state it, Opportune AI should not pretend that it knows it.**

---

## 🧩 Project Structure

```text
opportune-ai/
│
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── agents/
├── config/
├── core/
├── database/
├── documents/
├── intelligence/
├── llm/
├── models/
├── sources/
├── tests/
└── ui/
    └── pages/
```

---

## ⚙️ Technology Stack

### Frontend / Application

- Streamlit
- Python

### Backend / Core

- Python
- AsyncIO
- HTTPX
- Pydantic
- BeautifulSoup

### Documents

- PyMuPDF / pypdf
- python-docx

### Database

- SQLite

The database layer is structured so that a future migration to PostgreSQL can be introduced without rebuilding the entire application.

### AI / Search

- Google Gemini
- Groq
- OpenRouter
- Serper
- OpenRouter Web Search
- OpenAlex
- Arbeitnow
- Public web sources

---

## 🔐 Environment Variables

Create a local `.env` file.

```env
APP_ENV=development

GEMINI_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=

OPENROUTER_SEARCH_MODEL=openrouter/free
OPENROUTER_SEARCH_ENGINE=auto

SERPER_API_KEY=
```

### Important

Never commit `.env` or real API keys to GitHub.

Use `.env.example` as the public configuration template.

---

## 🚀 Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Nomi-smith/opportune-ai.git
cd opportune-ai
```

### 2. Create a virtual environment

Windows:

```bat
python -m venv .venv
```

### 3. Activate it

```bat
.venv\Scripts\activate
```

### 4. Install dependencies

```bat
python -m pip install -r requirements.txt
```

### 5. Configure environment variables

Create `.env` and add the API keys you have available.

### 6. Run Opportune AI

```bat
python -m streamlit run app.py
```

The application will normally open at:

```text
http://localhost:8501
```

---

## 🧪 Testing

Run the project tests with:

```bat
python -m pytest
```

For development, keep tests focused on:

- Discovery
- Provider failover
- Currentness filtering
- Deduplication
- Profile/project handling
- Application tracking
- Document extraction
- LLM fallback behavior

---

## 📊 Discovery Flow

A typical search follows this pattern:

```text
User Query
    ↓
Intent Detection
    ↓
Query Planning
    ↓
Parallel Source Discovery
    ↓
Collect URLs
    ↓
Fetch / Extract
    ↓
Normalize
    ↓
Deduplicate
    ↓
Currentness Filter
    ↓
Opportunity Classification
    ↓
Verification
    ↓
Profile Matching
    ↓
Results
```

---

## 🗺️ Roadmap

### Completed

- [x] Streamlit application foundation
- [x] SQLite persistence
- [x] User profile
- [x] Project management
- [x] Document handling foundation
- [x] Application tracker
- [x] Individual application removal
- [x] Multi-provider LLM abstraction
- [x] Global discovery foundation
- [x] Scholarship discovery
- [x] Master's discovery
- [x] Research discovery
- [x] Jobs and internships
- [x] Google Search integration
- [x] Serper fallback
- [x] OpenRouter web-search fallback
- [x] Current-opportunity filtering
- [x] Search diagnostics
- [x] Provider failover

### Next

- [ ] Faster discovery pipeline
- [ ] Better result relevance scoring
- [ ] Deep opportunity analysis on demand
- [ ] Stronger official-source verification
- [ ] Improved multilingual extraction
- [ ] Advanced profile-to-opportunity matching
- [ ] Tailored CV generation
- [ ] Application roadmap generation
- [ ] Research/professor matching
- [ ] Persistent user authentication and account isolation
- [ ] Production deployment
- [ ] PostgreSQL support

---

## 💡 Design Principles

### 1. Discover broadly

Don't restrict opportunity discovery to one website.

### 2. Verify carefully

Official sources should carry the highest trust.

### 3. Don't hallucinate

Missing information remains missing.

### 4. Separate discovery from intelligence

Finding a page and understanding a page are different tasks.

### 5. Keep the user in control

Opportune AI assists with research and preparation; the user makes the final application decisions and submissions.

### 6. Fail gracefully

One unavailable API should not bring down the entire discovery system.

### 7. Keep it lightweight

Prefer simple, maintainable components over unnecessary infrastructure.

---

## 📜 License

This project is currently a development / hackathon project.

License terms can be added before public production release.

---

## 👨‍💻 Project

**Opportune AI**

Personal Opportunity & Application Intelligence Agent

Repository:

https://github.com/Nomi-smith/opportune-ai
