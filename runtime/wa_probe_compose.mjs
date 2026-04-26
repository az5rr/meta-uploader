import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const sessionDir = path.join(projectRoot, 'runtime', 'whatsapp_session');
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
await page.goto('https://web.whatsapp.com/', { waitUntil: 'networkidle', timeout: 120000 });
await page.waitForTimeout(3000);
const body = await page.locator('body').innerText().catch(() => '');
const hasFooter = await page.locator('footer [contenteditable="true"]').count();
console.log(JSON.stringify({hasFooter, tail: body.split(/\r?\n/).slice(-20)}, null, 2));
await context.close();
