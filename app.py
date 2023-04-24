import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, CSRFProtectForm, UpdateUserForm, RedirectForm
from models import db, connect_db, User, Message

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ['DATABASE_URL'].replace("postgres://", "postgresql://"))
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
toolbar = DebugToolbarExtension(app)
app.config['WTF_CSRF_ENABLED'] = False


connect_db(app)
db.create_all()


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None

@app.before_request
def add_csrf_form_to_all_pages():
    """Before every route, add CSRF-only form to global object."""

    g.csrf_form = CSRFProtectForm()
    print("CSRF Token:", g.csrf_form.csrf_token._value())

@app.before_request
def add_redirect_form_to_all_pages():
    """ Before every route, add a hidden form that will
    have that routes location for the sake of redirects """

    g.redirect_form = RedirectForm()

@app.before_request
def create_user_likes():
    """ Before every route, populate a list of messages that the user
    likes """

    if CURR_USER_KEY in session:
        g.user_liked_messages = {message.id for message in g.user.liked_messages} #g.user.liked_message_ids
    else:
        g.user_liked_messages = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]



@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        print("I have validated the signup form")    
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        print("I have entered the get portion of the signup route")
        return render_template('users/signup.html', form=form)


# @app.route('/login', methods=["GET", "POST"])
# def login():
#     """Handle user login and redirect to homepage on success."""

#     print("session:", session)
#     print("session[CURR_USER_KEY]:", session.get(CURR_USER_KEY))
#     form = LoginForm()

#     if form.validate_on_submit():
#         print("I have validated the login form")    
#         user = User.authenticate(
#             form.username.data,
#             form.password.data)

#         if user:
#             do_login(user)
#             flash(f"Hello, {user.username}!", "success")
#             return redirect("/")

#         flash("Invalid credentials.", 'danger')
#     print("I have entered the get portion of the login route")
#     return render_template('users/login.html', form=form)

@app.get('/login')
def show_login_form():
    """Show the login form."""

    print("I am in the get login route")
    form = LoginForm()
    return render_template('users/login.html', form=form)

@app.post('/login')
def handle_login_form():
    """Handle the login form submission."""

    print("I am in the post login route")
    form = LoginForm()
    print("there is actually a form here", form)

    if form.validate_on_submit():
        
        print("I have validated_on_submit")
        user = User.authenticate(
            form.username.data,
            form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')
    print("form errors", form.errors)

    return redirect("/login")




@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    form = g.csrf_form

    if form.validate_on_submit():
        print("I have validated the logout form")
        do_logout()

    flash("You have been succesfully logged out!")
    return redirect("/login")


##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    g.redirect_form.redirect_location.data = f'/users/{user_id}'
    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user)


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    # Looks like obj automatically omits filling in PasswordField
    form = UpdateUserForm(obj=g.user)

    if form.validate_on_submit():
        user = User.authenticate(
            g.user.username,
            form.password.data
        )

        if user:
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data
            user.header_image_url = form.header_image_url.data
            user.bio = form.bio.data
            user.location = form.location.data

            db.session.add(user)
            db.session.commit()

            return redirect(f'/users/{user.id}')
        else:
            form.password.errors = ['Invalid password!']

    return render_template('/users/edit.html', form=form)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = g.csrf_form

    if form.validate_on_submit():
        do_logout()

        User.query.filter(User.id == g.user.id).delete()
        db.session.commit()

        flash('User successfully deleted :(', 'success')
        return redirect("/signup")

    flash('Access unauthorized', 'danger')
    return redirect('/')


@app.get('/users/<int:user_id>/likes')
def show_liked_messages(user_id):
    """ Show liked messages of user """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    g.redirect_form.redirect_location.data = f'/users/{user_id}/likes'
    user = User.query.get_or_404(user_id)

    return render_template('users/liked.html', messages=user.liked_messages)


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    g.redirect_form.redirect_location.data = f'/messages/{message_id}'
    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = g.csrf_form

    if form.validate_on_submit():
        msg = Message.query.get_or_404(message_id)

        if g.user.id == msg.user_id:
            db.session.delete(msg)
            db.session.commit()

            flash('Message successfully deleted.', 'success')
            return redirect(f"/users/{g.user.id}")
    flash("Access unauthorized.", "danger")
    return redirect(f'/messages/{message_id}')

@app.post('/messages/<int:message_id>/like')
def like_message(message_id):
    """ like message by user """

    if not g.user:
        flash("access unauthorized.", "danger")
        return redirect("/")

    form = g.redirect_form

    if form.validate_on_submit():
        msg = Message.query.get_or_404(message_id)
        msg.likers.append(g.user)
        db.session.commit()

    return redirect(form.redirect_location.data)

@app.post('/messages/<int:message_id>/unlike')
def unlike_message(message_id):
    """ unlike message by user """

    if not g.user:
        flash("access unauthorized.", "danger")
        return redirect("/")

    form = g.redirect_form

    if form.validate_on_submit():
        msg = Message.query.get_or_404(message_id)
        msg.likers.remove(g.user)
        db.session.commit()

    return redirect(form.redirect_location.data)


##############################################################################
# Homepage and error pages


@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        g.redirect_form.redirect_location.data = '/'

        users = g.user.following + [g.user]
        user_ids = [user.id for user in users]
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(user_ids))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
