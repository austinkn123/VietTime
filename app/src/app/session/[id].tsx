import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';

import { LearnerBubble, TutorBubble } from '@/components/Bubble';
import { Button, ExplainToggle, Notice, PlayButton, SectionTitle } from '@/components/ui';
import type { Correction, Transcript } from '@/lib/api';
import { useConversationAudioMode, usePlayer } from '@/lib/audio';
import { useSettings, type ExplainIn } from '@/lib/settings';
import { colors, radius, space } from '@/theme';

export default function SessionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { api, explainIn, setExplainIn } = useSettings();
  const player = usePlayer();
  useConversationAudioMode();
  const [data, setData] = useState<Transcript | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [speaking, setSpeaking] = useState<string | null>(null); // text being turned into audio
  const [spoken, setSpoken] = useState<Record<string, string>>({}); // text -> audio url

  const load = useCallback(() => {
    setError(null);
    api.session(Number(id)).then(setData, (e: Error) => setError(e.message));
  }, [api, id]);

  useEffect(load, [load]);

  const say = async (text: string) => {
    if (!data) return;
    const url = spoken[text];
    if (url) return player.playingUrl === url ? player.stop() : player.play(url);
    setSpeaking(text);
    try {
      const { audio_url } = await api.speak(text, data.session.persona.key);
      const full = api.audioUrl(audio_url);
      setSpoken((s) => ({ ...s, [text]: full }));
      player.play(full);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSpeaking(null);
    }
  };

  if (error && !data) {
    return (
      <View style={styles.page}>
        <Notice kind="error">{error}</Notice>
        <Button title="Try again" onPress={load} style={{ marginTop: space.md }} />
      </View>
    );
  }
  if (!data) return <ActivityIndicator style={{ marginTop: 48 }} color={colors.accent} />;

  const { session, recap, turns } = data;
  const sound = (text: string) => ({
    playing: !!spoken[text] && player.playingUrl === spoken[text],
    busy: speaking === text,
    onPress: () => say(text),
    label: `Hear “${text}”`,
  });

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Stack.Screen options={{ title: session.persona.name }} />
      <Text style={styles.meta}>
        {capitalize(session.persona.topic)} · {formatDate(session.started_at)} · you talked {recap.learner_turns} {recap.learner_turns === 1 ? 'time' : 'times'}
      </Text>
      {error && <Notice kind="error">{error}</Notice>}

      <SectionTitle>Say it better</SectionTitle>
      {recap.corrections.length === 0 ? (
        <Text style={styles.empty}>No corrections this time.</Text>
      ) : (
        <>
          <ExplainToggle value={explainIn} onChange={setExplainIn} />
          <View style={{ gap: space.sm, marginTop: space.md }}>
            {recap.corrections.map((c, i) => (
              <CorrectionCard key={i} c={c} explainIn={explainIn} sound={sound(c.better)} />
            ))}
          </View>
        </>
      )}

      <SectionTitle>New words</SectionTitle>
      {recap.new_words.length === 0 ? (
        <Text style={styles.empty}>No new words this time. Ask “How do you say…?” in English to get some.</Text>
      ) : (
        <View style={{ gap: space.sm }}>
          {recap.new_words.map((w) => (
            <View key={w.word} style={styles.card}>
              <View style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.word}>{w.word}</Text>
                  <Text style={styles.meaning}>{w.meaning_en}</Text>
                </View>
                <PlayButton {...sound(w.word)} />
              </View>
            </View>
          ))}
        </View>
      )}

      <SectionTitle>Conversation</SectionTitle>
      <View style={{ gap: space.md }}>
        {turns.map((t, i) =>
          t.role === 'learner' ? <LearnerBubble key={i} text={t.text} /> : <TutorBubble key={i} name={session.persona.name} text={t.text} />,
        )}
      </View>

      <Button
        title={`Talk with ${session.persona.name} again`}
        style={{ marginTop: space.xl }}
        onPress={() => router.replace({ pathname: '/talk/[topic]', params: { topic: session.persona.key } })}
      />
    </ScrollView>
  );
}

function CorrectionCard({ c, explainIn, sound }: { c: Correction; explainIn: ExplainIn; sound: React.ComponentProps<typeof PlayButton> }) {
  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={styles.label}>You said</Text>
          <Text style={styles.said}>{c.said}</Text>
          <Text style={[styles.label, { marginTop: space.sm }]}>Better</Text>
          <Text style={styles.better}>{c.better}</Text>
        </View>
        <PlayButton {...sound} />
      </View>
      {(explainIn === 'en' || explainIn === 'both') && c.why_en ? <Text style={styles.why}>{c.why_en}</Text> : null}
      {(explainIn === 'vi' || explainIn === 'both') && c.why_vi ? <Text style={styles.why}>{c.why_vi}</Text> : null}
      {c.in ? <Text style={styles.context}>From: “{c.in}”</Text> : null}
    </View>
  );
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function formatDate(iso: string) {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

const styles = StyleSheet.create({
  page: { padding: space.lg, paddingBottom: 48 },
  meta: { fontSize: 15, color: colors.muted, marginBottom: space.sm },
  empty: { fontSize: 15, color: colors.muted, lineHeight: 21 },
  card: { backgroundColor: colors.surface, borderRadius: radius.md, padding: space.lg, borderWidth: 1, borderColor: colors.line, gap: space.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  label: { fontSize: 12, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', letterSpacing: 0.5 },
  said: { fontSize: 18, color: colors.muted, textDecorationLine: 'line-through' },
  better: { fontSize: 20, fontWeight: '700', color: colors.accent },
  why: { fontSize: 15, color: colors.ink, lineHeight: 21 },
  context: { fontSize: 13, color: colors.muted, fontStyle: 'italic' },
  word: { fontSize: 20, fontWeight: '700', color: colors.ink },
  meaning: { fontSize: 15, color: colors.muted, marginTop: 2 },
});
