# Customer-Facing Resolution Agent ✈️

AI-powered airline disruption support agent built for the **AIONOS Assignment 3**.

The system verifies customers using **PNR + email**, understands requests using **Gemini**, evaluates policies using **deterministic Python**, executes only approved actions, and generates customer-facing responses through a **LangGraph** workflow.

> **Core principle:** The LLM handles language understanding and response generation. Policy decisions are deterministic and source-grounded.

---

## Features

- PNR + email customer verification
- Complete customer and booking retrieval
- Gemini-based structured request understanding
- Deterministic policy engine
- Multi-intent and multi-turn conversations
- Simulated rebooking, refund, meal voucher, lounge and hotel actions
- Policy-based escalation
- Emotion-aware customer responses
- React customer-facing chat interface
- Docker Compose support
- Automated pytest test suite

---

## Architecture

```text
                    React UI
                       │
                       ▼
                    FastAPI
                       │
                       ▼
             PNR + Email Verification
                       │
                       ▼
          Customer + Booking Context
                       │
                       ▼
                   LangGraph
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
 Understand       Policy          Action /
 Request          Evaluation      Escalation
 (Gemini)         (Python)        (Python)
        │              │              │
        └──────────────┼──────────────┘
                       ▼
               Generate Response
                   (Gemini)
                       │
                       ▼
                  React Chat

## Agent Workflow

```text
START
  ↓
understand_request
  ↓
policy_evaluation
  ↓
action_or_escalation
  ↓
generate_response
  ↓
END
```

**Important:** The LLM does not decide whether an action is allowed. The **deterministic policy engine is the authority for all policy decisions**.

## Tech Stack

| Layer      | Technologies                 |
| ---------- | ---------------------------- |
| Frontend   | React, Vite                  |
| Backend    | Python, FastAPI              |
| AI / Agent | Gemini, LangChain, LangGraph |
| Validation | Pydantic                     |
| Testing    | pytest                       |
| Deployment | Docker, Docker Compose       |

## Project Structure

```text
aionos-resolution-agent/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agent/
│   │   ├── services/
│   │   ├── models/
│   │   └── data/
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
│
├── docs/
├── .github/
├── docker-compose.yml
├── README.md
├── .gitignore
└── LICENSE
```

## API

| Method | Endpoint              | Purpose                   |
| ------ | --------------------- | ------------------------- |
| `GET`  | `/health`             | Health check              |
| `POST` | `/api/auth/verify`    | Verify PNR + email        |
| `GET`  | `/api/bookings/{pnr}` | Retrieve verified booking |
| `POST` | `/api/chat`           | Process customer message  |

### Interactive API Documentation

Once the backend is running, interactive Swagger documentation is available at:

```text
http://localhost:8000/docs
```

## Local Setup

### 1. Backend

Navigate to the backend directory:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

#### Windows

Activate the virtual environment:

```bash
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `backend/.env` file:

```env
GEMINI_API_KEY=your_api_key
```

St
