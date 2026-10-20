import os
from datetime import timedelta

DEBUG = False
SECRET_KEY = 'admin'
SQLALCHEMY_DATABASE_URI  = os.environ['DATABASE_URL']
SQLALCHEMY_TRACK_MODIFICATIONS = False
REMEMBER_COOKIE_DURATION = timedelta(days=7)