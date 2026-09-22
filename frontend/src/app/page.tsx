import Link from "next/link";
import { Brand } from "@/components/AppShell";
import { Icon } from "@/components/Icon";

export default function LandingPage() {
  return (
    <div className="min-h-screen overflow-x-clip bg-[#fbfcfa]">
      <header className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-6">
        <Brand />
        <nav className="flex flex-wrap items-center gap-6 text-sm">
          <Link
            href="/pricing"
            className="hidden text-muted hover:text-foreground sm:block"
          >
            Plans
          </Link>
          <Link
            href="/recruiter/login"
            className="text-muted hover:text-foreground"
          >
            Recruiter login
          </Link>
          <Link href="/login" className="text-muted hover:text-foreground">
            Sign in
          </Link>
          <Link href="/login" className="btn-primary hidden sm:inline-flex">
            Start practicing <Icon name="arrow" className="h-4 w-4" />
          </Link>
        </nav>
      </header>
      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-16 px-6 pb-24 pt-14 lg:grid-cols-[1.05fr_1fr] lg:pt-24">
          <div className="enter">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#d6e7df] bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />A better
              way to prepare
            </div>
            <h1 className="max-w-xl text-5xl font-semibold leading-[1.1] tracking-[-.045em] sm:text-6xl">
              Your experience.
              <br />
              Your next role.
              <br />
              <span className="text-accent">A stronger story.</span>
            </h1>
            <p className="mt-7 max-w-md text-base leading-7 text-muted">
              Turn what you know into answers that land. Practice with an AI
              interviewer that knows your resume, challenges your thinking, and
              helps you improve.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/login" className="btn-primary !px-6 !py-3.5">
                Build your interview confidence{" "}
                <Icon name="arrow" className="h-4 w-4" />
              </Link>
              <Link href="#how-it-works" className="btn-ghost !py-3.5">
                See how it works
              </Link>
            </div>
            <p className="mt-4 text-xs text-muted">
              Start with 3 interviews a month. No card required.
            </p>
          </div>
          <div className="enter relative" style={{ animationDelay: ".1s" }}>
            <div className="absolute -inset-7 rounded-full bg-[#d9eee3]/50 blur-3xl" />
            <div className="relative overflow-hidden rounded-3xl border border-border bg-white shadow-[0_24px_70px_-30px_#174e4240]">
              <div className="flex items-center justify-between border-b border-border px-6 py-4">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-accent" />
                  <span className="text-xs font-medium">
                    Your next role, in focus
                  </span>
                </div>
                <span className="text-[10px] text-muted">EXAMPLE SESSION</span>
              </div>
              <div className="p-6 sm:p-8">
                <div className="mb-6 flex items-center gap-3">
                  <div className="grid h-11 w-11 place-items-center rounded-xl bg-accent-soft text-accent">
                    <Icon name="mic" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">
                      Senior Software Engineer
                    </p>
                    <p className="mt-1 text-xs text-muted">
                      Project depth · Architecture · Leadership
                    </p>
                  </div>
                </div>
                <div className="rounded-2xl bg-[#f3f6f4] p-5">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-accent">
                    Your interviewer
                  </p>
                  <p className="text-[15px] leading-6">
                    “You mentioned reducing API latency on your resume. What did
                    you change, and which trade-off was hardest?”
                  </p>
                  <div className="mt-5 flex h-7 items-center gap-1">
                    {[
                      12, 22, 15, 28, 18, 24, 10, 20, 26, 15, 22, 12, 7, 18, 24,
                      10,
                    ].map((h, i) => (
                      <span
                        key={i}
                        className="w-1 rounded-full bg-accent/60"
                        style={{ height: h }}
                      />
                    ))}
                  </div>
                </div>
                <div className="mt-4 rounded-2xl border border-border p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-medium">
                      Feedback you can act on
                    </span>
                    <Icon name="spark" className="h-4 w-4 text-accent" />
                  </div>
                  <p className="text-sm leading-6 text-muted">
                    Make your individual contribution clear. Explain the
                    alternative you ruled out, then connect your decision to the
                    result.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 border-t border-border bg-[#fcfdfb] px-6 py-4 text-xs text-muted">
                <Icon name="check" className="h-4 w-4 text-accent" />
                From a practice session to a clear next step.
              </div>
            </div>
          </div>
        </section>
        <section id="how-it-works" className="border-y border-border bg-white">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <p className="eyebrow">Practice with purpose</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight">
              A feedback loop built around you.
            </h2>
            <div className="mt-12 grid gap-10 md:grid-cols-3">
              {[
                [
                  "01",
                  "Bring your context",
                  "Upload your resume and paste the role you want. Your interviewer prepares around the experience and skills that matter.",
                ],
                [
                  "02",
                  "Think out loud",
                  "Answer by voice or text. Get thoughtful follow-ups that test ownership, reasoning, and the evidence behind your claims.",
                ],
                [
                  "03",
                  "Know what to practice",
                  "Review feedback grounded in your answers. Work through focused drills and bring stronger examples to your next session.",
                ],
              ].map(([n, title, body]) => (
                <div key={n}>
                  <span className="font-mono text-xs text-accent">{n} /</span>
                  <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-muted">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
        <section className="mx-auto max-w-6xl px-6 py-20">
          <div className="flex flex-col justify-between gap-6 rounded-3xl bg-[#173d36] px-8 py-12 text-white md:flex-row md:items-center md:px-12">
            <div>
              <p className="text-xs uppercase tracking-widest text-[#9bcabb]">
                Make the next conversation count
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight">
                You have the experience.
                <br />
                Practice how you share it.
              </h2>
            </div>
            <Link
              href="/login"
              className="btn-primary !bg-white !px-6 !py-3.5 !text-[#173d36]"
            >
              Start your first interview{" "}
              <Icon name="arrow" className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>
      <footer className="mx-auto flex max-w-6xl flex-wrap justify-between gap-4 border-t border-border px-6 py-7 text-xs text-muted">
        <span>
          Interview Studio · Deliberate practice for your next chapter.
        </span>
        <span>Practice feedback, never a hiring prediction.</span>
      </footer>
    </div>
  );
}
