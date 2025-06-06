# app/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

bootstrap = Bootstrap()
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'authentication.do_login'
login_manager.session_protection = 'strong'

def create_app():    

    app = Flask(__name__)
    app.secret_key = 'Neousys@0709'
    #configuration = os.path.join(os.getcwd(), 'config', config_type+'.py')
    app.config.from_pyfile("config.py")
    bootstrap.init_app(app)
    db.init_app(app)    #bind the database to Flask app
    login_manager.init_app(app)     #Initialize login manager
    bcrypt.init_app(app)    #Initialize bcrypt
   
    from app.asset import main    #import blueprint
    app.register_blueprint(main)    #register blueprint

    from app.auth import authentication     #import blueprint
    app.register_blueprint(authentication)  #register blueprint

    from app.auth.forms import get_username
    @app.template_filter('usersname')
    def usersname(id: int) ->str:
        return get_username(id)

    return app

