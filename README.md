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

1. **Ensure environment variables are set appropriately for production.**
2. **Build Docker containers:**    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d    ```
3. **Apply migrations:**    ```bash
    docker-compose exec web python manage.py migrate    ```
4. **Collect static files:**    ```bash
    docker-compose exec web python manage.py collectstatic --noinput    ```
5. **Access the live application at your server's domain or IP.**
