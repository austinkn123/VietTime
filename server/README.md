# Server (runs on your PC)

The iPhone app sends your voice here. The server turns it into text (ears), writes the tutor's reply and quiet corrections (brain), turns the reply into Southern speech (voice), and saves the text of each conversation in `data/viettime.db`. Your recordings are deleted right after they're transcribed.

It has two modes:

| Mode | Start it with | What you get |
| --- | --- | --- |
| Practice | `python -m viettime_server --fake` | No models and no GPU. Canned replies and beeps, so you can test the app itself. |
| Real | `python -m viettime_server` | PhoWhisper, Qwen3 8B and VieNeu-TTS, the same models Step 0 tests. |

## Setup (Windows, one time)

You need [Python 3.12](https://www.python.org/downloads/) and [Git](https://git-scm.com/download/win). In Command Prompt:

```
cd VietTime\server
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

That's enough for practice mode. For the real models, also:

1. Install [Ollama](https://ollama.com/download) and run `ollama pull qwen3:8b`.
2. Install PyTorch with CUDA **before** the models (the default PyPI build is CPU-only):
   ```
   pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
   pip install -r requirements-models.txt
   ```

If you already set up Step 0, you can skip step 2 by reusing its environment: run `..\spike\.venv\Scripts\activate` instead, then `pip install -r requirements.txt`.

## Run it

```
cd VietTime\server
.venv\Scripts\activate
python -m viettime_server --fake
```

Drop `--fake` for the real models. The first real start downloads PhoWhisper and VieNeu (a few GB). When it's ready it prints the address the app needs, for example:

```
In the app's Settings, the server address is:  http://192.168.1.20:8000
```

Leave the window open while you practice. **The first time**, Windows asks whether Python may use the network: tick **Private networks** and allow it, or your phone can't reach it.

## Options

```
python -m viettime_server --brain qwen3:4b        # a smaller, faster brain
python -m viettime_server --tts-device cuda       # voice on the GPU instead of the CPU
python -m viettime_server --ears-device cpu       # free GPU memory for the brain
python -m viettime_server --fake --fake-delay 5   # practice mode, pretending replies take 5 s
python -m viettime_server --port 8001             # if 8000 is taken
```

## If something fails

| Symptom | Fix |
| --- | --- |
| The app says it can't reach the server | Check the phone is on the same Wi-Fi as the PC, and the address matches what the server printed. In Windows Settings → Network & internet → Wi-Fi → your network, set the network profile to **Private**. If you denied the firewall prompt, open "Allow an app through Windows Firewall" and tick Private for Python. |
| `Couldn't reach the brain` at start | Open the Ollama app, and run `ollama pull qwen3:8b` once. |
| `only N% of the brain fits on the GPU` | Replies will be slow. Try `--ears-device cpu` or `--brain qwen3:4b`. |
| Replies show but have no sound | The voice failed; the server window shows why. Text keeps working. |

Anything else: paste the server window's output into the project thread.

## How it fits together

| File | What |
| --- | --- |
| `viettime_server/api.py` | The HTTP endpoints the app calls |
| `viettime_server/tutor.py` | One turn: hear, reply, speak, save. Also builds the recap. |
| `viettime_server/engines.py` | The real ears, brain and voice, each swappable |
| `viettime_server/fakes.py` | Stand-ins for practice mode and tests |
| `viettime_server/prompts.py`, `personas.py` | The tutor's instructions and the six personas |
| `viettime_server/store.py` | Conversation history in SQLite |

`pytest` runs the server tests (no models needed).
