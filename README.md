# SAHAYA

**Inclusive Emergency Decision Engine**

> *Before we send help, let's make sure it can actually help.*

SAHAYA is decision support for emergency coordinators. It turns a report into structured accessibility needs, checks a proposed resource against deterministic rules, presents evidence, and records the human decision. It does not autonomously dispatch help.

**AI understands → Rules verify → Humans decide.**

## Why SAHAYA

Traditional matching asks: **“Is this resource available?”**

SAHAYA asks: **“Is this resource compatible with this person?”**

```text
Emergency report
      ↓
AI extraction + clarification
      ↓
Human requirement review
      ↓
Versioned final case requirements
      ↓
Resource verification + per-capability freshness
      ↓
Person-specific review + group capacity check
      ↓
Resource-type applicability
      ↓
Deterministic evidence-based evaluation
      ↓
SAFE / UNKNOWN / BLOCKED / NOT APPLICABLE
      ↓
Human confirmation or documented manual override
      ↓
Audit timeline
```

## Product capabilities

- Written incident intake in Malayalam or English, plus Malayalam voice transcription.
- OpenAI-backed structured extraction with a safety fallback to manual review.
- Requirement Review/Edit gate: preserves the AI proposal, records coordinator edits separately, and versions the final requirement set used by the engine.
- One-at-a-time clarification for missing MVP-critical information.
- Explicit accessibility requirements for wheelchair access, step-free access, accessible transport, caregiver support, hearing support, and visual communication.
- Deterministic resource evaluation with evidence for every applicable requirement.
- A reusable WHY panel that shows the reviewed person requirement, exact resource capability, provenance, freshness, versions, and deterministic result for every check.
- Evidence-based comparison of two to four resources. SAHAYA compares evidence; it never ranks or selects a “best” resource.
- Accessibility capacity: total places, accessible places, and caregiver places are independently recorded. General availability never substitutes for a required accessible or caregiver space.
- Multi-person case support: each person has an independently reviewed requirement version; group decisions aggregate person × resource evidence with deterministic total, accessible, and caregiver capacity checks.
- Resource-type applicability: shelters are evaluated for shelter capabilities; vehicles are evaluated only when accessible transport is required.
- Resource verification workspace with YES / NO / UNKNOWN evidence, source, coordinator, timestamp, notes, freshness state, and a versioned resource record.
- Resource images use a vision model for observation-only evidence (for example, visible stairs or ramp). A coordinator must apply or edit every proposal before it changes a capability or evaluation.
- Conservative freshness rule: stale or never-verified positive capabilities are treated as **UNKNOWN** during evaluation; known negative capabilities remain evidence of a conflict.
- Human confirmation for SAFE resources only.
- Manual override for BLOCKED resources, requiring an acknowledgement and documented reason. The original rule decision remains **BLOCKED**.
- An audit timeline recording analysis, clarification, evaluations, confirmations, and override events.

Any requirement or resource-verification change after evaluation invalidates previous reports. In multi-person cases, a change to any person or group membership invalidates the group report. Re-evaluation records every current person requirement version and resource version before a coordinator can confirm an assignment.

## Decision states

| State | Meaning | Human action |
| --- | --- | --- |
| **SAFE** | Every applicable requirement is verified. | Confirm assignment. |
| **UNKNOWN** | One or more applicable capabilities are not verified. | Resolve missing information. |
| **BLOCKED** | A required capability conflicts with the resource. | Assignment blocked; request manual override if authorized. |
| **NOT APPLICABLE** | This resource type is not required for the current case. | No compatibility decision is made. |

## Technology

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS, Lucide icons.
- **Backend:** FastAPI, Pydantic, Python deterministic constraint engine.
- **AI:** OpenAI `gpt-4o` structured extraction and Whisper transcription.
- **Storage:** In-memory data for the MVP/demo. Supabase configuration is reserved for future persistence.

## Project structure

```text
SAHAYA/
├── .gitignore                         # excludes secrets, dependencies, caches, build output
├── README.md
├── backend/
│   ├── .env.example                   # safe template; local .env is never committed
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                    # FastAPI startup, CORS, health endpoint
│   │   ├── seed_data.py               # single-person and multi-person seeded demos
│   │   ├── ai/
│   │   │   ├── extractor.py           # OpenAI → IncidentExtraction → PersonProfile
│   │   │   ├── clarifier.py           # missing-information questions and answers
│   │   │   └── whisper.py             # audio transcription
│   │   ├── api/
│   │   │   ├── incidents.py           # single-person intake, evaluation, confirmation, audit
│   │   │   ├── people.py              # people, per-person review, group evaluation, capacity
│   │   │   ├── resources.py           # capability/capacity verification, provenance, freshness endpoints
│   │   │   ├── evaluations.py         # evaluation lookup endpoints
│   │   │   └── audio.py               # transcription endpoint
│   │   ├── engine/
│   │   │   └── constraint_engine.py   # SAFE / UNKNOWN / BLOCKED / NOT APPLICABLE rules
│   │   ├── models/
│   │   │   ├── incident.py            # incident, person, request schemas
│   │   │   ├── resource.py            # capabilities, accessibility capacity, provenance, freshness
│   │   │   ├── evaluation.py          # reports and verdict schemas
│   │   │   └── audit.py               # auditable event schemas
│   │   └── store/
│   │       └── memory.py              # temporary in-memory store
│   └── tests/
│       └── test_constraint_engine.py  # deterministic engine regression tests
└── frontend/
    ├── .env.example                   # frontend environment template
    ├── package.json
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx                # intake and guided demo entry
    │   │   ├── processing/page.tsx     # extraction progress
    │   │   ├── incident/[id]/          # summary, review, people, group evidence, resources, audit
    │   │   └── resource/[id]/verify/   # coordinator capability verification workspace
    │   ├── components/sahaya/          # evidence, cards, dialogs, timeline, status UI
    │   └── lib/api.ts                  # typed FastAPI client
    └── public/                         # static assets
```

## Run locally

### Backend

Requires Python 3.12+.

```bash
cd backend
python -m venv venv
```

Windows:

```bash
.\venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Create the local configuration file, install dependencies, and start the API:

```bash
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

### Frontend

Requires Node.js 20+.

```bash
cd frontend
npm install
npm run dev
```

The application runs at `http://localhost:3000`.

## Environment configuration

Set `OPENAI_API_KEY` in `backend/.env` for live AI extraction and transcription. Never commit this file; use [`backend/.env.example`](backend/.env.example) as the template.

If no valid OpenAI key is available, SAHAYA visibly flags the report for manual review rather than treating unknown accessibility needs as absent. The guided demo works without live AI.

## Testing

Run deterministic backend tests:

```bash
cd backend
pytest tests/ -v
```

Run the frontend quality check:

```bash
cd frontend
npm run lint
```

## Guided demo

Use **Try Guided Demo** on the landing page to load `demo-001`. It bypasses live AI and demonstrates the complete reliable path:

```text
Clarification
→ requirement review and confirmation
→ resource evaluation
→ evidence
→ human confirmation or manual override
→ audit log
```

The seeded resources deliberately show contrasting outcomes, including SAFE, UNKNOWN, BLOCKED, and—for cases without a transport requirement—NOT APPLICABLE vehicles.

`demo-group-001` is the multi-person scenario. It contains a wheelchair user who cannot use stairs and requires hearing support, a person requiring caregiver support, and a person without active accessibility requirements. Group evaluation aggregates all person-resource decisions and checks total, accessible, and caregiver capacity separately.

## MVP limitation

Cases are intentionally stored in memory for this prototype. Restarting the backend removes live cases, so create a new case after a restart or use `demo-001`. Replace `backend/app/store/memory.py` with persistent storage before real-world deployment.
