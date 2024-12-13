# Our Menu

A totally unnessary django app to manage our menu - it uses GenAI to scrape recipes and manipulate menus.    I should contributed Mealie instead.

# Setup

```
cp .env.example .env
```

Set secrets in .env - to generate a good secret key for DJANGO_SECRET_KEY and POSTGRES_PASSWORD
```
openssl rand -hex 32
```

To develop in containers you need to copy the override file, which will hang the container so you can shell in and run django commands.

```
cp docker-compose.override.yml.example docker-compose.override.yml
```


```
docker-compose up -d
```

see logs
```
docker-compose logs
```

Shell into the python app container
```
docker-compose exec app /bin/bash
```

To make typing these commands less tedious it helps to have docker aliases in your .bash_profile or similar
```
alias dc='docker-compose'
alias dcu='docker-compose up -d'
alias dcd='docker-compose down'
alias dcl='docker-compose logs'
```

Once in the app container you can run the django commands
```
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser --noinput
python manage.py runserver 0.0.0.0:3000
``` 

# Deployment Instructions
## Deploying to Digital Ocean

To deploy to digital ocean you'll need doctl installed as a prerequisite.

On mac, `brew install doctl`

Then you'll need to config it with your digital ocean token. 

`doctl auth init`

In the deploy directory there are a number of scripts to help you get into production.  You run them from the parent directory.

* `deploy/go` will do everything
* `deploy/01-build-server` will make a digital ocean server and set `.digital_ocean_env` so your other scripts will work
* `deploy/02-config-server` this does everything to pave the road for deployment such as installing software and creating a non root user
* `deploy/03-deploy-repo` this will clone the repo in and copy up the env files mentioned below, then fire up docker compose 
* `deploy/userlogin` a shortcut for logging into the server
* `deploy/rootlogin` I should probably kill this
* `deploy/backup` take a copy of the production database
* `deploy/restore` restores the latest backup
* `deploy/cleanup` destroys the digital ocean server

If you are using the digital ocean deploy scripts in /deploy, there are two files you'll need;

* `.env-prod` for production configuration (same as .env unless you have different prod config)
* `.docker-compose-override.yml.prod` which open the app port
