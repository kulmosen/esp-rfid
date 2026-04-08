#include "../../src/core/ConfigValidation.h"
#include "test_framework.h"

TEST_CASE(config_validation_rejects_out_of_range_relay_count)
{
    esprfid::ConfigModel model;
    model.numRelays = 5;

    esprfid::ConfigValidationResult result = esprfid::validateConfigModel(model);

    ASSERT_FALSE(result.valid);
}

TEST_CASE(config_validation_rejects_empty_critical_strings)
{
    esprfid::ConfigModel model;
    model.deviceHostname.clear();

    esprfid::ConfigValidationResult result = esprfid::validateConfigModel(model);
    ASSERT_FALSE(result.valid);

    model = esprfid::ConfigModel();
    model.httpPass.clear();
    result = esprfid::validateConfigModel(model);
    ASSERT_FALSE(result.valid);

    model = esprfid::ConfigModel();
    model.ssid.clear();
    result = esprfid::validateConfigModel(model);
    ASSERT_FALSE(result.valid);
}

TEST_CASE(config_validation_rejects_invalid_relay_pin_and_opening_hours)
{
    esprfid::ConfigModel model;
    model.relays[0].relayPin = 99;

    esprfid::ConfigValidationResult result = esprfid::validateConfigModel(model);
    ASSERT_FALSE(result.valid);

    model = esprfid::ConfigModel();
    model.openingHours[0] = "101";
    result = esprfid::validateConfigModel(model);
    ASSERT_FALSE(result.valid);
}

TEST_CASE(config_validation_accepts_default_model)
{
    esprfid::ConfigModel model;
    esprfid::ConfigValidationResult result = esprfid::validateConfigModel(model);
    ASSERT_TRUE(result.valid);
}
