#ifndef ESP_RFID_ACCESS_LOGIC_H
#define ESP_RFID_ACCESS_LOGIC_H

namespace esprfid
{
enum class AccessEvaluation
{
    Denied,
    Granted,
    Admin,
    Expired
};

int weekdayFromMonday(int weekdayFromSunday);
bool isPinCodeAccepted(bool pinCodeRequested, const char *enteredPinCode, const char *storedPinCode, const char *uid);
bool isOpeningHourAllowed(const char *openingHoursForDay, int localHour);
bool isAccessAllowedForWeekSchedule(const char *const openingHours[7], int weekdayFromSunday, int localHour);
AccessEvaluation evaluateAccountAccess(int accountType,
                                       unsigned long validSince,
                                       unsigned long validUntil,
                                       unsigned long currentEpoch,
                                       const char *const openingHours[7],
                                       int weekdayFromSunday,
                                       int localHour);
} // namespace esprfid

#endif
