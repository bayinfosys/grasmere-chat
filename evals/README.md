# grasmere-evals

The same Welsh prompts to every model, with the answers side by side.
It runs each prompt in `prompts.jsonl` against each model in
`models.yaml` through the Marigold API, then exits.

## Models

| Model | Why |
|---|---|
| `jonpojonpo/grasmere-e4b-ftpo` | Grasmere with the FTPO anti-repetition fix |
| `jonpojonpo/grasmere-e4b` | Grasmere, the highest benchmark variant |
| `google/gemma-4-e4b-it` | the model Grasmere is fine-tuned from: the baseline |

`google/gemma-4-e4b-it` is gated on Hugging Face: accept its licence
there and set `HF_TOKEN` before `cache populate`. A model missing from
the catalogue is skipped with a message.

A new Grasmere release is one more entry in `models.yaml`.

## Prompts

Twelve prompts in five groups:

| Group | Tests |
|---|---|
| knowledge | answering factual questions in Welsh |
| language | explaining Welsh grammar and learning |
| translation | English to Welsh and Welsh to English |
| summary | condensing a Welsh paragraph |
| writing, long | free writing; the long prompts allow 768 tokens, where repetition loops show |

Each line of `prompts.jsonl` is one prompt:

```json
{"id": "cy-know-capital", "group": "knowledge", "messages": [{"role": "user", "content": "..."}], "max_tokens": 512}
```

`max_tokens` is optional. The prompts were written for this
evaluation and want checking by a Welsh speaker before results are
quoted.

## Outputs

Written to the application's outputs directory:

| File | Holds |
|---|---|
| `results.jsonl` | one line per model and prompt: answer, seconds, token counts, repetition, loop |
| `summary.md` | one row per model: answered, failed, mean seconds, mean output tokens, mean repetition, loops |
| `answers.md` | every answer grouped by prompt, for reading and comparing |

Repetition is the share of 4-word sequences in an answer that repeat an
earlier one. A loop is any 8-word sequence appearing three or more
times.

## Settings

`[environment]` in `marigold.toml`:

| Variable | Default | |
|---|---|---|
| `EVAL_TEMPERATURE` | `0.3` | the model card's recommendation |
| `EVAL_TOP_P` | `0.9` | the model card's recommendation |
| `EVAL_MAX_TOKENS` | `512` | per answer, unless a prompt sets its own |

Every request also sends `chat_template_kwargs = {"enable_thinking":
false}`, as the model card recommends.

Requests with the same model, prompt and settings return the cached
answer, so a second run finishes at once. Change a setting for new
answers.

All prompts run against one model before the next: the worker keeps one
model loaded, and each switch reloads about 16 GB.
