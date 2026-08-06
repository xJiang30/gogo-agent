# Specialist Agents

Gogo Agent should expose one calm user-facing assistant. Specialist agents are
internal capabilities that the main TravelAdvisor can call as tools when a trip
board needs deeper judgment.

## User Experience Principle

The user should not see agent handoffs during ordinary planning. They should
feel that Gogo Agent understands pacing, budget, lodging, and food as one
coherent assistant.

Specialists should return compact structured advice. The main TravelAdvisor is
responsible for turning that advice into a proposal, question, or Trip Board
change.

## When To Use A Specialist

Use a specialist agent when the task needs judgment over a structured itinerary
and cannot be expressed as a simple deterministic function.

Use a normal function tool instead when the task is:

- checking required fields
- parsing or validating structured input
- calling one external API
- calculating a deterministic value

## Specialist Candidates

### Route Sense

Purpose: evaluate route shape and day pacing.

Input:

- trip destination and dates
- day itinerary nodes
- approximate locations
- known transport segments
- user pacing preference

Output:

- pacing score
- route concerns
- suggested node moves or removals
- plain-language rationale

### Budget Sense

Purpose: estimate whether the current plan fits the user's budget.

Input:

- budget range
- travelers
- destination
- lodging assumptions
- itinerary nodes and transport segments

Output:

- budget confidence
- likely expensive areas
- trade-off suggestions
- assumptions that need confirmation

### Stay Sense

Purpose: compare lodging area trade-offs.

Input:

- candidate stay areas
- itinerary anchors
- airport or station constraints
- preferred travel style

Output:

- recommended base area
- trade-offs by area
- commute concerns
- questions to ask before booking

### Food Sense

Purpose: suggest meal anchors without overloading the trip.

Input:

- destination
- itinerary timing
- food preferences
- reservation tolerance
- neighborhood context

Output:

- meal anchor suggestions
- reservation notes
- flexible backup ideas
- warnings when food plans make the day too tight

## Integration Shape

Specialists should be added as agents-as-tools after the Trip Board schema is
stable. The main TravelAdvisor owns user-visible messaging and calls specialists
only when their output can improve a proposal.

Target flow:

```text
TravelAdvisor
  -> function tools for deterministic checks
  -> specialist agents as tools for route, budget, stay, and food judgment
  -> proposal returned to application service
  -> user approval before Trip Board mutation
```

## Non-Goals

- Do not create visible specialist personas in the UI.
- Do not hand off ordinary planning conversations to specialists.
- Do not add specialist agents before their input schema is real.
- Do not let specialists mutate Trip Board state directly.
