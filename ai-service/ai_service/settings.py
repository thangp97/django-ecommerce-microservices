from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-service-dev-secret')
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'rest_framework',
    'app',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'ai_service.urls'
WSGI_APPLICATION = 'ai_service.wsgi.application'

# AI-service stateless — SQLite chỉ để Django không lỗi. Dữ liệu thật ở Neo4j.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True

NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://neo4j:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'bookstore123')
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
BEHAVIOR_EXCHANGE = 'user_behavior'

PRODUCT_SERVICE_MAP = {
    'book': ('http://book-service:8000', 'books'),
    'clothe': ('http://clothe-service:8000', 'clothes'),
    'electronic': ('http://electronic-service:8000', 'electronics'),
    'food': ('http://food-service:8000', 'foods'),
    'toy': ('http://toy-service:8000', 'toys'),
    'furniture': ('http://furniture-service:8000', 'furnitures'),
    'cosmetic': ('http://cosmetic-service:8000', 'cosmetics'),
    'sport': ('http://sport-service:8000', 'sports'),
    'stationery': ('http://stationery-service:8000', 'stationeries'),
    'appliance': ('http://appliance-service:8000', 'appliances'),
    'jewelry': ('http://jewelry-service:8000', 'jewelries'),
    'pet-supply': ('http://pet-supply-service:8000', 'pet-supplies'),
}
