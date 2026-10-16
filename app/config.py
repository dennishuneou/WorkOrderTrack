import os

DEBUG = False
SECRET_KEY = 'admin'
SQLALCHEMY_DATABASE_URI  = os.environ['DATABASE_URL']
SQLALCHEMY_TRACK_MODIFICATIONS = False


# Session & Cookie lifetime (6 days)
PERMANENT_SESSION_LIFETIME = timedelta(days=6)
REMEMBER_COOKIE_DURATION = timedelta(days=6)
REMEMBER_COOKIE_HTTPONLY = True
