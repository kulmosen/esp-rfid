#include "ConfigValidation.h"

namespace
{
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

bool isValidRelayPin(int pin)
{
    return pin >= 0 && pin <= 16;
}

bool isValidOptionalPin(int pin)
{
    return pin >= 0 && pin <= 255;
}
} // namespace

namespace esprfid
{
ConfigValidationResult validateConfigModel(const ConfigModel &model)
{
    if (model.numRelays < 1 || model.numRelays > MAX_NUM_RELAYS)
    {
        return {false, "numrelays must be between 1 and 4"};
    }

    if (model.readertype < READER_MFRC522 || model.readertype > READER_PN532_RDM6300)
    {
        return {false, "readertype is out of range"};
    }

    if (model.deviceHostname.empty())
    {
        return {false, "general.hostnm must not be empty"};
    }

    if (model.httpPass.empty())
    {
        return {false, "general.pswd must not be empty"};
    }

    if (model.ssid.empty())
    {
        return {false, "network.ssid must not be empty"};
    }

    if (!isValidOptionalPin(model.wifiLedPin) ||
        !isValidOptionalPin(model.doorstatPin) ||
        !isValidOptionalPin(model.maxOpenDoorTime) ||
        !isValidOptionalPin(model.doorbellPin) ||
        !isValidOptionalPin(model.accessDeniedPin) ||
        !isValidOptionalPin(model.beeperPin) ||
        !isValidOptionalPin(model.ledWaitingPin) ||
        !isValidOptionalPin(model.openLockPin))
    {
        return {false, "one or more optional hardware pins are out of range"};
    }

    for (int relayIndex = 0; relayIndex < model.numRelays; ++relayIndex)
    {
        if (!isValidRelayPin(model.relays[relayIndex].relayPin))
        {
            return {false, "relay pin is out of range"};
        }
    }

    for (std::size_t dayIndex = 0; dayIndex < model.openingHours.size(); ++dayIndex)
    {
        if (!isValidOpeningHoursDay(model.openingHours[dayIndex]))
        {
            return {false, "openinghours must contain 7 day strings of 24 binary flags"};
        }
    }

    return {true, ""};
}
} // namespace esprfid
