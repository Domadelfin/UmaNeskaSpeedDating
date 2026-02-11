# Railway Deployment Guide

## 1) Create the Railway Project
- Create a new Railway project.
- Add a **PostgreSQL** plugin (Railway will provision the DB).

## 2) Connect Your App to the DB
- Open the PostgreSQL plugin and copy the **DATABASE_URL**.
- Add it to your app service Variables:
```
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
```

## 3) App Environment Variables
```
SECRET_KEY=your-secret
DEBUG=false
ALLOWED_HOSTS=yourapp.up.railway.app,yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourapp.up.railway.app,https://yourdomain.com
DB_SSL_REQUIRE=true
```

## 4) Start Command (Web)
Set this in Railway → Service → Settings:
```
gunicorn speeddating.wsgi:application --bind 0.0.0.0:$PORT
```

## 5) Migrations
Run once after deploy:
```
railway run python manage.py migrate
```

## 6) Create Admin User
```
railway run python manage.py createsuperuser
```

## 7) Static Files
Optional on Railway (WhiteNoise serves static):
```
python manage.py collectstatic --noinput
```

If you want automatic migrations + collectstatic, add a build command:
```
python manage.py migrate && python manage.py collectstatic --noinput
```
