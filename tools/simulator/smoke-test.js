"use strict";

const assert = require("node:assert/strict");
const { setTimeout: delay } = require("node:timers/promises");
const WebSocket = require("ws");

const { createSimulator } = require("./server");

function waitForMessage(ws, predicate, timeoutMs = 3000) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      ws.removeListener("message", onMessage);
      reject(new Error("Timed out waiting for websocket message"));
    }, timeoutMs);

    function onMessage(rawData) {
      const message = JSON.parse(rawData.toString());
      if (predicate(message)) {
        clearTimeout(timeout);
        ws.removeListener("message", onMessage);
        resolve(message);
      }
    }

    ws.on("message", onMessage);
  });
}

async function main() {
  const simulator = createSimulator({
    host: "127.0.0.1",
    port: 18080
  });

  await simulator.start();

  try {
    const health = await fetch("http://127.0.0.1:18080/healthz");
    assert.equal(health.status, 200);
    assert.equal((await health.json()).ok, true);

    const unauthorized = await fetch("http://127.0.0.1:18080/login");
    assert.equal(unauthorized.status, 401);

    const authorized = await fetch("http://127.0.0.1:18080/login", {
      headers: {
        Authorization: `Basic ${Buffer.from("admin:admin").toString("base64")}`
      }
    });
    assert.equal(authorized.status, 200);

    const index = await fetch("http://127.0.0.1:18080/");
    const indexBody = await index.text();
    assert.match(indexBody, /ESP-RFID/i);

    const requiredCss = await fetch("http://127.0.0.1:18080/css/required.css");
    assert.equal(requiredCss.status, 200);
    assert.match(await requiredCss.text(), /#sidebar|bootstrap/i);

    const requiredJs = await fetch("http://127.0.0.1:18080/js/required.js");
    assert.equal(requiredJs.status, 200);
    assert.match(await requiredJs.text(), /jQuery|FooTable/);

    const font = await fetch("http://127.0.0.1:18080/fonts/glyphicons-halflings-regular.woff");
    assert.equal(font.status, 200);
    assert.ok((await font.arrayBuffer()).byteLength > 0);

    const ws = new WebSocket("ws://127.0.0.1:18080/ws");
    await new Promise((resolve, reject) => {
      ws.once("open", resolve);
      ws.once("error", reject);
    });

    ws.send(JSON.stringify({ command: "status" }));
    const status = await waitForMessage(ws, (message) => message.command === "status");
    assert.equal(status.hostname, "esp-rfid-sim");

    ws.send(JSON.stringify({ command: "getconf" }));
    const config = await waitForMessage(ws, (message) => message.command === "configfile");
    assert.equal(config.general.hostnm, "esp-rfid-sim");

    ws.send(JSON.stringify({ command: "userlist", page: 1 }));
    const userList = await waitForMessage(ws, (message) => message.command === "userlist");
    assert.ok(Array.isArray(userList.list));
    assert.ok(userList.list.length >= 1);

    const scanMessagePromise = waitForMessage(ws, (message) => message.command === "piccscan" && message.uid === "feedbeef");
    const scanResponse = await fetch("http://127.0.0.1:18080/api/simulate/piccscan", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        uid: "feedbeef",
        known: 0,
        type: "mifare"
      })
    });

    assert.equal(scanResponse.status, 200);
    const scanPayload = await scanMessagePromise;
    assert.equal(scanPayload.known, 0);

    ws.send(JSON.stringify({
      command: "getlatestlog",
      page: 1,
      filename: "/latestlog.json"
    }));
    const latestLog = await waitForMessage(ws, (message) => message.command === "latestlist");
    assert.ok(latestLog.list.some((entry) => entry.includes("feedbeef")));

    ws.close();
    await delay(50);
    console.log("[ OK ] Simulator smoke test passed");
  } finally {
    await simulator.stop();
  }
}

main().catch((error) => {
  console.error("[ ERRO ] Simulator smoke test failed");
  console.error(error);
  process.exitCode = 1;
});
