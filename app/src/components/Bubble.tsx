import { StyleSheet, Text, View } from 'react-native';

import { PlayButton } from '@/components/ui';
import { colors, radius, space } from '@/theme';

export function LearnerBubble({ text, typed }: { text: string; typed?: boolean }) {
  return (
    <View style={[styles.bubble, styles.learner]}>
      <Text style={styles.who}>{typed ? 'You (typed)' : 'You (what it heard)'}</Text>
      <Text style={styles.text}>{text}</Text>
    </View>
  );
}

export function TutorBubble({
  name,
  text,
  playing,
  onPlay,
  note,
}: {
  name: string;
  text: string;
  playing?: boolean;
  onPlay?: () => void;
  note?: string | null;
}) {
  return (
    <View style={[styles.bubble, styles.tutor]}>
      <View style={styles.row}>
        <View style={{ flex: 1 }}>
          <Text style={styles.who}>{name}</Text>
          <Text style={styles.text}>{text}</Text>
          {note ? <Text style={styles.note}>{note}</Text> : null}
        </View>
        {onPlay ? <PlayButton label={playing ? 'Stop' : 'Play again'} playing={playing} onPress={onPlay} /> : null}
      </View>
    </View>
  );
}

export function ThinkingBubble({ name }: { name: string }) {
  return (
    <View style={[styles.bubble, styles.tutor, { opacity: 0.7 }]}>
      <Text style={styles.who}>{name}</Text>
      <Text style={[styles.text, { color: colors.muted }]}>…</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bubble: { borderRadius: radius.lg, padding: space.md, maxWidth: '88%' },
  learner: { alignSelf: 'flex-end', backgroundColor: colors.accentSoft, borderBottomRightRadius: 6 },
  tutor: { alignSelf: 'flex-start', backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line, borderBottomLeftRadius: 6 },
  row: { flexDirection: 'row', gap: space.md, alignItems: 'center' },
  who: { fontSize: 13, fontWeight: '600', color: colors.muted, marginBottom: 2 },
  text: { fontSize: 19, lineHeight: 27, color: colors.ink },
  note: { fontSize: 13, color: colors.warn, marginTop: 4 },
});
