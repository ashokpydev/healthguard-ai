import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";

const chromePath = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const remotePort = 9223;
const outputPath = path.resolve("outputs", "doctor-patient-problem.png");
const doctorUser = {
  id: 12,
  name: "Doctor Monitor",
  email: "doctor.monitor@healthguard.local",
  role: "doctor",
  demo_token: "demo-12-3wmGGIjxegfZckriMqyXE0EP",
};

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getJson(url, attempts = 40) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return response.json();
      }
    } catch (error) {
      lastError = error;
    }
    await delay(250);
  }
  throw lastError || new Error(`Unable to fetch ${url}`);
}

function createCdpClient(webSocketUrl) {
  const socket = new WebSocket(webSocketUrl);
  let nextId = 1;
  const pending = new Map();
  const listeners = new Map();

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) {
        reject(new Error(JSON.stringify(message.error)));
      } else {
        resolve(message.result || {});
      }
      return;
    }
    const callbacks = listeners.get(message.method) || [];
    callbacks.forEach((callback) => callback(message.params || {}));
  });

  return {
    ready: new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    }),
    send(method, params = {}) {
      const id = nextId;
      nextId += 1;
      socket.send(JSON.stringify({ id, method, params }));
      return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    },
    once(method) {
      return new Promise((resolve) => {
        const callbacks = listeners.get(method) || [];
        callbacks.push(resolve);
        listeners.set(method, callbacks);
      });
    },
    close() {
      socket.close();
    },
  };
}

async function main() {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const profileDir = path.resolve("outputs", "doctor-monitor-chrome-profile");
  await fs.mkdir(profileDir, { recursive: true });

  const chrome = spawn(chromePath, [
    "--headless=new",
    "--no-sandbox",
    `--remote-debugging-port=${remotePort}`,
    `--user-data-dir=${profileDir}`,
    "--disable-gpu",
    "--disable-crash-reporter",
    "--disable-features=Crashpad",
    "--no-first-run",
    "--window-size=1440,1100",
    "about:blank",
  ], { stdio: "ignore" });

  try {
    await getJson(`http://127.0.0.1:${remotePort}/json/version`);
    const targetResponse = await fetch(`http://127.0.0.1:${remotePort}/json/new?about:blank`, { method: "PUT" });
    if (!targetResponse.ok) {
      throw new Error(`Unable to create Chrome target: ${targetResponse.status}`);
    }
    const target = await targetResponse.json();
    const cdp = createCdpClient(target.webSocketDebuggerUrl);
    await cdp.ready;
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    let loadEvent = cdp.once("Page.loadEventFired");
    await cdp.send("Page.navigate", { url: "http://127.0.0.1:8001" });
    await loadEvent;

    await cdp.send("Runtime.evaluate", {
      expression: `
        localStorage.setItem("healthguardUser", ${JSON.stringify(JSON.stringify(doctorUser))});
        localStorage.setItem("healthguardTourSeen", "true");
      `,
    });

    loadEvent = cdp.once("Page.loadEventFired");
    await cdp.send("Page.navigate", { url: "http://127.0.0.1:8001" });
    await loadEvent;
    await delay(800);

    await cdp.send("Runtime.evaluate", {
      expression: `
        document.querySelector('button[data-scroll-target="role-panel"]')?.click();
        document.querySelector('#load-role-data')?.click();
      `,
    });

    for (let index = 0; index < 40; index += 1) {
      const result = await cdp.send("Runtime.evaluate", {
        expression: "document.querySelector('#role-output')?.textContent.includes('Patient problem')",
        returnByValue: true,
      });
      if (result.result?.value) {
        break;
      }
      await delay(250);
    }

    await cdp.send("Runtime.evaluate", {
      expression: "document.querySelector('#role-panel')?.scrollIntoView({ block: 'start' })",
    });
    await delay(700);

    const screenshot = await cdp.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: false,
    });
    await fs.writeFile(outputPath, Buffer.from(screenshot.data, "base64"));
    cdp.close();
  } finally {
    chrome.kill();
  }
  console.log(outputPath);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
