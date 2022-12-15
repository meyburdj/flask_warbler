"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows, connect_db, DEFAULT_IMAGE_URL, DEFAULT_HEADER_IMAGE_URL

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


class UserModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

        self.client = app.test_client()

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        u1 = User.query.get(self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

    def test_default_images(self):
        u1 = User.query.get(self.u1_id)
        

        #User should have the default images for both profile and header
        self.assertEqual(u1.image_url, DEFAULT_IMAGE_URL)
        self.assertEqual(u1.header_image_url, DEFAULT_HEADER_IMAGE_URL)

    def test_user_signup_method(self):
        """ creates a user and tests that the user is created with the correct information """
        u3 = User.signup("u3", "u3@email.com", "password", None)

        db.session.commit()

        u3_in_db = User.query.get(u3.id)

        self.assertEqual(u3, u3_in_db)
        self.assertEqual(len(u3_in_db.messages), 0)
        self.assertEqual(len(u3_in_db.followers), 0)
        self.assertEqual(len(u3_in_db.following), 0)
        self.assertEqual(len(u3_in_db.liked_messages), 0)

    def test_user_signup_invalid_username(self):
        """ creates a user that has a non-unique name and tests for failure """

        u1_repeat_name = User.signup("u1", "not_u1@email.com", "password", None)
        

        with self.assertRaises(IntegrityError):
            db.session.commit()





#test that an invalid entry responds with an error 
#error 1 user.signup = use of non-unique name


#error 2 = user of none entry in nullable=false



#test default image


#test authenticate 


#test is_followed_by


#test is_following