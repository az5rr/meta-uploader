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
  Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
  Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
  Object.defineProperty(navigator, 'platform', { get: () => 'Linux x86_64' });
});
const page = await context.newPage();
await page.goto(`https://web.whatsapp.com/send?phone=${targetPhone}`, { waitUntil: 'networkidle', timeout: 120000 });
await page.waitForTimeout(3000);
const text = await page.locator('body').innerText().catch(() => '');
const lines = text.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
console.log(JSON.stringify({ last80: lines.slice(-80) }, null, 2));
await context.close();
