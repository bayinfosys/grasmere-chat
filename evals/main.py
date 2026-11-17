"""evals: the same Welsh prompts to every model, answers side by side.

For each model in models.yaml, in order, and each prompt in
prompts.jsonl, this sends one chat completion through the Marigold API
and records the answer, the time it took, its token counts and a
repetition measure. All prompts run against one model before the next,
because the worker keeps one model loaded and a switch reloads it.

Writes to /outputs:

    results.jsonl   one line per model and prompt, written as it arrives
    summary.md      one row per model: answered, failed, time, tokens,
                    repetition, loops
    answers.md      every answer, grouped by prompt, for a Welsh speaker
                    to read and compare

Requests are deterministic for a given model, prompt and settings, so
running it again returns cached answers at once; change a setting to
get new ones.

Settings, from [environment] in marigold.toml:

    EVAL_TEMPERATURE   default 0.3, the model card's recommendation
    EVAL_TOP_P         default 0.9
    EVAL_MAX_TOKENS    default 512; a prompt may set its own max_tokens
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

from pathlib import Path

import httpx

API = os.environ.get("MARIGOLD_API_BASE", "http://localhost:8000").rstrip("/")
HERE = Path(__file__).resolve().parent
OUTPUTS = Path(os.environ.get("EVAL_OUTPUTS", "/outputs"))

TEMPERATURE = float(os.environ.get("EVAL_TEMPERATURE", "0.3"))
TOP_P = float(os.environ.get("EVAL_TOP_P", "0.9"))
MAX_TOKENS = int(os.environ.get("EVAL_MAX_TOKENS", "512"))

# A model load can take minutes; a long answer, minutes more.
REQUEST_TIMEOUT = 1800

# A run of LOOP_WORDS words seen LOOP_COUNT times or more is a loop.
LOOP_WORDS = 8
LOOP_COUNT = 3


def log(message: str) -> None:
    print(message, flush=True)


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

def model_names(path: Path) -> list[str]:
    """The `name:` of every entry under `models:` in models.yaml.

    Read line by line: the executor image has no YAML library, and the
    names are all this needs.
    """
    names = []
    in_models = False

    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^models:\s*$", line):
            in_models = True
            continue
        if in_models and re.match(r"^\S", line):
            break
        match = re.match(r"^\s+(?:-\s+)?name:\s*(\S+)\s*$", line)
        if in_models and match:
            names.append(match.group(1))

    return names


def load_prompts(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# the API
# ---------------------------------------------------------------------------

def wait_for_api(client: httpx.Client, attempts: int = 60, delay: float = 5.0) -> list[str]:
    """The model ids the API serves, once it answers."""
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(f"{API}/v1/models", timeout=10)
            response.raise_for_status()
            return [model["id"] for model in response.json()["data"]]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            log(f"waiting for the API ({attempt}/{attempts}): {e}")
            time.sleep(delay)

    raise SystemExit(f"the API at {API} did not answer")


def complete(client: httpx.Client, model: str, prompt: dict) -> dict:
    """One chat completion, with its timing and any error."""
    body = {
        "model": model,
        "messages": prompt["messages"],
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": prompt.get("max_tokens", MAX_TOKENS),
        # Gemma 4 can think before answering; the model card turns it off.
        "chat_template_kwargs": {"enable_thinking": False},
    }

    started = time.monotonic()

    try:
        response = client.post(f"{API}/v1/chat/completions", json=body, timeout=REQUEST_TIMEOUT)
        seconds = time.monotonic() - started
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        return {
            "ok": True,
            "answer": data["choices"][0]["message"]["content"] or "",
            "seconds": round(seconds, 2),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
        }
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "seconds": round(time.monotonic() - started, 2),
        }


# ---------------------------------------------------------------------------
# measures
# ---------------------------------------------------------------------------

def words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def repetition(text: str, n: int = 4) -> float:
    """Share of word n-grams that repeat an earlier one: 0 for none."""
    tokens = words(text)
    grams = [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
    return round(1 - len(set(grams)) / len(grams), 3) if grams else 0.0


def looped(text: str) -> bool:
    """True when one run of LOOP_WORDS words appears LOOP_COUNT times."""
    tokens = words(text)
    counts: dict[tuple, int] = {}

    for i in range(len(tokens) - LOOP_WORDS + 1):
        gram = tuple(tokens[i:i + LOOP_WORDS])
        counts[gram] = counts.get(gram, 0) + 1
        if counts[gram] >= LOOP_COUNT:
            return True

    return False


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------

def mean(values: list) -> str:
    values = [v for v in values if v is not None]
    return f"{sum(values) / len(values):.2f}" if values else "-"


def write_summary(rows: list[dict], models: list[str], path: Path) -> None:
    lines = [
        "# Summary",
        "",
        f"Temperature {TEMPERATURE}, top_p {TOP_P}, max_tokens {MAX_TOKENS} unless a prompt sets its own.",
        "",
        "| Model | Answered | Failed | Mean seconds | Mean output tokens | Mean repetition | Loops |",
        "|---|---|---|---|---|---|---|",
    ]

    for model in models:
        mine = [r for r in rows if r["model"] == model]
        good = [r for r in mine if r["ok"]]
        lines.append(
            f"| `{model}` | {len(good)} | {len(mine) - len(good)} "
            f"| {mean([r['seconds'] for r in good])} "
            f"| {mean([r.get('completion_tokens') for r in good])} "
            f"| {mean([r['repetition'] for r in good])} "
            f"| {sum(r['looped'] for r in good)} |"
        )

    lines += [
        "",
        "Repetition is the share of 4-word sequences that repeat an earlier one.",
        f"A loop is any {LOOP_WORDS}-word sequence appearing {LOOP_COUNT} or more times.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_answers(rows: list[dict], prompts: list[dict], models: list[str], path: Path) -> None:
    lines = ["# Answers", ""]

    for prompt in prompts:
        lines += [f"## {prompt['id']} ({prompt['group']})", ""]
        lines += [f"> {line}" for line in prompt["messages"][-1]["content"].splitlines()]
        lines.append("")

        for model in models:
            row = next((r for r in rows if r["model"] == model and r["prompt_id"] == prompt["id"]), None)
            lines.append(f"### `{model}`")
            lines.append("")
            if row is None:
                lines.append("_not run_")
            elif not row["ok"]:
                lines.append(f"_failed: {row['error']}_")
            else:
                note = ", loop" if row["looped"] else ""
                lines.append(f"_{row['seconds']} s, {row.get('completion_tokens')} tokens, repetition {row['repetition']}{note}_")
                lines.append("")
                lines.append(row["answer"].strip())
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    models = model_names(HERE / "models.yaml")
    prompts = load_prompts(HERE / "prompts.jsonl")
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    log(f"{len(prompts)} prompts, {len(models)} models, API at {API}")

    rows: list[dict] = []

    with httpx.Client() as client, open(OUTPUTS / "results.jsonl", "w", encoding="utf-8") as results:
        served = wait_for_api(client)

        for model in models:
            if model not in served:
                log(f"{model}: not in the catalogue; run marigold cache populate first. Skipped.")
                continue

            log(f"{model}: {len(prompts)} prompts")

            for prompt in prompts:
                row = {"model": model, "prompt_id": prompt["id"], "group": prompt["group"]}
                row.update(complete(client, model, prompt))

                if row["ok"]:
                    row["repetition"] = repetition(row["answer"])
                    row["looped"] = looped(row["answer"])
                    log(f"  {prompt['id']:<16} {row['seconds']:>8.1f} s  repetition {row['repetition']}"
                        + ("  LOOP" if row["looped"] else ""))
                else:
                    log(f"  {prompt['id']:<16} failed: {row['error']}")

                rows.append(row)
                results.write(json.dumps(row, ensure_ascii=False) + "\n")
                results.flush()

    write_summary(rows, models, OUTPUTS / "summary.md")
    write_answers(rows, prompts, models, OUTPUTS / "answers.md")
    log(f"wrote {OUTPUTS / 'results.jsonl'}, summary.md and answers.md")

    return 0 if rows and all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
