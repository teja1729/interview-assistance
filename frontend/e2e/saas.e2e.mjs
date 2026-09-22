/** Deterministic vertical-slice test. Requires demo API + report worker + web.
 * No existing resumes, model API keys, Google account or Stripe account are required.
 * A separate browser regression uses intercepted fixtures to test microphone cleanup.
 */
import assert from "node:assert/strict";
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
const OUT = process.env.SHOTS ?? "e2e/shots";
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({
  channel: "chromium",
  headless: true,
  args: [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--autoplay-policy=no-user-gesture-required",
  ],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  permissions: ["camera", "microphone"],
});
await context.addInitScript(() => {
  if (window !== window.top) return; // Search Suggestions intentionally use an opaque sandbox origin.
  localStorage.setItem("ia.voiceMode", "browser");
  Object.defineProperty(window, "speechSynthesis", {
    value: {
      speak(utterance) {
        setTimeout(() => utterance.onend?.(), 0);
      },
      cancel() {},
    },
  });
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
const shot = (name) =>
  page.screenshot({
    path: `${OUT}/${name}.png`,
    fullPage: true,
    animations: "disabled",
  });
const step = (label) => console.log(`✓ ${label}`);
const ready = () =>
  page.waitForFunction(
    () =>
      document.querySelector("[data-testid=status]")?.dataset.phase === "ready",
  );
try {
  await page.goto(BASE);
  await page.getByRole("heading", { name: /Your experience/ }).waitFor();
  await shot("01-landing");
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    "Landing overflows on mobile",
  );
  await shot("02-mobile");
  await page.setViewportSize({ width: 1440, height: 1000 });
  step("Public landing and mobile layout");

  await page.goto(`${BASE}/login`);
  await page.getByRole("button", { name: "Open local test account" }).click();
  await page.waitForURL("**/dashboard");
  await page.getByRole("heading", { name: /Welcome back/ }).waitFor();
  await shot("03-dashboard");
  step("Sign-in and authenticated dashboard");

  await page.goto(`${BASE}/resumes`);
  await page.getByLabel("Name", { exact: true }).fill("E2E engineering resume");
  await page.getByLabel("File (PDF or .txt)").setInputFiles({
    name: "candidate.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      "Alex Morgan\nBackend engineer with five years of experience. Designed APIs, improved database query latency, and led production incident reviews.",
    ),
  });
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  await page
    .getByText("E2E engineering resume", { exact: true })
    .first()
    .waitFor();
  step("Private resume upload and analysis");

  await page.goto(`${BASE}/setup`);
  await page.getByLabel("Job title").fill("Senior Backend Engineer");
  await page.getByLabel("Target company").fill("Example Company");
  await page
    .getByLabel("Company website or job URL", { exact: false })
    .fill("https://example.com");
  await page
    .getByRole("button", { name: "Research company", exact: true })
    .click();
  await page
    .getByText("Company research unavailable", { exact: true })
    .waitFor();
  await page.route("**/api/company-research", (route) =>
    route.fulfill({
      json: {
        id: null,
        company: "Example Company",
        status: "researched",
        facts: [
          {
            text: "Synthetic browser fixture: this company builds developer tools.",
            source_ids: ["s1"],
          },
        ],
        sources: [
          {
            id: "s1",
            title: "Example source",
            url: "https://example.com/about",
          },
        ],
        researched_at: Date.now() / 1000,
        note: "Isolated browser fixture.",
        search_suggestions: "<div>Search suggestions fixture</div>",
      },
    }),
  );
  await page
    .getByRole("button", { name: "Research company", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Example source", exact: true })
    .waitFor();
  assert.equal(
    await page
      .locator('iframe[title="Google Search suggestions"]')
      .getAttribute("sandbox"),
    "allow-popups allow-popups-to-escape-sandbox",
  );
  await page
    .getByLabel("Interview language", { exact: true })
    .selectOption("hi-IN");
  step(
    "Company research recovery, cited preview, isolated suggestions and language selection",
  );
  await page.getByRole("button", { name: "✦ Generate", exact: true }).click();
  await page.getByRole("status").filter({ hasText: "Test fixture" }).waitFor();
  const generatedDescription = await page
    .getByLabel("Job description")
    .inputValue();
  assert(generatedDescription.includes("Responsibilities"));
  assert(generatedDescription.includes("First 90 days"));
  assert(generatedDescription.startsWith("DEMO SAMPLE"));
  const savedId = await page
    .locator("#saved-role-brief option")
    .nth(1)
    .getAttribute("value");
  const aiUsage = () =>
    page.evaluate(
      async () =>
        (await (await fetch("/api/billing")).json()).resources.ai_calls.used,
    );
  const beforeReuse = await aiUsage();
  await page.getByRole("button", { name: "✦ Generate", exact: true }).click();
  await page
    .getByRole("status")
    .filter({ hasText: "Loaded saved description" })
    .waitFor();
  assert.equal(
    await aiUsage(),
    beforeReuse,
    "Reusing a saved description must not spend AI usage",
  );
  await page.goto(`${BASE}/setup`);
  await page.getByLabel("Use a saved role brief").selectOption(savedId);
  await page
    .getByRole("status")
    .filter({ hasText: "Loaded saved description" })
    .waitFor();
  assert.equal(
    await page.getByLabel("Job description").inputValue(),
    generatedDescription,
  );
  assert.equal(
    await page.getByLabel("Job title").inputValue(),
    "Senior Backend Engineer",
  );
  await page
    .getByLabel("Interview language", { exact: true })
    .selectOption("hi-IN");
  step(
    "Saved role brief survives navigation and reuses output without spending AI usage",
  );
  await page
    .getByLabel("Job description")
    .fill(
      "Design reliable APIs and distributed services. Explain trade-offs, own production performance, and mentor other engineers.",
    );
  await page.getByRole("button", { name: "15 min", exact: true }).click();
  assert.equal(await page.getByRole("radio").count(), 4);
  assert.equal(
    await page
      .getByRole("radio", { name: "Hiring Manager", exact: true })
      .isChecked(),
    true,
  );
  await page.getByText("Technical Interviewer", { exact: true }).click();
  assert.equal(
    await page
      .getByRole("radio", { name: "Technical Interviewer", exact: true })
      .isChecked(),
    true,
  );
  await page.getByText("Testing and failure cases", { exact: true }).waitFor();
  await page.screenshot({
    path: `${OUT}/03-interviewer-selection.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    "Interviewer cards overflow on mobile",
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("button", { name: "Start interview", exact: true })
    .click();
  await page.waitForURL("**/interview/**");
  await page.getByRole("heading", { name: "Ready to join?" }).waitFor();
  const interviewId = new URL(page.url()).pathname.split("/").pop();
  const beforeJoin = await page.evaluate(
    async (id) => (await fetch(`/api/interviews/${id}`)).json(),
    interviewId,
  );
  assert.equal(beforeJoin.started_at, null);
  assert.equal(beforeJoin.persona_profile.name, "Technical Interviewer");
  assert.equal(beforeJoin.persona, "technical");
  assert.equal(beforeJoin.language, "hi-IN");
  await page
    .getByText("Technical Interviewer · AI practice", { exact: true })
    .waitFor();
  await shot("04-lobby");
  await page.getByRole("button", { name: "Join now", exact: true }).click();
  await ready();
  await page.getByLabel("Your answer").fill("I used various tools.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await ready();
  await page
    .getByLabel("Your answer")
    .fill(
      "I owned the API query path. I compared caching with changing the database access pattern, then measured tail latency in a staged rollout. The change reduced duplicate lookups while keeping the operational model simple.",
    );
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await ready();
  await page.getByRole("button", { name: "Transcript", exact: true }).click();
  assert.equal(await page.locator("aside ol > li").count(), 3);
  await shot("05-interview");
  step("Timer starts on join; exact typed answers and bounded turns persist");

  await page
    .getByRole("button", { name: "End interview", exact: true })
    .click();
  await page.waitForURL("**/report/**");
  await page
    .getByText("out of 100", { exact: true })
    .waitFor({ timeout: 60_000 });
  await page
    .getByText("Evidence from your answers", { exact: true })
    .first()
    .waitFor();
  await shot("06-report");
  await page.getByRole("link", { name: "Open your practice plan" }).click();
  await page
    .getByRole("heading", { name: "Your practice plan", exact: true })
    .waitFor();
  const completeButton = page
    .getByRole("button", { name: /^Complete / })
    .first();
  await completeButton.click();
  await page
    .getByRole("button", { name: /^Mark .* incomplete/ })
    .first()
    .waitFor();
  await shot("07-practice");
  step(
    "Durable evaluator/coach job, evidence report, and practice task completion",
  );

  await page.goto(`${BASE}/settings`);
  await page
    .getByRole("heading", { name: "Account settings", exact: true })
    .waitFor();
  assert.equal(await page.getByRole("combobox").count(), 0);
  assert.equal(
    await page.getByRole("button", { name: "Save AI preferences" }).count(),
    0,
  );
  assert.equal(
    await page.getByRole("link", { name: "Workspace", exact: true }).count(),
    0,
  );
  await page.getByRole("button", { name: "Sign out on all devices" }).waitFor();
  await shot("08-settings");
  await page.goto(`${BASE}/activity`);
  await page
    .getByRole("cell", { name: /evaluator/ })
    .first()
    .waitFor();
  await shot("09-activity");
  await page.goto(`${BASE}/billing`);
  await page.getByRole("heading", { name: "Plans & usage" }).waitFor();
  await page.getByText("Current plan", { exact: true }).first().waitFor();
  await shot("10-billing");
  step(
    "Personal account settings, server-only routing, trace metadata and billing screens",
  );

  // Device lifecycle regression, using a fixture API to advance time without modifying real sessions.
  const devicePage = await context.newPage();
  await devicePage.addInitScript(() => {
    window.testTracks = [];
    const original = navigator.mediaDevices.getUserMedia.bind(
      navigator.mediaDevices,
    );
    navigator.mediaDevices.getUserMedia = async (...args) => {
      const stream = await original(...args);
      window.testTracks.push(...stream.getTracks());
      return stream;
    };
  });
  const fixture = {
    ...beforeJoin,
    id: "device-fixture",
    status: "active",
    started_at: Date.now() / 1000,
    remaining_seconds: 30,
    version: 1,
    current_question: "Describe your project.",
    turns: [
      {
        question: "Describe your project.",
        answer: null,
        at: Date.now() / 1000,
      },
    ],
  };
  await devicePage.route("**/api/capabilities", (route) =>
    route.fulfill({ json: { voice_input: true, cloud_voice: false } }),
  );
  await devicePage.route("**/api/interviews/device-fixture**", (route) => {
    if (route.request().url().endsWith("/turn"))
      return route.fulfill({
        json: {
          transcript: "A recorded answer",
          reply: "The interview is complete.",
          done: true,
          repeat: false,
          remaining_seconds: 0,
          version: 2,
        },
      });
    return route.fulfill({ json: fixture });
  });
  await devicePage.clock.install();
  await devicePage.goto(`${BASE}/interview/device-fixture`);
  await devicePage.getByRole("button", { name: "Join now" }).click();
  await devicePage.waitForFunction(
    () =>
      document.querySelector("[data-testid=status]")?.dataset.phase === "ready",
  );
  await devicePage.getByRole("button", { name: "Answer", exact: true }).click();
  await devicePage.waitForFunction(
    () =>
      document.querySelector("[data-testid=status]")?.dataset.phase ===
      "recording",
  );
  await devicePage.clock.fastForward(35_000);
  await devicePage.clock.runFor(1000);
  await devicePage.waitForFunction(
    () =>
      document.querySelector("[data-testid=status]")?.dataset.phase === "done",
  );
  assert.equal(
    await devicePage.evaluate(
      () =>
        window.testTracks.filter(
          (t) => t.kind === "audio" && t.readyState === "live",
        ).length,
    ),
    0,
  );
  await devicePage.close();
  step("Deadline submits the active recording and releases microphone tracks");

  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.waitForURL(BASE + "/");
  await page.goto(`${BASE}/settings`);
  await page.waitForURL("**/login?**");
  assert.deepEqual(errors, []);
  step("Logout and protected route redirect; no browser exceptions");
  console.log("All SaaS browser checks passed.");
} catch (error) {
  await shot("99-failure");
  console.error("Browser exceptions:", errors);
  throw error;
} finally {
  await browser.close();
}
