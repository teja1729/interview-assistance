/** Voice UX contract: real browser devices, intercepted APIs, no paid calls or user data. */
import assert from "node:assert/strict";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3000";
const browser = await chromium.launch({
  channel: "chromium",
  headless: true,
  args: [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--autoplay-policy=no-user-gesture-required",
  ],
});
const context = await browser.newContext({ permissions: ["microphone"] });
const errors = [];
const audioFixture = Buffer.alloc(44 + 4800);
audioFixture.write("RIFF", 0);
audioFixture.writeUInt32LE(audioFixture.length - 8, 4);
audioFixture.write("WAVEfmt ", 8);
audioFixture.writeUInt32LE(16, 16);
audioFixture.writeUInt16LE(1, 20);
audioFixture.writeUInt16LE(1, 22);
audioFixture.writeUInt32LE(24000, 24);
audioFixture.writeUInt32LE(48000, 28);
audioFixture.writeUInt16LE(2, 32);
audioFixture.writeUInt16LE(16, 34);
audioFixture.write("data", 36);
audioFixture.writeUInt32LE(4800, 40);
await context.addInitScript(() => {
  window.testVoice = {
    speaking: false,
    denyOnce: false,
    tracks: [],
    cloudPlaying: false,
    plays: 0,
    overlap: false,
  };
  const original = navigator.mediaDevices.getUserMedia.bind(
    navigator.mediaDevices,
  );
  navigator.mediaDevices.getUserMedia = async (...args) => {
    if (window.testVoice.denyOnce) {
      window.testVoice.denyOnce = false;
      throw new DOMException("Test denial", "NotAllowedError");
    }
    const stream = await original(...args);
    window.testVoice.overlap ||= window.testVoice.cloudPlaying;
    window.testVoice.tracks.push(...stream.getTracks());
    return stream;
  };
  AnalyserNode.prototype.getByteTimeDomainData = function (array) {
    array.fill(window.testVoice.speaking ? 140 : 128);
  };
  HTMLMediaElement.prototype.play = function () {
    window.testVoice.plays++;
    window.testVoice.cloudPlaying = true;
    setTimeout(() => {
      window.testVoice.cloudPlaying = false;
      this.onended?.(new Event("ended"));
    }, 100);
    return Promise.resolve();
  };
  HTMLMediaElement.prototype.pause = function () {};
  Object.defineProperty(window, "speechSynthesis", {
    value: {
      speak() {
        throw new Error("Robotic browser voice must not be used");
      },
      cancel() {},
    },
  });
});

async function fixture({
  denyOnce = false,
  failedAudio = false,
  voiceEnabled = true,
} = {}) {
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript((deny) => {
    window.testVoice.denyOnce = deny;
  }, denyOnce);
  let turns = 0,
    tts = 0;
  const interview = {
    id: "voice-check",
    job_title: "Engineer",
    company: "",
    persona: "friendly",
    duration_minutes: 5,
    status: "lobby",
    started_at: null,
    remaining_seconds: 300,
    version: 0,
    current_question: "Tell me about a project.",
    closing_remark: null,
    turns: [
      {
        question: "Tell me about a project.",
        answer: null,
        topic: 0,
        at: Date.now() / 1000,
      },
    ],
  };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me")
      return route.fulfill({
        json: {
          user: {
            id: "voice-user",
            name: "Voice Check",
            email: "voice@example.test",
            avatar_url: "",
          },
          account: { id: "voice-account", plan: "free" },
          csrf_token: "test-csrf",
          demo: false,
        },
      });
    if (path === "/api/capabilities")
      return route.fulfill({
        json: { voice_input: voiceEnabled, cloud_voice: voiceEnabled },
      });
    if (path === "/api/tts") {
      tts++;
      if (failedAudio && tts === 1)
        return route.fulfill({
          status: 503,
          json: { detail: "Test voice outage" },
        });
      return route.fulfill({
        contentType: "audio/wav",
        body: audioFixture,
      });
    }
    if (path.endsWith("/join"))
      return route.fulfill({
        json: {
          ...interview,
          status: "active",
          started_at: Date.now() / 1000,
          version: 1,
        },
      });
    if (path.endsWith("/turn")) {
      assert.match(
        route.request().headers()["content-type"],
        /multipart\/form-data/,
      );
      assert(
        route.request().postDataBuffer().includes(Buffer.from("RIFF")),
        "Voice answer must contain recorded WAV audio",
      );
      turns++;
      return route.fulfill({
        json: {
          transcript: "I built and tested a Python service.",
          reply:
            turns === 1 ? "What did you learn?" : "Thank you for your answers.",
          done: turns >= 2,
          repeat: false,
          remaining_seconds: 240,
          version: 1 + turns,
        },
      });
    }
    if (path === "/api/interviews/voice-check")
      return route.fulfill({ json: interview });
    throw new Error(`Unexpected API request: ${path}`);
  });
  await page.goto(`${BASE}/interview/voice-check`);
  return { page, turns: () => turns, tts: () => tts };
}

const phase = (page, expected) =>
  page.waitForFunction(
    (value) =>
      document.querySelector("[data-testid=status]")?.dataset.phase === value,
    expected,
  );
async function spokenTurn(page) {
  await page.evaluate(() => {
    window.testVoice.speaking = true;
  });
  await page.waitForTimeout(1100);
  await page.evaluate(() => {
    window.testVoice.speaking = false;
  });
}
async function tracksStopped(page) {
  assert.equal(
    await page.evaluate(
      () =>
        window.testVoice.tracks.filter((t) => t.readyState === "live").length,
    ),
    0,
  );
}

try {
  const flow = await fixture();
  await flow.page.getByRole("button", { name: "Join now" }).click();
  await phase(flow.page, "recording");
  assert.equal(
    await flow.page.getByRole("textbox", { name: "Your answer" }).count(),
    0,
  );
  await spokenTurn(flow.page);
  await flow.page.waitForFunction(() => window.testVoice.plays === 2);
  await phase(flow.page, "recording");
  assert.equal(flow.turns(), 1);
  assert.equal(await flow.page.evaluate(() => window.testVoice.overlap), false);
  await spokenTurn(flow.page);
  await phase(flow.page, "done");
  assert.equal(flow.turns(), 2);
  await tracksStopped(flow.page);
  await flow.page.close();
  console.log(
    "✓ Cloud question → automatic microphone → speech pause → spoken follow-up; no typing or browser voice",
  );

  const denied = await fixture({ denyOnce: true });
  await denied.page.getByRole("button", { name: "Join now" }).click();
  await denied.page.getByText(/Microphone permission is blocked/).waitFor();
  const retry = denied.page.getByRole("button", { name: "Retry microphone" });
  assert.equal(await retry.isEnabled(), true);
  await retry.click();
  await phase(denied.page, "recording");
  await denied.page.goto(`${BASE}/pricing`);
  await tracksStopped(denied.page);
  await denied.page.close();
  console.log(
    "✓ Denied microphone permission can be retried; navigation releases the microphone",
  );

  const outage = await fixture({ failedAudio: true });
  await outage.page.getByRole("button", { name: "Join now" }).click();
  await outage.page
    .getByRole("button", { name: "Retry question audio" })
    .waitFor();
  await tracksStopped(outage.page);
  await outage.page
    .getByRole("button", { name: "Retry question audio" })
    .click();
  await phase(outage.page, "recording");
  assert.equal(outage.tts(), 2);
  await outage.page.close();
  console.log(
    "✓ Cloud voice failures pause listening and retry without a robotic fallback",
  );

  const disabled = await fixture({ voiceEnabled: false });
  await disabled.page
    .getByText(/voice transcription is not configured/)
    .waitFor();
  await disabled.page.close();
  assert.deepEqual(errors, []);
  console.log("All voice browser checks passed.");
} catch (error) {
  for (const page of context.pages()) {
    console.error(
      await page.evaluate(() => ({
        status: document.querySelector("[data-testid=status]")?.textContent,
        phase: document
          .querySelector("[data-testid=status]")
          ?.getAttribute("data-phase"),
        plays: window.testVoice?.plays,
      })),
    );
  }
  console.error("Browser errors:", errors);
  throw error;
} finally {
  await browser.close();
}
