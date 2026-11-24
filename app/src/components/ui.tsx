import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import type { ExplainIn } from '@/lib/settings';
import { colors, radius, space } from '@/theme';

export function Button({
  title,
  onPress,
  kind = 'primary',
  disabled,
  busy,
  style,
}: {
  title: string;
  onPress: () => void;
  kind?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  busy?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const bg = kind === 'primary' ? colors.accent : kind === 'danger' ? colors.dangerSoft : colors.surface;
  const fg = kind === 'primary' ? '#fff' : kind === 'danger' ? colors.danger : colors.ink;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled || busy}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, opacity: disabled ? 0.45 : pressed ? 0.8 : 1 },
        kind === 'secondary' && styles.outlined,
        style,
      ]}
    >
      {busy ? <ActivityIndicator color={fg} /> : <Text style={[styles.buttonText, { color: fg }]}>{title}</Text>}
    </Pressable>
  );
}

export function Notice({ kind = 'info', children }: { kind?: 'info' | 'warn' | 'error'; children: ReactNode }) {
  const bg = kind === 'error' ? colors.dangerSoft : kind === 'warn' ? colors.warnSoft : colors.accentSoft;
  const fg = kind === 'error' ? colors.danger : kind === 'warn' ? colors.warn : colors.accent;
  return (
    <View style={[styles.notice, { backgroundColor: bg }]}>
      <Text style={{ color: fg, fontSize: 15, lineHeight: 21 }}>{children}</Text>
    </View>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <Text style={styles.section}>{children}</Text>;
}

/** A small round play button; shows a spinner while the audio is being made. */
export function PlayButton({ onPress, playing, busy, label }: { onPress: () => void; playing?: boolean; busy?: boolean; label: string }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      hitSlop={8}
      style={({ pressed }) => [styles.play, playing && styles.playing, pressed && { opacity: 0.7 }]}
    >
      {busy ? <ActivityIndicator size="small" color={colors.accent} /> : <Text style={[styles.playIcon, playing && { color: '#fff' }]}>{playing ? '■' : '▶'}</Text>}
    </Pressable>
  );
}

const EXPLAIN_OPTIONS: { value: ExplainIn; label: string }[] = [
  { value: 'both', label: 'Both' },
  { value: 'en', label: 'English' },
  { value: 'vi', label: 'Tiếng Việt' },
];

export function ExplainToggle({ value, onChange }: { value: ExplainIn; onChange: (v: ExplainIn) => void }) {
  return (
    <View style={styles.segments} accessibilityRole="radiogroup">
      {EXPLAIN_OPTIONS.map((o) => {
        const on = o.value === value;
        return (
          <Pressable
            key={o.value}
            accessibilityRole="radio"
            accessibilityState={{ selected: on }}
            onPress={() => onChange(o.value)}
            style={[styles.segment, on && styles.segmentOn]}
          >
            <Text style={[styles.segmentText, on && { color: '#fff' }]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  button: { minHeight: 50, borderRadius: radius.md, paddingHorizontal: space.lg, alignItems: 'center', justifyContent: 'center' },
  outlined: { borderWidth: 1, borderColor: colors.line },
  buttonText: { fontSize: 17, fontWeight: '600' },
  notice: { borderRadius: radius.md, padding: space.md },
  section: { fontSize: 13, fontWeight: '700', color: colors.muted, textTransform: 'uppercase', letterSpacing: 0.6, marginTop: space.xl, marginBottom: space.sm },
  play: { width: 36, height: 36, borderRadius: 18, borderWidth: 1, borderColor: colors.accent, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surface },
  playing: { backgroundColor: colors.accent },
  playIcon: { color: colors.accent, fontSize: 13, marginLeft: 1 },
  segments: { flexDirection: 'row', backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.line, padding: 3 },
  segment: { flex: 1, paddingVertical: 8, borderRadius: radius.sm, alignItems: 'center' },
  segmentOn: { backgroundColor: colors.accent },
  segmentText: { fontSize: 15, fontWeight: '600', color: colors.ink },
});
