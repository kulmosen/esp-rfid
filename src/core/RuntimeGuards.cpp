#include "RuntimeGuards.h"

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>

namespace esprfid
{
bool shouldEnableWifiOnAdminRequest(bool enableRequested, bool waitingForPinCode, bool relayActive, bool wifiConnected)
{
    return enableRequested && !waitingForPinCode && relayActive && !wifiConnected;
}

bool shouldProcessWifiReconnect(bool reconnectRequested, bool wifiConnected)
{
    return reconnectRequested && !wifiConnected;
}

bool shouldScheduleWifiReconnect(bool wifiDisabledByPolicy, bool fallbackMode)
{
    return !wifiDisabledByPolicy && !fallbackMode;
}

bool tryParseRelayIndex(const char *rawValue, int relayCount, int &relayIndex)
{
    relayIndex = -1;
    if (rawValue == NULL || relayCount <= 0)
    {
        return false;
    }

    errno = 0;
    char *endPtr = NULL;
    long parsedValue = strtol(rawValue, &endPtr, 10);
    if (errno != 0 || endPtr == rawValue || *endPtr != '\0')
    {
        return false;
    }
    if (parsedValue < 0 || parsedValue >= relayCount || parsedValue > INT_MAX)
    {
        return false;
    }

    relayIndex = static_cast<int>(parsedValue);
    return true;
}

std::string buildAutoTopic(const char *baseTopic, const uint8_t macAddress[6])
{
    if (baseTopic == NULL)
    {
        return "";
    }

    char suffix[8];
    snprintf(suffix, sizeof(suffix), "-%02x%02x%02x", macAddress[3], macAddress[4], macAddress[5]);
    return std::string(baseTopic) + suffix;
}
} // namespace esprfid
