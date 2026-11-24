import { getRecordingPermissionsAsync, requestRecordingPermissionsAsync, useAudioRecorder } from 'expo-audio';
import * as Haptics from 'expo-haptics';
import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View, type ScrollViewInstance } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { LearnerBubble, ThinkingBubble, TutorBubble } from '@/components/Bubble';
import { TalkButton, type TalkPhase } from '@/components/TalkButton';
import { Button, Notice } from '@/components/ui';
import type { ApiError, Session, Turn } from '@/lib/api';
import { MAX_RECORDING_MS, MIN_RECORDING_MS, useConversationAudioMode, usePlayer, WAV_16K } from '@/lib/audio';
import { useSettings } from '@/lib/settings';
import { colors, radius, space } from '@/theme';

const OPENER_DELAY_MS = 3_000; // the tutor speaks first unless Austin presses talk before this

type Item =
  | { key: string; role: 'learner'; text: string; typed: boolean }
  | { key: string; role: 'tutor'; text: string; audioUrl: string | null; voiceError: string | null };

type Pending = { kind: 'open' } | { kind: 'audio'; uri: string } | { kind: 'text'; text: string };

type LastTurn = { timings: Record<string, number>; roundTrip: number };

// Why a press on the talk button didn't start recording, so a tap is never silently ignored.
const NOT_READY: Partial<Record<TalkPhase, string>> = {
  starting: 'Still connecting to your PC. One sec.',
  thinking: 'Wait for the reply first. Your PC is still working on it.',
  failed: "Not connected to your PC, so the mic can't send anything. Go back and check the server window.",
};

export default function Talk() {
  const { topic } = useLocalSearchParams<{ topic: string }>();
  const { api } = useSettings();
  const insets = useSafeAreaInsets();
  const recorder = useAudioRecorder(WAV_16K);
  const player = usePlayer();
  useConversationAudioMode();

  const [session, setSession] = useState<Session | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [phase, setPhaseState] = useState<TalkPhase>('starting');
  const [seconds, setSeconds] = useState(0);
  const [hint, setHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [practiceMode, setPracticeMode] = useState(false);
  const [typing, setTyping] = useState(Platform.OS === 'web');
  const [draft, setDraft] = useState('');
  const [ending, setEnding] = useState(false);
  const [pendingKind, setPendingKind] = useState<Pending['kind'] | null>(null);
  const [lastTurn, setLastTurn] = useState<LastTurn | null>(null);

  // Refs, because press handlers and timers outlive the render that created them.
  const phaseRef = useRef<TalkPhase>('starting');
  const sessionRef = useRef<Session | null>(null);
  const pressing = useRef(false);
  const phaseStarted = useRef(Date.now());
  const recordStarted = useRef(0);
  const openerTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const failed = useRef<Pending | null>(null);
  const turns = useRef(0);
  const scroll = useRef<ScrollViewInstance>(null);

  const setPhase = (p: TalkPhase) => {
    phaseRef.current = p;
    phaseStarted.current = Date.now();
    setSeconds(0);
    setPhaseState(p);
  };

  const clearOpener = () => {
    if (openerTimer.current) clearTimeout(openerTimer.current);
    openerTimer.current = null;
  };
  const clearMax = () => {
    if (maxTimer.current) clearTimeout(maxTimer.current);
    maxTimer.current = null;
  };

  // Seconds counter while listening or thinking.
  useEffect(() => {
    if (phase !== 'recording' && phase !== 'thinking') return;
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - phaseStarted.current) / 1000)), 250);
    return () => clearInterval(id);
  }, [phase]);

  // Start a conversation; the tutor opens after a short pause.
  useEffect(() => {
    let cancelled = false;
    // Ask for the mic now, so the first press records instead of only showing the permission prompt.
    if (Platform.OS !== 'web') {
      requestRecordingPermissionsAsync().then(
        (p) => !cancelled && !p.granted && setError('The microphone is off. Turn it on in iPhone Settings → Expo Go → Microphone.'),
        () => {},
      );
    }
    api.health().then((h) => !cancelled && setPracticeMode(h.mode === 'fake'), () => {});
    api.newSession(topic === 'surprise' ? null : (topic ?? null)).then(
      (s) => {
        if (cancelled) return;
        sessionRef.current = s;
        setSession(s);
        setPhase('ready');
        setHint(`${s.persona.name} will start in a moment, or hold the button and talk first.`);
        openerTimer.current = setTimeout(() => {
          if (turns.current === 0 && phaseRef.current === 'ready') runTurn({ kind: 'open' });
        }, OPENER_DELAY_MS);
      },
      (e: Error) => {
        if (cancelled) return;
        setError(e.message);
        setPhase('failed');
      },
    );
    return () => {
      cancelled = true;
      clearOpener();
      clearMax();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runTurn(pending: Pending) {
    const s = sessionRef.current;
    if (!s) return;
    clearOpener();
    setPendingKind(pending.kind);
    setPhase('thinking');
    setHint(null);
    setError(null);
    const sentAt = Date.now();
    try {
      let turn: Turn;
      if (pending.kind === 'open') turn = await api.open(s.id);
      else if (pending.kind === 'audio') turn = await api.sendAudio(s.id, pending.uri);
      else turn = await api.sendText(s.id, pending.text);

      failed.current = null;
      turns.current += 1;
      setLastTurn({ timings: turn.timings, roundTrip: (Date.now() - sentAt) / 1000 });
      const audioUrl = turn.audio_url ? api.audioUrl(turn.audio_url) : null;
      const key = String(turn.turn_id);
      setItems((prev) => [
        ...prev,
        ...(turn.heard ? [{ key: `${key}-heard`, role: 'learner' as const, text: turn.heard, typed: pending.kind === 'text' }] : []),
        { key, role: 'tutor', text: turn.reply, audioUrl, voiceError: turn.voice_error },
      ]);
      if (audioUrl) player.play(audioUrl);
    } catch (e) {
      const err = e as ApiError;
      if (pending.kind === 'open' && err.status === 409) {
        // Austin started talking first; nothing to do.
      } else if (err.status === 422) {
        setHint(err.message); // didn't catch anything; just try again
      } else {
        failed.current = pending;
        setError(err.message);
      }
    } finally {
      setPhase('ready');
    }
  }

  async function onPressIn() {
    if (phaseRef.current !== 'ready' || !sessionRef.current) {
      const why = NOT_READY[phaseRef.current];
      if (why) setHint(why);
      return;
    }
    pressing.current = true;
    clearOpener();
    player.stop();
    setHint(null);
    setError(null);

    const perm = await getRecordingPermissionsAsync();
    if (!perm.granted) {
      const asked = await requestRecordingPermissionsAsync();
      setHint(asked.granted ? 'Microphone is on. Hold the button while you talk.' : null);
      if (!asked.granted) setError('The microphone is off. Turn it on in iPhone Settings → Expo Go → Microphone.');
      return;
    }

    setPhase('arming');
    try {
      await recorder.prepareToRecordAsync();
      if (!pressing.current) {
        setPhase('ready');
        setHint('Hold the button the whole time you talk, then let go.');
        return;
      }
      recorder.record();
    } catch (e) {
      setPhase('ready');
      setError(`Couldn't start recording: ${(e as Error).message}`);
      return;
    }
    recordStarted.current = Date.now();
    setPhase('recording');
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
    maxTimer.current = setTimeout(finishRecording, MAX_RECORDING_MS);
  }

  function onPressOut() {
    pressing.current = false;
    if (phaseRef.current === 'recording') finishRecording();
  }

  async function finishRecording() {
    if (phaseRef.current !== 'recording') return;
    clearMax();
    setPendingKind('audio');
    setPhase('thinking');
    const heldMs = Date.now() - recordStarted.current;
    try {
      await recorder.stop();
    } catch {}
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    const uri = recorder.uri;
    if (heldMs < MIN_RECORDING_MS || !uri) {
      setPhase('ready');
      setHint('Hold the button the whole time you talk, then let go.');
      return;
    }
    await runTurn({ kind: 'audio', uri });
  }

  function sendTyped() {
    const text = draft.trim();
    if (!text || phaseRef.current !== 'ready') return;
    setDraft('');
    runTurn({ kind: 'text', text });
  }

  async function end() {
    if (ending) return;
    clearOpener();
    clearMax();
    player.stop();
    if (phaseRef.current === 'recording') {
      try {
        await recorder.stop();
      } catch {}
    }
    const s = sessionRef.current;
    if (!s) return router.back();
    setEnding(true);
    try {
      await api.end(s.id);
    } catch (e) {
      setEnding(false);
      if (turns.current === 0) return router.back();
      setError(`Couldn't end the conversation: ${(e as Error).message}`);
      return;
    }
    if (turns.current === 0) return router.back();
    router.replace({ pathname: '/session/[id]', params: { id: String(s.id) } });
  }

  const persona = session?.persona;
  const playing = player.playingUrl !== null;
  const status = statusLine(phase, seconds, pendingKind, playing, persona?.name ?? 'The tutor');

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={100}>
      <Stack.Screen
        options={{
          title: persona?.name ?? '',
          headerBackVisible: false,
          headerRight: () => (
            <Pressable onPress={end} hitSlop={12} accessibilityRole="button">
              <Text style={styles.end}>{ending ? 'Ending…' : 'End'}</Text>
            </Pressable>
          ),
        }}
      />

      {practiceMode && (
        <View style={styles.fake}>
          <Text style={styles.fakeTitle}>PRACTICE MODE: no real models</Text>
          <Text style={styles.fakeSub}>
            The server was started with --fake. It ignores your voice, answers with canned lines, and beeps instead of speaking. Restart it without --fake for the
            real thing.
          </Text>
        </View>
      )}

      <ScrollView
        ref={scroll}
        contentContainerStyle={styles.chat}
        onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}
        keyboardShouldPersistTaps="handled"
      >
        {persona && (
          <View style={styles.intro}>
            <Text style={styles.introTitle}>
              {persona.name}, {persona.description}
            </Text>
            <Text style={styles.introSub}>
              You say “{persona.austin_calls_them}” and call yourself “{persona.austin_self}”. English is fine when you're stuck, like “How do you say…?”
            </Text>
          </View>
        )}
        {items.map((it) =>
          it.role === 'learner' ? (
            <LearnerBubble key={it.key} text={it.text} typed={it.typed} fake={practiceMode} />
          ) : (
            <TutorBubble
              key={it.key}
              name={persona?.name ?? ''}
              text={it.text}
              note={it.voiceError ? 'No audio this time (the voice failed on the PC).' : null}
              playing={!!it.audioUrl && player.playingUrl === it.audioUrl}
              onPlay={it.audioUrl ? () => (player.playingUrl === it.audioUrl ? player.stop() : player.play(it.audioUrl!)) : undefined}
            />
          ),
        )}
        {phase === 'thinking' && persona && <ThinkingBubble name={persona.name} />}
      </ScrollView>

      <View style={[styles.bottom, { paddingBottom: Math.max(insets.bottom, space.lg) }]}>
        <View style={styles.status} accessibilityLiveRegion="polite">
          <Text style={styles.statusNow}>{status}</Text>
          {lastTurn && <Text style={styles.statusLast}>{formatLastTurn(lastTurn)}</Text>}
        </View>
        {hint && <Text style={styles.hint}>{hint}</Text>}
        {error && (
          <View style={{ gap: space.sm, alignSelf: 'stretch' }}>
            <Notice kind="error">{error}</Notice>
            {failed.current && phase === 'ready' && <Button title="Try again" kind="secondary" onPress={() => failed.current && runTurn(failed.current)} />}
            {phase === 'failed' && <Button title="Back" kind="secondary" onPress={() => router.back()} />}
          </View>
        )}

        {typing && (
          <View style={styles.typeRow}>
            <TextInput
              value={draft}
              onChangeText={setDraft}
              placeholder="Type instead (Vietnamese or English)"
              style={styles.input}
              returnKeyType="send"
              onSubmitEditing={sendTyped}
              editable={phase === 'ready'}
            />
            <Button title="Send" onPress={sendTyped} disabled={!draft.trim() || phase !== 'ready'} />
          </View>
        )}

        {Platform.OS !== 'web' && <TalkButton phase={phase} seconds={seconds} onPressIn={onPressIn} onPressOut={onPressOut} />}

        {Platform.OS !== 'web' && (
          <Pressable onPress={() => setTyping((t) => !t)} hitSlop={8}>
            <Text style={styles.toggle}>{typing ? 'Hide typing' : 'Type instead'}</Text>
          </Pressable>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

/** One line that always says what the app is doing right now. */
function statusLine(phase: TalkPhase, seconds: number, pending: Pending['kind'] | null, playing: boolean, name: string): string {
  switch (phase) {
    case 'starting':
      return 'Connecting to your PC…';
    case 'arming':
      return 'Turning on the mic…';
    case 'recording':
      return `Recording ${seconds}s. Let go to send.`;
    case 'thinking': {
      const steps = pending === 'audio' ? 'sending your voice → ears → brain → voice' : 'brain → voice';
      return `Your PC is working (${steps}) ${seconds}s`;
    }
    case 'failed':
      return 'Not connected to your PC.';
    case 'ready':
      return playing ? `Playing ${name}'s reply. Hold the button to cut in.` : 'Ready. Hold the button and talk.';
  }
}

/** The server's per-step seconds, plus the full wait on the phone; the gap is the Wi-Fi. */
function formatLastTurn({ timings, roundTrip }: LastTurn): string {
  const parts = (['ears', 'brain', 'voice'] as const).filter((k) => timings[k] !== undefined).map((k) => `${k} ${timings[k].toFixed(1)}s`);
  const wifi = Math.max(0, roundTrip - (timings.total ?? 0));
  return `Last turn: ${parts.join(' · ')} · Wi-Fi ${wifi.toFixed(1)}s · total ${roundTrip.toFixed(1)}s`;
}

const styles = StyleSheet.create({
  fake: { backgroundColor: colors.warnSoft, borderBottomWidth: 2, borderBottomColor: colors.warn, padding: space.md, gap: 2 },
  fakeTitle: { color: colors.warn, fontSize: 15, fontWeight: '800' },
  fakeSub: { color: colors.warn, fontSize: 13, lineHeight: 18 },
  status: { alignSelf: 'stretch', alignItems: 'center', gap: 2 },
  statusNow: { fontSize: 15, fontWeight: '600', color: colors.ink, textAlign: 'center' },
  statusLast: { fontSize: 12, color: colors.muted, textAlign: 'center' },
  end: { color: colors.danger, fontSize: 17, fontWeight: '600' },
  chat: { padding: space.lg, gap: space.md },
  intro: { backgroundColor: colors.surface, borderRadius: radius.md, padding: space.md, borderWidth: 1, borderColor: colors.line },
  introTitle: { fontSize: 16, fontWeight: '600', color: colors.ink },
  introSub: { fontSize: 14, color: colors.muted, marginTop: 4, lineHeight: 20 },
  bottom: { alignItems: 'center', gap: space.md, paddingHorizontal: space.lg, paddingTop: space.md, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: colors.bg },
  hint: { fontSize: 15, color: colors.muted, textAlign: 'center' },
  typeRow: { flexDirection: 'row', gap: space.sm, alignSelf: 'stretch' },
  input: { flex: 1, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line, borderRadius: radius.md, paddingHorizontal: space.md, fontSize: 17, color: colors.ink, minHeight: 50 },
  toggle: { fontSize: 15, color: colors.accent, fontWeight: '600' },
});
