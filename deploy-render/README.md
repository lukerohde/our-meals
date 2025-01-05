# Render Deployment Scripts

Scripts for managing deployment and database operations on Render.

## Environment Setup

Create a `.env` file with your Render API key:
```bash
RENDER_API_KEY=your_key_here
```

## Deploying to Render

1. Prerequisites:
   - A Render account (sign up at render.com)
   - Render payment method set up - Account Settings -> Billing -> Add Payment Method

2. Create a render blueprint:
   - copy deploy-render/render.yaml.example to render.yaml in the root, and check it over
   - In Render Dashboard;
    - +New - Blueprint
    - Name: your-app-name 
    - Repo: https://github.com/your-github-account/our-meals
     - Deployment Branch: your-branch-name
     - Check the results of the blueprint validation
     - finish with Clickity clickity 

3. DNS Configuration:
   - In your DNS hosting provider, create a CNAME record:
     - Host: www or dev or whatever
     - Value: your-app-name.onrender.com 
   - Render will automatically provision and renew SSL certificates
   - make sure your render DJANGO_ALLOWED_HOSTS has both your cname and your-app-name.onrender.com (comma separated)

4. Environment Variables:
   - Most environment variables are automatically set from render.yaml
   - Database connection is handled via DATABASE_URL
   - Set secret stuff like OPENAI_API_KEY and AWS S3 secrets in Render dashboard


## Database Scripts

### Backup and Restore

- `backup`: Creates a SQL backup of the database
  ```bash
  ./backup
  # Creates: backup/backup_YYYY-MM-DD.sql and backup/backup_latest.sql
  ```

- `restore`: Restores a database from backup
  ```bash
  # Restore latest backup
  ./restore
  
  # Restore specific backup
  ./restore backup/backup_2024-12-30.sql
  ```

The scripts handle IP allowlist management automatically during backup/restore operations.

### Configuration and Access

- `get-db-config`: Fetches PostgreSQL database configuration from Render API and saves connection details to `.render_db_env`
- `manage-db-allowlist`: Manages IP allowlist for database access
  ```bash
  # Add your current IP
  ./manage-db-allowlist add
  
  # Remove your IP
  ./manage-db-allowlist remove
  ```

## Migrating Data

### From Digital Ocean to Render
1. Create a backup on Digital Ocean:
   ```bash
   cd deploy-do
   ./backup
   ```
2. Restore the backup on Render:
   ```bash
   cd deploy-render
   ./restore ../backup/backup_latest.sql
   ```

### From Render to Digital Ocean
1. Create a backup on Render:
   ```bash
   cd deploy-render
   ./backup
   ```
2. Restore the backup on Digital Ocean:
   ```bash
   cd deploy-do
   ./restore ../backup/backup_latest.sql
   ```