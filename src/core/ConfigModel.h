#ifndef ESP_RFID_CONFIG_MODEL_H
#define ESP_RFID_CONFIG_MODEL_H

#include <array>
#include <string>

#include "../magicnumbers.h"

namespace esprfid
{
struct RelayModel
{
    unsigned long activateTime;
    int lockType;
    int relayType;
    int relayPin;
    std::string doorName;

    RelayModel();
};

struct ConfigModel
{
    int numRelays;
    int readertype;
    int wiegandD0Pin;
    int wiegandD1Pin;
    int rdm6300Pin;
    int rfidSsPin;
    int rfidGain;
    int wifiLedPin;
    int doorstatPin;
    int maxOpenDoorTime;
    int doorbellPin;
    int accessDeniedPin;
    int beeperPin;
    int ledWaitingPin;
    int openLockPin;
    bool pinCodeRequested;
    bool pinCodeOnly;
    bool removeParityBits;
    bool wiegandReadHex;
    bool fallbackMode;
    unsigned long autoRestartIntervalSeconds;
    unsigned long wifiTimeout;
    std::string bssid;
    std::string deviceHostname;
    std::string ntpServer;
    int ntpInterval;
    std::string tzInfo;
    bool hasLegacyTimezone;
    double legacyTimezone;
    bool accessPointMode;
    std::string ssid;
    std::string wifiPassword;
    std::string wifiApIp;
    std::string wifiApSubnet;
    bool networkHidden;
    std::string httpPass;
    bool dhcpEnabled;
    std::string ipAddress;
    std::string subnet;
    std::string gateway;
    std::string dns;
    std::array<std::string, 7> openingHours;
    bool mqttEnabled;
    std::string mqttHost;
    int mqttPort;
    std::string mqttUser;
    std::string mqttPass;
    std::string mqttTopic;
    bool mqttAutoTopic;
    unsigned long mqttInterval;
    bool mqttEvents;
    bool mqttHA;
    std::array<RelayModel, MAX_NUM_RELAYS> relays;

    ConfigModel();
};

int clampRelayCount(int requestedRelayCount);
std::string normalizeTimezoneInfo(const std::string &tzInfo, bool hasLegacyTimezone, double legacyTimezone);
void normalizeConfigModel(ConfigModel &model);
} // namespace esprfid

#endif
