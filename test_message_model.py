"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows, connect_db, Like

from sqlalchemy.exc import IntegrityError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

connect_db(app)

db.drop_all()
db.create_all()


class MessageModelTestCase(TestCase):
    def setUp(self):
        """ Set up before each test """

        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

        self.client = app.test_client()

    def tearDown(self):
        """ Tear down after each test """

        db.session.rollback()



    def test_new_message(self):
        """ create a message instance and test it's properties """

        u1 = User.query.get(self.u1_id)

        new_message = Message(text = "This is a test message", user_id = u1.id)

        db.session.add(new_message)
        db.session.commit()

        new_message_db = Message.query.get(new_message.id)

        #testing message table
        self.assertEqual(new_message_db, new_message)
        self.assertEqual(new_message_db.text, "This is a test message")
        

        #testing user to message relationship
        self.assertEqual(new_message_db.user, u1)
        self.assertEqual(len(new_message_db.likers), 0)

    def test_new_invalid_message(self):
        """ Test creating messages with invalid inputs """

        new_message_no_text = Message(text = None, user_id=self.u1_id)

        with self.assertRaises(IntegrityError):
            db.session.add(new_message_no_text)
            db.session.commit()
        db.session.rollback()

        new_message_no_user = Message(text = "This is text", user_id=None)

        with self.assertRaises(IntegrityError):
            db.session.add(new_message_no_user)
            db.session.commit()
        db.session.rollback()

        new_message_non_existent_user = Message(text = "This is also text", user_id=0)

        with self.assertRaises(IntegrityError):
            db.session.add(new_message_non_existent_user)
            db.session.commit()
        db.session.rollback()

    



#TODO:
"""
- Test is_liked_by
- Test adding new message
- Test adding new invalid message
- Test liking/unliking message
- Test cascading delete?
    - Delete a user and all of their messages/likes should be gone
"""


    # def test_user_model(self):
    #     """ Test users created in setup """

    #     u1 = User.query.get(self.u1_id)

    #     # User should have no messages & no followers
    #     self.assertEqual(len(u1.messages), 0)
    #     self.assertEqual(len(u1.followers), 0)

    # def test_default_images(self):
    #     """ Test population of default images on signup """

    #     u1 = User.query.get(self.u1_id)

    #     #User should have the default images for both profile and header
    #     self.assertEqual(u1.image_url, DEFAULT_IMAGE_URL)
    #     self.assertEqual(u1.header_image_url, DEFAULT_HEADER_IMAGE_URL)

    # def test_is_following(self):
    #     """ Test the User.is_following method """

    #     u1 = User.query.get(self.u1_id)
    #     u2 = User.query.get(self.u2_id)

    #     self.assertFalse(u1.is_following(u2))

    #     u1.following.append(u2)
    #     db.session.commit()

    #     self.assertTrue(u1.is_following(u2))
    #     self.assertFalse(u2.is_following(u1))

    # def test_is_followed_by(self):
    #     """ Test the User.is_followed_by method """

    #     u1 = User.query.get(self.u1_id)
    #     u2 = User.query.get(self.u2_id)

    #     self.assertFalse(u1.is_followed_by(u2))

    #     u1.followers.append(u2)
    #     db.session.commit()

    #     self.assertTrue(u1.is_followed_by(u2))
    #     self.assertFalse(u2.is_followed_by(u1))


    # def test_user_signup_method(self):
    #     """ creates a user and tests that the user is created
    #     with the correct information """

    #     u3 = User.signup("u3", "u3@email.com", "password", None)

    #     db.session.commit()

    #     u3_in_db = User.query.get(u3.id)

    #     self.assertEqual(u3, u3_in_db)
    #     self.assertEqual(len(u3_in_db.messages), 0)
    #     self.assertEqual(len(u3_in_db.followers), 0)
    #     self.assertEqual(len(u3_in_db.following), 0)
    #     self.assertEqual(len(u3_in_db.liked_messages), 0)
    #     self.assertNotEqual('password', u3_in_db.password)

    # def test_invalid_user_signups(self):
    #     """ Test signing up users with invalid inputs """

    #     # Test signup with repeat username
    #     u1_repeat_name = User.signup("u1", "not_u1@email.com", "password", None)

    #     with self.assertRaises(IntegrityError):
    #         db.session.commit()

    #     db.session.rollback()

    #     # Test signup with repeat email
    #     u1_repeat_email = User.signup("u1_diff", "u1@email.com", "password", None)

    #     with self.assertRaises(IntegrityError):
    #         db.session.commit()

    #     db.session.rollback()