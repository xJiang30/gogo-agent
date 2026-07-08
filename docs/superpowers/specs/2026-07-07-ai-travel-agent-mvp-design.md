# AI Travel Agent MVP Design

Date: 2026-07-07
Status: Approved design, pending written-spec review

## 1. Objective

Build a desktop-first web MVP for users in mainland China that provides an
end-to-end AI-native travel planning experience:

1. The user starts with an incomplete natural-language travel idea.
2. The system asks only necessary questions and returns exactly three editable
   plan directions.
3. The user opens one direction as a Trip Board with a time-based itinerary,
   map, transport segments, and hotels.
4. The user edits itinerary nodes directly or discusses a node with AI over
   multiple turns.
5. AI defaults to making recommendations. It changes formal trip state only
   after explicit approval, delegated execution, or opt-in automatic mode.
6. Discovery, comparison, planning, and editing happen in this product.
   Booking and navigation use deep links to external platforms in phase one.

The MVP does not require users to gather and paste information from other
platforms. External-link and screenshot imports are deferred, not foundational.

## 2. Scope

### 2.1 Phase-one capabilities

- Account sign-in and persistent trips
- Conversational trip intake
- Three structured candidate plans
- Editable Trip Board organized by day and time
- AMap POI search, map rendering, and route planning
- Place, meal, hotel, activity, arrival, and departure nodes
- Explicit transport segments between nodes
- Node-scoped multi-turn discussions
- Stay, mobility, and experience research specialists
- Proposal diff, accept, reject, version-conflict handling, and undo
- Invite-only email/password authentication with server-side sessions
- Budget and route validation
- Platform deep links for booking or navigation
- Agent traces, deterministic tests, and an initial evaluation dataset

### 2.2 Out of scope

- Real-time hotel inventory or ticket inventory
- In-product booking, payment, cancellation, or customer support
- Native mobile applications
- Browser extensions or share extensions
- Link, screenshot, PDF, or email parsing
- Price monitoring and scheduled alerts
- Autonomous agent swarm
- Unbounded long-term conversational memory
- Full collaboration or organization-level permissions
- User-facing automatic execution mode; phase one stores the policy field but
  exposes manual approval and explicit per-action delegation only

## 3. Product Principles

### 3.1 AI is an advisor by default

The user edits the Trip Board directly. AI may explain, research, compare, and
propose changes. Formal state changes require a `TripProposal` and user approval
unless the user explicitly delegates the action or enables an automatic mode.

### 3.2 The Trip database is the source of truth

The itinerary is structured application state, not a generated article or chat
transcript. PostgreSQL stores the only formal Trip state. LangGraph checkpoints
store only the temporary execution state of a particular agent run.

### 3.3 The map is a projection of the timeline

Trip nodes and transport segments drive both the timeline and map. Editing a
node changes the timeline first, then triggers recalculation of affected
transport segments and map geometry.

### 3.4 Every important recommendation is traceable

Recommendations record source references, retrieval timestamps, confidence,
risks, and missing information. The system does not silently turn uncertain
external data into confirmed facts.

## 4. System Architecture

```text
Next.js Web
  - Trip Board
  - Chat and node discussions
  - AMap visualization
  - Proposal diff and approval
  - Optimistic interaction state
          |
          | Generated OpenAPI client + SSE
          v
FastAPI Application
  - Authentication and authorization
  - Trip and discussion APIs
  - Proposal Executor
  - Agent streaming endpoints
  - Domain and provider services
          |
          +--> Travel Advisor
          |      +--> Plan Agent
          |      +--> Stay Agent
          |      +--> Mobility Agent
          |      +--> Experience Agent
          |      +--> deterministic validators
          |
          +--> LangGraph Manager
          |      - initial plan generation
          |      - complex research
          |      - cross-day replanning
          |
          +--> Provider adapters
                 - Qwen / DeepSeek
                 - AMap
                 - weather
                 - web search
                 - platform deep links
          |
          v
PostgreSQL + PostGIS
  - Formal Trip state
  - Discussions and messages
  - Proposals and decision log
  - Agent runs and LangGraph checkpoints
```

### 4.1 State ownership

- Next.js owns ephemeral interaction state only.
- FastAPI is the only public business API.
- PostgreSQL is the only source of formal Trip state.
- Agent code may read a versioned `TripSnapshot` but may not write Trip tables.
- LangGraph may persist run checkpoints but may not use them as formal Trip
  state.
- `ProposalExecutor` is the only path from AI output to formal state changes.

## 5. Controlled Multi-Agent Design

The MVP uses a manager pattern, not free-form agent collaboration.

### 5.1 User-visible agent

`TravelAdvisor` is the only identity visible to the user. It understands intent,
asks clarifying questions, chooses capabilities, explains trade-offs, and
maintains conversational continuity.

### 5.2 Specialist agents

- `PlanAgent`: creates three coherent plan directions from incomplete needs.
- `StayAgent`: researches areas and accommodation candidates, commute impact,
  flexibility, and reference pricing.
- `MobilityAgent`: compares transport categories, route duration, transfers,
  and mode-specific risks.
- `ExperienceAgent`: researches POIs, food, activities, alternatives, and local
  fit.

Specialists:

- Receive an explicit `ResearchBrief` and immutable `TripSnapshot`.
- Return a strict `ResearchResult` schema.
- Do not interact directly with the user.
- Do not modify formal Trip state.
- Do not communicate with one another.
- Return no more than three user-facing candidates per request.

### 5.3 Deterministic services

Budget calculation, route validation, opening-hour checks, conflict detection,
proposal execution, and version checks are ordinary Python services. They are
not agents.

### 5.4 LangGraph usage

Use LangGraph for:

- Initial plan generation that queries specialists in parallel
- Complex domain research that needs multiple tool rounds
- Cross-day replanning
- Durable pause/resume around complex runs

Do not use LangGraph for:

- Basic Trip CRUD
- Simple node questions
- Direct manual edits
- Map rendering
- Every conversational turn

## 6. Conversation and Agent Flow

### 6.1 Initial planning

```text
User idea
  -> TravelAdvisor extracts known facts and material gaps
  -> Ask only blocking questions
  -> LangGraph invokes relevant specialists in parallel
  -> Deterministic budget and route validation
  -> PlanAgent produces exactly three plan directions
  -> User chooses and edits a direction
  -> Create formal Trip only after confirmation
```

### 6.2 Node-scoped discussion

Each itinerary node may have one or more `NodeDiscussion` threads. Context
contains:

- Discussion summary and recent messages
- Current node and adjacent nodes
- Active Trip constraints and preferences
- Pending proposals
- Formal Trip version

The interaction escalates by complexity:

```text
L1 explanation          -> direct model response
L2 factual research     -> dynamic provider tool calls
L3 local replacement    -> node-scoped TripProposal
L4 cross-day impact     -> LangGraph replanning workflow
```

### 6.3 Context management

Do not send the complete Trip and entire chat history on every turn. Build
context from structured Trip data, a rolling discussion summary, recent
messages, unresolved proposals, and only the relevant temporal neighborhood.

## 7. Proposal Protocol

Agent outputs are limited to:

- `Answer`: explanation without a state change
- `RecommendationSet`: exactly three candidates for discussion or selection
- `TripProposal`: a formal, reviewable change request

```python
class TripProposal(BaseModel):
    id: UUID
    trip_id: UUID
    base_version: int
    scope: Literal["node", "day", "trip"]
    title: str
    summary: str
    reasons: list[str]
    warnings: list[str]
    operations: list[TripOperation]
    impact: ProposalImpact
    evidence: list[Evidence]
    status: Literal[
        "draft", "pending", "accepted", "rejected", "expired", "conflicted"
    ]
```

Allowed operations are explicit commands:

- `ReplaceNode`
- `InsertNode`
- `RemoveNode`
- `MoveNode`
- `UpdateNode`
- `ReplaceTransportSegment`
- `UpdateHotelStay`
- `ReorderDay`

Arbitrary model-generated database updates are prohibited.

### 7.1 Approval and conflict handling

`base_version` must match the current Trip version. If it does not:

1. Check whether any targeted entity changed.
2. Revalidate if the changes are unrelated.
3. Mark the proposal `conflicted` if targeted entities changed.
4. Ask the agent to regenerate against the latest snapshot.

Accepted operations execute in one database transaction, increment the Trip
version, record a `DecisionLog`, and store inverse operations for undo.

## 8. Domain Model

### 8.1 Primary entities

```text
User
Trip
TripConstraint
ItineraryDay
TripNode
TransportSegment
PlaceRef
BookingRecord
NodeDiscussion
DiscussionMessage
TripProposal
DecisionLog
AgentRun
AgentEvidence
```

### 8.2 Trip nodes

`TripNode` types are place, meal, hotel, activity, arrival, and departure. Each
node contains start/end time, timezone, ordering position, place reference,
booking reference, selection status, data source, and entity version.

### 8.3 Transport segments

A `TransportSegment` explicitly connects two nodes. It contains mode,
departure/arrival times, duration, distance, route geometry, provider route
reference, and estimated/selected/booked status.

Replacing a node invalidates and recalculates only the incoming and outgoing
segments unless a validator finds a broader impact.

### 8.4 Places and coordinates

Phase one stores the AMap POI identifier plus a timestamped name, address,
opening-hours snapshot, and GCJ-02 coordinates. PostGIS supports proximity
filters and clustering. AMap remains authoritative for route duration and route
geometry.

## 9. Frontend State and Interaction

### 9.1 Server state

TanStack Query manages trips, days, nodes, segments, discussions, proposals,
and agent runs.

### 9.2 Ephemeral UI state

Zustand manages the selected day/node, open drawer, map viewport, and temporary
drag state. It does not contain a second complete copy of the Trip.

### 9.3 Optimistic edits

Manual edits update the timeline immediately, submit a versioned mutation,
then either commit or roll back. A successful node mutation emits an event,
marks adjacent routes as recalculating, and replaces their geometry when the
backend result arrives.

## 10. Technology Stack

### 10.1 Web

- Next.js App Router, React, TypeScript
- Tailwind CSS and shadcn/ui
- TanStack Query and narrowly scoped Zustand
- dnd-kit
- AMap JavaScript API 2.0
- Zod
- Vitest and Playwright

### 10.2 Backend

- Python 3.12 or later
- FastAPI and Pydantic v2
- SQLAlchemy 2 async, Alembic, psycopg 3
- PostgreSQL 16 and PostGIS
- LangGraph 1.x with PostgreSQL checkpointing
- HTTPX
- pytest and Testcontainers

### 10.3 Models and providers

- Primary model: Qwen through Alibaba Cloud Model Studio's OpenAI-compatible API
- Secondary provider: DeepSeek
- Application-owned `ModelProvider` abstraction
- AMap Web Service for server-side POI and route data
- AMap JavaScript API for client rendering
- Provider responses include source, fetch time, confidence, and missing fields

Do not combine LangGraph and Qwen-Agent as overlapping orchestration runtimes in
phase one.

### 10.4 Deployment

- Containerized Next.js standalone process
- Containerized FastAPI process
- LangGraph runs inside the FastAPI process in phase one and persists
  checkpoints to PostgreSQL
- Alibaba Cloud ECS or container service
- Alibaba Cloud RDS PostgreSQL and OSS
- Nginx or Caddy reverse proxy
- Redis and a durable queue are deferred until scheduled or detached tasks are
  required

An independent Python worker is not part of the phase-one topology. Introduce a
worker and durable queue only when measured request duration or detached jobs
require them; that change does not alter the agent or proposal contracts.

## 11. API Surface

```text
POST  /v1/conversations
POST  /v1/conversations/{id}/messages

POST  /v1/trips
GET   /v1/trips/{id}
PATCH /v1/trips/{id}
PATCH /v1/trips/{id}/nodes/{node_id}

POST  /v1/trips/{id}/nodes/{node_id}/discussions
POST  /v1/trips/{id}/plan-runs
GET   /v1/runs/{run_id}/events

GET   /v1/proposals/{id}
POST  /v1/proposals/{id}/accept
POST  /v1/proposals/{id}/reject
POST  /v1/decisions/{id}/undo
```

Streaming uses Server-Sent Events. FastAPI OpenAPI generates the TypeScript API
client consumed by Next.js.

## 12. Error Handling

- `ProviderTransientError`: bounded retry with exponential backoff
- `ProviderDataMissing`: return missing fields; do not ask the model to invent
  them
- `ProposalConflict`: revalidate or regenerate against the latest Trip version
- `ConstraintViolation`: reject execution and return the violated constraint
- `AgentOutputInvalid`: one schema-repair attempt, then fail safely
- `RouteUnavailable`: retain nodes and mark the segment unresolved
- `UnauthorizedTripAccess`: reject before constructing agent context

Every external call has timeout, cancellation, trace ID, and redacted logs.

## 13. Testing and Evaluation

### 13.1 Deterministic tests

- Domain rules and `ProposalExecutor` unit tests
- Repository, PostGIS, and transaction integration tests
- Provider contract tests using recorded sanitized fixtures
- Frontend reducer and component tests
- Playwright tests for the primary user journey

### 13.2 Agent evaluations

The initial regression dataset contains 50-100 cases covering:

- Incomplete request to exactly three viable plans
- Excluding places already present in the itinerary
- Accommodation advice that accounts for daily routes
- Transport category selection before specific service selection
- Allowed proposal operations only
- Stale Trip version conflict handling
- Honest handling of unavailable provider data
- Hard constraint preservation

Prompt, model, and tool-description changes must run the evaluation suite.

## 14. Two-Person Parallel Development Strategy

The team works contract-first. Neither frontend nor backend waits for the other
to complete an entire layer.

### 14.1 Shared contracts before parallel work

The first two days produce:

- Pydantic domain schemas
- OpenAPI endpoint contracts
- SSE event schema
- Proposal operation schemas
- Representative JSON fixtures for Trip, plan candidates, discussions, and
  proposals
- An architecture decision record for state ownership

The OpenAPI document and fixtures are versioned artifacts. Breaking contract
changes require both developers' review.

### 14.2 Development lanes

```text
Developer A: Product/Web lane
  - Next.js shell and authentication UI
  - Trip Board timeline
  - AMap rendering and interaction
  - Discussion drawer
  - Proposal diff and approval UI
  - Playwright user journeys

Developer B: Python/Core lane
  - FastAPI and authentication backend
  - Domain model and migrations
  - Trip/Proposal/Discussion use cases
  - AMap and model provider adapters
  - LangGraph and specialist agents
  - pytest and agent evals
```

Both developers review the other's boundary code. Ownership is not exclusive.

### 14.3 Frontend independence

The web lane develops against:

- Generated TypeScript API types
- Mock Service Worker handlers generated from shared fixtures
- A fake SSE event source with deterministic playback
- A map adapter with fake and AMap implementations

The UI can therefore implement loading, success, conflict, partial data, tool
progress, and failure states before the real endpoint exists.

### 14.4 Backend independence

The Python lane develops against:

- API contract tests
- Fake model, AMap, weather, and search providers
- Golden TripSnapshot and TripProposal fixtures
- A CLI or pytest harness for agent runs

Agent and domain behavior can be tested without the browser.

### 14.5 Vertical integration cadence

Integrate one thin vertical slice every two to three days:

1. Replace one mock endpoint with the real endpoint.
2. Run generated-client type checks.
3. Run backend contract tests.
4. Run the relevant Playwright path.
5. Record contract or behavior changes immediately.

Do not postpone integration until the end of a week.

### 14.6 Parallel six-week schedule

#### Week 1: foundation

Shared:
- Repository, Compose, contracts, fixtures, CI, and architecture tests

Web lane:
- Next.js shell, generated client, MSW, Trip Board skeleton

Python lane:
- FastAPI, database, migrations, auth, Trip CRUD

Integration milestone:
- Create and load a real persisted Trip in the Trip Board

#### Week 2: structured itinerary

Web lane:
- Timeline editing, node drawer, optimistic mutation, undo UI

Python lane:
- Node/segment/domain services, versioning, DecisionLog, ProposalExecutor

Integration milestone:
- Manual node edit with conflict detection and undo

#### Week 3: planning conversation

Web lane:
- Chat streaming UI, three-plan selection, agent progress states

Python lane:
- TravelAdvisor, PlanAgent, SSE, fake then real model provider

Integration milestone:
- Natural-language request creates three selectable plan directions

#### Week 4: maps and discussions

Web lane:
- AMap markers, polylines, synchronized selection, route recalculation state

Python lane:
- AMap POI/route adapters, NodeDiscussion, context builder

Integration milestone:
- Node replacement updates adjacent routes and map geometry

#### Week 5: specialists and proposals

Web lane:
- Three-candidate UI, proposal diff, accept/reject/conflict flows

Python lane:
- Stay/Mobility/Experience agents, LangGraph manager, validators

Integration milestone:
- Node discussion delegates research and produces an executable proposal

#### Week 6: reliability and release

Web lane:
- Responsive fallback, accessibility, error and recovery polish

Python lane:
- Eval dataset, tracing, timeouts, retries, deployment hardening

Shared:
- Playwright suite, performance pass, deployment, real-user testing

Integration milestone:
- Deployable MVP and release checklist

### 14.7 Coordination rules

- Daily 20-minute contract and blocker sync
- One developer may change a shared schema; both approve it
- API client generation and schema drift checks run in CI
- Every incomplete backend endpoint has an MSW fixture
- Every provider has a deterministic fake
- Feature work is complete only after one cross-boundary integration test

## 15. Proposed Repository Layout

```text
gogo-agent/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── trip-board/
│   │   │   ├── timeline/
│   │   │   ├── map/
│   │   │   ├── discussion/
│   │   │   └── proposals/
│   │   ├── lib/api-generated/
│   │   └── mocks/
│   └── api/
│       ├── app/
│       │   ├── domain/
│       │   ├── application/
│       │   ├── api/
│       │   ├── agents/
│       │   ├── providers/
│       │   └── infrastructure/
│       ├── migrations/
│       └── tests/
├── contracts/
│   ├── fixtures/
│   └── openapi/
├── evals/
│   ├── datasets/
│   ├── scorers/
│   └── regression/
├── infra/
│   ├── docker/
│   └── compose.yaml
└── docs/
```

## 16. Success Criteria

The MVP is ready for invited users when:

- A user can create a Trip from an incomplete request and choose one of three
  plans.
- Every Trip Board node is editable and map-linked.
- A node discussion can return three non-duplicate, evidence-backed options.
- An accepted proposal updates only allowed entities and can be undone.
- Route changes are visible and unresolved routes are explicit.
- Hard constraints survive tested planning and replanning scenarios.
- Core agent evaluations meet agreed thresholds with no critical regression.
- The primary Playwright journey passes against the deployed environment.
