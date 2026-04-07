#ifndef ESP_RFID_RUNTIME_GUARDS_H
#define ESP_RFID_RUNTIME_GUARDS_H

#include <stdint.h>
#include <string>

namespace esprfid
{
bool shouldEnableWifiOnAdminRequest(bool enableRequested, bool waitingForPinCode, bool relayActive, bool wifiConnected);
bool shouldProcessWifiReconnect(bool reconnectRequested, bool wifiConnected);
bool shouldScheduleWifiReconnect(bool wifiDisabledByPolicy, bool fallbackMode);
bool tryParseRelayIndex(const char *rawValue, int relayCount, int &relayIndex);
std::string buildAutoTopic(const char *baseTopic, const uint8_t macAddress[6]);
} // namespace esprfid

#endif
