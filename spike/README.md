# Step 0: test run on your PC

This answers one question before any app code gets written: can the three local models run together on your PC, fast enough and well enough?

| Part | Model | Runs on |
| --- | --- | --- |
| Ears (speech to text) | [PhoWhisper](https://github.com/VinAIResearch/PhoWhisper) medium | GPU |
| Brain (replies and quiet corrections) | Qwen3 8B through [Ollama](https://ollama.com) | GPU |
| Voice (text to Southern speech) | [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS) v3 Turbo, Southern voices | CPU |

It runs two kinds of tests:

- **Typed conversations:** 10 short conversations, one or two per persona, with the mistakes a Southern heritage speaker makes (Northern words, wrong pronouns, English mixed in). These test the brain and voice.
- **Spoken turns:** 8 clips of your own voice, recorded from English prompts, so the ears get tested on how you actually talk.

The report checks **fit** (no crashes, brain fully on the GPU), **speed** (median wait per turn, pass bar 15 s by default) and **valid replies**. **Quality** is yours to judge by ear, and Claude reviews the transcripts for wrong corrections.

## Setup (Windows, one time)

1. Install [Python 3.12](https://www.python.org/downloads/) (tick "Add python.exe to PATH"), [Git](https://git-scm.com/download/win) and [Ollama](https://ollama.com/download). Update your NVIDIA driver if it's old.
2. Download the brain (about 5 GB):
   ```
   ollama pull qwen3:8b
   ```
3. Get the code:
   ```
   git clone https://github.com/austinkn123/VietTime.git
   cd VietTime
   git checkout step0-test
   cd spike
   ```
4. Make a virtual environment and turn it on (in Command Prompt; in PowerShell use `.venv\Scripts\Activate.ps1`):
   ```
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   ```
5. Install PyTorch with CUDA **first**. The default PyPI build on Windows is CPU-only.
   ```
   pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
   ```
6. Install the rest:
   ```
   pip install -r requirements.txt
   ```
7. Check everything is in place. Fix any `FAIL` line before going on.
   ```
   python -m step0 check
   ```

## Run it

1. **Record** the 8 spoken prompts (about 5 minutes). Each one tells you who you're talking to and what to say, in English. Answer in Vietnamese the way you normally talk.
   ```
   python -m step0 record
   ```
2. **Run** every test. The first run also downloads PhoWhisper and VieNeu (a few GB), so it takes longer.
   ```
   python -m step0 run
   ```
3. **Listen.** Open `results\<time>\report.md` and play the files in `results\<time>\audio`. In each "Sounds Southern?" column, write y or n.
4. **Send it back.** Your voice recordings and the audio stay on your PC; only the report and numbers go up:
   ```
   git add results
   git commit -m "Step 0 results"
   git push
   ```
   Then say so in the project thread, and Claude reviews the transcripts.

## Optional comparisons

```
python -m step0 run --models qwen3:8b,qwen3:4b      # compare brains side by side
python -m step0 run --tts-device cuda               # voice on the GPU instead of the CPU
python -m step0 run --ears-model vinai/PhoWhisper-small
python -m step0 run --only typed --limit 3          # quick smoke test, no recordings needed
python -m step0 run --max-wait 20                   # change the speed pass bar
```

## If something fails

| Symptom | Fix |
| --- | --- |
| `PyTorch with CUDA: CUDA not available` | Step 5 was skipped or ran after step 6. Run `pip uninstall torch torchaudio`, then step 5 again. |
| `Ollama: not running` | Open the Ollama app from the Start menu. |
| `sounddevice` or microphone error | Windows Settings → Privacy & security → Microphone → allow desktop apps. |
| `out-of-memory` errors in the report | Expected if the models don't fit. Try `--ears-device cpu` or a smaller brain such as `qwen3:4b`. |

Anything else: paste the full error into the project thread.

## Tests

`pytest` runs the checks that need no models (prompts, reply parsing, the run loop with fake engines, the report).
