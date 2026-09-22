/** Login availability regression. Uses no accounts, model calls or application writes. */
import assert from "node:assert/strict";
import fs from "node:fs";
import { chromium } from "playwright";

const base = process.env.BASE ?? "http://localhost:3000";
const browser = await chromium.launch({ channel: "chromium", headless: true });
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
try {
  const response = await page.request.get(`${base}/api/auth/config`);
  assert(
    response.ok(),
    "Auth config unavailable: check for a stale backend on the API port",
  );
  const actual = await response.json();
  await page.goto(`${base}/login`);
  if (actual.google_enabled) {
    await page.getByRole("link", { name: "Continue with Google" }).waitFor();
    const redirect = await page.request.get(`${base}/api/auth/google`, {
      maxRedirects: 0,
    });
    assert.equal(redirect.status(), 302);
    const destination = new URL(redirect.headers().location);
    assert.equal(destination.hostname, "accounts.google.com");
    assert.equal(
      destination.searchParams.get("redirect_uri"),
      `${base}/api/auth/google/callback`,
    );
    for (const key of ["state", "nonce", "code_challenge"])
      assert(destination.searchParams.get(key));
    console.log(
      "✓ Live Google option and authorization redirect are available",
    );
  } else {
    await page.getByText(/Google sign-in is awaiting configuration/).waitFor();
  }
  fs.mkdirSync("e2e/shots", { recursive: true });
  await page.screenshot({ path: "e2e/shots/login-actual.png", fullPage: true });

  let status = 404;
  let options = { google_enabled: true, demo_enabled: false };
  await page.route("**/api/auth/config", (route) =>
    route.fulfill({
      status,
      json: status === 200 ? options : { detail: "Not Found" },
    }),
  );
  await page.reload();
  await page
    .getByRole("alert")
    .filter({ hasText: "Sign-in is temporarily unavailable" })
    .waitFor();
  assert.equal(await page.getByText(/awaiting configuration/).count(), 0);
  status = 200;
  await page.getByRole("button", { name: "Retry sign-in options" }).click();
  await page.getByRole("link", { name: "Continue with Google" }).waitFor();
  console.log(
    "✓ Failed auth discovery shows a recoverable service error, and retry restores Google sign-in",
  );

  await page.goto(`${base}/login?error=google`);
  await page
    .getByRole("alert")
    .filter({ hasText: "Google sign-in could not be completed" })
    .waitFor();
  await page.getByRole("link", { name: "Continue with Google" }).waitFor();
  console.log(
    "✓ Google callback failure is visible and allows another sign-in attempt",
  );

  options = { google_enabled: false, demo_enabled: true };
  await page.goto(`${base}/login`);
  await page.getByText(/Google sign-in is awaiting configuration/).waitFor();
  await page.getByRole("button", { name: "Open local test account" }).waitFor();
  assert.equal(
    await page.getByRole("link", { name: "Continue with Google" }).count(),
    0,
  );
  assert.deepEqual(errors, []);
  console.log(
    "✓ Unconfigured Google and demo availability remain distinct; no browser exceptions",
  );
} finally {
  await browser.close();
}
