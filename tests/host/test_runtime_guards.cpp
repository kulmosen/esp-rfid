#include "test_framework.h"

#include "../../src/core/RuntimeGuards.h"

#include <stdint.h>
#include <string>

TEST_CASE(parses_valid_relay_index)
{
    int relayIndex = -1;
    ASSERT_TRUE(esprfid::tryParseRelayIndex("2", 4, relayIndex));
    ASSERT_EQ(2, relayIndex);
}

TEST_CASE(rejects_missing_relay_index)
{
    int relayIndex = 9;
    ASSERT_FALSE(esprfid::tryParseRelayIndex(NULL, 4, relayIndex));
    ASSERT_EQ(-1, relayIndex);
}

TEST_CASE(rejects_non_numeric_relay_index)
{
    int relayIndex = -1;
    ASSERT_FALSE(esprfid::tryParseRelayIndex("door-1", 4, relayIndex));
    ASSERT_EQ(-1, relayIndex);
}

TEST_CASE(rejects_out_of_range_relay_index)
{
    int relayIndex = -1;
    ASSERT_FALSE(esprfid::tryParseRelayIndex("4", 4, relayIndex));
    ASSERT_EQ(-1, relayIndex);
}

TEST_CASE(builds_auto_topic_suffix_from_mac)
{
    const uint8_t macAddress[6] = {0xDE, 0xAD, 0xBE, 0xEF, 0x12, 0x34};
    ASSERT_EQ(std::string("/rfid-ef1234"), esprfid::buildAutoTopic("/rfid", macAddress));
}

TEST_CASE(admin_wifi_enable_requires_request_and_relay)
{
    ASSERT_TRUE(esprfid::shouldEnableWifiOnAdminRequest(true, false, true, false));
    ASSERT_FALSE(esprfid::shouldEnableWifiOnAdminRequest(false, false, true, false));
    ASSERT_FALSE(esprfid::shouldEnableWifiOnAdminRequest(true, true, true, false));
    ASSERT_FALSE(esprfid::shouldEnableWifiOnAdminRequest(true, false, false, false));
    ASSERT_FALSE(esprfid::shouldEnableWifiOnAdminRequest(true, false, true, true));
}

TEST_CASE(reconnect_policy_skips_manual_disable_and_fallback)
{
    ASSERT_TRUE(esprfid::shouldScheduleWifiReconnect(false, false));
    ASSERT_FALSE(esprfid::shouldScheduleWifiReconnect(true, false));
    ASSERT_FALSE(esprfid::shouldScheduleWifiReconnect(false, true));
}

TEST_CASE(reconnect_processing_requires_disconnected_wifi)
{
    ASSERT_TRUE(esprfid::shouldProcessWifiReconnect(true, false));
    ASSERT_FALSE(esprfid::shouldProcessWifiReconnect(false, false));
    ASSERT_FALSE(esprfid::shouldProcessWifiReconnect(true, true));
}
