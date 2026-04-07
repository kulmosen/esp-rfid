#include "ConfigModel.h"

#include <algorithm>
#include <cstdio>

namespace
{
const char *const kDefaultHostname = "esp-rfid";
const char *const kDefaultNtpServer = "pool.ntp.org";
const char *const kDefaultOpeningHours = "111111111111111111111111";
const char *const kDefaultHttpPassword = "admin";
const char *const kDefaultApIp = "192.168.4.1";
const char *const kDefaultApSubnet = "255.255.255.0";
const int kDefaultMqttPort = 1883;
const unsigned long kDefaultMqttInterval = 180;

int clampOptionalPin(int value)
{
    if (value < 0 || value > 255)
    {
        return 255;
    }

    return value;
}

int clampByte(int value)
{
    if (value < 0)
    {
        return 0;
    }
    if (value > 255)
    {
        return 255;
    }

    return value;
}

bool isValidOpeningHoursDay(const std::string &day)
{
    if (day.size() != 24)
    {
        return false;
    }

    for (std::string::const_iterator it = day.begin(); it != day.end(); ++it)
    {
        if (*it != '0' && *it != '1')
        {
            return false;
        }
    }

    return true;
}
} // namespace

namespace esprfid
{
RelayModel::RelayModel()
    : activateTime(400), lockType(LOCKTYPE_MOMENTARY), relayType(1), relayPin(4), doorName("")
{
}

ConfigModel::ConfigModel()
    : numRelays(1),
      readertype(READER_WIEGAND),
      wiegandD0Pin(4),
      wiegandD1Pin(5),
      rdm6300Pin(4),
      rfidSsPin(15),
      rfidGain(32),
      wifiLedPin(255),
      doorstatPin(255),
      maxOpenDoorTime(0),
      doorbellPin(255),
      accessDeniedPin(255),
      beeperPin(255),
      ledWaitingPin(255),
      openLockPin(255),
      pinCodeRequested(false),
      pinCodeOnly(false),
      removeParityBits(true),
      wiegandReadHex(true),
      fallbackMode(false),
      autoRestartIntervalSeconds(0),
      wifiTimeout(0),
      bssid(""),
      deviceHostname(kDefaultHostname),
      ntpServer(kDefaultNtpServer),
      ntpInterval(30),
      tzInfo(""),
      hasLegacyTimezone(false),
      legacyTimezone(0.0),
      accessPointMode(false),
      ssid(kDefaultHostname),
      wifiPassword(""),
      wifiApIp(kDefaultApIp),
      wifiApSubnet(kDefaultApSubnet),
      networkHidden(false),
      httpPass(kDefaultHttpPassword),
      dhcpEnabled(true),
      ipAddress(""),
      subnet(""),
      gateway(""),
      dns(""),
      mqttEnabled(false),
      mqttHost(""),
      mqttPort(kDefaultMqttPort),
      mqttUser(""),
      mqttPass(""),
      mqttTopic(""),
      mqttAutoTopic(false),
      mqttInterval(kDefaultMqttInterval),
      mqttEvents(false),
      mqttHA(false)
{
    relays[0].doorName = "Door";
    openingHours.fill(kDefaultOpeningHours);
}

int clampRelayCount(int requestedRelayCount)
{
    if (requestedRelayCount < 1)
    {
        return 1;
    }
    if (requestedRelayCount > MAX_NUM_RELAYS)
    {
        return MAX_NUM_RELAYS;
    }

    return requestedRelayCount;
}

std::string normalizeTimezoneInfo(const std::string &tzInfo, bool hasLegacyTimezone, double legacyTimezone)
{
    if (!tzInfo.empty())
    {
        return tzInfo;
    }

    if (!hasLegacyTimezone)
    {
        return "";
    }

    if (legacyTimezone == 0.0)
    {
        return "UTC";
    }

    char legacyBuffer[16];
    const double absoluteTimezone = legacyTimezone < 0.0 ? -legacyTimezone : legacyTimezone;
    snprintf(legacyBuffer,
             sizeof(legacyBuffer),
             "UTC%c%.2f",
             legacyTimezone < 0.0 ? '-' : '+',
             absoluteTimezone);
    return legacyBuffer;
}

void normalizeConfigModel(ConfigModel &model)
{
    model.numRelays = clampRelayCount(model.numRelays);
    model.readertype = std::max(READER_MFRC522, std::min(model.readertype, READER_PN532_RDM6300));

    model.wifiLedPin = clampOptionalPin(model.wifiLedPin);
    model.doorstatPin = clampOptionalPin(model.doorstatPin);
    model.doorbellPin = clampOptionalPin(model.doorbellPin);
    model.accessDeniedPin = clampOptionalPin(model.accessDeniedPin);
    model.beeperPin = clampOptionalPin(model.beeperPin);
    model.ledWaitingPin = clampOptionalPin(model.ledWaitingPin);
    model.openLockPin = clampOptionalPin(model.openLockPin);
    model.maxOpenDoorTime = clampByte(model.maxOpenDoorTime);

    if (model.deviceHostname.empty())
    {
        model.deviceHostname = kDefaultHostname;
    }
    if (model.ntpServer.empty())
    {
        model.ntpServer = kDefaultNtpServer;
    }
    if (model.ntpInterval <= 0)
    {
        model.ntpInterval = 30;
    }
    if (model.ssid.empty())
    {
        model.ssid = kDefaultHostname;
    }
    if (model.wifiApIp.empty())
    {
        model.wifiApIp = kDefaultApIp;
    }
    if (model.wifiApSubnet.empty())
    {
        model.wifiApSubnet = kDefaultApSubnet;
    }
    if (model.httpPass.empty())
    {
        model.httpPass = kDefaultHttpPassword;
    }
    if (model.mqttPort <= 0)
    {
        model.mqttPort = kDefaultMqttPort;
    }
    if (model.mqttInterval == 0)
    {
        model.mqttInterval = kDefaultMqttInterval;
    }
    if (model.relays[0].doorName.empty())
    {
        model.relays[0].doorName = "Door";
    }

    model.tzInfo = normalizeTimezoneInfo(model.tzInfo, model.hasLegacyTimezone, model.legacyTimezone);

    for (std::size_t dayIndex = 0; dayIndex < model.openingHours.size(); ++dayIndex)
    {
        if (!isValidOpeningHoursDay(model.openingHours[dayIndex]))
        {
            model.openingHours[dayIndex] = kDefaultOpeningHours;
        }
    }
}
} // namespace esprfid
