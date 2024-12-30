# Digital Ocean Deployment Scripts

Scripts for managing deployment and database operations on Digital Ocean.

## Deployment Instructions

These instructions will configure a droplet in digital ocean to run docker-compose, with nginx, certbot, postgres and python/django.

To deploy to digital ocean you'll need doctl installed as a prerequisite.

On mac, `brew install doctl`

Then you'll need to config it with your digital ocean token. 

`doctl auth init`

In the deploy directory there are a number of scripts to help you get into production. You run them from the parent directory.

* `deploy/go` will do everything including the following.
* `deploy/01-build-server` will make a digital ocean server and set `.digital_ocean_env` so your other scripts will work
* `deploy/02-config-server` this does everything to pave the road for deployment such as installing docker and creating a non root user
* `deploy/03-deploy-repo` this will clone the repo in and copy up the env files mentioned below, then fire up docker compose 
* `deploy/userlogin` a shortcut for logging into the server
* `deploy/rootlogin` I should probably kill this
* `deploy/cleanup` destroys the digital ocean server

If you are using the digital ocean deploy scripts in /deploy, there are two files you'll need;

* `.env-prod` for production configuration (same as .env unless you have different prod config)
* `.docker-compose-override.yml.prod` which open the app port

To setup completely new hosting, I purchased a domain from namecheap and configured custom dns pointing to digital ocean's nameservers - ns1.digitalocean.com, ns2.digitalocean.com, ns3.digitalocean.com. I created a new project in digital ocean just to group the server and domain. I added my new mac's public ssh key to my digital ocean team. I think this key is used in two ways; First to avoid needing to provide a doctl token on every call, automating the deployment script. It is also added to the droplet by the deployment script for passwordless sign in. I updated the .env-prod with domain name I purchased, and my ssh key name and public key. I click-ops'd a dns domain/zone in digital ocean, but I think the deploy script would have done that for me. After that it was just a matter waiting for dns propagation and then running the deploy script. We need the dns propagation to complete because certbot needs to reach the server to download the challenge file. I had a bunch of troubles because I was missing the .nginx, .certbot directories resulted in them having root permissions.

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