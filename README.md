# GitLab Secrets Manager

A powerful command-line tool for managing GitLab CI/CD variables (secrets) with ease. This tool provides a simple and intuitive interface for creating, reading, updating, deleting, and downloading GitLab secrets.

## Features

- ✅ **Create** new GitLab secrets with various options (protected, masked, raw)
- 📖 **Read** existing GitLab secrets to view their details
- ✏️ **Update** existing GitLab secrets
- 🗑️ **Delete** GitLab secrets with confirmation
- 📥 **Download** GitLab secrets in JSON or .env format
- 🔄 **Sort** downloaded secrets alphabetically, by creation time, or other criteria
- 📄 **Automatic Pagination** - Handles GitLab's pagination automatically to fetch all secrets
- 🎨 **Beautiful CLI** with rich formatting and colors
- 📝 **Well-documented** codebase with comprehensive comments

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd git-secrets-manager
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```bash
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_personal_access_token
GITLAB_PROJECT_ID=your_project_id
```

## Getting Your GitLab Token

1. Go to your GitLab profile: `Settings > Access Tokens`
2. Create a new personal access token with the following scopes:
   - `api` - Full API access
3. Copy the token and add it to your `.env` file

## Getting Your Project ID

You can find your project ID in the GitLab project settings under "General" or check the URL when viewing your project.

## Usage

### Create Secrets

```bash
# Create a single variable
python gitlab_secrets.py create KEY_NAME "value"

# With options
python gitlab_secrets.py create KEY_NAME "value" --protected --masked --raw

# Upsert: create if new, update if exists
python gitlab_secrets.py create KEY_NAME "value" --upsert

# Bulk create from file
python gitlab_secrets.py create --file variables.json
python gitlab_secrets.py create --file .env.production

# Bulk upsert: creates or updates existing variables
python gitlab_secrets.py create --file variables.json --upsert
```

### Read a Secret

```bash
python gitlab_secrets.py read KEY_NAME
```

### Update Secrets

```bash
# Update a single variable
python gitlab_secrets.py update KEY_NAME "new_value"

# Update other properties
python gitlab_secrets.py update KEY_NAME "new_value" --protected true --masked false

# Update environment scope
python gitlab_secrets.py update KEY_NAME "new_value" --environment-scope staging

# Bulk update from file
python gitlab_secrets.py update --file updates.json
python gitlab_secrets.py update --file .env.updates
```

### Delete a Secret

```bash
python gitlab_secrets.py delete KEY_NAME
```

### List All Secrets

```bash
# List all secrets sorted by key (default)
python gitlab_secrets.py list

# Sort by different fields
python gitlab_secrets.py list --sort protected
python gitlab_secrets.py list --sort masked --reverse

# Show values (careful with sensitive data!)
python gitlab_secrets.py list --show-values

# Filter by key pattern (regex supported)
python gitlab_secrets.py list --filter "API.*"
python gitlab_secrets.py list --filter "DATABASE_" --show-values
python gitlab_secrets.py list --filter "^DB_" --sort key
```

### Download Secrets

```bash
# Download as YAML simple format (default)
python gitlab_secrets.py download

# Download as YAML simple format with custom name
python gitlab_secrets.py download --simple --output myvars.yml
python gitlab_secrets.py download --simple --output backup.yaml

# Download as YAML structured format with custom name
python gitlab_secrets.py download --structured --output vars.yml
python gitlab_secrets.py download --structured --output full-backup.yaml

# Download as JSON (format auto-detected from .json extension)
python gitlab_secrets.py download --output backup.json

# Download as .env file (format auto-detected from .env extension)
python gitlab_secrets.py download --output backup.env

# Or explicitly specify format
python gitlab_secrets.py download --format json --output backup.json
python gitlab_secrets.py download --format env --output backup.env

# Include actual values (use with caution!)
python gitlab_secrets.py download --include-values

# Sort by different criteria
python gitlab_secrets.py download --sort protected --reverse

# Download only specific variables by filter pattern
python gitlab_secrets.py download --filter "API.*" --output api-vars.yaml
python gitlab_secrets.py download --filter "DATABASE_" --include-values
python gitlab_secrets.py download --filter "^PROD_" --output prod-vars.env
```

## Project Structure

The project is organized into well-documented modules:

- **`gitlab_secrets.py`** - Command-line interface with comprehensive comments explaining each command
- **`gitlab_client.py`** - GitLab API client with detailed docstrings for all methods
- **`config.py`** - Configuration management with inline comments explaining each setting
- **`requirements.txt`** - Python dependencies
- **`setup.py`** - Package setup for distribution
- **`QUICKSTART.md`** - Quick start guide for new users

## Code Documentation

All Python files include:
- **Module-level docstrings** explaining the purpose and usage
- **Class docstrings** with attributes and examples
- **Function docstrings** with parameters, return values, and exceptions
- **Inline comments** explaining complex logic and important decisions
- **Type hints** for better code clarity

## Output Formats

### YAML Format (Default)

The tool supports two YAML formats with automatic multiline string formatting:

**1. Structured Format** - Contains metadata and all properties:
```yaml
variables:
  - key: API_KEY
    protected: false
    masked: true
    raw: false
    environment_scope: "*"
    value: your_value_here
total: 1
sorted_by: key
```

**2. Simple Format (Default)** - Just key-value pairs:
```yaml
# GitLab CI/CD Variables
# Total: 1
# Sorted by: key

API_KEY: your_value_here
DATABASE_URL: postgresql://localhost/db
```

**Multiline Strings:**
Long values and values with newlines are automatically formatted using YAML's literal block style (`|`):
```yaml
DATABASE_URL: |
  postgres://user:password@localhost:5432/dbname
  ?sslmode=require&application_name=MyApp
```

**Format Auto-Detection:**
The format is automatically detected from the file extension when `--output` is specified:
- `.yml` or `.yaml` → YAML format
- `.json` → JSON format
- `.env` → .env format

**Note:** If both `--format` and `--output` with an extension are specified, the file extension takes precedence. This ensures the output file format matches its extension.

**How to choose:**
- Default: `python gitlab_secrets.py download` → Creates simple format in `secrets.yml` (default)
- Simple YAML: `python gitlab_secrets.py download --simple --output filename.yml` → Just key-value pairs
- Structured YAML: `python gitlab_secrets.py download --structured --output filename.yml` → Full metadata
- JSON: `python gitlab_secrets.py download --output filename.json` → JSON format (auto-detected)
- .env: `python gitlab_secrets.py download --output filename.env` → .env format (auto-detected)
- Format override: `python gitlab_secrets.py download --format json --output data.txt` → Uses `--format` value (no extension detected)

### JSON Format
```json
{
  "variables": [
    {
      "key": "API_KEY",
      "protected": false,
      "masked": true,
      "raw": false,
      "environment_scope": "*"
    }
  ],
  "total": 1,
  "sorted_by": "key"
}
```

**Note:** JSON format uses standard JSON encoding. Multiline values are represented with escaped newlines (`\n`) to maintain valid JSON format. The tool automatically formats nested JSON content within values for better readability while preserving JSON validity.

### ENV Format
```env
# GitLab CI/CD Variables
# Total: 1
# Sorted by: key

API_KEY=your_value_here
```

## Examples

### Example Workflow

```bash
# 1. Create a secret
python gitlab_secrets.py create DATABASE_URL "postgresql://localhost:5432/mydb" --protected

# 2. Read it back
python gitlab_secrets.py read DATABASE_URL

# 3. Update it
python gitlab_secrets.py update DATABASE_URL "postgresql://localhost:5432/newdb"

# 4. List all secrets
python gitlab_secrets.py list

# 5. Download all secrets
python gitlab_secrets.py download --output backup.json

# 6. Delete a secret
python gitlab_secrets.py delete DATABASE_URL
```

### Bulk Operations

**Bulk Create/Update:**

Create files in YAML, JSON, or .env format:

**YAML format:**
```yaml
variables:
  - key: API_KEY
    value: secret123
    protected: true
    masked: true
  - key: DATABASE_URL
    value: postgresql://localhost/db
```

**JSON format:**
```json
{
  "variables": [
    {
      "key": "API_KEY",
      "value": "secret123",
      "protected": true,
      "masked": true
    },
    {
      "key": "DATABASE_URL",
      "value": "postgresql://localhost/db"
    }
  ]
}
```

**Or as .env file:**
```env
API_KEY=secret123
DATABASE_URL=postgresql://localhost/db
```

**Note on .env File Format:**
The tool uses a simple parser for .env files. This means:
- ✅ Simple `KEY=VALUE` pairs are supported
- ✅ Comments (lines starting with `#`) are ignored
- ✅ Empty lines are skipped
- ✅ Whitespace around keys and values is stripped
- ❌ Variable expansion/interpolation (e.g., `${VAR}`) is not supported - values are treated literally
- ❌ Quoted values (single or double quotes) are preserved as-is - quotes become part of the value
- ❌ Multiline values are not supported - each line is processed independently
- ❌ Escaped characters are treated literally (e.g., `\n` stays as backslash-n, not a newline)
- ❌ Variables without values (e.g., `KEY` without `=`) are ignored

For advanced features like variable expansion or multiline values, use YAML or JSON format instead.

Then use:
```bash
# Bulk create
python gitlab_secrets.py create --file variables.yaml
python gitlab_secrets.py create --file variables.json
python gitlab_secrets.py create --file .env.production

# Bulk update
python gitlab_secrets.py update --file updates.yaml
python gitlab_secrets.py update --file updates.json
python gitlab_secrets.py update --file .env.updates
```

**Bulk Download:**

```bash
# Download to JSON
python gitlab_secrets.py download --include-values --output secrets.json

# Download to .env format
python gitlab_secrets.py download --format env --include-values --output .env.backup

# Download filtered variables
python gitlab_secrets.py download --filter "API.*" --include-values --output api-vars.json
```

**Bulk Operation Output:**

When performing bulk operations, the tool shows real-time progress for each variable:

```bash
python gitlab_secrets.py create --file variables.yaml
  ✓ Created: API_KEY
  ✓ Created: DATABASE_URL
  ✗ DUPLICATE_KEY: 409 Conflict - Variable already exists
  ✓ Created: NEW_SECRET

Successfully created: 3
Failed: 1
```

**With Upsert Mode:**

When using `--upsert`, existing variables are automatically updated:

```bash
python gitlab_secrets.py create --file variables.yaml --upsert
  ✓ Created: API_KEY
  ✓ Created: DATABASE_URL
  🔄 Updated: DUPLICATE_KEY (already exists)
  ✓ Created: NEW_SECRET

Successfully created: 4
Failed: 0
```

This output shows that 4 variables were processed: 3 were newly created, and 1 was updated because it already existed. The upsert mode ensures idempotent operations.

## Command Reference

| Command | Description |
|---------|-------------|
| `create KEY VALUE` | Create a new secret |
| `read KEY` | Read a secret |
| `update KEY VALUE` | Update a secret |
| `delete KEY` | Delete a secret |
| `list` | List all secrets |
| `download` | Download all secrets |

### Options

#### Create Options
- `--protected` - Mark variable as protected
- `--masked` - Mask variable in job logs
- `--raw` - Treat variable as raw (no expansion)
- `--environment-scope SCOPE` - Environment scope (default: * for all environments)
- `--file` / `-f` - Bulk create from file (YAML, JSON, or .env format)
- `--upsert` - Create if new, update if already exists (no error on conflict)

#### Update Options
- `--protected BOOL` - Set protected status (true/false)
- `--masked BOOL` - Set masked status (true/false)
- `--raw BOOL` - Set raw status (true/false)
- `--environment-scope SCOPE` - Set environment scope (e.g., production, staging, *)
- `--file` / `-f` - Bulk update from file (YAML, JSON, or .env format)

#### List Options
- `--sort FIELD` - Sort by field (key, protected, masked, raw)
- `--reverse` - Reverse sort order
- `--show-values` - Display variable values (⚠️ use with caution for sensitive data)
- `--filter PATTERN` / `-f PATTERN` - Filter variables by key pattern (regex supported)

#### Download Options
- `--output FILE` / `-o FILE` - Output file path (format inferred from extension if present)
- `--format FORMAT` - Output format (yaml, json, env) - default: inferred from file extension. Note: If both `--format` and `--output` with extension are specified, the file extension takes precedence.
- `--simple` - Use simple YAML format (key-value pairs, default for YAML)
- `--structured` - Use structured YAML format (with metadata)
- `--sort FIELD` - Sort by field (key, protected, masked, raw)
- `--reverse` - Reverse sort order
- `--include-values` - Include variable values in output (⚠️ use with caution)
- `--filter PATTERN` / `-f PATTERN` - Filter variables by key pattern (regex supported)

## Security Notes

- ⚠️ Never commit your `.env` file to version control
- ⚠️ The `.env` file is already included in `.gitignore`
- ⚠️ Use `--include-values` flag carefully when downloading secrets
- ⚠️ Use `--show-values` flag carefully when listing secrets (values are hidden by default)
- ⚠️ Protect your GitLab personal access token
- ⚠️ Use protected variables for sensitive secrets
- ⚠️ Values are hidden by default in the `list` command to prevent accidental exposure

## Troubleshooting

### Authentication Error
- Verify your `GITLAB_TOKEN` is correct and has the `api` scope
- Check that your token hasn't expired

### Project Not Found
- Verify your `GITLAB_PROJECT_ID` is correct
- Ensure your token has access to the project

### Permission Denied
- Check that your token has the necessary permissions
- For protected variables, ensure your token has the right scope

### Common HTTP Status Codes

| Status Code | Meaning | What to Do |
|-------------|---------|------------|
| 400 Bad Request | Invalid variable key or value | Check that your key/value is valid and doesn't contain invalid characters |
| 401 Unauthorized | Invalid or expired token | Regenerate your GitLab personal access token |
| 403 Forbidden | Permission denied | Check that your token has the `api` scope |
| 404 Not Found | Variable or project doesn't exist | Verify the variable key or project ID |
| 409 Conflict | Variable already exists (create) | Use `update` command instead, or check for duplicate entries in bulk files |
| 422 Unprocessable Entity | Validation failed | Check that masked values are at least 8 characters |

### Only Seeing Some Secrets
- **Fixed!** The tool now automatically handles GitLab's pagination (20 items per page)
- All secrets are fetched across multiple pages automatically
- The total count shown includes all secrets in your project

### Filtering Variables
- Use `--filter` or `-f` option with list and download commands
- Supports regex patterns for flexible matching
- Examples:
  - `--filter "API.*"` - Match variables starting with "API"
  - `--filter "DATABASE_"` - Match variables containing "DATABASE_"
  - `--filter "^PROD_|^STAGING_"` - Match variables starting with "PROD_" or "STAGING_"

### Bulk Operations
- Create or update multiple variables from a file
- Supports YAML, JSON, and .env file formats
- YAML and JSON formats can include properties like `protected`, `masked`, `raw`
- .env format is simple `KEY=VALUE` pairs (see limitations in "Bulk Operations" section)
- See `example-variables.yaml`, `example-variables.json`, and `example-variables.env` for reference

**.env File Format Limitations:**
The tool uses simple parsing for .env files (not python-dotenv). Supported features:
- ✅ Simple `KEY=VALUE` pairs
- ✅ Comments (lines starting with `#`)
- ✅ Empty lines (ignored)
- ✅ Whitespace trimming around keys/values

**Not supported** (use YAML/JSON for these):
- ❌ Variable expansion/interpolation (e.g., `${VAR}` or `$VAR`)
- ❌ Quote removal (quotes are preserved as part of the value)
- ❌ Multiline values
- ❌ Escaped characters (e.g., `\n` is literal, not newline)
- ❌ Variables without values (e.g., `KEY` without `=`)
- ❌ `export` keyword handling

Values are treated literally - exactly as written in the file. For advanced features, use YAML or JSON format instead.

### Error Handling

**Creating Variables:**
- **Variable already exists**: The create operation will fail with an error message by default. Use the `update` command to modify existing variables, or use the `--upsert` flag to automatically update if the variable already exists.
- **Bulk create**: If a variable already exists, it will show as failed with an error message, but the tool will continue processing other variables. A summary shows successful vs failed counts. Use `--upsert` to automatically update existing variables.
- **Upsert mode** (`--upsert`): When enabled, existing variables are updated instead of causing an error. This is useful for synchronizing environments or re-running bulk imports.

**Updating Variables:**
- **Variable doesn't exist**: The update operation will fail with an error message. Use the `create` command to add new variables.
- **Bulk update**: If a variable doesn't exist, it will show as failed with an error message, but the tool will continue processing other variables. A summary shows successful vs failed counts.

**Deleting Variables:**
- **Variable doesn't exist**: The delete command will display a "Variable not found" warning message but will not throw an error.

**Best Practices:**
- Use `python gitlab_secrets.py list` to check existing variables before creating new ones
- Use bulk operations to get a complete summary of successful and failed operations
- Use filters (`--filter`) to preview which variables match your pattern before bulk operations
- Use `--upsert` when you want to synchronize variables (e.g., syncing from another environment)
- Use `--upsert` for idempotent bulk operations that can be safely re-run
- **Warning**: `--upsert` will update existing variables without confirmation, use carefully

**Variable Key Validation:**
- The tool validates variable keys according to GitLab's API rules
- Keys must:
  - Not be empty
  - Consist of one line without spaces
  - Contain only letters, numbers, and underscores
- Examples:
  - ✅ Valid: `API_KEY`, `DATABASE_URL`, `MY_VAR_123`, `123_KEY` (allowed but not recommended)
  - ❌ Invalid: `MY-KEY` (contains dash), `MY KEY` (contains space), `MY.KEY` (contains period)
- Note: While GitLab allows keys starting with numbers, it's not recommended as it can cause job failures

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

