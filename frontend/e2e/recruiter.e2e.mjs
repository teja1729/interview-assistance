/** Real database consent workflow using three isolated identities. No OAuth or paid AI calls.
 * See RUN.md: start the fixture stack, then pass its /tmp DB as RECRUITER_E2E_DATABASE_URL.
 * The seed helper refuses normal application databases; it adds no production bypass endpoint.
 */
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:3200";
const database = process.env.RECRUITER_E2E_DATABASE_URL;
assert(
  database?.startsWith("sqlite:////tmp/suri-browser-tests-"),
  "Provide the isolated test database URL",
);
const identities = JSON.parse(
  execFileSync(
    "../backend/.venv/bin/python",
    ["../backend/tests/seed_recruiter_browser.py"],
    { env: process.env, encoding: "utf8" },
  ),
);
const OUT = process.env.SHOTS ?? "e2e/shots/recruiter";
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ headless: true });
const errors = [];
async function open(identity) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
  });
  if (identity)
    await context.addCookies([
      {
        name: "interview_session",
        value: identity.token,
        url: BASE,
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  return { context, page };
}
async function mobile(page, name) {
  await page.setViewportSize({ width: 390, height: 844 });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    `${name} overflows on mobile`,
  );
  await page.screenshot({ path: `${OUT}/${name}-mobile.png`, fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
}
try {
  const anonymous = await open();
  await anonymous.page.goto(`${BASE}/recruiter`);
  await anonymous.page.waitForURL("**/recruiter/login?**");
  await anonymous.page
    .getByRole("heading", { name: "Meet your next candidate." })
    .waitFor();
  await mobile(anonymous.page, "recruiter-login");
  let returnTo;
  await anonymous.page.route("**/api/auth/google?**", (route) => {
    returnTo = new URL(route.request().url()).searchParams.get("next");
    return route.fulfill({
      status: 200,
      body: "OAuth redirect intercepted for browser test",
    });
  });
  await anonymous.page
    .getByRole("link", { name: "Continue with Google" })
    .click();
  await anonymous.page.waitForURL("**/api/auth/google?**");
  assert.equal(returnTo, "/recruiter");
  console.log(
    "✓ Separate recruiter login preserves its Google return destination",
  );

  const candidate = await open(identities.candidate);
  const recruiter = await open(identities.recruiter);
  const stranger = await open(identities.stranger);
  await recruiter.page.goto(`${BASE}/recruiter`);
  await recruiter.page.getByLabel("Company name").fill("Example Hiring Team");
  await recruiter.page.getByLabel("Your job title").fill("Talent Partner");
  await recruiter.page
    .getByRole("button", { name: "Create recruiter profile" })
    .click();
  await recruiter.page
    .getByRole("heading", { name: "Candidate directory" })
    .waitFor();
  const name = `Candidate ${Date.now()}`;
  await candidate.page.goto(`${BASE}/resumes`);
  await candidate.page
    .getByLabel("Name", { exact: true })
    .fill("Shared engineering resume");
  const original =
    "ORIGINAL RESUME: Built Python services for four years. Reduced database latency through indexed queries and measured rollout results.";
  await candidate.page.getByLabel("File (PDF or .txt)").setInputFiles({
    name: "candidate.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(original),
  });
  await candidate.page
    .getByRole("button", { name: "Upload", exact: true })
    .click();
  await candidate.page
    .getByText("Shared engineering resume", { exact: true })
    .first()
    .waitFor();
  await candidate.page.goto(`${BASE}/opportunities`);
  await candidate.page.getByLabel("Display name", { exact: true }).fill(name);
  await candidate.page
    .getByLabel("Headline", { exact: true })
    .fill(`Backend engineer ${name}`);
  await candidate.page
    .getByLabel("Target role", { exact: true })
    .fill("Software Engineer");
  await candidate.page.getByLabel("Years of experience").fill("4");
  await candidate.page
    .getByLabel("Skills, separated by commas")
    .fill("Python, PostgreSQL");
  await candidate.page
    .getByLabel("Resume to share after approval")
    .selectOption({ label: "Shared engineering resume" });
  await candidate.page
    .getByLabel("Let signed-in recruiters discover my profile")
    .check();
  await candidate.page
    .getByRole("button", { name: "Save candidate profile" })
    .click();
  await candidate.page
    .getByRole("status")
    .filter({ hasText: "visible to signed-in recruiters" })
    .waitFor();
  await mobile(candidate.page, "candidate-profile");
  await recruiter.page.getByLabel("Role, headline or location").fill(name);
  await recruiter.page
    .getByRole("button", { name: "Search", exact: true })
    .click();
  await recruiter.page.getByRole("heading", { name, exact: true }).waitFor();
  assert.equal(
    await recruiter.page.getByText(identities.candidate.email).count(),
    0,
  );
  await mobile(recruiter.page, "candidate-directory");
  await recruiter.page
    .getByRole("button", { name: "Request resume", exact: true })
    .click();
  await recruiter.page
    .getByRole("textbox", { name: /Tell .* about the opportunity/ })
    .fill(
      "We are hiring a Python engineer. Would you like to discuss the role?",
    );
  await recruiter.page
    .getByRole("button", { name: "Send request", exact: true })
    .click();
  await recruiter.page
    .getByRole("status")
    .filter({ hasText: "Request sent" })
    .waitFor();
  const requests = await (
    await recruiter.context.request.get(`${BASE}/api/recruiter/requests`)
  ).json();
  const request = requests[0];
  assert.equal(
    (
      await recruiter.context.request.get(
        `${BASE}/api/recruiter/requests/${request.id}/resume`,
      )
    ).status(),
    403,
  );
  console.log(
    "✓ Candidate publication, directory filtering and pending consent use the real API",
  );

  await candidate.page.reload();
  await candidate.page
    .getByRole("button", { name: "Approve resume & email" })
    .click();
  await candidate.page.getByRole("button", { name: "Revoke access" }).waitFor();
  await recruiter.page.goto(`${BASE}/recruiter/requests`);
  await recruiter.page
    .getByRole("button", { name: "View resume & contact" })
    .click();
  await recruiter.page.getByText(original, { exact: true }).waitFor();
  await recruiter.page
    .getByRole("link", { name: identities.candidate.email, exact: true })
    .waitFor();
  await recruiter.page.screenshot({
    path: `${OUT}/approved-resume.png`,
    fullPage: true,
  });
  await mobile(recruiter.page, "approved-resume");
  assert.equal(
    (
      await stranger.context.request.get(
        `${BASE}/api/recruiter/requests/${request.id}/resume`,
      )
    ).status(),
    403,
  );
  await candidate.page
    .getByLabel("Let signed-in recruiters discover my profile")
    .uncheck();
  await candidate.page
    .getByRole("button", { name: "Save candidate profile" })
    .click();
  await candidate.page
    .getByRole("status")
    .filter({ hasText: "saved privately" })
    .waitFor();
  assert.equal(
    (
      await recruiter.context.request.get(
        `${BASE}/api/recruiter/requests/${request.id}/resume`,
      )
    ).status(),
    403,
  );
  await recruiter.page.reload();
  await recruiter.page.getByText("revoked", { exact: true }).waitFor();
  assert.equal(
    await recruiter.page
      .getByRole("button", { name: "View resume & contact" })
      .count(),
    0,
  );
  await candidate.page.goto(`${BASE}/progress`);
  await candidate.page
    .getByRole("heading", { name: "Your score over time" })
    .waitFor();
  await mobile(candidate.page, "progress");
  assert.deepEqual(errors, []);
  console.log(
    "✓ Approval reveals only original resume text and email; withdrawal revokes future reads",
  );
  console.log(
    "✓ Recruiter, candidate and progress screens fit mobile; no uncaught browser errors",
  );
} finally {
  await browser.close();
}
