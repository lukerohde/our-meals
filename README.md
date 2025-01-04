# Our Menu

A totally unnessary django app to manage our menu - it uses GenAI to scrape recipes and manipulate menus.    I should contributed Mealie instead.

TODO
* Features
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
    * Suggest and search for meals 
        * Cookbooks
        * Online
    * Set goals
        * Prioritise meals by goals
        * Rate meals against goals
    * Order groceries online - https://github.com/drkno/au-supermarket-apis
* Improve code
    * DONE Tests!! 
    * DONE-ish Refactor scrapping - that's super ugly
    * DONE Refactor authorisation check (meal plan member)
    * DONE Refactor JS
    * DONE Refactor CSS
    * DONE-ish Refactor views & URLs
    * DONE Get playwright going
    * Fix bugs
        * Can't drop and drag two files
    * DONE Refactor models
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
    * Social sign up
* Improve meal import
    * Handle coles online and www.deliciousmagazine.co.uk 
    * Checkout python recipe-scraper
    * DONE Import from photos using openai 4o or similar
    * Import from pdf 
    * Convert ingredients to region
    * Better handle odd units (to taste, one piece of egg)
    * DONE fix https://cookieandkate.com/classic-french-75-cocktail-recipe/
    * Dan murphy's gives me random recipes??? https://www.danmurphys.com.au/dans-daily/cocktails/elderflower-martini-cocktail-recipe
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
    * DONE Multistage docker build with;
        * DONE build
        * DONE test
        * DONE run
    * Makefile
    * DONE Render deploy yaml
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
docker-compose exec app /bin/sh
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

## Database Operations

For database backup, restore, and migration instructions:
- Render: See [deploy-render/README.md](deploy-render/README.md)
- Digital Ocean: See [deploy-do/README.md](deploy-do/README.md)

# Deployment Instructions

For more detailed instructions, please refer to the following README files:

- [Deploy to Render](deploy-render/README.md)
- [Deploy to Digital Ocean](deploy-do/README.md)
