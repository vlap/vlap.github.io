import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { after, before, describe, it } from "node:test";
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
      let relPath = decodeURIComponent(reqUrl.pathname).replace(/^\/+/, "");
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

async function navigateAndCheckErrors(cdp, url) {
  cdp.events = [];
  await cdp.send("Page.navigate", { url });
  await cdp.waitForLoad();
  await new Promise((r) => setTimeout(r, 150));

  const consoleErrors = cdp.events.filter(
    (e) => e.method === "Runtime.consoleAPICalled" && e.params?.type === "error",
  );
  const pageExceptions = cdp.events.filter((e) => e.method === "Runtime.exceptionThrown");
  assert.equal(consoleErrors.length, 0, `Console errors on ${url}: ${JSON.stringify(consoleErrors)}`);
  assert.equal(pageExceptions.length, 0, `Page exceptions on ${url}: ${JSON.stringify(pageExceptions)}`);
}

describe("vlap.github.io headless browser verification", () => {
  let outDir;
  let userDataDir;
  let serverObj;
  let chromeProc;
  let cdp;

  before(async () => {
    outDir = fs.mkdtempSync(path.join(REPO_ROOT, "_tmp_hugo_e2e_"));
    userDataDir = fs.mkdtempSync(path.join(REPO_ROOT, "_tmp_chrome_profile_"));
    serverObj = await startStaticServer(outDir);
    await runHugoBuild(outDir, serverObj.baseUrl);
    const launched = await launchChrome(userDataDir);
    chromeProc = launched.proc;
    cdp = launched.cdp;
  });

  after(() => {
    try { cdp?.close(); } catch {}
    try { chromeProc?.kill("SIGKILL"); } catch {}
    try { serverObj?.server?.close(); } catch {}
    fs.rmSync(outDir, { recursive: true, force: true });
    fs.rmSync(userDataDir, { recursive: true, force: true });
  });

  it("synchronizes meta[name=color-scheme], computed color-scheme, and light-dark badges on theme toggle & reload", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/`);
    await cdp.eval(`localStorage.clear()`);
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/`);

    const initial = await cdp.eval(`({
      meta: document.querySelector('meta[name="color-scheme"]')?.content,
      theme: document.documentElement.dataset.theme,
      supportsSpeculation: HTMLScriptElement.supports('speculationrules')
    })`);
    assert.equal(initial.meta, "light dark");
    assert.ok(initial.theme === "light" || initial.theme === "dark");
    assert.equal(initial.supportsSpeculation, true);

    await cdp.eval(`document.getElementById('theme-toggle').click()`);
    const afterFirstClick = await cdp.eval(`({
      meta: document.querySelector('meta[name="color-scheme"]')?.content,
      theme: document.documentElement.dataset.theme,
      stored: localStorage.getItem('pref-theme'),
      computedScheme: getComputedStyle(document.documentElement).colorScheme
    })`);
    assert.notEqual(afterFirstClick.theme, initial.theme);
    assert.equal(afterFirstClick.meta, afterFirstClick.theme);
    assert.equal(afterFirstClick.stored, afterFirstClick.theme);
    assert.equal(afterFirstClick.computedScheme, afterFirstClick.theme);

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/about/`);
    const persistedAbout = await cdp.eval(`({
      meta: document.querySelector('meta[name="color-scheme"]')?.content,
      theme: document.documentElement.dataset.theme,
      badgeBg: getComputedStyle(document.querySelector('.badge-hpc')).backgroundColor
    })`);
    assert.equal(persistedAbout.theme, afterFirstClick.theme);
    assert.equal(persistedAbout.meta, afterFirstClick.theme);

    await cdp.eval(`document.getElementById('theme-toggle').click()`);
    await new Promise((r) => setTimeout(r, 250));
    const toggledAbout = await cdp.eval(`({
      meta: document.querySelector('meta[name="color-scheme"]')?.content,
      theme: document.documentElement.dataset.theme,
      badgeBg: getComputedStyle(document.querySelector('.badge-hpc')).backgroundColor,
      badgeVar: getComputedStyle(document.documentElement).getPropertyValue('--badge-hpc-bg').trim()
    })`);
    assert.notEqual(toggledAbout.theme, persistedAbout.theme);
    assert.equal(toggledAbout.meta, toggledAbout.theme);
    assert.notEqual(toggledAbout.badgeBg, persistedAbout.badgeBg, "--badge-hpc-bg must adapt between light and dark");
  });

  it("activates .sim-facade native <button> via keyboard Enter and replaces with native <video>", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/software/`);
    const beforeInfo = await cdp.eval(`(async () => {
      const btns = [...document.querySelectorAll('button.sim-facade')];
      const posters = [...document.querySelectorAll('img.sim-poster')];
      for (const img of posters) {
        img.scrollIntoView({ block: 'center' });
        if (!img.complete) {
          await new Promise((resolve) => {
            img.addEventListener('load', resolve, { once: true });
            img.addEventListener('error', resolve, { once: true });
            setTimeout(resolve, 3000);
          });
        }
      }
      return {
        count: btns.length,
        labels: btns.map((b) => b.getAttribute('aria-label')),
        types: btns.map((b) => b.getAttribute('type')),
        postersLoaded: posters.every((img) => img.complete && img.naturalWidth > 0)
      };
    })()`);
    assert.equal(beforeInfo.count, 3);
    assert.ok(beforeInfo.labels.every((l) => l && l.startsWith("Play ")));
    assert.ok(beforeInfo.types.every((t) => t === "button"));
    assert.equal(beforeInfo.postersLoaded, true, "All 3 simulation WebP posters must load");

    await cdp.send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: "reduce" }],
    });
    try {
      await cdp.eval(`document.querySelector('button.sim-facade').focus()`);
      await new Promise((r) => setTimeout(r, 400));
      const reducedMotion = await cdp.eval(`(() => {
        const facade = document.querySelector('button.sim-facade');
        const icon = facade?.querySelector('.sim-play-icon');
        const poster = facade?.querySelector('.sim-poster');
        return {
          matches: matchMedia('(prefers-reduced-motion: reduce)').matches,
          focused: document.activeElement === facade,
          iconTransform: icon ? getComputedStyle(icon).transform : null,
          posterTransform: poster ? getComputedStyle(poster).transform : null
        };
      })()`);
      assert.equal(reducedMotion.matches, true);
      assert.equal(reducedMotion.focused, true);
      assert.equal(reducedMotion.iconTransform, "none", "Reduced motion must disable .sim-play-icon scale");
      assert.equal(reducedMotion.posterTransform, "none", "Reduced motion must disable .sim-poster scale");
    } finally {
      await cdp.send("Emulation.setEmulatedMedia", { features: [] });
      await cdp.eval(`document.activeElement?.blur()`);
    }

    await cdp.eval(`document.querySelector('button.sim-facade').focus()`);
    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: "Enter",
      code: "Enter",
      text: "\r",
      unmodifiedText: "\r",
      windowsVirtualKeyCode: 13,
      nativeVirtualKeyCode: 13,
    });
    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key: "Enter",
      code: "Enter",
      windowsVirtualKeyCode: 13,
      nativeVirtualKeyCode: 13,
    });

    const videoInfo = await cdp.eval(`(() => {
      const video = document.querySelector('.sim-video video');
      if (!video) return null;
      const sources = [...video.querySelectorAll('source')].map((s) => ({
        src: s.getAttribute('src'),
        type: s.getAttribute('type')
      }));
      return {
        controls: video.controls,
        muted: video.muted,
        poster: video.getAttribute('poster'),
        sources
      };
    })()`);
    assert.ok(videoInfo, "Expected .sim-video video element after facade activation");
    assert.equal(videoInfo.controls, true);
    assert.equal(videoInfo.muted, true);
    assert.ok(videoInfo.poster && videoInfo.poster.startsWith("/images/simulations/"), `Unexpected poster: ${videoInfo.poster}`);
    assert.ok(videoInfo.sources.some((s) => s.type === "video/webm" && s.src?.endsWith(".webm")));
    assert.ok(videoInfo.sources.some((s) => s.type === "video/mp4" && s.src?.endsWith(".mp4")));
    const remainingFacades = await cdp.eval(`document.querySelectorAll('button.sim-facade').length`);
    assert.equal(remainingFacades, 2);
  });

  it("updates #pubFilterStatus live region, shows :focus-visible outline, and reaches deferred groups via Tab", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
    const initialPubs = await cdp.eval(`({
      totalPubs: document.querySelectorAll('.pub-card').length,
      role: document.getElementById('pubFilterStatus')?.getAttribute('role'),
      live: document.getElementById('pubFilterStatus')?.getAttribute('aria-live'),
      text: document.getElementById('pubFilterStatus')?.textContent.trim(),
      deferredCv: getComputedStyle(document.querySelector('.pub-year-group:nth-of-type(n+3)')).contentVisibility
    })`);
    const totalPubs = initialPubs.totalPubs;
    assert.ok(totalPubs > 0, `Expected > 0 .pub-card elements, got ${totalPubs}`);
    assert.equal(initialPubs.role, "status");
    assert.equal(initialPubs.live, "polite");
    assert.equal(initialPubs.text, `Showing all ${totalPubs} publications`);
    assert.equal(initialPubs.deferredCv, "auto");

    // Regression check: filtering must match off-screen content-visibility: auto cards on fresh load before scrolling
    const preScroll = await cdp.eval(`({
      scrollY: window.scrollY,
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      year2011Count: document.querySelectorAll('#year-2011 .pub-card').length,
      yearOtherCount: document.querySelectorAll('#year-Other .pub-card').length
    })`);
    assert.equal(preScroll.scrollY, 0, "Expected fresh /publications/ load before scrolling");
    assert.equal(preScroll.innerWidth, 1280);
    assert.equal(preScroll.innerHeight, 800);
    assert.equal(preScroll.year2011Count, 4);
    assert.equal(preScroll.yearOtherCount, 1);

    for (const [query, expectedCount] of [
      ["irregular boundaries", 1],
      ["2011", 4],
    ]) {
      const deferredRes = await cdp.eval(`(() => {
        const input = document.getElementById('pubFilterInput');
        input.value = ${JSON.stringify(query)};
        input.dispatchEvent(new Event('input', { bubbles: true }));
        const visibleCards = [...document.querySelectorAll('.pub-card')].filter((c) => {
          const grp = c.closest('.pub-year-group');
          return c.style.display !== 'none' && (!grp || grp.style.display !== 'none');
        }).length;
        return {
          visibleCards,
          emptyHidden: document.getElementById('pubEmptyState')?.hidden,
          status: document.getElementById('pubFilterStatus')?.textContent.trim()
        };
      })()`);
      assert.equal(
        deferredRes.visibleCards,
        expectedCount,
        `Expected ${expectedCount} visible cards for "${query}" before scrolling, got ${JSON.stringify(deferredRes)}`,
      );
      assert.equal(deferredRes.emptyHidden, true);
      assert.equal(deferredRes.status, `Showing ${expectedCount} of ${totalPubs} publications`);

      const clearedRes = await cdp.eval(`(() => {
        document.getElementById('pubFilterClear')?.click();
        const visibleCards = [...document.querySelectorAll('.pub-card')].filter((c) => {
          const grp = c.closest('.pub-year-group');
          return c.style.display !== 'none' && (!grp || grp.style.display !== 'none');
        }).length;
        return {
          value: document.getElementById('pubFilterInput')?.value,
          status: document.getElementById('pubFilterStatus')?.textContent.trim(),
          emptyHidden: document.getElementById('pubEmptyState')?.hidden,
          visibleCards
        };
      })()`);
      assert.equal(clearedRes.value, "");
      assert.equal(clearedRes.status, `Showing all ${totalPubs} publications`);
      assert.equal(clearedRes.emptyHidden, true);
      assert.equal(clearedRes.visibleCards, totalPubs);
    }

    // Reload cleanly to reset sequential Tab focus navigation starting point
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);

    // Focus #pubFilterInput via keyboard Tab until reached
    for (let i = 0; i < 40; i++) {
      await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      const activeId = await cdp.eval(`document.activeElement?.id`);
      if (activeId === "pubFilterInput") break;
    }
    const focusInfo = await cdp.eval(`(() => {
      const el = document.activeElement;
      const cs = getComputedStyle(el);
      return {
        id: el?.id,
        matchesFocusVisible: el?.matches(':focus-visible'),
        outlineStyle: cs.outlineStyle,
        outlineWidth: cs.outlineWidth
      };
    })()`);
    assert.equal(focusInfo.id, "pubFilterInput");
    assert.equal(focusInfo.matchesFocusVisible, true);
    assert.notEqual(focusInfo.outlineStyle, "none");
    assert.notEqual(focusInfo.outlineWidth, "0px");

    await cdp.send("Input.insertText", { text: "EC-Earth" });
    await new Promise((r) => setTimeout(r, 50));
    const filteredText = await cdp.eval(`document.getElementById('pubFilterStatus').textContent.trim()`);
    const match = filteredText.match(new RegExp(`^Showing (\\d+) of ${totalPubs} publications$`));
    assert.ok(match, `Unexpected status text: ${filteredText}`);
    const filteredCount = Number(match[1]);
    assert.equal(filteredText, `Showing ${filteredCount} of ${totalPubs} publications`);
    assert.ok(filteredCount > 0 && filteredCount < totalPubs, `Expected 0 < count < ${totalPubs}, got ${filteredCount}`);

    await cdp.eval(`document.getElementById('pubFilterClear').click()`);
    const cleared = await cdp.eval(`({
      text: document.getElementById('pubFilterStatus').textContent.trim(),
      activeId: document.activeElement?.id
    })`);
    assert.equal(cleared.text, `Showing all ${totalPubs} publications`);
    assert.equal(cleared.activeId, "pubFilterInput");

    await cdp.send("Input.insertText", { text: "zzzz_nomatch" });
    await new Promise((r) => setTimeout(r, 50));
    const noMatchState = await cdp.eval(`(() => {
      const status = document.getElementById('pubFilterStatus')?.textContent.trim();
      const empty = document.getElementById('pubEmptyState');
      const query = document.getElementById('pubEmptyQuery')?.textContent.trim();
      return {
        status,
        hasEmpty: Boolean(empty && empty.closest('.publication-feed')),
        hidden: empty ? empty.hidden : true,
        display: empty ? getComputedStyle(empty).display : 'none',
        query
      };
    })()`);
    assert.equal(noMatchState.status, `Showing 0 of ${totalPubs} publications`);
    assert.equal(noMatchState.hasEmpty, true);
    assert.equal(noMatchState.hidden, false);
    assert.notEqual(noMatchState.display, "none");
    assert.equal(noMatchState.query, "zzzz_nomatch");

    await cdp.eval(`document.querySelector('#pubEmptyState button[type="button"]').click()`);
    const resetFromEmpty = await cdp.eval(`({
      status: document.getElementById('pubFilterStatus').textContent.trim(),
      value: document.getElementById('pubFilterInput').value,
      emptyHidden: document.getElementById('pubEmptyState').hidden,
      activeId: document.activeElement?.id
    })`);
    assert.equal(resetFromEmpty.status, `Showing all ${totalPubs} publications`);
    assert.equal(resetFromEmpty.value, "");
    assert.equal(resetFromEmpty.emptyHidden, true);
    assert.equal(resetFromEmpty.activeId, "pubFilterInput");

    // Verify sequential Tab reachability from non-deferred group into deferred .pub-year-group:nth-of-type(n+3)
    const beforeFocusId = await cdp.eval(`(() => {
      const firstDeferred = document.querySelector('.pub-year-group:nth-of-type(n+3)');
      const nonDeferred = firstDeferred?.previousElementSibling;
      const linksBefore = [...(nonDeferred?.querySelectorAll('a, button:not(.copy-code)') || [])];
      const target = linksBefore[linksBefore.length - 1];
      target?.focus();
      return document.activeElement === target ? nonDeferred.id : null;
    })()`);
    assert.equal(typeof beforeFocusId, "string", "Expected focus on non-deferred .pub-year-group");
    let reachedDeferredPub = false;
    for (let i = 0; i < 4; i++) {
      await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      reachedDeferredPub = await cdp.eval(`Boolean(document.activeElement?.closest('.pub-year-group:nth-of-type(n+3)'))`);
      if (reachedDeferredPub) break;
    }
    assert.equal(reachedDeferredPub, true, "Deferred .pub-year-group must remain reachable via sequential Tab");

    // Verify deterministic cross-button #pubCopyStatus timer isolation & N-click deduplication
    const crossBtnResult = await cdp.eval(`(async () => {
      const realSetTimeout = window.setTimeout;
      const realClearTimeout = window.clearTimeout;
      let now = 0;
      let nextId = 1;
      const tasks = new Map();
      window.setTimeout = (fn, delay = 0) => {
        const id = nextId++;
        tasks.set(id, { at: now + delay, fn });
        return id;
      };
      window.clearTimeout = (id) => { tasks.delete(id); };
      const advance = (ms) => {
        const target = now + ms;
        while (true) {
          const due = [...tasks.entries()]
            .filter(([, t]) => t.at <= target)
            .sort((a, b) => a[1].at - b[1].at);
          if (!due.length) break;
          const [id, task] = due[0];
          tasks.delete(id);
          now = task.at;
          task.fn();
        }
        now = target;
      };
      try {
        Object.defineProperty(navigator, 'clipboard', {
          value: { writeText: () => Promise.resolve() },
          configurable: true
        });
        const btns = [...document.querySelectorAll('.pub-copy-btn')];
        const statusEl = document.getElementById('pubCopyStatus');
        btns[0].click();
        await Promise.resolve();
        await Promise.resolve();
        const click1 = statusEl?.textContent;
        btns[0].click();
        await Promise.resolve();
        await Promise.resolve();
        const click2 = statusEl?.textContent;
        btns[0].click();
        await Promise.resolve();
        await Promise.resolve();
        const click3 = statusEl?.textContent;
        advance(1000);
        btns[1].click();
        await Promise.resolve();
        await Promise.resolve();
        advance(1000); // t=2000: btns[0] timer fires; btns[1] still active until t=3000
        const mid = {
          btn0Text: btns[0].querySelector('.pub-copy-text')?.textContent.trim(),
          btn0Copied: btns[0].classList.contains('copied'),
          btn1Text: btns[1].querySelector('.pub-copy-text')?.textContent.trim(),
          btn1Copied: btns[1].classList.contains('copied'),
          statusAt2000: statusEl?.textContent.trim()
        };
        advance(1000); // t=3000: btns[1] + status timer finish
        const end = {
          btn1Text: btns[1].querySelector('.pub-copy-text')?.textContent.trim(),
          btn1Copied: btns[1].classList.contains('copied'),
          statusAt3000: statusEl?.textContent.trim()
        };
        return { clicks: [click1, click2, click3], mid, end };
      } finally {
        window.setTimeout = realSetTimeout;
        window.clearTimeout = realClearTimeout;
      }
    })()`);
    assert.deepEqual(crossBtnResult.clicks, ["Copied!", "Copied!\u00A0", "Copied!"]);
    assert.equal(crossBtnResult.mid.btn0Text, "Copy BibTeX");
    assert.equal(crossBtnResult.mid.btn0Copied, false);
    assert.equal(crossBtnResult.mid.btn1Text, "Copied!");
    assert.equal(crossBtnResult.mid.btn1Copied, true);
    assert.ok(
      crossBtnResult.mid.statusAt2000.includes("Copied!"),
      `#pubCopyStatus cleared prematurely while button 2 active: ${JSON.stringify(crossBtnResult.mid)}`,
    );
    assert.equal(crossBtnResult.end.btn1Text, "Copy BibTeX");
    assert.equal(crossBtnResult.end.btn1Copied, false);
    assert.equal(crossBtnResult.end.statusAt3000, "");

    // Verify copyBibTeX error feedback & WCAG AA (>= 4.5:1) contrast in light & dark modes
    await cdp.eval(`(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: () => Promise.reject(new Error('denied')) },
        configurable: true
      });
    })()`);
    const origTheme = await cdp.eval(`document.documentElement.dataset.theme`);
    try {
      for (const theme of ["light", "dark"]) {
        await cdp.eval(`(() => {
          document.documentElement.dataset.theme = ${JSON.stringify(theme)};
          document.querySelector('.pub-copy-btn').click();
        })()`);
        await new Promise((r) => setTimeout(r, 300));
        const failInfo = await cdp.eval(`(() => {
          const btn = document.querySelector('.pub-copy-btn');
          const card = btn.closest('.pub-card');
          const parseRgba = (str) => {
            const m = str.match(/rgba?\\(([^)]+)\\)/);
            const parts = m[1].split(',').map((s) => Number(s.trim()));
            return [parts[0], parts[1], parts[2], parts[3] ?? 1];
          };
          const over = (fg, bg) => {
            const a = fg[3];
            return [
              a * fg[0] + (1 - a) * bg[0],
              a * fg[1] + (1 - a) * bg[1],
              a * fg[2] + (1 - a) * bg[2],
              1
            ];
          };
          const lum = ([r, g, b]) => {
            const ch = [r, g, b].map((v) => {
              const s = v / 255;
              return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
            });
            return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
          };
          const cardBg = parseRgba(getComputedStyle(card).backgroundColor);
          const btnBg = over(parseRgba(getComputedStyle(btn).backgroundColor), cardBg);
          const btnFg = over(parseRgba(getComputedStyle(btn).color), btnBg);
          const l1 = lum(btnFg);
          const l2 = lum(btnBg);
          const contrast = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
          return {
            text: btn.querySelector('.pub-copy-text')?.textContent.trim(),
            hasFailedClass: btn.classList.contains('copy-failed'),
            statusText: document.getElementById('pubCopyStatus')?.textContent.trim(),
            contrast
          };
        })()`);
        assert.equal(failInfo.text, "Copy failed");
        assert.equal(failInfo.hasFailedClass, true);
        assert.ok(failInfo.statusText.includes("Copy failed"));
        assert.ok(
          failInfo.contrast >= 4.5,
          `.pub-copy-btn.copy-failed ${theme} contrast ${failInfo.contrast.toFixed(2)}:1 < 4.5:1`,
        );
      }
    } finally {
      await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(origTheme)}`);
    }
  });

  it("maintains zero CLS, zero horizontal overflow (desktop & mobile), mobile #theme-toggle >= 44px, and Tab reachability on /cv/", async () => {
    const routes = [
      "/",
      "/about/",
      "/software/",
      "/publications/",
      "/cv/",
      "/contact/",
      "/search/",
      "/posts/2026-05-04-senior-dev-hpc-workflows/",
      "/posts/2026-06-15-neural-surrogates-shallow-water-equations/",
      "/posts/2026-07-20-scaling-python-hpc-uv-lustre/",
      "/posts/2026-09-22-pragmatic-scientist-audit-climate-workflows/",
      "/posts/2026-09-24-openifs-mass-conservation-stochastic-rounding/",
    ];
    for (const viewport of [
      { width: 1280, height: 800, mobile: false },
      { width: 320, height: 568, mobile: false },
      { width: 375, height: 812, mobile: false },
      { width: 390, height: 844, mobile: false },
      { width: 375, height: 812, mobile: true },
      { width: 390, height: 844, mobile: true },
    ]) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        ...viewport,
        deviceScaleFactor: 1,
      });
      for (const route of routes) {
        await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}${route}`);
        const metrics = await cdp.eval(`(async () => {
          let cls = 0;
          const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              if (!entry.hadRecentInput) cls += entry.value;
            }
          });
          observer.observe({ type: 'layout-shift', buffered: true });
          await new Promise((r) => setTimeout(r, 100));
          observer.disconnect();
          return {
            cls,
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth
          };
        })()`);
        assert.equal(metrics.cls, 0, `Expected CLS === 0 on ${route} (${viewport.width}px mobile=${viewport.mobile}), got ${metrics.cls}`);
        assert.ok(
          metrics.scrollWidth <= metrics.innerWidth,
          `Horizontal overflow on ${route} (${viewport.width}px mobile=${viewport.mobile}): ${metrics.scrollWidth} > ${metrics.innerWidth}`,
        );
        if (!viewport.mobile && viewport.width <= 390 && route === "/software/") {
          const gridOverflow = await cdp.eval(`(() => {
            const pc = document.querySelector('.post-content');
            const sw = document.querySelector('.software-container');
            const sim = document.querySelector('.simulation-gallery');
            return {
              pcClientW: pc?.clientWidth || 0,
              pcScrollW: pc?.scrollWidth || 0,
              swClientW: sw?.clientWidth || 0,
              swScrollW: sw?.scrollWidth || 0,
              simClientW: sim?.clientWidth || 0,
              simScrollW: sim?.scrollWidth || 0
            };
          })()`);
          assert.ok(
            gridOverflow.pcScrollW <= gridOverflow.pcClientW
            && gridOverflow.swScrollW <= gridOverflow.swClientW
            && gridOverflow.simScrollW <= gridOverflow.simClientW,
            `/software/ grid overflows container at ${viewport.width}px: ${JSON.stringify(gridOverflow)}`,
          );
        }
        if (viewport.width === 375 && route === "/posts/2026-09-24-openifs-mass-conservation-stochastic-rounding/") {
          const tableScroll = await cdp.eval(`(() => {
            const t = document.querySelector('.post-content table');
            return t ? { overflowX: getComputedStyle(t).overflowX, scrollWidth: t.scrollWidth, clientWidth: t.clientWidth } : null;
          })()`);
          assert.ok(tableScroll && tableScroll.overflowX === "auto", `Expected table overflow-x:auto, got ${JSON.stringify(tableScroll)}`);
          assert.ok(tableScroll.scrollWidth > tableScroll.clientWidth, `Expected wide table to scroll internally: ${JSON.stringify(tableScroll)}`);
        }
        if (viewport.width === 375 && route === "/") {
          const toggleBox = await cdp.eval(`(() => {
            const r = document.getElementById('theme-toggle')?.getBoundingClientRect();
            return r ? { width: r.width, height: r.height } : null;
          })()`);
          assert.ok(toggleBox && toggleBox.width >= 44 && toggleBox.height >= 44, (
            `Mobile #theme-toggle target too small: ${JSON.stringify(toggleBox)}`
          ));
        }
      }
    }

    // Verify <details class="cv-section-details"> starts closed, opens via anchor click, and Tab reachability works into .cv-item:nth-of-type(n+6)
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/cv/`);
    const cvDetailsState = await cdp.eval(`(() => {
      const details = [...document.querySelectorAll('details.cv-section-details')];
      return {
        count: details.length,
        initiallyClosed: details.every((d) => !d.open),
        deferredCv: getComputedStyle(document.querySelector('.cv-item:nth-of-type(n+6)')).contentVisibility
      };
    })()`);
    assert.equal(cvDetailsState.count, 2);
    assert.equal(cvDetailsState.initiallyClosed, true);
    assert.equal(cvDetailsState.deferredCv, "auto");

    await cdp.eval(`document.querySelector('.cv-nav-link[href="#trainings--certifications"]').click()`);
    await new Promise((r) => setTimeout(r, 250));
    const openedByNav = await cdp.eval(`document.querySelector('details.cv-section-details[data-cv-section="trainings--certifications"]')?.open`);
    assert.equal(openedByNav, true, "Clicking #trainings--certifications nav link must open Trainings <details>");

    await cdp.eval(`(() => {
      const items = [...document.querySelectorAll('.cv-item')];
      const beforeDeferred = items[4];
      const focusable = beforeDeferred.querySelector('a, button');
      if (focusable) focusable.focus();
      else items[5].previousElementSibling?.querySelector('a, button')?.focus();
    })()`);
    let enteredDeferredCv = false;
    for (let i = 0; i < 6; i++) {
      await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      enteredDeferredCv = await cdp.eval(`Boolean(document.activeElement?.closest('.cv-item:nth-of-type(n+6)'))`);
      if (enteredDeferredCv) break;
    }
    assert.equal(enteredDeferredCv, true, "Deferred .cv-item:nth-of-type(n+6) must be reachable via sequential Tab");
  });

  it("shows :focus-visible outline on #searchInput, excludes /404/ from index.json, and keeps SVG rollout labels inside card bounds", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/search/`);
    for (let i = 0; i < 40; i++) {
      const ready = await cdp.eval(`!document.getElementById('searchInput')?.disabled`);
      if (ready) break;
      await new Promise((r) => setTimeout(r, 50));
    }
    await cdp.eval(`document.activeElement?.blur()`);
    for (let i = 0; i < 40; i++) {
      await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      const activeId = await cdp.eval(`document.activeElement?.id`);
      if (activeId === "searchInput") break;
    }
    const searchFocus = await cdp.eval(`(() => {
      const el = document.activeElement;
      const cs = getComputedStyle(el);
      return {
        id: el?.id,
        matchesFocusVisible: el?.matches(':focus-visible'),
        outlineStyle: cs.outlineStyle,
        outlineWidth: cs.outlineWidth
      };
    })()`);
    assert.equal(searchFocus.id, "searchInput");
    assert.equal(searchFocus.matchesFocusVisible, true);
    assert.notEqual(searchFocus.outlineStyle, "none");
    assert.notEqual(searchFocus.outlineWidth, "0px");

    const indexJson = await cdp.eval(`fetch('/index.json').then((r) => r.json())`);
    assert.ok(Array.isArray(indexJson) && indexJson.length >= 10);
    assert.equal(
      indexJson.some((e) => (e.permalink || "").includes("/404") || (e.title || "").includes("404: Page Not Found")),
      false,
      "/404/ must not appear in /index.json",
    );

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/images/posts/neural_surrogate_swe_rollout.svg`);
    const svgBounds = await cdp.eval(`(() => {
      const texts = [...document.querySelectorAll('text')].filter((t) =>
        t.textContent.includes('FNO: Dispersion Blowup') || t.textContent.includes('Flowers: Stable Rollout')
      );
      return texts.map((t) => {
        const rect = t.closest('g')?.querySelector('rect');
        const tb = t.getBBox();
        const rb = rect.getBBox();
        return {
          label: t.textContent.trim(),
          tx: tb.x,
          tw: tb.width,
          rx: rb.x,
          rw: rb.width
        };
      });
    })()`);
    assert.equal(svgBounds.length, 2);
    for (const b of svgBounds) {
      assert.ok(
        b.tx >= b.rx && b.tx + b.tw <= b.rx + b.rw,
        `SVG label overflows card rect: ${JSON.stringify(b)}`,
      );
    }
  });

  it("injects button.copy-code on posts with <pre><code> and copies code block text", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-05-04-senior-dev-hpc-workflows/`);
    const codeCopyInfo = await cdp.eval(`(() => {
      let copied = null;
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: (txt) => { copied = txt; return Promise.resolve(); } },
        configurable: true
      });
      const codeBlocks = document.querySelectorAll('pre > code');
      const copyBtns = document.querySelectorAll('button.copy-code');
      const expectedText = codeBlocks[0]?.textContent || '';
      copyBtns[0]?.click();
      return {
        codeBlockCount: codeBlocks.length,
        copyBtnCount: copyBtns.length,
        copiedMatches: copied === expectedText && expectedText.length > 0,
        btnTextAfterClick: copyBtns[0]?.textContent.trim()
      };
    })()`);
    assert.ok(codeCopyInfo.codeBlockCount >= 1);
    assert.ok(codeCopyInfo.copyBtnCount >= 1, "Expected ShowCodeCopyButtons script to inject button.copy-code");
    assert.equal(codeCopyInfo.copiedMatches, true);
    assert.equal(codeCopyInfo.btnTextAfterClick, "copied!");
  });

  it("achieves WCAG 2.1 AA (>= 4.5:1) computed contrast in light and dark modes across all Idea 2A selectors", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    const checksByRoute = [
      ["/", [".post-tag"]],
      ["/about/", [".badge-lead"]],
      ["/software/", [".software-tag", ".sim-spec-pill", ".sim-physics"]],
      ["/publications/", [".pub-year-pill", ".pub-copy-btn", ".pub-bibtex-summary"]],
      ["/cv/", [".cv-nav-link", ".cv-date-badge", ".cv-skills-tag"]],
      ["/posts/2026-09-24-openifs-mass-conservation-stochastic-rounding/", [".chroma .c", ".post-tags a", ".paginav .title"]],
    ];

    for (const [route, selectors] of checksByRoute) {
      await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}${route}`);
      const origTheme = await cdp.eval(`document.documentElement.dataset.theme`);
      try {
        for (const theme of ["light", "dark"]) {
          await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(theme)}`);
          await new Promise((r) => setTimeout(r, 350));
          const results = await cdp.eval(`((sels) => {
            const parseRgba = (str) => {
              const m = str.match(/rgba?\\(([^)]+)\\)/);
              if (!m) return [0, 0, 0, 0];
              const parts = m[1].split(',').map((s) => Number(s.trim()));
              return [parts[0], parts[1], parts[2], parts[3] ?? 1];
            };
            const over = (fg, bg) => {
              const a = fg[3];
              return [
                a * fg[0] + (1 - a) * bg[0],
                a * fg[1] + (1 - a) * bg[1],
                a * fg[2] + (1 - a) * bg[2],
                1,
              ];
            };
            const lum = ([r, g, b]) => {
              const ch = [r, g, b].map((v) => {
                const s = v / 255;
                return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
              });
              return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
            };
            const effectiveBg = (el) => {
              const layers = [];
              let cur = el;
              while (cur) {
                layers.push(parseRgba(getComputedStyle(cur).backgroundColor));
                cur = cur.parentElement;
              }
              let bg = [255, 255, 255, 1];
              for (let i = layers.length - 1; i >= 0; i--) {
                bg = over(layers[i], bg);
              }
              return bg;
            };
            return sels.map((sel) => {
              const el = document.querySelector(sel);
              if (!el) return { sel, missing: true };
              const bg = effectiveBg(el);
              const fg = over(parseRgba(getComputedStyle(el).color), bg);
              const l1 = lum(fg);
              const l2 = lum(bg);
              const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
              return { sel, missing: false, ratio, fg: fg.slice(0, 3), bg: bg.slice(0, 3) };
            });
          })(${JSON.stringify(selectors)})`);

          for (const res of results) {
            assert.equal(res.missing, false, `Missing selector ${res.sel} on ${route}`);
            assert.ok(
              res.ratio >= 4.5,
              `Contrast failure on ${route} (${theme}) for ${res.sel}: ${res.ratio.toFixed(2)}:1 < 4.5:1 (fg=${res.fg}, bg=${res.bg})`,
            );
          }
        }
      } finally {
        await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(origTheme)}`);
      }
    }
  });

  it("renders profile-symbol.svg in home <h1>, removes duplicate /cv/ post-entry cards, and displays 3 CV PDF sublabels", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/`);
    const homeCheck = await cdp.eval(`(() => {
      const h1 = document.querySelector('.home-info h1');
      const img = h1?.querySelector('img.home-symbol-icon');
      return {
        hasImg: Boolean(img),
        src: img?.getAttribute('src'),
        alt: img?.getAttribute('alt'),
        ariaHidden: img?.getAttribute('aria-hidden'),
        complete: img?.complete,
        naturalWidth: img?.naturalWidth,
        hasEmojiBar: Boolean(h1?.querySelector('.symbol-bar')),
        h1Text: h1?.textContent || '',
      };
    })()`);
    assert.equal(homeCheck.hasImg, true);
    assert.equal(homeCheck.src, "/images/decor/profile-symbol.svg");
    assert.equal(homeCheck.alt, "");
    assert.equal(homeCheck.ariaHidden, "true");
    assert.equal(homeCheck.complete, true);
    assert.ok(homeCheck.naturalWidth > 0, "Expected profile-symbol.svg to decode with naturalWidth > 0");
    assert.equal(homeCheck.hasEmojiBar, false);
    assert.equal(/[🌐♾🤖]/.test(homeCheck.h1Text), false);

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/cv/`);
    const cvCheck = await cdp.eval(`(() => {
      const btns = [...document.querySelectorAll('.cv-download-btn')];
      return {
        postEntries: document.querySelectorAll('article.post-entry').length,
        btnCount: btns.length,
        sublabels: btns.map((b) => b.querySelector('.cv-download-sublabel')?.textContent.trim() || ''),
      };
    })()`);
    assert.equal(cvCheck.postEntries, 0);
    assert.equal(cvCheck.btnCount, 3);
    assert.ok(cvCheck.sublabels.every((s) => s.length > 0));
    assert.equal(new Set(cvCheck.sublabels).size, 3);
  });

  it("highlights live publication matches via CSS.highlights, syncs ?q= URL state, and handles / and Escape shortcuts", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
    const apiSupported = await cdp.eval(`typeof Highlight !== 'undefined' && 'highlights' in CSS`);
    assert.equal(apiSupported, true);

    await cdp.eval(`document.activeElement?.blur()`);
    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: "/",
      code: "Slash",
      text: "/",
      unmodifiedText: "/",
      windowsVirtualKeyCode: 191,
      nativeVirtualKeyCode: 191,
    });
    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key: "/",
      code: "Slash",
      windowsVirtualKeyCode: 191,
      nativeVirtualKeyCode: 191,
    });

    const afterSlash = await cdp.eval(`({
      activeId: document.activeElement?.id,
      value: document.getElementById('pubFilterInput')?.value
    })`);
    assert.equal(afterSlash.activeId, "pubFilterInput");
    assert.equal(afterSlash.value, "");

    await cdp.send("Input.insertText", { text: "EC-Earth" });
    await new Promise((r) => setTimeout(r, 80));
    const afterFilter = await cdp.eval(`({
      highlightSize: CSS.highlights.get('pub-search-match')?.size || 0,
      qParam: new URLSearchParams(window.location.search).get('q'),
      markCount: document.querySelectorAll('.pub-card mark').length
    })`);
    assert.ok(afterFilter.highlightSize > 0, "Expected CSS.highlights range matches for EC-Earth");
    assert.equal(afterFilter.qParam, "EC-Earth");
    assert.equal(afterFilter.markCount, 0, "CSS.highlights must not mutate DOM with <mark> elements");

    const composingEscapeValue = await cdp.eval(`(() => {
      const inp = document.getElementById('pubFilterInput');
      inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true, isComposing: true }));
      return inp.value;
    })()`);
    assert.equal(composingEscapeValue, "EC-Earth", "Escape during IME composition must not clear filter");

    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: "Escape",
      code: "Escape",
      windowsVirtualKeyCode: 27,
      nativeVirtualKeyCode: 27,
    });
    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key: "Escape",
      code: "Escape",
      windowsVirtualKeyCode: 27,
      nativeVirtualKeyCode: 27,
    });
    await new Promise((r) => setTimeout(r, 50));

    const afterEscape = await cdp.eval(`({
      value: document.getElementById('pubFilterInput')?.value,
      hasHighlight: CSS.highlights.has('pub-search-match'),
      hasQ: new URLSearchParams(window.location.search).has('q'),
      totalCards: document.querySelectorAll('.pub-card').length,
      visibleCards: [...document.querySelectorAll('.pub-card')].filter((c) => c.style.display !== 'none').length
    })`);
    assert.equal(afterEscape.value, "");
    assert.equal(afterEscape.hasHighlight, false);
    assert.equal(afterEscape.hasQ, false);
    assert.equal(afterEscape.visibleCards, afterEscape.totalCards);

    // Ensure '/' inside another editable control does not steal focus
    await cdp.eval(`(() => {
      const ta = document.createElement('textarea');
      ta.id = 'tmpEditableTest';
      document.body.appendChild(ta);
      ta.focus();
    })()`);
    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: "/",
      code: "Slash",
      text: "/",
      unmodifiedText: "/",
      windowsVirtualKeyCode: 191,
      nativeVirtualKeyCode: 191,
    });
    await cdp.send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key: "/",
      code: "Slash",
      windowsVirtualKeyCode: 191,
      nativeVirtualKeyCode: 191,
    });
    const editableStay = await cdp.eval(`(() => {
      const id = document.activeElement?.id;
      document.getElementById('tmpEditableTest')?.remove();
      return id;
    })()`);
    assert.equal(editableStay, "tmpEditableTest");

    // Direct navigation with ?q= query initializes filter and highlights
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/?q=irregular%20boundaries`);
    const initFromUrl = await cdp.eval(`({
      value: document.getElementById('pubFilterInput')?.value,
      status: document.getElementById('pubFilterStatus')?.textContent.trim(),
      highlightSize: CSS.highlights.get('pub-search-match')?.size || 0
    })`);
    assert.equal(initFromUrl.value, "irregular boundaries");
    assert.ok(initFromUrl.status.startsWith("Showing 1 of "), initFromUrl.status);
    assert.ok(initFromUrl.highlightSize > 0);

    // Verify UTF-16 .toLowerCase() expansion (e.g. U+0130) does not shift ranges or throw IndexSizeError
    const unicodeHighlight = await cdp.eval(`(() => {
      const el = document.createElement('div');
      el.appendChild(document.createTextNode('\\u0130 '));
      const strong = document.createElement('strong');
      strong.textContent = 'Foo';
      el.appendChild(strong);
      const ranges = [];
      addFieldMatchRanges(el, 'foo', ranges);
      return ranges.map((r) => r.toString());
    })()`);
    assert.deepEqual(unicodeHighlight, ["Foo"]);
  });

  it("finds enriched publication and software entries via Fuse on /search/", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/search/`);
    for (let i = 0; i < 40; i++) {
      const ready = await cdp.eval(`!document.getElementById('searchInput')?.disabled`);
      if (ready) break;
      await new Promise((r) => setTimeout(r, 50));
    }

    await cdp.eval(`document.getElementById('searchInput').focus()`);
    await cdp.send("Input.insertText", { text: "Tsujino" });
    await new Promise((r) => setTimeout(r, 350));
    const pubSearchHrefs = await cdp.eval(`[...document.querySelectorAll('#searchResults li a')].map((a) => a.getAttribute('href'))`);
    assert.ok(
      pubSearchHrefs.some((h) => h && h.includes("/publications/?q=")),
      `Expected /publications/?q= result for Tsujino, got ${JSON.stringify(pubSearchHrefs)}`,
    );

    await cdp.eval(`(() => {
      const inp = document.getElementById('searchInput');
      inp.value = '';
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.focus();
    })()`);
    await cdp.send("Input.insertText", { text: "pisces-inidata" });
    await new Promise((r) => setTimeout(r, 350));
    const swSearchHrefs = await cdp.eval(`[...document.querySelectorAll('#searchResults li a')].map((a) => a.getAttribute('href'))`);
    assert.ok(
      swSearchHrefs.some((h) => h && h.endsWith("/software/")),
      `Expected /software/ result for pisces-inidata, got ${JSON.stringify(swSearchHrefs)}`,
    );
  });

  it("applies modern CSS polish (68ch measure, text-wrap, scroll reading progress, and @view-transition) while respecting reduced motion", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-09-24-openifs-mass-conservation-stochastic-rounding/`);
    const polish = await cdp.eval(`(() => {
      const h1 = document.querySelector('h1.post-title');
      const pc = document.querySelector('.post-content');
      const proseP = [...document.querySelectorAll('.post-content > p')].find((el) => !el.querySelector('img'));
      const figImg = document.querySelector('.entry-cover img[src*="co2_90day_mass_budget_tracking.png"]');
      const dupInline = document.querySelector('.post-content img[src*="co2_90day_mass_budget_tracking.png"]');
      const table = document.querySelector('.post-content table');
      const h1Style = getComputedStyle(h1);
      const pStyle = getComputedStyle(proseP);
      const tableStyle = getComputedStyle(table);
      const beforeStyle = getComputedStyle(document.querySelector('.post-single'), '::before');
      let hasViewTransition = false;
      for (const sheet of document.styleSheets) {
        try {
          const walk = (rules) => {
            for (const r of rules) {
              if (r.cssText && r.cssText.includes('@view-transition')) hasViewTransition = true;
              if (r.cssRules) walk(r.cssRules);
            }
          };
          walk(sheet.cssRules);
        } catch {}
      }
      return {
        h1Wrap: h1Style.textWrap,
        pWrap: pStyle.textWrap,
        pMaxWidthPx: parseFloat(pStyle.maxWidth),
        pFontSizePx: parseFloat(pStyle.fontSize),
        postContentWidth: pc?.getBoundingClientRect().width || 0,
        co2ImgComplete: Boolean(figImg?.complete && figImg?.naturalWidth > 0),
        co2ImgWidth: figImg?.getBoundingClientRect().width || 0,
        hasDupInline: Boolean(dupInline),
        tableMaxWidth: tableStyle.maxWidth,
        beforeContent: beforeStyle.content,
        beforeTimeline: beforeStyle.animationTimeline,
        hasViewTransition,
      };
    })()`);
    assert.equal(polish.h1Wrap, "balance");
    assert.equal(polish.pWrap, "pretty");
    assert.ok(polish.pMaxWidthPx > 0 && polish.pMaxWidthPx <= 68 * polish.pFontSizePx, (
      `Expected .post-content p maxWidth <= 68em (${68 * polish.pFontSizePx}px), got ${polish.pMaxWidthPx}px`
    ));
    assert.equal(polish.co2ImgComplete, true, "Expected co2_90day_mass_budget_tracking.png cover image to load");
    assert.equal(polish.hasDupInline, false, "Duplicate inline co2_90day_mass_budget_tracking.png must be removed");
    assert.ok(
      polish.co2ImgWidth > polish.pMaxWidthPx,
      `Expected co2_90day_mass_budget_tracking.png width (${polish.co2ImgWidth}px) > 68ch prose cap (${polish.pMaxWidthPx}px)`,
    );
    assert.ok(
      Math.abs(polish.co2ImgWidth - polish.postContentWidth) <= 4,
      `Expected co2_90day_mass_budget_tracking.png width (${polish.co2ImgWidth}px) to match .post-content (${polish.postContentWidth}px)`,
    );
    assert.equal(polish.tableMaxWidth, "100%");
    assert.notEqual(polish.beforeContent, "none");
    assert.ok((polish.beforeTimeline || "").includes("scroll"), `Expected scroll() timeline, got ${polish.beforeTimeline}`);
    assert.equal(polish.hasViewTransition, true);

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-06-15-neural-surrogates-shallow-water-equations/`);
    const sweFigures = await cdp.eval(`(async () => {
      const pc = document.querySelector('.post-content');
      const proseP = [...document.querySelectorAll('.post-content > p')].find((el) => !el.querySelector('img'));
      const flowersImg = document.querySelector('.post-content img[src*="flowers_warpfield.png"]');
      const svgImg = document.querySelector('.post-content img[src*="neural_surrogate_swe_rollout.svg"]');
      for (const img of [flowersImg, svgImg]) {
        if (!img) continue;
        img.scrollIntoView({ block: 'center' });
        if (!img.complete) {
          await new Promise((resolve) => {
            img.addEventListener('load', resolve, { once: true });
            img.addEventListener('error', resolve, { once: true });
            setTimeout(resolve, 3000);
          });
        }
      }
      await new Promise((r) => setTimeout(r, 50));
      return {
        postContentWidth: pc?.getBoundingClientRect().width || 0,
        pMaxWidthPx: proseP ? parseFloat(getComputedStyle(proseP).maxWidth) : 0,
        flowersComplete: Boolean(flowersImg?.complete && flowersImg?.naturalWidth > 0),
        flowersWidth: flowersImg?.getBoundingClientRect().width || 0,
        flowersParentMaxWidth: flowersImg ? getComputedStyle(flowersImg.parentElement).maxWidth : null,
        svgComplete: Boolean(svgImg?.complete && svgImg?.naturalWidth > 0),
        svgWidth: svgImg?.getBoundingClientRect().width || 0,
        svgParentMaxWidth: svgImg ? getComputedStyle(svgImg.parentElement).maxWidth : null,
      };
    })()`);
    assert.equal(sweFigures.flowersComplete, true, "Expected flowers_warpfield.png to load");
    assert.ok(
      sweFigures.flowersWidth > sweFigures.pMaxWidthPx,
      `Expected flowers_warpfield.png width (${sweFigures.flowersWidth}px) > 68ch (${sweFigures.pMaxWidthPx}px)`,
    );
    assert.ok(
      Math.abs(sweFigures.flowersWidth - sweFigures.postContentWidth) <= 2,
      `Expected flowers_warpfield.png width (${sweFigures.flowersWidth}px) to match .post-content (${sweFigures.postContentWidth}px)`,
    );
    assert.equal(sweFigures.flowersParentMaxWidth, "100%");
    assert.equal(sweFigures.svgComplete, true, "Expected neural_surrogate_swe_rollout.svg to load");
    assert.ok(
      Math.abs(sweFigures.svgWidth - sweFigures.postContentWidth) <= 2,
      `Expected neural_surrogate_swe_rollout.svg width (${sweFigures.svgWidth}px) to match .post-content (${sweFigures.postContentWidth}px)`,
    );
    assert.equal(sweFigures.svgParentMaxWidth, "100%");

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-09-24-openifs-mass-conservation-stochastic-rounding/`);

    await cdp.send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: "reduce" }],
    });
    try {
      const reducedBefore = await cdp.eval(`getComputedStyle(document.querySelector('.post-single'), '::before').content`);
      assert.equal(reducedBefore, "none", "Scroll progress bar must disable under prefers-reduced-motion: reduce");
    } finally {
      await cdp.send("Emulation.setEmulatedMedia", { features: [] });
    }
  });
});
