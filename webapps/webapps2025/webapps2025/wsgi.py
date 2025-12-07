"""
WSGI config for webapps2025 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# 🚨 Force the correct settings module (overwrite anything Render sets)
os.environ["DJANGO_SETTINGS_MODULE"] = "webapps.webapps2025.webapps2025.settings"

application = get_wsgi_application()
