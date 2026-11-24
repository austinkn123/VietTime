import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { makeApi, normalizeServerUrl, type Api } from './api';

export type ExplainIn = 'both' | 'en' | 'vi';

type Settings = {
  loaded: boolean;
  serverUrl: string;
  explainIn: ExplainIn;
  setServerUrl: (url: string) => void;
  setExplainIn: (v: ExplainIn) => void;
  api: Api;
};

const KEY = 'viettime.settings.v1';
const SERVER_PORT = 8000;

/** In Expo Go the app is served from the PC, so the same PC's address is a good first guess. */
export function guessServerUrl(): string {
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  if (!host || host.endsWith('.exp.direct')) return '';
  return `http://${host}:${SERVER_PORT}`;
}

const SettingsContext = createContext<Settings | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [loaded, setLoaded] = useState(false);
  const [serverUrl, setServerUrlState] = useState('');
  const [explainIn, setExplainInState] = useState<ExplainIn>('both');

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        const saved = raw ? JSON.parse(raw) : {};
        setServerUrlState(saved.serverUrl ?? guessServerUrl());
        if (saved.explainIn) setExplainInState(saved.explainIn);
      })
      .catch(() => setServerUrlState(guessServerUrl()))
      .finally(() => setLoaded(true));
  }, []);

  const save = useCallback((patch: object) => {
    AsyncStorage.getItem(KEY)
      .then((raw) => AsyncStorage.setItem(KEY, JSON.stringify({ ...(raw ? JSON.parse(raw) : {}), ...patch })))
      .catch(() => {});
  }, []);

  const setServerUrl = useCallback(
    (url: string) => {
      const clean = normalizeServerUrl(url);
      setServerUrlState(clean);
      save({ serverUrl: clean });
    },
    [save],
  );

  const setExplainIn = useCallback(
    (v: ExplainIn) => {
      setExplainInState(v);
      save({ explainIn: v });
    },
    [save],
  );

  const api = useMemo(() => makeApi(serverUrl), [serverUrl]);
  const value = useMemo(
    () => ({ loaded, serverUrl, explainIn, setServerUrl, setExplainIn, api }),
    [loaded, serverUrl, explainIn, setServerUrl, setExplainIn, api],
  );
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Settings {
  const s = useContext(SettingsContext);
  if (!s) throw new Error('useSettings must be used inside SettingsProvider');
  return s;
}
