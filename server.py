#!/usr/bin/python3
"""Simple Flask-based Bittrex API wrapper server."""
import os

from bittrex import fetch
from flask import (Flask, current_app, redirect, render_template, request,
                   send_from_directory, session, url_for)
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired
from werkzeug.security import check_password_hash


app = Flask(__name__)
app.secret_key = ''
app.config['UPLOAD_FOLDER'] = 'archive'
hashed_pass = ''
hashed_name = ''


class LoginForm(FlaskForm):
    """Basic login form."""

    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Log in to the website."""
    if 'username' in session:
        if request.method == 'GET':
            return redirect(url_for('index'))
    form = LoginForm()
    error = False
    if form.validate_on_submit():
        if check_password_hash(hashed_name, form.username.data) and\
                check_password_hash(hashed_pass, form.password.data):
            session['username'] = form.username.data
            return redirect(url_for('index'))
        else:
            error = True
    return render_template('login.html', form=form, error=error)


@app.route('/logout')
def logout():
    """Log out from the website."""
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/uploads/<path:filename>')
def download(filename):
    """Download a single file."""
    uploads = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'])
    return send_from_directory(directory=uploads, filename=filename)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Show the main page."""
    if 'username' in session:
        if request.method == 'GET':
            return render_template('index.html',
                                   name=session['username'],
                                   get=True)
        elif request.method == 'POST':
            result = fetch(request.form['from'],
                           request.form['to'],
                           request.form['coin'])
            return render_template('index.html',
                                   name=session['username'],
                                   download=result)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
