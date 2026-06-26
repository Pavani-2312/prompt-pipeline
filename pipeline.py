"""
Trip Day-Planner — Prompt Pipeline
Stages: UNDERSTAND → REASON → PRODUCE → SELF-CHECK (stretch)
"""

import json
import os
import sys

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_KEY         = os.environ.get("OPENROUTER_API_KEY")
MODEL           = "openai/gpt-4o-mini"
MAX_ATTEMPTS    = 3    # 1 original + 2 retries
STAGE4_MAX_REDO = 1    # max Stage 3 redos triggered by Stage 4
TEMPERATURE     = 0.3

if not API_KEY:
    sys.exit("[ERROR] OPENROUTER_API_KEY environment variable is not set.")

# ---------------------------------------------------------------------------
# Prompts  (canonical text: docs/SPECIFICATIONS.md)
# ---------------------------------------------------------------------------
PROMPT_1 = """\
You are a travel data extractor. Your only job is to parse a user's \
trip request into a structured JSON object. Return ONLY valid JSON, \
no commentary, no markdown fences.

Schema: {{ city, days, interests[], budget_level, travel_style, \
dietary_restrictions[], mobility_notes, errors[] }}

Rules:
- budget_level must be one of: budget | mid | luxury
- travel_style must be one of: slow | moderate | packed
- If city or days is missing/unparseable, add a message to errors[] and \
set city="unknown" / days=3 as defaults.
- If the input is gibberish or a non-English language, set \
errors=["Input not parseable"] and all fields to defaults.

Input: {raw_text}"""

PROMPT_2 = """\
You are a travel planner who thinks carefully before deciding.
You will receive structured trip constraints as JSON and must produce \
a day-by-day activity skeleton.

IMPORTANT: Before writing the days array, think step by step about:
1. What is realistic to see/do per day given travel_style?
2. Which interests match this city best?
3. What budget constraints apply to each day?
Write this reasoning in the "reasoning" field FIRST, then fill "days".

If city is "unknown", set feasibility_notes to \
"City unknown — generic itinerary produced" and generate a reasonable \
generic template (e.g. a walkable city with common tourist activities).

Return ONLY valid JSON matching this schema:
{{ feasibility_notes, reasoning, \
days[{{day, theme, morning, afternoon, evening, estimated_cost}}], \
warnings[] }}

Constraints JSON: {stage1_json}"""

PROMPT_3 = """\
You are a friendly travel writer producing a polished itinerary.
You receive trip constraints and a day skeleton. Write a warm, practical, \
human-readable itinerary.

Rules:
- Respect ALL dietary_restrictions and mobility_notes from constraints.
- Never suggest activities inconsistent with the budget_level.
- Each description: 1-2 sentences, specific and vivid.
- Add 1-2 practical tips per day.
- Estimate daily and total costs honestly.
- If city is "unknown", write the title and summary to make clear this is \
a generic itinerary, not city-specific.

Return ONLY valid JSON matching this schema:
{{ title, summary, \
itinerary[{{day, label, morning, afternoon, evening, tips[], \
estimated_daily_cost}}], total_estimated_cost, packing_tips[] }}

Constraints: {stage1_json}
Day skeleton: {stage2_json}"""

PROMPT_4 = """\
You are a strict travel itinerary critic. You will receive the original \
trip constraints and a finished itinerary. Grade the itinerary against \
the checklist below and return ONLY valid JSON.

Checklist:
- budget_respected (0-10): Does every activity and cost estimate match \
the requested budget_level?
- interests_covered (0-10): Are the traveller's stated interests \
meaningfully represented across the days?
- feasibility (0-10): Is the day-by-day schedule realistic (travel time, \
opening hours, physical demands vs. mobility_notes)?
- readability (0-10): Is the itinerary warm, specific, and easy to follow?

Set redo_required to true if any score is below 6 OR if a hard constraint \
(dietary restriction, mobility note) was violated. In issues[], list each \
specific problem so it can be corrected.

Return ONLY valid JSON matching this schema:
{{ passes, \
scores{{budget_respected, interests_covered, feasibility, readability}}, \
issues[], redo_required }}

Constraints: {stage1_json}
Itinerary: {stage3_json}"""

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def call_llm(prompt: str) -> str:
    """Single LLM call via OpenRouter. Returns raw string response."""
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": TEMPERATURE,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    return text.strip()


def parse_json_with_retry(prompt: str, raw: str) -> dict:
    """Parse JSON from LLM output, retrying on failure up to MAX_ATTEMPTS total."""
    original_prompt = prompt
    for attempt in range(MAX_ATTEMPTS):
        try:
            return json.loads(_strip_fences(raw))
        except json.JSONDecodeError as e:
            if attempt + 1 >= MAX_ATTEMPTS:
                raise RuntimeError(
                    f"[ERROR] Failed to parse JSON after {MAX_ATTEMPTS} attempts.\n"
                    f"Last error: {e}\nLast response:\n{raw}"
                )
            print(f"  [retry {attempt+1}/{MAX_ATTEMPTS-1}] Invalid JSON — re-prompting…")
            raw = call_llm(
                original_prompt
                + f"\n\n[CORRECTION] Your last response was invalid JSON."
                  f" Error: {e}\nReturn ONLY valid JSON."
            )


def show(label: str, data) -> None:
    """Print a stage label and its payload (satisfies FR-6)."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2) if isinstance(data, dict) else data)


# ---------------------------------------------------------------------------
# Stage functions
# ---------------------------------------------------------------------------

def stage1_understand(raw_text: str) -> dict:
    # Technique: role + structured_output
    prompt = PROMPT_1.format(raw_text=raw_text)
    return parse_json_with_retry(prompt, call_llm(prompt))


def stage2_reason(s1: dict) -> dict:
    # Technique: chain_of_thought
    prompt = PROMPT_2.format(stage1_json=json.dumps(s1, indent=2))
    return parse_json_with_retry(prompt, call_llm(prompt))


def stage3_produce(s1: dict, s2: dict, revision_notes: str = "") -> dict:
    # Technique: goal_oriented + constraints
    prompt = PROMPT_3.format(
        stage1_json=json.dumps(s1, indent=2),
        stage2_json=json.dumps(s2, indent=2),
    )
    if revision_notes:
        prompt += f"\n\n[REVISION REQUIRED] Fix these issues:\n{revision_notes}"
    return parse_json_with_retry(prompt, call_llm(prompt))


def stage4_selfcheck(s1: dict, s3: dict) -> dict:
    # Technique: role (critic) + structured_output
    prompt = PROMPT_4.format(
        stage1_json=json.dumps(s1, indent=2),
        stage3_json=json.dumps(s3, indent=2),
    )
    return parse_json_with_retry(prompt, call_llm(prompt))


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

def run(raw_text: str) -> dict:
    show("INPUT", raw_text)

    s1 = stage1_understand(raw_text)
    show("STAGE 1 — UNDERSTAND  [role + structured_output]", s1)

    if s1.get("errors"):
        print(f"\n  ⚠  WARNING: Stage 1 errors: {s1['errors']}")

    s2 = stage2_reason(s1)
    show("STAGE 2 — REASON  [chain_of_thought]", s2)

    s3 = stage3_produce(s1, s2)
    show("STAGE 3 — PRODUCE  [goal_oriented + constraints]", s3)

    s4 = stage4_selfcheck(s1, s3)
    show("STAGE 4 — SELF-CHECK  [role + structured_output]", s4)

    if s4.get("redo_required"):
        issues = "\n".join(f"- {i}" for i in s4.get("issues", []))
        print(f"\n  ↺  Redo triggered. Issues:\n{issues}")
        s3 = stage3_produce(s1, s2, revision_notes=issues)
        show("STAGE 3 — PRODUCE (revised)", s3)

    return s3


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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
        try:
            run(text)
        except Exception as e:
            print(f"\n[ERROR] Run {i} aborted: {e}")
