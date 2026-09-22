"use client";
import { api } from "./api";
export type VoiceMode = "cloud" | "browser";
/** Playback is server-configured. Cloud failures are retryable; never silently switch voices. */
export class Speaker {
  private generation = 0;
  private cleanup: (() => void) | null = null;
  private cachedAudio: { key: string; blob: Blob } | null = null;
  async speak(
    text: string,
    mode: VoiceMode = "cloud",
    context?: { interview_id: string; language?: string },
  ): Promise<"cloud" | "browser" | "silent"> {
    this.stop();
    const generation = this.generation;
    if (mode === "cloud") {
      const key = JSON.stringify([text, context]);
      const blob =
        this.cachedAudio?.key === key
          ? this.cachedAudio.blob
          : await api.tts(text, 25_000, context);
      if (generation !== this.generation) return "silent";
      this.cachedAudio = { key, blob };
      await this.play(blob);
      return generation === this.generation ? "cloud" : "silent";
    }
    if (generation !== this.generation) return "silent";
    if (typeof speechSynthesis === "undefined") return "silent";
    await new Promise<void>((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = context?.language || "en-IN";
      utterance.rate = 1;
      let settled = false;
      const timer = setTimeout(() => finish(), 90_000);
      const finish = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        this.cleanup = null;
        resolve();
      };
      this.cleanup = () => {
        speechSynthesis.cancel();
        finish();
      };
      utterance.onend = finish;
      utterance.onerror = finish;
      speechSynthesis.speak(utterance);
    });
    return generation === this.generation ? "browser" : "silent";
  }
  private play(blob: Blob) {
    return new Promise<void>((resolve, reject) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      let settled = false;
      const timer = setTimeout(() => finish(), 90_000);
      const finish = (error?: Error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        audio.pause();
        URL.revokeObjectURL(url);
        this.cleanup = null;
        if (error) reject(error);
        else resolve();
      };
      this.cleanup = () => finish();
      audio.onended = () => finish();
      audio.onerror = () => finish(new Error("Audio playback failed"));
      audio.play().catch(() => finish(new Error("Audio playback was blocked")));
    });
  }
  stop() {
    this.generation++;
    this.cleanup?.();
    this.cleanup = null;
  }
}
