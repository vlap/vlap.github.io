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

function runHugoBuild(outDir, baseUrl, extraArgs = []) {
  return new Promise((resolve, reject) => {
    const proc = spawn("hugo", ["--gc", "--minify", ...extraArgs, "-d", outDir, "--baseURL", `${baseUrl}/`], {
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

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/work/`);
    const persistedWork = await cdp.eval(`({
      meta: document.querySelector('meta[name="color-scheme"]')?.content,
      theme: document.documentElement.dataset.theme,
      linkColor: getComputedStyle(document.querySelector('.post-content a')).color
    })`);
    assert.equal(persistedWork.theme, afterFirstClick.theme);
    assert.equal(persistedWork.meta, afterFirstClick.theme);

    await cdp.eval(`document.getElementById('theme-toggle').click()`);
    await new Promise((r) => setTimeout(r, 250));
    const toggledWork = await cdp.eval(`({
      meta: document.querySelector('meta[name="color-scheme"]')?.content,
      theme: document.documentElement.dataset.theme,
      linkColor: getComputedStyle(document.querySelector('.post-content a')).color
    })`);
    assert.notEqual(toggledWork.theme, persistedWork.theme);
    assert.equal(toggledWork.meta, toggledWork.theme);
    assert.notEqual(toggledWork.linkColor, persistedWork.linkColor, "--accent-ocean must adapt between light and dark");
  });

  it("activates .sim-facade native <button> via keyboard Enter and replaces with native <video>", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/work/`);
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
        tabIndex: video.tabIndex,
        isFocused: document.activeElement === video,
        poster: video.getAttribute('poster'),
        sources
      };
    })()`);
    assert.ok(videoInfo, "Expected .sim-video video element after facade activation");
    assert.equal(videoInfo.controls, true);
    assert.equal(videoInfo.muted, true);
    assert.equal(videoInfo.tabIndex, 0, "Inserted <video> must have tabIndex=0");
    assert.equal(videoInfo.isFocused, true, "Activating button.sim-facade must move focus to inserted <video>");
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
      "/work/",
      "/publications/",
      "/cv/",
      "/cv/presentations/",
      "/cv/trainings/",
      "/posts/",
      "/kinds/",
      "/kinds/note/",
      "/kinds/talk/",
      "/tags/",
      "/tags/hpc/",
      "/categories/",
      "/404.html",
      "/posts/2026-06-15-neural-surrogates-shallow-water-equations/",
      "/posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/",
      "/posts/2013-06-21-ams19-global-modelling-surface-internal-tides/",
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
        if (!viewport.mobile && viewport.width <= 390 && route === "/work/") {
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
            `/work/ grid overflows container at ${viewport.width}px: ${JSON.stringify(gridOverflow)}`,
          );
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

  it("keeps SVG rollout labels inside card bounds", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });

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

  it("injects button.copy-code on posts with <pre><code>, supports keyboard Tab & clipboard rejection, and skips .pub-bibtex-block", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-06-15-neural-surrogates-shallow-water-equations/`);
    await cdp.eval(`(() => {
      window.__copiedText = null;
      window.__unhandledRejections = [];
      window.addEventListener('unhandledrejection', (e) => {
        window.__unhandledRejections.push(String(e.reason));
      });
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: (txt) => { window.__copiedText = txt; return Promise.resolve(); } },
        configurable: true
      });
    })()`);

    // Verify button.copy-code is in keyboard Tab order (never display: none at rest) and visible on :focus-visible
    const preTargetOk = await cdp.eval(`(() => {
      const btn = document.querySelector('button.copy-code');
      const restDisplay = btn ? getComputedStyle(btn).display : null;
      const container = btn?.closest('.highlight, pre');
      let prev = container?.previousElementSibling;
      while (prev && !prev.querySelector('a, button, summary, [tabindex]')) {
        prev = prev.previousElementSibling;
      }
      const anchor = prev?.querySelector('a, button, summary, [tabindex]') || document.querySelector('.post-header a');
      anchor?.focus();
      return { ok: Boolean(btn && anchor), restDisplay };
    })()`);
    assert.equal(preTargetOk.ok, true);
    assert.notEqual(preTargetOk.restDisplay, "none", "button.copy-code must not use display: none at rest");
    let tabbedToCopy = false;
    for (let i = 0; i < 15; i++) {
      await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      tabbedToCopy = await cdp.eval(`document.activeElement?.classList.contains('copy-code') || false`);
      if (tabbedToCopy) break;
    }
    assert.equal(tabbedToCopy, true, "button.copy-code must be reachable via keyboard Tab");

    const focusStyle = await cdp.eval(`(() => {
      const btn = document.activeElement;
      const cs = getComputedStyle(btn);
      return {
        type: btn.getAttribute('type'),
        display: cs.display,
        opacity: Number(cs.opacity),
        outlineStyle: cs.outlineStyle,
        outlineWidth: cs.outlineWidth
      };
    })()`);
    assert.equal(focusStyle.type, "button");
    assert.notEqual(focusStyle.display, "none");
    assert.equal(focusStyle.opacity, 1);
    assert.notEqual(focusStyle.outlineStyle, "none");
    assert.notEqual(focusStyle.outlineWidth, "0px");

    const expectedText = await cdp.eval(`document.querySelector('pre > code')?.textContent || ''`);
    await cdp.eval(`document.querySelector('button.copy-code').click()`);
    await new Promise((r) => setTimeout(r, 50));
    const codeCopyInfo = await cdp.eval(`(() => {
      const codeBlocks = document.querySelectorAll('pre > code');
      const copyBtns = document.querySelectorAll('button.copy-code');
      return {
        codeBlockCount: codeBlocks.length,
        copyBtnCount: copyBtns.length,
        copiedMatches: window.__copiedText === ${JSON.stringify(expectedText)} && ${expectedText.length} > 0,
        btnTextAfterClick: copyBtns[0]?.textContent.trim()
      };
    })()`);
    assert.ok(codeCopyInfo.codeBlockCount >= 1);
    assert.ok(codeCopyInfo.copyBtnCount >= 1, "Expected ShowCodeCopyButtons script to inject button.copy-code");
    assert.equal(codeCopyInfo.copiedMatches, true);
    assert.equal(codeCopyInfo.btnTextAfterClick, "copied!");

    // Verify rejected clipboard promise does not throw unhandledrejection or falsely show "copied!"
    await cdp.eval(`(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: () => Promise.reject(new Error('Clipboard denied')) },
        configurable: true
      });
      document.querySelector('button.copy-code').click();
    })()`);
    await new Promise((r) => setTimeout(r, 50));
    const rejectInfo = await cdp.eval(`(() => {
      const btn = document.querySelector('button.copy-code');
      return {
        text: btn?.textContent.trim(),
        hasFailedClass: btn?.classList.contains('copy-failed') || false,
        unhandled: window.__unhandledRejections
      };
    })()`);
    assert.deepEqual(rejectInfo.unhandled, [], "Rejected clipboard write must not cause unhandledrejection");
    assert.notEqual(rejectInfo.text, "copied!", "Rejected clipboard write must not falsely display 'copied!'");
    assert.equal(rejectInfo.hasFailedClass, true);

    // Verify zero .copy-code buttons are injected inside .pub-bibtex-block on /publications/
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
    const pubCopyCodeCount = await cdp.eval(`document.querySelectorAll('.pub-bibtex-block .copy-code, button.copy-code').length`);
    assert.equal(pubCopyCodeCount, 0, "/publications/ must not inject duplicate button.copy-code inside BibTeX blocks");
  });

  it("achieves WCAG 2.1 AA (>= 4.5:1) computed contrast in light and dark modes across all monograph selectors", async () => {
    const checksByRoute = [
      ["/", [".home-audience-link", ".home-subtitle", ".kind-badge", ".log-row-date", ".view-all-link", ".footer .social-icons a"]],
      ["/work/", [".software-tag", ".sim-spec-pill", ".sim-physics", ".pub-badge-btn"]],
      ["/publications/", [".pub-year-pill", ".pub-year-heading", ".pub-copy-btn", ".pub-bibtex-summary", ".action-pill"]],
      ["/cv/", [".cv-nav-link", ".cv-date-badge", ".cv-download-sublabel", ".cv-download-badge", ".cv-download-badge--primary", ".action-pill"]],
      ["/cv/presentations/", [".cv-link", ".action-pill", ".action-pill--primary"]],
      ["/cv/trainings/", [".cv-skills-tag", ".cv-date-badge"]],
      ["/posts/", [".log-kind-pill.active", ".log-kind-pill:not(.active)", ".kind-badge", ".log-row-date", ".post-tag"]],
      ["/tags/", [".terms-tags a", "h1"]],
      ["/tags/hpc/", [".kind-badge", ".log-row-date", ".post-tag"]],
      ["/categories/", ["h1", "#menu a", ".footer .social-icons a"]],
      ["/404.html", ["h1", ".post-content p", ".post-content a", ".footer .social-icons a"]],
      ["/posts/2026-06-15-neural-surrogates-shallow-water-equations/", [".chroma .c1", ".post-tags a", ".paginav .title", ".kind-badge"]],
    ];

    for (const viewport of [
      { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false },
      { width: 375, height: 812, deviceScaleFactor: 1, mobile: true },
    ]) {
      await cdp.send("Emulation.setDeviceMetricsOverride", viewport);
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
                const matched = [...document.querySelectorAll(sel)];
                if (matched.length === 0) return { sel, matchedCount: 0, visibleCount: 0, failures: [] };
                const visible = matched.filter((el) => {
                  if (el.closest('details:not([open]) > :not(summary)')) return false;
                  const r = el.getBoundingClientRect();
                  return r.width > 0 && r.height > 0;
                });
                const failures = [];
                for (const el of visible) {
                  el.scrollIntoView({ block: 'nearest' });
                  const bg = effectiveBg(el);
                  const fg = over(parseRgba(getComputedStyle(el).color), bg);
                  const l1 = lum(fg);
                  const l2 = lum(bg);
                  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
                  if (ratio < 4.5) {
                    failures.push({
                      text: el.textContent.trim().slice(0, 40),
                      ratio,
                      fg: fg.slice(0, 3),
                      bg: bg.slice(0, 3),
                    });
                  }
                }
                return { sel, matchedCount: matched.length, visibleCount: visible.length, failures };
              });
            })(${JSON.stringify(selectors)})`);

            for (const res of results) {
              assert.ok(
                res.matchedCount > 0 && res.visibleCount > 0,
                `Missing or invisible selector ${res.sel} on ${route} (${viewport.width}px ${theme}): ${JSON.stringify(res)}`,
              );
              assert.equal(
                res.failures.length,
                0,
                `Contrast failure on ${route} (${viewport.width}px ${theme}) for ${res.sel}: ${JSON.stringify(res.failures)}`,
              );
            }
          }
        } finally {
          await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(origTheme)}`);
        }
      }
    }
  });

  it("renders M2 tidal field SVG, monograph Log rows, 3 nav items, 3 Home links, 6 footer social icons, 2 CV PDF buttons, and EGU2014 talk link", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/`);
    const origHomeTheme = await cdp.eval(`document.documentElement.dataset.theme`);
    const themeSnapshots = {};
    try {
      for (const theme of ["light", "dark"]) {
        await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(theme)}`);
        await new Promise((r) => setTimeout(r, 250));
        themeSnapshots[theme] = await cdp.eval(`(() => {
          const band = document.querySelector('.home-info .tidal-field-band');
          const svg = document.querySelector('.home-info .tidal-field-svg');
          const hi = document.querySelector('.home-info')?.getBoundingClientRect();
          const bandRect = band?.getBoundingClientRect();
          const svgRect = svg?.getBoundingClientRect();
          const coamp = svg?.querySelector('g.tidal-coamplitude');
          const cotid = svg?.querySelector('g.tidal-cotidal');
          const zero = svg?.querySelector('.tidal-cotidal-zero');
          const amphiCircle = svg?.querySelector('g.tidal-amphidromes circle');
          const csSvg = svg ? getComputedStyle(svg) : null;
          const csCoamp = coamp ? getComputedStyle(coamp) : null;
          const csCotid = cotid ? getComputedStyle(cotid) : null;
          const csZero = zero ? getComputedStyle(zero) : null;
          const csCircle = amphiCircle ? getComputedStyle(amphiCircle) : null;
          const firstCoPath = coamp?.querySelector('path');
          const csPath = firstCoPath ? getComputedStyle(firstCoPath) : null;
          return {
            legacyImg: Boolean(document.querySelector('img.home-symbol-icon')),
            legacySrc: Boolean(document.querySelector('[src*="profile-symbol.svg"]')),
            bandCount: document.querySelectorAll('.home-info .tidal-field-band').length,
            svgCount: document.querySelectorAll('.home-info .tidal-field-svg').length,
            bandAriaHidden: band?.getAttribute('aria-hidden'),
            svgAriaHidden: svg?.getAttribute('aria-hidden'),
            viewBox: svg?.getAttribute('viewBox'),
            primitiveCount: svg ? svg.querySelectorAll('path, circle, ellipse, polyline, polygon').length : 0,
            bandInBounds: Boolean(hi && bandRect && bandRect.width >= 40 && bandRect.height >= 24 && bandRect.left >= hi.left - 1 && bandRect.right <= hi.right + 1),
            svgInBounds: Boolean(hi && svgRect && svgRect.width >= 40 && svgRect.height >= 24 && svgRect.left >= hi.left - 1 && svgRect.right <= hi.right + 1),
            svgDisplay: csSvg?.display,
            svgVisibility: csSvg?.visibility,
            svgOpacity: csSvg ? Number(csSvg.opacity) : 0,
            coampColor: csCoamp?.color,
            coampOpacity: csCoamp ? Number(csCoamp.opacity) : 0,
            pathStroke: csPath?.stroke,
            cotidColor: csCotid?.color,
            cotidOpacity: csCotid ? Number(csCotid.opacity) : 0,
            zeroColor: csZero?.color,
            circleFill: csCircle?.fill,
            circleStroke: csCircle?.stroke,
          };
        })()`);
      }
    } finally {
      await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(origHomeTheme)}`);
    }

    for (const theme of ["light", "dark"]) {
      const snap = themeSnapshots[theme];
      assert.equal(snap.legacyImg, false, `Legacy img.home-symbol-icon present in ${theme}`);
      assert.equal(snap.legacySrc, false, `Legacy profile-symbol.svg present in ${theme}`);
      assert.equal(snap.bandCount, 1);
      assert.equal(snap.svgCount, 1);
      assert.equal(snap.bandAriaHidden, "true");
      assert.equal(snap.svgAriaHidden, "true");
      assert.ok(snap.viewBox && snap.viewBox.split(/\s+/).length === 4, `Invalid viewBox: ${snap.viewBox}`);
      assert.ok(snap.primitiveCount >= 4, `Expected >= 4 contour primitives, got ${snap.primitiveCount}`);
      assert.equal(snap.bandInBounds, true, `.tidal-field-band out of bounds in ${theme}`);
      assert.equal(snap.svgInBounds, true, `.tidal-field-svg out of bounds in ${theme}`);
      assert.notEqual(snap.svgDisplay, "none");
      assert.notEqual(snap.svgVisibility, "hidden");
      assert.ok(snap.svgOpacity > 0 && snap.coampOpacity > 0 && snap.cotidOpacity > 0);
      assert.ok(snap.pathStroke && snap.pathStroke !== "none", `Missing stroke on tidal path: ${snap.pathStroke}`);
      assert.ok(snap.circleStroke && snap.circleStroke !== "none");
    }
    assert.notEqual(themeSnapshots.light.coampColor, themeSnapshots.dark.coampColor, "coamplitude color must adapt between light and dark");
    assert.notEqual(themeSnapshots.light.cotidColor, themeSnapshots.dark.cotidColor, "cotidal color must adapt between light and dark");
    assert.notEqual(themeSnapshots.light.circleFill, themeSnapshots.dark.circleFill, "amphidrome circle fill must adapt between light and dark");

    const homeCheck = await cdp.eval(`(() => {
      const h1 = document.querySelector('.home-info h1');
      const navItems = [...document.querySelectorAll('#menu a')].map((a) => ({
        name: a.textContent.trim(),
        href: a.getAttribute('href'),
      }));
      const audienceLinks = [...document.querySelectorAll('.home-audience-links a')].map((a) => ({
        title: a.querySelector('.home-audience-title')?.textContent.trim() || '',
        href: a.getAttribute('href'),
      }));
      const footerIcons = [...document.querySelectorAll('footer.footer .social-icons a')].map((a) => ({
        href: a.getAttribute('href'),
        label: a.getAttribute('aria-label'),
      }));
      const logRows = [...document.querySelectorAll('.home-posts .log-rows .log-row')].map((row) => {
        const cs = getComputedStyle(row);
        return {
          hasBadge: Boolean(row.querySelector('.kind-badge')),
          badgeText: row.querySelector('.kind-badge')?.textContent.trim() || '',
          titleHref: row.querySelector('a.log-row-title-link')?.getAttribute('href') || '',
          dateText: row.querySelector('time.log-row-date')?.textContent.trim() || '',
          boxShadow: cs.boxShadow,
          borderRadius: cs.borderRadius,
        };
      });
      return {
        hasEmojiBar: Boolean(h1?.querySelector('.symbol-bar')),
        h1Text: h1?.textContent || '',
        navItems,
        audienceLinks,
        footerIcons,
        hasImpactMetrics: Boolean(document.querySelector('.impact-metrics')),
        hasHighlights: Boolean(document.querySelector('.research-highlights')),
        logHeading: document.querySelector('.home-posts h2')?.textContent.trim() || '',
        logRows,
      };
    })()`);
    assert.equal(homeCheck.hasEmojiBar, false);
    assert.equal(/[🌐♾🤖🌍]/.test(homeCheck.h1Text), false);
    assert.equal(homeCheck.hasImpactMetrics, false);
    assert.equal(homeCheck.hasHighlights, false);
    assert.deepEqual(
      homeCheck.navItems.map((n) => n.name),
      ["Work", "Log", "CV"],
    );
    assert.equal(homeCheck.audienceLinks.length, 3);
    assert.equal(homeCheck.audienceLinks[0].title, "Collaborate");
    assert.ok(homeCheck.audienceLinks[0].href.endsWith("/work/"));
    assert.equal(homeCheck.audienceLinks[1].title, "Hiring");
    assert.ok(homeCheck.audienceLinks[1].href.endsWith("/cv/"));
    assert.equal(homeCheck.audienceLinks[2].title, "Read");
    assert.ok(homeCheck.audienceLinks[2].href.endsWith("/posts/"));
    assert.equal(homeCheck.footerIcons.length, 6);
    assert.ok(homeCheck.footerIcons.every((i) => i.label && i.label.length > 0));
    assert.equal(homeCheck.logHeading, "Latest from the Log");
    assert.ok(homeCheck.logRows.length >= 2 && homeCheck.logRows.length <= 3, `Expected 2..3 Home log rows, got ${homeCheck.logRows.length}`);
    for (const row of homeCheck.logRows) {
      assert.equal(row.hasBadge, true);
      assert.ok(["note", "talk", "paper"].includes(row.badgeText), `Unexpected badge: ${row.badgeText}`);
      assert.ok(row.titleHref.length > 0, "Missing a.log-row-title-link href on Home");
      assert.match(row.dateText, /^\d{4}-\d{2}-\d{2}$/);
      assert.equal(row.boxShadow, "none");
      assert.equal(row.borderRadius, "0px");
    }

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/cv/`);
    const cvCheck = await cdp.eval(`(() => {
      const btns = [...document.querySelectorAll('.cv-download-btn')];
      const eguItem = [...document.querySelectorAll('.cv-item')].find((el) => el.textContent.includes('EGU2014'));
      const eguTalkHref = eguItem?.querySelector('a[href*="/posts/2014-04-28-egu2014"]')?.getAttribute('href') || null;
      return {
        postEntries: document.querySelectorAll('article.post-entry, .log-entry, .log-row').length,
        btnCount: btns.length,
        sublabels: btns.map((b) => b.querySelector('.cv-download-sublabel')?.textContent.trim() || ''),
        eguTalkHref,
      };
    })()`);
    assert.equal(cvCheck.postEntries, 0);
    assert.equal(cvCheck.btnCount, 2);
    assert.ok(cvCheck.sublabels.every((s) => s.length > 0));
    assert.equal(new Set(cvCheck.sublabels).size, 2);
    assert.ok(cvCheck.eguTalkHref, "Expected EGU2014 entry on /cv/ to link to its Log talk page");
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

  it("preserves left-aligned monograph header, 720px alignment, clean pill links, modern CSS polish, redirects, and reduced motion", async () => {
    for (const vp of [
      { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false },
      { width: 375, height: 812, deviceScaleFactor: 1, mobile: true },
    ]) {
      await cdp.send("Emulation.setDeviceMetricsOverride", vp);
      await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/`);
      const origTheme = await cdp.eval(`document.documentElement.dataset.theme`);
      try {
        for (const theme of ["light", "dark"]) {
          await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(theme)}`);
          await new Promise((r) => setTimeout(r, 200));
          const homeAlign = await cdp.eval(`(() => {
            const rectsOverlap = (a, b) => !(
              a.right <= b.left + 0.5 ||
              b.right <= a.left + 0.5 ||
              a.bottom <= b.top + 0.5 ||
              b.bottom <= a.top + 0.5
            );
            const m = document.querySelector('.main')?.getBoundingClientRect();
            const hiEl = document.querySelector('.home-info');
            const hi = hiEl?.getBoundingClientRect();
            const hp = document.querySelector('.home-posts')?.getBoundingClientRect();
            const imgEl = document.querySelector('.home-info-image img');
            const img = imgEl?.getBoundingClientRect();
            const h1 = document.querySelector('.home-info h1');
            const subEl = document.querySelector('.home-subtitle');
            const subRect = subEl?.getBoundingClientRect();
            const fieldRect = document.querySelector('.home-info .tidal-field-band')?.getBoundingClientRect();
            const range = document.createRange();
            const textNode = [...(h1?.childNodes || [])].find((n) => n.nodeType === Node.TEXT_NODE && n.nodeValue.trim());
            if (textNode) range.selectNodeContents(textNode);
            const nameRect = textNode ? range.getBoundingClientRect() : h1?.getBoundingClientRect();
            const hiStyle = hiEl ? getComputedStyle(hiEl) : null;
            const h1Style = h1 ? getComputedStyle(h1) : null;
            return {
              clientWidth: document.documentElement.clientWidth,
              mainWidth: m?.width || 0,
              mainCenterX: m ? m.left + m.width / 2 : 0,
              homeInfoLeft: hi?.left || 0,
              homeInfoRight: hi?.right || 0,
              homePostsLeft: hp?.left || 0,
              homePostsRight: hp?.right || 0,
              hasHomePosts: Boolean(hp),
              homeInfoTextAlign: hiStyle?.textAlign || '',
              h1TextAlign: h1Style?.textAlign || '',
              h1Justify: h1Style?.justifyContent || '',
              imgComplete: Boolean(imgEl?.complete && imgEl?.naturalWidth > 0),
              imgFetchPriority: imgEl?.getAttribute('fetchpriority') || '',
              imgWidth: img?.width || 0,
              imgHeight: img?.height || 0,
              imgCenterX: img ? img.left + img.width / 2 : 0,
              nameCenterX: nameRect ? nameRect.left + nameRect.width / 2 : 0,
              imgBottom: img?.bottom || 0,
              nameTop: nameRect?.top || 0,
              nameLeft: nameRect?.left || 0,
              subtitleLeft: subRect?.left || 0,
              imgInsideHomeInfo: Boolean(img && hi && img.left >= hi.left - 1 && img.right <= hi.right + 1 && img.top >= hi.top - 1),
              overlapImgName: Boolean(img && nameRect && rectsOverlap(img, nameRect)),
              overlapImgSub: Boolean(img && subRect && rectsOverlap(img, subRect)),
              overlapImgField: Boolean(img && fieldRect && rectsOverlap(img, fieldRect)),
              overlapNameField: Boolean(nameRect && fieldRect && rectsOverlap(nameRect, fieldRect)),
            };
          })()`);

          if (!vp.mobile) {
            assert.ok(homeAlign.mainWidth <= 780, `Expected centered .main width <= 780px, got ${homeAlign.mainWidth}`);
            assert.ok(Math.abs(homeAlign.mainCenterX - homeAlign.clientWidth / 2) <= 4);
            if (homeAlign.hasHomePosts) {
              assert.ok(Math.abs(homeAlign.homeInfoLeft - homeAlign.homePostsLeft) <= 2);
              assert.ok(Math.abs(homeAlign.homeInfoRight - homeAlign.homePostsRight) <= 2);
            }
          }
          assert.ok(
            homeAlign.homeInfoTextAlign === "left" || homeAlign.homeInfoTextAlign === "start",
            `Expected left-aligned .home-info, got ${homeAlign.homeInfoTextAlign}`,
          );
          assert.notEqual(homeAlign.h1TextAlign, "center");
          assert.notEqual(homeAlign.h1Justify, "center");
          assert.ok(homeAlign.nameLeft < homeAlign.mainCenterX, "Expected h1 left edge left of mainCenterX");
          assert.ok(Math.abs(homeAlign.nameLeft - homeAlign.subtitleLeft) <= 4);
          assert.equal(
            Math.abs(homeAlign.imgCenterX - homeAlign.nameCenterX) <= 4 && homeAlign.imgBottom <= homeAlign.nameTop,
            false,
            "Legacy centered stacked avatar+name layout must not return",
          );
          assert.equal(homeAlign.imgComplete, true);
          assert.equal(homeAlign.imgFetchPriority, "high");
          assert.ok(homeAlign.imgWidth >= 48 && homeAlign.imgWidth <= 130, `Unexpected imgWidth: ${homeAlign.imgWidth}`);
          assert.ok(homeAlign.imgHeight >= 48 && homeAlign.imgHeight <= 130, `Unexpected imgHeight: ${homeAlign.imgHeight}`);
          assert.ok(Math.abs(homeAlign.imgWidth - homeAlign.imgHeight) <= 2);
          assert.equal(homeAlign.imgInsideHomeInfo, true);
          assert.equal(homeAlign.overlapImgName, false);
          assert.equal(homeAlign.overlapImgSub, false);
          assert.equal(homeAlign.overlapImgField, false);
          assert.equal(homeAlign.overlapNameField, false);
        }
      } finally {
        await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(origTheme)}`);
      }
    }

    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });

    for (const staticRoute of ["/work/", "/publications/", "/cv/"]) {
      await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}${staticRoute}`);
      const hasMeta = await cdp.eval(`Boolean(document.querySelector('.post-meta'))`);
      assert.equal(hasMeta, false, `Unexpected .post-meta on static portfolio route ${staticRoute}`);
    }

    const redirectAndMissing = await cdp.eval(`(async () => {
      const redirects = {};
      for (const [src, targetSuffix] of [
        ['/about/', '/'],
        ['/contact/', '/'],
        ['/software/', '/work/'],
        ['/archives/', '/posts/'],
      ]) {
        const res = await fetch(src);
        const html = await res.text();
        redirects[src] = { status: res.status, hasRefresh: /http-equiv="?refresh"?/i.test(html), html };
      }
      const searchRes = await fetch('/search/');
      const jsonRes = await fetch('/index.json');
      return { redirects, searchStatus: searchRes.status, jsonStatus: jsonRes.status };
    })()`);
    assert.equal(redirectAndMissing.searchStatus, 404);
    assert.equal(redirectAndMissing.jsonStatus, 404);
    for (const [src, expected] of [
      ["/about/", `${serverObj.baseUrl}/`],
      ["/contact/", `${serverObj.baseUrl}/`],
      ["/software/", `${serverObj.baseUrl}/work/`],
      ["/archives/", `${serverObj.baseUrl}/posts/`],
    ]) {
      const info = redirectAndMissing.redirects[src];
      assert.equal(info.status, 200);
      assert.equal(info.hasRefresh, true, `Expected meta refresh on ${src}`);
      assert.ok(info.html.includes(expected), `Expected ${src} redirect to target ${expected}, got ${info.html}`);
    }

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/cv/`);
    const compactGap = await cdp.eval(`Boolean(document.querySelector('.cv-entry-compact'))`);
    assert.equal(compactGap, true, "Expected .cv-entry-compact on Career Break entry");

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
    const pubLinksClean = await cdp.eval(`(() => {
      const pill = document.querySelector('.pub-year-pill');
      const badge = document.querySelector('.pub-badge-btn');
      return {
        pillBoxShadow: pill ? getComputedStyle(pill).boxShadow : null,
        pillTextDeco: pill ? getComputedStyle(pill).textDecorationLine : null,
        badgeBoxShadow: badge ? getComputedStyle(badge).boxShadow : null,
        badgeTextDeco: badge ? getComputedStyle(badge).textDecorationLine : null,
      };
    })()`);
    assert.equal(pubLinksClean.pillBoxShadow, "none");
    assert.equal(pubLinksClean.pillTextDeco, "none");
    assert.equal(pubLinksClean.badgeBoxShadow, "none");
    assert.equal(pubLinksClean.badgeTextDeco, "none");

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-06-15-neural-surrogates-shallow-water-equations/`);
    const polish = await cdp.eval(`(() => {
      const m = document.querySelector('.main')?.getBoundingClientRect();
      const h1 = document.querySelector('h1.post-title');
      const pc = document.querySelector('.post-content');
      const h2 = document.querySelector('.post-content > h2');
      const proseP = [...document.querySelectorAll('.post-content > p')].find((el) => !el.querySelector('img'));
      const figImg = document.querySelector('.entry-cover img[src*="flowers_banner.png"]');
      const dupInline = document.querySelector('.post-content img[src*="flowers_banner.png"]');
      const h1Style = getComputedStyle(h1);
      const pStyle = getComputedStyle(proseP);
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
        mainWidth: m?.width || 0,
        h1Wrap: h1Style.textWrap,
        pWrap: pStyle.textWrap,
        pWidth: proseP?.getBoundingClientRect().width || 0,
        h2Width: h2?.getBoundingClientRect().width || 0,
        postContentWidth: pc?.getBoundingClientRect().width || 0,
        coverImgComplete: Boolean(figImg?.complete && figImg?.naturalWidth > 0),
        coverImgWidth: figImg?.getBoundingClientRect().width || 0,
        hasDupInline: Boolean(dupInline),
        beforeContent: beforeStyle.content,
        beforeTimeline: beforeStyle.animationTimeline,
        hasViewTransition,
      };
    })()`);
    assert.ok(polish.mainWidth <= 780, `Expected .main <= 780px on post, got ${polish.mainWidth}`);
    assert.equal(polish.h1Wrap, "balance");
    assert.equal(polish.pWrap, "pretty");
    assert.ok(
      Math.abs(polish.pWidth - polish.postContentWidth) <= 4,
      `Expected paragraph width (${polish.pWidth}px) to align with .post-content (${polish.postContentWidth}px)`,
    );
    assert.ok(
      Math.abs(polish.h2Width - polish.postContentWidth) <= 4,
      `Expected h2 width (${polish.h2Width}px) to align with .post-content (${polish.postContentWidth}px)`,
    );
    assert.equal(polish.coverImgComplete, true, "Expected flowers_banner.png cover image to load");
    assert.equal(polish.hasDupInline, false, "Duplicate inline flowers_banner.png must not appear");
    assert.ok(
      Math.abs(polish.coverImgWidth - polish.postContentWidth) <= 4,
      `Expected flowers_banner.png width (${polish.coverImgWidth}px) to match .post-content (${polish.postContentWidth}px)`,
    );
    assert.notEqual(polish.beforeContent, "none");
    assert.ok((polish.beforeTimeline || "").includes("scroll"), `Expected scroll() timeline, got ${polish.beforeTimeline}`);
    assert.equal(polish.hasViewTransition, true);

    const sweFigures = await cdp.eval(`(async () => {
      const pc = document.querySelector('.post-content');
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
        flowersComplete: Boolean(flowersImg?.complete && flowersImg?.naturalWidth > 0),
        flowersWidth: flowersImg?.getBoundingClientRect().width || 0,
        svgComplete: Boolean(svgImg?.complete && svgImg?.naturalWidth > 0),
        svgWidth: svgImg?.getBoundingClientRect().width || 0,
      };
    })()`);
    assert.equal(sweFigures.flowersComplete, true, "Expected flowers_warpfield.png to load");
    assert.ok(
      Math.abs(sweFigures.flowersWidth - sweFigures.postContentWidth) <= 4,
      `Expected flowers_warpfield.png width (${sweFigures.flowersWidth}px) to match .post-content (${sweFigures.postContentWidth}px)`,
    );
    assert.equal(sweFigures.svgComplete, true, "Expected neural_surrogate_swe_rollout.svg to load");
    assert.ok(
      Math.abs(sweFigures.svgWidth - sweFigures.postContentWidth) <= 4,
      `Expected neural_surrogate_swe_rollout.svg width (${sweFigures.svgWidth}px) to match .post-content (${sweFigures.postContentWidth}px)`,
    );

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-06-15-neural-surrogates-shallow-water-equations/`);

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

  it("renders /kinds/note/ and /kinds/talk/ with expected items and navigates to a backfilled talk page", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/kinds/note/`);
    const noteRows = await cdp.eval(
      `[...document.querySelectorAll('.log-rows .log-row')].map((row) => ({
        href: row.querySelector('a.log-row-title-link')?.getAttribute('href') || '',
        hasBadge: Boolean(row.querySelector('.kind-badge')),
        dateText: row.querySelector('time.log-row-date')?.textContent.trim() || '',
        boxShadow: getComputedStyle(row).boxShadow,
        borderRadius: getComputedStyle(row).borderRadius,
      }))`,
    );
    assert.equal(noteRows.length, 1, `Expected 1 note on /kinds/note/, got ${JSON.stringify(noteRows)}`);
    assert.ok(
      noteRows[0].href.endsWith("/posts/2026-06-15-neural-surrogates-shallow-water-equations/"),
      `Unexpected note link: ${noteRows[0].href}`,
    );
    assert.equal(noteRows[0].hasBadge, true);
    assert.match(noteRows[0].dateText, /^\d{4}-\d{2}-\d{2}$/);
    assert.equal(noteRows[0].boxShadow, "none");
    assert.equal(noteRows[0].borderRadius, "0px");

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/kinds/talk/`);
    const talkRows = await cdp.eval(
      `[...document.querySelectorAll('.log-rows .log-row')].map((row) => ({
        href: row.querySelector('a.log-row-title-link')?.getAttribute('href') || '',
        hasBadge: Boolean(row.querySelector('.kind-badge')),
        dateText: row.querySelector('time.log-row-date')?.textContent.trim() || '',
        boxShadow: getComputedStyle(row).boxShadow,
        borderRadius: getComputedStyle(row).borderRadius,
      }))`,
    );
    assert.equal(talkRows.length, 2, `Expected 2 talks on /kinds/talk/, got ${JSON.stringify(talkRows)}`);
    assert.ok(
      talkRows.some((r) => r.href.endsWith("/posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/")),
      `Missing EGU2014 talk link in ${JSON.stringify(talkRows)}`,
    );
    assert.ok(
      talkRows.some((r) => r.href.endsWith("/posts/2013-06-21-ams19-global-modelling-surface-internal-tides/")),
      `Missing AMS 19th talk link in ${JSON.stringify(talkRows)}`,
    );
    for (const r of talkRows) {
      assert.equal(r.hasBadge, true);
      assert.match(r.dateText, /^\d{4}-\d{2}-\d{2}$/);
      assert.equal(r.boxShadow, "none");
      assert.equal(r.borderRadius, "0px");
    }

    cdp.events = [];
    await cdp.eval(`document.querySelector('.log-rows .log-row a.log-row-title-link').click()`);
    await cdp.waitForLoad();
    await new Promise((r) => setTimeout(r, 150));

    const consoleErrors = cdp.events.filter(
      (e) => e.method === "Runtime.consoleAPICalled" && e.params?.type === "error",
    );
    const pageExceptions = cdp.events.filter((e) => e.method === "Runtime.exceptionThrown");
    assert.equal(consoleErrors.length, 0, `Console errors after clicking talk link: ${JSON.stringify(consoleErrors)}`);
    assert.equal(pageExceptions.length, 0, `Page exceptions after clicking talk link: ${JSON.stringify(pageExceptions)}`);

    const talkPageInfo = await cdp.eval(`({
      pathname: window.location.pathname,
      hasBlockquote: Boolean(document.querySelector('.post-content blockquote')),
      h1Text: document.querySelector('h1.post-title')?.textContent.trim() || ''
    })`);
    assert.ok(talkPageInfo.pathname.startsWith("/posts/201"), `Expected talk pathname, got ${talkPageInfo.pathname}`);
    assert.equal(talkPageInfo.hasBlockquote, true, "Expected quoted abstract <blockquote> on talk page");
    assert.ok(talkPageInfo.h1Text.includes("Global modelling of surface and internal tides"));
  });

  it("renders Section 6 verbatim prose across Home, Work, CV, and Publications", async () => {
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/`);
    const homeProse = await cdp.eval(`(() => {
      const norm = (el) => (el?.textContent || '').replace(/\\s+/g, ' ').trim();
      return {
        subtitle: norm(document.querySelector('.home-subtitle')),
        bio: norm(document.querySelector('.home-info .entry-content')),
        focus: norm(document.querySelector('.home-info .current-focus')),
        links: [...document.querySelectorAll('.home-audience-links a')].map((a) => ({
          title: norm(a.querySelector('.home-audience-title')),
          href: a.getAttribute('href') || '',
          desc: norm(a.querySelector('.home-audience-desc')),
        })),
      };
    })()`);
    assert.equal(homeProse.subtitle, "Senior Research Engineer, BSC · Climate models, HPC, ML emulators");
    assert.equal(
      homeProse.bio,
      "I am a Senior Research Engineer at the Barcelona Supercomputing Center. I work on the EC-Earth4 climate model: coupling, performance on MareNostrum 5, and the ensemble workflows behind our decadal predictions for CMIP7. Before BSC, I wrote sea-ice and ocean-tide solvers at MPI-M and the University of Leeds. Climate models have become too expensive to improve, and I think AI tools and automated verification can make that work affordable again.",
    );
    assert.equal(
      homeProse.focus,
      "Current Focus: Preparing EC-Earth4 for CMIP7 on MareNostrum 5, tracer mass conservation in OpenIFS, and coupling neural emulators to EC-Earth4.",
    );
    assert.equal(homeProse.links.length, 3);
    assert.deepEqual(
      homeProse.links.map((l) => [l.title, l.desc]),
      [
        ["Collaborate", "what I work on, the code, and how to reach me."],
        ["Hiring", "CV, career history and PDF downloads."],
        ["Read", "notes, talks and papers."],
      ],
    );
    assert.ok(homeProse.links[0].href.endsWith("/work/"));
    assert.ok(homeProse.links[1].href.endsWith("/cv/"));
    assert.ok(homeProse.links[2].href.endsWith("/posts/"));

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/work/`);
    const workProse = await cdp.eval(`(() => {
      const norm = (el) => (el?.textContent || '').replace(/\\s+/g, ' ').trim();
      const firstP = document.querySelector('.post-content > p');
      const emailLink = firstP?.querySelector('a[href="mailto:vladimir.lapin@bsc.es"]');
      const projects = [...document.querySelectorAll('.post-content > ul:first-of-type > li')].map(norm);
      const software = [...document.querySelectorAll('.software-card')].map((card) => [
        norm(card.querySelector('h3')),
        norm(card.querySelector('.software-desc')),
      ]);
      return {
        intro: norm(firstP),
        hasMailto: emailLink?.textContent.trim() === 'email me',
        projects,
        software,
      };
    })()`);
    assert.equal(
      workProse.intro,
      "Projects I am on now, the public code, and some older simulations. If something here overlaps with your work, email me.",
    );
    assert.equal(workProse.hasMailto, true);
    assert.deepEqual(workProse.projects, [
      "Auto-EC-Earth4 — I co-lead the Autosubmit workflow for 50–100 member decadal ensembles (CMIP7, WMO/DCPP).",
      "EC-Earth4 performance — single precision, load balancing and MPI tuning; coupled runs are 2–3× faster.",
      "Emulators in EC-Earth4 — interfaces to couple neural emulators, and a GNN ocean biogeochemistry emulator with mass-conservation checks.",
      "OpenIFS tracer mass conservation in CY48R1.1.",
    ]);
    assert.deepEqual(workProse.software, [
      [
        "Climate Commons (cvc-commons)",
        "Shared workflow tasks and preprocessing scripts for climate computing at BSC, with schema checks and CI.",
      ],
      [
        "EC-Earth4",
        "The European community Earth system model. I work on OpenIFS integration, OASIS3-MCT coupling and CMIP7 runs.",
      ],
      [
        "Prediction Data Workflow",
        "Preprocessing and interpolation of EN4, ERA5 and ORAS5 data for climate predictions.",
      ],
      [
        "ece4-exp",
        "Manages EC-Earth4 experiment configuration with layered YAML files.",
      ],
      [
        "baro_tides_fd",
        "Global finite-difference solver for barotropic ocean tides (Fortran).",
      ],
      [
        "internal_tides_fd",
        "Global solver for barotropic and internal tides with vertical mode decomposition (Fortran).",
      ],
      [
        "pisces-inidata",
        "Builds PISCES biogeochemistry initial conditions for NEMO and EC-Earth4 from a data catalog.",
      ],
    ]);

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/cv/`);
    const cvTools = await cdp.eval(
      `(document.querySelector('.cv-tools-line')?.textContent || '').replace(/\\s+/g, ' ').trim()`,
    );
    assert.equal(
      cvTools,
      "Tools: Python (xarray, Dask, PyTorch), Fortran (MPI, OpenMP), Bash, Slurm, Autosubmit, CDO, NCO. Models: EC-Earth4, OpenIFS, NEMO/PISCES, OASIS3-MCT, ICON.",
    );

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
    const pubIntro = await cdp.eval(
      `(document.querySelector('.pub-metrics-intro')?.textContent || '').replace(/\\s+/g, ' ').trim()`,
    );
    assert.match(pubIntro, /^\d+ papers · \d+ citations · h-index \d+ \(OpenAlex\)\.$/);
  });

  it("enforces tabular-nums glyph width invariance and clean CV mobile wrapping across routes", async () => {
    const routesAndSelectors = [
      ["/", [".log-row-date"]],
      ["/work/", [".sim-spec-pill", ".pub-card-year"]],
      ["/posts/", [".log-row-date", ".log-kind-pill"]],
      ["/cv/", [".cv-date-badge", ".cv-download-badge"]],
      ["/publications/", [".pub-year-pill", ".pub-card-year", ".pub-year-heading", ".pub-metrics-intro"]],
    ];

    for (const vp of [
      { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false },
      { width: 375, height: 812, deviceScaleFactor: 1, mobile: true },
    ]) {
      await cdp.send("Emulation.setDeviceMetricsOverride", vp);
      for (const [route, selectors] of routesAndSelectors) {
        await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}${route}`);
        const res = await cdp.eval(`((sels) => {
          const out = [];
          for (const sel of sels) {
            const matches = [...document.querySelectorAll(sel)].filter((el) => {
              if (el.closest('details:not([open]) > :not(summary)')) return false;
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            });
            if (matches.length === 0) {
              out.push({ sel, visibleCount: 0, failures: ['no visible elements'] });
              continue;
            }
            const failures = [];
            for (const el of matches.slice(0, 5)) {
              const cs = getComputedStyle(el);
              if (!cs.fontVariantNumeric.includes('tabular-nums')) {
                failures.push('missing tabular-nums: ' + cs.fontVariantNumeric);
              }
              const probe = document.createElement('span');
              probe.style.position = 'fixed';
              probe.style.visibility = 'hidden';
              probe.style.whiteSpace = 'nowrap';
              probe.style.fontFamily = cs.fontFamily;
              probe.style.fontSize = cs.fontSize;
              probe.style.fontWeight = cs.fontWeight;
              probe.style.fontVariantNumeric = cs.fontVariantNumeric;
              probe.style.letterSpacing = cs.letterSpacing;
              probe.textContent = '1111';
              document.body.appendChild(probe);
              const r1 = document.createRange();
              r1.selectNodeContents(probe);
              const w1 = r1.getBoundingClientRect().width;
              probe.textContent = '8888';
              const r8 = document.createRange();
              r8.selectNodeContents(probe);
              const w8 = r8.getBoundingClientRect().width;
              probe.remove();
              if (Math.abs(w1 - w8) > 0.25) {
                failures.push('width delta ' + Math.abs(w1 - w8).toFixed(3));
              }
            }
            out.push({ sel, visibleCount: matches.length, failures });
          }
          return out;
        })(${JSON.stringify(selectors)})`);

        for (const item of res) {
          assert.ok(item.visibleCount > 0, `Expected visible elements for ${item.sel} on ${route}`);
          assert.equal(
            item.failures.length,
            0,
            `tabular-nums check failed for ${item.sel} on ${route} (${vp.width}px): ${JSON.stringify(item.failures)}`,
          );
        }
      }

      if (vp.mobile) {
        await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/cv/`);
        const cvWrap = await cdp.eval(`(() => {
          const rectsOverlap = (a, b) => !(
            a.right <= b.left + 0.5 ||
            b.right <= a.left + 0.5 ||
            a.bottom <= b.top + 0.5 ||
            b.bottom <= a.top + 0.5
          );
          const headers = [...document.querySelectorAll('.cv-entry-header')].filter((h) => !h.closest('details:not([open])'));
          return headers.map((h) => {
            const hr = h.getBoundingClientRect();
            const title = h.querySelector('.cv-entry-title')?.getBoundingClientRect();
            const badge = h.querySelector('.cv-date-badge')?.getBoundingClientRect();
            if (!title || !badge) return { missing: true };
            const overlap = rectsOverlap(title, badge);
            const rightAligned = Math.abs(badge.right - hr.right) <= 2;
            const leftWrapped = Math.abs(badge.left - hr.left) <= 2 && badge.top >= title.bottom - 1;
            return { missing: false, overlap, rightAligned, leftWrapped };
          });
        })()`);
        assert.ok(cvWrap.length > 0, "Expected visible .cv-entry-header elements on /cv/");
        for (const row of cvWrap) {
          assert.equal(row.missing, false);
          assert.equal(row.overlap, false, "CV title and date badge must not overlap on mobile");
          assert.ok(row.rightAligned || row.leftWrapped, `CV date badge alignment failed: ${JSON.stringify(row)}`);
        }
      }
    }
  });

  it("enforces action pill containment, zero overlap, and >= 3.5px gap without clipping across viewports", async () => {
    const routeContainers = [
      ["/", [".entry-kinds"]],
      ["/work/", [".software-tags", ".sim-specs", ".pub-card-actions"]],
      ["/posts/", [".log-kind-filter", ".entry-kinds", ".entry-tags"]],
      ["/cv/", [".cv-nav-bar"]],
      ["/cv/presentations/", [".cv-item-actions"]],
      ["/cv/trainings/", [".cv-skills"]],
      ["/publications/", [".pub-year-nav", ".pub-card-actions"]],
      ["/posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/", [".post-kinds", ".post-tags"]],
      ["/posts/2026-06-15-neural-surrogates-shallow-water-equations/", [".post-kinds", ".post-tags"]],
    ];

    for (const vp of [
      { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false },
      { width: 375, height: 812, deviceScaleFactor: 1, mobile: true },
    ]) {
      await cdp.send("Emulation.setDeviceMetricsOverride", vp);
      for (const [route, containers] of routeContainers) {
        await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}${route}`);
        const audit = await cdp.eval(`((containerSels) => {
          const rectsOverlap = (a, b) => !(
            a.right <= b.left + 0.5 ||
            b.right <= a.left + 0.5 ||
            a.bottom <= b.top + 0.5 ||
            b.bottom <= a.top + 0.5
          );
          for (const deferred of document.querySelectorAll('.pub-year-group:nth-of-type(n+3), .cv-item:nth-of-type(n+6)')) {
            if (!deferred.closest('details:not([open])')) {
              deferred.scrollIntoView({ block: 'center' });
            }
          }
          const report = [];
          for (const sel of containerSels) {
            const boxes = [...document.querySelectorAll(sel)].filter((c) => {
              if (c.closest('details:not([open]) > :not(summary)')) return false;
              const r = c.getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            });
            if (boxes.length === 0) {
              report.push({ sel, boxCount: 0, pillCount: 0, issues: ['0 visible containers'] });
              continue;
            }
            let pillCount = 0;
            const issues = [];
            for (const box of boxes) {
              const items = [...box.querySelectorAll(':scope > a, :scope > button, :scope > span, :scope > li > a, :scope > details > summary')]
                .filter((el) => {
                  const r = el.getBoundingClientRect();
                  return r.width > 0 && r.height > 0;
                });
              pillCount += items.length;
              const rects = items.map((el) => ({ el, r: el.getBoundingClientRect() }));
              for (const { el, r } of rects) {
                if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1) {
                  issues.push('internal scrollWidth clip on ' + el.textContent.trim() + ': ' + el.scrollWidth + '>' + el.clientWidth);
                }
                if (r.left < -0.5 || r.right > window.innerWidth + 0.5) {
                  issues.push('viewport clip on ' + el.textContent.trim() + ': left=' + r.left + ' right=' + r.right + ' vw=' + window.innerWidth);
                }
              }
              for (let i = 0; i < rects.length; i++) {
                for (let j = i + 1; j < rects.length; j++) {
                  const a = rects[i].r;
                  const b = rects[j].r;
                  if (rectsOverlap(a, b)) {
                    issues.push('overlap between "' + rects[i].el.textContent.trim() + '" and "' + rects[j].el.textContent.trim() + '"');
                    continue;
                  }
                  const verticalOverlap = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
                  if (verticalOverlap > 2) {
                    const hGap = Math.max(a.left - b.right, b.left - a.right);
                    if (hGap < 3.5) {
                      issues.push('tight gap ' + hGap.toFixed(2) + 'px between "' + rects[i].el.textContent.trim() + '" and "' + rects[j].el.textContent.trim() + '"');
                    }
                  }
                }
              }
            }
            report.push({ sel, boxCount: boxes.length, pillCount, issues });
          }
          return report;
        })(${JSON.stringify(containers)})`);

        for (const entry of audit) {
          assert.ok(entry.boxCount > 0 && entry.pillCount > 0, `Vacuous pill check for ${entry.sel} on ${route}`);
          assert.equal(
            entry.issues.length,
            0,
            `Pill geometry issues on ${route} (${vp.width}px) for ${entry.sel}: ${JSON.stringify(entry.issues)}`,
          );
        }
      }
    }
  });

  it("renders CV PDFs above the fold, serves valid PDF bytes, and expands details for print media", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/cv/`);

    const cvAboveFold = await cdp.eval(`(() => {
      const btns = [...document.querySelectorAll('.cv-download-btn')];
      return btns.map((b) => {
        const r = b.getBoundingClientRect();
        return {
          href: b.getAttribute('href'),
          text: b.textContent.replace(/\\s+/g, ' ').trim(),
          bottom: r.bottom,
          height: r.height,
        };
      });
    })()`);
    assert.equal(cvAboveFold.length, 2);
    for (const btn of cvAboveFold) {
      assert.ok(btn.bottom <= 800, `CV button ${btn.href} extends below fold: ${btn.bottom}`);
      assert.ok(btn.height >= 44, `CV button ${btn.href} height < 44px: ${btn.height}`);
    }
    const industryBtn = cvAboveFold.find((b) => b.href === "/downloads/vladimir-lapin-cv-industry.pdf");
    assert.ok(industryBtn && industryBtn.text.includes("2-page"), `Industry button missing 2-page label: ${JSON.stringify(industryBtn)}`);

    for (const pdfPath of [
      "/downloads/vladimir-lapin-cv-industry.pdf",
      "/downloads/vladimir-lapin-cv-research-full.pdf",
      "/downloads/phd-thesis-vlapin.pdf",
      "/downloads/msc-thesis-vlapin.pdf",
    ]) {
      const res = await fetch(`${serverObj.baseUrl}${pdfPath}`);
      assert.equal(res.status, 200, `Expected 200 for ${pdfPath}, got ${res.status}`);
      assert.ok((res.headers.get("content-type") || "").includes("application/pdf"));
      const buf = Buffer.from(await res.arrayBuffer());
      assert.equal(buf.subarray(0, 5).toString("ascii"), "%PDF-", `Invalid PDF magic bytes for ${pdfPath}`);
    }

    try {
      await cdp.eval(`window.dispatchEvent(new Event('beforeprint'))`);
      await cdp.send("Emulation.setEmulatedMedia", { media: "print" });
      await new Promise((r) => setTimeout(r, 150));
      const cvPrint = await cdp.eval(`(() => ({
        allOpen: [...document.querySelectorAll('details.cv-section-details')].every((d) => d.open === true),
        cvItemVisibility: getComputedStyle(document.querySelector('.cv-item:nth-of-type(n+6)')).contentVisibility,
        barDisplay: getComputedStyle(document.querySelector('.cv-download-bar')).display,
        navDisplay: getComputedStyle(document.querySelector('.cv-nav-bar')).display,
      }))()`);
      assert.equal(cvPrint.allOpen, true, "beforeprint must open all details.cv-section-details");
      assert.equal(cvPrint.cvItemVisibility, "visible", "@media print must reset .cv-item content-visibility");
      assert.equal(cvPrint.barDisplay, "none");
      assert.equal(cvPrint.navDisplay, "none");
    } finally {
      await cdp.send("Emulation.setEmulatedMedia", { media: "screen" });
      await cdp.eval(`window.dispatchEvent(new Event('afterprint'))`);
    }

    const restoredClosed = await cdp.eval(
      `[...document.querySelectorAll('details.cv-section-details')].every((d) => d.open === false)`,
    );
    assert.equal(restoredClosed, true, "afterprint must restore previously collapsed details.cv-section-details");

    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
    try {
      await cdp.send("Emulation.setEmulatedMedia", { media: "print" });
      await new Promise((r) => setTimeout(r, 150));
      const pubPrint = await cdp.eval(`(() => ({
        groupVisibility: getComputedStyle(document.querySelector('.pub-year-group:nth-of-type(n+3)')).contentVisibility,
        filterDisplay: getComputedStyle(document.querySelector('.pub-filter-container')).display,
        yearNavDisplay: getComputedStyle(document.querySelector('.pub-year-nav')).display,
      }))()`);
      assert.equal(pubPrint.groupVisibility, "visible", "@media print must reset .pub-year-group content-visibility");
      assert.equal(pubPrint.filterDisplay, "none");
      assert.equal(pubPrint.yearNavDisplay, "none");
    } finally {
      await cdp.send("Emulation.setEmulatedMedia", { media: "screen" });
    }
  });

  it("contains zero Nick Higham WordPress patterns across all built routes", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    const routes = [
      "/",
      "/work/",
      "/publications/",
      "/cv/",
      "/cv/presentations/",
      "/cv/trainings/",
      "/posts/",
      "/kinds/",
      "/kinds/note/",
      "/kinds/talk/",
      "/tags/",
      "/tags/hpc/",
      "/categories/",
      "/404.html",
      "/posts/2026-06-15-neural-surrogates-shallow-water-equations/",
      "/posts/2014-04-28-egu2014-global-modelling-surface-internal-tides/",
      "/posts/2013-06-21-ams19-global-modelling-surface-internal-tides/",
    ];
    for (const route of routes) {
      await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}${route}`);
      const audit = await cdp.eval(`(() => {
        const main = document.querySelector('main.main');
        const parentCols = main?.parentElement ? getComputedStyle(main.parentElement).gridTemplateColumns : '';
        const inputs = [...document.querySelectorAll('input')].map((i) => ({ id: i.id, type: i.type }));
        const hasWhatIs = [...document.querySelectorAll('a')].some((a) => /\\bWhat Is\\b/.test(a.textContent));
        return {
          forbiddenNodes: document.querySelectorAll('aside, #secondary, .widget-area, .sidebar, .widget_recent_entries, .widget_archive, .widget_categories, input[type="email"]').length,
          parentCols,
          inputs,
          hasMathJax: typeof window.MathJax !== 'undefined',
          hasWhatIs,
        };
      })()`);
      assert.equal(audit.forbiddenNodes, 0, `Forbidden WP/sidebar widget found on ${route}`);
      assert.ok(!audit.parentCols.includes(" "), `Multi-column sidebar wrapper found on ${route}: ${audit.parentCols}`);
      assert.equal(audit.hasMathJax, false, `Unexpected MathJax on ${route}`);
      assert.equal(audit.hasWhatIs, false, `Unexpected 'What Is' series link on ${route}`);
      for (const inp of audit.inputs) {
        assert.ok(route === "/publications/" && inp.id === "pubFilterInput", `Unexpected input on ${route}: ${JSON.stringify(inp)}`);
      }
    }
  });

  it("scrolls long KaTeX equations and --buildDrafts wide tables locally on 375x812 mobile", async () => {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 375,
      height: 812,
      deviceScaleFactor: 1,
      mobile: true,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/posts/2026-06-15-neural-surrogates-shallow-water-equations/`);
    const katexScroll = await cdp.eval(`(() => {
      const blocks = [...document.querySelectorAll('.katex-display')];
      return {
        count: blocks.length,
        allOverflowAuto: blocks.every((b) => getComputedStyle(b).overflowX === 'auto'),
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      };
    })()`);
    assert.ok(katexScroll.count > 0, "Expected .katex-display blocks on published math note");
    assert.equal(katexScroll.allOverflowAuto, true);
    assert.ok(katexScroll.scrollWidth <= 375, `KaTeX note overflowed 375px: ${katexScroll.scrollWidth}`);

    const draftsDir = fs.mkdtempSync(path.join(REPO_ROOT, "_tmp_hugo_drafts_"));
    let draftServer;
    try {
      draftServer = await startStaticServer(draftsDir);
      await runHugoBuild(draftsDir, draftServer.baseUrl, ["--buildDrafts"]);
      await navigateAndCheckErrors(
        cdp,
        `${draftServer.baseUrl}/posts/2026-09-24-openifs-mass-conservation-stochastic-rounding/`,
      );
      const tableCheck = await cdp.eval(`(() => {
        const tables = [...document.querySelectorAll('.post-content table')];
        const td = tables[0]?.querySelector('td');
        let tdTabular = false;
        let tdDelta = 999;
        if (td) {
          const cs = getComputedStyle(td);
          tdTabular = cs.fontVariantNumeric.includes('tabular-nums');
          const probe = document.createElement('span');
          probe.style.position = 'fixed';
          probe.style.visibility = 'hidden';
          probe.style.whiteSpace = 'nowrap';
          probe.style.fontFamily = cs.fontFamily;
          probe.style.fontSize = cs.fontSize;
          probe.style.fontWeight = cs.fontWeight;
          probe.style.fontVariantNumeric = cs.fontVariantNumeric;
          probe.textContent = '1111';
          document.body.appendChild(probe);
          const r1 = document.createRange();
          r1.selectNodeContents(probe);
          const w1 = r1.getBoundingClientRect().width;
          probe.textContent = '8888';
          const r8 = document.createRange();
          r8.selectNodeContents(probe);
          const w8 = r8.getBoundingClientRect().width;
          probe.remove();
          tdDelta = Math.abs(w1 - w8);
        }
        return {
          tableCount: tables.length,
          allBlockAuto: tables.every((t) => {
            const cs = getComputedStyle(t);
            return cs.display === 'block' && cs.overflowX === 'auto';
          }),
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          tdTabular,
          tdDelta,
        };
      })()`);
      assert.ok(tableCheck.tableCount > 0, "Expected wide <table> in drafted OpenIFS post");
      assert.equal(tableCheck.allBlockAuto, true);
      assert.ok(tableCheck.scrollWidth <= 375, `Drafted table overflowed 375px: ${tableCheck.scrollWidth}`);
      assert.equal(tableCheck.tdTabular, true);
      assert.ok(tableCheck.tdDelta <= 0.25, `table td glyph width delta ${tableCheck.tdDelta} > 0.25px`);
    } finally {
      try { draftServer?.server?.close(); } catch {}
      fs.rmSync(draftsDir, { recursive: true, force: true });
    }
  });

  it("lands #year-* pill jumps on target heading without CLS, trims ?q=%20%20, provides >=44px mobile #pubFilterClear, unifies BibTeX pre/code, and provides skip-to-content link", async () => {
    // 1. Skip-to-content link on Home (desktop) with zero CLS
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 800,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/`);
    await cdp.eval(`(() => {
      window.__skipCls = 0;
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) window.__skipCls += entry.value;
        }
      }).observe({ type: 'layout-shift', buffered: true });
    })()`);
    await cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
    await cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
    const skipFocus = await cdp.eval(`(() => {
      const el = document.activeElement;
      const r = el?.getBoundingClientRect();
      return {
        isSkipLink: el?.classList.contains('skip-link') || false,
        href: el?.getAttribute('href'),
        visible: Boolean(r && r.width >= 40 && r.height >= 20 && r.top >= 0 && r.left >= 0)
      };
    })()`);
    assert.equal(skipFocus.isSkipLink, true, "First Tab stop on page must be .skip-link");
    assert.equal(skipFocus.href, "#main-content");
    assert.equal(skipFocus.visible, true, ".skip-link must become visible on keyboard focus");

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
    await new Promise((r) => setTimeout(r, 100));
    const afterSkip = await cdp.eval(`({
      activeId: document.activeElement?.id,
      cls: window.__skipCls
    })`);
    assert.equal(afterSkip.activeId, "main-content", "Activating .skip-link must move focus to #main-content");
    assert.equal(afterSkip.cls, 0, "Focusing/activating .skip-link must not cause CLS");

    // 2. /publications/ #year-2011 and #year-Other pill click accuracy under content-visibility: auto
    for (const hash of ["#year-2011", "#year-Other"]) {
      await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
      const cvBefore = await cdp.eval(`getComputedStyle(document.querySelector('.pub-year-group:nth-of-type(n+3)')).contentVisibility`);
      assert.equal(cvBefore, "auto");
      await cdp.eval(`(() => {
        window.__yearCls = 0;
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) window.__yearCls += entry.value;
          }
        }).observe({ type: 'layout-shift', buffered: true });
        document.querySelector('.pub-year-pill[href="${hash}"]').focus();
      })()`);
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
      await new Promise((r) => setTimeout(r, 250));
      const jumpRes = await cdp.eval(`(() => {
        const el = document.querySelector('${hash}');
        return {
          top: el ? el.getBoundingClientRect().top : 99999,
          hash: window.location.hash,
          cls: window.__yearCls
        };
      })()`);
      assert.ok(
        jumpRes.top >= 0 && jumpRes.top <= 100,
        `Clicking .pub-year-pill[href="${hash}"] landed off-target: top=${jumpRes.top}px`,
      );
      assert.equal(jumpRes.hash, hash);
      assert.equal(jumpRes.cls, 0, `Jumping to ${hash} caused CLS=${jumpRes.cls}`);
    }

    // 3. .pub-bibtex-block <pre> and <code> unified background & >= 4.5:1 contrast in light and dark modes
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/`);
    await cdp.eval(`document.querySelector('.pub-bibtex-details').open = true`);
    const origTheme = await cdp.eval(`document.documentElement.dataset.theme`);
    try {
      for (const theme of ["light", "dark"]) {
        await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(theme)}`);
        await new Promise((r) => setTimeout(r, 200));
        const bibCheck = await cdp.eval(`(() => {
          const pre = document.querySelector('.pub-bibtex-block pre');
          const code = document.querySelector('.pub-bibtex-block pre code');
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
            for (let i = layers.length - 1; i >= 0; i--) bg = over(layers[i], bg);
            return bg;
          };
          const preBg = effectiveBg(pre);
          const codeBg = effectiveBg(code);
          const codeFg = over(parseRgba(getComputedStyle(code).color), codeBg);
          const l1 = lum(codeFg);
          const l2 = lum(codeBg);
          const contrast = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
          return {
            preBg: preBg.slice(0, 3),
            codeBg: codeBg.slice(0, 3),
            contrast
          };
        })()`);
        assert.deepEqual(
          bibCheck.codeBg,
          bibCheck.preBg,
          `BibTeX pre/code background mismatch in ${theme}: pre=${JSON.stringify(bibCheck.preBg)} code=${JSON.stringify(bibCheck.codeBg)}`,
        );
        assert.ok(bibCheck.contrast >= 4.5, `BibTeX code contrast in ${theme} is ${bibCheck.contrast.toFixed(2)}:1 < 4.5:1`);
      }
    } finally {
      await cdp.eval(`document.documentElement.dataset.theme = ${JSON.stringify(origTheme)}`);
    }

    // 4. ?q=%20%20 whitespace trimming & mobile #pubFilterClear >= 44x44px touch target
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/?q=%20%20`);
    const wsState = await cdp.eval(`(() => {
      const inp = document.getElementById('pubFilterInput');
      const clr = document.getElementById('pubFilterClear');
      const total = document.querySelectorAll('.pub-card').length;
      const visible = [...document.querySelectorAll('.pub-card')].filter((c) => c.style.display !== 'none').length;
      return {
        value: inp?.value,
        clearDisplay: clr ? getComputedStyle(clr).display : null,
        total,
        visible
      };
    })()`);
    assert.equal(wsState.value, "", "?q=%20%20 must not leave whitespace in #pubFilterInput");
    assert.equal(wsState.clearDisplay, "none");
    assert.equal(wsState.visible, wsState.total);

    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 375,
      height: 812,
      deviceScaleFactor: 1,
      mobile: true,
    });
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/publications/?q=ocean`);
    const clearBox = await cdp.eval(`(() => {
      const r = document.getElementById('pubFilterClear')?.getBoundingClientRect();
      return r ? { width: r.width, height: r.height } : null;
    })()`);
    assert.ok(
      clearBox && clearBox.width >= 44 && clearBox.height >= 44,
      `Mobile #pubFilterClear touch target too small: ${JSON.stringify(clearBox)}`,
    );

    // 5. /404.html renders cleanly at root without post-meta or empty post-tags
    await navigateAndCheckErrors(cdp, `${serverObj.baseUrl}/404.html`);
    const notFoundState = await cdp.eval(`({
      h1: document.querySelector('h1')?.textContent.trim(),
      hasPostMeta: Boolean(document.querySelector('.post-meta')),
      hasEmptyPostTags: Boolean(document.querySelector('footer.post-footer ul.post-tags')),
      hasHomeLink: [...document.querySelectorAll('main a[href]')].some((a) => a.getAttribute('href') === '/' || a.getAttribute('href')?.endsWith('/'))
    })`);
    assert.ok(notFoundState.h1 && notFoundState.h1.includes("404"), `Unexpected /404.html h1: ${notFoundState.h1}`);
    assert.equal(notFoundState.hasPostMeta, false);
    assert.equal(notFoundState.hasEmptyPostTags, false);
    assert.equal(notFoundState.hasHomeLink, true);
  });
});
