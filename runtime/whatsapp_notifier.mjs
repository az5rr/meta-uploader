import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const runtimeDir = path.join(projectRoot, "runtime");
const sessionDir = path.join(runtimeDir, "whatsapp_session");
const outputDir = path.join(runtimeDir, "whatsapp_output");
const statePath = path.join(runtimeDir, "whatsapp_notifier_state.json");

for (const dir of [runtimeDir, sessionDir, outputDir]) {
  fs.mkdirSync(dir, { recursive: true });
}

function loadEnv(filePath) {
  if (!fs.existsSync(filePath)) return;
  const content = fs.readFileSync(filePath, "utf8");
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const index = line.indexOf("=");
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim();
    if (!(key in process.env)) process.env[key] = value;
  }
}

loadEnv(path.join(projectRoot, ".env"));

const pythonBin = process.env.META_UPLOADER_PYTHON || path.join(projectRoot, ".venv", "bin", "python");
const prepareScript = path.join(projectRoot, "bin", "prepare_and_schedule.py");

const config = {
  apiBase: process.env.META_UPLOADER_API_BASE || "http://127.0.0.1:8000",
  targetPhone: (process.env.WHATSAPP_TARGET_PHONE || "").replace(/[^\d]/g, ""),
  checkIntervalSeconds: Number(process.env.WHATSAPP_CHECK_INTERVAL_SECONDS || "10"),
  reelsLowThreshold: Number(process.env.WHATSAPP_REELS_LOW_THRESHOLD || "3"),
  timezone: process.env.WHATSAPP_STATUS_TIMEZONE || "Asia/Muscat",
  headed: (process.env.WHATSAPP_HEADLESS || "false").toLowerCase() !== "true",
  loginOnly: process.argv.includes("--login-only"),
  sendStatusNow: process.argv.includes("--send-status"),
};

if (!config.targetPhone) {
  throw new Error("WHATSAPP_TARGET_PHONE is required");
}

const COMMANDS = new Set([
  "status",
  "jobs",
  "reel-links",
  "queue",
  "next-id",
  "last-upload",
  "today-report",
  "help",
]);

const COMMAND_ALIASES = {
  "reel links": "reel-links",
  "need reels": "reel-links",
  "next": "next-id",
  "health": "status",
};

function createDefaultState() {
  return {
    healthUp: null,
    loginRequired: null,
    lastNextJobId: null,
    lastHandledInboundSignature: null,
    reelsLowAlerted: false,
    notifiedPublishedJobIds: [],
    notifiedFailedJobIds: [],
    processedCommandCounts: {},
    processedLinkCounts: {},
    processedCommandSignatures: [],
    processedLinkSignatures: [],
    acceptedSourceLinks: [],
  };
}

function readState() {
  if (!fs.existsSync(statePath)) {
    return createDefaultState();
  }
  const raw = JSON.parse(fs.readFileSync(statePath, "utf8"));
  return {
    ...createDefaultState(),
    healthUp: raw.healthUp ?? null,
    loginRequired: raw.loginRequired ?? null,
    lastNextJobId: raw.lastNextJobId ?? null,
    lastHandledInboundSignature: raw.lastHandledInboundSignature || null,
    reelsLowAlerted: Boolean(raw.reelsLowAlerted),
    notifiedPublishedJobIds: raw.notifiedPublishedJobIds || [],
    notifiedFailedJobIds: raw.notifiedFailedJobIds || [],
    processedCommandCounts: raw.processedCommandCounts || {},
    processedLinkCounts: raw.processedLinkCounts || {},
    processedCommandSignatures: raw.processedCommandSignatures || [],
    processedLinkSignatures: raw.processedLinkSignatures || [],
    acceptedSourceLinks: raw.acceptedSourceLinks || [],
  };
}

function writeState(state) {
  const normalized = {
    ...createDefaultState(),
    healthUp: state.healthUp ?? null,
    loginRequired: state.loginRequired ?? null,
    lastNextJobId: state.lastNextJobId ?? null,
    lastHandledInboundSignature: state.lastHandledInboundSignature || null,
    reelsLowAlerted: Boolean(state.reelsLowAlerted),
    notifiedPublishedJobIds: state.notifiedPublishedJobIds || [],
    notifiedFailedJobIds: state.notifiedFailedJobIds || [],
    processedCommandCounts: state.processedCommandCounts || {},
    processedLinkCounts: state.processedLinkCounts || {},
    processedCommandSignatures: state.processedCommandSignatures || [],
    processedLinkSignatures: state.processedLinkSignatures || [],
    acceptedSourceLinks: state.acceptedSourceLinks || [],
  };
  fs.writeFileSync(statePath, JSON.stringify(normalized, null, 2));
}

function formatLocal(dateValue, options = {}) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: config.timezone,
    ...options,
  }).format(new Date(dateValue));
}

function nowLocal() {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: config.timezone,
  }).format(new Date());
}

function queueLine(job) {
  return `${job.media_type} #${job.id} | ${formatLocal(job.publish_at)} ${config.timezone}`;
}

function extractLinks(text) {
  const matches = text.match(/https?:\/\/\S+/g) || [];
  return matches.map((item) => item.replace(/[)\],.]+$/g, ""));
}

function isSchedulableSourceLink(link) {
  try {
    const host = new URL(link).hostname.toLowerCase();
    return (
      host.includes("instagram.com") ||
      host.includes("tiktok.com") ||
      host.includes("youtu.be") ||
      host.includes("youtube.com")
    );
  } catch {
    return false;
  }
}

function targetPhoneVariants() {
  const digits = config.targetPhone;
  const variants = new Set([digits, `+${digits}`]);
  if (digits.length >= 8) {
    const local = digits.slice(-8);
    variants.add(local);
    variants.add(`${local.slice(0, 4)} ${local.slice(4)}`);
    if (digits.length > 8) {
      const country = digits.slice(0, digits.length - 8);
      variants.add(`+${country} ${local.slice(0, 4)} ${local.slice(4)}`);
    }
  }
  return [...variants];
}

function appendDebugLog(name, payload) {
  const line = `[${new Date().toISOString()}] ${JSON.stringify(payload, null, 2)}\n`;
  fs.appendFileSync(path.join(outputDir, name), line, "utf8");
}

function looksLikeTimeLabel(text) {
  return /^(?:\d{1,2}:\d{2}\s?(?:AM|PM)|Today|Yesterday)$/i.test(text);
}

function nearbyTimeLabel(lines, index) {
  for (const offset of [1, 2, -1, -2]) {
    const candidate = lines[index + offset];
    if (candidate && looksLikeTimeLabel(candidate)) return candidate;
  }
  return "unknown-time";
}

function lineSignature(lines, index, normalizedText) {
  return `${normalizedText}|${nearbyTimeLabel(lines, index)}`;
}

function messageSignature(text, timeLabel = "unknown-time") {
  return `${text}|${timeLabel}`;
}

function latestLinkMessage(lines, state) {
  const seen = new Set(state.processedLinkSignatures || []);
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    const line = lines[index];
    if (!extractLinks(line).some(isSchedulableSourceLink)) continue;
    const signature = lineSignature(lines, index, line);
    if (seen.has(signature)) continue;
    return { text: line, signature };
  }
  return null;
}

function extractCommandFromMessages(messages, state) {
  const seen = new Set(state.processedCommandSignatures || []);
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    for (const rawLine of message.text.split(/\r?\n/)) {
      const command = normalizeCommand(rawLine.trim());
      if (!COMMANDS.has(command)) continue;
      const signature = messageSignature(command, message.timeLabel);
      if (seen.has(signature)) continue;
      return { command, signature };
    }
  }
  return null;
}

function latestLinkMessageFromMessages(messages, state) {
  const seen = new Set(state.processedLinkSignatures || []);
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    const links = extractLinks(message.text).filter(isSchedulableSourceLink);
    if (!links.length) continue;
    const signature = messageSignature(links[0], message.timeLabel);
    if (seen.has(signature)) continue;
    return { text: links[0], signature };
  }
  return null;
}

function nextScheduled(jobs) {
  return jobs
    .filter((job) => job.status === "scheduled")
    .sort((a, b) => new Date(a.publish_at) - new Date(b.publish_at))[0] || null;
}

function scheduledJobs(jobs) {
  return jobs
    .filter((job) => job.status === "scheduled")
    .sort((a, b) => new Date(a.publish_at) - new Date(b.publish_at));
}

function scheduledReels(jobs) {
  return scheduledJobs(jobs).filter((job) => job.media_type === "REEL");
}

function scheduledPosts(jobs) {
  return scheduledJobs(jobs).filter((job) => job.media_type === "POST");
}

function nextReelSlots(jobs, count) {
  const occupied = new Set(jobs.map((job) => new Date(job.publish_at).getTime()));
  const latest = jobs.length
    ? Math.max(...jobs.map((job) => new Date(job.publish_at).getTime()))
    : Date.now();
  const slots = [];
  const candidate = new Date(latest);
  candidate.setSeconds(0, 0);

  while (slots.length < count) {
    candidate.setMinutes(0, 0, 0);
    const hours = [6, 20];
    let advanced = false;
    for (const hour of hours) {
      const trial = new Date(candidate);
      trial.setHours(hour, 0, 0, 0);
      if (trial.getTime() <= latest) continue;
      if (occupied.has(trial.getTime())) continue;
      slots.push(new Date(trial));
      occupied.add(trial.getTime());
      advanced = true;
      if (slots.length >= count) break;
    }
    candidate.setDate(candidate.getDate() + 1);
    if (!advanced && slots.length >= count) break;
  }
  return slots;
}

function reelCaption() {
  return `تُعَدُّ ساعةُ مكةَ المكرمة، المعروفةُ بساعةِ البرجِ الملكي، واحدةً من أبرزِ المعالمِ المعماريةِ والحضاريةِ في المملكةِ العربيةِ السعودية، إذ ترتفعُ شامخةً فوقَ أبراجِ البيتِ لتُعلنَ الوقتَ من قلبِ الحرمِ المكيِّ في مشهدٍ مهيبٍ يجمعُ بينَ عظمةِ الهندسةِ الحديثةِ وروحانيةِ المكانِ وقدسيته، حتى غدت مع مرور السنوات رمزًا بصريًّا يلفتُ أنظارَ الزائرينَ من مختلفِ أنحاءِ العالم لما تتميزُ به من حجمٍ ضخمٍ وإضاءةٍ آسرةٍ وحضورٍ استثنائيٍّ يرسِّخُ في الأذهانِ صورةً مهيبةً لمكةَ المكرمةِ ومكانتها الدينيةِ العظيمة.

وتبرزُ الساعةُ بواجهاتها العملاقةِ وزخارفها الإسلاميةِ الدقيقةِ وتصميمها الفريد الذي يمزجُ بينَ الفخامةِ المعماريةِ والهويةِ الروحية، فتبدو كأنها شاهدٌ دائمٌ على حركةِ الحياةِ والعبادةِ حولَ المسجدِ الحرام، وتمنحُ الأفقَ المكيَّ ملامحَ مميزةً لا تُخطئها العين، خاصةً حين تتلألأ أنوارها في الليلِ فتنعكسُ هيبتُها على المكان وتزيدُ المشهدَ جلالًا وسكينة.

ولا تقتصرُ قيمةُ ساعةِ مكةَ على كونها وسيلةً لبيانِ الوقت، بل أصبحت معلمًا عالميًّا يعكسُ حجمَ العنايةِ التي أُحيطت بها أطهرُ بقاعِ الأرض، كما تجسدُ التقاءَ التقنيةِ الحديثةِ مع الإرثِ الإسلاميِّ في صورةٍ مبهرةٍ تثيرُ التأملَ والإعجاب، وتجعلُ من رؤيتها تجربةً لا تُنسى لكلِّ من قصدَ مكةَ المكرمةَ حاجًّا أو معتمرًا أو زائرًا متطلعًا إلى جمالِ المشهدِ وعظمةِ التفاصيل.

#quran #dua #islam #ذكر #قرآن #مكة #ساعة_مكة #الحرم_المكي #islamic #reels`;
}

function scheduleReelLinks(messageText, jobs, state) {
  const submittedLinks = extractLinks(messageText);
  const uniqueSubmitted = [...new Set(submittedLinks)];
  const acceptedSourceLinks = new Set(state.acceptedSourceLinks || []);
  const accepted = [];
  let duplicates = 0;
  let rejected = 0;
  const failures = [];

  for (const link of uniqueSubmitted) {
    if (!isSchedulableSourceLink(link)) {
      rejected += 1;
      continue;
    }
    if (acceptedSourceLinks.has(link)) {
      duplicates += 1;
      continue;
    }
    accepted.push(link);
  }

  if (!accepted.length) {
    return {
      reply: [
        "🎞️ Reel Links Received",
        `- Submitted: ${submittedLinks.length}`,
        "- Accepted: 0",
        `- Rejected: ${rejected}`,
        `- Duplicates: ${duplicates}`,
        "",
        "Scheduling Result",
        "- Created Reel IDs: Not available",
        "- Inserted: 0",
        "- First Slot: Not available",
        "- Last Slot: Not available",
        "",
        "Remaining Need:",
        `- ${Math.max(0, 10 - scheduledReels(jobs).length)} more reel links needed`,
      ].join("\n"),
      createdIds: [],
      acceptedLinks: [],
    };
  }

  const slots = nextReelSlots(jobs, accepted.length);
  const createdIds = [];
  accepted.forEach((link, index) => {
    const slot = slots[index];
    if (!slot) {
      rejected += 1;
      failures.push({ link, reason: "No slot available" });
      return;
    }
    const publishAt = slot.toISOString();
    const result = spawnSync(
      pythonBin,
      [
        prepareScript,
        link,
        reelCaption(),
        publishAt,
        "REEL",
      ],
      { cwd: projectRoot, encoding: "utf8" }
    );
    if (result.status !== 0) {
      rejected += 1;
      failures.push({
        link,
        reason: "prepare_and_schedule failed",
        status: result.status,
        stderr: result.stderr?.trim() || null,
        stdout: result.stdout?.trim() || null,
      });
      return;
    }
    try {
      const payload = JSON.parse(result.stdout);
      createdIds.push(payload.job.id);
      acceptedSourceLinks.add(link);
    } catch (error) {
      rejected += 1;
      failures.push({
        link,
        reason: "Invalid scheduler JSON",
        error: String(error),
        stdout: result.stdout?.trim() || null,
      });
    }
  });

  state.acceptedSourceLinks = [...acceptedSourceLinks];
  if (failures.length) {
    appendDebugLog("whatsapp-link-debug.log", {
      messageText,
      submittedLinks,
      accepted,
      createdIds,
      failures,
    });
  }
  const remaining = Math.max(0, 10 - (scheduledReels(jobs).length + createdIds.length));
  const nextTime = slots[0] ? formatLocal(slots[0].toISOString()) : "Not available";
  const lastTime = slots[createdIds.length - 1]
    ? formatLocal(slots[createdIds.length - 1].toISOString())
    : "Not available";

  return {
    reply: [
      "🎞️ Reel Links Received",
      `- Submitted: ${submittedLinks.length}`,
      `- Accepted: ${createdIds.length}`,
      `- Rejected: ${rejected}`,
      `- Duplicates: ${duplicates}`,
      "",
      "Scheduling Result",
      `- Created Reel IDs: ${createdIds.length ? createdIds.join(", ") : "Not available"}`,
      `- Inserted: ${createdIds.length}`,
      `- First Slot: ${nextTime}`,
      `- Last Slot: ${lastTime}`,
      "",
      "Remaining Need:",
      `- ${remaining === 0 ? "Reel library sufficient" : `${remaining} more reel links needed`}`,
    ].join("\n"),
    createdIds,
    acceptedLinks: accepted,
  };
}

function summarizeStatus(healthUp, jobs) {
  const scheduled = scheduledJobs(jobs);
  const next = scheduled[0];
  const lines = [
    "Meta-Uploader Status",
    `Checked: ${nowLocal()}`,
    `Health: ${healthUp ? "UP" : "DOWN"}`,
    `Scheduled jobs: ${scheduled.length}`,
  ];
  if (next) {
    lines.push(`Next: ${queueLine(next)}`);
  } else {
    lines.push("Next: none");
  }
  return lines.join("\n");
}

function summarizeSettings(jobs) {
  return [
    "Settings",
    "Pattern: Reel -> Post -> Reel block",
    `Timezone: ${config.timezone}`,
    "Slots: 06:00 reel | 09:00 post | 20:00 reel",
    `Scheduled reels: ${scheduledReels(jobs).length}`,
    `Scheduled posts: ${scheduledPosts(jobs).length}`,
    `Reels low threshold: ${config.reelsLowThreshold}`,
  ].join("\n");
}

function summarizeNext(jobs) {
  const next = nextScheduled(jobs);
  if (!next) return "Next Item\nNo scheduled jobs.";
  return ["Next Item", queueLine(next)].join("\n");
}

function summarizeJobs(jobs) {
  const scheduled = scheduledJobs(jobs).slice(0, 8);
  if (!scheduled.length) return "Upcoming Jobs\nNo scheduled jobs.";
  return ["Upcoming Jobs", ...scheduled.map(queueLine)].join("\n");
}

function summarizeHealth(healthUp) {
  return ["Health", healthUp ? "UP" : "DOWN"].join("\n");
}

function summarizeNeedReels(jobs) {
  const reels = scheduledReels(jobs);
  const needed = Math.max(0, config.reelsLowThreshold - reels.length);
  return [
    "Reel Inventory",
    `Need reels: ${needed > 0 ? "Yes" : "No"}`,
    `Scheduled reels remaining: ${reels.length}`,
    `Add at least: ${needed}`,
  ].join("\n");
}

function summarizeReelLinks(jobs) {
  const reels = scheduledReels(jobs).slice(0, 5);
  if (!reels.length) return "Reel Links\nNo scheduled reels found.";
  return [
    "🎞️ Reel Links Status",
    `- Available Reels: ${scheduledReels(jobs).length}`,
    "- Minimum Required: 10",
    `- Missing: ${Math.max(0, 10 - scheduledReels(jobs).length)}`,
    "",
    "Status:",
    scheduledReels(jobs).length < 10 ? "- Reel links needed" : "- Sufficient",
    ...(reels.length ? ["", ...reels.map((job) => `${job.id} | ${formatLocal(job.publish_at)} | ${job.video_url}`)] : []),
  ].join("\n");
}

function sameLocalDay(dateValue) {
  const date = new Date(dateValue);
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: config.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return formatter.format(date) === formatter.format(new Date());
}

function todayJobsOnly(jobs) {
  return jobs.filter((job) => sameLocalDay(job.publish_at) && job.status !== "cancelled");
}

function jobDetailLine(job) {
  return `- ${job.media_type} #${job.id} | ${formatLocal(job.updated_at || job.publish_at)} | ${job.status === "published" ? "Success" : "Failed"}`;
}

function summarizeQueue(jobs) {
  const pending = jobs.filter((job) => job.status === "scheduled").length;
  const running = jobs.filter((job) => job.status === "running").length;
  const completed = jobs.filter((job) => job.status === "published").length;
  const failed = jobs.filter((job) => job.status === "failed").length;
  return [
    "📦 Upload Queue",
    `- Pending: ${pending}`,
    `- Running: ${running}`,
    `- Completed: ${completed}`,
    `- Failed: ${failed}`,
  ].join("\n");
}

function summarizeLastUpload(jobs) {
  const last = jobs
    .filter((job) => job.status === "published" || job.status === "failed")
    .sort((a, b) => new Date(b.updated_at || b.publish_at) - new Date(a.updated_at || a.publish_at))[0];
  if (!last) {
    return [
      "⬆️ Last Upload Result",
      "- ID: Not available",
      "- Type: Not available",
      "- Result: Not available",
      "- Upload Time: Not available",
      "- Platform ID: Not available",
      "- Notes: Not available",
    ].join("\n");
  }
  return [
    "⬆️ Last Upload Result",
    `- ID: ${last.id}`,
    `- Type: ${last.media_type}`,
    `- Result: ${last.status === "published" ? "Success" : "Failed"}`,
    `- Upload Time: ${formatLocal(last.updated_at || last.publish_at)}`,
    `- Platform ID: ${last.meta_media_id || "Not available"}`,
    `- Notes: ${last.last_error || "Not available"}`,
  ].join("\n");
}

function summarizeTodayReport(jobs) {
  const todayJobs = todayJobsOnly(jobs);
  const scheduledToday = todayJobs.length;
  const successJobs = todayJobs.filter((job) => job.status === "published");
  const failedJobs = todayJobs.filter((job) => job.status === "failed");
  const pending = todayJobs.filter((job) => job.status === "scheduled").length;
  const lines = [
    "📊 Today's Activity Report",
    `- Scheduled: ${scheduledToday}`,
    `- Success: ${successJobs.length}`,
    `- Failed: ${failedJobs.length}`,
    `- Pending: ${pending}`,
    `- Reels Available: ${scheduledReels(jobs).length}`,
  ];
  if (successJobs.length) {
    lines.push("", "Completed Today");
    lines.push(...successJobs.map(jobDetailLine));
  }
  if (failedJobs.length) {
    lines.push("", "Failed Today");
    lines.push(...failedJobs.map(jobDetailLine));
  }
  return lines.join("\n");
}

function helpMessage() {
  return [
    "🤖 Commands",
    "status",
    "jobs",
    "reel-links",
    "queue",
    "next-id",
    "last-upload",
    "today-report",
    "help",
  ].join("\n");
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${url}`);
  }
  return response.json();
}

async function readHealth() {
  try {
    const json = await fetchJson(`${config.apiBase}/health`);
    return json.status === "ok";
  } catch {
    return false;
  }
}

async function readJobs() {
  try {
    return await fetchJson(`${config.apiBase}/jobs`);
  } catch {
    return [];
  }
}

function normalizeCommand(text) {
  const normalized = text.toLowerCase().replace(/\s+/g, " ").trim();
  return COMMAND_ALIASES[normalized] || normalized;
}

function extractCommand(lines, state) {
  const normalizedLines = lines.map((line) => normalizeCommand(line));
  const seen = new Set(state.processedCommandSignatures || []);

  for (let index = normalizedLines.length - 1; index >= 0; index -= 1) {
    const command = normalizedLines[index];
    if (!COMMANDS.has(command)) continue;
    const signature = lineSignature(lines, index, command);
    if (seen.has(signature)) continue;
    return { command, signature };
  }
  return null;
}

function collectUnseenCommands(lines, state) {
  const normalizedLines = lines.map((line) => normalizeCommand(line));
  const seen = new Set(state.processedCommandSignatures || []);
  const hits = [];
  for (let index = 0; index < normalizedLines.length; index += 1) {
    const command = normalizedLines[index];
    if (!COMMANDS.has(command)) continue;
    const signature = lineSignature(lines, index, command);
    if (seen.has(signature)) continue;
    hits.push({ command, signature });
  }
  return hits;
}

function collectUnseenLinks(lines, state) {
  const seen = new Set(state.processedLinkSignatures || []);
  const hits = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!extractLinks(line).some(isSchedulableSourceLink)) continue;
    const signature = lineSignature(lines, index, line);
    if (seen.has(signature)) continue;
    hits.push({ text: line, signature });
  }
  return hits;
}

function syncVisibleBacklog(lines, state) {
  const unseenCommands = collectUnseenCommands(lines, state);
  const unseenLinks = collectUnseenLinks(lines, state);
  const total = unseenCommands.length + unseenLinks.length;
  if (total <= 1) return false;

  state.processedCommandSignatures = [
    ...new Set([...(state.processedCommandSignatures || []), ...unseenCommands.map((item) => item.signature)]),
  ].slice(-200);
  state.processedLinkSignatures = [
    ...new Set([...(state.processedLinkSignatures || []), ...unseenLinks.map((item) => item.signature)]),
  ].slice(-200);

  appendDebugLog("whatsapp-backlog-sync.log", {
    unseenCommands,
    unseenLinks,
  });
  return true;
}

function renderCommandReply(command, healthUp, jobs) {
  switch (command) {
    case "status":
      return summarizeStatus(healthUp, jobs);
    case "next-id":
      return summarizeNext(jobs);
    case "reel-links":
      return summarizeReelLinks(jobs);
    case "jobs":
      return summarizeJobs(jobs);
    case "queue":
      return summarizeQueue(jobs);
    case "last-upload":
      return summarizeLastUpload(jobs);
    case "today-report":
      return summarizeTodayReport(jobs);
    case "help":
      return helpMessage();
    default:
      return null;
  }
}

async function saveArtifacts(page) {
  await page.screenshot({ path: path.join(outputDir, "whatsapp-debug.png") }).catch(() => {});
  const html = await page.content().catch(() => null);
  if (html) {
    fs.writeFileSync(path.join(outputDir, "whatsapp-debug.html"), html, "utf8");
  }
}

function loginRequiredText(bodyText) {
  const text = bodyText.toLowerCase();
  return (
    text.includes("scan to log in") ||
    text.includes("scan qr code") ||
    text.includes("link with phone number instead") ||
    text.includes("log in with phone number")
  );
}

async function openChat(context) {
  const page = await context.newPage();
  await page.goto("https://web.whatsapp.com/", { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForTimeout(3000);
  await saveArtifacts(page);

  let bodyText = await page.locator("body").innerText().catch(() => "");
  if (loginRequiredText(bodyText)) {
    await page.screenshot({ path: path.join(outputDir, "whatsapp-login.png") }).catch(() => {});
    return { page, loggedIn: false, bodyText };
  }

  const directUrl = `https://web.whatsapp.com/send?phone=${config.targetPhone}`;
  await page.goto(directUrl, { waitUntil: "networkidle", timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(2500);

  const tryCompose = async () => {
    try {
      await findComposeBox(page, 4000);
      return true;
    } catch {
      return false;
    }
  };

  const trySearchAndOpenChat = async () => {
    const searchSelectors = [
      '[contenteditable="true"][role="textbox"]',
      '[contenteditable="true"][data-tab="3"]',
      '[aria-label*="Search"]',
      '[title*="Search"]'
    ];

    for (const selector of searchSelectors) {
      const locator = page.locator(selector).first();
      if (!(await locator.isVisible().catch(() => false))) continue;
      await locator.click().catch(() => {});
      await page.keyboard.press("Control+A").catch(() => {});
      await page.keyboard.press("Meta+A").catch(() => {});
      await page.keyboard.press("Backspace").catch(() => {});
      await page.keyboard.type(config.targetPhone, { delay: 25 }).catch(() => {});
      await page.waitForTimeout(1500);

      const resultNeedles = targetPhoneVariants();
      for (const needle of resultNeedles) {
        const result = page.getByText(needle, { exact: false }).first();
        if (await result.isVisible().catch(() => false)) {
          await result.click().catch(() => {});
          await page.waitForTimeout(1500);
          if (await tryCompose()) return true;
        }
      }
    }
    return false;
  };

  if (!(await tryCompose())) {
    const needles = targetPhoneVariants();

    for (const needle of needles) {
      const locator = page.getByText(needle, { exact: false }).first();
      if (await locator.isVisible().catch(() => false)) {
        await locator.click().catch(() => {});
        await page.waitForTimeout(1500);
        if (await tryCompose()) break;
      }
    }
  }

  if (!(await tryCompose())) {
    await trySearchAndOpenChat();
  }

  bodyText = await page.locator("body").innerText().catch(() => "");
  await saveArtifacts(page);

  await page.screenshot({ path: path.join(outputDir, "whatsapp-ready.png") }).catch(() => {});
  return { page, loggedIn: true, bodyText };
}

async function findComposeBox(page, timeout = 30000) {
  const selectors = [
    'footer [contenteditable="true"]',
    '[contenteditable="true"][role="textbox"]',
    '[contenteditable="true"][data-tab]'
  ];
  for (const selector of selectors) {
    const locator = page.locator(selector).last();
    try {
      await locator.waitFor({ timeout });
      return locator;
    } catch {}
  }
  throw new Error("WhatsApp compose box not found");
}

async function extractLatestInboundMessage(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll("div.message-in")];
    const node = nodes.at(-1);
    if (!node) return null;
    const text = (node.innerText || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .join("\n");
    if (!text) return null;
    const pre = node.querySelector("[data-pre-plain-text]")?.getAttribute("data-pre-plain-text") || "";
    const timeMatch = pre.match(/\[(.*?)\]/);
    return {
      text,
      timeLabel: timeMatch ? timeMatch[1].trim() : "unknown-time",
      signature: `${pre || "unknown-pre"}|${text}`,
    };
  }).catch(() => null);
}

async function sendWhatsAppMessage(page, message) {
  const box = await findComposeBox(page, 45000);
  await box.click().catch(() => {});
  for (const line of message.split("\n")) {
    await page.keyboard.type(line, { delay: 8 });
    await page.keyboard.press("Shift+Enter");
  }
  await page.keyboard.press("Enter");
  await page.waitForTimeout(1200);
}

function buildNotifications(state, healthUp, jobs) {
  const notifications = [];

  state.healthUp = healthUp;

  const published = jobs.filter((job) => job.status === "published");
  const publishedSeen = new Set(state.notifiedPublishedJobIds || []);
  for (const job of published) {
    if (publishedSeen.has(job.id)) continue;
    if (job.replacement_for_job_id) {
      notifications.push([
        "Replacement upload successful",
        `${job.media_type} #${job.id}`,
        `Replaced failed job: #${job.replacement_for_job_id}`,
        `Published: ${formatLocal(job.updated_at || job.publish_at)} ${config.timezone}`,
      ].join("\n"));
    } else {
      notifications.push(["Upload confirmed", `${job.media_type} #${job.id}`, `Published: ${formatLocal(job.updated_at || job.publish_at)} ${config.timezone}`].join("\n"));
    }
    publishedSeen.add(job.id);
  }
  state.notifiedPublishedJobIds = Array.from(publishedSeen).slice(-200);

  const failed = jobs.filter((job) => job.status === "failed");
  const failedSeen = new Set(state.notifiedFailedJobIds || []);
  for (const job of failed) {
    if (failedSeen.has(job.id)) continue;
    notifications.push(["Upload failed", `${job.media_type} #${job.id}`, `Scheduled: ${formatLocal(job.publish_at)} ${config.timezone}`].join("\n"));
    failedSeen.add(job.id);
  }
  state.notifiedFailedJobIds = Array.from(failedSeen).slice(-200);

  const next = nextScheduled(jobs);
  state.lastNextJobId = next ? next.id : null;

  const reelCount = scheduledReels(jobs).length;
  state.reelsLowAlerted = reelCount < config.reelsLowThreshold;

  return notifications;
}

async function createContext() {
  const context = await chromium.launchPersistentContext(sessionDir, {
    headless: !config.headed,
    channel: "chromium",
    viewport: { width: 1440, height: 960 },
    locale: "en-US",
    timezoneId: config.timezone,
    userAgent:
      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    extraHTTPHeaders: {
      "Accept-Language": "en-US,en;q=0.9",
    },
    args: [
      "--disable-blink-features=AutomationControlled",
      "--lang=en-US",
    ],
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", {
      get: () => undefined,
    });
    Object.defineProperty(navigator, "language", {
      get: () => "en-US",
    });
    Object.defineProperty(navigator, "languages", {
      get: () => ["en-US", "en"],
    });
    Object.defineProperty(navigator, "platform", {
      get: () => "Linux x86_64",
    });
  });

  return context;
}

async function runCycle(state, options = {}) {
  const context = await createContext();
  try {
    const { page, loggedIn, bodyText } = await openChat(context);
    if (!loggedIn) {
      state.loginRequired = true;
      writeState(state);
      if (options.loginOnly) {
        console.log("WhatsApp login required. See runtime/whatsapp_output/whatsapp-login.png");
      }
      return;
    }

    state.loginRequired = false;

    const healthUp = await readHealth();
    const jobs = healthUp ? await readJobs() : [];

    const inboundMessage = await extractLatestInboundMessage(page);
    if (!inboundMessage || inboundMessage.signature === state.lastHandledInboundSignature) {
      const notifications = buildNotifications(state, healthUp, jobs);
      for (const message of notifications) {
        await sendWhatsAppMessage(page, message);
      }
      writeState(state);
      return;
    }

    let handled = false;
    for (const rawLine of inboundMessage.text.split(/\r?\n/)) {
      const command = normalizeCommand(rawLine.trim());
      if (!COMMANDS.has(command)) continue;
      const reply = renderCommandReply(command, healthUp, jobs);
      if (reply) {
        await sendWhatsAppMessage(page, reply);
      }
      state.lastHandledInboundSignature = inboundMessage.signature;
      state.processedCommandSignatures = [...new Set([...(state.processedCommandSignatures || []), messageSignature(command, inboundMessage.timeLabel)])].slice(-200);
      state.processedCommandCounts = {
        ...(state.processedCommandCounts || {}),
        [command]: ((state.processedCommandCounts || {})[command] || 0) + 1,
      };
      handled = true;
      writeState(state);
      return;
    }

    const links = extractLinks(inboundMessage.text).filter(isSchedulableSourceLink);
    if (links.length) {
      const result = scheduleReelLinks(links[0], jobs, state);
      await sendWhatsAppMessage(page, result.reply);
      state.lastHandledInboundSignature = inboundMessage.signature;
      state.processedLinkSignatures = [...new Set([...(state.processedLinkSignatures || []), messageSignature(links[0], inboundMessage.timeLabel)])].slice(-200);
      state.processedLinkCounts = {
        ...(state.processedLinkCounts || {}),
        [links[0]]: ((state.processedLinkCounts || {})[links[0]] || 0) + 1,
      };
      writeState(state);
      return;
    }

    state.lastHandledInboundSignature = inboundMessage.signature;

    if (options.sendStatusNow) {
      for (const message of [
        summarizeStatus(healthUp, jobs),
        summarizeSettings(jobs),
        summarizeReelLinks(jobs),
      ]) {
        await sendWhatsAppMessage(page, message);
      }
      writeState(state);
      return;
    }

    const notifications = buildNotifications(state, healthUp, jobs);
    for (const message of notifications) {
      await sendWhatsAppMessage(page, message);
    }

    writeState(state);
  } finally {
    await context.close();
  }
}

async function watchLoop() {
  const state = readState();
  while (true) {
    try {
      await runCycle(state);
    } catch (error) {
      console.error(error);
      writeState(state);
    }
    await new Promise((resolve) => setTimeout(resolve, config.checkIntervalSeconds * 1000));
  }
}

async function main() {
  const state = readState();
  if (config.loginOnly) {
    await runCycle(state, { loginOnly: true });
    return;
  }
  if (config.sendStatusNow) {
    await runCycle(state, { sendStatusNow: true });
    return;
  }
  await watchLoop();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
