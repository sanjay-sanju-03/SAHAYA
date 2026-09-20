# SAHAYA

## Overview

**SAHAYA — Inclusive Emergency Decision Engine** is a decision-support system for emergency coordinators. It turns a Malayalam or English emergency report into reviewed accessibility requirements, verifies whether a shelter or vehicle can actually meet them, and preserves the evidence behind every decision.

SAHAYA does **not** autonomously dispatch people. It makes compatibility decisions explainable, identifies uncertainty, and records a coordinator's final confirmation or authorized override.

**Live demo:** [sahaya-sigma.vercel.app](https://sahaya-sigma.vercel.app/)

**Live API:** [sahaya-api.onrender.com/health](https://sahaya-api.onrender.com/health)

## Problem Statement

In an emergency, “a resource is available” does not mean “the resource is usable.” A shelter with stairs may be unusable for a wheelchair user; a vehicle may have seats but lack accessible transport; a route may be hazardous even when the destination is compatible.

Many workflows hide these mismatches, treat missing data as if it were safe, or provide no evidence for why a decision was made. This can exclude people with mobility, communication, hearing, visual, and caregiver-support needs.

## Solution

SAHAYA combines AI interpretation with deterministic rules and human accountability:

~~~text
Emergency report
      ↓
AI extraction + clarification
      ↓
Human requirement review
      ↓
Versioned requirements and verified resource evidence
      ↓
Deterministic compatibility checks
      ↓
SAFE / UNKNOWN / BLOCKED / NOT APPLICABLE
      ↓
Human confirmation or documented manual override
      ↓
Audit timeline
~~~

> Traditional matching asks: **“Is this resource available?”**

> SAHAYA asks: **“Is this resource compatible with this person?”**

## Features

- Malayalam and English incident intake, with AI-assisted structured extraction and a conservative manual-review fallback.
- Human requirement review/edit, ensuring that a coordinator confirms the authoritative accessibility profile.
- Deterministic evaluation of wheelchair access, step-free access, accessible transport, caregiver support, hearing support, and visual communication.
- Evidence-first SAFE, UNKNOWN, and BLOCKED outcomes with requirement, capability, provenance, freshness, and rule-result details.
- Accessibility-aware capacity checks: accessible and caregiver spaces never get substituted with general capacity.
- QR Resource Passports for field verification, resource freshness, versioning, and live capability/capacity updates.
- Operations map plus route/hazard evidence, kept separate from resource compatibility.
- Human confirmation for SAFE resources and documented manual override for BLOCKED resources, without changing the original rule verdict.
- Audit timeline and a read-only SAHAYA Assistant that explains evidence and changes without altering records.

## Tech Stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS, Lucide Icons, MapLibre.
- **Backend:** FastAPI, Python 3.12, Pydantic, deterministic constraint engine.
- **Database:** Supabase/PostgreSQL with versioned JSONB persistence.
- **APIs / Services:** OpenAI gpt-4o for structured extraction, image observations, and grounded assistant wording; OpenAI transcription for Malayalam/English voice intake.
- **Hosting / Deployment:** Vercel frontend, Render backend, Supabase database.
- **Other Tools:** GitHub, QR Resource Passport workflow, OpenStreetMap map tiles.

## Codex / OpenAI Usage

Codex and OpenAI were used as development collaborators during the hackathon:

- Planned the safety architecture around AI interpretation, deterministic verification, and human authority.
- Generated and refined FastAPI, Next.js, Pydantic, Supabase, testing, and deployment code.
- Diagnosed extraction fallback, CORS, deployment, dependency, and stale-evaluation issues.
- Improved UI/UX copy, evidence presentation, testing, documentation, and the guided demo flow.
- Integrated OpenAI APIs for structured incident extraction, accessibility-image observations, transcription, and the read-only evidence assistant.

AI never becomes the final dispatcher in SAHAYA. Deterministic rules validate compatibility, and a human coordinator remains responsible for confirmation or explicit override.

## Demo

### Live Demo

[Open SAHAYA](https://sahaya-sigma.vercel.app/)

Recommended judge flow:

1. Select **Try Guided Demo**.
2. Review and confirm the requirements.
3. Evaluate resources and compare SAFE, UNKNOWN, and BLOCKED evidence.
4. Open a SAFE resource, inspect WHY evidence, and record a human confirmation.
5. Open the audit timeline to see the accountable decision trail.

### Demo / Pitch Video

[Watch the SAHAYA demo / pitch video](https://drive.google.com/file/d/1XPAWHWl1wKnA6Ab6MJS56uqPr9TCaQeq/view?usp=sharing)

The video demonstrates the guided-demo flow and the distinction between AI interpretation, deterministic rules, evidence, and human confirmation.

## Screenshots

Before final submission, add three screenshots here:

1. **Emergency intake / guided demo** — Malayalam or English accessibility capture.
2. **Resource evaluation** — SAFE, UNKNOWN, and BLOCKED cards with evidence.
3. **WHY evidence or audit timeline** — provenance plus a human confirmation or manual override.

## Architecture and Safety Details

- Written incident intake in Malayalam or English, plus Malayalam voice transcription.
- OpenAI-backed structured extraction with a safety fallback to manual review.
- Requirement Review/Edit gate: preserves the AI proposal, records coordinator edits separately, and versions the final requirement set used by the engine.
- One-at-a-time clarification for missing MVP-critical information.
- Explicit accessibility requirements for wheelchair access, step-free access, accessible transport, caregiver support, hearing support, and visual communication.
- Deterministic resource evaluation with evidence for every applicable requirement.
- A reusable WHY panel that shows the reviewed person requirement, exact resource capability, provenance, freshness, versions, and deterministic result for every check.
- Evidence-based comparison of two to four resources. SAHAYA compares evidence; it never ranks or selects a “best” resource.
- Accessibility capacity: total places, accessible places, and caregiver places are independently recorded. General availability never substitutes for a required accessible or caregiver space.
- QR Resource Passport: a QR code identifies a resource and opens its live passport with current capacity, capability evidence, freshness, provenance, version, and the existing coordinator verification flow. The QR contains no duplicate capability data.
- Operations Map: a visual-only MapLibre + OpenStreetMap view of the recorded incident point and current resource verdicts. Markers link to existing evidence and Resource Passports; it does not calculate routes or dispatch decisions.
- Route/hazard rule foundation: versioned route observations are evaluated separately for route existence, known hazards, person-specific accessibility, and observation freshness. A route verdict never rewrites a resource compatibility verdict.
- SAHAYA Assistant: a compact, read-only evidence assistant beside resource evidence. It answers from the structured case, resource, capacity, route, version, provenance, and audit snapshot; it cannot assign, override, verify, or change records.
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
- **Storage:** Supabase persistence in production; deterministic in-memory fallback for local demos.

## Project structure

```text
SAHAYA/
├── .gitignore                         # excludes secrets, dependencies, caches, build output
├── README.md
├── render.yaml                         # Render backend Blueprint
├── supabase/
│   └── migrations/                     # production persistence schema
├── backend/
│   ├── .env.example                   # safe template; local .env is never committed
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                    # FastAPI startup, CORS, health endpoint
│   │   ├── seed_data.py               # single-person and multi-person seeded demos
│   │   ├── ai/
│   │   │   ├── extractor.py           # OpenAI → IncidentExtraction → PersonProfile
│   │   │   ├── clarifier.py           # missing-information questions and answers
│   │   │   ├── assistant.py            # read-only evidence-grounded assistant
│   │   │   └── whisper.py             # audio transcription
│   │   ├── api/
│   │   │   ├── incidents.py           # single-person intake, evaluation, confirmation, audit
│   │   │   ├── people.py              # people, per-person review, group evaluation, capacity
│   │   │   ├── resources.py           # capability/capacity verification, provenance, freshness endpoints
│   │   │   ├── evaluations.py         # evaluation lookup endpoints
│   │   │   ├── assistant.py            # read-only assistant query endpoint
│   │   │   └── audio.py               # transcription endpoint
│   │   ├── engine/
│   │   │   └── constraint_engine.py   # SAFE / UNKNOWN / BLOCKED / NOT APPLICABLE rules
│   │   ├── models/
│   │   │   ├── incident.py            # incident, person, request schemas
│   │   │   ├── resource.py            # capabilities, accessibility capacity, provenance, freshness
│   │   │   ├── evaluation.py          # reports and verdict schemas
│   │   │   ├── audit.py               # auditable event schemas
│   │   │   └── assistant.py           # assistant request/response schemas
│   │   └── store/
│   │       ├── memory.py              # repository API + local deterministic fallback
│   │       └── supabase_store.py      # production JSONB persistence adapter
│   └── tests/
│       └── test_constraint_engine.py  # deterministic engine regression tests
└── frontend/
    ├── .env.example                   # frontend environment template
    ├── vercel.json                     # Vercel Next.js configuration
    ├── package.json
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx                # intake and guided demo entry
    │   │   ├── processing/page.tsx     # extraction progress
    │   │   ├── incident/[id]/          # summary, review, map, people, group evidence, resources, audit
    │   │   ├── resource/[id]/           # live QR Resource Passport
    │   │   └── resource/[id]/verify/   # coordinator capability/capacity verification workspace
    │   ├── components/sahaya/          # evidence, cards, dialogs, timeline, status UI
    │   └── lib/api.ts                  # typed FastAPI client
    └── public/                         # static assets
```

## How to Run Locally

Clone the repository:

~~~bash
git clone https://github.com/sanjay-sanju-03/SAHAYA.git
cd SAHAYA
~~~

### Backend

Requires Python 3.12+.

```bash
cd backend
python -m venv .venv
```

Windows:

```bash
.\.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
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

For a QR code scanned from another device, set `NEXT_PUBLIC_APP_URL` in `frontend/.env.local` to the LAN-reachable address of the frontend, for example `http://192.168.1.10:3000`.

## Environment configuration

Set `OPENAI_API_KEY` in `backend/.env` for live AI extraction and transcription. Never commit this file; use [`backend/.env.example`](backend/.env.example) as the template.

If no valid OpenAI key is available, SAHAYA visibly flags the report for manual review rather than treating unknown accessibility needs as absent. The guided demo works without live AI.

For local development with the frontend available on both the laptop and a phone on the same network, use the matching origins in `backend/.env`:

```env
APP_ENV=development
CORS_ORIGINS=http://localhost:3000,http://192.168.1.43:3000
STORE_BACKEND=memory
```

Replace `192.168.1.43` with the laptop's current LAN address. This local configuration is separate from Render production variables.

## Deploy to Render + Vercel

SAHAYA is configured for a Render FastAPI backend and a Vercel Next.js frontend. Browsers call the frontend's same-origin `/api` path; Vercel proxies it to Render using the server-only `BACKEND_URL` value. Do not set `NEXT_PUBLIC_API_URL` in production.

### Supabase database

1. Create a Supabase project.
2. Open its SQL Editor and run the migration file at supabase/migrations/001_sahaya_state.sql.
3. Copy the project URL and its server-only **secret** key (starts with `sb_secret_`). Keep that key private; it belongs only in Render.

### Render backend

1. In Render, choose **New → Blueprint** and select this repository. It uses [`render.yaml`](render.yaml).
2. Add these secret environment variables:
   - `OPENAI_API_KEY`: your OpenAI key.
   - `CORS_ORIGINS`: the final Vercel origin, for example `https://your-app.vercel.app`.
   - `SUPABASE_URL` and `SUPABASE_SECRET_KEY`: required for persistence. Keep the secret key on Render only.
3. Deploy and verify `https://<your-render-service>.onrender.com/health` returns `status: ok`.

### Vercel frontend

1. Import the same GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Set these Production environment variables:
   - `BACKEND_URL`: `https://<your-render-service>.onrender.com` (no trailing slash).
   - `NEXT_PUBLIC_APP_URL`: the final Vercel URL; Resource Passport QR codes use it.
   - Leave `NEXT_PUBLIC_API_URL` unset so the same-origin proxy is used.
4. Deploy. If the Vercel URL differs from the value used above, update Render's `CORS_ORIGINS`.

### Production check

Open the deployed Vercel URL, run **Try Guided Demo**, and verify the flow `Vercel page → /api proxy → Render API`. Open Community Hall C, select **ASK SAHAYA**, and verify that a capacity answer includes its evidence/version footer.

> **Persistence:** Render uses `STORE_BACKEND=supabase` from the Blueprint. The backend loads and writes incidents, resources, people, evaluations, routes, and audit logs through Supabase. A restart no longer clears live state after the SQL migration has been applied.

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

## Production data behavior

Local development defaults to `STORE_BACKEND=memory`, so restarting a local API resets non-seeded cases. Render uses `STORE_BACKEND=supabase`; after the migration and Render secrets are configured, incidents, reviewed requirements, resource verification, evaluations, route evidence, and audit records survive restarts.

The browser never connects to Supabase directly. Keep `SUPABASE_SECRET_KEY` only in Render, never in Vercel or a client-side `NEXT_PUBLIC_*` variable.

## Additional Notes

- SAHAYA is a decision-support prototype, not an autonomous emergency-dispatch system.
- The guided demo uses synthetic records; no real emergency dispatch is initiated.
- AI outputs are proposals for review. A coordinator confirms requirements, verifies resources, and makes the final operational decision.
- If evidence is missing, stale, or contradictory, SAHAYA prefers **UNKNOWN** over an unsupported safety claim.
