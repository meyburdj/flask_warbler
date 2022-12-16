"""User View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_user_views.py


import os
from unittest import TestCase

from models import db, Message, User, connect_db, Like, Follows, DEFAULT_HEADER_IMAGE_URL, DEFAULT_IMAGE_URL

from flask import session

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

connect_db(app)

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserBaseViewTestCase(TestCase):
    def setUp(self):
        """ Set up for tests """
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()

        m1 = Message(text="m1-text", user_id=u1.id)
        db.session.add_all([m1])
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id

        self.client = app.test_client()

    def tearDown(self):
        """ Clean up after test """
        db.session.rollback()

class UserInfoViewTestCase(UserBaseViewTestCase):
    """ Tests for viewing user info """

    def test_users_listing(self):
        """ Test GET /users route with login """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get('/users')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Here is the user listing page', html)

    def test_users_listing_w_query(self):
        """ Test GET /users route with query string with login """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get('/users?q=u1')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Here is the user listing page', html)
            self.assertNotIn('u2', html)

    def test_users_listing_wo_auth(self):
        """ Test accessing /users route without authorization """

        with self.client as c:

            resp = c.get("/users", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>Sign up now to get your own personalized timeline!</p>', html)
            self.assertIn("Access unauthorized.", html)

    def test_user_profile(self):
        """ Test user profile page with login """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get(f'/users/{self.u2_id}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Here is the user profile page', html)
            self.assertIn(f'<h4 id="sidebar-username">@u2</h4>', html)


class UserFollowViewTestCase(UserBaseViewTestCase):
    """ Tests for viewing user follows """

    def test_user_following_page(self):
        """ Test GET /users/<user_id>/following """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            u2.following.append(u1)
            db.session.commit()

            resp = c.get(f'/users/{self.u2_id}/following')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@u1</p>', html)
            self.assertIn('Here is the following page', html)

    def test_user_following_page_wo_auth(self):
        """ Test accessing /users/<user_id>/following route without authorization """

        with self.client as c:

            resp = c.get(f'/users/{self.u2_id}/following', follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>Sign up now to get your own personalized timeline!</p>', html)
            self.assertIn("Access unauthorized.", html)

    def test_user_followers_page(self):
        """ Test GET /users/<user_id>/followers """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            u1.following.append(u2)
            db.session.commit()

            resp = c.get(f'/users/{self.u2_id}/followers')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@u1</p>', html)
            self.assertIn('Here is the followers page', html)

    def test_user_followers_page_wo_auth(self):
        """ Test accessing /users/<user_id>/followers route without authorization """

        with self.client as c:

            resp = c.get(f'/users/{self.u2_id}/followers', follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>Sign up now to get your own personalized timeline!</p>', html)
            self.assertIn("Access unauthorized.", html)

    def test_follow_user_post(self):
        """ Test POST route to follow a user """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f'/users/follow/{self.u2_id}', follow_redirects=True)
            html = resp.get_data(as_text=True)

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>@u2</p>', html)
            self.assertIn('Here is the following page', html)
            self.assertIn(u1, u2.followers)

    def test_unfollow_user_post(self):
        """ Test POST route to unfollow a user """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            u1 = User.query.get(self.u1_id)
            u2 = User.query.get(self.u2_id)

            u2.followers.append(u1)
            db.session.commit()

            resp = c.post(f'/users/stop-following/{self.u2_id}', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<p>@u2</p>', html)
            self.assertIn('Here is the following page', html)
            self.assertNotIn(u1, u2.followers)

class UserUpdateViewTestCase(UserBaseViewTestCase):
    """ Tests for updating a user """

    def test_update_user_form(self):
        """ Test display of user update form """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get('/users/profile')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<h2 class="join-message">Edit Your Profile.</h2>', html)
            self.assertIn(
                '<input class="form-control" id="username" name="username" placeholder="Username" required type="text" value="u1">',
                html
            )

    def test_update_user_form_submit(self):
        """ Test submission of user update form """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            d={
                "username": 'u1',
                "email": 'u1new@email.com',
                "image_url": DEFAULT_IMAGE_URL,
                "header_image_url": DEFAULT_HEADER_IMAGE_URL,
                "bio": 'what bio',
                "location": 'Hawaii',
                "password": "password"
            }
            resp = c.post('/users/profile', data=d, follow_redirects=True)
            html = resp.get_data(as_text=True)

            u1 = User.query.get(self.u1_id)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Here is the user profile page', html)
            self.assertIn('Hawaii', html)
            self.assertIn('what bio', html)
            self.assertEqual(u1.location, 'Hawaii')
            self.assertEqual(u1.bio, 'what bio')
            self.assertEqual(u1.email, 'u1new@email.com')
            self.assertEqual(u1.username, 'u1')

class UserDeleteViewTestCase(UserBaseViewTestCase):
    """ Tests for deleting a user """

    def test_user_delete(self):
        """ Test POST to /users/delete route """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post('/users/delete', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<h2 class="join-message">Join Warbler today.</h2>', html)
            self.assertIn("User successfully deleted :(", html)
            self.assertIsNone(User.query.get(self.u1_id))

    def test_user_delete_wo_auth(self):
        """ Test POST to /users/delete route without authentication """

        with self.client as c:

            resp = c.post('/users/delete', follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>Sign up now to get your own personalized timeline!</p>', html)
            self.assertIn("Access unauthorized.", html)

class UserLikesListTestCase(UserBaseViewTestCase):
    """ Tests for listing a user's likes """

    def test_user_likes_page(self):
        """ Test GET to /users/<int:user_id>/likes """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            m1 = Message.query.get(self.m1_id)
            u1 = User.query.get(self.u1_id)
            u1.liked_messages.append(m1)
            db.session.commit()

            resp = c.get(f"/users/{self.u1_id}/likes")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('m1-text', html)

class UserSignupTestCase(UserBaseViewTestCase):
    """ Tests for when a user attempts to signup or visit the signup page """

    def test_signup_page(self):
        """ Test GET to /signup """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get("/signup")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<h2 class="join-message">Join Warbler today.</h2>', html)
            self.assertNotIn(CURR_USER_KEY, session)

    def test_signup_submission(self):
        """ Test POST to /signup """

        with self.client as c:

            d = {
                "username": "test_4",
                "password": "password",
                "email": "test_4@email.com",
                "image_url": ""
            }

            resp = c.post("/signup", data=d, follow_redirects=True)
            html = resp.get_data(as_text=True)

            u4 = User.query.filter_by(username = "test_4").one()

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(session[CURR_USER_KEY], u4.id)
            self.assertIn('<p>@test_4</p>', html)

    def test_signup_submission_repeat_name(self):
        """ Test POST to /signup with repeat username """

        with self.client as c:

            d = {
                "username": "u1",
                "password": "password",
                "email": "test_4@email.com",
                "image_url": ""
            }

            resp = c.post('/signup', data=d, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Username already taken', html)
            self.assertIn('<h2 class="join-message">Join Warbler today.</h2>', html)
            self.assertNotIn(CURR_USER_KEY, session)

class UserLoginViewTestCase(UserBaseViewTestCase):
    """ Tests for when a user attempts to login or visit the login page """

    def test_login_form(self):
        """ Test GET to /login """

        with self.client as c:
            resp = c.get('/login')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<h2 class="join-message">Welcome back.</h2>', html)
            self.assertIn('<form method="POST" id="user_form">', html)

    def test_login_submission(self):
        """ Test POST to /login with valid credentials """

        with self.client as c:
            d = {
                "username": "u1",
                "password": "password",
            }

            resp = c.post('/login', data=d, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Hello, u1!", html)
            self.assertIn('<p>@u1</p>', html)
            self.assertIn('Here is the home page', html)
            self.assertIn(CURR_USER_KEY, session)
            self.assertEqual(session[CURR_USER_KEY], self.u1_id)

    def test_invalid_pwd_login_submission(self):
        """ Test POST to /login with invalid password """

        with self.client as c:
            d = {
                "username": "u1",
                "password": "pAsSwOrD",
            }

            resp = c.post('/login', data=d, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<h2 class="join-message">Welcome back.</h2>', html)
            self.assertIn('<form method="POST" id="user_form">', html)
            self.assertIn('Invalid credentials', html)
            self.assertNotIn(CURR_USER_KEY, session)

    def test_invalid_user_login_submission(self):
        """ Test POST to /login with invalid username """

        with self.client as c:
            d = {
                "username": "u1000",
                "password": "password",
            }

            resp = c.post('/login', data=d, follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<h2 class="join-message">Welcome back.</h2>', html)
            self.assertIn('<form method="POST" id="user_form">', html)
            self.assertIn('Invalid credentials', html)
            self.assertNotIn(CURR_USER_KEY, session)


class UserLogoutViewTestCase(UserBaseViewTestCase):
    """ Tests for logging out a user """

    def test_user_logout(self):
        """ Test POST to /logout """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post('/logout', follow_redirects=True)
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('You have been succesfully logged out!', html)
            self.assertIn('<h2 class="join-message">Welcome back.</h2>', html)
            self.assertIn('<form method="POST" id="user_form">', html)
            self.assertNotIn(CURR_USER_KEY, session)


class UserHomepageViewTestCase(UserBaseViewTestCase):
    """ Tests for home page """

    def test_user_homepage(self):
        """ Test homepage for logged in user """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get('/')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Here is the home page', html)
            self.assertIn('<p>@u1</p>', html)


    def test_user_homepage_logged_out(self):
        """ Test homepage for logged out user """

        with self.client as c:
            resp = c.get('/')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                '<p>Sign up now to get your own personalized timeline!</p>',
                html
            )