import Link from "next/link";
import { Brand } from "@/components/AppShell";
import { Icon } from "@/components/Icon";
import { InteractivePracticeScene } from "./InteractivePracticeScene";
import styles from "./page.module.css";

const steps = [
  {
    number: "01",
    icon: "file",
    title: "Bring your real story",
    body: "Add your resume and the role you want. Okkra builds the practice around your actual experience.",
    note: "YOUR EXPERIENCE, IN CONTEXT",
  },
  {
    number: "02",
    icon: "mic",
    title: "Find your words out loud",
    body: "Meet a voice interviewer that listens, follows up, and gives you room to think.",
    note: "VOICE OR TEXT, YOUR CALL",
  },
  {
    number: "03",
    icon: "spark",
    title: "Make the next answer stronger",
    body: "Get feedback tied to what you said, then practice the exact skill you want to improve.",
    note: "FEEDBACK YOU CAN USE",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen overflow-hidden bg-background">
      <header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
        <Brand />
        <nav aria-label="Main" className="flex items-center gap-3 sm:gap-6">
          <Link
            href="/pricing"
            className="hidden text-sm text-muted transition hover:text-foreground sm:block"
          >
            Plans
          </Link>
          <Link
            href="/recruiter/login"
            className="hidden text-sm text-muted transition hover:text-foreground md:block"
          >
            Recruiter login
          </Link>
          <Link
            href="/login"
            className="text-sm text-muted transition hover:text-foreground"
          >
            Sign in
          </Link>
          <Link
            href="/login"
            className="btn-primary !rounded-full !px-5 !py-2.5"
          >
            Get started <Icon name="arrow" className="h-4 w-4" />
          </Link>
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-7xl items-center gap-10 px-5 pb-16 pt-8 sm:px-8 md:pb-24 lg:grid-cols-[.95fr_1.05fr] lg:gap-4 lg:px-12 lg:pt-12">
          <div className="relative z-[1] py-6 lg:py-12">
            <div className={`${styles.eyebrow} enter`}>
              <span className={styles.eyebrowDot} />
              INTERVIEW PRACTICE THAT GETS PERSONAL
            </div>
            <h1
              className={`${styles.heroTitle} enter mt-7`}
              style={{ animationDelay: ".08s" }}
            >
              Your story is
              <br />
              <span className={styles.heroAccent}>the answer.</span>
            </h1>
            <p
              className="enter mt-7 max-w-lg text-base leading-7 text-muted sm:text-lg sm:leading-8"
              style={{ animationDelay: ".16s" }}
            >
              Practice saying it with confidence. Okkra turns your resume and
              target role into a real voice interview, then helps you sharpen
              the answers that matter.
            </p>
            <div
              className="enter mt-9 flex flex-wrap items-center gap-3"
              style={{ animationDelay: ".24s" }}
            >
              <Link
                href="/login"
                className="btn-primary !rounded-full !px-6 !py-3.5"
              >
                Practice your first answer{" "}
                <Icon name="arrow" className="h-4 w-4" />
              </Link>
              <Link
                href="#how-it-works"
                className="rounded-full border border-border bg-surface px-5 py-3.5 text-sm font-medium transition hover:bg-accent-soft"
              >
                See how it works
              </Link>
            </div>
            <div
              className={`${styles.promise} enter mt-6`}
              style={{ animationDelay: ".32s" }}
            >
              <span>
                <Icon name="check" className="h-3.5 w-3.5" /> Resume-grounded
              </span>
              <span>
                <Icon name="check" className="h-3.5 w-3.5" /> Voice-to-voice
              </span>
              <span>
                <Icon name="check" className="h-3.5 w-3.5" /> Built for practice
              </span>
            </div>
          </div>

          <InteractivePracticeScene />
        </section>

        <div
          className={styles.ticker}
          aria-label="Resume-grounded practice, voice interviews, and useful feedback"
        >
          <div className={styles.tickerTrack} aria-hidden="true">
            {[0, 1].map((copy) => (
              <div className={styles.tickerGroup} key={copy}>
                <span>YOUR EXPERIENCE</span>
                <i />
                <span>REAL VOICE PRACTICE</span>
                <i />
                <span>FEEDBACK THAT FITS</span>
                <i />
                <span>YOUR NEXT CHAPTER</span>
                <i />
              </div>
            ))}
          </div>
        </div>

        <section
          id="how-it-works"
          className="mx-auto max-w-7xl px-5 py-20 sm:px-8 md:py-28 lg:px-12"
        >
          <div className="mb-12 grid gap-5 md:grid-cols-[1fr_.7fr] md:items-end">
            <div>
              <p className="eyebrow">A BETTER WAY TO GET READY</p>
              <h2 className="mt-4 max-w-2xl text-3xl font-semibold leading-tight tracking-tight sm:text-5xl">
                Practice the interview.
                <br />
                <span className="text-muted">Keep what makes you, you.</span>
              </h2>
            </div>
            <p className="max-w-md text-sm leading-6 text-muted md:justify-self-end">
              No generic scripts. No mystery scores. Just thoughtful reps,
              grounded in your experience, with useful next steps after every
              session.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {steps.map((step, index) => (
              <article
                className={`${styles.stepCard} enter`}
                key={step.number}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className={styles.stepTop}>
                  <span>{step.number}</span>
                  <Icon name={step.icon} className="h-5 w-5" />
                </div>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
                <div className={styles.stepNote}>
                  <span />
                  {step.note}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="px-5 pb-20 sm:px-8 md:pb-28 lg:px-12">
          <div className={styles.finalCta}>
            <div className={styles.ctaOrbit} aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <div className="relative z-[1] max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[.2em] text-white/65">
                Your next interview starts here
              </p>
              <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-white sm:text-5xl">
                You already have the experience.
                <br />
                Let’s make it land.
              </h2>
              <p className="mt-5 max-w-lg text-sm leading-6 text-white/70">
                One practice session can turn “I think I did okay” into “I know
                what I want to say next time.”
              </p>
              <Link
                href="/login"
                className="mt-8 inline-flex items-center gap-2 rounded-full bg-white px-6 py-3.5 text-sm font-semibold text-foreground transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                Start practicing <Icon name="arrow" className="h-4 w-4" />
              </Link>
            </div>
            <div className={styles.ctaStamp} aria-hidden="true">
              <Icon name="spark" className="h-8 w-8" />
              <span>
                MAKE IT
                <br />
                YOUR STORY
              </span>
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex max-w-7xl flex-wrap justify-between gap-3 border-t border-border px-5 py-6 text-xs text-muted sm:px-8 lg:px-12">
        <span>Okkra · Deliberate practice for your next chapter.</span>
        <span>Practice feedback, never a hiring prediction.</span>
      </footer>
    </div>
  );
}
