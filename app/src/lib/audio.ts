import {
  AudioQuality,
  IOSOutputFormat,
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
  type RecordingOptions,
} from 'expo-audio';
import { useCallback, useEffect, useState } from 'react';

/**
 * 16 kHz mono 16-bit WAV: what PhoWhisper reads, and the server can open it without ffmpeg.
 * Only iOS is a target; the Android and web values just satisfy the type.
 */
export const WAV_16K: RecordingOptions = {
  extension: '.wav',
  sampleRate: 16_000,
  numberOfChannels: 1,
  bitRate: 256_000,
  ios: {
    extension: '.wav',
    outputFormat: IOSOutputFormat.LINEARPCM,
    audioQuality: AudioQuality.HIGH,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  android: { outputFormat: 'default', audioEncoder: 'default' },
  web: {},
};

export const MAX_RECORDING_MS = 30_000; // the ears read at most 30 s per turn
export const MIN_RECORDING_MS = 500;

/** Play through the speaker even with the silent switch on, and allow recording. */
export function useConversationAudioMode() {
  useEffect(() => {
    setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true }).catch(() => {});
  }, []);
}

/** One shared player: play(url) swaps in a new clip; `playingUrl` says which one is playing. */
export function usePlayer() {
  const player = useAudioPlayer(null);
  const status = useAudioPlayerStatus(player);
  const [current, setCurrent] = useState<string | null>(null);

  const play = useCallback(
    (url: string) => {
      setCurrent(url);
      player.replace({ uri: url });
      player.play();
    },
    [player],
  );

  const stop = useCallback(() => {
    player.pause();
    setCurrent(null);
  }, [player]);

  useEffect(() => {
    if (status.didJustFinish) setCurrent(null);
  }, [status.didJustFinish]);

  return { play, stop, playingUrl: current };
}
