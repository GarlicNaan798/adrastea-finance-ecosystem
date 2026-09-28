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
    // A cold container boots blank for a while after waking, so wait generously and
    // reload once if the first attempt times out (the observed failure mode).
    const app = () => page.frameLocator('iframe[title="streamlitApp"]');
    const appIsUp = async (timeout) => {
      try {
        await app().getByText(LIVE_APP).first().waitFor({ state: "visible", timeout });
        return true;
      } catch { return false; }
    };
    let up = await appIsUp(300000);            // 5 min - covers a cold boot after wake
    if (!up) {
      console.log("Not rendered yet; reloading and waiting once more...");
      await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
      up = await appIsUp(180000);              // another 3 min
    }
    if (!up) {
      console.error("App did not render inside the iframe within the timeout. Diagnostics:");
      console.error("  page title:", await page.title());
      console.error("  frames:", page.frames().map((f) => f.url()));
      try {
        const t = await app().locator("body").innerText();
        console.error("  app-frame text sample:", (t || "").slice(0, 300).replace(/\n+/g, " | "));
      } catch (e) { console.error("  could not read app frame:", e.message); }
      process.exit(1);
    }
    console.log("Live app rendered inside the Streamlit iframe (login visible).");

    // Linger so the websocket session is fully established (a genuine "view").
    await page.waitForTimeout(15000);
    console.log("Done. Page title:", await page.title());
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error("keepalive failed:", e); process.exit(1); });
