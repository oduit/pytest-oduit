# AGENTS.md

This file defines how coding agents should work in the `pytest-oduit` repository.

## 1. Communication

- Assume the user is technically strong.
- Be direct, concrete, and brief.
- Do not explain obvious Python, pytest, or Odoo basics.
- Do not narrate trivial edits.
- Push back on bad ideas when the tradeoff is real.
- Ask a clarifying question only when ambiguity would likely cause the wrong change.
- Otherwise, proceed.

## 2. Working Style

### 2.1 Prefer the smallest correct change

Default to the narrowest change that solves the actual problem.

Priorities:

1. behavior is correct
2. behavior is verified
3. intent is obvious in code
4. changes stay local
5. pytest/Odoo behavior stays stable unless the task requires changing it

Avoid:

- speculative abstractions
- framework-like indirection for a single plugin use case
- broad refactors during bugfix work
- renaming things without payoff
- changing unrelated pytest output
- changing docs for behavior that did not change
- cleanup commits mixed into task work

### 2.2 Preserve existing interfaces unless asked

`pytest-oduit` is a pytest plugin and may be loaded automatically by pytest.
Treat these as stability-sensitive:

- pytest entry point name
- pytest hook behavior
- command-line option names and semantics
- fixture names and scopes
- public imports from `pytest_oduit.py`
- behavior of `.oduit.toml` and `--oduit-env` activation
- generated Odoo option validation and error messages
- Odoo version compatibility branches
- addon/manifest discovery behavior

If a change must break one of these, call it out explicitly.

### 2.3 Solve tasks as verifiable outcomes

Translate requests into a concrete loop:

1. identify the affected plugin surface
2. make the smallest coherent code change
3. verify with the narrowest useful test set
4. widen verification only as needed

Examples:

- plugin autoload bug -> add or update an isolation test, then fix
- command option bug -> test pytest invocation, exit code, and message
- Odoo option generation bug -> test the generated option list and validation path
- addon detection bug -> test manifest/addon path extraction directly
- Odoo version behavior -> test the helper or branch with a focused mock
- docs-only change -> ensure docs describe behavior that exists in code

## 3. Repository-Specific Guidance

### 3.1 What this project is

`pytest-oduit` is a Python package exposing a pytest plugin for running Odoo tests through pytest while using `oduit` configuration and command-building logic.

Important surfaces:

- `pytest_oduit.py` — the plugin implementation
- `pytest_addoption` — pytest CLI option registration
- `pytest_cmdline_main` — Odoo/oduit activation, config loading, Odoo option parsing, server startup
- `pytest_runtest_call` — per-test Odoo integration hooks
- `load_http`, `load_registry`, `enable_odoo_test_flag` — autouse fixtures for active Odoo runs
- `_build_odoo_config_with_oduit_core` — bridge from oduit config to Odoo options
- `_validate_generated_odoo_options` and `_find_unknown_odoo_options` — generated option safety checks
- `_find_manifest_path` and `_extract_addon_name` — addon discovery
- `monkey_patch_resolve_pkg_root_and_module_name` — pytest package-name compatibility for Odoo addons
- `support_subtest` and `disable_odoo_test_retry` — Odoo test-case compatibility patches
- `tests/test_pytest_oduit.py` — primary test coverage
- `tests/mock/odoo/` — fake Odoo package used by tests

When changing behavior, identify which hook/helper owns the concern before editing code.

### 3.2 Respect the activation boundary

The plugin must be inert for ordinary pytest runs that are not Odoo/oduit runs.

Activation should remain explicit and limited to:

- `--oduit-env`
- a detected local `.oduit.toml`

Non-Odoo pytest runs must not require the `odoo` package, must not start Odoo, must not mutate Odoo config, and must not alter collection behavior.

An active Odoo/oduit run without an importable `odoo` package should fail early with a clear `pytest.UsageError` explaining the trigger and remediation.

### 3.3 Keep plugin registration safe

Because pytest plugins can be auto-loaded from installed packages, every hook and autouse fixture must be safe when the run is inactive.

For any new hook, fixture, or import path:

- guard active-only behavior with `_oduit_active(config)` or equivalent
- avoid importing Odoo-only modules unless Odoo is available and the run is active
- avoid changing global pytest or Odoo state during inactive runs
- add or update an autoload-isolation test when touching activation logic

### 3.4 Prefer reusable helper fixes over hook-only patches

When a task starts from pytest behavior, check whether the real fix belongs in a helper.

Good:

- fix addon detection in `_extract_addon_name`
- fix manifest lookup in `_find_manifest_path`
- fix option validation in `_validate_generated_odoo_options`
- fix oduit config bridging in `_build_odoo_config_with_oduit_core`
- add a guard helper and reuse it from multiple hooks/fixtures

Less good:

- patch around a helper bug only inside `pytest_cmdline_main`
- duplicate activation checks with slightly different semantics
- hide option mapping problems behind broad exception handling

### 3.5 Treat generated Odoo options as a contract

Options generated from oduit config are part of the plugin behavior.

When touching option generation or validation:

- preserve existing option names unless the task requires changing them
- validate against Odoo's parser when available
- keep error messages actionable
- include the config source in user-facing failures
- test both valid and invalid generated options
- prefer structured helper tests before full pytest subprocess tests

### 3.6 Keep Odoo side effects deliberate

Active runs can create databases, start Odoo services, patch Odoo test classes, patch pytest package resolution, and modify Odoo config.

Never widen those side effects silently.

Be especially careful with code that can:

- create or drop databases
- start Odoo HTTP/server machinery
- mutate `odoo.tools.config`
- set `threading.current_thread().testing`
- patch `BaseCase.run`, `TestCase.subTest`, or pytest internals
- change addon/module auto-install behavior
- change test collection for non-installable addons

If safety behavior changes, make it explicit in code and tests.

## 4. Testing Expectations

### 4.1 Minimum rule

Every non-trivial behavior change should come with verification.

Prefer the narrowest test that proves the change.

Examples:

- inactive-run bug -> subprocess test with plugin loaded and no `.oduit.toml`
- active-run-without-Odoo bug -> subprocess test blocking `odoo` imports
- option validation bug -> direct helper test with mocked Odoo parser
- addon lookup bug -> direct `_extract_addon_name` or `_find_manifest_path` test
- pytest package resolution bug -> direct monkeypatch test against fake addon layout
- Odoo test-case compatibility bug -> direct test using `tests/mock/odoo`

### 4.2 Test the owned layer first

Prefer tests closest to the changed logic.

- helper fix -> helper unit test
- hook activation change -> subprocess pytest invocation
- CLI option change -> pytest invocation checking exit code and output
- fixture behavior -> focused pytest run only when helper-level coverage is insufficient
- docs-only change -> no code test unless docs exposed a missing behavior guarantee

Do not only test through a full pytest subprocess when the real change is a pure helper.

### 4.3 Verify regressions, not just happy paths

Include error-path checks when relevant:

- no local `.oduit.toml`
- `.oduit.toml` present but Odoo not importable
- invalid generated Odoo option
- malformed or missing manifest
- addon path without a manifest
- non-installable addon collection skip
- pytest node IDs with `::`
- Odoo versions before/after compatibility branches
- xdist worker database-name handling, when touched

### 4.4 Avoid oversized test runs unless necessary

Start narrow. Expand only when the change crosses boundaries.

Typical progression:

1. targeted test class or test function
2. `tests/test_pytest_oduit.py`
3. full suite
4. lint/type checks only when relevant to the touched code

## 5. Pytest Plugin Rules

### 5.1 Preserve command ergonomics

Keep these options stable unless explicitly changing the public contract:

- `--odoo-log-level`
- `--odoo-http`
- `--oduit-env`
- `--odoo-install`

For option changes:

- preserve exit-code behavior
- keep usage errors clear
- test both active and inactive plugin states
- update help text in `pytest_addoption`

### 5.2 Do not make inactive runs pay Odoo costs

Inactive pytest runs must not import Odoo submodules, initialize registries, parse Odoo config, create/drop databases, or patch Odoo/pytest behavior.

Top-level imports should remain defensive. Any Odoo-specific import beyond basic availability detection must be guarded.

### 5.3 Keep collection behavior predictable

`pytest_ignore_collect` should only affect active Odoo/oduit runs.

When changing collection logic:

- do not skip files in inactive runs
- keep non-installable addon handling local to manifest-backed paths
- avoid reading arbitrary parent files outside addon discovery needs
- test with realistic addon directory layouts

## 6. Config and Environment Rules

### 6.1 Respect both activation/config flows

The plugin supports:

- local `.oduit.toml`
- explicit `--oduit-env`

Do not break one workflow while editing the other.

When changing config handling, test source selection and failure messaging.

### 6.2 Validate near the boundary

- detect local config in `_has_oduit_config`
- load/bridge oduit config in `_build_odoo_config_with_oduit_core`
- validate generated Odoo options in `_validate_generated_odoo_options`
- surface user-facing errors through `pytest.UsageError`

Do not scatter config assumptions throughout hooks and fixtures.

### 6.3 Keep dependency failures clear

If `oduit` is missing while an active run needs it, raise a clear pytest usage error.
If `odoo` is missing while an active run needs it, raise a clear pytest usage error.
Inactive runs should not fail because either package is unavailable unless pytest itself requires loading this plugin module from the installed package.

## 7. Odoo-Specific Rules

### 7.1 Distinguish static inspection from runtime execution

Use the least invasive mechanism that solves the task.

Examples:

- need addon name -> use `_extract_addon_name`
- need manifest path -> use `_find_manifest_path`
- need option validation -> use Odoo parser metadata when available
- need runtime registry/server behavior -> keep it inside active-run hooks/fixtures

Do not start Odoo or load registries to solve static path/config questions.

### 7.2 Keep read-only paths read-only

Manifest discovery and option validation should be read-only.
Database creation, server startup, and config mutation belong only in active runtime setup.

### 7.3 Preserve version branches

Odoo compatibility branches are intentional.

When touching version-specific behavior:

- keep `get_odoo_version()` comparable with tuples
- preserve fallback behavior when `odoo.release.version_info` is absent
- test branch behavior with mocks where possible
- do not assume only one Odoo major version is supported

## 8. Documentation Rules

### 8.1 Keep docs aligned with reality

If public behavior changes, update the relevant docs or examples.

Important public behavior includes:

- activation rules
- required dependencies for active Odoo runs
- pytest options
- `.oduit.toml` / `--oduit-env` behavior
- addon auto-install behavior from test paths
- behavior when Odoo is unavailable

Do not add aspirational docs that describe behavior the code does not implement.

### 8.2 Examples should be executable in spirit

Keep examples realistic and consistent with current pytest option names and expected output.

## 9. Code Style Rules

- Follow the existing repository style first.
- Keep functions focused.
- Prefer explicit names over compressed cleverness.
- Add type hints for new or changed public helpers.
- Use docstrings where surrounding code expects them.
- Avoid introducing new dependencies unless explicitly requested.
- Do not reformat unrelated files.
- Do not rename public symbols without a strong reason.
- Do not use git commands or create commits.

## 10. Preferred Verification Commands

Use the narrowest relevant commands first.

```bash
# Run all tests
pytest

# Run the primary test file
pytest tests/test_pytest_oduit.py

# Run a specific test class
pytest tests/test_pytest_oduit.py::TestPluginAutoloadIsolation

# Run a specific test
pytest tests/test_pytest_oduit.py::TestPluginAutoloadIsolation::test_plain_pytest_run_is_inert_without_oduit_config

# Lint
ruff check --fix --exit-non-zero-on-fix --config=.ruff.toml

# Format
ruff format

# Type-check, if mypy is configured or requested
mypy pytest_oduit.py
```

Notes:

- Prefer targeted `pytest` invocation before running the full suite.
- Run isolation tests when touching plugin activation, imports, hooks, or autouse fixtures.
- Run option-validation tests when touching oduit/Odoo config bridging.
- Run `ruff check` and relevant tests before finishing.
- Do not install packages unless the user explicitly asks.

## 11. Packaging Rules

The package exposes one pytest plugin module.

Protect these packaging assumptions:

- package name: `pytest-oduit`
- Python module: `pytest_oduit`
- pytest entry point group: `pytest11`
- pytest plugin entry point: `odoo = pytest_oduit`
- runtime dependencies remain minimal

Do not add package data, new plugin modules, or new runtime dependencies without a concrete reason.

## 12. What good agent work looks like here

A strong change in this repo usually has these properties:

- preserves inactive pytest behavior
- edits the right helper or hook
- keeps active Odoo behavior explicit
- adds or updates focused tests
- preserves pytest option semantics
- keeps generated Odoo option errors actionable
- avoids Odoo side effects outside active runs
- updates docs when public behavior changes
- stays small unless a larger redesign is actually required

## 13. What to avoid

- making ordinary pytest runs require Odoo
- importing Odoo submodules during inactive runs
- changing global pytest/Odoo state before activation is known
- fixing helper problems only in hook wrappers
- changing option names or error behavior without tests
- mixing refactors with feature work
- broad style churn
- introducing abstraction layers for hypothetical future plugins
- starting Odoo for static manifest/addon inspection
- adding behavior without documenting or testing the public contract
