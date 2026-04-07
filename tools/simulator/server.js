"use strict";

const http = require("node:http");
const path = require("node:path");
const fs = require("node:fs/promises");
const { Buffer } = require("node:buffer");
const { WebSocketServer } = require("ws");

const { createDefaultState } = require("./default-state");

const DEFAULT_HOST = process.env.ESP_RFID_SIM_HOST || "127.0.0.1";
const DEFAULT_PORT = parseInt(process.env.ESP_RFID_SIM_PORT || "8080", 10);
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const WEB_ROOT = path.join(REPO_ROOT, "src", "websrc");
const THIRD_PARTY_ROOT = path.join(WEB_ROOT, "3rdparty");
const PAGE_SIZE = 10;
const MAX_BODY_SIZE = 1024 * 1024;

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".htm": "text/html; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".woff": "font/woff"
};

function unixNowWithOffset(state) {
  return Math.floor((Date.now() + state.timeOffsetMs) / 1000);
}

function formatUptime(seconds) {
  const hours = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  const secs = String(seconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${secs}`;
}

function fileEntriesSize(entries) {
  return entries.reduce((total, entry) => total + Buffer.byteLength(`${JSON.stringify(entry)}\n`), 0);
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function asInteger(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

function parseJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let bodySize = 0;

    req.on("data", (chunk) => {
      bodySize += chunk.length;
      if (bodySize > MAX_BODY_SIZE) {
        reject(new Error("Request body too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });

    req.on("end", () => {
      if (chunks.length === 0) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString("utf8")));
      } catch (error) {
        reject(new Error("Invalid JSON body"));
      }
    });

    req.on("error", reject);
  });
}

function parseBasicAuth(headerValue) {
  if (!headerValue || !headerValue.startsWith("Basic ")) {
    return null;
  }

  try {
    const decoded = Buffer.from(headerValue.slice(6), "base64").toString("utf8");
    const separator = decoded.indexOf(":");
    if (separator === -1) {
      return null;
    }
    return {
      username: decoded.slice(0, separator),
      password: decoded.slice(separator + 1)
    };
  } catch (error) {
    return null;
  }
}

function defaultHeaders(extraHeaders) {
  return Object.assign({
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-store"
  }, extraHeaders || {});
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload, null, 2);
  res.writeHead(statusCode, defaultHeaders({
    "Content-Length": Buffer.byteLength(body),
    "Content-Type": "application/json; charset=utf-8"
  }));
  res.end(body);
}

async function readFilesInOrder(filePaths) {
  const contents = await Promise.all(filePaths.map((filePath) => fs.readFile(filePath, "utf8")));
  return contents.join("\n");
}

async function resolveAssetAlias(requestedPath) {
  if (requestedPath === "/css/required.css") {
    return {
      absolutePath: null,
      body: await readFilesInOrder([
        path.join(THIRD_PARTY_ROOT, "css", "bootstrap-3.3.7.min.css"),
        path.join(THIRD_PARTY_ROOT, "css", "footable.bootstrap-3.1.6.min.css"),
        path.join(THIRD_PARTY_ROOT, "css", "sidebar.css")
      ]),
      contentType: "text/css; charset=utf-8"
    };
  }

  if (requestedPath === "/js/required.js") {
    return {
      absolutePath: null,
      body: await readFilesInOrder([
        path.join(THIRD_PARTY_ROOT, "js", "01-jquery-1.12.4.min.js"),
        path.join(THIRD_PARTY_ROOT, "js", "02-bootstrap-3.3.7.min.js"),
        path.join(THIRD_PARTY_ROOT, "js", "03-footable-3.1.6.min.js")
      ]),
      contentType: "application/javascript; charset=utf-8"
    };
  }

  if (requestedPath.startsWith("/fonts/")) {
    return {
      absolutePath: path.join(THIRD_PARTY_ROOT, requestedPath),
      body: null,
      contentType: CONTENT_TYPES[path.extname(requestedPath)] || "application/octet-stream"
    };
  }

  return null;
}

function getPagedSlice(items, page) {
  const safePage = Math.max(1, asInteger(page, 1));
  const start = (safePage - 1) * PAGE_SIZE;
  const end = safePage * PAGE_SIZE;
  return {
    page: safePage,
    items: items.slice(start, end),
    haspages: items.length === 0 ? 0 : Math.ceil(items.length / PAGE_SIZE)
  };
}

function createSimulator(options = {}) {
  const host = options.host || DEFAULT_HOST;
  const port = options.port || DEFAULT_PORT;

  let state = createDefaultState();
  let bootTimestampMs = Date.now();

  function resetState() {
    state = createDefaultState();
    bootTimestampMs = Date.now();
  }

  function sendToSocket(socket, payload) {
    if (socket.readyState === socket.OPEN) {
      socket.send(JSON.stringify(payload));
    }
  }

  function broadcast(payload) {
    const serialized = JSON.stringify(payload);
    for (const client of wss.clients) {
      if (client.readyState === client.OPEN) {
        client.send(serialized);
      }
    }
  }

  function appendEvent(type, src, desc, data) {
    const file = state.files["/eventlog.json"];
    file.entries.push({
      type,
      src,
      desc,
      data,
      time: unixNowWithOffset(state)
    });
  }

  function appendLatest(uid, username, acctype, access) {
    const file = state.files["/latestlog.json"];
    file.entries.push({
      timestamp: unixNowWithOffset(state),
      uid,
      username,
      acctype,
      access
    });
  }

  function buildStatusPayload() {
    const uptimeSeconds = Math.floor((Date.now() - bootTimestampMs) / 1000);
    return {
      command: "status",
      heap: 29784,
      chipid: "sim8266",
      cpu: 80,
      sketchsize: 462848,
      availsize: 573440,
      availspiffs: 786432,
      spiffssize: 1048576,
      uptime: formatUptime(uptimeSeconds),
      version: "simulator",
      hostname: state.config.general.hostnm,
      ssid: state.config.network.ssid,
      dns: state.config.network.dns || "8.8.8.8",
      mac: "02:00:00:82:66:01",
      ip: state.config.network.ip || "192.168.1.42",
      gateway: state.config.network.gateway || "192.168.1.1",
      netmask: state.config.network.subnet || "255.255.255.0"
    };
  }

  function sendUserList(socket, page) {
    const pageData = getPagedSlice(state.users, page);
    sendToSocket(socket, {
      command: "userlist",
      page: pageData.page,
      haspages: pageData.haspages,
      list: pageData.items
    });
    sendToSocket(socket, {
      command: "result",
      resultof: "userlist",
      result: true
    });
  }

  function sendLogPage(socket, filename, resultOfCommand) {
    const file = state.files[filename];
    const kind = file?.kind || (resultOfCommand === "eventlist" ? "event" : "latest");
    const entries = file ? file.entries : [];
    const pageData = getPagedSlice(entries, 1);
    const safePages = pageData.haspages === 0 ? 1 : pageData.haspages;

    sendToSocket(socket, {
      command: resultOfCommand === "eventlist" ? "eventlist" : "latestlist",
      page: 1,
      haspages: safePages,
      list: pageData.items.map((entry) => JSON.stringify(entry))
    });

    sendToSocket(socket, {
      command: "result",
      resultof: resultOfCommand,
      result: true
    });

    if (!file) {
      state.files[filename] = {
        kind,
        entries: []
      };
    }
  }

  function sendLogPageByPage(socket, filename, page, resultOfCommand) {
    const file = state.files[filename];
    const kind = file?.kind || (resultOfCommand === "eventlist" ? "event" : "latest");
    const entries = file ? file.entries : [];
    const pageData = getPagedSlice(entries, page);
    const safePages = pageData.haspages === 0 ? 1 : pageData.haspages;

    sendToSocket(socket, {
      command: resultOfCommand === "eventlist" ? "eventlist" : "latestlist",
      page: pageData.page,
      haspages: safePages,
      list: pageData.items.map((entry) => JSON.stringify(entry))
    });

    sendToSocket(socket, {
      command: "result",
      resultof: resultOfCommand,
      result: true
    });

    if (!file) {
      state.files[filename] = {
        kind,
        entries: []
      };
    }
  }

  function sendFileList(socket, page) {
    const files = Object.keys(state.files)
      .filter((fileName) => fileName.includes("latestlog") || fileName.includes("eventlog"))
      .sort()
      .map((fileName) => ({
        filename: fileName,
        filesize: fileEntriesSize(state.files[fileName].entries)
      }));

    const pageData = getPagedSlice(files, page);
    sendToSocket(socket, {
      command: "listfiles",
      page: pageData.page,
      haspages: pageData.haspages,
      list: pageData.items
    });
    sendToSocket(socket, {
      command: "result",
      resultof: "listfiles",
      result: true
    });
  }

  function ensureFile(filename, kind) {
    if (!state.files[filename]) {
      state.files[filename] = {
        kind,
        entries: []
      };
    }
    return state.files[filename];
  }

  function nextGeneratedFilename(baseName, infix) {
    let suffix = 1;
    let candidate = `${baseName}${infix}${suffix}`;

    while (state.files[candidate]) {
      suffix += 1;
      candidate = `${baseName}${infix}${suffix}`;
    }

    return candidate;
  }

  function handleLogMaintenance(socket, message) {
    const filename = message.filename || "";
    const action = message.action || "";
    const target = state.files[filename];

    if (!target) {
      sendToSocket(socket, {
        command: "result",
        resultof: "logfileMaintenance",
        result: false,
        message: `File not found: ${filename}`
      });
      return;
    }

    if (action === "delete") {
      if (filename === "/latestlog.json" || filename === "/eventlog.json") {
        target.entries = [];
      } else {
        delete state.files[filename];
      }
    } else if (action === "rollover") {
      const archiveName = nextGeneratedFilename(filename, ".");
      state.files[archiveName] = {
        kind: target.kind,
        entries: clone(target.entries)
      };
      target.entries = [];
    } else if (action === "split") {
      const halfway = Math.ceil(target.entries.length / 2);
      const firstSplitName = nextGeneratedFilename(filename, ".split.");
      const secondSplitName = nextGeneratedFilename(filename, ".split.");
      state.files[firstSplitName] = {
        kind: target.kind,
        entries: clone(target.entries.slice(0, halfway))
      };
      state.files[secondSplitName] = {
        kind: target.kind,
        entries: clone(target.entries.slice(halfway))
      };
    } else {
      sendToSocket(socket, {
        command: "result",
        resultof: "logfileMaintenance",
        result: false,
        message: `Unsupported action: ${action}`
      });
      return;
    }

    appendEvent("INFO", "sim", `Log maintenance: ${action}`, filename);
    sendToSocket(socket, {
      command: "result",
      resultof: "logfileMaintenance",
      result: true
    });
  }

  function upsertUser(userUpdate) {
    const index = state.users.findIndex((user) => user.uid === userUpdate.uid);
    if (index >= 0) {
      state.users.splice(index, 1, userUpdate);
    } else {
      state.users.push(userUpdate);
    }
  }

  function handleUserFile(socket, message) {
    const user = {
      uid: message.uid,
      pincode: message.pincode || "",
      username: message.user || "",
      acctype: asInteger(message.acctype, 0),
      acctype2: asInteger(message.acctype2, 0),
      acctype3: asInteger(message.acctype3, 0),
      acctype4: asInteger(message.acctype4, 0),
      validsince: asInteger(message.validsince, 0),
      validuntil: asInteger(message.validuntil, 0)
    };

    upsertUser(user);
    appendEvent("INFO", "sim", "User updated", user.uid);
    sendToSocket(socket, {
      command: "result",
      resultof: "userfile",
      result: true
    });
  }

  function simulatePICCScan(input = {}) {
    const knownUser = state.users.find((user) => user.uid === input.uid);
    const uid = input.uid || knownUser?.uid || Math.random().toString(16).slice(2, 10);
    const known = Object.prototype.hasOwnProperty.call(input, "known")
      ? asInteger(input.known, 0)
      : (knownUser ? 1 : 0);
    const access = Object.prototype.hasOwnProperty.call(input, "access")
      ? asInteger(input.access, known ? 1 : 0)
      : (known ? 1 : 0);
    const payload = {
      command: "piccscan",
      uid,
      type: input.type || "mifare",
      known
    };

    if (known) {
      payload.user = input.user || input.username || knownUser?.username || "Simulated User";
      payload.acctype = asInteger(input.acctype, knownUser?.acctype ?? 1);
      appendLatest(uid, payload.user, payload.acctype, access);
      appendEvent(access === 1 ? "INFO" : "WARN", "rfid", "Simulated RFID tag scanned", `${uid} ${payload.type}`);
    } else {
      appendLatest(uid, "Unknown", 98, 0);
      appendEvent("WARN", "rfid", "Unknown simulated RFID tag scanned", `${uid} ${payload.type}`);
    }

    broadcast(payload);
    return payload;
  }

  async function handleApiRequest(req, res, url) {
    if (req.method === "GET" && url.pathname === "/healthz") {
      sendJson(res, 200, {
        ok: true,
        host,
        port
      });
      return true;
    }

    if (req.method === "GET" && url.pathname === "/api/state") {
      sendJson(res, 200, {
        hostname: state.config.general.hostnm,
        userCount: state.users.length,
        fileCount: Object.keys(state.files).length,
        latestLogEntries: state.files["/latestlog.json"]?.entries.length || 0,
        eventLogEntries: state.files["/eventlog.json"]?.entries.length || 0,
        uploads: state.uploads.length
      });
      return true;
    }

    if (req.method === "POST" && url.pathname === "/api/reset") {
      resetState();
      sendJson(res, 200, {
        ok: true
      });
      return true;
    }

    if (req.method === "POST" && url.pathname === "/api/simulate/piccscan") {
      try {
        const body = await parseJsonBody(req);
        const payload = simulatePICCScan(body);
        sendJson(res, 200, payload);
      } catch (error) {
        sendJson(res, 400, {
          ok: false,
          error: error.message
        });
      }
      return true;
    }

    return false;
  }

  async function handleHttpRequest(req, res) {
    const url = new URL(req.url, `http://${req.headers.host || `${host}:${port}`}`);

    if (req.method === "OPTIONS") {
      res.writeHead(204, defaultHeaders({
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
      }));
      res.end();
      return;
    }

    if (await handleApiRequest(req, res, url)) {
      return;
    }

    if (url.pathname === "/login") {
      const credentials = parseBasicAuth(req.headers.authorization);
      const expectedPassword = state.config.general.pswd;
      const loginAccepted = credentials
        && credentials.username === "admin"
        && credentials.password === expectedPassword;

      if (!loginAccepted) {
        res.writeHead(401, defaultHeaders({
          "WWW-Authenticate": "Basic realm=\"esp-rfid-simulator\""
        }));
        res.end("Unauthorized");
        return;
      }

      sendJson(res, 200, {
        ok: true,
        hostname: state.config.general.hostnm
      });
      return;
    }

    if (url.pathname === "/update" && req.method === "POST") {
      let receivedBytes = 0;

      req.on("data", (chunk) => {
        receivedBytes += chunk.length;
      });

      req.on("end", () => {
        state.uploads.push({
          receivedBytes,
          time: unixNowWithOffset(state)
        });
        appendEvent("INFO", "websrv", "Firmware upload simulated", `${receivedBytes} bytes`);
        sendJson(res, 200, {
          ok: true,
          receivedBytes
        });
      });

      req.on("error", () => {
        sendJson(res, 500, {
          ok: false,
          error: "Upload failed"
        });
      });
      return;
    }

    if (url.pathname === "/favicon.ico") {
      res.writeHead(204, defaultHeaders());
      res.end();
      return;
    }

    let requestedPath = url.pathname;
    if (requestedPath === "/") {
      requestedPath = "/index.html";
    }

    const aliasedAsset = await resolveAssetAlias(requestedPath);
    if (aliasedAsset) {
      if (aliasedAsset.body !== null) {
        const bodyBuffer = Buffer.from(aliasedAsset.body, "utf8");
        res.writeHead(200, defaultHeaders({
          "Content-Length": bodyBuffer.length,
          "Content-Type": aliasedAsset.contentType
        }));
        res.end(bodyBuffer);
        return;
      }

      try {
        const fileBuffer = await fs.readFile(aliasedAsset.absolutePath);
        res.writeHead(200, defaultHeaders({
          "Content-Length": fileBuffer.length,
          "Content-Type": aliasedAsset.contentType
        }));
        res.end(fileBuffer);
      } catch (error) {
        sendJson(res, 404, {
          ok: false,
          error: `Not found: ${requestedPath}`
        });
      }
      return;
    }

    const safePath = path.normalize(requestedPath).replace(/^(\.\.(\/|\\|$))+/, "");
    const absolutePath = path.join(WEB_ROOT, safePath);

    if (!absolutePath.startsWith(WEB_ROOT)) {
      sendJson(res, 403, {
        ok: false,
        error: "Forbidden"
      });
      return;
    }

    try {
      const fileBuffer = await fs.readFile(absolutePath);
      const extension = path.extname(absolutePath);
      res.writeHead(200, defaultHeaders({
        "Content-Length": fileBuffer.length,
        "Content-Type": CONTENT_TYPES[extension] || "application/octet-stream"
      }));
      res.end(fileBuffer);
    } catch (error) {
      sendJson(res, 404, {
        ok: false,
        error: `Not found: ${requestedPath}`
      });
    }
  }

  function handleWsMessage(socket, rawMessage) {
    let message;

    try {
      message = JSON.parse(rawMessage.toString());
    } catch (error) {
      sendToSocket(socket, {
        command: "result",
        resultof: "invalid",
        result: false
      });
      return;
    }

    if (!message.command) {
      return;
    }

    if (/^testrelay\d+$/.test(message.command)) {
      appendEvent("INFO", "relay", "Simulated relay test", message.command);
      return;
    }

    switch (message.command) {
      case "remove":
        state.users = state.users.filter((user) => user.uid !== message.uid);
        appendEvent("INFO", "sim", "User removed", message.uid || "");
        break;
      case "configfile":
        state.config = clone(message);
        appendEvent("INFO", "sim", "Configuration updated", state.config.general.hostnm || "");
        break;
      case "userlist":
        sendUserList(socket, message.page);
        break;
      case "status":
        sendToSocket(socket, buildStatusPayload());
        break;
      case "userfile":
        handleUserFile(socket, message);
        break;
      case "getlatestlog":
        ensureFile(message.filename || "/latestlog.json", "latest");
        sendLogPageByPage(socket, message.filename || "/latestlog.json", message.page, "latestlist");
        break;
      case "scan":
        sendToSocket(socket, state.networks);
        break;
      case "gettime":
        sendToSocket(socket, {
          command: "gettime",
          epoch: unixNowWithOffset(state)
        });
        break;
      case "settime":
        state.timeOffsetMs = (asInteger(message.epoch, unixNowWithOffset(state)) * 1000) - Date.now();
        sendToSocket(socket, {
          command: "gettime",
          epoch: unixNowWithOffset(state)
        });
        break;
      case "getconf":
        sendToSocket(socket, state.config);
        break;
      case "geteventlog":
        ensureFile(message.filename || "/eventlog.json", "event");
        sendLogPageByPage(socket, message.filename || "/eventlog.json", message.page, "eventlist");
        break;
      case "listfiles":
        sendFileList(socket, message.page);
        break;
      case "logMaintenance":
        handleLogMaintenance(socket, message);
        break;
      case "clearevent":
        ensureFile("/eventlog.json", "event").entries = [];
        appendEvent("WARN", "sys", "Event log cleared", "");
        break;
      case "clearlatest":
        ensureFile("/latestlog.json", "latest").entries = [];
        appendEvent("WARN", "sys", "Access log cleared", "");
        break;
      case "restart":
        bootTimestampMs = Date.now();
        appendEvent("INFO", "sys", "Simulator restart requested", "");
        break;
      case "destroy":
        resetState();
        appendEvent("WARN", "sys", "Simulator reset to defaults", "");
        break;
      default:
        sendToSocket(socket, {
          command: "result",
          resultof: message.command,
          result: false
        });
        break;
    }
  }

  const server = http.createServer((req, res) => {
    handleHttpRequest(req, res).catch((error) => {
      sendJson(res, 500, {
        ok: false,
        error: error.message
      });
    });
  });

  const wss = new WebSocketServer({ noServer: true });

  wss.on("connection", (socket) => {
    socket.on("message", (message) => {
      handleWsMessage(socket, message);
    });
  });

  server.on("upgrade", (req, socket, head) => {
    if (req.url !== "/ws") {
      socket.destroy();
      return;
    }

    wss.handleUpgrade(req, socket, head, (client) => {
      wss.emit("connection", client, req);
    });
  });

  return {
    host,
    port,
    getState() {
      return state;
    },
    resetState,
    simulatePICCScan,
    start() {
      return new Promise((resolve) => {
        server.listen(port, host, () => {
          console.log(`[ INFO ] ESP-RFID simulator listening on http://${host}:${port}`);
          resolve();
        });
      });
    },
    stop() {
      return new Promise((resolve, reject) => {
        for (const client of wss.clients) {
          client.terminate();
        }

        wss.close(() => {
          server.close((error) => {
            if (error) {
              reject(error);
              return;
            }
            resolve();
          });
        });
      });
    }
  };
}

module.exports = {
  createSimulator
};

if (require.main === module) {
  const simulator = createSimulator();
  simulator.start().catch((error) => {
    console.error("[ ERRO ] Failed to start simulator");
    console.error(error);
    process.exitCode = 1;
  });
}
