import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button, ExplainToggle, Notice, SectionTitle } from '@/components/ui';
import { makeApi, normalizeServerUrl } from '@/lib/api';
import { guessServerUrl, useSettings } from '@/lib/settings';
import { colors, radius, space } from '@/theme';

type Check = { kind: 'info' | 'error'; text: string } | null;

export default function SettingsScreen() {
  const { serverUrl, setServerUrl, explainIn, setExplainIn } = useSettings();
  const [draft, setDraft] = useState(serverUrl);
  const [check, setCheck] = useState<Check>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => setDraft(serverUrl), [serverUrl]);

  const test = async () => {
    const url = normalizeServerUrl(draft);
    setServerUrl(url);
    setBusy(true);
    setCheck(null);
    try {
      const h = await makeApi(url).health();
      const what = h.mode === 'fake' ? 'practice mode (no models)' : `real models: ${h.brain}, ${h.ears}`;
      setCheck({ kind: 'info', text: `Connected. The server is in ${what}.` });
    } catch (e) {
      setCheck({ kind: 'error', text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const guess = guessServerUrl();

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <SectionTitle>Server address</SectionTitle>
      <Text style={styles.help}>The server window on your PC prints this, for example http://192.168.1.20:8000.</Text>
      <TextInput
        value={draft}
        onChangeText={setDraft}
        placeholder="http://192.168.1.20:8000"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        returnKeyType="done"
        onSubmitEditing={test}
        style={styles.input}
      />
      <View style={styles.row}>
        <Button title="Save and test" onPress={test} busy={busy} style={{ flex: 1 }} />
        {guess && guess !== draft ? <Button title="Use this PC" kind="secondary" onPress={() => setDraft(guess)} /> : null}
      </View>
      {check && (
        <View style={{ marginTop: space.md }}>
          <Notice kind={check.kind}>{check.text}</Notice>
        </View>
      )}

      <SectionTitle>Explain corrections in</SectionTitle>
      <ExplainToggle value={explainIn} onChange={setExplainIn} />
      <Text style={[styles.help, { marginTop: space.sm }]}>Used in the recap at the end of each conversation. You can switch it there too.</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: space.lg },
  help: { fontSize: 15, color: colors.muted, lineHeight: 21, marginBottom: space.sm },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    paddingVertical: 12,
    fontSize: 17,
    color: colors.ink,
  },
  row: { flexDirection: 'row', gap: space.sm, marginTop: space.md },
});
