"""Start the VietTime server on this PC.

    python -m viettime_server          # the real models (ears, brain, voice)
    python -m viettime_server --fake   # no models: canned replies and beeps, to test the app
"""

import argparse
import shutil
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BRAIN = "qwen3:8b"
DEFAULT_EARS = "vinai/PhoWhisper-medium"


def lan_ip() -> str:
    """This PC's address on the home network (no traffic is sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def load_engines(args):
    if args.fake:
        from .fakes import FakeBrain, FakeEars, FakeVoice

        info = {"mode": "fake", "brain": "fake", "ears": "fake", "voice": "beeps"}
        return FakeEars(), FakeBrain(delay=args.fake_delay), FakeVoice(), info

    from .engines import Brain, Ears, Voice

    def step(label, fn):
        print(f"Loading {label}...", flush=True)
        start = time.perf_counter()
        result = fn()
        print(f"  ready in {time.perf_counter() - start:.0f} s", flush=True)
        return result

    voice = step(f"voice (VieNeu-TTS on {args.tts_device})", lambda: Voice(args.tts_device))
    ears = step(f"ears ({args.ears_model} on {args.ears_device})", lambda: Ears(args.ears_model, args.ears_device))
    brain = Brain(args.brain, host=args.ollama)
    try:
        step(f"brain ({args.brain} through Ollama)", brain.warm)
    except Exception as e:
        sys.exit(f"Couldn't reach the brain: {e}\nOpen the Ollama app, and run `ollama pull {args.brain}` if you haven't.")
    share = brain.gpu_share()
    if share is not None and share < 0.99:
        print(f"  warning: only {share:.0%} of the brain fits on the GPU, so replies will be slow")
    info = {"mode": "real", "brain": args.brain, "ears": args.ears_model, "voice": "VieNeu-TTS v3 Turbo"}
    return ears, brain, voice, info


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")  # Vietnamese text in the Windows console

    parser = argparse.ArgumentParser(prog="python -m viettime_server", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fake", action="store_true", help="no models: canned replies and beeps, to test the app")
    parser.add_argument("--fake-delay", type=float, default=1.0, help="seconds the fake brain pretends to think")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--brain", default=DEFAULT_BRAIN, help="Ollama model, e.g. qwen3:8b or qwen3:4b")
    parser.add_argument("--ollama", default="http://127.0.0.1:11434")
    parser.add_argument("--ears-model", default=DEFAULT_EARS)
    parser.add_argument("--ears-device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--tts-device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--data", type=Path, default=ROOT / "data", help="where history and reply audio are kept")
    args = parser.parse_args(argv)

    import uvicorn

    from .api import create_app
    from .store import Store
    from .tutor import Tutor

    args.data.mkdir(parents=True, exist_ok=True)
    audio_dir = args.data / "audio"
    shutil.rmtree(audio_dir, ignore_errors=True)  # reply audio is only needed while it plays

    ears, brain, voice, info = load_engines(args)
    tutor = Tutor(ears, brain, voice, Store(args.data / "viettime.db"), audio_dir)
    app = create_app(tutor, info)

    print()
    print(f"VietTime server is running ({'practice mode, no models' if args.fake else 'real models'}).")
    print(f"In the app's Settings, the server address is:  http://{lan_ip()}:{args.port}")
    print("Leave this window open. Ctrl+C stops it.\n")
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    finally:
        voice.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
