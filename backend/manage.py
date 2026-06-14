#!/usr/bin/env python
"""Точка входа командной строки Django (migrate, runserver, shell и др.)."""
import os
import sys


def main():
    """Парсит argv и передаёт управление Django management-командам."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classified_ads.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
