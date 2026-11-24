"""Step 0: can ears, brain and voice all run on this PC, fast enough and well enough?

    python -m step0 check    # what's installed, what's missing
    python -m step0 record   # record your voice for the spoken tests
    python -m step0 run      # run every test and write results/<time>/report.md
"""

import argparse
import json
import platform
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORDINGS = ROOT / "recordings"
RESULTS = ROOT / "results"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_EARS = "vinai/PhoWhisper-medium"
OLLAMA = "http://127.0.0.1:11434"


def _line(ok: bool | None, label: str, detail: str = "") -> None:
    mark = {True: "OK  ", False: "FAIL", None: "WARN"}[ok]
    print(f"[{mark}] {label}{': ' + detail if detail else ''}")


def cmd_check(args) -> int:
    import requests

    failures = 0
    py_ok = sys.version_info >= (3, 10)
    _line(py_ok, "Python", platform.python_version() + ("" if py_ok else " (need 3.10 or newer)"))
    failures += not py_ok

    try:
        import torch

        cuda = torch.cuda.is_available()
        detail = f"torch {torch.__version__}, " + (torch.cuda.get_device_name(0) if cuda else "CUDA not available")
        _line(cuda, "PyTorch with CUDA", detail)
        failures += not cuda
    except ImportError:
        _line(False, "PyTorch", "not installed (see README step 5)")
        failures += 1

    from .monitor import gpu_memory_mb

    gpu = gpu_memory_mb()
    _line(gpu is not None, "nvidia-smi", f"{gpu[0]} / {gpu[1]} MB in use" if gpu else "not found")

    for module in ("transformers", "vieneu", "sounddevice", "soundfile", "soxr", "psutil"):
        try:
            mod = __import__(module)
            _line(True, module, getattr(mod, "__version__", "installed"))
        except Exception as e:  # sounddevice raises OSError without PortAudio
            _line(False, module, str(e))
            failures += 1

    try:
        version = requests.get(f"{OLLAMA}/api/version", timeout=5).json().get("version")
        _line(True, "Ollama", version)
        names = {m["name"] for m in requests.get(f"{OLLAMA}/api/tags", timeout=5).json().get("models", [])}
        for model in args.models.split(","):
            has = model in names or f"{model}:latest" in names
            _line(has, f"Ollama model {model}", "pulled" if has else f"run: ollama pull {model}")
            failures += not has
    except requests.RequestException:
        _line(False, "Ollama", "not running; install it and open the Ollama app")
        failures += 1

    try:
        import sounddevice as sd

        mic = sd.query_devices(kind="input")
        _line(True, "Microphone", mic["name"])
    except Exception as e:
        _line(None, "Microphone", f"none found ({e}); only needed for `record`")

    free_gb = shutil.disk_usage(Path.home()).free / 2**30
    _line(free_gb > 20, "Free disk", f"{free_gb:.0f} GB (models need about 15 GB)")

    recs = sorted(RECORDINGS.glob("*.wav"))
    _line(None if not recs else True, "Recordings", f"{len(recs)} found" if recs else "none yet; run `python -m step0 record`")
    print("\nReady to run." if not failures else f"\n{failures} problem(s) to fix first.")
    return 1 if failures else 0


def cmd_record(args) -> int:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    from .personas import PERSONAS
    from .scenarios import RECORDING_PROMPTS

    RECORDINGS.mkdir(exist_ok=True)
    print("Speak Vietnamese the way you normally would. English words are fine where a prompt says so.")
    print("For each prompt: press Enter to start, Enter again to stop.\n")
    for i, prompt in enumerate(RECORDING_PROMPTS, 1):
        persona = PERSONAS[prompt.persona]
        while True:
            print(f"{i}/{len(RECORDING_PROMPTS)}  You're talking to {persona.name} ({persona.description}).")
            print(f"     Call them '{persona.austin_calls_them}', yourself '{persona.austin_self}'.")
            print(f"     {prompt.say}")
            input("     Enter to start recording... ")
            chunks = []
            with sd.InputStream(samplerate=16_000, channels=1, dtype="float32", callback=lambda d, *_: chunks.append(d.copy())):
                input("     Recording. Enter to stop... ")
            audio = np.concatenate(chunks) if chunks else np.zeros((0, 1), dtype="float32")
            path = RECORDINGS / f"{i:02d}-{prompt.key}.wav"
            sf.write(str(path), audio, 16_000)
            again = input(f"     Saved {len(audio) / 16_000:.1f} s. Enter to continue, r to redo: ").strip().lower()
            if again != "r":
                break
        print()
    print(f"Done. Recordings are in {RECORDINGS}. Next: python -m step0 run")
    return 0


def _is_oom(e: Exception) -> bool:
    return "out of memory" in str(e).lower()


def cmd_run(args) -> int:
    from .engines import Brain, Ears, Voice
    from .monitor import ResourceMonitor
    from .personas import PERSONAS
    from .prompts import build_messages
    from .report import render, summary_rows
    from .scenarios import RECORDING_PROMPTS, SCRIPTED

    started = datetime.now()
    out_dir = RESULTS / started.strftime("%Y%m%d-%H%M%S")
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    recordings = {p.key: next(iter(sorted(RECORDINGS.glob(f"*-{p.key}.wav"))), None) for p in RECORDING_PROMPTS}
    spoken = [(p, path) for p, path in ((p, recordings[p.key]) for p in RECORDING_PROMPTS) if path]
    if args.only == "typed":
        spoken = []
    scripted = [] if args.only == "spoken" else SCRIPTED[: args.limit or None]
    if args.only == "spoken" and not spoken:
        print("No recordings found. Run `python -m step0 record` first.")
        return 1

    results = {
        "started": started.isoformat(timespec="seconds"),
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "config": {
            "models": models,
            "ears_model": args.ears_model,
            "ears_device": args.ears_device,
            "tts_device": args.tts_device,
            "max_wait": args.max_wait,
        },
        "snapshots": [],
        "errors": [],
        "models": {},
    }
    try:
        import torch

        if torch.cuda.is_available():
            results["machine"]["gpu"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    monitor = ResourceMonitor()
    monitor.start()
    monitor.snapshot("Before loading anything")

    def fail(where: str, e: Exception) -> None:
        print(f"  ! {where}: {e}")
        results["errors"].append({"where": where, "message": str(e)[:500], "oom": _is_oom(e)})

    print("Loading voice (VieNeu)...")
    start = time.perf_counter()
    voice = Voice(args.tts_device)
    monitor.snapshot("Voice loaded")["seconds"] = time.perf_counter() - start
    for p in PERSONAS.values():
        if not voice.has_voice(p.voice):
            fail("voice", RuntimeError(f"VieNeu has no voice named {p.voice} (for {p.name})"))

    ears = None
    if spoken:
        print(f"Loading ears ({args.ears_model})...")
        start = time.perf_counter()
        try:
            ears = Ears(args.ears_model, args.ears_device)
            monitor.snapshot("Ears loaded")["seconds"] = time.perf_counter() - start
        except Exception as e:
            fail("loading ears", e)
            spoken = []

    def speak(text: str, persona, name: str) -> tuple[float | None, str | None]:
        try:
            return voice.speak(text, persona.voice, audio_dir / name), name
        except Exception as e:
            fail(f"voice for {name}", e)
            return None, None

    for model in models:
        print(f"\nBrain: {model}")
        brain = Brain(model, host=OLLAMA)
        data = {"turns": []}
        results["models"][model] = data
        slug = model.replace(":", "-").replace("/", "-")
        try:
            start = time.perf_counter()
            brain.warm()
            monitor.snapshot(f"Brain loaded ({model})")["seconds"] = time.perf_counter() - start
            data["gpu_share"] = brain.gpu_share()
        except Exception as e:
            fail(f"loading {model}", e)
            continue

        for prompt, path in spoken:
            persona = PERSONAS[prompt.persona]
            print(f"  spoken: {prompt.key}")
            turn = {"kind": "spoken", "scenario": prompt.key, "prompt": prompt.say, "persona_name": persona.name}
            try:
                turn["heard"], turn["ears_s"] = ears.transcribe(path)
                answer = brain.respond(build_messages(persona, [], turn["heard"]))
            except Exception as e:
                fail(f"{model} {prompt.key}", e)
                turn["error"] = str(e)[:300]
                data["turns"].append(turn)
                continue
            turn.update(reply=answer.reply, corrections=answer.corrections, new_words=answer.new_words, brain_s=answer.seconds, error=answer.error)
            if answer.reply:
                turn["voice_s"], turn["audio"] = speak(answer.reply, persona, f"{slug}-spoken-{prompt.key}.wav")
            if turn.get("voice_s") is not None:
                turn["total_s"] = turn["ears_s"] + turn["brain_s"] + turn["voice_s"]
            data["turns"].append(turn)

        for sc in scripted:
            persona = PERSONAS[sc.persona]
            print(f"  typed: {sc.key}")
            history: list[dict] = []
            for i, said in enumerate((None, *sc.turns)):
                turn = {
                    "kind": "opener" if said is None else "typed",
                    "scenario": sc.key,
                    "persona_name": persona.name,
                    "expect": sc.expect,
                    "said": said,
                }
                try:
                    answer = brain.respond(build_messages(persona, history, said))
                except Exception as e:
                    fail(f"{model} {sc.key} turn {i}", e)
                    turn["error"] = str(e)[:300]
                    data["turns"].append(turn)
                    break
                turn.update(reply=answer.reply, corrections=answer.corrections, new_words=answer.new_words, brain_s=answer.seconds, error=answer.error)
                if answer.reply:
                    turn["voice_s"], turn["audio"] = speak(answer.reply, persona, f"{slug}-{sc.key}-{i}.wav")
                if turn.get("voice_s") is not None:
                    turn["total_s"] = turn["brain_s"] + turn["voice_s"]
                data["turns"].append(turn)
                if said is not None:
                    history.append({"role": "user", "content": said})
                history.append({"role": "assistant", "content": answer.reply or "..."})
        monitor.snapshot(f"After all turns ({model})")

    monitor.stop()
    voice.close()
    results["peaks"] = {
        "gpu_peak_mb": monitor.gpu_peak_mb,
        "gpu_total_mb": monitor.gpu_total_mb,
        "ram_peak_mb": monitor.ram_peak_mb,
        "ram_total_mb": monitor.ram_total_mb,
    }
    results["snapshots"] = monitor.snapshots
    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render(results), encoding="utf-8")

    print("\nSummary")
    for check, result, bar, passed in summary_rows(results):
        print(f"  {check}: {result} (pass bar: {bar}) -> {passed.replace('*', '')}")
    print(f"\nReport: {out_dir / 'report.md'}")
    print(f"Audio to listen to: {audio_dir}")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")  # Vietnamese text in the Windows console

    parser = argparse.ArgumentParser(prog="python -m step0", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="check what's installed")
    check.add_argument("--models", default=DEFAULT_MODEL)
    check.set_defaults(func=cmd_check)

    record = sub.add_parser("record", help="record the spoken test prompts")
    record.set_defaults(func=cmd_record)

    run = sub.add_parser("run", help="run every test and write a report")
    run.add_argument("--models", default=DEFAULT_MODEL, help="comma-separated Ollama models to compare, e.g. qwen3:8b,qwen3:4b")
    run.add_argument("--ears-model", default=DEFAULT_EARS)
    run.add_argument("--ears-device", default="cuda", choices=["cuda", "cpu"])
    run.add_argument("--tts-device", default="cpu", choices=["cpu", "cuda"])
    run.add_argument("--max-wait", type=float, default=15.0, help="speed pass bar in seconds (median per turn)")
    run.add_argument("--only", choices=["typed", "spoken"], help="run only one kind of test")
    run.add_argument("--limit", type=int, default=0, help="run only the first N typed conversations")
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
