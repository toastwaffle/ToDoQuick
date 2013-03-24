#!/usr/bin/env python2

from flask import Flask, session, redirect, url_for, escape, request, render_template, send_from_directory
import os
import datetime
import json
import re
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://todoquick:qWxUSx33rmev3snT@localhost/todoquick'
app.secret_key = '<%\xd9\xfb\xbc )\xf6\xb1\xb9~:{g\x04Cp\xf7X\xca\xf5\xc0)\xee'

from database import *
from helpers import *
from paginator import Paginator


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html')


@app.route('/login/', methods=['POST'])
def login():
    user = User.query.filter((User.username==request.form['username']) | (User.email==request.form['username'])).first()
    if not user:
        flash("Username or password not recognised. Please try again", 'error')
        return redirect(url_for('index'))
    else:
        if user.checkpassword(request.form['password']):
            session['username'] = user.username
            session['userid'] = user.id
            session['timezone'] = user.timezone

            flash("You are now logged in.", 'info')

            resp = redirect(url_for('dashboard'))

            try:
                if request.form['remember']=='true':
                    user.cookiekey = random_key(64)
                    resp.setcookie('todoquick-remember', user.username+':'+user.cookiekey)
            except KeyError:
                pass # NameError just means the box isn't ticked

            return resp
        else:
            flash("Username or password not recognised. Please try again", 'error')
            return redirect(url_for('index'))


@app.route('/logout/')
def logout():
    session.pop('username', None)
    session.pop('userid', None)
    return redirect(url_for('index'))


@app.route('/register/', methods=['POST'])
def register():
    user = User.query.filter((User.username==request.form['username'])).first()
    if user:
        flash("Username is already in use.", 'error')
        return render_template('index.html',
                               css=url_for('static', filename='style.css'),
                               register_form=request.form
                              )

    user = User.query.filter((User.email==request.form['email'])).first()
    if user:
        flash("Email Address is already in use.", 'error')
        return render_template('index.html',
                               css=url_for('static', filename='style.css'),
                               register_form=request.form
                              )

    if not re.match('^[a-zA-Z0-9\.]*$', request.form['username']):
        flash("Username invalid. Please use only alphanumeric characters and periods.", 'error')
        return render_template('index.html',
                               css=url_for('static', filename='style.css'),
                               register_form=request.form
                              )

    user = User(request.form['username'],
                request.form['email'],
                request.form['password'],
                request.form['name'],
               )
    db.session.add(user)
    db.session.commit()

    send_email('welcome', 'Welcome to ToDoQuick', user)
    flash('A message has been sent to %s. Please check your email for further instructions.' % user.email, 'info')

    return redirect(url_for('index'))


@app.route('/verify/<emailaddr>/<key>/')
def verify(emailaddr,key):
    user = User.query.filter(User.email==emailaddr).first()
    if not user:
        flash('Identity could not be verified.', 'error')
        return redirect(url_for('index'))

    if user.emailkey == key:
        user.verified = True
        user.emailkey = None
        db.session.commit()
        flash('Registration Complete. Welcome to ToDoQuick!', 'info')
        flash("Please log in.", 'info')
        return redirect(url_for('index'))
    else:
        flash('Email could not be verified. <a href="%s">Re-send verifcation email?</a>' % url_for('reverify', email=emailaddr), 'error')
        return redirect(url_for('index'))


@app.route('/reverify/', methods=['POST', 'GET'])
@app.route('/reverify/<emailaddr>/')
def reverify(emailaddr=None):
    if emailaddr is None or request.method == 'GET':
        return render_template('reverify.html')
    else:
        if request.method == 'POST':
            emailaddr = request.form['email']

        user = User.query.filter(Useremail==emailaddr).first()
        if not user:
            flash('Could not re-send email verification.', 'error')
        return redirect(url_for('index'))

        user.emailkey = random_key(64)
        db.session.commit()

        send_email('verifyemail', 'Verify ToDoQuick Email', user)
        flash('A message has been sent to %s. Please check your email for further instructions.' % user.email, 'info')
        return redirect(url_for('index'))


@app.route('/forgotpassword/', methods=['GET'])
def forgotpassword():
    return render_template('forgotpassword.html')


@app.route('/forgotpassword/', methods=['POST'])
@app.route('/forgotpassword/<emailuser>/')
def sendforgotpassword(emailuser=None):
    if request.method == 'POST':
        emailuser = request.form['emailuser']

    user = User.query.filter((User.username==emailuser) | (User.email==emailuser)).first()
    if not user:
        flash("Username/email not recognised. Please try again", 'error')
        return redirect(url_for('index'))

    user.emailkey = random_key(64)
    db.session.commit()

    send_email('forgotpassword', '[ToDoQuick] Forgotten Password', user)
    flash('A message has been sent to %s. Please check your email for further instructions.' % user.email, 'info')
    return redirect(url_for('index'))


@app.route('/forgotpassword/<emailaddr>/<key>/', methods=['POST', 'GET'])
def changeforgotpassword(emailaddr, key):
    user = User.query.filter(User.email==emailaddr).first()
    if not user:
        flash('Identity could not be verified.', 'error')
        return redirect(url_for('index'))

    if user.emailkey == key:
        if request.method == 'POST':
            user.setpassword(request.form['password'])
            user.emailkey = None
            db.session.commit()

            session['username'] = user.username
            session['userid'] = user.id
            session['timezone'] = user.timezone

            flash('Your password has been changed.', 'info')
            flash("You are now logged in.", 'info')

            return redirect(url_for('dashboard'))
        else:
            return render_template('changeforgotpassword.html')
    else:
        flash('Identity could not be verified. <a href="%s">Re-send password reset email?</a>' % url_for('sendforgotpassword', emailuser=emailaddr), 'error')
        return redirect(url_for('index'))


@app.route('/rememberpassword/<emailuser>/')
def rememberpassword(emailuser):
    user = User.query.filter((User.username==emailuser) | (User.email==emailuser)).first()
    if not user:
        flash("Username/email not recognised. Please try again", 'error')
        return redirect(url_for('index'))

    user.emailkey = None
    db.session.commit()

    flash('Password reset request cancelled.', 'info')
    flash('Please log in.', 'info')

    return redirect(url_for('index'))


@app.route('/dashboard/')
@app.route('/dashboard/<int:theyear>/<int:themonth>/<int:theday>/')
def dashboard(theyear=None, themonth=None, theday=None):
    try:
        if not is_logged_in():
            return redirect(url_for('index'))

        tz = pytz.timezone(session['timezone'])

        if theyear is not None:
            tzdate = datetime.datetime(theyear,
                                       themonth,
                                       theday,
                                       tzinfo=tz)
        else:
            try:
                tzdate = datetime.datetime(int(request.args['date'][0:4]),
                                           int(request.args['date'][5:7]),
                                           int(request.args['date'][8:10]),
                                           tzinfo=tz
                                           )
            except KeyError:
                tznow = tz.fromutc(datetime.datetime.utcnow())
                tzdate = tznow.replace(hour=0,
                                       minute=0,
                                       second=0,
                                       microsecond=0)

        date = tzdate.astimezone(pytz.utc)

        datedtasklist = Task.query.filter((Task.owner_id==session['userid']) & (Task.parent == None) & ((Task.start == None) | (Task.start <= date)) & (Task.end != None)).order_by(Task.end).all()

        undatedtasklist = Paginator(Task.query.filter((Task.owner_id==session['userid']) & (Task.parent == None) & ((Task.start == None) | (Task.start <= date)) & (Task.end == None)).order_by(Task.id).all())

        today = date.strftime('%Y-%m-%d')

        day_before = tzdate - datetime.timedelta(days=1)
        url_for_day_before = url_for('dashboard',
                                     theyear=day_before.year,
                                     themonth=day_before.month,
                                     theday=day_before.day)

        day_after = tzdate + datetime.timedelta(days=1)
        url_for_day_after = url_for('dashboard',
                                     theyear=day_after.year,
                                     themonth=day_after.month,
                                     theday=day_after.day)

        if undatedtasklist.next:
            url_for_next_page = url_for('dashboard',
                                        theyear=tzdate.year,
                                        themonth=tzdate.month,
                                        theday=tzdate.day,
                                        page=undatedtasklist.next)
        else:
            url_for_next_page = None

        if undatedtasklist.prev:
            url_for_prev_page = url_for('dashboard',
                                        theyear=tzdate.year,
                                        themonth=tzdate.month,
                                        theday=tzdate.day,
                                        page=undatedtasklist.prev)
        else:
            url_for_prev_page = None

        return render_template('dashboard.html',
                                dated=datedtasklist,
                                undated=undatedtasklist,
                                today=today,
                                url_for_day_after=url_for_day_after,
                                url_for_day_before=url_for_day_before,
                                url_for_next_page=url_for_next_page,
                                url_for_prev_page=url_for_prev_page)
    except KeyError as e:
        print "KeyError: %s" % e.strerror
    except NameError as e:
        print "NameError: %s" % e.strerror


@app.route('/search/')
def search():
    try:
        term = request.args['search']
    except KeyError:
        return redirect(request.referrer or url_for('dashboard'))

    tasks = Paginator(Task.query.filter_by(Task.name.match(term) | Task.description.match(term)).all(), 'task')

    tags = Paginator(Task.query.filter_by(Tag.name.match(term)).all(), 'tag')

    projects = Paginator(Project.query.filter_by(Project.name.match(term) | Project.description.match(term)).all, 'project')

    return render_template('searchresults.html',
                           tasks=tasks,
                           tags=tags,
                           projects=projects)


@app.route('/task/<int:id>/')
def task(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    task = Task.query.filter_by(Task.id==tid).first()

    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('dashboard'))

    if task.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    return render_template('task.html', task=task)


@app.route('/task/create/', methods=['POST', 'GET'])
@app.route('/task/create/parent/<int:parent>/', methods=['POST', 'GET'])
@app.route('/task/create/project/<int:project>/', methods=['POST', 'GET'])
def createtask(parent=None, project=None):
    if not is_logged_in():
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            if request.form['start'] != '':
                start = datetime.strptime(request.form['start'], '%Y-%m-%d')
                start = start.replace(tzinfo=pytz.timezone(session['timezone']))
                start = start.astimezone(pytz.utc)
            else:
                start = None
        except KeyError:
            start = None
        except ValueError:
            flash('Start date in wrong format, please use YYYY-MM-DD', 'error')
            return render_template('createtask.html', retry=True, fields=request.form)


        try:
            if request.form['end'] != '':
                end = datetime.strptime(request.form['end'], '%Y-%m-%d %H:%M')
                end = end.replace(tzinfo=pytz.timezone(session['timezone']))
                end = end.astimezone(pytz.utc)
            else:
                end = None
        except KeyError:
            end = None
        except ValueError:
            flash('End date/time in wrong format, please use YYYY-MM-DD HH:MM:SS', 'error')
            return render_template('createtask.html', retry=True, fields=request.form)

        task = Task(session['userid'],
                    request.form['name'],
                    None if request.form['desc'] == '' else request.form['desc'],
                    start,
                    end,
                    project,
                    parent)
        db.session.add(task)
        db.session.commit()

        flash('Task created.', 'info')
        return redirect(url_for('task', id=task.id))

    else:
        return render_template('createtask.html')


@app.route('/task/edit/<int:id>/', methods=['POST', 'GET'])
def edittask(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    task = Task.query.filter_by(Task.id==tid).first()
    projects = Project.query.order_by(Project.name).all()

    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('dashboard'))

    if task.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    if request.method == 'POST':
        try:
            if request.form['start'] != '':
                start = datetime.strptime(request.form['start'], '%Y-%m-%d')
                start = start.replace(tzinfo=pytz.timezone(session['timezone']))
                start = start.astimezone(pytz.utc)
            else:
                start = None
            task.start = start
        except KeyError:
            task.start = None
        except ValueError:
            flash('Start date in wrong format, not changed. Please use YYYY-MM-DD', 'error')

        try:
            if request.form['end'] != '':
                end = datetime.strptime(request.form['end'], '%Y-%m-%d %H:%M')
                end = end.replace(tzinfo=pytz.timezone(session['timezone']))
                end = end.astimezone(pytz.utc)
            else:
                end = None
            task.end = end
        except KeyError:
            task.end = None
        except ValueError:
            flash('End date/time in wrong format, not changed. Please use YYYY-MM-DD HH:MM:SS', 'error')

        task.name = request.form['name']
        task.description = None if request.form['desc'] == '' else request.form['desc']
        task.project_id = request.form['project']

        db.session.commit()

    return render_template('edittask.html', task=task, projects=projects)


@app.route('/task/delete/<int:id>/')
def deletetask(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    task = Task.query.filter_by(Task.id==id).first()

    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('dashboard'))

    if task.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    db.session.delete(task)
    db.session.commit()

    flash('Task deleted.', 'info')

    try:
        if 'task' not in request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('dashboard'))
    except NameError:
        return redirect(url_for('dashboard'))


@app.route('/tags/')
def tags():
    if not is_logged_in():
        return redirect(url_for('index'))

    tags = Tag.query.filter_by(Tag.owner_id==session['userid']).all()

    return render_template('tags.html', tags=tags)


@app.route('/tag/<int:id>/')
def tag(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    tag = Tag.query.filter_by(Tag.id==id).first()

    if not tag:
        flash('Tag not found.', 'error')
        return redirect(url_for('dashboard'))

    if tag.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(url_for('dashboard'))

    tasks = Paginator(tag.tasks.order_by(Task.end).all())

    return render_template('tag.html', tag=tag, tasks=tasks)


@app.route('/tag/create/', methods=['POST', 'GET'])
@app.route('/tag/create/parent/<int:parent>', methods=['POST', 'GET'])
def createtag(parent=None):
    if not is_logged_in():
        return redirect(url_for('index'))

    tag = Tag(session['userid'],
              request.form['name'],
              parent)
    db.session.add(tag)
    db.session.commit()

    return redirect(request.referrer or url_for('dashboard'))


@app.route('/tag/delete/<int:id>/')
def deletetag(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    tag = Tag.query.filter_by(Tag.id==id).first()

    if not tag:
        flash('Tag not found.', 'error')
        return redirect(url_for('dashboard'))

    if tag.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    db.session.delete(tag)
    db.session.commit()

    flash('Tag deleted.', 'info')

    try:
        if 'tag' not in request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('dashboard'))
    except NameError:
        return redirect(url_for('dashboard'))

@app.route('/projects/')
def projects():
    if not is_logged_in():
        return redirect(url_for('index'))

    project = Project.query.filter_by(Project.owner_id==session['userid']).all()

    return render_template('projects.html', projects=projects)


@app.route('/project/<int:id>/')
def project(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    project = Project.query.filter_by(Project.id==id).first()

    if not project:
        if 'delete' not in referrer:
            flash('Project not found.', 'error')
        return redirect(url_for('dashboard'))

    if project.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    tasks = Paginator(project.tasks.order_by(Task.end).all())

    return render_template('project.html', project=project, tasks=tasks)

@app.route('/project/create/', methods=['POST', 'GET'])
def createproject():
    if not is_logged_in():
        return redirect(url_for('index'))

    if request.method == 'POST':
        project = Project(session['userid'],
                          request.form['name'],
                          None if request.form['desc'] == '' else request.form['desc'])
        db.session.add(project)
        db.session.commit()

        flash('Project created.', 'info')
        return redirect(url_for('project', id=project.id))

    else:
        return render_template('createproject.html')

@app.route('/project/edit/<int:id>/', methods=['POST', 'GET'])
def editproject(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    project = Project.query.filter_by(Project.id==id).first()

    if not project:
        if 'delete' not in referrer:
            flash('Project not found.', 'error')
        return redirect(url_for('dashboard'))

    if project.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    if request.method == 'POST':
        project.name = request.form['name']
        project.description = None if request.form['desc'] == '' else request.form['desc']
        db.session.commit()

        flash('Changes Saved.', 'info')

    return render_template('editproject.html', project=project)


@app.route('/project/delete/<int:id>/')
def deleteproject(id):
    if not is_logged_in():
        return redirect(url_for('index'))

    project = Project.query.filter_by(Project.id==id).first()

    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('dashboard'))

    if project.owner_id != session['userid']:
        flash('An error occurred, please try again later', 'error')
        return redirect(request.referrer or url_for('dashboard'))

    db.session.delete(project)
    db.session.commit()

    flash('Project deleted.', 'info')

    return redirect(request.referrer or url_for('dashboard'))


@app.route('/profile/', methods=['POST', 'GET'])
def profile():
    if not is_logged_in():
        return redirect(url_for('index'))

    user = User.query.filter(User.id==session['userid']).first()
    if not user:
        app.logger.error('Could not get user for profile edit')
        return redirect(url_for('logout'))

    if request.method == 'POST':
        if request.form['email'] == '':
            flash('Email cannot be blank.', 'error')
            return render_template('profile.html', user=user)

        if request.form['oldpassword'] != '':
            flash('Please enter your password to make changes.', 'error')
            return render_template('profile.html', user=user)

        if not user.checkpassword(request.form['oldpassword']):
            flash('The password you entered was incorrect, your changes have not been saved.', 'error')
            return render_template('profile.html', user=user)

        if user.email != request.form['email']:
            user.email = request.form['email']
            user.verified = False
            user.emailkey = random_key(64)

            send_email('verifyemail', 'Verify ToDoQuick Email', user)

            flash('A message has been sent to %s to confirm your email. Please check your email for further instructions.' % user.email, 'info')

        if request.form['newpassword'] != '':
            user.setpassword(request.form['newpassword'])

        user.name = request.form['name']

        db.session.commit()

    return render_template('profile.html', user=user)


@app.route('/ajax/completetask/<int:tid>/')
def ajaxcompletetask(tid):
    task = Task.query.filter_by(Task.id==tid).first()

    if 'username' not in session:
        response = {'status': 401, 'message': 'Not logged in'}
    elif not task:
        response = {'status': 404, 'message': 'Task not found'}
    elif task.owner_id != session['userid']:
        response = {'status': 401, 'message': 'Task not owned by user'}
    else:
        task.completed = not task.completed
        db.session.commit()
        response = {'status': 200, 'message': 'Task status changed', 'completed': task.completed}

    return json.dumps(response), response['status']


@app.route('/ajax/changetag/<int:tagid>/task/<int:taskid>/')
@app.route('/ajax/changetag/<int:tagid>/project/<int:projectid>/')
def ajaxchangetag(tagid, taskid=None, projectid=None):
    tag = Tag.query.filter_by(Tag.id==tagid).first()

    if 'username' not in session:
        return json.dumps({'status': 401, 'message': 'Not logged in'}), 401
    elif not tag:
        return json.dumps({'status': 404, 'message': 'Tag not found'}), 404
    elif tag.owner_id != session['userid']:
        return json.dumps({'status': 401, 'message': 'Tag not owned by user'}), 403

    if taskid is not None:
        task = Task.query.filter_by(Task.id==taskid).first()
        if not task:
            return json.dumps({'status': 404, 'message': 'Task not found'}), 404
        elif task.owner_id != session['userid']:
            return json.dumps({'status': 403, 'message': 'Task not owned by user'}), 403
        elif tag in task.tags:
            task.tags.remove(tag)
            db.session.commit()
            return json.dumps({'status': 200, 'message': 'Tag removed successfully', 'hastag': False}), 200
        else:
            task.tags.append(tag)
            db.session.commit()
            return json.dumps({'status': 200, 'message': 'Tag added successfully', 'hastag': True}), 200

    else:
        project = Project.query.filter_by(Project.id==projectid).first()
        if not project:
            return json.dumps({'status': 404, 'message': 'Project not found'}), 404
        elif project.owner_id != session['userid']:
            return json.dumps({'status': 403, 'message': 'Project not owned by user'}), 403
        elif tag in project.tags:
            project.tags.remove(tag)
            db.session.commit()
            return json.dumps({'status': 200, 'message': 'Tag removed successfully', 'hastag': False}), 200
        else:
            project.tags.append(tag)
            db.session.commit()
            return json.dumps({'status': 200, 'message': 'Tag added successfully', 'hastag': True}), 200


@app.route('/ajax/tag/create/', methods=['POST'])
@app.route('/ajax/tag/create/parent/<int:parent>/', methods=['POST'])
def ajaxcreatetag(parent=None):
    if 'username' not in session:
        return json.dumps({'status': 401, 'message': 'Not logged in'}), 401

    tag = Tag(session['userid'],
              request.form['name'],
              parent)
    db.session.add(tag)
    db.session.commit()

    return json.dumps({'status': 200,
                       'message': 'Tag created.',
                       'id': tag.id,
                       'name': tag.name,
                       'parent': tag.parent_id}), 200


@app.route('/ajax/tag/edit/<int:id>/', methods=['POST'])
def ajaxedittag(id):
    tag = Tag.query.filter_by(Tag.id==id).first()

    if 'username' not in session:
        return json.dumps({'status': 401, 'message': 'Not logged in'}), 401
    elif not tag:
        return json.dumps({'status': 404, 'message': 'Tag not found'}), 404
    elif tag.owner_id != session['userid']:
        return json.dumps({'status': 401, 'message': 'Tag not owned by user'}), 403


    if request.form.haskey('name'):
        tag.name = request.form['name']

    if request.form.haskey('project'):
        if request.form['project'] == 'NONE':
            tag.project_id = None
        else:
            tag.project_id = request.form['project']

    db.session.commit()

    return json.dumps({'status': 200,
                       'message': 'Tag created.',
                       'id': tag.id,
                       'name': tag.name,
                       'parent': tag.parent_id}), 200


@app.route('/ajax/gettags/')
def ajaxgettags():
    if 'username' not in session:
        return json.dumps({'status': 401, 'message': 'Not logged in'}), 401

    tags = Tag.query.filter_by(Tag.owner_id == session['user_id']).all()

    return json.dumps({'status': 200,
                       'result': [tagtodicttree(x) for x in tag.children.all()]}), 200


@app.route('/ajax/task/delete/<int:id>/')
def ajaxdeletetask():
    task = Task.query.filter_by(Task.id==tid).first()

    if 'username' not in session:
        response = {'status': 401, 'message': 'Not logged in'}
    elif not task:
        response = {'status': 404, 'message': 'Task not found'}
    elif task.owner_id != session['userid']:
        response = {'status': 401, 'message': 'Task not owned by user'}
    else:
        db.session.delete(task)
        db.session.commit()
        response = {'status': 200, 'message': 'Task deleted'}

    return json.dumps(response), response['status']

@app.route('/ajax/tag/delete/<int:id>/')
def ajaxdeletetag():
    tag = Tag.query.filter_by(Tag.id==tid).first()

    if 'username' not in session:
        response = {'status': 401, 'message': 'Not logged in'}
    elif not tag:
        response = {'status': 404, 'message': 'Tag not found'}
    elif tag.owner_id != session['userid']:
        response = {'status': 401, 'message': 'Tag not owned by user'}
    else:
        db.session.delete(tag)
        db.session.commit()
        response = {'status': 200, 'message': 'Tag deleted'}

    return json.dumps(response), response['status']

@app.route('/ajax/project/delete/<int:id>/')
def ajaxdeleteproject():
    project = Project.query.filter_by(Project.id==tid).first()

    if 'username' not in session:
        response = {'status': 401, 'message': 'Not logged in'}
    elif not project:
        response = {'status': 404, 'message': 'Project not found'}
    elif project.owner_id != session['userid']:
        response = {'status': 401, 'message': 'Project not owned by user'}
    else:
        db.session.delete(project)
        db.session.commit()
        response = {'status': 200, 'message': 'Project deleted'}

    return json.dumps(response), response['status']


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/privacy/')
def privacy():
    return render_template('privacy.html')

@app.route('/terms/')
def terms():
    return render_template('terms.html')
