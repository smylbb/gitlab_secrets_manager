# Quick Start Guide

Get up and running with GitLab Secrets Manager in 5 minutes!

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure GitLab Access

1. Get your GitLab Personal Access Token:

   - Go to https://gitlab.com/-/profile/personal_access_tokens
   - Create a token with `api` scope
   - Copy the token

2. Get your Project ID:

   - Navigate to your GitLab project
   - Check the URL or go to Settings > General
   - Copy the Project ID

3. Create a `.env` file:

   ```bash
   cp env.example .env
   ```

4. Edit `.env` and add your credentials:
   ```
   GITLAB_URL=https://gitlab.com
   GITLAB_TOKEN=glpat-your-token-here
   GITLAB_PROJECT_ID=12345678
   ```

## 3. Test Your Setup

```bash
# List all your GitLab secrets
python gitlab_secrets.py list
```

## 4. Start Managing Secrets

```bash
# Create a new secret
python gitlab_secrets.py create MY_SECRET "secret_value"

# Read a secret
python gitlab_secrets.py read MY_SECRET

# Update a secret
python gitlab_secrets.py update MY_SECRET "new_value"

# Create or update (upsert) - useful for sync operations
python gitlab_secrets.py create MY_SECRET "value" --upsert

# Download all secrets
python gitlab_secrets.py download --output backup.json

# Delete a secret
python gitlab_secrets.py delete MY_SECRET
```

## Need Help?

Run `python gitlab_secrets.py --help` to see all available commands and options.

For more detailed documentation, see [README.md](README.md).
