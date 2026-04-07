#ifndef ESP_RFID_HOST_TEST_FRAMEWORK_H
#define ESP_RFID_HOST_TEST_FRAMEWORK_H

#include <sstream>
#include <stdexcept>
#include <vector>

namespace hosttests
{
struct TestCase
{
    const char *name;
    void (*func)();
};

std::vector<TestCase> &registry();

struct Registrar
{
    Registrar(const char *name, void (*func)());
};
} // namespace hosttests

#define TEST_CASE(name)                                                                                                 \
    void name();                                                                                                         \
    static hosttests::Registrar registrar_##name(#name, name);                                                          \
    void name()

#define ASSERT_TRUE(condition)                                                                                           \
    do                                                                                                                   \
    {                                                                                                                    \
        if (!(condition))                                                                                                \
        {                                                                                                                \
            std::ostringstream assertionStream;                                                                          \
            assertionStream << "Assertion failed: " #condition << " at " << __FILE__ << ":" << __LINE__;              \
            throw std::runtime_error(assertionStream.str());                                                             \
        }                                                                                                                \
    } while (0)

#define ASSERT_FALSE(condition) ASSERT_TRUE(!(condition))

#define ASSERT_EQ(expected, actual)                                                                                      \
    do                                                                                                                   \
    {                                                                                                                    \
        const auto expectedValue = (expected);                                                                           \
        const auto actualValue = (actual);                                                                               \
        if (!(expectedValue == actualValue))                                                                             \
        {                                                                                                                \
            std::ostringstream assertionStream;                                                                          \
            assertionStream << "Assertion failed: expected [" << expectedValue << "] but got [" << actualValue         \
                            << "] at " << __FILE__ << ":" << __LINE__;                                                 \
            throw std::runtime_error(assertionStream.str());                                                             \
        }                                                                                                                \
    } while (0)

#endif
