from datetime import timedelta
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "fallback-insecure-key")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

BASE_DIR = Path(__file__).resolve().parent.parent


DEBUG = True

ALLOWED_HOSTS = [
    'api-baopaint.ru',
    '127.0.0.1',
    'localhost',
    '2.59.42.161',  # 👈 добавь это
]

INSTALLED_APPS = [
    'Backend_paint_app',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'djoser',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",       # фронтенд локально
    "http://127.0.0.1:5173",       # иногда используется вместо localhost
    "https://baopaint.ru",         # фронтенд на проде
    "http://baopaint.ru"
]

CSRF_TRUSTED_ORIGINS = ['https://api-baopaint.ru']

CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

ROOT_URLCONF = 'Backend_paint.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Backend_paint.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'default_db',  # имя базы данных
        'USER': 'gen_user',  # имя пользователя
        'PASSWORD': 'dfdfyz12',  # пароль
        'HOST': '89.223.125.202',  # адрес сервера базы
        'PORT': '5432',  # порт
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

AUTH_USER_MODEL = 'Backend_paint_app.CustomUser'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
