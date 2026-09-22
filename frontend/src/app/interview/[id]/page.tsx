"use client";
import { useParams } from "next/navigation";
import Link from "next/link";
import { CompanyContext } from "@/components/CompanyContext";
import { InterviewerAvatar } from "@/features/interview/InterviewerAvatar";
import { useInterviewSession } from "@/features/interview/useInterviewSession";
import {
  TopBar,
  RoundBtn,
  SpeakingBars,
  CamIcon,
  CamOffIcon,
  MicIcon,
  MicOffIcon,
  CcIcon,
  KeyboardIcon,
  CloseIcon,
  ChatIcon,
  EndIcon,
} from "@/features/interview/CallControls";
export default function InterviewCallPage() {
  const { id } = useParams<{ id: string }>();
  const {
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
  } = useInterviewSession(id);
  if (!iv)
    return (
      <div className="card p-8 text-center">
        <p className={error ? "text-red-600" : "text-muted"}>
          {error ?? "Opening your interview…"}
        </p>
        {error && (
          <Link href="/dashboard" className="btn-ghost mt-4">
            Back to overview
          </Link>
        )}
      </div>
    );
  if (iv.status === "abandoned")
    return (
      <div className="card p-8 text-center">
        <h1 className="text-xl font-medium">This session was closed.</h1>
        <Link href="/setup" className="btn-primary mt-5">
          Start a new interview
        </Link>
      </div>
    );
  const personaName = iv.persona_profile?.name ?? "AI interviewer";
  const busy = phase === "thinking" || phase === "finishing";
  const micEnabled =
    phase === "recording" ||
    (phase === "ready" &&
      remaining > 0 &&
      voiceInput &&
      !audioRetry &&
      !hasPending);
  const caption =
    closing ??
    (phase === "recording"
      ? "Listening…"
      : phase === "thinking"
        ? "Considering your answer…"
        : current);
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#17292b] text-white">
      <TopBar
        clock={clock}
        title={iv.job_title}
        company={iv.company}
        remaining={phase === "lobby" ? null : remaining}
      />
      {phase === "lobby" ? (
        <div className="flex min-h-0 flex-1 flex-col items-center gap-8 overflow-y-auto px-6 py-8 lg:justify-center lg:flex-row lg:gap-14">
          <div className="relative aspect-video w-full max-w-xl overflow-hidden rounded-2xl bg-[#243c3e]">
            {camOn ? (
              <video
                ref={bindVideo}
                autoPlay
                playsInline
                muted
                className="h-full w-full -scale-x-100 object-cover"
              />
            ) : (
              <div className="grid h-full place-items-center text-white/50">
                Your camera stays on your device
              </div>
            )}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
              <RoundBtn
                on={camOn}
                onClick={() => (camOn ? stopCamera() : startCamera())}
                label={camOn ? "Turn off camera" : "Turn on camera"}
                icon={camOn ? <CamIcon /> : <CamOffIcon />}
              />
            </div>
          </div>
          <div className="max-w-sm text-center">
            <InterviewerAvatar icon={iv.persona_profile?.icon} compact />
            <h1 className="mt-5 text-2xl font-medium">Ready to join?</h1>
            <p className="mt-2 text-sm font-medium text-[#a5d9c6]">
              {personaName} · AI practice
            </p>
            <p className="mt-3 text-sm leading-6 text-white/60">
              {iv.duration_minutes} minutes to explore your experience with your{" "}
              {personaName.toLowerCase()}. Your clock starts when you join.
            </p>
            <p className="mt-3 text-xs text-white/50">
              {voiceInput
                ? "Your interviewer speaks, then your microphone opens. Pause for three seconds to send your answer. Camera is optional."
                : micUnavailable}
            </p>
            <div className="mt-4 max-h-56 overflow-y-auto">
              <CompanyContext brief={iv.company_context} dark />
            </div>
            <button
              className="mt-6 rounded-full bg-[#a5d9c6] px-8 py-3 font-medium text-[#173d36]"
              onClick={join}
            >
              Join now
            </button>
            <Link
              href="/dashboard"
              className="mt-4 block text-xs text-white/60 hover:text-white"
            >
              Back to overview
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div className="flex min-h-0 flex-1">
            <div className="relative m-3 mb-0 flex min-w-0 flex-1 flex-col">
              <div
                className={`relative flex flex-1 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-b from-[#2c4647] to-[#1e3335] ring-2 ${phase === "speaking" ? "ring-[#a5d9c6]" : "ring-transparent"}`}
              >
                <div className="relative">
                  <InterviewerAvatar icon={iv.persona_profile?.icon} />
                  {phase === "speaking" && <SpeakingBars />}
                </div>
                {phase === "done" && (
                  <div className="absolute top-7 rounded-full bg-black/30 px-4 py-2 text-xs">
                    Interview complete
                  </div>
                )}
                <div className="absolute left-4 top-4 text-xs text-white/70">
                  {personaName}
                  {iv.persona_profile?.round && (
                    <p className="mt-1 text-[10px] text-white/40">
                      {iv.persona_profile.round}
                    </p>
                  )}
                </div>
                {captions && caption && (
                  <div className="absolute inset-x-0 bottom-10 mx-auto max-w-2xl px-5">
                    <p
                      data-testid="caption"
                      className="rounded-xl bg-black/50 px-4 py-3 text-center text-sm leading-6"
                    >
                      {caption}
                    </p>
                    {lastTranscript && phase !== "recording" && (
                      <p
                        data-testid="you-caption"
                        className="mt-2 line-clamp-3 rounded-xl bg-black/25 px-4 py-2 text-center text-xs text-white/70"
                      >
                        You: {lastTranscript}
                      </p>
                    )}
                  </div>
                )}
                {camOn && (
                  <div
                    data-testid="selfview"
                    className="absolute right-4 top-4 aspect-video w-32 overflow-hidden rounded-xl sm:w-44"
                  >
                    <video
                      ref={bindVideo}
                      autoPlay
                      muted
                      playsInline
                      className="h-full w-full -scale-x-100 object-cover"
                    />
                  </div>
                )}
              </div>
              {typing && phase !== "done" && (
                <div className="mt-3 flex gap-2">
                  <textarea
                    aria-label="Your answer"
                    className="min-h-20 flex-1 resize-none rounded-xl border border-white/10 bg-[#243c3e] px-4 py-3 text-sm outline-none focus:border-[#a5d9c6]"
                    placeholder="Think it through, then share your answer…"
                    value={typed}
                    onChange={(e) => setTyped(e.target.value)}
                    disabled={phase !== "ready" || remaining <= 0 || hasPending}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        void submitTyped();
                      }
                    }}
                  />
                  <button
                    className="rounded-xl bg-[#a5d9c6] px-5 text-sm font-medium text-[#173d36] disabled:opacity-40"
                    onClick={submitTyped}
                    disabled={
                      phase !== "ready" ||
                      remaining <= 0 ||
                      !typed.trim() ||
                      hasPending
                    }
                  >
                    Send
                  </button>
                </div>
              )}
            </div>
            {panel && (
              <aside className="m-3 mb-0 flex w-72 shrink-0 flex-col rounded-2xl bg-white text-foreground max-sm:absolute max-sm:inset-3 max-sm:z-20 max-sm:w-auto">
                <div className="flex items-center justify-between border-b border-border px-4 py-4">
                  <h2 className="text-sm font-semibold">Transcript</h2>
                  <button
                    aria-label="Close transcript"
                    onClick={() => setPanel(false)}
                  >
                    <CloseIcon />
                  </button>
                </div>
                <ol className="flex-1 space-y-5 overflow-y-auto px-4 py-4 text-sm">
                  {turns.map((t, i) => (
                    <li key={i}>
                      <p className="text-xs font-medium text-accent">
                        Interviewer
                      </p>
                      <p className="mt-1 leading-6">{t.question}</p>
                      {t.answer && (
                        <>
                          <p className="mt-3 text-xs font-medium text-muted">
                            You
                          </p>
                          <p className="mt-1 rounded-xl bg-background p-3 text-xs leading-6">
                            {t.answer}
                          </p>
                        </>
                      )}
                    </li>
                  ))}
                </ol>
              </aside>
            )}
          </div>
          <div
            data-testid="status"
            data-phase={phase}
            className="min-h-8 px-5 pt-2 text-center text-xs text-white/60"
          >
            {error ? (
              <span className="text-[#ffd1bc]">{error}</span>
            ) : phase === "finishing" ? (
              "Saving your session…"
            ) : phase === "recording" ? (
              `Listening · ${recSeconds.toFixed(0)}s${autoListen && cloudVoice ? " · Pause for 3 seconds when you’re finished" : " · Select Send answer when you’re finished"}`
            ) : remaining <= 0 ? (
              "Your time is up. Finish to get your report."
            ) : phase === "ready" ? (
              micUnavailable ||
              "Take your time. Specific examples make a difference."
            ) : phase === "done" ? (
              "Your practice is complete. Get your feedback when ready."
            ) : (
              ""
            )}
            {hasPending && phase === "ready" && (
              <button className="ml-3 underline" onClick={() => sendPending()}>
                Retry saved answer
              </button>
            )}
            {audioRetry && (
              <button className="ml-3 underline" onClick={retryAudio}>
                Retry question audio
              </button>
            )}
            {cloudVoice && voiceInput && !busy && phase !== "done" && (
              <button
                className="ml-3 underline"
                aria-pressed={autoListen}
                onClick={() => setAutoListen((value) => !value)}
              >
                {autoListen ? "Hands-free on" : "Hands-free off"}
              </button>
            )}
          </div>
          <div className="flex items-center justify-center gap-2 px-3 pb-5 pt-2">
            <div className="relative">
              <RoundBtn
                on
                active={phase === "recording"}
                disabled={!micEnabled}
                onClick={toggleMic}
                label={
                  phase === "recording"
                    ? "Send answer"
                    : micDenied
                      ? "Retry microphone"
                      : !voiceInput
                        ? "Microphone unavailable"
                        : "Answer"
                }
                icon={micEnabled ? <MicIcon /> : <MicOffIcon />}
              />
              {phase === "recording" && (
                <span
                  className="pointer-events-none absolute inset-0 rounded-full border border-[#a5d9c6]"
                  style={{ transform: `scale(${1.1 + level * 0.4})` }}
                />
              )}
            </div>
            <RoundBtn
              on={camOn}
              onClick={() => (camOn ? stopCamera() : startCamera())}
              label={camOn ? "Turn off camera" : "Turn on camera"}
              icon={camOn ? <CamIcon /> : <CamOffIcon />}
            />
            <RoundBtn
              on={captions}
              onClick={() => setCaptions((v) => !v)}
              label="Captions"
              icon={<CcIcon />}
            />
            <RoundBtn
              on={typing}
              onClick={toggleTyping}
              disabled={phase === "recording" || busy}
              label="Type an answer"
              icon={<KeyboardIcon />}
            />
            <button
              onClick={endCall}
              disabled={busy}
              aria-label={phase === "done" ? "Get report" : "End interview"}
              className="ml-1 flex h-12 items-center rounded-full bg-[#cc6353] px-5 text-xs font-medium disabled:opacity-40"
            >
              {phase === "done" ? "Get report" : <EndIcon />}
            </button>
            <RoundBtn
              on={panel}
              onClick={() => setPanel((v) => !v)}
              label="Transcript"
              icon={<ChatIcon />}
            />
          </div>
        </>
      )}
      {phase === "lobby" && error && (
        <p
          role="alert"
          className="px-5 pb-5 text-center text-sm text-[#ffd1bc]"
        >
          {error}
        </p>
      )}
    </div>
  );
}
