import sys

import pytest


def run():
    sys.exit(pytest.main([]))


def coverage():
    sys.exit(pytest.main([
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-fail-under=70",
    ]))
