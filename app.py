from flask import Flask, render_template, redirect, session, flash, url_for
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Feedback
from forms import RegisterForm, LoginForm, FeedbackForm
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Unauthorized


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///feedback"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

app.app_context().push()
connect_db(app)
db.create_all()

toolbar = DebugToolbarExtension(app)

def userCheck(username):
    if 'username' not in session or session['username'] != username:
        raise Unauthorized()


@app.route('/')
def home():
    """Go to home"""
    return redirect('/register')


@app.route('/register', methods=['GET', 'POST'])
def register_user():
    """Create a user form"""
    
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        new_user = User.register(username, password, email, first_name, last_name)
    
        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            form.username.errors.append("Username taken")
            return render_template('register.html', form=form)
        session['username'] = new_user.username
        flash(f"Successfully created {new_user.username}", "success")
        return redirect(f"/users/{new_user.username}")
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login_user():
    """Login user form"""

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.authenticate(username, password)

        if user:
            session['username'] = user.username
            return redirect(f"/users/{user.username}")
        else:
            form.username.errors = ["Invalid username/password."]
    return render_template('login.html', form=form)


@app.route('/users/<username>')
def secret_page(username):
    """Validates a user is signed in"""
    
    userCheck(username)

    user = User.query.filter_by(username=username).first()
    all_feedback = Feedback.query.filter_by(username=username).all()  
    return render_template('secret.html', user=user, all_feedback=all_feedback)


@app.route('/users/<username>/delete', methods=['POST'])
def delete_user(username):
    """Delete user"""
    userCheck(username)

    user = User.query.filter_by(username=username).first() 
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.username}" removed!', 'info')
    return redirect('/logout')


@app.route('/users/<username>/feedback/add', methods=['GET', 'POST'])
def add_feedback(username):
    """Show feedback form/ Add feedback for signed in user"""
    username = session['username']
    userCheck(username)
    
    form = FeedbackForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        new_feedback = Feedback(title=title, content=content, username=session['username'])
        db.session.add(new_feedback)
        db.session.commit()
        return redirect(f"/users/{username}")
    return render_template('feedback.html', form=form)


@app.route('/feedback/<int:feedback_id>/delete', methods=['POST'])
def delete_feedback(feedback_id):
    """Delete selected feedback for signed in user"""
    userCheck(session['username'])
    
    feedback = Feedback.query.filter_by(id=feedback_id).first() 
    if feedback.username == session['username']:
        db.session.delete(feedback)
        db.session.commit()
        flash(f'Feedback removed!', 'info')
        return redirect(f"/users/{session['username']}")
    return redirect(f"/users/{session['username']}")


@app.route('/feedback/<int:feedback_id>/update', methods=['GET', 'POST'])
def update_feedback(feedback_id):
    """Shows and handles updating feedback"""
    userCheck(session['username'])

    edit_feedback = Feedback.query.filter_by(id=feedback_id).first()
    if edit_feedback.username == session['username']:
        form = FeedbackForm()
 
        if form.validate_on_submit():
            title = form.title.data
            content = form.content.data
            edit_feedback.title = title
            edit_feedback.content = content 
            db.session.commit()
            return redirect(f"/users/{session['username']}")
        return render_template('edit-feedback.html', form=form)
    flash("You don't have the permissions to view this page", 'info')
    return redirect('/')



@app.route('/logout')
def logout():
    """Log out user from session"""

    session.pop('username')
    flash('Goodbye', 'info')
    return redirect('/')
