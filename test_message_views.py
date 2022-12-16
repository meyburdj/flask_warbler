"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User, connect_db, Like

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


class MessageBaseViewTestCase(TestCase):
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


class MessageAddViewTestCase(MessageBaseViewTestCase):
    """ Add related views """

    def test_add_message(self):
        """ Tests that when a user submits a new message while authorized, that the data is sent and that a redirect occurs """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)

            Message.query.filter_by(text="Hello").one()

    def test_add_message_page(self):
        """ Tests the messages/new page to display form if logged in """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get("/messages/new")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn('<button class="btn btn-outline-success">Add my message!</button>', html)

    def test_add_message_page_wo_auth(self):
        """ Tests the redirect if user tries to get the messages/new route without authorization """
        with self.client as c:

            resp = c.get("/messages/new", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>Sign up now to get your own personalized timeline!</p>', html)
            self.assertIn("Access unauthorized.", html)


    def test_show_message(self):
        """ Tests the messages/<message_id> route to display message if logged in """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get(f"/messages/{self.m1_id}")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p class="single-message">m1-text</p>', html)

class MessageDeleteViewTestCase(MessageBaseViewTestCase):
    """ Delete related views """

    def test_delete_message_proper_user(self):
        """ Test deletion of user's own message """
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(
                f'/messages/{self.m1_id}/delete',
                follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Message successfully deleted', html)
            self.assertIn('Here is the user profile page', html)

            self.assertIsNone(Message.query.get(self.m1_id))

    def test_delete_message_no_user(self):
        """ Test deletion of user's message if you are not logged in """

        with self.client as c:

            resp = c.post(f'/messages/{self.m1_id}/delete',
                follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p>Sign up now to get your own personalized timeline!</p>', html)
            self.assertIn("Access unauthorized.", html)

    def test_delete_message_incorrect_user(self):
        """ Test attempt to delete a message that is not the user's """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post(f'/messages/{self.m1_id}/delete',
                follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p class="single-message">m1-text</p>', html)
            self.assertIn("Access unauthorized.", html)

class MessageLikeViewTestCase(MessageBaseViewTestCase):
    """ Like related views """

    def test_like_message(self):
        """ Test when user likes a message """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post(f'/messages/{self.m1_id}/like',
                data={"redirect_location":f"/messages/{self.m1_id}"},
                follow_redirects=True)

            html = resp.get_data(as_text=True)

            m1 = Message.query.get(self.m1_id)
            u2_likes = User.query.get(self.u2_id).liked_messages

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p class="single-message">m1-text</p>', html)
            self.assertIn(m1, u2_likes)

    def test_unliking_message(self):
        """ Test when user unlikes a message """

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            liked_message = Like(user_id=self.u2_id, message_id=self.m1_id)

            db.session.add(liked_message)
            db.session.commit()

            resp = c.post(f'/messages/{self.m1_id}/unlike',
                data={"redirect_location":f"/messages/{self.m1_id}"},
                follow_redirects=True)

            html = resp.get_data(as_text=True)

            m1 = Message.query.get(self.m1_id)
            u2_likes = User.query.get(self.u2_id).liked_messages

            self.assertEqual(resp.status_code, 200)
            self.assertIn('<p class="single-message">m1-text</p>', html)
            self.assertNotIn(m1, u2_likes)



