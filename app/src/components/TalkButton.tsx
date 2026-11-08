import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, space } from '@/theme';

export type TalkPhase = 'starting' | 'ready' | 'arming' | 'recording' | 'thinking' | 'failed';

const LABEL: Record<TalkPhase, string> = {
  starting: 'Getting ready…',
  ready: 'Hold to talk',
  arming: 'Listening…',
  recording: 'Listening…',
  thinking: 'Thinking…',
  failed: 'Not connected',
};

export function TalkButton({
  phase,
  seconds,
  onPressIn,
  onPressOut,
}: {
  phase: TalkPhase;
  seconds: number;
  onPressIn: () => void;
  onPressOut: () => void;
}) {
  const listening = phase === 'recording' || phase === 'arming';
  const disabled = phase === 'starting' || phase === 'thinking' || phase === 'failed';
  const label = listening ? `Listening… ${seconds}s · let go to send` : phase === 'thinking' ? `Thinking… ${seconds}s` : LABEL[phase];

  return (
    <View style={styles.wrap}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Hold to talk"
        accessibilityState={{ disabled, busy: phase === 'thinking' }}
        disabled={disabled}
        onPressIn={onPressIn}
        onPressOut={onPressOut}
        hitSlop={16}
        style={[styles.circle, listening && styles.listening, disabled && styles.disabled]}
      >
        {phase === 'thinking' || phase === 'starting' ? <ActivityIndicator color="#fff" size="large" /> : <View style={[styles.mic, listening && styles.micOn]} />}
      </Pressable>
      <Text style={[styles.label, listening && { color: colors.record }]}>{label}</Text>
    </View>
  );
}

const SIZE = 104;

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: space.sm },
  circle: {
    width: SIZE,
    height: SIZE,
    borderRadius: SIZE / 2,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
  },
  listening: { backgroundColor: colors.record, transform: [{ scale: 1.08 }] },
  disabled: { backgroundColor: '#A8A29E' },
  mic: { width: 26, height: 40, borderRadius: 13, backgroundColor: '#fff' },
  micOn: { width: 30, height: 30, borderRadius: 6 },
  label: { fontSize: 16, fontWeight: '600', color: colors.muted },
});
