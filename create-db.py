from app import create_app, db
from app.auth.models import User
flask_app = create_app()
with flask_app.app_context():
    # create the database and the db table
    print("create db");
    db.create_all()
    if not User.query.filter_by(user_name='admin').first():
        User.create_user(user='admin',
                         email='admin@user.com',
                         password='admin')
    # commit the changes
    db.session.commit()
