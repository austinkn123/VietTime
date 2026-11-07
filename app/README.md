# iPhone app

The app you talk to. It runs inside **Expo Go**, a free app from the App Store, and loads from your PC while you practice. The [server](../server) does the listening, thinking and speaking.

## Setup (one time)

1. On the PC, install [Node.js LTS](https://nodejs.org/).
2. On the iPhone, install **Expo Go** from the App Store.
3. In Command Prompt:
   ```
   cd VietTime\app
   npm install
   ```

## Run it

You need two Command Prompt windows on the PC, and the phone on the same Wi-Fi.

1. **Window 1, the server** (see [server/README.md](../server/README.md)):
   ```
   cd VietTime\server
   .venv\Scripts\activate
   python -m viettime_server --fake
   ```
   Drop `--fake` once you want the real models.
2. **Window 2, the app:**
   ```
   cd VietTime\app
   npx expo start
   ```
   It shows a QR code. Scan it with the iPhone's Camera app, and it opens in Expo Go.
3. The first time, Windows asks whether Node.js may use the network: allow it on **Private networks**. Then allow the microphone when the app asks.

The app guesses the server's address from the PC it loaded from. If the home screen says it can't reach the server, open **Settings**, type the address the server window printed (like `http://192.168.1.20:8000`), and tap **Save and test**.

## Using it

- Pick a topic, or **Surprise me** for someone different from last time.
- The tutor starts talking after about 3 seconds. To go first, hold the button before then.
- **Hold** the big button while you talk and **let go** to send. You'll see what it heard, then the reply plays out loud. Tap ▶ to hear a reply again.
- Stuck on a word? Ask in English: "How do you say deadline?"
- **Type instead** under the button lets you type a turn.
- **End** shows the recap: what to say better (with the reason in English, Vietnamese or both) and new words. Tap ▶ to hear any of them.
- **History** on the home screen has every past conversation and its recap.

## Limits for now

- It works only on your home Wi-Fi, with both windows running on the PC.
- It opens through Expo Go rather than as its own app icon. Installing it as a standalone app needs either a Mac or a paid Apple developer account, so that's not set up.
- If Expo Go says the project needs a newer or older SDK, update Expo Go from the App Store.

## For development

```
npm run typecheck   # TypeScript check
npm run web         # opens in a browser; typing only, no voice
```

Screens are in `src/app` (Expo Router), the server client is `src/lib/api.ts`, and recording and playback are in `src/lib/audio.ts`.
