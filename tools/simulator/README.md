# ESP-RFID Simulator

This is a local behavior-level simulator for ESP-RFID. It is meant for testing the web UI, WebSocket flows, config handling, user CRUD, log views, and simulated RFID scans without real hardware.

It is **not** a full ESP8266 CPU or peripheral emulator.

## What it simulates

* Static hosting of the files in `src/websrc/`
* `/login` and `/update` HTTP endpoints
* `/ws` WebSocket endpoint
* Device status responses
* Config get/save flow
* User list, add/edit, delete
* Event log and access log pagination
* Log maintenance actions
* WiFi scan results
* Time sync commands
* Simulated PICC scans over HTTP

## Usage

```sh
cd tools/simulator
npm install
npm start
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080).

Log in with password `admin`, or use the web UI's built-in local shortcut password `neo`.

## Useful endpoints

Health check:

```sh
curl http://127.0.0.1:8080/healthz
```

Inspect current state:

```sh
curl http://127.0.0.1:8080/api/state
```

Reset simulator state:

```sh
curl -X POST http://127.0.0.1:8080/api/reset
```

Simulate an unknown RFID scan:

```sh
curl -X POST http://127.0.0.1:8080/api/simulate/piccscan \
  -H 'Content-Type: application/json' \
  -d '{"uid":"feedbeef","known":0,"type":"mifare"}'
```

Simulate a known RFID scan:

```sh
curl -X POST http://127.0.0.1:8080/api/simulate/piccscan \
  -H 'Content-Type: application/json' \
  -d '{"uid":"70f3675d","known":1,"type":"mifare","user":"Maria Cohen","acctype":1,"access":1}'
```

Run the smoke test:

```sh
npm run smoke
```

Run the browser-based end-to-end test:

```sh
npm run e2e
```

The browser scenario covers:

* rejected invalid config saves
* editing and committing general settings
* adding a user from an unknown RFID scan
* replaying a known RFID scan
* verifying access log and event log views
* settings backup and restore
* user backup and restore
* logfile rollover, split, and delete flows
