[![codecov](https://codecov.io/gh/oduit/pytest-oduit/graph/badge.svg?token=4VKN1JL1UM)](https://codecov.io/gh/oduit/pytest-oduit)

# pytest-oduit

A pytest plugin for running Odoo tests with automatic Odoo setup and oduit integration.

## Features

- **Automatic Odoo configuration**: Integrates with `.oduit.toml` configuration files using oduit-core
- **Automatic module installation**: Automatically detects and installs addon modules based on test paths
- **Module path resolution**: Automatically resolves Odoo addon module paths for proper test discovery
- **Test retry management**: Disables Odoo's built-in test retry mechanism to work seamlessly with pytest
- **Distributed testing support**: Works with pytest-xdist for parallel test execution
- **HTTP server support**: Optional Odoo HTTP server launch for integration tests
- **Actionable config errors**: Surfaces clearer messages when generated Odoo options are invalid

## Installation

```bash
pip install pytest-oduit
```

Note: `pytest-odoo` must not be installed. Also, do not run Odoo module tests from
inside the `pytest-oduit` source directory (it contains Odoo mocks used for this project's own tests).

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
- `--odoo-install`: Control module installation behavior:
  - **Not specified** (default): Automatically detect and install modules based on test paths
  - **`--odoo-install=module1,module2`**: Manually specify modules to install (disables auto-detection)
  - **`--odoo-install=""`**: Disable all module installation
- `--oduit-env`: Path to an oduit config file (if omitted, uses local `.oduit.toml` in current directory)
- `--odoo-http`: Enables http server for testing tours (only needed for Odoo < 18)

### Automatic Module Installation

By default, the plugin automatically detects which addon modules are being tested and initializes them in Odoo. This eliminates the need to manually specify modules for each test run.

**How it works:**

1. Analyzes the test paths provided to pytest
2. Extracts addon names by locating `__manifest__.py` files
3. Automatically appends `--init=<detected_modules>` to the Odoo configuration

**Examples:**

```bash
# Auto-detect and install modules
pytest addons/sale                    # Installs: sale
pytest addons/sale addons/purchase    # Installs: purchase, sale
pytest addons/sale/tests/test_sale.py # Installs: sale

# Manually specify modules (overrides auto-detection)
pytest --odoo-install=sale,purchase addons/crm  # Installs: sale, purchase (NOT crm)

# Disable all module installation
pytest --odoo-install="" addons/sale  # Installs: nothing
```

**When automatic detection activates:**

- A `.oduit.toml` configuration file is present or `--oduit-env` is specified
- `--odoo-install` is not provided (no manual override)

**Supported path types:**

- Addon directories: `addons/my_module`
- Test files: `addons/my_module/tests/test_something.py`
- Subdirectories: `addons/my_module/tests/`
- Multiple addons: `addons/module_a addons/module_b`

### Configuration

The plugin loads configuration from one of these sources:

1. `--oduit-env=/path/to/config.toml` (explicit path)
2. Local `.oduit.toml` in the current working directory

This config is converted into Odoo CLI options and passed to `odoo.tools.config.parse_config()`.
Use valid Odoo option keys (for example, `db_maxconn`, not `db-maxconn`).

Example `.oduit.toml`:

```toml
python_bin = "/path/to/.venv/bin/python"
odoo_bin = "/path/to/odoo/odoo-bin"
db_name = "test_db"
db_user = "odoo"
db_password = "odoo"
db_host = "127.0.0.1"
db_port = 5432
db_maxconn = 64
http_port = 8069
addons_path = ["./addons", "./custom_addons"]
```

Sectioned format is also supported:

```toml
[binaries]
python_bin = "/path/to/.venv/bin/python"
odoo_bin = "/path/to/odoo/odoo-bin"

[odoo_params]
db_name = "test_db"
db_maxconn = 64
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

### Troubleshooting

If startup fails with an error like:

```text
pytest: error: no such option: --db-maxconn
```

check your oduit config key names. Some Odoo DB options use underscores in their CLI names.

- Correct: `db_maxconn` -> `--db_maxconn`
- Incorrect: `db-maxconn` -> `--db-maxconn`

`pytest-oduit` now raises a clearer `pytest.UsageError` for invalid generated Odoo options and includes a hint for common DB option naming mistakes.

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
