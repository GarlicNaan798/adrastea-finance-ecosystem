// Loads the Streamlit app in a headless browser so Streamlit Community Cloud
// registers a real view (resets the inactivity-sleep timer). If the app is asleep
// it clicks the wake button, then CONFIRMS the live app actually rendered - so the
// job fails loudly instead of passing green while the app is still asleep.
//
// IMPORTANT: Community Cloud serves the app INSIDE an iframe (title="streamlitApp").
// The app's DOM (login, widgets) lives in that frame, NOT the top document - so we
// look for the app via frameLocator, and only the sleep/wake screen (if any) on the
// top wrapper. Used by .github/workflows/keep-alive.yml.
const { chromium } = require("playwright");

// A string only the *rendered* app shows (its login screen).
const LIVE_APP = /held to account|Create account|Sign in/i;

(async () => {
  // Normalize the secret: trim, strip stray quotes, add https:// if the scheme was
  // omitted (a bare "name.streamlit.app" throws "Cannot navigate to invalid URL").
  let url = (process.env.APP_URL || "").trim().replace(/^['"]|['"]$/g, "");
  if (!url) { console.error("APP_URL not set"); process.exit(1); }
  if (!/^https?:\/\//i.test(url)) url = "https://" + url;
  try { new URL(url); } catch {
    console.error("APP_URL is not a valid URL - check the secret has https:// and no "
      + "spaces/quotes/newlines.");
    process.exit(1);
  }

  const browser = await chromium.launch();
  const page = await browser.newPage();
  try {
    // Not "networkidle": Streamlit holds a websocket open, so it never idles.
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });

    // The sleep "wake" button (if the app is asleep) lives on the wrapper/top frame.
    // Wait briefly for it; absent => the app isn't asleep.
    const wake = page.getByRole("button", { name: /get this app back up|wake|back up/i });
    try {
      await wake.first().waitFor({ state: "visible", timeout: 20000 });
      console.log("Sleep screen detected -> clicking wake button");
      await wake.first().click();
    } catch {
      console.log("No wake button (app not asleep, or already waking).");
    }

    // The real app is INSIDE the Streamlit iframe - confirm the login rendered there.
    // Generous timeout: a cold container can take a while to boot after waking.
    const app = page.frameLocator('iframe[title="streamlitApp"]');
    try {
      await app.getByText(LIVE_APP).first().waitFor({ state: "visible", timeout: 180000 });
      console.log("Live app rendered inside the Streamlit iframe (login visible).");
    } catch {
      console.error("App did not render inside the iframe within the timeout - it may "
        + "still be asleep or the container failed to boot. Failing loudly.");
      process.exit(1);
    }

    // Linger so the websocket session is fully established (a genuine "view").
    await page.waitForTimeout(15000);
    console.log("Done. Page title:", await page.title());
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error("keepalive failed:", e); process.exit(1); });
