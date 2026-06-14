"""
Точка входа WSGI для продакшен-развёртывания проекта classified_ads.

WSGI config for classified_ads project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classified_ads.settings')

application = get_wsgi_application()
