import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { SettingsProvider } from '@/lib/settings';
import { colors } from '@/theme';

export default function RootLayout() {
  return (
    <SettingsProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerShadowVisible: false,
          headerTintColor: colors.accent,
          headerTitleStyle: { color: colors.ink },
          contentStyle: { backgroundColor: colors.bg },
          headerBackTitle: 'Back',
        }}
      >
        <Stack.Screen name="index" options={{ title: 'VietTime' }} />
        <Stack.Screen name="talk/[topic]" options={{ title: '', gestureEnabled: false }} />
        <Stack.Screen name="session/[id]" options={{ title: 'Recap' }} />
        <Stack.Screen name="history" options={{ title: 'History' }} />
        <Stack.Screen name="settings" options={{ title: 'Settings' }} />
      </Stack>
    </SettingsProvider>
  );
}
