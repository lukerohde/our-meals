# Our Menu

A totally unnessary django app to manage our menu - it uses GenAI to scrape recipes and manipulate menus.    I should contributed Mealie instead.

TODO
* Edit a meal
* DONE AI instruction for meal scraping
* DONE Edit a meal plan - change its name
* DONE Delete a meal
* Delete a collection
* Account settings w/Set region
* DONE Add to meal plan
* DONE Share meal plan with friends
* DONE Show shopping list
* DONE Share meal collection with friends?
* Import and display pictures
* DONE Accept a family invite
* DONE Invite a family member
* Improve code
    * Tests!! 
    * Refactor scrapping - that's super ugly
    * Refactor authorisation check (meal plan member)
    * DONE Refactor JS
    * DONE Refactor CSS
    * Refactor views & URLs
* Improve security
    * Unguessable collection and recipe links
    * Read only mode on collections and recipies that aren't yours (or your meal plans)
    * a capture for sign up
    * DONE Invitation only sign up - stop randos joining during rollout 
    * DONE URL/path whitelisting
* Improve sign up
    * DONE De-restrict passwords, allowing passphrases
    * DONE Allow emails for username
    * DONE Sign up when joining a meal plan
    * DONE Fix intermittent 500 on email use
    * Sign up or sign in, as the same page? 
    * DONE Redirect to meal plan after sign up
* Improve meal import
    * Handle coles online and www.deliciousmagazine.co.uk 
    * Checkout python recipe-scraper
    * Import from photos using openai 4o or similar
    * Import from pdf 
    * Convert ingredients to region
    * Better handle odd units (to taste, one piece of egg)
* Improve Nav
    * DONE Get to collections from meal plan
    * DONE Meal plan is more prominent
    * DONE Can add meal to meal plan from meal details page
    * DONE Improve error pages
    * DONE AJAX Add to meal plan
    * DONE AJAX Remove from meal plan
    * AJAX Grocery list
    * Async or streaming grocery list
* Improve deployment
    * DONE Serve via gunicorn
    * Multistage docker build with;
        * build
        * test
        * run
    * Makefile
    * Render deploy yaml
    * Github action for test and deploy off main


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
npm run build
python manage.py runserver 0.0.0.0:3000
``` 

If you want hot reloading js and css
```
docker compose exec app npm run dev
```

To simulate production running via gunicorn and nginx on localhost port 80 
```
docker compose exec app gunicorn ourmeals wsgi:application --bind 0.0.0.0:3000 --workers 3 --chdir .
```

# Deployment Instructions
## Deploying to Digital Ocean Droplet

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

To setup completely new hosting, I purchased a domain from namecheap and configured custom dns pointing to digital ocean's nameservers - ns1.digitalocean.com, ns2.digitalocean.com, ns3.digitalocean.com (don't forgot to click the tick!).  I created a new project in digital ocean just to group the server and domain.  I added my new mac's public ssh key to my digital ocean team.   I think this key is used in two ways.  First to avoid needing to config doctl with a token and provide it all the time, automating the deployment script.  It is also added to the server by the deployment script for passwordless sign in.  I updated the .env-prod with domain name I purchased, and my ssh key name and public key.  I click-ops'd a dns domain/zone in digital ocean, but I think the deploy script would have done that for me. After that it was just a matter of running the deploy script.  Because I failed to save the custom dns settings, certbot was failing because it reach my server to download the challenge file.  Waiting for DNS propergation is fun.  I also had a bunch of troubles because I was missing the .nginx, .certbot directories resulting in them having root permissions.

## Deploying to Render

1. Prerequisites:
   - A Render account (sign up at render.com)
   - Render payment method set up - Account Settings -> Billing -> Add Payment Method
   - To query Render (not needed).  Render API key in your .env file: `RENDER_API_KEY=your_key_here`
        - `jq` command-line tool installed (`brew install jq`)

2. Create a render blueprint:
   - copy render.yaml.example to render.yaml, and check it over
   - In Render Dashboard;
    - +New - Blueprint
    - Name: your-app-name
    - Repo: https://github.com/our-meals/our-meals
     - Deployment Branch: your-branch-name
     - Check the results of the blueprint validation
     - Clickity clickity

3. DNS Configuration:
   - In your DNS provider, create a CNAME record:
     - Host: dev
     - Value: your-app-name.onrender.com (get this from Render dashboard)
   - Render will automatically provision and renew SSL certificates

4. Environment Variables:
   - Most environment variables are automatically set from render.yaml
   - Database connection is handled via DATABASE_URL
