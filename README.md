# Grasmere on Marigold

A [Marigold](https://marigold.run) registry for the
[Grasmere](https://huggingface.co/jonpojonpo/Grasmere-E4B) models:
Gemma 4 E4B fine-tuned for Welsh, Irish, Scottish Gaelic and Scots.

| Application | Directory | What it does |
|---|---|---|
| `chat` | [chat](chat/) | chat with the Grasmere models through Open WebUI |
| `evals` | [evals](evals/) | the same Welsh prompts to each Grasmere model and stock Gemma 4, answers side by side |

The names are deliberately those of applications in other registries,
such as `chat` in [marigold-examples](https://examples.marigold.run):
a host with both registries resolves `chat` to whichever it lists
first.

The registry is published at `https://grasmere-chat.marigold.run`.

## Running from this repository

Requires Marigold, Docker and, for these models, a GPU with about 24 GB
of memory.

```sh
git clone https://github.com/bayinfosys/grasmere-chat
cd grasmere-chat

marigold application create chat -o dist/
marigold application install dist/chat-local.tar.gz
marigold cache populate chat
marigold application start chat               # Open WebUI at http://localhost:3000
```

The evaluation, the same way:

```sh
marigold application create evals -o dist/
marigold application install dist/evals-local.tar.gz
marigold cache populate evals                 # needs HF_TOKEN for google/gemma-4-e4b-it
marigold application start evals
marigold application logs evals
```

Its results are written to the application's outputs directory under
the Marigold cache.

## Layout

Each application is one directory below the root, holding its
`marigold.toml`, and the directory's name is the application's name. `marigold-registry.toml` at the root describes the
registry. Pushing a `v*` tag publishes every application under that
tag.

## Credits

The Grasmere models are by
[jonpojonpo](https://huggingface.co/jonpojonpo). They are Gemma 4
fine-tunes, used under the Gemma terms. This repository holds only
Marigold applications, under the MIT licence.
