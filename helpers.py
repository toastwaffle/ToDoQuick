"""
helpers.py

Various helper functions
"""

import smtplib
from email.mime.text import MIMEText
from flask import render_template, session, flash, request
import random
import string
from todoquick import app
import datetime
import pytz
from database import *

def send_email(email, subject, user):
    msg = MIMEText(render_template('emails/%s.email' % email, user=user))
    msg['Subject'] = subject
    msg['To'] = user.email
    msg['From'] = 'todoquick@toastwaffle.com'

    s = smtplib.SMTP('localhost')
    s.sendmail('todoquick@toastwaffle.com', user.email, msg.as_string())
    s.quit()


def random_key(length):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(length))

def is_logged_in():
    if 'username' not in session:
        try:
            cookie = request.cookies['todoquick-remember'].split(':')
            user = User.query.filter_by(User.username==cookie[0]).first()
            if user.cookiekey == cookie[1]:
                session['username'] = user.username
                session['userid'] = user.id
                return True
        except KeyError:
            pass # avoid writing the next 2 lines twice
        flash('Please log in.', 'warn')
        return False
    else:
        return True

def tagtodicttree(tag, selectedtags=[]):
    return {'id': tag.id,
            'name': tag.name,
            'parent': tag.project_id,
            'selected': tag in selectedtags,
            'children': [tagtodicttree(x, selectedtags) for x in tag.children.all()]}

@app.context_processor
def utility_processor():
    def is_overdue(task):
        if task.end < datetime.datetime.now:
            return True
        else:
            return False
    def get_all(query):
        return query.all()
    def show_datetime(dt, tzstr, format):
        tz = pytz.timezone(tzstr)
        tzdt = tz.fromutc(dt)
        return tzdt.strftime(format)
    def show_date(d, tzstr, format):
        tz = pytz.timezone(tzstr)
        tzdt = tz.fromutc(datetime.datetime.combine(d, datetime.datetime.now().time()))
        return tzdt.strftime(format)
    def get_taglist(selector=[]):
        tags = Tag.query.filter_by(Tag.owner_id == session['user_id']).all()
        return [tagtodicttree(x, selector.tags) for x in tags]
    return dict(is_overdue=is_overdue,
                get_all=get_all,
                show_date=show_date,
                show_datetime=show_datetime,
                get_taglist=get_taglist
                )
