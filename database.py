"""
database.py

Contains classes for database table objects
"""

from flask.ext.sqlalchemy import SQLAlchemy
from ToDoQuick import app
from ToDoQuick.helpers import *
import bcrypt

db = SQLAlchemy(app)


task_tag_link = db.Table('task-tag-link', db.Model.metadata,
                         db.Column('task_id',
                                   db.Integer,
                                   db.ForeignKey('task.id')
                                   ),
                         db.Column('tag_id',
                                   db.Integer,
                                   db.ForeignKey('tag.id')
                                   )
                         )


project_tag_link = db.Table('project-tag-link', db.Model.metadata,
                         db.Column('project_id',
                                   db.Integer,
                                   db.ForeignKey('project.id')
                                   ),
                         db.Column('tag_id',
                                   db.Integer,
                                   db.ForeignKey('tag.id')
                                   )
                         )


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passhash = db.Column(db.BINARY(60), nullable=False)
    name = db.Column(db.String(120))
    emailkey = db.Column(db.String(64))
    verified = db.Column(db.Boolean)
    timezone = db.Column(db.String(40))

    def __init__(self, username, email, password, name, timezone='UTC'):
        self.username = username
        self.email = email
        self.passhash = bcrypt.hashpw(password, bcrypt.gensalt())
        self.name = name
        self.emailkey = random_key(64)
        self.verified = False
        self.timezone = timezone

    def __repr__(self):
        return '<User %s: %s>' % (self.id, self.username)

    def checkpassword(self, candidate):
        return bcrypt.hashpw(candidate, self.passhash) == self.passhash

    def setpassword(self, password):
        self.passhash = bcrypt.hashpw(password, bcrypt.gensalt())


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start = db.Column(db.Date())
    end = db.Column(db.DateTime())
    completed = db.Column(db.Boolean, default=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User',
                            backref=db.backref('tasks',
                                               lazy='dynamic',
                                               order_by=Task.end
                                               )
                            )

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project',
                              backref=db.backref('tasks',
                                                 lazy='dynamic',
                                                 order_by=Task.end
                                                 )
                              )

    parent_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    parent = db.relationship('Task',
                             remote_side=[id],
                             backref=db.backref('children',
                                                lazy='dynamic',
                                                order_by=Task.end
                                                )
                             )

    tags = db.relationship('Tag',
                           secondary=task_tag_link,
                           backref='tasks',
                           order_by=Task.end
                           )

    def __init__(self,
                 name,
                 description=None,
                 start=None,
                 end=None,
                 project=None,
                 parent=None,
                 owner):
        self.name = name
        self.description = description
        self.start = start
        self.end = end

        if isinstance(project, Project):
            self.project_id = project.id
        else:
            self.project_id = project

        if isinstance(parent, Task):
            self.parent_id = parent.id
        else:
            self.parent_id = parent

        if isinstance(owner, User):
            self.owner_id = owner.id
        else:
            self.owner_id = owner

    def __repr__(self):
        return '<Task %s: %s>' % (self.id, self.name)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    tags = db.relationship('Tag',
                           secondary=task_tag_link,
                           backref='projects',
                           order_by=Project.name
                           )

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User',
                            backref=db.backref('projects',
                                               lazy='dynamic',
                                               order_by=Project.name
                                               )
                            )

    def __init__(self, name, description=None, owner):
        self.name = name
        self.description = description

        if isinstance(owner, User):
            self.owner_id = owner.id
        else:
            self.owner_id = owner

    def __repr__(self):
        return '<Project %s: %s>' % (self.id, self.name)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User',
                            backref=db.backref('tags',
                                               lazy='dynamic',
                                               order_by=Tag.name
                                               )
                            )

    parent_id = db.Column(db.Integer, db.ForeignKey('tag.id'))
    parent = db.relationship('Tag',
                             remote_side=[id],
                             backref=db.backref('children',
                                                lazy='dynamic',,
                                                order_by=Tag.name
                                                )
                             )

    def __init__(self, name, parent=None, owner):
        self.name = name

        if isinstance(parent, Tag):
            self.parent_id = parent.id
        else:
            self.parent_id = parent

        if isinstance(owner, User):
            self.owner_id = owner.id
        else:
            self.owner_id = owner

    def __repr__(self):
        return '<Tag %s: %s>' % (self.id, self.name)
