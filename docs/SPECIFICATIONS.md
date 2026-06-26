# Prompt Pipeline — Specifications

## Chosen Task: Trip Day-Planner

> **Input:** A loose natural-language request (city, days, interests, budget)  
> **Output:** Structured constraints JSON + a feasible day-by-day itinerary

Chosen because it naturally decomposes into four clean stages (parse → reason → plan → format) and produces a satisfying, human-readable final output.

---

## Stage Definitions

### Stage 1 · UNDERSTAND
**Technique:** `role` + `structured_output`  
**Job:** Parse the raw user request into structured travel constraints.

**Input:** Raw text string (user's trip request)

**Output JSON schema:**
```json
{
  "city": "string",
  "days": "integer",
  "interests": ["string"],
  "budget_level": "budget | mid | luxury",
  "travel_style": "slow | moderate | packed",
  "dietary_restrictions": ["string"] | [],
  "mobility_notes": "string | null",
  "errors": ["string"] | []
}
```

**Error handling:** If any required field (`city`, `days`) is missing or unparseable, populate `errors[]` and set safe defaults. Do not throw. Downstream stages read `errors[]` and skip gracefully if critical fields are missing.

---

### Stage 2 · REASON
**Technique:** `chain_of_thought`  
**Job:** Think step-by-step about what is feasible given the constraints, and produce a day-by-day activity skeleton with reasoning.

**Input:** Stage 1 JSON

**Output JSON schema:**
```json
{
  "feasibility_notes": "string",
  "reasoning": "string (step-by-step thought process)",
  "days": [
    {
      "day": "integer",
      "theme": "string",
      "morning": "string (activity description)",
      "afternoon": "string",
      "evening": "string",
      "estimated_cost": "string (e.g. ~$40)"
    }
  ],
  "warnings": ["string"] | []
}
```

**Chain-of-thought contract:** The `reasoning` field must contain visible step-by-step thinking: e.g. "Day 1: The user arrives — don't over-schedule. They like history, so... Day 2: Budget is mid, so...". This reasoning must appear *before* the final `days` array is committed to.

---

### Stage 3 · PRODUCE
**Technique:** `goal_oriented` + constraints  
**Job:** Take the structured day plan and write a polished, human-readable itinerary.

**Input:** Stage 1 JSON + Stage 2 JSON

**Output JSON schema:**
```json
{
  "title": "string",
  "summary": "string (2–3 sentences)",
  "itinerary": [
    {
      "day": "integer",
      "label": "string (e.g. Day 1 — Arrival & Old Town)",
      "morning": "string",
      "afternoon": "string",
      "evening": "string",
      "tips": ["string"],
      "estimated_daily_cost": "string"
    }
  ],
  "total_estimated_cost": "string",
  "packing_tips": ["string"]
}
```

**Constraints baked into prompt:**
- Must respect all dietary/mobility constraints from Stage 1.
- Must not suggest activities incompatible with the stated budget level.
- Each day description must be warm and readable, not robotic.
- Activities should be drawn from general knowledge about real places; the model should not invent implausible or fictional venues.

---

### Stage 4 (Stretch) · SELF-CHECK
**Technique:** `role` (critic) + `structured_output`  
**Job:** Grade the Stage 3 output against a checklist. If it fails, flag it for redo.

**Input:** Stage 1 JSON + Stage 3 JSON

**Output JSON schema:**
```json
{
  "passes": "boolean",
  "scores": {
    "budget_respected": "integer (0–10)",
    "interests_covered": "integer (0–10)",
    "feasibility": "integer (0–10)",
    "readability": "integer (0–10)"
  },
  "issues": ["string"],
  "redo_required": "boolean"
}
```

If `redo_required` is `true`, Stage 3 is re-called with the issues appended to its prompt (max 1 retry).

---

## JSON Handoff Contract

```
Raw text
   │
   ▼ Stage 1 (UNDERSTAND)
Stage1JSON  ── city, days, interests, budget_level, errors[]
   │
   ▼ Stage 2 (REASON)
Stage2JSON  ── reasoning, days[{theme, morning, afternoon, evening}], warnings[]
   │
   ▼ Stage 3 (PRODUCE)   ◄── also receives Stage1JSON
Stage3JSON  ── title, summary, itinerary[{label, tips}], packing_tips
   │
   ▼ Stage 4 (SELF-CHECK, optional)   ◄── also receives Stage1JSON
Stage4JSON  ── passes, scores{}, redo_required
```

Every arrow is a JSON object. No prose is passed between stages.

---

## Prompt Specifications

> **Note on prompt format:** Prompts are passed as a single user-turn message to `call_llm()`. The `System:` prefix in each prompt below is a label for readability in this document — in code it is the start of the user message content, not a separate API system role. See ARCHITECTURE.md § `call_llm` for the exact API shape.

### PROMPT_1 — Stage 1

```
System: You are a travel data extractor. Your only job is to parse a user's 
trip request into a structured JSON object. Return ONLY valid JSON,
no commentary, no markdown fences.

Schema: { city, days, interests[], budget_level, travel_style, 
          dietary_restrictions[], mobility_notes, errors[] }

Rules:
- budget_level must be one of: budget | mid | luxury
- travel_style must be one of: slow | moderate | packed  
- If city or days is missing/unparseable, add a message to errors[] and 
  set city="unknown" / days=3 as defaults.
- If the input is gibberish or a non-English language, set 
  errors=["Input not parseable"] and all fields to defaults.

Input: {raw_text}
```

### PROMPT_2 — Stage 2

```
System: You are a travel planner who thinks carefully before deciding.
You will receive structured trip constraints as JSON and must produce 
a day-by-day activity skeleton.

IMPORTANT: Before writing the days array, think step by step about:
1. What is realistic to see/do per day given travel_style?
2. Which interests match this city best?
3. What budget constraints apply to each day?
Write this reasoning in the "reasoning" field FIRST, then fill "days".

If city is "unknown", set feasibility_notes to "City unknown — generic
itinerary produced" and generate a reasonable generic template
(e.g. a walkable city with common tourist activities).

Return ONLY valid JSON matching this schema:
{ feasibility_notes, reasoning, days[{day, theme, morning, afternoon, 
  evening, estimated_cost}], warnings[] }

Constraints JSON: {stage1_json}
```

### PROMPT_3 — Stage 3

```
System: You are a friendly travel writer producing a polished itinerary.
You receive trip constraints and a day skeleton. Write a warm, practical, 
human-readable itinerary.

Rules:
- Respect ALL dietary_restrictions and mobility_notes from constraints.
- Never suggest activities inconsistent with the budget_level.
- Each description: 1–2 sentences, specific and vivid.
- Add 1–2 practical tips per day.
- Estimate daily and total costs honestly.
- If city is "unknown", write the title and summary to make clear this is
  a generic itinerary, not city-specific.

Return ONLY valid JSON matching this schema:
{ title, summary, itinerary[{day, label, morning, afternoon, evening, 
  tips[], estimated_daily_cost}], total_estimated_cost, packing_tips[] }

Constraints: {stage1_json}
Day skeleton: {stage2_json}
```

---

### PROMPT_4 — Stage 4 (stretch)

```
System: You are a strict travel itinerary critic. You will receive the 
original trip constraints and a finished itinerary. Grade the itinerary 
against the checklist below and return ONLY valid JSON.

Checklist:
- budget_respected (0–10): Does every activity and cost estimate match 
  the requested budget_level?
- interests_covered (0–10): Are the traveller's stated interests 
  meaningfully represented across the days?
- feasibility (0–10): Is the day-by-day schedule realistic (travel time, 
  opening hours, physical demands vs. mobility_notes)?
- readability (0–10): Is the itinerary warm, specific, and easy to follow?

Set redo_required to true if any score is below 6 OR if a hard constraint
(dietary restriction, mobility note) was violated. In issues[], list each
specific problem so it can be corrected.

Return ONLY valid JSON matching this schema:
{ passes, scores{budget_respected, interests_covered, feasibility, 
  readability}, issues[], redo_required }

Constraints: {stage1_json}
Itinerary: {stage3_json}
```

---

## Error Handling Specification

| Scenario | Behaviour |
|----------|-----------|
| Stage returns invalid JSON | Re-prompt once with the parse error appended. Second failure → raise with full context. |
| `errors[]` non-empty in Stage 1 | Stages 2 and 3 read `errors[]` and note the issue; they do not crash. Final output includes a top-level warning. |
| `city = "unknown"` | Stage 2 writes `feasibility_notes: "City unknown — generic itinerary produced"` and generates a generic template. |
| LLM API error / timeout | Catch, print error, re-raise. No silent swallowing. |
| Max retries exceeded | Print `"[ERROR] Stage N failed after max retries"` and exit cleanly. |
| Stage 3 receives malformed Stage 2 JSON (missing keys) | `KeyError` caught; logged; safe default used. Stage 3 prompt includes only available fields. |

---

## Broken Input Test Case

**Input:**
```
asdkjhaksjdhaksjdh 123 ??? 🤔🤔🤔
```

**Acceptance criteria for Stage 1 output:**
- `errors` array is non-empty and describes unparseable input
- `city` defaults to `"unknown"`
- `days` defaults to `3`
- All other fields are set to safe defaults (empty arrays, `null`, or enum defaults)

**Expected pipeline behaviour:** Stages 2 and 3 continue with defaults, producing a generic 3-day moderate-budget itinerary. The final output includes a visible warning banner.

> Note: Exact field values (e.g. the precise wording in `errors[]`) will vary between runs. Acceptance is based on structure and semantics, not literal string matching.

---

## Three Test Inputs

| Run | Input summary | Why it's interesting |
|-----|---------------|----------------------|
| Run 1 | "3 days in Kyoto, love temples and food, mid budget, vegetarian" | Happy path, clean input |
| Run 2 | "10 days Tokyo on a shoestring, obsessed with anime and street food, mobility issues (bad knee)" | Constraint-heavy: budget + mobility + many interests |
| Run 3 | `asdkjhaksjdhaksjdh 123 ???` | Broken input — gibberish |
