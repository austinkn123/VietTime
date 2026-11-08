"""Turns a run's results into report.md: the summary Austin reads and the transcripts Claude reviews."""

from statistics import median


def _cell(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", "<br>")


def _fixes(turn: dict) -> str:
    parts = [f"{c.get('said', '')} → **{c.get('better', '')}** ({c.get('why_en', '')})" for c in turn.get("corrections", [])]
    parts += [f"new: **{w.get('word', '')}** = {w.get('meaning_en', '')}" for w in turn.get("new_words", [])]
    return "<br>".join(_cell(p) for p in parts) or "none"


def _secs(*values) -> str:
    return " / ".join("–" if v is None else f"{v:.1f}" for v in values)


def speed_stats(turns: list[dict], kind: str) -> tuple[float, float, int] | None:
    totals = [t["total_s"] for t in turns if t["kind"] == kind and t.get("total_s") is not None]
    if not totals:
        return None
    return median(totals), max(totals), len(totals)


def summary_rows(results: dict) -> list[tuple[str, str, str, str]]:
    max_wait = results["config"]["max_wait"]
    rows = []
    peaks = results["peaks"]
    oom = [e for e in results["errors"] if e.get("oom")]
    gpu = (
        f"peak GPU {peaks['gpu_peak_mb']} / {peaks['gpu_total_mb']} MB"
        if peaks.get("gpu_total_mb")
        else "GPU not measured (nvidia-smi missing)"
    )
    shares = ", ".join(
        f"{m}: {s * 100:.0f}% on GPU" for m, d in results["models"].items() if (s := d.get("gpu_share")) is not None
    )
    fit = f"{gpu}; peak RAM {peaks['ram_peak_mb']} / {peaks['ram_total_mb']} MB; {len(oom)} out-of-memory errors"
    if shares:
        fit += f"; brain {shares}"
    # Ollama quietly moves layers to the CPU when VRAM runs out, which slows every reply.
    offloaded = any((d.get("gpu_share") or 1) < 0.99 for d in results["models"].values())
    rows.append(("Fit", fit, "No crashes; brain fully on GPU", "yes" if not oom and not offloaded else "**no**"))

    for model, data in results["models"].items():
        for kind, label in (("spoken", "spoken turns"), ("typed", "typed turns")):
            stats = speed_stats(data["turns"], kind)
            if stats:
                med, worst, n = stats
                rows.append(
                    (
                        f"Speed, {label} ({model})",
                        f"median {med:.1f} s, worst {worst:.1f} s over {n} turns",
                        f"median ≤ {max_wait:g} s",
                        "yes" if med <= max_wait else "**no**",
                    )
                )
        replies = [t for t in data["turns"] if t["kind"] != "opener"]
        bad = [t for t in replies if t.get("error")]
        rows.append(
            (
                f"Valid replies ({model})",
                f"{len(replies) - len(bad)} of {len(replies)}",
                "all",
                "yes" if not bad else "**no**",
            )
        )
    rows.append(("Quality", "Listen to the audio files and read the tables below", "Natural Southern; correct fixes", "Austin: ☐  Claude: pending"))
    rows.append(("English mixing", "See the spoken turns below", "Understood well enough to reply", "Claude: pending"))
    return rows


def render(results: dict) -> str:
    cfg = results["config"]
    lines = [
        f"# Step 0 results, {results['started'][:16].replace('T', ' ')}",
        "",
        f"GPU: {results['machine'].get('gpu') or 'unknown'} · Ears: `{cfg['ears_model']}` on {cfg['ears_device']} · "
        f"Voice: VieNeu v3 Turbo on {cfg['tts_device']} · Brain: {', '.join(f'`{m}`' for m in cfg['models'])}",
        "",
        "## Summary",
        "",
        "| Check | Result | Pass bar | Pass? |",
        "| --- | --- | --- | --- |",
        *(f"| {' | '.join(_cell(c) for c in row)} |" for row in summary_rows(results)),
        "",
        "## Load times and memory",
        "",
        "| Step | GPU used (MB) | RAM used (MB) | Seconds |",
        "| --- | --- | --- | --- |",
        *(
            f"| {_cell(s['label'])} | {s.get('gpu_used_mb', '–')} | {s.get('ram_used_mb', '–')} | "
            f"{_secs(s.get('seconds')) if 'seconds' in s else ''} |"
            for s in results["snapshots"]
        ),
    ]
    if results["errors"]:
        lines += ["", "## Errors", ""]
        lines += [f"- {_cell(e['where'])}: {_cell(e['message'])}" for e in results["errors"]]

    for model, data in results["models"].items():
        lines += ["", f"## Brain: `{model}`"]
        spoken = [t for t in data["turns"] if t["kind"] == "spoken"]
        if spoken:
            lines += [
                "",
                "### Spoken turns (your recordings)",
                "",
                "Times are ears / brain / voice / total seconds.",
                "",
                "| Prompt | Heard | Tutor reply | Fixes | Times | Audio | Sounds Southern? |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
            for t in spoken:
                lines.append(
                    f"| {_cell(t['prompt'])} | {_cell(t.get('heard'))} | {_cell(t.get('reply') or t.get('error'))} | "
                    f"{_fixes(t)} | {_secs(t.get('ears_s'), t.get('brain_s'), t.get('voice_s'), t.get('total_s'))} | "
                    f"{_cell(t.get('audio'))} |  |"
                )
        typed = [t for t in data["turns"] if t["kind"] in ("opener", "typed")]
        scenarios = list(dict.fromkeys(t["scenario"] for t in typed))
        if scenarios:
            lines += ["", "### Typed conversations", "", "Times are brain / voice / total seconds."]
        for key in scenarios:
            turns = [t for t in typed if t["scenario"] == key]
            first = turns[0]
            lines += [
                "",
                f"#### {key} · {first['persona_name']} · should fix: {first['expect']}",
                "",
                "| Austin | Tutor reply | Fixes | Times | Audio | Sounds Southern? |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for t in turns:
                said = "(tutor opens)" if t["kind"] == "opener" else t["said"]
                lines.append(
                    f"| {_cell(said)} | {_cell(t.get('reply') or t.get('error'))} | {_fixes(t)} | "
                    f"{_secs(t.get('brain_s'), t.get('voice_s'), t.get('total_s'))} | {_cell(t.get('audio'))} |  |"
                )
    lines.append("")
    return "\n".join(lines)
