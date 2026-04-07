#include "test_framework.h"

#include "../../src/core/AccessLogic.h"

#include <string>

TEST_CASE(converts_weekday_from_sunday_to_monday_index)
{
    ASSERT_EQ(6, esprfid::weekdayFromMonday(1));
    ASSERT_EQ(0, esprfid::weekdayFromMonday(2));
    ASSERT_EQ(5, esprfid::weekdayFromMonday(7));
}

TEST_CASE(pin_code_is_accepted_when_pin_not_required)
{
    ASSERT_TRUE(esprfid::isPinCodeAccepted(false, "1234", "9999", "abcd"));
}

TEST_CASE(pin_code_is_accepted_when_user_has_no_stored_pin)
{
    ASSERT_TRUE(esprfid::isPinCodeAccepted(true, "1234", "", "abcd"));
}

TEST_CASE(pin_code_accepts_matching_pin_or_uid)
{
    ASSERT_TRUE(esprfid::isPinCodeAccepted(true, "1234", "1234", "abcd"));
    ASSERT_TRUE(esprfid::isPinCodeAccepted(true, "abcd", "1234", "abcd"));
}

TEST_CASE(pin_code_rejects_wrong_value)
{
    ASSERT_FALSE(esprfid::isPinCodeAccepted(true, "0000", "1234", "abcd"));
}

TEST_CASE(opening_hour_requires_valid_day_string_and_hour)
{
    ASSERT_TRUE(esprfid::isOpeningHourAllowed("111111111111111111111111", 23));
    ASSERT_FALSE(esprfid::isOpeningHourAllowed("111", 5));
    ASSERT_FALSE(esprfid::isOpeningHourAllowed(NULL, 5));
    ASSERT_FALSE(esprfid::isOpeningHourAllowed("111111111111111111111111", 24));
}

TEST_CASE(granted_user_within_window_and_schedule_is_allowed)
{
    const char *week[7] = {
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111"};

    ASSERT_EQ(static_cast<int>(esprfid::AccessEvaluation::Granted),
              static_cast<int>(esprfid::evaluateAccountAccess(1, 100, 200, 150, week, 2, 10)));
}

TEST_CASE(granted_user_outside_validity_window_expires)
{
    const char *week[7] = {
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111"};

    ASSERT_EQ(static_cast<int>(esprfid::AccessEvaluation::Expired),
              static_cast<int>(esprfid::evaluateAccountAccess(1, 100, 120, 150, week, 2, 10)));
}

TEST_CASE(granted_user_outside_schedule_is_denied)
{
    const char *week[7] = {
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000"};

    ASSERT_EQ(static_cast<int>(esprfid::AccessEvaluation::Denied),
              static_cast<int>(esprfid::evaluateAccountAccess(1, 100, 200, 150, week, 2, 10)));
}

TEST_CASE(admin_user_bypasses_schedule_and_validity)
{
    const char *week[7] = {
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000",
        "000000000000000000000000"};

    ASSERT_EQ(static_cast<int>(esprfid::AccessEvaluation::Admin),
              static_cast<int>(esprfid::evaluateAccountAccess(99, 500, 600, 1000, week, 7, 23)));
}

TEST_CASE(disabled_user_is_denied)
{
    const char *week[7] = {
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111",
        "111111111111111111111111"};

    ASSERT_EQ(static_cast<int>(esprfid::AccessEvaluation::Denied),
              static_cast<int>(esprfid::evaluateAccountAccess(0, 100, 200, 150, week, 2, 10)));
}
