#include "AccessLogic.h"

#include "../magicnumbers.h"

#include <stddef.h>
#include <string.h>

namespace esprfid
{
int weekdayFromMonday(int weekdayFromSunday)
{
    return (weekdayFromSunday + 5) % 7;
}

bool isPinCodeAccepted(bool pinCodeRequested, const char *enteredPinCode, const char *storedPinCode, const char *uid)
{
    if (!pinCodeRequested)
    {
        return true;
    }

    const char *safeEnteredPinCode = enteredPinCode != NULL ? enteredPinCode : "";
    const char *safeStoredPinCode = storedPinCode != NULL ? storedPinCode : "";
    const char *safeUid = uid != NULL ? uid : "";

    if (safeStoredPinCode[0] == '\0')
    {
        return true;
    }

    return strcmp(safeEnteredPinCode, safeStoredPinCode) == 0 || strcmp(safeEnteredPinCode, safeUid) == 0;
}

bool isOpeningHourAllowed(const char *openingHoursForDay, int localHour)
{
    if (openingHoursForDay == NULL || localHour < 0 || localHour >= 24)
    {
        return false;
    }
    if (strlen(openingHoursForDay) <= static_cast<size_t>(localHour))
    {
        return false;
    }

    return openingHoursForDay[localHour] == '1';
}

bool isAccessAllowedForWeekSchedule(const char *const openingHours[7], int weekdayFromSunday, int localHour)
{
    if (openingHours == NULL)
    {
        return false;
    }

    int weekdayIndex = weekdayFromMonday(weekdayFromSunday);
    if (weekdayIndex < 0 || weekdayIndex >= 7)
    {
        return false;
    }

    return isOpeningHourAllowed(openingHours[weekdayIndex], localHour);
}

AccessEvaluation evaluateAccountAccess(int accountType,
                                       unsigned long validSince,
                                       unsigned long validUntil,
                                       unsigned long currentEpoch,
                                       const char *const openingHours[7],
                                       int weekdayFromSunday,
                                       int localHour)
{
    if (accountType == ACCESS_ADMIN)
    {
        return AccessEvaluation::Admin;
    }

    if (accountType != ACCESS_GRANTED)
    {
        return AccessEvaluation::Denied;
    }

    if (validUntil < currentEpoch || validSince > currentEpoch)
    {
        return AccessEvaluation::Expired;
    }

    if (!isAccessAllowedForWeekSchedule(openingHours, weekdayFromSunday, localHour))
    {
        return AccessEvaluation::Denied;
    }

    return AccessEvaluation::Granted;
}
} // namespace esprfid
