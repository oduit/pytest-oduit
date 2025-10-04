[![codecov](https://codecov.io/gh/oduit/pytest-oduit/graph/badge.svg?token=4VKN1JL1UM)](https://codecov.io/gh/oduit/pytest-oduit)

# pytest-oduit

A pytest plugin for running Odoo tests with enhanced functionality and integration with oduit-core.

## Features

- **Automatic Odoo configuration**: Integrates with `.oduit.toml` configuration files using oduit-core
- **Automatic module installation**: Automatically detects and installs addon modules based on test paths
- **Module path resolution**: Automatically resolves Odoo addon module paths for proper test discovery
- **Test retry management**: Disables Odoo's built-in test retry mechanism to work seamlessly with pytest
- **Distributed testing support**: Works with pytest-xdist for parallel test execution
- **HTTP server support**: Optional Odoo HTTP server launch for integration tests

## Installation

```bash
pip install pytest-oduit
```

Note: pytest-odoo must not be installed.

## Requirements

- Python >= 3.9
- pytest >= 8
- oduit
- Odoo >= 15.0

## Usage

### Basic Usage

Simply run pytest in your Odoo addon directory:

```bash
pytest
```

The plugin will automatically detect which addon modules contain your tests and initialize them in Odoo. For example:

```bash
pytest addons/sale                    # Automatically adds --init=sale
pytest addons/sale addons/purchase    # Automatically adds --init=purchase,sale
pytest addons/sale/tests/test_sale.py # Automatically adds --init=sale
```

This eliminates the need to manually specify `--odoo-install` for each test run.

### Other pytest plugins

This plugin works also together `pytest-subtests` and `pytest-xdist`.

### Command Line Options

- `--odoo-log-level`: Set the log level for Odoo processes during tests (default: 'critical')
- `--odoo-install`: Manually specify modules to install during tests (overrides automatic detection)
- `--oduit-env`: Set the oduit config file, when not specified a local `.oduit.toml` configuration is needed

### Automatic Module Installation

When running tests, the plugin automatically detects which addon modules are being tested and initializes them in Odoo by adding them to the `--init` parameter. This works by:

1. Analyzing the test paths provided to pytest
2. Extracting addon names by locating `__manifest__.py` files
3. Automatically appending `--init=<detected_modules>` to the Odoo configuration

This feature only activates when:
- A `.oduit.toml` configuration file is present or `--oduit-env` is specified
- `--odoo-install` is not explicitly provided (manual specification takes precedence)

The automatic detection supports:
- Addon directories: `pytest addons/my_module`
- Test files: `pytest addons/my_module/tests/test_something.py`
- Multiple addons: `pytest addons/module_a addons/module_b`

### Configuration

The plugin automatically detects and uses `.oduit.toml` configuration files when available. This provides seamless integration with oduit for database configuration, addon paths, and other Odoo settings.

Example `.oduit.toml`:

```toml
[odoo]
db_name = "test_db"
addons_path = ["./addons", "./custom_addons"]
```

### Module Path Resolution

The plugin automatically resolves Odoo addon module paths, ensuring that:

- Test modules in `addon_name/tests/` are properly recognized as `odoo.addons.addon_name.tests.test_module`
- Only installable addons (with `installable: True` in `__manifest__.py`) are collected for testing
- Namespace packages are handled correctly

### Distributed Testing

Works seamlessly with pytest-xdist for parallel test execution:

```bash
pytest -n auto  # Run tests in parallel using all available CPUs
```

The plugin automatically creates isolated database copies for each worker to prevent conflicts.

## Development

### Running Tests

```bash
cd pytest-oduit
pytest
```

### Test Structure

The plugin includes comprehensive tests that use mock Odoo modules to verify functionality without requiring a full Odoo installation.

## License

AGPLv3 - see LICENSE file for details.

## Authors

- Holger Nahrstaedt
- Based on original work by Pierre Verkest and Camptocamp SA

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
