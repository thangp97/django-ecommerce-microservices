import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-recommender-service-key'
DEBUG = True
ALLOWED_HOSTS = ['*']
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'app',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'recommender_service.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'recommender_service.wsgi.application'
DATABASES = {'default': {
    'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
    'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
    'USER': os.environ.get('DB_USER', ''), 'PASSWORD': os.environ.get('DB_PASSWORD', ''),
    'HOST': os.environ.get('DB_HOST', ''), 'PORT': os.environ.get('DB_PORT', ''),
}}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Service URLs for fetching data
BOOK_SERVICE_URL = os.environ.get('BOOK_SERVICE_URL', 'http://book-service:8000')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://order-service:8000')
COMMENT_RATE_SERVICE_URL = os.environ.get('COMMENT_RATE_SERVICE_URL', 'http://comment-rate-service:8000')
CLOTHE_SERVICE_URL = os.environ.get('CLOTHE_SERVICE_URL', 'http://clothe-service:8000')
CUSTOMER_SERVICE_URL = os.environ.get('CUSTOMER_SERVICE_URL', 'http://customer-service:8000')

# AI configuration
AI_MODEL_DIR = os.environ.get('AI_MODEL_DIR', '/app/ai_models')
CHROMA_DB_DIR = os.environ.get('CHROMA_DB_DIR', '/app/chroma_db')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
