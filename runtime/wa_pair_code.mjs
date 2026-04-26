import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const runtimeDir = path.join(projectRoot, 'runtime');
const sessionDir = path.join(runtimeDir, 'whatsapp_session');
const outputDir = path.join(runtimeDir, 'whatsapp_output');
const targetPhone = process.env.WHATSAPP_TARGET_PHONE || '';

for (const dir of [sessionDir, outputDir]) {
  fs.mkdirSync(dir, { recursive: true });
}

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

const loginWithPhone = page.getByText('Log in with phone number', { exact: false });
if (await loginWithPhone.isVisible().catch(() => false)) {
  await loginWithPhone.click();
  await page.waitForTimeout(3000);
}

await page.screenshot({ path: path.join(outputDir, 'whatsapp-phone-login.png') }).catch(() => {});
const html = await page.content().catch(() => '');
fs.writeFileSync(path.join(outputDir, 'whatsapp-phone-login.html'), html, 'utf8');
const text = await page.locator('body').innerText().catch(() => '');
console.log(text);
await context.close();
