#!/bin/bash
# Generator script cho 10 product-service mới — dựa trên template clothe-service.
# Chạy 1 lần từ thư mục gốc repo: bash scripts/generate_services.sh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Format: folder|ModelName|url_plural|module_underscore|extra_fields (Python code, comma-separated)
SERVICES=(
  "electronic-service|Electronic|electronics|electronic_service|brand = models.CharField(max_length=255, blank=True); warranty_months = models.IntegerField(default=0); power_w = models.IntegerField(default=0)"
  "food-service|Food|foods|food_service|origin = models.CharField(max_length=255, blank=True); weight_g = models.IntegerField(default=0); expiry_date = models.CharField(max_length=32, blank=True)"
  "toy-service|Toy|toys|toy_service|age_range = models.CharField(max_length=64, blank=True); material = models.CharField(max_length=255, blank=True)"
  "furniture-service|Furniture|furnitures|furniture_service|dimensions = models.CharField(max_length=128, blank=True); material = models.CharField(max_length=255, blank=True); color = models.CharField(max_length=64, blank=True)"
  "cosmetic-service|Cosmetic|cosmetics|cosmetic_service|skin_type = models.CharField(max_length=64, blank=True); volume_ml = models.IntegerField(default=0); expiry_date = models.CharField(max_length=32, blank=True)"
  "sport-service|Sport|sports|sport_service|sport_type = models.CharField(max_length=64, blank=True); size = models.CharField(max_length=32, blank=True)"
  "stationery-service|Stationery|stationeries|stationery_service|brand = models.CharField(max_length=255, blank=True); category = models.CharField(max_length=64, blank=True)"
  "appliance-service|Appliance|appliances|appliance_service|voltage = models.CharField(max_length=32, blank=True); warranty_months = models.IntegerField(default=0)"
  "jewelry-service|Jewelry|jewelries|jewelry_service|material = models.CharField(max_length=64, blank=True); weight_g = models.IntegerField(default=0)"
  "pet-supply-service|PetSupply|pet-supplies|pet_supply_service|pet_type = models.CharField(max_length=64, blank=True); weight_g = models.IntegerField(default=0)"
)

for entry in "${SERVICES[@]}"; do
  IFS='|' read -r folder model plural module extra <<< "$entry"
  svc_dir="$ROOT/$folder"
  app_dir="$svc_dir/app"
  mig_dir="$app_dir/migrations"
  mod_dir="$svc_dir/$module"

  mkdir -p "$mig_dir" "$mod_dir"

  # --- Dockerfile ---
  cat > "$svc_dir/Dockerfile" <<'EOF'
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
EOF

  # --- requirements.txt ---
  cat > "$svc_dir/requirements.txt" <<'EOF'
django
djangorestframework
requests
psycopg2-binary==2.9.9
EOF

  # --- manage.py ---
  cat > "$svc_dir/manage.py" <<EOF
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '${module}.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
EOF

  # --- <module>/__init__.py (empty) ---
  : > "$mod_dir/__init__.py"

  # --- <module>/settings.py ---
  cat > "$mod_dir/settings.py" <<EOF
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-${module}-local-dev-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = '${module}.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = '${module}.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EOF

  # --- <module>/urls.py ---
  cat > "$mod_dir/urls.py" <<EOF
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
]
EOF

  # --- <module>/wsgi.py ---
  cat > "$mod_dir/wsgi.py" <<EOF
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '${module}.settings')
application = get_wsgi_application()
EOF

  # --- <module>/asgi.py ---
  cat > "$mod_dir/asgi.py" <<EOF
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '${module}.settings')
application = get_asgi_application()
EOF

  # --- app/__init__.py ---
  : > "$app_dir/__init__.py"

  # --- app/apps.py ---
  cat > "$app_dir/apps.py" <<'EOF'
from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
EOF

  # --- app/admin.py ---
  cat > "$app_dir/admin.py" <<EOF
from django.contrib import admin
from .models import ${model}

admin.site.register(${model})
EOF

  # --- app/models.py ---
  # Convert "a; b; c" -> lines with 4-space indent
  extra_lines=$(echo "$extra" | sed 's/; /\n    /g')
  cat > "$app_dir/models.py" <<EOF
from django.db import models


class ${model}(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    category = models.CharField(max_length=64, blank=True)
    ${extra_lines}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
EOF

  # --- app/serializers.py ---
  cat > "$app_dir/serializers.py" <<EOF
from rest_framework import serializers
from .models import ${model}


class ${model}Serializer(serializers.ModelSerializer):
    class Meta:
        model = ${model}
        fields = '__all__'
EOF

  # --- app/views.py ---
  cat > "$app_dir/views.py" <<EOF
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ${model}
from .serializers import ${model}Serializer


class ${model}ListCreate(APIView):
    def get(self, request):
        items = ${model}.objects.all()
        return Response(${model}Serializer(items, many=True).data)

    def post(self, request):
        serializer = ${model}Serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class ${model}Detail(APIView):
    def get(self, request, pk):
        try:
            item = ${model}.objects.get(pk=pk)
            return Response(${model}Serializer(item).data)
        except ${model}.DoesNotExist:
            return Response({'error': '${model} not found'}, status=404)

    def patch(self, request, pk):
        try:
            item = ${model}.objects.get(pk=pk)
            serializer = ${model}Serializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except ${model}.DoesNotExist:
            return Response({'error': '${model} not found'}, status=404)


class ${model}ReduceStock(APIView):
    def post(self, request, pk):
        try:
            item = ${model}.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            if item.stock < quantity:
                return Response({'error': f'Không đủ hàng cho {item.name}'}, status=400)
            item.stock -= quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except ${model}.DoesNotExist:
            return Response({'error': '${model} không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ${model}RestoreStock(APIView):
    def post(self, request, pk):
        try:
            item = ${model}.objects.get(pk=pk)
            quantity = int(request.data.get('quantity', 0))
            item.stock += quantity
            item.save()
            return Response({'success': True, 'new_stock': item.stock})
        except ${model}.DoesNotExist:
            return Response({'error': '${model} không tồn tại'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
EOF

  # --- app/urls.py ---
  cat > "$app_dir/urls.py" <<EOF
from django.urls import path
from .views import ${model}ListCreate, ${model}Detail, ${model}ReduceStock, ${model}RestoreStock

urlpatterns = [
    path('${plural}/', ${model}ListCreate.as_view()),
    path('${plural}/<int:pk>/', ${model}Detail.as_view()),
    path('${plural}/<int:pk>/reduce-stock/', ${model}ReduceStock.as_view()),
    path('${plural}/<int:pk>/restore-stock/', ${model}RestoreStock.as_view()),
]
EOF

  # --- app/tests.py ---
  cat > "$app_dir/tests.py" <<'EOF'
from django.test import TestCase
EOF

  # --- app/migrations/__init__.py ---
  : > "$mig_dir/__init__.py"

  echo "Generated: $folder"
done

echo "Done. 10 services created."
