"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import Waveform from "@/components/b2b/Waveform";
import styles from "./home.module.css";

// ─── Scroll reveal hook ───────────────────────────────────────────────────────
function useScrollReveal() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("visible");
        }),
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" },
    );
    document
      .querySelectorAll(".reveal, .reveal-left, .reveal-scale")
      .forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
}

// ─── Pricing toggle ───────────────────────────────────────────────────────────
const PLANS = [
  {
    id: "free",
    name: "Free",
    tag: "Always free",
    monthly: "₹0",
    yearly: "₹0",
    desc: "Get a feel for Okkra before committing.",
    features: [
      "3 sessions per month",
      "Text mode only",
      "Basic STAR feedback",
      "Readiness score",
    ],
    cta: "Start free",
    href: "/signup",
    highlight: false,
  },
  {
    id: "starter",
    name: "Starter",
    tag: "For freshers",
    monthly: "₹999",
    yearly: "₹9,999",
    desc: "Full access to practice. Right for freshers entering the market.",
    features: [
      "Unlimited sessions",
      "Voice + Text modes",
      "Full STAR + filler analysis",
      "Readiness score & trend",
      "Resume visibility to recruiters",
    ],
    cta: "Start Starter",
    href: "/signup?plan=starter",
    highlight: false,
  },
  {
    id: "pro",
    name: "Pro",
    tag: "Most popular",
    monthly: "₹2,999",
    yearly: "₹29,999",
    desc: "For mid-level professionals stepping up or switching tracks.",
    features: [
      "Everything in Starter",
      "Advanced feedback analytics",
      "Category performance tracking",
      "Priority recruiter discovery",
      "Drill recommendations",
    ],
    cta: "Start Pro",
    href: "/signup?plan=pro",
    highlight: true,
  },
  {
    id: "senior",
    name: "Senior",
    tag: "For leaders",
    monthly: "₹4,999",
    yearly: "₹49,999",
    desc: "For senior and leadership roles with elevated expectations.",
    features: [
      "Everything in Pro",
      "Leadership interview formats",
      "Executive communication coaching",
      "Top recruiter priority listing",
      "Dedicated improvement path",
    ],
    cta: "Start Senior",
    href: "/signup?plan=senior",
    highlight: false,
  },
];

const STEPS = [
  {
    num: "01",
    title: "Learn",
    desc: "Role-specific question banks, interview format guides, and preparation frameworks for every level.",
  },
  {
    num: "02",
    title: "Practise",
    desc: "AI-powered mock sessions with voice or text. Structured feedback on clarity, structure, and impact.",
  },
  {
    num: "03",
    title: "Get Exposed",
    desc: "Your interview readiness profile surfaces to vetted recruiters once you grant access. No cold applications.",
  },
  {
    num: "04",
    title: "Get Placed",
    desc: "Recruiters reach out to you directly. You decide who gets your full profile. Zero agency fees.",
  },
];

export default function HomePage() {
  useScrollReveal();
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");
  const [waveActive, setWaveActive] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setWaveActive(true), 1200);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className={styles.page}>
      <nav className={styles.nav} aria-label="Main navigation">
        <div className={styles.navInner}>
          <Link href="/" className={styles.wordmark} aria-label="Okkra home">
            <Image
              src="/okkra-logo.svg"
              alt="Okkra"
              width={145}
              height={54}
              className={styles.headerLogo}
              priority
            />
          </Link>
          <div className={styles.navLinks}>
            <Link href="/#how-it-works">How it works</Link>
            <Link href="/#pricing">Pricing</Link>
            <Link href="/recruiter/login">For recruiters</Link>
          </div>
          <div className={styles.navActions}>
            <Link href="/login" className={styles.navSignIn}>
              Sign in
            </Link>
            <Link href="/signup" className="btn btn-primary btn-sm">
              Get started
            </Link>
          </div>
        </div>
        <div className={styles.navDivider} />
      </nav>

      {/* ─── HERO ──────────────────────────────────────────────────────────── */}
      <section className={styles.hero} id="hero" aria-label="Hero">
        <div className={styles.heroInner}>
          <div className={styles.heroLeft}>
            <p className={`label-sm ${styles.heroEyebrow} reveal`}>
              AI-POWERED INTERVIEW PLATFORM
            </p>
            <h1
              className={`${styles.heroHeadline} reveal`}
              style={{ transitionDelay: "80ms" }}
            >
              From Practice
              <br />
              to Offer.
            </h1>
            <p
              className={`${styles.heroSub} reveal`}
              style={{ transitionDelay: "160ms" }}
            >
              Build confidence with AI-powered mock interviews,
              <br className={styles.heroBreak} />
              then let the right recruiters find you.
            </p>
            <div
              className={`${styles.heroCtas} reveal`}
              style={{ transitionDelay: "240ms" }}
            >
              <Link
                href="/signup"
                className="btn btn-primary btn-lg"
                id="hero-signup-btn"
              >
                Get started free
              </Link>
              <a
                href="#how-it-works"
                className={`${styles.heroLink} text-link body-sm`}
              >
                See how it works ↓
              </a>
            </div>
            <div
              className={`${styles.heroStats} reveal`}
              style={{ transitionDelay: "320ms" }}
            >
              {STATS.map((s, i) => (
                <span key={i} className={styles.heroStat}>
                  <span className={styles.heroStatNum}>{s.num}</span>
                  <span className={styles.heroStatLabel}>{s.label}</span>
                  {i < STATS.length - 1 && (
                    <span className={styles.heroStatDot} aria-hidden />
                  )}
                </span>
              ))}
            </div>
          </div>

          <div
            className={`${styles.heroRight} reveal-scale`}
            style={{ transitionDelay: "120ms" }}
          >
            <div className={styles.heroVisual}>
              {/* Waveform accent */}
              <div className={styles.heroWaveform}>
                <Waveform bars={40} active={waveActive} height={96} spectral />
              </div>
              {/* 4-step journey vertical */}
              <div className={styles.heroJourney}>
                {STEPS.map((step, i) => (
                  <div key={step.num} className={styles.heroJourneyStep}>
                    <span className={styles.heroJourneyNum}>{step.num}</span>
                    <span className={styles.heroJourneyTitle}>
                      {step.title}
                    </span>
                    {i < STEPS.length - 1 && (
                      <div className={styles.heroJourneyLine} aria-hidden />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <hr className="divider" />

      {/* ─── HOW IT WORKS ──────────────────────────────────────────────────── */}
      <section
        className={styles.section}
        id="how-it-works"
        aria-labelledby="hiw-title"
      >
        <div className={styles.sectionInner}>
          <p className={`label-sm ${styles.sectionEyebrow} reveal`}>
            HOW IT WORKS
          </p>
          <h2
            className={`display-md ${styles.sectionHeadline} reveal`}
            style={{ transitionDelay: "60ms" }}
            id="hiw-title"
          >
            Four steps. One outcome.
          </h2>

          <div className={`${styles.steps} reveal-group`}>
            {STEPS.map((step, i) => (
              <div key={step.num} className={styles.stepItem}>
                <div
                  className={`${styles.stepInner} reveal`}
                  style={{ transitionDelay: `${i * 80}ms` }}
                >
                  <span className={styles.stepNum}>{step.num}</span>
                  <div className={styles.stepBody}>
                    <h3 className={styles.stepTitle}>{step.title}</h3>
                    <p className={`body-sm ${styles.stepDesc}`}>{step.desc}</p>
                  </div>
                </div>
                {i < STEPS.length - 1 && (
                  <hr className={`divider ${styles.stepDivider}`} />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <hr className="divider" />

      {/* ─── FOR JOB SEEKERS ───────────────────────────────────────────────── */}
      <section className={styles.section} aria-labelledby="seekers-title">
        <div className={styles.sectionInner}>
          <div className={`grid-12 ${styles.splitSection}`}>
            <div className="col-6">
              <p className={`label-sm ${styles.sectionEyebrow} reveal`}>
                FOR JOB SEEKERS
              </p>
              <h2
                className={`display-md ${styles.splitHeadline} reveal`}
                style={{ transitionDelay: "60ms" }}
                id="seekers-title"
              >
                Practice that actually prepares you.
              </h2>
              <p
                className={`body-lg ${styles.splitSub} reveal`}
                style={{ transitionDelay: "120ms" }}
              >
                Whether you are a fresher stepping into your first interview, or
                a director changing tracks — Okkra meets you where you are.
              </p>

              <div
                className={`${styles.featureList} reveal`}
                style={{ transitionDelay: "180ms" }}
              >
                {SEEKER_FEATURES.map((f, i) => (
                  <div key={i} className={styles.featureItem}>
                    <span className={`${styles.featureCheck} text-success`}>
                      ✓
                    </span>
                    <span className="body-sm">{f}</span>
                  </div>
                ))}
              </div>

              <div
                className={`${styles.splitCta} reveal`}
                style={{ transitionDelay: "240ms" }}
              >
                <Link
                  href="/signup"
                  className="btn btn-primary"
                  id="seekers-cta-btn"
                >
                  Start practising →
                </Link>
              </div>
            </div>

            <div
              className={`col-6 ${styles.splitVisual} reveal-scale`}
              style={{ transitionDelay: "160ms" }}
            >
              <div className={styles.readinessCard}>
                <p className="label-xs" style={{ marginBottom: 16 }}>
                  INTERVIEW READINESS
                </p>
                <div className={styles.readinessNum}>
                  <span
                    style={{
                      fontSize: 72,
                      fontWeight: 200,
                      letterSpacing: "-0.04em",
                      lineHeight: 1,
                    }}
                  >
                    74
                  </span>
                  <span
                    className="body-xs"
                    style={{
                      alignSelf: "flex-end",
                      marginBottom: 8,
                      marginLeft: 4,
                    }}
                  >
                    /100
                  </span>
                </div>
                <p
                  className="body-xs mt-8"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  ↑ +8 pts this week
                </p>
                <div
                  className={styles.readinessMiniWave}
                  style={{ marginTop: 20 }}
                >
                  <Waveform bars={20} active={false} height={40} spectral />
                </div>
                <hr className="divider" style={{ margin: "20px 0" }} />
                {MINI_SCORES.map((s) => (
                  <div key={s.label} className={styles.miniScore}>
                    <span className="body-xs">{s.label}</span>
                    <div className={styles.miniScoreTrack}>
                      <div
                        className={styles.miniScoreFill}
                        style={{ width: `${s.val}%` }}
                      />
                    </div>
                    <span className={styles.miniScoreVal}>{s.val}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <hr className="divider" />

      {/* ─── FOR RECRUITERS ────────────────────────────────────────────────── */}
      <section
        className={`${styles.section} ${styles.recruiterSection}`}
        aria-labelledby="recruiters-title"
      >
        <div className={styles.sectionInner}>
          <div className={styles.recruiterInner}>
            <div className={styles.recruiterLeft}>
              <p
                className={`label-sm ${styles.sectionEyebrow} reveal`}
                style={{ color: "rgba(246,243,235,0.5)" }}
              >
                FOR RECRUITERS
              </p>
              <h2
                className={`display-md ${styles.recruiterHeadline} reveal`}
                style={{ transitionDelay: "60ms" }}
                id="recruiters-title"
              >
                Find practised,
                <br />
                prepared candidates.
                <br />
                Free.
              </h2>
              <p
                className={`body-lg reveal`}
                style={{
                  transitionDelay: "120ms",
                  color: "rgba(246,243,235,0.7)",
                  maxWidth: 440,
                }}
              >
                Browse candidates by role, level, and verified readiness score.
                Candidates approve your access. You reach out directly — no
                agency, no fees.
              </p>
            </div>
            <div className={`${styles.recruiterRight} reveal-group`}>
              {RECRUITER_POINTS.map((point, i) => (
                <div
                  key={i}
                  className={`${styles.recruiterPoint} reveal`}
                  style={{ transitionDelay: `${i * 80}ms` }}
                >
                  <span className={styles.recruiterPointNum}>
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p className={styles.recruiterPointTitle}>{point.title}</p>
                    <p
                      className={`body-xs`}
                      style={{ color: "rgba(246,243,235,0.55)", marginTop: 4 }}
                    >
                      {point.desc}
                    </p>
                  </div>
                </div>
              ))}
              <div
                className={`${styles.recruiterCta} reveal`}
                style={{ transitionDelay: "320ms" }}
              >
                <Link
                  href="/recruiter/login"
                  className={styles.recruiterBtn}
                  id="recruiter-cta-btn"
                >
                  Apply as a recruiter →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <hr className="divider" />

      {/* ─── AI DIFFERENTIATOR ─────────────────────────────────────────────── */}
      <section className={styles.section} aria-labelledby="ai-title">
        <div className={styles.sectionInner}>
          <div className={`grid-12 ${styles.aiSection}`}>
            <div className="col-5">
              <p className={`label-sm ${styles.sectionEyebrow} reveal`}>
                OUR AI
              </p>
              <h2
                className={`display-md ${styles.splitHeadline} reveal`}
                style={{ transitionDelay: "60ms" }}
                id="ai-title"
              >
                Not borrowed.
                <br />
                Built for interviews.
              </h2>
            </div>
            <div className="col-7">
              <p className={`body-lg ${styles.aiBody} reveal`}>
                We did not wrap a general-purpose model and call it an interview
                coach. Okkra&apos;s AI is trained specifically on interview
                structure, scoring frameworks, and communication patterns. It
                knows the difference between a strong STAR answer and a vague
                one — because that&apos;s all it does.
              </p>
              <div
                className={`${styles.aiPoints} reveal-group`}
                style={{ marginTop: 32 }}
              >
                {AI_POINTS.map((pt, i) => (
                  <div
                    key={i}
                    className={`${styles.aiPoint} reveal`}
                    style={{ transitionDelay: `${i * 80}ms` }}
                  >
                    <span className={styles.aiPointLine} aria-hidden />
                    <p className="body-sm">{pt}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <hr className="divider" />

      {/* ─── PRICING ───────────────────────────────────────────────────────── */}
      <section
        className={styles.section}
        id="pricing"
        aria-labelledby="pricing-title"
      >
        <div className={styles.sectionInner}>
          <p className={`label-sm ${styles.sectionEyebrow} reveal`}>PRICING</p>
          <h2
            className={`display-md ${styles.sectionHeadline} reveal`}
            style={{ transitionDelay: "60ms" }}
            id="pricing-title"
          >
            Simple. Honest. Flexible.
          </h2>

          {/* Billing toggle */}
          <div
            className={`${styles.billingToggle} reveal`}
            style={{ transitionDelay: "120ms" }}
          >
            <button
              className={`${styles.toggleBtn} ${billing === "monthly" ? styles.toggleActive : ""}`}
              onClick={() => setBilling("monthly")}
              id="billing-monthly-btn"
              aria-pressed={billing === "monthly"}
            >
              Monthly
            </button>
            <button
              className={`${styles.toggleBtn} ${billing === "yearly" ? styles.toggleActive : ""}`}
              onClick={() => setBilling("yearly")}
              id="billing-yearly-btn"
              aria-pressed={billing === "yearly"}
            >
              Yearly
              <span className={styles.saveBadge}>Save ~17%</span>
            </button>
          </div>

          {/* Plans grid */}
          <div className={`${styles.plansGrid} reveal-group`}>
            {PLANS.map((plan, i) => (
              <div
                key={plan.id}
                className={`${styles.planCard} ${plan.highlight ? styles.planCardHighlight : ""} reveal`}
                style={{ transitionDelay: `${i * 70}ms` }}
                aria-label={`${plan.name} plan`}
              >
                {plan.highlight && (
                  <div className={styles.planPopular}>Most popular</div>
                )}
                <div className={styles.planHeader}>
                  <div>
                    <p className={styles.planTag}>{plan.tag}</p>
                    <h3 className={styles.planName}>{plan.name}</h3>
                  </div>
                  <div className={styles.planPrice}>
                    <span className={styles.planPriceNum}>
                      {billing === "monthly" ? plan.monthly : plan.yearly}
                    </span>
                    <span className={styles.planPricePeriod}>
                      /{billing === "monthly" ? "mo" : "yr"}
                    </span>
                  </div>
                </div>
                <p className={styles.planDesc}>{plan.desc}</p>
                <ul
                  className={styles.planFeatures}
                  aria-label={`${plan.name} features`}
                >
                  {plan.features.map((f, fi) => (
                    <li key={fi} className={styles.planFeatureItem}>
                      <span className={styles.planFeatureDot} aria-hidden />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.href}
                  className={`btn ${plan.highlight ? "btn-primary" : "btn-secondary"} w-full ${styles.planCta}`}
                  id={`plan-${plan.id}-cta-btn`}
                  style={{ justifyContent: "center" }}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>

          <p
            className={`body-xs ${styles.pricingNote} reveal`}
            style={{ transitionDelay: "350ms" }}
          >
            Recruiter access is free. Recruiters can view a candidate&apos;s
            resume only after the candidate approves their request.
          </p>
        </div>
      </section>

      <hr className="divider" />

      {/* ─── FINAL CTA ─────────────────────────────────────────────────────── */}
      <section
        className={`${styles.section} ${styles.ctaSection}`}
        aria-labelledby="cta-title"
      >
        <div className={styles.sectionInner}>
          <div className={styles.ctaInner}>
            <p className={`label-sm ${styles.sectionEyebrow} reveal`}>
              GET STARTED
            </p>
            <h2
              className={`display-lg ${styles.ctaHeadline} reveal`}
              style={{ transitionDelay: "60ms" }}
              id="cta-title"
            >
              Your next interview
              <br />
              starts here.
            </h2>
            <div
              className={`${styles.ctaBtns} reveal`}
              style={{ transitionDelay: "140ms" }}
            >
              <Link
                href="/signup"
                className="btn btn-primary btn-lg"
                id="cta-signup-btn"
              >
                Create free account
              </Link>
              <Link
                href="/signin"
                className="btn btn-secondary btn-lg"
                id="cta-signin-btn"
              >
                Sign in
              </Link>
            </div>
            <p
              className={`body-xs reveal`}
              style={{
                transitionDelay: "200ms",
                color: "var(--text-tertiary)",
                marginTop: 16,
              }}
            >
              No credit card required. 3 sessions free every month.
            </p>
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─────────────────────────────────────────────────────────── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerLeft}>
            <div className={styles.footerWordmark}>
              <Image
                src="/okkra-logo.svg"
                alt="Okkra"
                width={145}
                height={54}
                className={styles.footerLogo}
              />
            </div>
            <p
              className="body-xs"
              style={{ color: "var(--text-tertiary)", marginTop: 6 }}
            >
              From Practice to Offer.
            </p>
          </div>
          <nav className={styles.footerLinks} aria-label="Footer navigation">
            {FOOTER_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={styles.footerLink}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <hr className="divider" style={{ marginTop: 24 }} />
        <p className={`body-xs ${styles.footerCopy}`}>
          © {new Date().getFullYear()} Okkra. All rights reserved.
        </p>
      </footer>
    </div>
  );
}

// ─── Static data ──────────────────────────────────────────────────────────────

const STATS = [
  { num: "4,200+", label: "sessions practiced" },
  { num: "380+", label: "vetted recruiters" },
  { num: "92%", label: "report more confidence" },
];

const SEEKER_FEATURES = [
  "AI feedback on structure, clarity, and impact — after every session",
  "Voice and text practice modes for any environment",
  "Weekly readiness score that shows real improvement over time",
  "Built for freshers stepping in and directors stepping up",
  "Your profile is only visible to recruiters you approve",
];

const MINI_SCORES = [
  { label: "Structure", val: 82 },
  { label: "Clarity", val: 76 },
  { label: "Metrics", val: 64 },
];

const RECRUITER_POINTS = [
  {
    title: "Browse by role and readiness",
    desc: "Filter candidates by target role, experience level, and verified AI readiness score.",
  },
  {
    title: "Candidate-controlled access",
    desc: "You see a profile summary. The full resume unlocks only when the candidate approves your request.",
  },
  {
    title: "Direct reach. Zero fees.",
    desc: "Message candidates directly. No agency cut, no placement fee, no middleman.",
  },
];

const AI_POINTS = [
  "Trained on behavioral, case, and technical interview patterns",
  "Understands STAR, SOAR, and narrative communication frameworks",
  "Scores structure, metrics, filler words, and concision separately",
  "No data shared with third-party AI providers",
];

const FOOTER_LINKS = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#pricing", label: "Pricing" },
  { href: "/signup", label: "Sign up" },
  { href: "/signin", label: "Sign in" },
  { href: "/dashboard", label: "App" },
];
