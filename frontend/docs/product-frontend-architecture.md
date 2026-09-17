# Product Frontend Architecture

The formal frontend is not a static copy of `demo/`, and it should not keep
mock trip data inside page components. `demo/` remains the interaction reference;
`frontend/` is the product implementation.

## Product Direction

Gogo Agent has two primary product surfaces:

- Project Inbox: a lightweight planning workspace with multiple trip projects,
  ongoing intake conversations, and entry points into created Trip Boards.
- Trip Board: a route-first planning workspace inspired by the demo, with a
  route canvas, day timeline, node inspector, and assistant panel.

The demo's Trip Board interaction is the stronger reference. The demo's entry
page should be redesigned for the product frontend.

## Core Principles

- Components consume typed data; they do not own hard-coded trip fixtures.
- Mock data lives in `mock.ts` files and is accessed through service adapters.
- The same UI should work with mock services today and backend API services
  later.
- Chat is embedded as contextual assistance, not as the main application.
- Trip Board state is mutated by application services, never directly by the
  assistant UI.

## Suggested Folder Structure

```text
frontend/src/
  app/
    App.tsx
    routes.tsx
  features/
    projects/
      model.ts
      mock.ts
      service.ts
      ProjectInboxPage.tsx
      components/
        ProjectList.tsx
        ProjectHome.tsx
    intake/
      model.ts
      mock.ts
      service.ts
      IntakePage.tsx
      components/
    trip-board/
      model.ts
      mock.ts
      service.ts
      TripBoardPage.tsx
      components/
        BoardHeader.tsx
        RouteCanvas.tsx
        DayTimeline.tsx
        NodeInspector.tsx
    assistant/
      model.ts
      mock.ts
      service.ts
      AssistantPanel.tsx
      chatkitAdapter.ts
  shared/
    api/
    ui/
```

This structure keeps domain data, service boundaries, and UI components close
to the feature they belong to.

## Project Inbox And Intake

The entry surface should feel closer to Codex's project/thread list than a
one-off prompt box. Users may have several trip projects, and each project can
be in a different planning state.

Recommended layout:

```text
left: project list
right: selected project home
```

Project model:

```ts
type PlanningProject = {
  id: string
  title: string
  status: 'collecting' | 'ready_to_start' | 'board_created'
  intake: IntakeFields
  chatSessionId: string
  tripBoardId?: string
  updatedAt: string
}
```

When a project is still collecting information, the project home keeps the
conversation visible:

Expected flow:

```text
user message
  -> intake service extracts or updates fields
  -> missing fields are shown as compact chips
  -> the assistant asks only for what is missing
  -> Start Plan becomes available when ready
  -> user enters Trip Board
```

Collecting project home should include:

- natural-language input
- chat history
- collected field summary
- missing field state
- `Start Plan` action

When a Trip Board has already been created, the project home should remove the
large conversation composer and show a compact project summary instead:

- destination, dates, travelers, budget, and preferences
- Trip Board status
- primary `Enter Trip Board` action
- optional secondary access to history or follow-up

This keeps completed projects light while letting unfinished projects continue
exactly where the user left off.

The entry surface should not include:

- three generated plan cards
- forced template selection
- a full-screen chat-only layout

## Trip Board Page

The Trip Board page should inherit the demo's route-board feel while improving
layout polish and density.

Recommended desktop layout:

```text
top: board header, day selector, key actions
center-left: route canvas with connected nodes
bottom or left: day timeline
right: collapsible assistant panel
```

Recommended mobile layout:

```text
top: board header and day selector
main: route canvas
below: day timeline and node inspector
bottom sheet: assistant panel
```

The route canvas should keep the demo's visual language: spatial nodes,
connection lines, day context, and immediate node selection. It should avoid a
large empty map area and avoid redundant summary blocks under the canvas.

## Node Interaction

Nodes should be directly clickable. Selecting a node opens the node inspector
without requiring a separate "view" button.

Node inspector responsibilities:

- show time, title, location, duration, and notes
- surface booking or confirmation state
- show relevant proposal actions
- provide a contextual assistant entry point

## Assistant And ChatKit

ChatKit belongs inside `features/assistant/AssistantPanel`.

Assistant responsibilities:

- intake follow-up
- day or node-level questions
- proposal confirmation
- post-apply summaries

Assistant non-goals:

- render Trip Board
- own map layout
- mutate itinerary state directly
- choose model routing

The current implementation can render an internal mock assistant panel. Later,
`chatkitAdapter.ts` can swap the panel body to ChatKit while preserving the same
feature boundary.

ChatKit appears in two places:

- Project Inbox for projects in `collecting` or `ready_to_start` states.
- Trip Board assistant panel for day or node context.

For `board_created` projects in the inbox, the default surface should be a
summary plus `Enter Trip Board`, not a large chat composer.

## Data Flow

Initial development should use mock services:

```text
mock.ts -> service.ts -> page state -> components
```

Backend integration should keep the same page/component boundary:

```text
backend API -> service.ts -> page state -> components
```

This lets us build realistic frontend UX without hard-coding data into React
components.

## First Implementation Slice

The first slice should build:

- feature folder structure
- typed project model
- typed intake and Trip Board models
- mock-backed services
- redesigned Project Inbox with project list and status-aware project home
- demo-inspired Trip Board page
- assistant panel shell with mock proposal confirmation

This slice should not install ChatKit yet. ChatKit should be added after the
backend custom server and session endpoint are in place.
