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
        Message.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()

        m1 = Message(
            text = 'This is text',
            user_id = u1.id
        )

        m2 = Message(
            text = 'This is also text',
            user_id = u2.id
        )

        db.session.add_all([m1, m2])
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id
        self.m2_id = m2.id

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

    def test_like_message(self):
        """ Test liking a message """

        u1 = User.query.get(self.u1_id)
        m1 = Message.query.get(self.m1_id)

        u1.liked_messages.append(m1)
        db.session.commit()

        self.assertIn(u1, m1.likers)
        self.assertIn(m1, u1.liked_messages)
        self.assertEqual(len(Like.query.all()), 1)

    def test_unlike_message(self):
        """ Test unliking a message """

        u1 = User.query.get(self.u1_id)
        m1 = Message.query.get(self.m1_id)

        u1.liked_messages.append(m1)
        db.session.commit()

        num_likes_before_unliking = len(Like.query.all())

        u1.liked_messages.remove(m1)
        db.session.commit()

        num_likes_after_unliking = len(Like.query.all())

        self.assertNotIn(u1, m1.likers)
        self.assertNotIn(m1, u1.liked_messages)
        self.assertEqual(num_likes_before_unliking - 1, num_likes_after_unliking)


    def test_is_liked_by(self):
        """ Test the Message.is_liked_by method """

        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)
        m1 = Message.query.get(self.m1_id)

        u1.liked_messages.append(m1)
        db.session.commit()

        self.assertTrue(m1.is_liked_by(u1))
        self.assertFalse(m1.is_liked_by(u2))


    def test_delete_user_deletes_messages(self):
        """ Test that deleting a user deletes their messages """

        u1 = User.query.get(self.u1_id)
        u1_num_messages = len(u1.messages)
        num_messages_before = len(Message.query.all())

        User.query.filter(User.id == u1.id).delete()
        db.session.commit()

        # Querying the message should now return None because message is deleted
        m1 = Message.query.get(self.m1_id)

        num_messages_after = len(Message.query.all())

        self.assertIsNone(m1)
        self.assertEqual(num_messages_before - u1_num_messages, num_messages_after)