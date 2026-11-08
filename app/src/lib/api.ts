// Client for the VietTime server running on the PC (server/viettime_server/api.py).

import { File } from 'expo-file-system';

export type Persona = {
  key: string;
  topic: string;
  name: string;
  description: string;
  austin_calls_them: string;
  austin_self: string;
};

export type Correction = {
  said: string;
  better: string;
  why_en: string;
  why_vi: string;
  in?: string | null; // the whole sentence it came from (recap only)
};

export type NewWord = { word: string; meaning_en: string };

export type Turn = {
  heard: string | null;
  reply: string;
  audio_url: string | null;
  voice_error: string | null;
  corrections: Correction[];
  new_words: NewWord[];
  timings: Record<string, number>;
  turn_id: number;
};

export type Session = {
  id: number;
  persona: Persona;
  started_at: string;
  ended_at: string | null;
  turn_count: number;
};

export type Recap = { learner_turns: number; corrections: Correction[]; new_words: NewWord[] };

export type Transcript = {
  session: Session;
  turns: { role: 'learner' | 'tutor'; text: string; created_at: string }[];
  recap: Recap;
};

export type Health = { ok: boolean; mode: 'fake' | 'real'; brain: string; ears: string; voice: string };

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number | null,
  ) {
    super(message);
  }
}

const QUICK = 10_000;
const TURN = 180_000; // the first real turn can be slow while the models warm up

export function normalizeServerUrl(raw: string): string {
  let url = raw.trim().replace(/\/+$/, '');
  if (url && !/^https?:\/\//i.test(url)) url = `http://${url}`;
  return url;
}

export function makeApi(base: string) {
  async function call<T>(path: string, init: RequestInit = {}, timeout = QUICK): Promise<T> {
    if (!base) throw new ApiError('Set the server address in Settings first.', null);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    let res: Response;
    try {
      res = await fetch(base + path, { ...init, signal: controller.signal });
    } catch (e) {
      // fetch also throws here when it can't build the request, so keep its own words for debugging.
      const why = controller.signal.aborted ? 'The server took too long to answer.' : `Can't reach the server at ${base}.`;
      const detail = controller.signal.aborted ? '' : ` (${e instanceof Error ? e.message : String(e)})`;
      throw new ApiError(`${why} Is it running on your PC, and is your phone on the same Wi-Fi?${detail}`, null);
    } finally {
      clearTimeout(timer);
    }
    if (!res.ok) {
      let detail = `The server answered ${res.status}.`;
      try {
        const body = await res.json();
        if (typeof body.detail === 'string') detail = body.detail;
      } catch {}
      throw new ApiError(detail, res.status);
    }
    return (await res.json()) as T;
  }

  const json = (body: unknown): RequestInit => ({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return {
    base,
    audioUrl: (path: string) => base + path,
    health: () => call<Health>('/api/health', {}, 5_000),
    topics: () => call<Persona[]>('/api/topics'),
    newSession: (topic: string | null) => call<Session>('/api/sessions', json({ topic })),
    open: (id: number) => call<Turn>(`/api/sessions/${id}/open`, { method: 'POST' }, TURN),
    sendText: (id: number, text: string) => call<Turn>(`/api/sessions/${id}/turns/text`, json({ text }), TURN),
    sendAudio: async (id: number, uri: string) => {
      const file = new File(uri);
      if (!file.exists || !file.size) throw new ApiError("The recording didn't save on the phone. Try again.", null);
      const form = new FormData();
      // Expo SDK 58's fetch uploads an expo-file-system File. React Native's old { uri, name, type } object
      // fails inside fetch before anything is sent.
      form.append('audio', file);
      return call<Turn>(`/api/sessions/${id}/turns`, { method: 'POST', body: form }, TURN);
    },
    end: (id: number) => call<Transcript>(`/api/sessions/${id}/end`, { method: 'POST' }),
    sessions: () => call<Session[]>('/api/sessions'),
    session: (id: number) => call<Transcript>(`/api/sessions/${id}`),
    speak: (text: string, topic: string) => call<{ audio_url: string }>('/api/speak', json({ text, topic }), 60_000),
  };
}

export type Api = ReturnType<typeof makeApi>;
