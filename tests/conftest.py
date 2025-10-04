import sys
from pathlib import Path


def pytest_configure(config):
    mock_path = Path(__file__).parent / "mock"

    if mock_path.exists():
        test_args = [
            Path(arg.split("::")[0]).resolve()
            for arg in config.args
            if arg and not arg.startswith("-")
        ]

        tests_dir = Path(__file__).parent.resolve()
        is_running_unit_tests = any(
            tests_dir in arg.parents or arg == tests_dir
            for arg in test_args
            if arg.exists()
        )

        if is_running_unit_tests or not test_args:
            sys.path.insert(0, str(mock_path))


def pytest_unconfigure(config):
    mock_path = Path(__file__).parent / "mock"
    mock_path_str = str(mock_path)

    if mock_path_str in sys.path:
        sys.path.remove(mock_path_str)
