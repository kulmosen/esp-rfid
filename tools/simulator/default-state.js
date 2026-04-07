"use strict";

function unixNow() {
  return Math.floor(Date.now() / 1000);
}

function daysFromNow(days) {
  return unixNow() + (days * 24 * 60 * 60);
}

function createDefaultState() {
  return {
    timeOffsetMs: 0,
    networks: {
      command: "ssidlist",
      list: [
        {
          ssid: "Workshop WiFi",
          bssid: "4c:f4:39:a1:41:01",
          rssi: "-42",
          channel: 1,
          enctype: 4,
          hidden: false
        },
        {
          ssid: "Office Mesh",
          bssid: "9c:f1:90:c5:15:22",
          rssi: "-58",
          channel: 6,
          enctype: 4,
          hidden: false
        },
        {
          ssid: "Guest Network",
          bssid: "8a:e6:63:a8:15:33",
          rssi: "-75",
          channel: 11,
          enctype: 4,
          hidden: false
        },
        {
          ssid: "Hidden Reader VLAN",
          bssid: "8a:f5:86:c3:12:44",
          rssi: "-81",
          channel: 3,
          enctype: 4,
          hidden: true
        }
      ]
    },
    config: {
      command: "configfile",
      network: {
        bssid: "4c:f4:39:a1:41:01",
        ssid: "Workshop WiFi",
        wmode: 0,
        hide: 0,
        pswd: "supersecret",
        offtime: 180,
        dhcp: 1,
        ip: "",
        subnet: "",
        gateway: "",
        dns: "",
        apip: "192.168.4.1",
        apsubnet: "255.255.255.0",
        fallbackmode: 1
      },
      hardware: {
        readertype: 1,
        wgd0pin: 4,
        wgd1pin: 5,
        rdm6300pin: 4,
        sspin: 15,
        rfidgain: 32,
        wifipin: 255,
        rtype: 1,
        ltype: 0,
        rpin: 16,
        rtime: 400,
        doorname: "Front Door",
        beeperpin: 255,
        ledwaitingpin: 255,
        openlockpin: 255,
        doorbellpin: 255,
        accessdeniedpin: 255,
        useridstoragemode: "hexadecimal",
        requirepincodeafterrfid: 1,
        allowpincodeonly: 0,
        removeparitybits: 1,
        doorstatpin: 255,
        maxOpenDoorTime: 0,
        numrelays: 2,
        relay2: {
          rtype: 1,
          ltype: 0,
          rpin: 14,
          rtime: 500,
          doorname: "Workshop Gate"
        }
      },
      general: {
        hostnm: "esp-rfid-sim",
        restart: 86400,
        pswd: "admin",
        openinghours: [
          "111111111111111111111111",
          "111111111111111111111111",
          "111111111111111111111111",
          "111111111111111111111111",
          "111111111111111111111111",
          "000000001111111111000000",
          "000000001111111111000000"
        ]
      },
      mqtt: {
        enabled: 1,
        host: "broker.local",
        port: 1883,
        topic: "test/door/front",
        autotopic: 0,
        user: "esp-rfid",
        pswd: "mqtt-secret",
        syncrate: 180,
        mqttlog: 1,
        mqttha: 0
      },
      ntp: {
        server: "pool.ntp.org",
        interval: 30,
        tzinfo: "CET-1CEST,M3.5.0,M10.5.0/3"
      }
    },
    users: [
      {
        uid: "12c9298d",
        pincode: "1234",
        username: "Nikki Kidd",
        acctype: 99,
        acctype2: 1,
        validsince: 0,
        validuntil: daysFromNow(365)
      },
      {
        uid: "70f3675d",
        pincode: "4567",
        username: "Maria Cohen",
        acctype: 1,
        acctype2: 0,
        validsince: 0,
        validuntil: daysFromNow(120)
      },
      {
        uid: "80c2489b",
        pincode: "9999",
        username: "Hilda Whitaker",
        acctype: 1,
        acctype2: 1,
        validsince: 0,
        validuntil: daysFromNow(30)
      }
    ],
    files: {
      "/latestlog.json": {
        kind: "latest",
        entries: [
          {
            timestamp: unixNow() - 900,
            uid: "12c9298d",
            username: "Nikki Kidd",
            acctype: 99,
            access: 1
          },
          {
            timestamp: unixNow() - 600,
            uid: "70f3675d",
            username: "Maria Cohen",
            acctype: 1,
            access: 1
          },
          {
            timestamp: unixNow() - 60,
            uid: "deadbeef",
            username: "Unknown",
            acctype: 98,
            access: 0
          }
        ]
      },
      "/eventlog.json": {
        kind: "event",
        entries: [
          {
            type: "INFO",
            src: "sys",
            desc: "System setup completed, running",
            data: "",
            time: unixNow() - 1200
          },
          {
            type: "INFO",
            src: "wifi",
            desc: "WiFi is connected",
            data: "Workshop WiFi",
            time: unixNow() - 1000
          },
          {
            type: "WARN",
            src: "rfid",
            desc: "Unknown rfid tag is scanned",
            data: "deadbeef mifare",
            time: unixNow() - 60
          }
        ]
      }
    },
    uploads: []
  };
}

module.exports = {
  createDefaultState
};
