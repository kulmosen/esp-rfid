"use strict";

const assert = require("node:assert/strict");
const net = require("node:net");
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

async function waitForPageText(page, selector, expectedText, timeoutMs = 5000) {
  await page.waitForFunction(
    ([resolvedSelector, resolvedText]) => {
      const element = document.querySelector(resolvedSelector);
      return !!element && element.innerText.includes(resolvedText);
    },
    [selector, expectedText],
    { timeout: timeoutMs }
  );
}

async function openContent(page, contentSelector, readySelector) {
  await page.evaluate((selector) => {
    getContent(selector);
  }, contentSelector);
  await page.waitForSelector(readySelector, { state: "visible" });
}

async function loginToSimulator(page, pageUrl, expectedHostname) {
  await page.goto(pageUrl, {
    waitUntil: "networkidle"
  });

  await page.fill("#password", "neo");
  await page.click("text=Login");
  await page.waitForTimeout(1500);

  await page.waitForSelector("#sidebar", { state: "visible" });
  await waitForCondition(async () => {
    return page.evaluate((hostname) => {
      return window.wsConnectionPresent === true
        && window.config
        && window.config.general
        && window.config.general.hostnm === hostname;
    }, expectedHostname);
  });
}

function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();

    probe.on("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address();
      const port = typeof address === "object" && address ? address.port : 0;
      probe.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(port);
      });
    });
  });
}

async function main() {
  const port = await findAvailablePort();
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
    const wsOverride = encodeURIComponent(`ws://127.0.0.1:${port}/ws`);
    const pageUrl = `http://127.0.0.1:${port}/?ws=${wsOverride}`;
    await loginToSimulator(page, pageUrl, "esp-rfid-sim");

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
    await waitForCondition(() => simulator.getState().config.general.hostnm === "sim-door-alpha", 6000);
    await loginToSimulator(page, pageUrl, "sim-door-alpha");

    await openContent(page, "#userscontent", "#ajaxcontent #usersbanner");
    await waitForPageText(page, "#ajaxcontent #usertable", "Maria Cohen", 6000);

    const newUser = {
      uid: "cafefeed",
      username: "Sim Door Test",
      pincode: "4242",
      validsince: "2026-01-01",
      validuntil: "2036-01-01"
    };

    simulator.simulatePICCScan({
      uid: newUser.uid,
      known: 0,
      type: "mifare"
    });

    await page.waitForFunction(() => {
      const modal = document.querySelector("#ajaxcontent #editor-modal");
      return !!modal && modal.classList.contains("in");
    });
    await page.waitForFunction((uid) => {
      const uidField = document.querySelector("#ajaxcontent #editor-modal #uid");
      const usernameField = document.querySelector("#ajaxcontent #editor-modal #username");
      return uidField && uidField.value === uid && usernameField && usernameField.value === "";
    }, newUser.uid);

    await page.fill("#ajaxcontent #editor-modal #pincode", newUser.pincode);
    await page.fill("#ajaxcontent #editor-modal #username", newUser.username);
    await page.fill("#ajaxcontent #editor-modal #validsince", newUser.validsince);
    await page.fill("#ajaxcontent #editor-modal #validuntil", newUser.validuntil);
    await page.click("#ajaxcontent #editor-modal button[type='submit']");

    await waitForCondition(() => {
      return simulator.getState().users.some((user) => user.uid === newUser.uid && user.username === newUser.username);
    }, 6000);
    await waitForPageText(page, "#ajaxcontent #usertable", newUser.username, 6000);

    const eventEntriesAfterSave = simulator.getState().files["/eventlog.json"].entries;
    assert.ok(eventEntriesAfterSave.some((entry) => entry.desc === "User updated" && entry.data === newUser.uid));

    simulator.simulatePICCScan({
      uid: newUser.uid,
      type: "mifare"
    });

    await waitForCondition(() => {
      const latestEntries = simulator.getState().files["/latestlog.json"].entries;
      return latestEntries.some((entry) => entry.uid === newUser.uid && entry.username === newUser.username && entry.access === 1);
    }, 6000);

    await page.evaluate(() => {
      $("#latestlog").click();
    });
    await page.waitForSelector("#ajaxcontent #latestlogtable", { state: "visible" });
    await waitForPageText(page, "#ajaxcontent #latestlogtable", newUser.username, 6000);
    await waitForPageText(page, "#ajaxcontent #latestlogtable", "Granted", 6000);

    await page.evaluate(() => {
      $("#eventlog").click();
    });
    await page.waitForSelector("#ajaxcontent #eventtable", { state: "visible" });
    await waitForPageText(page, "#ajaxcontent #eventtable", "User updated", 6000);
    await waitForPageText(page, "#ajaxcontent #eventtable", "Simulated RFID tag scanned", 6000);
    await waitForPageText(page, "#ajaxcontent #eventtable", newUser.uid, 6000);

    const state = simulator.getState();
    assert.equal(state.config.general.hostnm, "sim-door-alpha");
    assert.ok(state.users.some((user) => user.uid === newUser.uid && user.username === newUser.username));
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
