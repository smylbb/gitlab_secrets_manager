"""
Command-line interface for GitLab Secrets Manager.

This module provides a comprehensive CLI tool for managing GitLab CI/CD variables.
It uses Click for command-line parsing and Rich for beautiful terminal output.

The CLI supports all CRUD operations:
- Create: Add new secrets with various protection options
- Read: View details of existing secrets
- Update: Modify existing secrets
- Delete: Remove secrets with confirmation
- List: View all secrets in a formatted table
- Download: Export secrets to JSON or .env files

Example usage:
    python gitlab_secrets.py create API_KEY "secret123" --protected --masked
    python gitlab_secrets.py read API_KEY
    python gitlab_secrets.py list --sort key
    python gitlab_secrets.py download --format json --include-values
"""
import click
import json
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from config import Config
from gitlab_client import GitLabClient


# Initialize Rich console for beautiful terminal output
console = Console()


# Variable key validation
def validate_variable_key(key: str) -> bool:
    """
    Validate a GitLab variable key according to GitLab's API rules.
    
    GitLab variable keys must:
    - Not be empty
    - Consist of one line without spaces
    - Contain only letters, numbers, or underscores
    
    Note: While GitLab allows keys starting with numbers, it's not recommended
    as it can cause job failures. This validation allows it but follows GitLab's
    documented API behavior.
    
    Args:
        key (str): Variable key to validate
        
    Returns:
        bool: True if valid, raises ValueError if invalid
        
    Raises:
        ValueError: If the key is invalid
        
    Example:
        >>> validate_variable_key("API_KEY")  # Valid
        True
        >>> validate_variable_key("MY_VAR_123")  # Valid
        True
        >>> validate_variable_key("MY KEY")  # Invalid: contains space
        ValueError: Invalid variable key 'MY KEY'. ...
    """
    if not key or not key.strip():
        raise ValueError("Variable key cannot be empty or whitespace only")
    
    # GitLab requires: one line without spaces, letters/numbers/underscores only
    # Check for spaces (including tabs, newlines, etc.)
    if re.search(r'\s', key):
        raise ValueError(
            f"Invalid variable key '{key}'. "
            "Variable keys must consist of one line without spaces."
        )
    
    # GitLab allows: letters, numbers, and underscores
    # Note: Keys can start with numbers (allowed by GitLab, but not recommended)
    if not re.match(r'^[A-Za-z0-9_]+$', key):
        invalid_chars = re.findall(r'[^A-Za-z0-9_]', key)
        if invalid_chars:
            unique_chars = ', '.join(sorted(set(invalid_chars)))
            raise ValueError(
                f"Invalid variable key '{key}'. "
                f"Key contains invalid characters: {unique_chars}. "
                "Variable keys can only contain letters, numbers, and underscores."
            )
        # Generic error for other cases
        raise ValueError(
            f"Invalid variable key '{key}'. "
            "Variable keys can only contain letters, numbers, and underscores."
        )
    
    return True


# Custom YAML representer for multiline strings
def multiline_str_presenter(dumper, data):
    """Custom YAML representer for multiline strings using literal block style."""
    if '\n' in str(data):
        # Use literal block style for strings with newlines
        return dumper.represent_scalar('tag:yaml.org,2002:str', str(data), style='|')
    # Use folded block style for very long strings without newlines
    if len(str(data)) > 120:
        return dumper.represent_scalar('tag:yaml.org,2002:str', str(data), style='>')
    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data))

yaml.add_representer(str, multiline_str_presenter)


@click.group()
@click.pass_context
def cli(ctx):
    """
    GitLab Secrets Manager - Manage CI/CD variables for your GitLab projects.
    
    This is the main CLI entry point. It initializes configuration and creates
    a GitLab client instance that is shared across all commands.
    
    Before running any commands, you must set:
    - GITLAB_TOKEN: Your GitLab personal access token
    - GITLAB_PROJECT_ID: Your GitLab project ID
    
    These can be set as environment variables or in a .env file.
    """
    # Load and validate configuration
    config = Config()
    try:
        # Ensure required credentials are present
        config.validate()
        
        # Set up Click context for passing data between commands
        ctx.ensure_object(dict)
        ctx.obj['config'] = config
        ctx.obj['client'] = GitLabClient(config)
        
    except ValueError as e:
        # Display helpful error message if configuration is missing
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Please set the following environment variables:[/yellow]")
        console.print("  - GITLAB_TOKEN: Your GitLab personal access token")
        console.print("  - GITLAB_PROJECT_ID: Your GitLab project ID")
        console.print("\nYou can also create a .env file with these variables.")
        
        # Abort CLI execution
        ctx.abort()


@cli.command()
@click.argument('key', required=False)
@click.argument('value', required=False)
@click.option('--protected', is_flag=True, help='Mark variable as protected')
@click.option('--masked', is_flag=True, help='Mask variable in job logs')
@click.option('--raw', is_flag=True, help='Treat variable as raw (no expansion)')
@click.option('--environment-scope', default='*', help='Environment scope (default: * for all environments)')
@click.option('--file', '-f', type=click.Path(exists=True), help='Bulk create from file (JSON or .env format)')
@click.option('--upsert', is_flag=True, help='Update existing variables instead of failing (creates if not exists)')
@click.pass_context
def create(ctx, key: str, value: str, protected: bool, masked: bool, raw: bool, environment_scope: str, file: str, upsert: bool):
    """
    Create GitLab secrets (CI/CD variables).
    
    Creates one or more CI/CD variables in your GitLab project. You can create
    a single variable or bulk create from a file. You can optionally mark variables
    as protected (only available on protected branches), masked (hidden in job logs),
    or raw (no variable expansion).
    
    Args:
        key: The variable name/key (optional if using --file)
        value: The variable value (optional if using --file)
    
    Example:
        # Create a single variable
        python gitlab_secrets.py create DATABASE_URL "postgresql://localhost/db" --protected
        python gitlab_secrets.py create API_KEY "secret123" --masked --raw
        
        # Upsert: create or update if already exists
        python gitlab_secrets.py create DATABASE_URL "new_value" --upsert
        
        # Bulk create from file
        python gitlab_secrets.py create --file variables.json
        python gitlab_secrets.py create --file .env.production
        
        # Bulk upsert: create or update existing variables
        python gitlab_secrets.py create --file variables.json --upsert
    """
    # Get the GitLab client from context
    client = ctx.obj['client']
    
    try:
        # Bulk create from file
        if file:
            file_path = Path(file)
            
            # Read file based on extension
            if file_path.suffix in ['.yml', '.yaml']:
                # Read YAML file
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                
                # Handle different YAML structures
                if isinstance(data, dict):
                    if 'variables' in data:
                        variables = data['variables']
                    else:
                        # Assume it's a dict of key-value pairs
                        variables = [{'key': k, 'value': v} for k, v in data.items()]
                elif isinstance(data, list):
                    variables = data
                else:
                    console.print("[red]Invalid YAML format[/red]")
                    return
                    
            elif file_path.suffix == '.json':
                # Read JSON file
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, dict):
                    if 'variables' in data:
                        variables = data['variables']
                    else:
                        # Assume it's a dict of key-value pairs
                        variables = [{'key': k, 'value': v} for k, v in data.items()]
                elif isinstance(data, list):
                    variables = data
                else:
                    console.print("[red]Invalid JSON format[/red]")
                    return
                
            elif file_path.suffix == '.env' or 'env' in file_path.name:
                # Read .env file
                variables = []
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith('#'):
                            continue
                        # Parse key=value
                        if '=' in line:
                            key, value = line.split('=', 1)
                            variables.append({'key': key.strip(), 'value': value.strip()})
            else:
                console.print("[red]Unsupported file format. Use .yaml, .json, or .env files[/red]")
                return
            
            if not variables:
                console.print("[yellow]No variables found in file[/yellow]")
                return
            
            # Create all variables
            console.print(f"[cyan]Creating {len(variables)} variables...[/cyan]")
            success_count = 0
            failed_count = 0
            
            for var in variables:
                try:
                    var_key = var.get('key', '')
                    var_value = var.get('value', '')
                    
                    # Check if key is missing
                    if not var_key:
                        console.print(f"  [red]✗[/red] Missing key in variable entry")
                        failed_count += 1
                        continue
                    
                    # Validate variable key
                    try:
                        validate_variable_key(var_key)
                    except ValueError as e:
                        console.print(f"  [red]✗[/red] {var_key}: {e}")
                        failed_count += 1
                        continue
                    
                    # Build kwargs from variable data or use defaults
                    kwargs = {}
                    if var.get('protected') is not None:
                        kwargs['protected'] = var['protected']
                    elif protected:
                        kwargs['protected'] = True
                        
                    if var.get('masked') is not None:
                        kwargs['masked'] = var['masked']
                    elif masked:
                        kwargs['masked'] = True
                        
                    if var.get('raw') is not None:
                        kwargs['raw'] = var['raw']
                    elif raw:
                        kwargs['raw'] = True
                    
                    # Handle environment_scope
                    if var.get('environment_scope') is not None:
                        kwargs['environment_scope'] = var['environment_scope']
                    elif environment_scope and environment_scope != '*':
                        kwargs['environment_scope'] = environment_scope
                    
                    # Try to create the variable
                    try:
                        client.create_variable(var_key, var_value, **kwargs)
                        console.print(f"  [green]✓[/green] Created: {var_key}")
                        success_count += 1
                    except Exception as create_error:
                        # If variable already exists and upsert is enabled, try to update
                        # Check if it's an HTTPError with status code 409 (Conflict)
                        is_conflict = False
                        if hasattr(create_error, 'response'):
                            is_conflict = create_error.response.status_code == 409
                        else:
                            # Fallback to string matching for other exception types
                            is_conflict = '409' in str(create_error) or 'Conflict' in str(create_error)
                        
                        if upsert and is_conflict:
                            try:
                                client.update_variable(var_key, var_value, **kwargs)
                                console.print(f"  [yellow]🔄[/yellow] Updated: {var_key} (already exists)")
                                success_count += 1
                            except Exception as update_error:
                                console.print(f"  [red]✗[/red] {var_key}: {update_error}")
                                failed_count += 1
                        else:
                            raise create_error
                except Exception as e:
                    console.print(f"  [red]✗[/red] {var_key}: {e}")
                    failed_count += 1
            
            console.print(f"\n[green]Successfully created: {success_count}[/green]")
            if failed_count > 0:
                console.print(f"[red]Failed: {failed_count}[/red]")
            
            return
        
        # Single variable creation
        if not key or not value:
            console.print("[red]Error: Both key and value are required for single variable creation[/red]")
            console.print("Use --file option for bulk creation")
            return
        
        # Validate variable key
        try:
            validate_variable_key(key)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return
        
        # Build optional parameters dictionary
        kwargs = {}
        
        # Protected variables are only available on protected branches/tags
        if protected:
            kwargs['protected'] = True
        
        # Masked variables hide their values in CI/CD job logs
        if masked:
            kwargs['masked'] = True
        
        # Raw variables are not expanded (useful for JSON or multiline values)
        if raw:
            kwargs['raw'] = True
        
        # Environment scope (default is '*' for all environments)
        if environment_scope and environment_scope != '*':
            kwargs['environment_scope'] = environment_scope
        
        # Create or update the variable via GitLab API
        is_updated = False
        try:
            # Try to create the variable
            variable = client.create_variable(key, value, **kwargs)
            console.print(f"[green]✓[/green] Successfully created variable: [bold]{key}[/bold]")
        except Exception as create_error:
            # If variable already exists and upsert is enabled, try to update
            # Check if it's an HTTPError with status code 409 (Conflict)
            is_conflict = False
            if hasattr(create_error, 'response'):
                is_conflict = create_error.response.status_code == 409
            else:
                # Fallback to string matching for other exception types
                is_conflict = '409' in str(create_error) or 'Conflict' in str(create_error)
            
            if upsert and is_conflict:
                variable = client.update_variable(key, value, **kwargs)
                is_updated = True
                console.print(f"[yellow]🔄[/yellow] Successfully updated variable: [bold]{key}[/bold] (already exists)")
            else:
                raise create_error
        
        # Display variable details in a formatted table
        table = Table(title="Variable Details")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Key", variable.get('key', ''))
        table.add_row("Protected", str(variable.get('protected', False)))
        table.add_row("Masked", str(variable.get('masked', False)))
        table.add_row("Raw", str(variable.get('raw', False)))
        table.add_row("Environment Scope", variable.get('environment_scope', '*'))
        
        console.print(table)
        
    except Exception as e:
        # Display error message if creation fails
        console.print(f"[red]Error creating variable: {e}[/red]")


@cli.command()
@click.argument('key')
@click.pass_context
def read(ctx, key: str):
    """
    Read an existing GitLab secret (CI/CD variable).
    
    Retrieves and displays detailed information about a specific CI/CD variable,
    including its value and all configuration settings.
    
    Args:
        key: The variable name/key to retrieve
    
    Example:
        python gitlab_secrets.py read DATABASE_URL
        python gitlab_secrets.py read API_KEY
    """
    # Get the GitLab client from context
    client = ctx.obj['client']
    
    # Validate variable key
    try:
        validate_variable_key(key)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    try:
        # Fetch the variable from GitLab
        variable = client.get_variable(key)
        
        # Check if variable exists
        if variable is None:
            console.print(f"[yellow]Variable '{key}' not found[/yellow]")
            return
        
        # Display variable details in a formatted table
        table = Table(title=f"Variable: {key}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        
        # Add all variable properties to the table
        table.add_row("Key", variable.get('key', ''))
        table.add_row("Value", variable.get('value', ''))
        table.add_row("Protected", str(variable.get('protected', False)))
        table.add_row("Masked", str(variable.get('masked', False)))
        table.add_row("Raw", str(variable.get('raw', False)))
        table.add_row("Environment Scope", variable.get('environment_scope', '*'))
        
        console.print(table)
        
    except Exception as e:
        # Display error message if read fails
        console.print(f"[red]Error reading variable: {e}[/red]")


@cli.command()
@click.argument('key', required=False)
@click.argument('value', required=False)
@click.option('--protected', type=bool, help='Set protected status (true/false)')
@click.option('--masked', type=bool, help='Set masked status (true/false)')
@click.option('--raw', type=bool, help='Set raw status (true/false)')
@click.option('--environment-scope', help='Set environment scope (e.g., production, staging, *)')
@click.option('--file', '-f', type=click.Path(exists=True), help='Bulk update from file (JSON or .env format)')
@click.pass_context
def update(ctx, key: str, value: str, protected: bool, masked: bool, raw: bool, environment_scope: str, file: str):
    """
    Update existing GitLab secrets (CI/CD variables).
    
    Modifies the value and/or properties of one or more CI/CD variables. You can
    update a single variable or bulk update from a file. Only the parameters you
    provide will be updated.
    
    Args:
        key: The variable name/key to update (optional if using --file)
        value: The new variable value (optional if using --file)
    
    Example:
        # Update a single variable
        python gitlab_secrets.py update DATABASE_URL "postgresql://new-db" --protected true
        python gitlab_secrets.py update API_KEY "new_secret" --masked false
        
        # Bulk update from file
        python gitlab_secrets.py update --file updates.json
        python gitlab_secrets.py update --file .env.updates
    """
    # Get the GitLab client from context
    client = ctx.obj['client']
    
    try:
        # Bulk update from file
        if file:
            file_path = Path(file)
            
            # Read file based on extension
            if file_path.suffix in ['.yml', '.yaml']:
                # Read YAML file
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                
                # Handle different YAML structures
                if isinstance(data, dict):
                    if 'variables' in data:
                        variables = data['variables']
                    else:
                        # Assume it's a dict of key-value pairs
                        variables = [{'key': k, 'value': v} for k, v in data.items()]
                elif isinstance(data, list):
                    variables = data
                else:
                    console.print("[red]Invalid YAML format[/red]")
                    return
                    
            elif file_path.suffix == '.json':
                # Read JSON file
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, dict):
                    if 'variables' in data:
                        variables = data['variables']
                    else:
                        # Assume it's a dict of key-value pairs
                        variables = [{'key': k, 'value': v} for k, v in data.items()]
                elif isinstance(data, list):
                    variables = data
                else:
                    console.print("[red]Invalid JSON format[/red]")
                    return
                
            elif file_path.suffix == '.env' or 'env' in file_path.name:
                # Read .env file
                variables = []
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith('#'):
                            continue
                        # Parse key=value
                        if '=' in line:
                            key, value = line.split('=', 1)
                            variables.append({'key': key.strip(), 'value': value.strip()})
            else:
                console.print("[red]Unsupported file format. Use .yaml, .json, or .env files[/red]")
                return
            
            if not variables:
                console.print("[yellow]No variables found in file[/yellow]")
                return
            
            # Update all variables
            console.print(f"[cyan]Updating {len(variables)} variables...[/cyan]")
            success_count = 0
            failed_count = 0
            
            for var in variables:
                try:
                    var_key = var.get('key', '')
                    var_value = var.get('value', '')
                    
                    # Check if key is missing
                    if not var_key:
                        console.print(f"  [red]✗[/red] Missing key in variable entry")
                        failed_count += 1
                        continue
                    
                    # Validate variable key
                    try:
                        validate_variable_key(var_key)
                    except ValueError as e:
                        console.print(f"  [red]✗[/red] {var_key}: {e}")
                        failed_count += 1
                        continue
                    
                    # Build kwargs from variable data or use defaults
                    kwargs = {}
                    if var.get('protected') is not None:
                        kwargs['protected'] = var['protected']
                    elif protected is not None:
                        kwargs['protected'] = protected
                        
                    if var.get('masked') is not None:
                        kwargs['masked'] = var['masked']
                    elif masked is not None:
                        kwargs['masked'] = masked
                        
                    if var.get('raw') is not None:
                        kwargs['raw'] = var['raw']
                    elif raw is not None:
                        kwargs['raw'] = raw
                    
                    # Handle environment_scope
                    if var.get('environment_scope') is not None:
                        kwargs['environment_scope'] = var['environment_scope']
                    elif environment_scope:
                        kwargs['environment_scope'] = environment_scope
                    
                    client.update_variable(var_key, var_value, **kwargs)
                    console.print(f"  [green]✓[/green] {var_key}")
                    success_count += 1
                except Exception as e:
                    console.print(f"  [red]✗[/red] {var_key}: {e}")
                    failed_count += 1
            
            console.print(f"\n[green]Successfully updated: {success_count}[/green]")
            if failed_count > 0:
                console.print(f"[red]Failed: {failed_count}[/red]")
            
            return
        
        # Single variable update
        if not key or not value:
            console.print("[red]Error: Both key and value are required for single variable update[/red]")
            console.print("Use --file option for bulk update")
            return
        
        # Validate variable key
        try:
            validate_variable_key(key)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return
        
        # Build update parameters dictionary
        kwargs = {}
        
        # Only include parameters that were explicitly provided
        if protected is not None:
            kwargs['protected'] = protected
        if masked is not None:
            kwargs['masked'] = masked
        if raw is not None:
            kwargs['raw'] = raw
        if environment_scope:
            kwargs['environment_scope'] = environment_scope
        
        # Update the variable via GitLab API
        variable = client.update_variable(key, value, **kwargs)
        
        # Display success message
        console.print(f"[green]✓[/green] Successfully updated variable: [bold]{key}[/bold]")
        
        # Display updated variable details
        table = Table(title="Updated Variable Details")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Key", variable.get('key', ''))
        table.add_row("Protected", str(variable.get('protected', False)))
        table.add_row("Masked", str(variable.get('masked', False)))
        table.add_row("Raw", str(variable.get('raw', False)))
        table.add_row("Environment Scope", variable.get('environment_scope', '*'))
        
        console.print(table)
        
    except Exception as e:
        # Display error message if update fails
        console.print(f"[red]Error updating variable: {e}[/red]")


@cli.command()
@click.argument('key')
@click.confirmation_option(prompt='Are you sure you want to delete this variable?')
@click.pass_context
def delete(ctx, key: str):
    """
    Delete a GitLab secret (CI/CD variable).
    
    Permanently removes a CI/CD variable from your GitLab project. This action
    cannot be undone, so a confirmation prompt is shown before deletion.
    
    Args:
        key: The variable name/key to delete
    
    Example:
        python gitlab_secrets.py delete OLD_API_KEY
    """
    # Get the GitLab client from context
    client = ctx.obj['client']
    
    # Validate variable key
    try:
        validate_variable_key(key)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return
    
    try:
        # Delete the variable via GitLab API
        success = client.delete_variable(key)
        
        # Display appropriate message based on result
        if success:
            console.print(f"[green]✓[/green] Successfully deleted variable: [bold]{key}[/bold]")
        else:
            console.print(f"[yellow]Variable '{key}' not found[/yellow]")
        
    except Exception as e:
        # Display error message if deletion fails
        console.print(f"[red]Error deleting variable: {e}[/red]")


@cli.command('list')
@click.option('--sort', type=click.Choice(['key', 'protected', 'masked', 'raw']), 
              default='key', help='Sort by field')
@click.option('--reverse', is_flag=True, help='Reverse sort order')
@click.option('--show-values', is_flag=True, default=False, 
              help='Display variable values (use with caution for sensitive data)')
@click.option('--filter', '-f', help='Filter variables by key pattern (regex supported)')
@click.pass_context
def list_variables(ctx, sort: str, reverse: bool, show_values: bool, filter: str):
    """
    List all GitLab secrets (CI/CD variables).
    
    Displays all CI/CD variables in your GitLab project in a formatted table.
    You can sort by different fields and reverse the sort order.
    
    Note: Automatically handles GitLab's pagination to fetch ALL secrets,
    not just the first 20.
    
    By default, values are hidden for security. Use --show-values to display them.
    
    Example:
        python gitlab_secrets.py list
        python gitlab_secrets.py list --sort protected --reverse
        python gitlab_secrets.py list --sort masked --show-values
        python gitlab_secrets.py list --filter "API.*"
        python gitlab_secrets.py list --filter "DATABASE_" --show-values
    """
    # Get the GitLab client from context
    client = ctx.obj['client']
    
    try:
        # Fetch all variables from GitLab
        variables = client.list_variables()
        
        # Check if any variables exist
        if not variables:
            console.print("[yellow]No variables found[/yellow]")
            return
        
        # Apply filter if provided
        if filter:
            try:
                # Compile regex pattern for matching
                pattern = re.compile(filter, re.IGNORECASE)
                # Filter variables by key name
                variables = [var for var in variables if pattern.search(var.get('key', ''))]
                
                if not variables:
                    console.print(f"[yellow]No variables match the filter pattern: {filter}[/yellow]")
                    return
                
                console.print(f"[dim]Filtered by pattern: {filter}[/dim]")
            except re.error as e:
                console.print(f"[red]Invalid regex pattern: {e}[/red]")
                return
        
        # Sort variables by the specified field
        # Lambda function extracts the sort field from each variable dict
        variables.sort(key=lambda x: x.get(sort, ''), reverse=reverse)
        
        # Create a formatted table to display variables
        table = Table(title=f"GitLab CI/CD Variables (sorted by {sort})")
        table.add_column("Key", style="cyan", no_wrap=True)
        
        # Add Value column if --show-values flag is set
        if show_values:
            table.add_column("Value", style="magenta", max_width=50)
        
        table.add_column("Protected", style="yellow")
        table.add_column("Masked", style="yellow")
        table.add_column("Raw", style="yellow")
        table.add_column("Environment Scope", style="green")
        
        # Add each variable as a row in the table
        for var in variables:
            row_data = [var.get('key', '')]
            
            # Add value if requested
            if show_values:
                row_data.append(var.get('value', ''))
            
            # Add other properties
            row_data.extend([
                str(var.get('protected', False)),
                str(var.get('masked', False)),
                str(var.get('raw', False)),
                var.get('environment_scope', '*')
            ])
            
            table.add_row(*row_data)
        
        # Display the table
        console.print(table)
        console.print(f"\n[dim]Total: {len(variables)} variables[/dim]")
        
        # Warn if values are being displayed
        if show_values:
            console.print("[yellow]⚠ Warning: Sensitive values are being displayed[/yellow]")
        
    except Exception as e:
        # Display error message if listing fails
        console.print(f"[red]Error listing variables: {e}[/red]")


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', type=click.Choice(['yaml', 'json', 'env']), default='yaml', 
              help='Output format (default: inferred from file extension)')
@click.option('--sort', type=click.Choice(['key', 'protected', 'masked', 'raw']), 
              default='key', help='Sort by field')
@click.option('--reverse', is_flag=True, help='Reverse sort order')
@click.option('--include-values', is_flag=True, default=False, 
              help='Include variable values in output')
@click.option('--filter', '-f', help='Filter variables by key pattern (regex supported)')
@click.option('--simple', 'yaml_format', flag_value='simple',
              help='Use simple YAML format (key-value pairs, default)')
@click.option('--structured', 'yaml_format', flag_value='structured',
              help='Use structured YAML format (with metadata)')
@click.pass_context
def download(ctx, output: str, format: str, sort: str, reverse: bool, include_values: bool, filter: str, yaml_format):
    """
    Download GitLab secrets (CI/CD variables) to a file.
    
    Exports all CI/CD variables to a file in YAML, JSON, or .env format. This is useful
    for backups or migrating secrets between projects. By default, values are
    excluded for security, but you can include them with --include-values.
    
    Example:
        python gitlab_secrets.py download
        python gitlab_secrets.py download --output backup.json
        python gitlab_secrets.py download --output backup.env
        python gitlab_secrets.py download --include-values --sort protected
        python gitlab_secrets.py download --filter "API.*" --output api-vars.yaml
        python gitlab_secrets.py download --filter "DATABASE_" --include-values
        python gitlab_secrets.py download --simple --output simple-backup.yml
        python gitlab_secrets.py download --structured --output structured-backup.yml
        python gitlab_secrets.py download --format json --output backup.json  # Override format
    """
    # Get the GitLab client from context
    client = ctx.obj['client']
    
    try:
        # Fetch all variables from GitLab
        variables = client.list_variables()
        
        # Check if any variables exist
        if not variables:
            console.print("[yellow]No variables found[/yellow]")
            return
        
        # Apply filter if provided
        if filter:
            try:
                # Compile regex pattern for matching
                pattern = re.compile(filter, re.IGNORECASE)
                # Filter variables by key name
                variables = [var for var in variables if pattern.search(var.get('key', ''))]
                
                if not variables:
                    console.print(f"[yellow]No variables match the filter pattern: {filter}[/yellow]")
                    return
                
                console.print(f"[dim]Filtered by pattern: {filter}[/dim]")
            except re.error as e:
                console.print(f"[red]Invalid regex pattern: {e}[/red]")
                return
        
        # Sort variables by the specified field
        variables.sort(key=lambda x: x.get(sort, ''), reverse=reverse)
        
        # Determine output file path if not provided
        if not output:
            if format == 'yaml':
                output = 'secrets.yml'  # Default to simple format
            elif format == 'json':
                output = 'secrets.json'
            else:
                output = '.env'
        
        output_path = Path(output)
        
        # Infer format from file extension when output is specified
        if output:
            file_ext = output_path.suffix.lower()
            if file_ext == '.json':
                format = 'json'
            elif file_ext == '.env':
                format = 'env'
            # .yaml, .yml, or no extension defaults to yaml
        
        # Write to file based on format
        if format == 'yaml':
            # YAML format: human-readable structured data
            # Use the yaml_format parameter (simple or structured)
            # Default to simple if no format specified
            use_simple_format = (yaml_format is None or yaml_format == 'simple')
            
            if use_simple_format:
                # Simple key-value format (no metadata)
                simple_data = {}
                for var in variables:
                    key = var.get('key', '')
                    if include_values:
                        simple_data[key] = var.get('value', '')
                    else:
                        simple_data[key] = ''  # Empty value for security
                
                # Write simple YAML format
                with open(output_path, 'w') as f:
                    f.write("# GitLab CI/CD Variables\n")
                    f.write(f"# Total: {len(variables)}\n")
                    f.write(f"# Sorted by: {sort}\n\n")
                    yaml.dump(simple_data, f, default_flow_style=False, sort_keys=False)
                
            else:
                # Structured format with metadata
                if include_values:
                    # Include all data including sensitive values
                    data = {
                        'variables': variables,
                        'total': len(variables),
                        'sorted_by': sort
                    }
                else:
                    # Exclude values for security (only show metadata)
                    data = {
                        'variables': [
                            {k: v for k, v in var.items() if k != 'value'} 
                            for var in variables
                        ],
                        'total': len(variables),
                        'sorted_by': sort
                    }
                
                # Write structured YAML to file with indentation for readability
                with open(output_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False, indent=2)
            
            console.print(f"[green]✓[/green] Downloaded {len(variables)} variables to [bold]{output_path}[/bold]")
            
        elif format == 'json':
            # JSON format: structured data with metadata
            if include_values:
                # Include all data including sensitive values
                data = {
                    'variables': variables,
                    'total': len(variables),
                    'sorted_by': sort
                }
            else:
                # Exclude values for security (only show metadata)
                data = {
                    'variables': [
                        {k: v for k, v in var.items() if k != 'value'} 
                        for var in variables
                    ],
                    'total': len(variables),
                    'sorted_by': sort
                }
            
            # Write standard JSON format (valid JSON with escaped newlines)
            with open(output_path, 'w', encoding='utf-8') as f:
                # Process data to format multiline JSON values nicely (still as escaped newlines for valid JSON)
                formatted_data = json.loads(json.dumps(data))  # Deep copy to avoid modifying original
                
                if include_values and 'variables' in formatted_data:
                    for var in formatted_data['variables']:
                        if 'value' in var and var['value'] and isinstance(var['value'], str):
                            value = var['value']
                            # If value contains escaped newlines and looks like JSON (starts with { or [)
                            # parse and format with proper indentation (outputs as escaped newlines for valid JSON)
                            if '\\n' in value:
                                stripped = value.strip()
                                if stripped.startswith('{') or stripped.startswith('['):
                                    try:
                                        # Parse the inner JSON (replace escaped newlines with actual newlines)
                                        inner_json_str = value.replace('\\n', '\n')
                                        inner_json = json.loads(inner_json_str)
                                        # Re-encode with proper indentation and escaped newlines
                                        # Format with 2-space indent to match outer structure
                                        formatted_inner = json.dumps(inner_json, indent=2, ensure_ascii=False)
                                        # Replace actual newlines with escaped newlines for JSON string value
                                        var['value'] = formatted_inner.replace('\n', '\\n')
                                    except (json.JSONDecodeError, ValueError):
                                        # Not valid JSON, leave as-is
                                        pass
                
                # Write standard JSON (with escaped newlines in string values)
                json.dump(formatted_data, f, indent=2, ensure_ascii=False)
            
            console.print(f"[green]✓[/green] Downloaded {len(variables)} variables to [bold]{output_path}[/bold]")
            
        elif format == 'env':
            # .env format: key=value pairs (like .env files)
            with open(output_path, 'w') as f:
                # Write header comments
                f.write(f"# GitLab CI/CD Variables\n")
                f.write(f"# Total: {len(variables)}\n")
                f.write(f"# Sorted by: {sort}\n\n")
                
                # Write each variable as key=value
                for var in variables:
                    key = var.get('key', '')
                    if include_values:
                        # Include actual values
                        value = var.get('value', '')
                        f.write(f"{key}={value}\n")
                    else:
                        # Leave values empty for security
                        f.write(f"{key}=\n")
            
            console.print(f"[green]✓[/green] Downloaded {len(variables)} variables to [bold]{output_path}[/bold]")
        
        # Display download summary
        console.print(f"[dim]Format: {format}[/dim]")
        console.print(f"[dim]Sorted by: {sort}[/dim]")
        
        # Warn if values were excluded
        if not include_values:
            console.print("[yellow]Note: Values excluded for security. Use --include-values to include them.[/yellow]")
        
    except Exception as e:
        # Display error message if download fails
        console.print(f"[red]Error downloading variables: {e}[/red]")


# Entry point for running the CLI directly
if __name__ == '__main__':
    cli()

