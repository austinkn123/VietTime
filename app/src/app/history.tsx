import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';

import { Button, Notice } from '@/components/ui';
import type { Session } from '@/lib/api';
import { useSettings } from '@/lib/settings';
import { colors, radius, space } from '@/theme';

export default function History() {
  const { api } = useSettings();
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.sessions().then(setSessions, (e: Error) => setError(e.message));
  }, [api]);

  useFocusEffect(load);

  if (error) {
    return (
      <View style={styles.page}>
        <Notice kind="error">{error}</Notice>
        <Button title="Try again" onPress={load} style={{ marginTop: space.md }} />
      </View>
    );
  }
  if (!sessions) return <ActivityIndicator style={{ marginTop: 48 }} color={colors.accent} />;

  return (
    <FlatList
      contentContainerStyle={styles.page}
      data={sessions}
      keyExtractor={(s) => String(s.id)}
      ItemSeparatorComponent={() => <View style={{ height: space.sm }} />}
      ListEmptyComponent={<Text style={styles.empty}>No conversations yet.</Text>}
      renderItem={({ item: s }) => (
        <Pressable
          style={({ pressed }) => [styles.card, pressed && { opacity: 0.75 }]}
          onPress={() => router.push({ pathname: '/session/[id]', params: { id: String(s.id) } })}
        >
          <Text style={styles.name}>{s.persona.name}</Text>
          <Text style={styles.sub}>
            {s.persona.topic} · {new Date(s.started_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
            {' · '}
            {s.turn_count} lines
          </Text>
        </Pressable>
      )}
    />
  );
}

const styles = StyleSheet.create({
  page: { padding: space.lg },
  empty: { fontSize: 16, color: colors.muted, textAlign: 'center', marginTop: space.xl },
  card: { backgroundColor: colors.surface, borderRadius: radius.md, padding: space.lg, borderWidth: 1, borderColor: colors.line },
  name: { fontSize: 18, fontWeight: '700', color: colors.ink },
  sub: { fontSize: 15, color: colors.muted, marginTop: 2 },
});
