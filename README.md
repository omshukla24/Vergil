<p align="center">
  <img src="https://img.shields.io/badge/Auth0-EB5424?style=for-the-badge&logo=auth0&logoColor=white" alt="Auth0" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
</p>

<h1 align="center">⚔️ Vergil</h1>
<h3 align="center">Agentic Auth Middleware — Confidence-Gated Authorization for Autonomous AI</h3>

<p align="center">
  <em>An open-source Python SDK & FastAPI State Engine that secures autonomous AI agents using Auth0 Step-Up Authentication, Confidence-Gated Authorization, and Quorum-as-a-Service.</em>
</p>

---

## 🧠 The Problem

Autonomous AI agents are increasingly deployed in high-stakes environments—SOC automation, financial trading, infrastructure management—where a single wrong action can be catastrophic. Current authorization models are binary: an agent either **has** permission or **doesn't**. There's no mechanism to say:

> *"You can do this automatically if you're confident, but if you're uncertain, ask a human."*

## 💡 The Solution

**Vergil** introduces a novel authorization paradigm:

| Feature | Description |
|---|---|
| **Confidence-Gated Authorization** | Actions are auto-approved when AI confidence exceeds a tunable threshold. Below that threshold, the system triggers Auth0 Step-Up Authentication to bring a human into the loop. |
| **Quorum-as-a-Service** | For truly critical operations, Vergil requires N-of-M human approvals via parallel Auth0 Step-Up flows, with Redis-backed atomic state tracking. |
| **RS256 Token Verification** | All inbound API calls are cryptographically verified against Auth0's JWKS public keys using RS256 — no shared secrets, no forgery. |

---

## 🏗️ Architecture

```
┌──────────────────────┐        ┌──────────────────────┐
│   AI Agent / SOC     │        │    Auth0 Tenant       │
│   (demo_app/)        │        │  ┌────────────────┐   │
│                      │        │  │ Universal Login │   │
│  Uses VergilClient    │        │  │  (Step-Up MFA)  │   │
│  (vergil_sdk/)       │        │  └───────┬────────┘   │
└──────────┬───────────┘        └──────────┼────────────┘
           │ HTTP                          │ Redirect
           ▼                               ▼
┌──────────────────────────────────────────────────────┐
│              Vergil State Engine                      │
│              (vergil_engine/)                         │
│                                                       │
│  POST /api/v1/actions/execute                         │
│    → confidence ≥ threshold? AUTO-APPROVE             │
│    → confidence <  threshold? STEP-UP AUTH URL        │
│                                                       │
│  POST /api/v1/actions/quorum                          │
│    → Generate N trustee Step-Up URLs                  │
│    → Track M-of-N approvals atomically                │
│                                                       │
│  GET  /api/v1/actions/{id}/status                     │
│    → PENDING | APPROVED | EXECUTABLE | REJECTED       │
│                                                       │
│  GET  /api/v1/auth0/callback                          │
│    → Process Auth0 redirect, update state             │
├───────────────────────────────────────────────────────┤
│              Redis (State Store)                       │
│  • Optimistic concurrency via WATCH/MULTI             │
│  • TTL-based expiry (1hr)                             │
│  • Atomic quorum counter increments                   │
└───────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
vergil-project/
├── vergil_engine/          # FastAPI State Engine (Control Plane)
│   ├── main.py             # API endpoints & lifespan management
│   ├── auth0_utils.py      # RS256 JWT verification & Step-Up URL generation
│   ├── config.py           # Pydantic Settings (env-driven configuration)
│   ├── models.py           # Typed request/response DTOs
│   └── redis_store.py      # Async Redis with optimistic concurrency
│
├── vergil_sdk/             # Python SDK for AI agents
│   ├── client.py           # VergilClient with async polling & backoff
│   └── exceptions.py       # Typed exceptions (StepUpAuthRequired, etc.)
│
├── dashboard/              # Command Center Web UI
│   ├── index.html          # Interactive dashboard
│   ├── dashboard.css       # Premium dark theme
│   └── dashboard.js        # Real-time event feed & state machine
│
├── demo_app/               # SOC Agent simulation
│   └── soc_agent.py        # 3-scenario demo (auto → step-up → quorum)
│
├── tests/                  # pytest + httpx ASGI test suite
│   └── test_engine.py      # Full-stack endpoint & state tests
│
├── .env                    # Auth0 tenant configuration
├── requirements.txt        # Pinned dependencies
└── pytest.ini              # Async test configuration
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Redis** running on `localhost:6379`
- An **Auth0 tenant** with an API configured

### 1. Install Dependencies

```bash
cd vergil-project
pip install -r requirements.txt
```

### 2. Configure Auth0

Edit `.env` with your Auth0 credentials:

```env
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret
AUTH0_AUDIENCE=https://your-api-identifier
REDIS_URL=redis://localhost:6379
```

### 3. Start the State Engine

```bash
uvicorn vergil_engine.main:app --reload
```

The engine starts at `http://localhost:8000` with interactive docs at `/docs`.

### 4. Run the SOC Agent Demo

```bash
python -m demo_app.soc_agent
```

Watch the agent process three escalating threat scenarios in real-time.

### 5. Run Tests

```bash
pytest tests/ -v
```

---

## 🔐 How It Works

### Scenario 1: Low Risk → Auto-Approve
```python
async with VergilClient() as vergil:
    approved = await vergil.execute(
        action="Block IP 192.168.1.100",
        confidence=0.95,  # High confidence
        threshold=0.90,   # Meets threshold
        user_id="soc_admin@company.com"
    )
    # → Instantly returns True, no human needed
```

### Scenario 2: High Risk → Step-Up Auth
```python
    approved = await vergil.execute(
        action="Isolate engineering VLAN",
        confidence=0.75,  # Below threshold
        threshold=0.90,
        user_id="soc_admin@company.com"
    )
    # → Emits Auth0 Step-Up URL, polls until human approves
```

### Scenario 3: Critical → Multi-Party Quorum
```python
    approved = await vergil.require_quorum(
        action="Wipe DB drives and failover",
        trustees=["ciso@co.com", "vp_eng@co.com", "oncall@co.com"],
        required=2  # Need 2-of-3 approvals
    )
    # → Generates unique Auth0 URLs per trustee
    # → Atomically tracks approvals via Redis WATCH
```

---

## 🧪 Testing

The test suite uses `pytest-asyncio` and `httpx.ASGITransport` to test against the live ASGI application without spinning up a server:

| Test | What It Validates |
|---|---|
| `test_execute_auto_approve` | High-confidence actions bypass auth and immediately transition to `EXECUTABLE` |
| `test_execute_requires_step_up` | Low-confidence actions return `PENDING` with a valid Auth0 `/authorize` URL |
| `test_quorum_flow` | Full quorum lifecycle: initiation → partial approval → quorum met → `EXECUTABLE` |

All tests use a `MockRedisStore` injected via `monkeypatch` for isolated, deterministic testing.

---

## 🔧 Technical Highlights

- **RS256 JWKS Verification**: Tokens are verified against Auth0's rotatable public keys — no symmetric secrets stored server-side
- **Optimistic Concurrency**: Redis `WATCH`/`MULTI` transactions prevent race conditions when multiple trustees approve simultaneously
- **Exponential Backoff Polling**: The SDK uses capped exponential backoff (2s → 5s) to poll for approval without hammering the engine
- **Typed Everything**: Pydantic v2 models for all DTOs, Pydantic Settings for config, Python type hints throughout
- **Zero State Leakage**: All Redis keys expire after 1 hour — no stale authorization state accumulates

---

## 📜 License

MIT

---

<p align="center">
  Built for the <strong>Auth0 AI Security Hackathon</strong> by <a href="https://github.com/omshukla24">@omshukla24</a>
</p>

---

### 🧪 Reviewer Testing Credentials
To properly test the Step-Up Auth mechanism, when prompted by the Auth0 Universal Login, please use:
- **Email:** `reviewer@company.com`
- **Password:** `Vergil@storm1`
