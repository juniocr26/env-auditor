# ENV Auditor

A standalone Python CLI for auditing, synchronizing, and cleaning `.env`, `.env.*`, and `.env.example` files across projects in a workspace.

ENV Auditor keeps all environment files within the same project consistent with a shared `.env.example`, detects potentially unused variables, removes stale configuration, and helps reduce the risk of accidentally exposing sensitive values.

The tool is designed to work without external Python dependencies and never prints environment variable values.

## Features

- Automatically discovers `.env`, `.env.*`, and `.env.example` files.
- Supports any environment file matching `.env.*`, including:
  - `.env.prod`
  - `.env.test`
  - `.env.local`
  - `.env.dev`
  - `.env.qa`
  - `.env.staging`
  - `.env.production`
  - `.env.docker`
  - custom environment names
- Treats all `.env` / `.env.*` files in the same directory as environments of the same project.
- Uses a single `.env.example` as the environment contract for each project.
- Synchronizes the union of environment keys into `.env.example`.
- Synchronizes `.env.example` keys back into every existing environment file.
- Never copies real values from `.env` / `.env.*` into `.env.example`.
- Creates `.env.example` when only environment files exist.
- Can create `.env` from `.env.example` when no environment file exists.
- Detects duplicate keys.
- Detects possible secrets stored in `.env.example`.
- Searches runtime and configuration files for environment variable references.
- Classifies variable usage as strong, weak, or potentially unused.
- Automatically removes variables with no detected usage.
- Preserves variables with weak usage evidence.
- Supports explicit exclusions for externally managed variables.
- Creates backups before modifying existing files.
- Supports safe simulation with `--dry-run`.
- Supports read-only analysis with `--audit-only`.
- Never prints environment variable values.

## Project Structure

The executable script is located at:

```text
scripts/audit-envs.py
```

A project being audited may look like this:

```text
project/
├── .env
├── .env.prod
├── .env.test
├── .env.local
├── .env.example
├── .env-audit.json
└── scripts/
    └── audit-envs.py
```

The following files are treated as real environment files:

```text
.env
.env.*
```

Special files are excluded, including:

```text
.env.example
.env*.bak.*
```

This means files such as:

```text
.env.test
.env.qa
.env.production
.env.my-environment
```

are discovered automatically without additional configuration.

## How It Works

Each directory containing environment files is treated as one project.

```text
                 ┌── .env
                 ├── .env.prod
.env.example  ←→ ├── .env.test
                 ├── .env.local
                 └── .env.staging
```

The `.env.example` file represents the complete set of expected environment variable keys for that project.

Real values remain isolated inside each environment file and are never propagated from one real environment to another.

## Requirements

- Python 3.10 or newer
- Read access to the projects being audited
- Write access for normal execution

No external Python packages are required.

## Basic Usage

Run the auditor from the workspace root:

```bash
python3 scripts/audit-envs.py
```

By default, ENV Auditor:

1. discovers `.env`, `.env.*`, and `.env.example` files;
2. groups environment files by project directory;
3. synchronizes environment keys into `.env.example`;
4. synchronizes `.env.example` keys into each environment file;
5. detects duplicate keys and possible secrets;
6. searches the project for environment variable references;
7. classifies variables by usage evidence;
8. automatically removes variables with no detected usage;
9. reports which variables were removed and from which files.

Unused-variable cleanup is part of the default behavior.

There is no separate `--remove-unused` option.

## Environment File Discovery

Any file matching:

```text
.env.*
```

is treated as a real environment file unless explicitly excluded.

Examples:

```text
.env.prod
.env.test
.env.local
.env.dev
.env.qa
.env.staging
.env.production
.env.docker
.env.custom
```

The regular `.env` file is also supported.

`.env.example` is handled separately as the reference file for the project.

Backups created by ENV Auditor are ignored during discovery.

## Synchronizing Multiple Environments

Consider the following project:

```text
project/
├── .env
├── .env.prod
├── .env.test
└── .env.example
```

Suppose the files contain these keys:

```text
.env
APP_NAME
LOCAL_ONLY

.env.prod
APP_NAME
PROD_ONLY

.env.test
APP_NAME
TEST_ONLY

.env.example
APP_NAME
FROM_EXAMPLE
```

After synchronization, all environment files and `.env.example` will contain the same key set:

```text
APP_NAME
LOCAL_ONLY
PROD_ONLY
TEST_ONLY
FROM_EXAMPLE
```

The values are not synchronized between real environment files.

### Values are handled differently depending on direction

When a key is discovered in a real environment file and does not exist in `.env.example`, only the key is added:

```env
MY_VARIABLE=
```

The real value is never copied.

When a key exists in `.env.example` but is missing from a real environment file, the corresponding block from `.env.example` may be copied into that environment.

This allows safe defaults from `.env.example` to be propagated without copying secrets between real environments.

## Key Exists in an Environment but Not in `.env.example`

If a variable exists in:

```text
.env
.env.prod
.env.test
.env.local
```

but does not exist in `.env.example`, ENV Auditor adds only the key:

```env
MY_VARIABLE=
```

The original environment value is never copied.

## Key Exists in `.env.example` but Not in an Environment

Suppose `.env.example` contains:

```env
APP_TIMEZONE=UTC
```

and `.env.prod` does not contain `APP_TIMEZONE`.

The corresponding block from `.env.example` is added to `.env.prod`.

Synchronization is performed independently for every environment file.

## Environment-Specific Keys

A variable may initially exist in only one environment.

For example:

```text
.env
APP_NAME=...

.env.prod
APP_NAME=...
PROD_SPECIAL=real-value

.env.example
APP_NAME=
```

ENV Auditor first adds the key to `.env.example`:

```env
PROD_SPECIAL=
```

The key can then be propagated to the other environments from the safe `.env.example` representation.

The real value from `.env.prod` is never copied to another environment.

## Creating `.env.example`

If a project contains environment files but no `.env.example`:

```text
.env
.env.prod
.env.test
```

ENV Auditor creates `.env.example` using the union of all discovered keys.

Given:

```text
.env
A=value
B=value

.env.prod
A=value
C=value

.env.test
A=value
D=value
```

the generated `.env.example` contains:

```env
A=
B=
C=
D=
```

No real values are copied.

## Creating `.env`

If a project contains only:

```text
.env.example
```

ENV Auditor can create:

```text
.env
```

from `.env.example`, provided that no potentially real secret is detected in the example file.

The tool does not automatically create `.env.prod`, `.env.test`, or other environment-specific files that did not already exist.

## Automatic Cleanup

During normal execution:

```bash
python3 scripts/audit-envs.py
```

ENV Auditor automatically removes variables for which no strong or weak usage evidence was found.

Removal is applied to:

```text
.env
.env.*
.env.example
```

wherever the key is present.

Variables with weak usage evidence are preserved.

Variables listed under:

```json
"ignore_unused_keys"
```

are also preserved.

## Example Cleanup

A normal execution may produce output similar to:

```text
REMOVING automatically detected unused variables:

    - LEGACY_FEATURE_FLAG
    - OLD_WORKER_COUNT

REMOVED BY FILE:

    .env:
      - LEGACY_FEATURE_FLAG
      - OLD_WORKER_COUNT

    .env.example:
      - LEGACY_FEATURE_FLAG
      - OLD_WORKER_COUNT

    .env.prod:
      - LEGACY_FEATURE_FLAG
      - OLD_WORKER_COUNT
```

ENV Auditor reports variable names only.

Environment values are never printed.

> Note: the current CLI implementation may display some status labels in Portuguese. The behavior described here remains the same.

## Dry Run

To preview all synchronization and cleanup operations without modifying files:

```bash
python3 scripts/audit-envs.py --dry-run
```

`--dry-run` simulates:

- environment discovery;
- `.env.example` creation;
- `.env` creation from `.env.example`;
- key synchronization;
- unused-variable detection;
- automatic cleanup.

No files are changed.

This is the recommended mode before running ENV Auditor against an existing project for the first time.

## Audit-Only Mode

To inspect a project without synchronizing or modifying anything:

```bash
python3 scripts/audit-envs.py --audit-only
```

In this mode:

- no files are created;
- no variables are added;
- no variables are removed;
- no files are modified.

Potentially unused variables are reported only.

`--audit-only` cannot be combined with `--dry-run`.

## Showing Usage Evidence

Use:

```bash
python3 scripts/audit-envs.py --show-usage
```

to display the files where usage evidence was found.

Example:

```text
USO_FORTE DB_HOST: docker-compose.yml, config/database.php
USO_FRACO FEATURE_FLAG_X: config/custom.php
```

It can also be combined with:

```bash
python3 scripts/audit-envs.py --dry-run --show-usage
```

or:

```bash
python3 scripts/audit-envs.py --audit-only --show-usage
```

## Usage Detection

ENV Auditor separates references into three categories.

### Strong Usage

Strong usage is detected when a variable is referenced using a recognized environment-access pattern.

PHP / Laravel:

```php
env('DB_HOST')
```

Shell and Docker Compose:

```bash
${DB_HOST}
$DB_HOST
```

Node.js:

```javascript
process.env.DB_HOST;
process.env["DB_HOST"];
```

Vite:

```javascript
import.meta.env.VITE_API_URL;
```

Python:

```python
os.getenv("DB_HOST")
os.environ["DB_HOST"]
```

Java / Kotlin:

```java
System.getenv("DB_HOST")
```

The auditor also recognizes several environment helper functions:

```text
getRequiredEnv
getEnv
getNumberEnv
getListEnv
getRequiredEnvFrom
getNumberEnvFrom
getListEnvFrom
```

Variables with strong usage evidence are preserved.

### Weak Usage

Weak usage means the exact variable name was found in a searchable runtime or configuration file, but the reference did not match a recognized strong-usage pattern.

Example:

```text
USO_APENAS_FRACO:
    - MY_VARIABLE
```

Weakly referenced variables are preserved automatically.

This conservative behavior helps prevent accidental removal when variables are accessed indirectly or through unsupported patterns.

### Potentially Unused

If no strong or weak reference is found, the variable is classified as potentially unused.

In audit-only mode:

```text
POSSIVELMENTE_SEM_USO:
    - LEGACY_VARIABLE
```

During normal execution, these variables are automatically removed from all relevant environment files.

## Environment Files Are Not Usage Evidence

Environment files themselves are configuration sources, not evidence that a variable is actually consumed by the application.

For this reason, files such as:

```text
.env
.env.prod
.env.test
.env.local
.env.example
```

are excluded from usage analysis.

This prevents a variable from being considered "in use" simply because it is declared in another environment file.

## Execution Flow

A normal execution follows this general flow:

```text
Discover projects
        ↓
Discover .env / .env.*
        ↓
Read .env.example
        ↓
Validate potential secrets
        ↓
Build the union of environment keys
        ↓
Synchronize keys into .env.example
        ↓
Synchronize .env.example into each environment
        ↓
Search runtime/configuration files
        ↓
Classify usage
        ↓
Preserve strong usage
        ↓
Preserve weak usage
        ↓
Preserve ignore_unused_keys
        ↓
Remove variables with no usage evidence
        ↓
Reload modified files
        ↓
Validate final key parity
```

## Project-Level Output

When environment files are discovered, ENV Auditor reports which files belong to the project.

Example:

```text
[my-project]
  Environment files: .env, .env.local, .env.prod, .env.test
```

This makes it easier to confirm that custom files such as `.env.test` or `.env.qa` were discovered correctly.

## Key Parity Validation

Parity is checked between:

```text
.env.example
```

and every real environment file in the same project.

The current CLI reports structural conditions using labels such as:

```text
FALTANDO_NO_EXAMPLE
EXAMPLE_SEM_CHAVE_NO_AMBIENTE
DUPLICADAS
POSSIVEL_SECRET_NO_EXAMPLE
```

### `FALTANDO_NO_EXAMPLE`

A key exists in at least one real environment file but not in `.env.example`.

### `EXAMPLE_SEM_CHAVE_NO_AMBIENTE`

A key exists in `.env.example` but is missing from one or more real environment files.

### `DUPLICADAS`

A key appears more than once in the same file.

### `POSSIVEL_SECRET_NO_EXAMPLE`

A sensitive-looking variable contains a value in `.env.example` that may represent a real credential.

## Secret Protection

ENV Auditor checks sensitive-looking variable names containing terms such as:

```text
SECRET
PASSWORD
PASS
TOKEN
PRIVATE
CREDENTIAL
CREDENTIALS
CLIENT_SECRET
APP_KEY
API_KEY
```

Common placeholder values are accepted, including:

```text
change
changeme
placeholder
example
dummy
fake
your_...
xxx
<value>
false
true
0
1
null
base64:
```

If a sensitive-looking variable contains a value that appears to be real, synchronization may be blocked.

Secret validation is applied to `.env.example`.

Real `.env` / `.env.*` values are not inspected for propagation and are never printed.

## Backups

Before modifying existing files, ENV Auditor creates backups under:

```text
.env-audit-backups/
```

Example:

```text
.env-audit-backups/
└── my-project/
    ├── .env.20260911_083500_123456.bak
    ├── .env.prod.20260911_083500_234567.bak
    ├── .env.test.20260911_083500_345678.bak
    └── .env.example.20260911_083500_456789.bak
```

Backup files receive `0600` permissions when supported by the operating system.

To disable backups:

```bash
python3 scripts/audit-envs.py --no-backup
```

Use this option only when necessary.

## Strict Mode

Use:

```bash
python3 scripts/audit-envs.py --strict
```

to return exit code `1` when structural problems remain.

Strict mode considers conditions such as:

- missing `.env.example`;
- missing real environment files;
- key divergence;
- duplicate variables;
- possible secrets in `.env.example`.

To also treat variables with no detected references as failures:

```bash
python3 scripts/audit-envs.py --strict --strict-unused
```

`--strict-unused` requires `--strict`.

Because normal execution removes completely unused variables, successfully removed variables do not remain as final strict-mode issues.

## Auditing Another Directory

By default, ENV Auditor uses the current directory:

```bash
python3 scripts/audit-envs.py
```

A different workspace root can be provided:

```bash
python3 scripts/audit-envs.py /path/to/workspace
```

Dry run:

```bash
python3 scripts/audit-envs.py /path/to/workspace --dry-run
```

Audit only:

```bash
python3 scripts/audit-envs.py /path/to/workspace --audit-only
```

## CLI Options

```text
--strict
    Return exit code 1 when structural issues remain.

--strict-unused
    Used together with --strict.
    Also fails when a variable has no detected usage.

--audit-only
    Analyze only.
    Do not synchronize or remove variables.

--dry-run
    Simulate synchronization and cleanup without modifying files.

--no-backup
    Disable backups before modifying existing files.

--show-usage
    Show files containing strong or weak usage evidence.
```

There is no `--remove-unused` option.

Removing completely unused variables is part of the default execution behavior.

## Configuration

An optional configuration file can be created at the workspace root:

```text
.env-audit.json
```

Example:

```json
{
  "public_non_secret_keys": ["PUBLIC_CLIENT_KEY"],
  "ignore_unused_keys": ["EXTERNALLY_MANAGED_VARIABLE"],
  "ignore_projects": ["legacy-project"],
  "ignore_files": ["generated/config.js"]
}
```

The `.env-audit.json` file itself is excluded from usage detection to prevent false positives.

### `public_non_secret_keys`

Some variable names may look sensitive even though their values are intentionally public.

Those keys can be explicitly allowed:

```json
{
  "public_non_secret_keys": ["PUBLIC_CLIENT_KEY"]
}
```

### `ignore_unused_keys`

Some variables may be consumed outside the source tree and therefore cannot be detected through static scanning.

Example:

```json
{
  "ignore_unused_keys": ["SERVER_INJECTED_VARIABLE"]
}
```

These variables:

- are not treated as unused;
- are not automatically removed from environment files;
- are not removed from `.env.example`.

This is useful for variables provided by systems such as:

- CI/CD pipelines;
- GitHub Actions;
- GitLab CI;
- Docker Swarm;
- Kubernetes;
- systemd;
- deployment platforms;
- external scripts;
- server configuration;
- another application or service.

### `ignore_projects`

Entire directories can be excluded from discovery:

```json
{
  "ignore_projects": ["legacy-project"]
}
```

### `ignore_files`

Specific files can be excluded from usage scanning:

```json
{
  "ignore_files": ["generated/config.js"]
}
```

## Ignored Directories

The following directories are ignored by default:

```text
.git
.idea
.vscode
.env-audit-backups
node_modules
storage
vendor
__pycache__
bootstrap/cache
public/build
```

Documentation, binary files, and common assets are also excluded.

Examples:

```text
.png
.jpg
.jpeg
.gif
.webp
.ico
.pdf
.zip
.gz
.tar
.tgz
.7z
.woff
.woff2
.ttf
.otf
.mp3
.mp4
.wav
.ogg
.webm
.jar
.class
.so
.dylib
.dll
.exe
.sqlite
.db
```

## Important Limitation of Static Usage Detection

A variable may not appear in the project's source code and still be required at runtime.

Examples include variables injected by:

- CI/CD systems;
- GitHub Actions;
- GitLab CI;
- Kubernetes;
- Docker Swarm;
- systemd;
- hosting providers;
- infrastructure outside the workspace;
- external deployment scripts;
- another service.

When that happens, add the key to:

```json
"ignore_unused_keys"
```

For example:

```json
{
  "ignore_unused_keys": ["EXTERNAL_VARIABLE", "SERVER_MANAGED_VARIABLE"]
}
```

This prevents ENV Auditor from removing those variables.

## Environment-Specific Configuration

ENV Auditor intentionally keeps key parity between `.env.example` and all `.env` / `.env.*` files in the same directory.

As a result, a key initially found only in `.env.prod` may be:

1. added to `.env.example` with an empty value;
2. propagated as a key to other environment files.

This is intentional.

`.env.example` acts as the complete environment-variable contract for the project.

The real production value is never propagated.

If a variable should not participate in that contract, consider whether it belongs in an environment file managed by ENV Auditor.

## Recommended Workflow

Before modifying an existing project, run:

```bash
python3 scripts/audit-envs.py --dry-run --show-usage
```

Review discovered environments and planned changes.

Then run:

```bash
python3 scripts/audit-envs.py
```

Optionally, perform a read-only verification afterward:

```bash
python3 scripts/audit-envs.py --audit-only --show-usage
```

## Security Notes

ENV Auditor is designed to avoid printing environment variable values.

However, environment management still requires care:

- never commit `.env` or `.env.*` files containing real credentials;
- keep only safe values and placeholders in `.env.example`;
- keep backups enabled unless there is a specific reason not to;
- use `--dry-run` before applying changes to unfamiliar projects;
- use `ignore_unused_keys` for externally consumed variables;
- review weak usage when necessary;
- do not assume that absence of a source-code reference proves a variable is unnecessary.

A safe workflow is:

```bash
# 1. Preview synchronization, cleanup, and usage evidence
python3 scripts/audit-envs.py --dry-run --show-usage

# 2. Review discovered environment files and planned changes

# 3. Apply synchronization and cleanup
python3 scripts/audit-envs.py

# 4. Optionally verify the final state without modifying anything
python3 scripts/audit-envs.py --audit-only --show-usage
```

## Summary

ENV Auditor maintains a consistent set of environment files without propagating real values between environments.

It supports:

```text
.env
.env.*
```

including files such as:

```text
.env.prod
.env.test
.env.local
.env.staging
.env.production
```

with:

```text
.env.example
```

acting as the shared environment-variable contract.

A normal execution:

```bash
python3 scripts/audit-envs.py
```

performs:

```text
environment discovery
        +
project grouping
        +
.env.example synchronization
        +
environment synchronization
        +
structural validation
        +
usage detection
        +
weak-reference preservation
        +
explicit exclusion preservation
        +
unused-variable cleanup
        +
backups
```

To preview all changes without modifying files:

```bash
python3 scripts/audit-envs.py --dry-run
```

To inspect the workspace without synchronization or cleanup:

```bash
python3 scripts/audit-envs.py --audit-only
```
