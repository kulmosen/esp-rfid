#include "../../src/core/ConfigModel.h"
#include "test_framework.h"

TEST_CASE(clamps_relay_count_to_supported_range)
{
    ASSERT_EQ(1, esprfid::clampRelayCount(0));
    ASSERT_EQ(4, esprfid::clampRelayCount(9));
    ASSERT_EQ(3, esprfid::clampRelayCount(3));
}

TEST_CASE(legacy_negative_timezone_is_migrated_without_double_minus)
{
    ASSERT_EQ(std::string("UTC-3.50"), esprfid::normalizeTimezoneInfo("", true, -3.5));
}

TEST_CASE(explicit_tzinfo_wins_over_legacy_timezone)
{
    ASSERT_EQ(std::string("CET-1CEST,M3.5.0,M10.5.0/3"),
              esprfid::normalizeTimezoneInfo("CET-1CEST,M3.5.0,M10.5.0/3", true, -1.0));
}

TEST_CASE(config_model_applies_safe_defaults)
{
    esprfid::ConfigModel model;
    model.deviceHostname.clear();
    model.ntpServer.clear();
    model.ntpInterval = 0;
    model.ssid.clear();
    model.wifiApIp.clear();
    model.wifiApSubnet.clear();
    model.httpPass.clear();
    model.mqttPort = 0;
    model.mqttInterval = 0;

    esprfid::normalizeConfigModel(model);

    ASSERT_EQ(std::string("esp-rfid"), model.deviceHostname);
    ASSERT_EQ(std::string("pool.ntp.org"), model.ntpServer);
    ASSERT_EQ(30, model.ntpInterval);
    ASSERT_EQ(std::string("esp-rfid"), model.ssid);
    ASSERT_EQ(std::string("192.168.4.1"), model.wifiApIp);
    ASSERT_EQ(std::string("255.255.255.0"), model.wifiApSubnet);
    ASSERT_EQ(std::string("admin"), model.httpPass);
    ASSERT_EQ(1883, model.mqttPort);
    ASSERT_EQ(180ul, model.mqttInterval);
}

TEST_CASE(config_model_normalizes_invalid_opening_hours_and_byte_values)
{
    esprfid::ConfigModel model;
    model.openingHours[0] = "111";
    model.openingHours[1] = "11111111111111111111111x";
    model.maxOpenDoorTime = 999;
    model.wifiLedPin = 999;

    esprfid::normalizeConfigModel(model);

    ASSERT_EQ(std::string("111111111111111111111111"), model.openingHours[0]);
    ASSERT_EQ(std::string("111111111111111111111111"), model.openingHours[1]);
    ASSERT_EQ(255, model.maxOpenDoorTime);
    ASSERT_EQ(255, model.wifiLedPin);
}
