import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button, Notice, SectionTitle } from '@/components/ui';
import type { Health, Persona } from '@/lib/api';
import { useSettings } from '@/lib/settings';
import { colors, radius, space } from '@/theme';

type Load = { state: 'loading' } | { state: 'ok'; health: Health; topics: Persona[] } | { state: 'error'; message: string };

export default function Home() {
  const { api, loaded } = useSettings();
  const [load, setLoad] = useState<Load>({ state: 'loading' });

  const refresh = useCallback(() => {
    if (!loaded) return;
    setLoad({ state: 'loading' });
    Promise.all([api.health(), api.topics()])
      .then(([health, topics]) => setLoad({ state: 'ok', health, topics }))
      .catch((e: Error) => setLoad({ state: 'error', message: e.message }));
  }, [api, loaded]);

  useFocusEffect(refresh);

  const start = (topic: string) => router.push({ pathname: '/talk/[topic]', params: { topic } });

  return (
    <ScrollView contentContainerStyle={styles.page} refreshControl={<RefreshControl refreshing={false} onRefresh={refresh} />}>
      <Text style={styles.lead}>Talk out loud in Southern Vietnamese. Pick who to talk to.</Text>

      {load.state === 'loading' && <ActivityIndicator style={{ marginTop: space.xl }} color={colors.accent} />}

      {load.state === 'error' && (
        <View style={{ gap: space.md, marginTop: space.lg }}>
          <Notice kind="error">{load.message}</Notice>
          <Button title="Try again" onPress={refresh} />
          <Button title="Open Settings" kind="secondary" onPress={() => router.push('/settings')} />
        </View>
      )}

      {load.state === 'ok' && (
        <>
          {load.health.mode === 'fake' && (
            <View style={{ marginTop: space.lg }}>
              <Notice kind="warn">Practice mode: the server is using stand-ins, so replies are canned and the voice is beeps.</Notice>
            </View>
          )}

          <Pressable style={({ pressed }) => [styles.surprise, pressed && styles.pressed]} onPress={() => start('surprise')}>
            <Text style={styles.surpriseTitle}>Surprise me</Text>
            <Text style={styles.surpriseSub}>Someone different from last time</Text>
          </Pressable>

          <SectionTitle>Topics</SectionTitle>
          <View style={{ gap: space.sm }}>
            {load.topics.map((p) => (
              <Pressable key={p.key} style={({ pressed }) => [styles.card, pressed && styles.pressed]} onPress={() => start(p.key)}>
                <Text style={styles.cardTopic}>{capitalize(p.topic)}</Text>
                <Text style={styles.cardWho}>
                  {p.name}, {p.description}
                </Text>
                <Text style={styles.cardPronouns}>
                  You say “{p.austin_calls_them}” and call yourself “{p.austin_self}”
                </Text>
              </Pressable>
            ))}
          </View>
        </>
      )}

      <View style={styles.footer}>
        <Button title="History" kind="secondary" style={{ flex: 1 }} onPress={() => router.push('/history')} />
        <Button title="Settings" kind="secondary" style={{ flex: 1 }} onPress={() => router.push('/settings')} />
      </View>
    </ScrollView>
  );
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

const styles = StyleSheet.create({
  page: { padding: space.lg, paddingBottom: 48 },
  lead: { fontSize: 17, color: colors.muted, lineHeight: 24 },
  surprise: { marginTop: space.lg, backgroundColor: colors.accent, borderRadius: radius.lg, padding: space.lg },
  surpriseTitle: { color: '#fff', fontSize: 22, fontWeight: '700' },
  surpriseSub: { color: '#E6FFFA', fontSize: 15, marginTop: 2 },
  card: { backgroundColor: colors.surface, borderRadius: radius.md, padding: space.lg, borderWidth: 1, borderColor: colors.line },
  cardTopic: { fontSize: 18, fontWeight: '700', color: colors.ink },
  cardWho: { fontSize: 15, color: colors.ink, marginTop: 4 },
  cardPronouns: { fontSize: 14, color: colors.muted, marginTop: 4 },
  pressed: { opacity: 0.75 },
  footer: { flexDirection: 'row', gap: space.sm, marginTop: space.xl },
});
