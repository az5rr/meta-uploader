import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const sessionDir = path.join(projectRoot, 'runtime', 'whatsapp_session');
const targetPhone = process.env.WHATSAPP_TARGET_PHONE || '';

const context = await chromium.launchPersistentContext(sessionDir, {
  headless: true,
  channel: 'chromium',
  viewport: { width: 1440, height: 960 },
  locale: 'en-US',
  timezoneId: 'Asia/Muscat',
  userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
  extraHTTPHeaders: { 'Accept-Language': 'en-US,en;q=0.9' },
  args: ['--disable-blink-features=AutomationControlled', '--lang=en-US'],
});
await context.addInitScript(() => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
});
const page = await context.newPage();
await page.goto(`https://web.whatsapp.com/send?phone=${targetPhone}`, { waitUntil: 'networkidle', timeout: 120000 });
await page.waitForTimeout(3000);
const info = await page.evaluate(() => {
  const selectors = ['button', '[role="button"]', 'a', 'div[tabindex]'];
  const out = [];
  for (const sel of selectors) {
    for (const el of document.querySelectorAll(sel)) {
      const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
      if (!text) continue;
      out.push({
        sel,
        text: text.slice(0, 120),
        aria: el.getAttribute('aria-label'),
        title: el.getAttribute('title'),
        tag: el.tagName,
      });
      if (out.length >= 60) break;
    }
    if (out.length >= 60) break;
  }
  return out;
});
console.log(JSON.stringify(info, null, 2));
await context.close();
