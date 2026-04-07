#include "test_framework.h"

#include <exception>
#include <iostream>

namespace hosttests
{
std::vector<TestCase> &registry()
{
    static std::vector<TestCase> tests;
    return tests;
}

Registrar::Registrar(const char *name, void (*func)())
{
    registry().push_back(TestCase{name, func});
}
} // namespace hosttests

int main()
{
    int failures = 0;
    for (const auto &test : hosttests::registry())
    {
        try
        {
            test.func();
            std::cout << "[PASS] " << test.name << "\n";
        }
        catch (const std::exception &ex)
        {
            ++failures;
            std::cerr << "[FAIL] " << test.name << ": " << ex.what() << "\n";
        }
    }

    if (failures > 0)
    {
        std::cerr << failures << " test(s) failed\n";
        return 1;
    }

    std::cout << hosttests::registry().size() << " test(s) passed\n";
    return 0;
}
