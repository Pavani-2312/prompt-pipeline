# Prompt Pipeline — Requirements

## Overview

Build a **prompt-only task-completer**: a chain of 3–4 LLM prompts that together solve a real task too large for a single prompt. No RAG, no tools, no external APIs beyond the LLM. Each prompt does one job and hands structured JSON to the next.

---

## Functional Requirements

### FR-1 · Task Selection
- Choose **exactly one** task from the approved menu:
  - Support ticket triage
  - Essay grader
  - Bug report triage
  - Meeting notes → actions
  - Recipe adapter
  - Trip day-planner

### FR-2 · Stage Count and Labelling
- The pipeline must have **3 to 4 stages**. An optional stretch-goal stage (e.g. a self-check critic) is additive and does not count toward this requirement.
- The chosen task must decompose naturally into that many discrete stages.
- Each stage must be labelled with the Day-2 technique(s) it uses. A stage may carry more than one label if multiple techniques are genuinely applied:
  - `role` — persona/role assignment
  - `structured_output` — explicit JSON schema in prompt
  - `chain_of_thought` — step-by-step reasoning before answer
  - `goal_oriented` — output defined by goal + constraints

### FR-3 · Structured Handoff (JSON)
- Every stage must **return JSON** as its output.
- Stages 2 onward must **consume the JSON** from the previous stage as their input.
- Stage 1 takes raw text as input and returns JSON; it is the only stage that does not consume JSON input.
- No stage may read raw prose output from a prior stage.
- The JSON schema for each handoff must be defined explicitly in the prompt.

### FR-4 · Chain-of-Thought Requirement
- **At least one stage** must use explicit chain-of-thought.
- The model must reason step-by-step before committing to an answer in that stage.
- The reasoning must be visible in the output (e.g. a `"reasoning"` or `"why"` field in JSON).

### FR-5 · Graceful Degradation on Bad Input
- The pipeline must handle **one deliberately broken input**:
  - Missing required field, gibberish text, or wrong language.
- The pipeline must not crash; it must choose one of: **skip** or **default**.
- The chosen strategy must be documented in the reflection.

### FR-6 · Transparency / Inspectability
- Every stage's **input and output must be printed** during a run.
- A run must be readable end-to-end: raw input → Stage 1 out → Stage 2 out → … → final output.
- No silent intermediate steps.

### FR-7 · Proof Runs
- The pipeline must be demonstrated on **three distinct inputs**:
  - At least one "tricky" or edge-case input.
  - At least one broken input (FR-5).
- Full output of all stages must be captured for each run.
- Captured output must be saved to a file (e.g. via stdout redirect or explicit file write) and submitted as a deliverable.

### FR-8 · Reflection
- A written paragraph identifying the **weakest stage**:
  - Why it is the weakest.
  - How you would know (what failure mode looks like).
  - What a tool or retrieval step (Days 4/6) would fix.

---

## Non-Functional Requirements

### NFR-1 · No RAG, No Tools
- No vector databases, no web search, no file I/O beyond reading the input.
- The only external call is the LLM API.

### NFR-2 · Single File
- All code delivered in **one Python file** (`.py`). No notebooks, no multi-file packages.
- The only permitted third-party dependency is `requests` (for HTTP calls to the LLM API). Install with `pip install requests` before running.

### NFR-3 · From Scratch
- No provided scaffold. Every line of code and every prompt is authored by the student.

### NFR-4 · LLM Access
- Use the **OpenRouter API key** from Day 1 (or equivalent).
- The key must be supplied via the `OPENROUTER_API_KEY` environment variable. The program must validate on startup that this variable is set and exit with a clear error message if it is not — never pass `None` silently to the API.
- `call_llm(prompt)` must be a reusable helper function.

### NFR-5 · JSON Robustness
- If a stage returns invalid JSON, the pipeline must **re-prompt with the error** (parse-and-retry).
- A maximum retry count must be enforced to prevent infinite loops.

---

## Stretch Goals (Optional)

| ID | Goal |
|----|------|
| SG-1 | Stage 4: self-check / critic pass that can trigger a redo |
| SG-2 | Model-mix: run the reasoning stage on a different model and compare |
| SG-3 | Few-shot example added to the weakest stage; note the lift |

---

## Deliverables

| Item | Required |
|------|----------|
| Single source file with all code and prompts | ✅ |
| Three captured runs (all stages visible), saved to file | ✅ |
| One broken-input run captured | ✅ |
| One-paragraph reflection on the weakest stage | ✅ |
