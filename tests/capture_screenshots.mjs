import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".woff2": "font/woff2",
  ".pdf": "application/pdf",
  ".xml": "application/xml; charset=utf-8",
};

const ROUTES = [
  { slug: "home", route: "/" },
  { slug: "work", route: "/work/" },
  { slug: "posts", route: "/posts/" },
  { slug: "cv", route: "/cv/" },
  { slug: "publications", route: "/publications/" },
];

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 800, deviceScaleFactor: 1, mobile: false },
  { name: "mobile", width: 375, height: 812, deviceScaleFactor: 2, mobile: true },
];

const THEMES = ["light", "dark"];

export function resolveScreenshotOutDir(envDir = process.env.SCREENSHOT_OUT_DIR) {
  const raw = envDir && envDir.trim()
    ? envDir.trim()
    : path.join(os.tmpdir(), `vlap-screenshots-${Date.now()}`);
  const resolvedOut = path.resolve(raw);
  const rel = path.relative(REPO_ROOT, resolvedOut);
  if (rel === "" || rel === "." || (!rel.startsWith(`..${path.sep}`) && rel !== ".." && !path.isAbsolute(rel))) {
    throw new Error(
      `Refusing to write screenshots inside REPO_ROOT (${REPO_ROOT}): ${resolvedOut}`,
    );
  }
  return resolvedOut;
}

function findChromeBinary() {
  if (process.env.CHROME_BIN && fs.existsSync(process.env.CHROME_BIN)) {
    return process.env.CHROME_BIN;
  }
  const candidates = [
    "/home/volant/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error("No headless Chromium binary found; set CHROME_BIN.");
}

function startStaticServer(rootDir) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const reqUrl = new URL(req.url, "http://127.0.0.1");
      const relPath = decodeURIComponent(reqUrl.pathname).replace(/^\/+/, "");
      let target = path.join(rootDir, relPath);
      if (fs.existsSync(target) && fs.statSync(target).isDirectory()) {
        target = path.join(target, "index.html");
      } else if (!fs.existsSync(target) && fs.existsSync(`${target}.html`)) {
        target = `${target}.html`;
      }
      if (!target.startsWith(rootDir) || !fs.existsSync(target) || fs.statSync(target).isDirectory()) {
        res.writeHead(404);
        res.end("Not found");
        return;
      }
      const ext = path.extname(target).toLowerCase();
      res.writeHead(200, { "Content-Type": MIME_TYPES[ext] || "application/octet-stream" });
      fs.createReadStream(target).pipe(res);
    });
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ server, port, baseUrl: `http://127.0.0.1:${port}` });
    });
  });
}

function runHugoBuild(outDir, baseUrl) {
  return new Promise((resolve, reject) => {
    const proc = spawn("hugo", ["--gc", "--minify", "-d", outDir, "--baseURL", `${baseUrl}/`], {
      cwd: REPO_ROOT,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let output = "";
    proc.stdout.on("data", (d) => { output += d.toString(); });
    proc.stderr.on("data", (d) => { output += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) resolve(output);
      else reject(new Error(`Hugo build failed (${code}): ${output}`));
    });
  });
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
    this.ready = new Promise((resolve, reject) => {
      this.ws.addEventListener("open", () => resolve());
      this.ws.addEventListener("error", (err) => reject(err));
    });
    this.ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id) {
        const entry = this.pending.get(msg.id);
        if (entry) {
          this.pending.delete(msg.id);
          if (msg.error) entry.reject(new Error(JSON.stringify(msg.error)));
          else entry.resolve(msg.result);
        }
      } else if (msg.method) {
        this.events.push(msg);
      }
    });
  }

  async send(method, params = {}) {
    await this.ready;
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expression) {
    const res = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    if (res.exceptionDetails) {
      throw new Error(`Page eval error: ${JSON.stringify(res.exceptionDetails)}`);
    }
    return res.result?.value;
  }

  waitForLoad(timeoutMs = 10000) {
    const start = Date.now();
    return new Promise((resolve, reject) => {
      const check = () => {
        const idx = this.events.findIndex((e) => e.method === "Page.loadEventFired");
        if (idx !== -1) {
          this.events.splice(idx, 1);
          resolve();
          return;
        }
        if (Date.now() - start > timeoutMs) {
          reject(new Error("Timed out waiting for Page.loadEventFired"));
          return;
        }
        setTimeout(check, 25);
      };
      check();
    });
  }

  close() {
    this.ws.close();
  }
}

async function launchChrome(userDataDir) {
  const chromeBin = findChromeBinary();
  const proc = spawn(
    chromeBin,
    [
      "--headless",
      "--disable-gpu",
      "--no-sandbox",
      "--remote-debugging-port=0",
      `--user-data-dir=${userDataDir}`,
      "about:blank",
    ],
    { stdio: ["ignore", "pipe", "pipe"] },
  );

  const wsUrl = await new Promise((resolve, reject) => {
    let stderr = "";
    const timer = setTimeout(() => reject(new Error(`Chrome startup timed out: ${stderr}`)), 15000);
    const onData = (chunk) => {
      const text = chunk.toString();
      stderr += text;
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) {
        clearTimeout(timer);
        resolve(match[1]);
      }
    };
    proc.stderr.on("data", onData);
    proc.stdout.on("data", onData);
    proc.on("exit", (code) => {
      clearTimeout(timer);
      reject(new Error(`Chrome exited early (${code}): ${stderr}`));
    });
  });

  const versionRes = await fetch(wsUrl.replace(/^ws:/, "http:").replace(/\/devtools\/browser\/.*$/, "/json/list"));
  const targets = await versionRes.json();
  const pageTarget = targets.find((t) => t.type === "page");
  if (!pageTarget?.webSocketDebuggerUrl) {
    throw new Error("No page target found in headless Chromium");
  }
  const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("DOM.enable");
  return { proc, cdp };
}

async function main() {
  const screenshotOutDir = resolveScreenshotOutDir();
  fs.mkdirSync(screenshotOutDir, { recursive: true });

  const outHugoDir = fs.mkdtempSync(path.join(REPO_ROOT, "_tmp_hugo_shots_"));
  const userDataDir = fs.mkdtempSync(path.join(REPO_ROOT, "_tmp_chrome_shots_"));
  let serverObj;
  let chromeProc;
  let cdp;

  try {
    serverObj = await startStaticServer(outHugoDir);
    await runHugoBuild(outHugoDir, serverObj.baseUrl);
    const launched = await launchChrome(userDataDir);
    chromeProc = launched.proc;
    cdp = launched.cdp;

    const manifest = [];
    for (const vp of VIEWPORTS) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: vp.width,
        height: vp.height,
        deviceScaleFactor: vp.deviceScaleFactor,
        mobile: vp.mobile,
      });

      for (const theme of THEMES) {
        await cdp.send("Emulation.setEmulatedMedia", {
          features: [{ name: "prefers-color-scheme", value: theme }],
        });

        for (const { slug, route } of ROUTES) {
          const url = `${serverObj.baseUrl}${route}`;
          cdp.events = [];
          await cdp.send("Page.navigate", { url });
          await cdp.waitForLoad();
          await cdp.eval(`localStorage.setItem('pref-theme', ${JSON.stringify(theme)})`);

          cdp.events = [];
          await cdp.send("Page.reload", { ignoreCache: true });
          await cdp.waitForLoad();
          await new Promise((r) => setTimeout(r, 150));

          const metrics = await cdp.eval(`(async () => {
            await document.fonts.ready;
            const step = Math.max(200, Math.floor(window.innerHeight * 0.8));
            const maxY = document.documentElement.scrollHeight;
            for (let y = 0; y <= maxY; y += step) {
              window.scrollTo(0, y);
              await new Promise((r) => setTimeout(r, 40));
            }
            const imgs = [...document.querySelectorAll('img')].filter((img) => {
              if (img.closest('details:not([open])')) return false;
              const cs = getComputedStyle(img);
              return cs.display !== 'none' && cs.visibility !== 'hidden';
            });
            for (const img of imgs) {
              if (!img.complete) {
                await new Promise((resolve) => {
                  img.addEventListener('load', resolve, { once: true });
                  img.addEventListener('error', resolve, { once: true });
                  setTimeout(resolve, 3000);
                });
              }
            }
            window.scrollTo(0, 0);
            await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
            await new Promise((r) => setTimeout(r, 150));

            let cls = 0;
            const observer = new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) cls += entry.value;
              }
            });
            observer.observe({ type: 'layout-shift', buffered: true });
            await new Promise((r) => setTimeout(r, 80));
            observer.disconnect();

            const failedImages = imgs.filter((img) => !img.complete || img.naturalWidth === 0).length;
            return {
              datasetTheme: document.documentElement.dataset.theme || '',
              scrollWidth: document.documentElement.scrollWidth,
              innerWidth: window.innerWidth,
              cls,
              failedImages,
            };
          })()`);

          const consoleErrors = cdp.events.filter(
            (e) => e.method === "Runtime.consoleAPICalled" && e.params?.type === "error",
          ).length;
          const pageExceptions = cdp.events.filter(
            (e) => e.method === "Runtime.exceptionThrown",
          ).length;

          const foldName = `${slug}_${vp.name}_${theme}_fold.png`;
          const fullName = `${slug}_${vp.name}_${theme}_full.png`;
          const foldShot = await cdp.send("Page.captureScreenshot", { format: "png" });
          fs.writeFileSync(path.join(screenshotOutDir, foldName), Buffer.from(foldShot.data, "base64"));

          const fullShot = await cdp.send("Page.captureScreenshot", {
            format: "png",
            captureBeyondViewport: true,
          });
          fs.writeFileSync(path.join(screenshotOutDir, fullName), Buffer.from(fullShot.data, "base64"));

          manifest.push({
            route,
            slug,
            viewport: vp.name,
            width: vp.width,
            height: vp.height,
            theme,
            datasetTheme: metrics.datasetTheme,
            scrollWidth: metrics.scrollWidth,
            innerWidth: metrics.innerWidth,
            cls: metrics.cls,
            consoleErrors,
            pageExceptions,
            failedImages: metrics.failedImages,
            foldPng: foldName,
            fullPng: fullName,
          });
        }
      }
    }

    const manifestPath = path.join(screenshotOutDir, "manifest.json");
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf-8");

    const failures = manifest.filter(
      (m) =>
        m.datasetTheme !== m.theme ||
        m.consoleErrors > 0 ||
        m.pageExceptions > 0 ||
        m.failedImages > 0 ||
        m.scrollWidth > m.innerWidth ||
        m.cls > 0,
    );
    if (manifest.length !== 20 || failures.length > 0) {
      console.error("Screenshot verification failed:", JSON.stringify({ count: manifest.length, failures }, null, 2));
      process.exitCode = 1;
    } else {
      console.log(`Captured ${manifest.length * 2} PNGs across ${manifest.length} states into ${screenshotOutDir}`);
    }
  } finally {
    try { cdp?.close(); } catch {}
    try { chromeProc?.kill("SIGKILL"); } catch {}
    try { serverObj?.server?.close(); } catch {}
    fs.rmSync(outHugoDir, { recursive: true, force: true });
    fs.rmSync(userDataDir, { recursive: true, force: true });
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
