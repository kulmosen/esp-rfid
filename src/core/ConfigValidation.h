#ifndef ESP_RFID_CONFIG_VALIDATION_H
#define ESP_RFID_CONFIG_VALIDATION_H

#include <string>

#include "ConfigModel.h"

namespace esprfid
{
struct ConfigValidationResult
{
    bool valid;
    std::string message;
};

ConfigValidationResult validateConfigModel(const ConfigModel &model);
} // namespace esprfid

#endif
