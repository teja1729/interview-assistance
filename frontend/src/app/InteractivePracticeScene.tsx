"use client";

import { useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import styles from "./page.module.css";

const views = [
  {
    id: "context",
    tab: "Your context",
    status: "RESUME CONTEXT",
    tag: "YOUR RESUME",
    tagDetail: "Experience in focus",
    title: "A story from your actual work.",
    label: "CONTEXT, NOT A SCRIPT",
    footer: "BASED ON YOUR EXPERIENCE",
    icon: "file",
    badge: "Resume matched",
  },
  {
    id: "practice",
    tab: "Live practice",
    status: "LIVE PRACTICE",
    tag: "VOICE INTERVIEW",
    tagDetail: "Listening to your answer",
    title: "What was the hardest trade-off you made on that project?",
    label: "OKKRA ASKS",
    footer: "A FOLLOW-UP THAT LISTENS",
    icon: "mic",
    badge: "Your turn to think",
  },
  {
    id: "feedback",
    tab: "Useful feedback",
    status: "COACHING NOTE",
    tag: "NEXT REP",
    tagDetail: "Make the outcome clearer",
    title: "You explained the decision. Now connect it to the result.",
    label: "ONE USEFUL NEXT STEP",
    footer: "GROUNDED IN YOUR ANSWER",
    icon: "spark",
    badge: "Keep building",
  },
] as const;

export function InteractivePracticeScene() {
  const stageRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(1);
  const view = views[active];

  function movePointer(event: React.PointerEvent<HTMLDivElement>) {
    if (event.pointerType === "touch" || !stageRef.current) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    stageRef.current.style.setProperty("--tilt-x", `${-y * 3}deg`);
    stageRef.current.style.setProperty("--tilt-y", `${x * 4}deg`);
  }

  function resetPointer() {
    stageRef.current?.style.setProperty("--tilt-x", "0deg");
    stageRef.current?.style.setProperty("--tilt-y", "0deg");
  }

  return (
    <div className={`${styles.stageWrap} enter`} style={{ animationDelay: ".12s" }}>
      <div className={styles.stageGlow} />
      <div
        ref={stageRef}
        className={styles.stage}
        onPointerMove={movePointer}
        onPointerLeave={resetPointer}
        role="group"
        aria-label="Interactive preview of Okkra's practice flow"
      >
        <div className={styles.stageGrid} />
        <div className={styles.stageHeader}>
          <div className={styles.liveLabel}><span className={styles.liveDot} /> {view.status}</div>
          <div className={styles.sessionTime}>0{active + 1} <span> / 03</span></div>
        </div>

        <div className={styles.stageTabs} role="group" aria-label="Explore the practice flow">
          {views.map((item, index) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={active === index}
              className={active === index ? styles.stageTabActive : styles.stageTab}
              onClick={() => setActive(index)}
            >
              <span>0{index + 1}</span>{item.tab}
            </button>
          ))}
        </div>

        <div className={styles.orbitScene} aria-hidden="true">
          <div className={`${styles.orbit} ${styles.orbitA}`} />
          <div className={`${styles.orbit} ${styles.orbitB}`} />
          <div className={styles.orbitDot} />
          <div className={styles.coreGlow} />
          <div className={styles.core}><Icon name="mic" className="h-8 w-8" /></div>
          <div className={styles.soundWave}>
            {[12, 20, 30, 18, 25, 36, 22, 31, 16, 27, 38, 20, 29, 15, 24, 34, 19, 28, 13, 23, 32, 18, 27, 14, 21, 30, 17, 26].map((height, index) => (
              <span key={index} style={{ "--bar-height": `${height}px`, "--bar-delay": `${index * -0.045}s` } as React.CSSProperties} />
            ))}
          </div>
        </div>

        <div key={`tag-${view.id}`} className={`${styles.floatTag} ${styles.tagTop} ${styles.panelIn}`}>
          <span className={styles.tagIcon}><Icon name={view.icon} className="h-4 w-4" /></span>
          <span><strong>{view.tag}</strong><small>{view.tagDetail}</small></span>
          <Icon name="check" className={styles.tagCheck} />
        </div>
        <div className={`${styles.floatTag} ${styles.tagBottom}`}>
          <span className={styles.scoreRing}>+<br /><b>1</b></span>
          <span><strong>{view.badge.toUpperCase()}</strong><small>Small steps, real progress</small></span>
        </div>

        <div key={`question-${view.id}`} className={`${styles.questionCard} ${styles.panelIn}`} aria-live="polite">
          <div className={styles.questionMeta}><span className={styles.avatar}>O</span> {view.label} <span className={styles.questionPulse} /></div>
          <p>{view.title}</p>
          <div className={styles.questionFoot}><span>{view.footer}</span><span>BUILT AROUND YOU</span></div>
        </div>
        <div className={styles.stageCaption}>Choose a step to explore the practice loop.</div>
      </div>
    </div>
  );
}
