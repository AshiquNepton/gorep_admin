# from django.apps import AppConfig


# class MyappConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'myApp'



import os
from django.apps import AppConfig

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myApp'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true':
            return
        from .ssh_tunnel import start_tunnel
        try:
            start_tunnel()
        except Exception as e:
            import logging
            logging.getLogger('ssh_tunnel').error(f"[SSH Tunnel] Failed to start: {e}")