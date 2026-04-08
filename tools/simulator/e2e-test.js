"use strict";

const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const { createSimulator } = require("./server");

async function waitForCondition(predicate, timeoutMs = 5000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await predicate()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Timed out waiting for condition");
}

async function main() {
  const port = 8080;
  const simulator = createSimulator({
    host: "127.0.0.1",
    port
  });

  await simulator.start();

  const browser = await chromium.launch({
    headless: true
  });
  const page = await browser.newPage();
  const dialogs = [];

  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.accept();
  });

  try {
    await page.goto(`http://127.0.0.1:${port}`, {
      waitUntil: "networkidle"
    });

    await page.fill("#password", "neo");
    await page.click("text=Login");
    await page.waitForTimeout(1500);

    await page.waitForSelector("#sidebar", { state: "visible" });
    await waitForCondition(async () => {
      return page.evaluate(() => {
        return window.wsConnectionPresent === true
          && window.config
          && window.config.general
          && window.config.general.hostnm === "esp-rfid-sim";
      });
    });

    await page.evaluate(() => {
      sendWebsocket(JSON.stringify({
        command: "configfile",
        network: {},
        hardware: {},
        general: {}
      }));
    });
    await page.waitForTimeout(500);

    await waitForCondition(async () => dialogs.length > 0);
    assert.match(dialogs[0], /Missing required config field|Missing required config section/);

    await page.evaluate(() => {
      getContent("#generalcontent");
    });
    await page.waitForSelector("#ajaxcontent #hostname", { state: "visible" });
    await page.fill("#ajaxcontent #hostname", "sim-door-alpha");
    await page.evaluate(() => {
      savegeneral();
    });
    await page.evaluate(() => {
      commit();
    });
    await waitForCondition(async () => {
      const response = await fetch(`http://127.0.0.1:${port}/api/state`);
      const state = await response.json();
      return state.hostname === "sim-door-alpha";
    }, 6000);

    const state = await (await fetch(`http://127.0.0.1:${port}/api/state`)).json();

    assert.equal(state.hostname, "sim-door-alpha");
    console.log("[ OK ] Simulator browser e2e test passed");
  } finally {
    await page.close();
    await browser.close();
    await simulator.stop();
  }
}

main().catch((error) => {
  console.error("[ ERRO ] Simulator browser e2e test failed");
  console.error(error);
  process.exitCode = 1;
});
