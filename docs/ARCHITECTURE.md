# Prompt Pipeline — Architecture

## System Overview

A purely prompt-driven pipeline. The only moving parts are Python functions, prompt strings, and JSON objects. No databases, no vector stores, no tool calls — just structured data flowing between LLM calls.

```
┌─────────────────────────────────────────────────────────────────┐
│                        pipeline.py                              │
│                                                                 │
│  raw_text                                                       │
│     │                                                           │
│     ▼                                                           │
│  ┌──────────────┐   JSON    ┌──────────────┐   JSON            │
│  │  Stage 1     │ ────────► │  Stage 2     │ ──────┐           │
│  │  UNDERSTAND  │           │  REASON      │       │           │
│  │  role +      │           │  chain-of-   │       │           │
│  │  struct out  │           │  thought     │       │ JSON      │
│  └──────────────┘           └──────────────┘       ▼           │
│                                              ┌──────────────┐  │
│         Stage1JSON ──────────────────────────► Stage 3      │  │
│                                              │  PRODUCE     │  │
│                                              │  goal +      │  │
│                                              │  constraints │  │
│                                              └──────┬───────┘  │
│                                                     │ JSON     │
│                                                     ▼          │
│                                              ┌──────────────┐  │
│                                              │  [Stage 4]   │  │
│                                              │  SELF-CHECK  │  │
│                                              │  (stretch)   │  │
│                                              └──────┬───────┘  │
│                                                     │          │
│                                                     ▼          │
│                                              final_output      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Layout

```
pipeline.py
├── Configuration
│   ├── API_KEY           — OpenRouter key from environment / Day 1
│   ├── MODEL             — e.g. "openai/gpt-4o-mini"
│   ├── MAX_ATTEMPTS = 3  — total attempts per stage (1 original + 2 retries)
│   ├── STAGE4_MAX_REDO=1 — max Stage 3 redos triggered by Stage 4
│   └── TEMPERATURE = 0.3
│
├── Core Helper
│   └── call_llm(prompt: str) → str
│
├── JSON Helper
│   └── parse_json_with_retry(prompt: str, raw: str) → dict
│
├── Stage Functions
│   ├── stage1_understand(raw_text: str) → dict
│   ├── stage2_reason(s1: dict) → dict
│   ├── stage3_produce(s1: dict, s2: dict) → dict
│   └── stage4_selfcheck(s1: dict, s3: dict) → dict  [stretch]
│
├── Display Helper
│   └── show(label: str, data: any) → None  ← required for FR-6
│
└── Entry Point
    └── run(raw_text: str) → dict
```

---

## Data Flow Diagram

```
run(raw_text)
     │
     ├── [SHOW] "INPUT" raw_text
     │
     ▼
stage1_understand(raw_text)
     │   prompt = PROMPT_1.format(raw_text=raw_text)
     │   raw    = call_llm(prompt)
     │   s1     = parse_json_with_retry(prompt, raw)
     │
     ├── [SHOW] "STAGE 1 — UNDERSTAND" s1
     │
     ▼
stage2_reason(s1)
     │   prompt = PROMPT_2.format(stage1_json=json.dumps(s1, indent=2))
     │   raw    = call_llm(prompt)
     │   s2     = parse_json_with_retry(prompt, raw)
     │
     ├── [SHOW] "STAGE 2 — REASON" s2
     │
     ▼
stage3_produce(s1, s2)
     │   prompt = PROMPT_3.format(
     │               stage1_json=json.dumps(s1, indent=2),
     │               stage2_json=json.dumps(s2, indent=2))
     │   raw    = call_llm(prompt)
     │   s3     = parse_json_with_retry(prompt, raw)
     │
     ├── [SHOW] "STAGE 3 — PRODUCE" s3
     │
     ▼
[stage4_selfcheck(s1, s3)]  ← stretch goal
     │   if s4["redo_required"]: re-call stage3 with issues injected
     │
     └── [SHOW] "STAGE 4 — SELF-CHECK" s4
     │
     ▼
return s3  (or s3_redo if Stage 4 triggered a redo)
```

---

## Core Components

### `call_llm(prompt)`

Each prompt is sent as a single user-turn message. The role and persona instructions are embedded at the top of the prompt string itself — no separate API system role is used. This keeps the function signature simple and each prompt fully self-contained.

```python
def call_llm(prompt: str) -> str:
    """Single LLM call via OpenRouter. Returns raw string response."""
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": TEMPERATURE
        }
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
```

**Notes:**
- `TEMPERATURE = 0.3`: low enough for consistent JSON, high enough for natural prose in Stage 3.
- `raise_for_status()` ensures HTTP errors surface immediately.

---

### `parse_json_with_retry(prompt, raw)`

```
original_prompt = prompt   # captured once before the loop; never modified
attempt = 0
while attempt < MAX_ATTEMPTS:
    try:
        strip markdown fences if present
        return json.loads(cleaned_raw)
    except json.JSONDecodeError as e:
        attempt += 1
        if attempt >= MAX_ATTEMPTS:
            raise RuntimeError(f"Failed to parse JSON after {MAX_ATTEMPTS} attempts")
        retry_prompt = original_prompt + f"\n\n[CORRECTION] Your last response was invalid JSON. Error: {e}\nReturn ONLY valid JSON."
        raw = call_llm(retry_prompt)
```

**Attempt accounting:** `MAX_ATTEMPTS = 3` means one original call plus up to two retries. The condition `attempt >= MAX_ATTEMPTS` fires after the third failure, so the model gets exactly `MAX_ATTEMPTS - 1` correction chances.

**Note on prompt growth:** Each retry appends a correction block to `original_prompt` (not to the previous retry prompt), so the prompt grows by exactly one correction block per retry. With `MAX_ATTEMPTS = 3` the growth is bounded.

**Why this matters:** The seam between stages is where pipelines break. A missing comma or trailing explanation text from the LLM causes a cascade failure. The retry loop catches this, shows the error to the model, and asks for a correction — without human intervention.

---

### `show(label, data)`

```python
def show(label: str, data: any) -> None:
    """Print a stage's input or output in an inspectable format."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    if isinstance(data, dict):
        print(json.dumps(data, indent=2))
    else:
        print(data)
```

**Important:** `show()` is not optional. Every call to `show()` satisfies FR-6 (Transparency / Inspectability). Removing or skipping any `show()` call means a stage's input or output is not printed, which directly violates FR-6.

---

## Stage Architecture Detail

### Stage 1 — UNDERSTAND
| Property | Value |
|----------|-------|
| Technique | `role` + `structured_output` |
| Input | `str` (raw user text) |
| Output | `dict` matching Stage1Schema |
| Error handling | Populates `errors[]` field; never throws on bad input |
| Key prompt design | Explicit JSON schema in prompt; enumerated valid values for `budget_level` and `travel_style` |

### Stage 2 — REASON
| Property | Value |
|----------|-------|
| Technique | `chain_of_thought` |
| Input | Stage 1 `dict` |
| Output | `dict` matching Stage2Schema |
| Key prompt design | Instructs model to fill `reasoning` field FIRST before filling `days[]`; visible step-by-step thinking is contractually required |
| Why CoT here | This is the highest-stakes decision stage — feasibility and activity selection. CoT reduces hallucinated or incoherent day plans. |

### Stage 3 — PRODUCE
| Property | Value |
|----------|-------|
| Technique | `goal_oriented` + `constraints` |
| Input | Stage 1 `dict` + Stage 2 `dict` |
| Output | `dict` matching Stage3Schema |
| Key prompt design | Goal stated upfront ("produce a warm, human-readable itinerary"); hard constraints listed explicitly (respect dietary/mobility, match budget) |
| Why both inputs | Stage 1 carries constraints; Stage 2 carries the skeleton. Stage 3 needs both. |
| Schema-level failure | If Stage 2 JSON is missing expected keys, `KeyError` is caught, logged, and the prompt is built with only available fields. Stage 3 continues with a degraded but non-crashing input. |

### Stage 4 — SELF-CHECK (stretch)
| Property | Value |
|----------|-------|
| Technique | `role` (critic) + `structured_output` |
| Input | Stage 1 `dict` + Stage 3 `dict` |
| Output | `dict` with `passes`, `scores{}`, `redo_required` |
| Redo logic | If `redo_required=true`: append `issues[]` to Stage 3 prompt and re-call. Capped at `STAGE4_MAX_REDO = 1` redo to avoid loops. |

---

## Prompt Template Ownership

Each stage owns its prompt as a module-level constant string, named clearly:

```python
PROMPT_1 = """..."""   # Stage 1: UNDERSTAND
PROMPT_2 = """..."""   # Stage 2: REASON (chain-of-thought)
PROMPT_3 = """..."""   # Stage 3: PRODUCE
PROMPT_4 = """..."""   # Stage 4: SELF-CHECK (stretch)
```

Prompts use Python `.format()` for variable injection. Template variables are always named (e.g. `{raw_text}`, `{stage1_json}`) — never positional `{0}`.

The canonical prompt text lives in SPECIFICATIONS.md (Prompt Specifications section). The constants in `pipeline.py` must match that text exactly. SPECIFICATIONS.md is the single source of truth for prompt wording; this file describes the structural role of those constants in the code.

---

## Error Taxonomy

| Error type | Where it occurs | Handling |
|------------|-----------------|----------|
| Bad user input | Stage 1 input | `errors[]` populated; pipeline continues with defaults |
| Invalid JSON from LLM | Any stage | `parse_json_with_retry` re-prompts up to `MAX_ATTEMPTS - 1` times |
| Missing required JSON field (schema-level) | Any stage | `KeyError` caught; logged; safe default used |
| LLM API HTTP error | `call_llm` | `raise_for_status()` — propagates up, printed, run aborts |
| Max retries exceeded | `parse_json_with_retry` | `RuntimeError` raised with full context |

---

## Configuration

```python
API_KEY          = os.environ.get("OPENROUTER_API_KEY")   # never hardcode
MODEL            = "openai/gpt-4o-mini"                    # fast + cheap
MAX_ATTEMPTS     = 3    # total LLM attempts per stage (1 original + 2 retries)
STAGE4_MAX_REDO  = 1    # max times Stage 4 can trigger a Stage 3 redo
TEMPERATURE      = 0.3  # reproducible but not robotic
```

**Model selection rationale:** `gpt-4o-mini` balances speed, cost, and JSON reliability. The reasoning stage could be swapped for a stronger model (stretch goal SG-2) — the architecture supports this by isolating each stage in its own function.

---

## Run Entry Point

```python
if __name__ == "__main__":
    test_inputs = [
        "3 days in Kyoto, love temples and food, mid budget, vegetarian",
        "10 days Tokyo shoestring, obsessed with anime and street food, bad knee",
        "asdkjhaksjdhaksjdh 123 ??? 🤔🤔🤔",
    ]
    for i, text in enumerate(test_inputs, 1):
        print(f"\n{'#'*60}")
        print(f"  RUN {i} OF {len(test_inputs)}")
        print(f"{'#'*60}")
        result = run(text)
```

To capture proof runs for the deliverable, redirect stdout when executing:

```bash
python pipeline.py 2>&1 | tee proof_runs.txt
```

---

## Why This Architecture Is the Agent Skeleton

| Component | Today (pipeline) | Day 4 (RAG) | Days 6–8 (agent) |
|-----------|-----------------|-------------|-----------------|
| `call_llm` | Direct prompt | Prompt + retrieved docs | Prompt + tools |
| Stage 1 | Parse input | Parse + retrieve | Parse + decide next tool |
| Stage 2 | Reason over JSON | Reason over docs | Reason over tool results |
| Stage 3 | Produce output | Produce cited output | Produce + loop |
| Handoff format | JSON | JSON + citations | JSON + tool calls |

The function signatures, JSON contracts, and `parse_json_with_retry` pattern are reused verbatim in more complex architectures. The skeleton is the same.
