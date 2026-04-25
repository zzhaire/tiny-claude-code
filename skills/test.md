---
name: test
description: Write tests — unit tests, edge cases, and test strategy
---

You are writing tests for the code the user provides. Follow these principles:

1. **Coverage**: Cover the happy path, edge cases (empty input, boundary values, None/null), and error paths.
2. **Clarity**: Each test should have one clear purpose. Name tests descriptively: `test_<what>_<condition>_<expected>`.
3. **Isolation**: Tests should not depend on each other or on external state. Mock external dependencies.
4. **Framework**: Match the testing framework already used in the project (pytest, unittest, jest, etc.). If none exists, default to pytest for Python.
5. **Runnable**: Produce tests that can be run immediately without modification.

Output the complete test file, or a clearly delimited block that can be appended to an existing test file.
