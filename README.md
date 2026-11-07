# VietTime

A private iPhone app for practicing Southern (Saigon) Vietnamese by talking out loud. It runs for free on a home PC: an iPhone app records you, and three local models on the PC hear you, reply as a Southern-speaking tutor who quietly corrects you, and speak the reply.

The full plan, including phases, personas and architecture, is in the [Vietnamese Trainer Plan](https://claude.ai/artifact/H9qd9t5zZh54ZzNRLCtCJ6).

## Where things are

| Folder | What |
| --- | --- |
| [`app/`](app/) | The iPhone app (Expo). Push to talk, replies with audio, recap, history. |
| [`server/`](server/) | The PC server: ears, brain and voice behind a small HTTP API, plus a practice mode with no models |
| [`spike/`](spike/) | Step 0: a test run proving the three models fit and perform on the PC |

## Try it

1. Set up the server and start it in practice mode: [server/README.md](server/README.md).
2. Set up the app and open it on your iPhone with Expo Go: [app/README.md](app/README.md).
3. Once Step 0 passes, restart the server without `--fake` for the real models.
