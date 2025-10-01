# pytest-oduit

A pytest plugin for running Odoo tests with enhanced functionality and integration with oduit-core.

## Features

- **Automatic Odoo configuration**: Integrates with `.oduit.toml` configuration files using oduit-core
- **Module path resolution**: Automatically resolves Odoo addon module paths for proper test discovery
- **Test retry management**: Disables Odoo's built-in test retry mechanism to work seamlessly with pytest
- **Distributed testing support**: Works with pytest-xdist for parallel test execution
- **HTTP server support**: Optional Odoo HTTP server launch for integration tests

## Installation

```bash
pip install pytest-oduit
```

## Requirements

- Python >= 3.9
- pytest >= 8
- oduit
- Odoo (any supported version)

## Usage

### Basic Usage

Simply run pytest in your Odoo addon directory:

```bash
pytest
```

### Other pytest plugins

This plugin works also together `pytest-subtests` and `pytest-xdist`.

### Command Line Options

- `--odoo-log-level`: Set the log level for Odoo processes during tests (default: 'critical')
- `--odoo-http`: Launch an Odoo HTTP server during tests
- `--odoo-dev`: Development mode options

### Configuration

The plugin automatically detects and uses `.oduit.toml` configuration files when available. This provides seamless integration with oduit-core for database configuration, addon paths, and other Odoo settings.

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

- Holger Nahrstaedt <holger.nahrstaedt@hasomed.de>
- Based on original work by Pierre Verkest and Camptocamp SA

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.
