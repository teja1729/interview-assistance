"use client";
/** Device/UI lifecycle for a single interview. Backend state remains authoritative.
 * Pending answers keep their original request ID, so uncertain network responses can be retried.
 * Any new device resource must be released by cleanup and by explicit stop/hang-up.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  type Interview,
  type Turn,
  type TurnResult,
} from "@/lib/api";
import { WavRecorder } from "@/lib/recorder";
import { Speaker } from "@/lib/speech";
type Phase =
  | "loading"
  | "lobby"
  | "speaking"
  | "ready"
  | "recording"
  | "thinking"
  | "done"
  | "finishing"
  | "error";
export function useInterviewSession(id: string) {
  const router = useRouter();
  const [iv, setIv] = useState<Interview | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [current, setCurrent] = useState("");
  const [closing, setClosing] = useState<string | null>(null);
  const [remaining, setRemaining] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [camOn, setCamOn] = useState(false);
  const [captions, setCaptions] = useState(true);
  const [panel, setPanel] = useState(false);
  const [typing, setTyping] = useState(false);
  const [typed, setTyped] = useState("");
  const [voiceInput, setVoiceInput] = useState(false);
  const [cloudVoice, setCloudVoice] = useState(false);
  const [autoListen, setAutoListen] = useState(true);
  const [audioRetry, setAudioRetry] = useState<{
    text: string;
    next: Phase;
  } | null>(null);
  const speechActivity = useRef({ heardMs: 0, lastAt: 0 });
  const [micUnavailable, setMicUnavailable] = useState("");
  const [micDenied, setMicDenied] = useState(false);
  const [level, setLevel] = useState(0);
  const [recSeconds, setRecSeconds] = useState(0);
  const [lastTranscript, setLastTranscript] = useState<string | null>(null);
  const [clock, setClock] = useState("");
  const [hasPending, setHasPending] = useState(false);
  const recorder = useRef<WavRecorder | null>(null);
  const speaker = useRef<Speaker | null>(null);
  const meterTimer = useRef<number | null>(null);
  const deadline = useRef(0);
  const version = useRef(0);
  const camStream = useRef<MediaStream | null>(null);
  const cameraRequest = useRef(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mounted = useRef(false);
  const pending = useRef<(() => Promise<TurnResult>) | null>(null);
  const locked = useRef(false);
  const generation = useRef(0);
  const invalidate = useCallback(() => {
    generation.current++;
    cameraRequest.current++;
  }, []);
  const bindVideo = useCallback((el: HTMLVideoElement | null) => {
    videoRef.current = el;
    if (el && camStream.current) {
      el.srcObject = camStream.current;
      void el.play().catch(() => {});
    }
  }, []);
  const startCamera = useCallback(async () => {
    const request = ++cameraRequest.current;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 360 },
        audio: false,
      });
      if (!mounted.current || request !== cameraRequest.current) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      camStream.current?.getTracks().forEach((t) => t.stop());
      camStream.current = stream;
      setCamOn(true);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        void videoRef.current.play().catch(() => {});
      }
    } catch {
      if (mounted.current) setCamOn(false);
    }
  }, []);
  const stopCamera = () => {
    cameraRequest.current++;
    camStream.current?.getTracks().forEach((t) => t.stop());
    camStream.current = null;
    setCamOn(false);
  };
  useEffect(() => {
    mounted.current = true;
    const localSpeaker = new Speaker();
    speaker.current = localSpeaker;
    let active = true;
    Promise.all([api.interview(id), api.capabilities()])
      .then(([data, caps]) => {
        if (!active) return;
        if (["finished", "finishing", "report_failed"].includes(data.status)) {
          router.replace(`/report/${id}`);
          return;
        }
        setIv(data);
        setTurns(data.turns);
        version.current = data.version;
        setRemaining(data.remaining_seconds);
        deadline.current = data.started_at
          ? Date.now() + data.remaining_seconds * 1000
          : 0;
        const deviceSupported = WavRecorder.isSupported();
        setVoiceInput(caps.voice_input && deviceSupported);
        setCloudVoice(caps.cloud_voice);
        setMicUnavailable(
          !caps.voice_input
            ? "Microphone answers are unavailable because voice transcription is not configured. You can type your answer."
            : !deviceSupported
              ? "Microphone access requires a supported browser on HTTPS or localhost. You can type your answer."
              : "",
        );
        if (!caps.voice_input || !deviceSupported) setTyping(true);
        setCurrent(data.current_question ?? "");
        setClosing(data.closing_remark);
        setPhase(
          data.current_question && data.status !== "abandoned"
            ? "lobby"
            : "done",
        );
      })
      .catch((e) => {
        if (active) {
          setError(e.message);
          setPhase("error");
        }
      });
    return () => {
      active = false;
      mounted.current = false;
      invalidate();
      localSpeaker.stop();
      recorder.current?.cancel();
      recorder.current = null;
      if (meterTimer.current) clearInterval(meterTimer.current);
      camStream.current?.getTracks().forEach((t) => t.stop());
      camStream.current = null;
    };
  }, [id, router, invalidate]);
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (deadline.current)
        setRemaining(
          Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000)),
        );
      setClock(
        new Date().toLocaleTimeString(undefined, {
          hour: "2-digit",
          minute: "2-digit",
        }),
      );
    }, 500);
    return () => clearInterval(timer);
  }, []);

  async function speakLine(text: string, next: Phase) {
    const token = generation.current;
    setAudioRetry(null);
    setPhase("speaking");
    try {
      await speaker.current?.speak(text, cloudVoice ? "cloud" : "browser", {
        interview_id: id,
        language: iv?.language,
      });
      if (mounted.current && token === generation.current) setPhase(next);
    } catch {
      if (mounted.current && token === generation.current) {
        setError(
          "The question audio could not play. Check your sound output and retry the audio to continue.",
        );
        setAudioRetry({ text, next });
        setPhase(next);
      }
    }
  }
  async function retryAudio() {
    if (!audioRetry || locked.current) return;
    locked.current = true;
    setError(null);
    try {
      await speakLine(audioRetry.text, audioRetry.next);
    } finally {
      locked.current = false;
    }
  }
  async function join() {
    if (locked.current) return;
    locked.current = true;
    setError(null);
    try {
      const data = await api.join(id);
      version.current = data.version;
      setIv(data);
      deadline.current = Date.now() + data.remaining_seconds * 1000;
      setRemaining(data.remaining_seconds);
      await speakLine(data.current_question ?? current, "ready");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      locked.current = false;
    }
  }
  async function startRecording() {
    if (
      phase !== "ready" ||
      !voiceInput ||
      audioRetry ||
      remaining <= 0 ||
      locked.current ||
      pending.current
    )
      return;
    locked.current = true;
    setError(null);
    const rec = new WavRecorder();
    recorder.current = rec;
    try {
      speaker.current?.stop();
      await rec.start();
      if (!mounted.current) {
        rec.cancel();
        return;
      }
      setPhase("recording");
      if (micDenied && cloudVoice) setAutoListen(true);
      setMicDenied(false);
      speechActivity.current = { heardMs: 0, lastAt: 0 };
      setRecSeconds(0);
      setLastTranscript(null);
      meterTimer.current = window.setInterval(() => {
        const volume = rec.level();
        setLevel(volume);
        if (volume >= 0.025) {
          speechActivity.current.heardMs += 100;
          speechActivity.current.lastAt = performance.now();
        }
        setRecSeconds(rec.elapsed());
      }, 100);
    } catch (error) {
      rec.cancel();
      recorder.current = null;
      if (mounted.current) {
        const name = error instanceof Error ? error.name : "";
        const denied = name === "NotAllowedError" || name === "SecurityError";
        setMicDenied(denied);
        setAutoListen(false);
        setError(
          denied
            ? "Microphone permission is blocked. Allow microphone access in your browser's site settings, then select Retry microphone."
            : name === "NotFoundError"
              ? "No microphone was found. Connect one, then try again, or type your answer."
              : name === "NotReadableError"
                ? "The microphone could not be opened. Check your system microphone permissions and whether another app is using it, then try again."
                : "Microphone unavailable. Try again or type your answer instead.",
        );
      }
    } finally {
      locked.current = false;
    }
  }
  async function sendPending(withSpeech = true): Promise<boolean> {
    if (!pending.current || locked.current) return false;
    locked.current = true;
    setPhase("thinking");
    setError(null);
    try {
      const result = await pending.current();
      version.current = result.version;
      deadline.current = Date.now() + result.remaining_seconds * 1000;
      pending.current = null;
      setHasPending(false);
      if (result.repeat) {
        setError("No speech detected. Please try again or type your answer.");
        if (withSpeech) await speakLine(result.reply, "ready");
        else setPhase("ready");
        return false;
      }
      setTyped("");
      setLastTranscript(result.transcript);
      setTurns((ts) => {
        const next = [...ts];
        next[next.length - 1] = {
          ...next[next.length - 1],
          answer: result.transcript,
        };
        if (!result.done)
          next.push({
            question: result.reply,
            answer: null,
            at: Date.now() / 1000,
          });
        return next;
      });
      setCurrent(result.done ? "" : result.reply);
      if (result.done) setClosing(result.reply);
      if (withSpeech)
        await speakLine(result.reply, result.done ? "done" : "ready");
      else setPhase(result.done ? "done" : "ready");
      return true;
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 409
          ? `${e.message} Reopen this session from Overview to synchronize.`
          : (e as Error).message,
      );
      setPhase("ready");
      return false;
    } finally {
      locked.current = false;
    }
  }
  async function stopRecording(withSpeech = true): Promise<boolean> {
    const rec = recorder.current;
    if (!rec || locked.current) return false;
    recorder.current = null;
    if (meterTimer.current) clearInterval(meterTimer.current);
    setLevel(0);
    const elapsed = rec.elapsed();
    locked.current = true;
    let wav: Blob;
    try {
      wav = await rec.stop();
    } catch (e) {
      setError((e as Error).message);
      setPhase("ready");
      return false;
    } finally {
      locked.current = false;
    }
    if (elapsed < 1) {
      setPhase("ready");
      return false;
    }
    const requestId = crypto.randomUUID(),
      expected = version.current;
    pending.current = () => api.audioTurn(id, wav, expected, requestId);
    setHasPending(true);
    return sendPending(withSpeech);
  }
  function toggleMic() {
    if (phase === "recording") void stopRecording();
    else void startRecording();
  }
  function toggleTyping() {
    if (phase === "recording" || locked.current) return;
    setTyping((value) => !value);
  }
  async function submitTyped() {
    const text = typed.trim();
    if (
      !text ||
      locked.current ||
      pending.current ||
      remaining <= 0 ||
      phase !== "ready"
    )
      return;
    const requestId = crypto.randomUUID(),
      expected = version.current;
    pending.current = () => api.textTurn(id, text, expected, requestId);
    setHasPending(true);
    await sendPending();
  }
  async function endCall() {
    if (locked.current) return;
    generation.current++;
    speaker.current?.stop();
    let answerSaved = false;
    if (recorder.current) {
      answerSaved = await stopRecording(false);
      if (pending.current) return;
    }
    if (pending.current) {
      setError(
        "Retry your pending answer before finishing so it is included in your report.",
      );
      return;
    }
    const answered =
      turns.filter((t) => t.answer).length + (answerSaved ? 1 : 0);
    if (!answered) {
      if (!confirm("Leave this interview without a report?")) return;
      await api.abandon(id);
      router.push("/dashboard");
      return;
    }
    locked.current = true;
    setPhase("finishing");
    try {
      const data = await api.finish(id);
      router.push(`/report/${data.id}`);
    } catch (e) {
      setError((e as Error).message);
      setPhase(closing ? "done" : "ready");
    } finally {
      locked.current = false;
    }
  }
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (
        e.code === "Space" &&
        !e.repeat &&
        !typing &&
        phase === "ready" &&
        remaining > 0 &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !(e.target instanceof HTMLButtonElement)
      ) {
        e.preventDefault();
        void startRecording();
      }
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === "Space" && phase === "recording") {
        e.preventDefault();
        void stopRecording();
      }
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
    // Event handlers intentionally follow the current device phase; refs serialize async calls.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, typing, remaining]);
  useEffect(() => {
    if (
      phase !== "ready" ||
      !cloudVoice ||
      !voiceInput ||
      !autoListen ||
      typing ||
      audioRetry ||
      hasPending ||
      remaining <= 0
    )
      return;
    // Let the preceding request release its lock before opening the next recording.
    const timer = setTimeout(() => void startRecording(), 250);
    return () => clearTimeout(timer);
    // The phase owns this transition; the callback intentionally sees the latest session state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    phase,
    cloudVoice,
    voiceInput,
    autoListen,
    typing,
    audioRetry,
    hasPending,
    remaining,
  ]);
  useEffect(() => {
    if (phase !== "recording" || !autoListen || !cloudVoice) return;
    const timer = setInterval(() => {
      const { heardMs, lastAt } = speechActivity.current;
      if (heardMs >= 500 && performance.now() - lastAt >= 3000)
        void stopRecording();
    }, 200);
    return () => clearInterval(timer);
    // End a spoken turn only after detected speech followed by a pause; silence alone is not an answer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, autoListen, cloudVoice]);
  useEffect(() => {
    if (phase !== "recording" || (remaining > 0 && recSeconds < 295)) return;
    const timer = setTimeout(() => void stopRecording(), 0);
    return () => clearTimeout(timer);
    // Stop and submit the final answer at the deadline; never disable an active recorder.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining, recSeconds, phase]);
  return {
    iv,
    phase,
    turns,
    current,
    closing,
    remaining,
    error,
    camOn,
    captions,
    panel,
    typing,
    typed,
    voiceInput,
    cloudVoice,
    autoListen,
    audioRetry,
    micUnavailable,
    micDenied,
    level,
    recSeconds,
    lastTranscript,
    clock,
    hasPending,
    bindVideo,
    startCamera,
    stopCamera,
    join,
    sendPending,
    toggleMic,
    submitTyped,
    endCall,
    toggleTyping,
    setAutoListen,
    retryAudio,
    setTyped,
    setCaptions,
    setPanel,
  };
}
