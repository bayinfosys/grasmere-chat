# chat

Chat in Welsh, Irish, Scottish Gaelic and Scots through
[Open WebUI](https://docs.openwebui.com/), with the
[Grasmere](https://huggingface.co/jonpojonpo/Grasmere-E4B) models.
Open WebUI is added to the platform as a service and answers at
`http://localhost:3000`.

## Models

| Model | Use |
|---|---|
| `jonpojonpo/grasmere-e4b-ftpo` | everyday chat; the FTPO fix reduces repetition loops in long answers |
| `jonpojonpo/grasmere-e4b` | the highest benchmark scores; loops more often in long answers |
| `sentence-transformers/all-minilm-l6-v2` | Open WebUI's document embeddings |

Both Grasmere models are Gemma 4 E4B fine-tunes, about 16 GB each in
bf16. A 24 GB GPU holds one with room for its context. The worker keeps
one model loaded at a time, so switching between them in Open WebUI
reloads the weights.

## Settings in Open WebUI

The model card recommends these, set per model under Workspace,
Models:

| Setting | Value |
|---|---|
| Temperature | 0.3 |
| Top P | 0.9 |
| Custom parameter `chat_template_kwargs` | `{"enable_thinking": false}` |

Title, tag and follow-up generation run on the same worker as chat. To
keep the queue for chat, turn them off under Admin Panel, Settings,
Interface.

Replies arrive whole when generation finishes; Marigold does not
stream token by token.

## Comparing the models

The [evals](../evals/) application runs a fixed set of Welsh prompts
against each Grasmere model and a stock Gemma 4 baseline, and writes
the answers side by side.
