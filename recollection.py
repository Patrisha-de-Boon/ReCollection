""" This module handles user authentication and retrieval of user data"""

## This is based on the following sources
## https://github.com/miguelgrinberg/REST-auth/blob/master/api.py
## https://dev.to/carlosemv/dockerizing-a-flask-based-web-camera-application-469m

import os
from flask import Flask, abort, render_template, request, jsonify, g, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
from easyfacenet.simple import facenet
from scipy import spatial

# initialization
APP = Flask(__name__)
APP.config['SECRET_KEY'] = '07e4ad11-3538-42f9-bfd4-6e559eefe22d'
APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
APP.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

##########################################
# Camera
##########################################
# This is based on the following source
# https://github.com/yushulx/web-camera-recorder/blob/master/server.py

@APP.route('/')
def index():
    '''
        Display the index page which contains the UI for this application
    '''
    return render_template('index.html')

##########################################
## Database and Facial Recognition
##########################################

# extensions
DB = SQLAlchemy(APP)
AUTH = HTTPBasicAuth()

class User(DB.Model):
    '''
        A user registered in the database
    '''
    __tablename__ = 'users'
    id = DB.Column(DB.Integer, primary_key=True)
    username = DB.Column(DB.String(32), index=True)
    password_hash = DB.Column(DB.String(64))

    def hash_password(self, password):
        '''
            Generate a hash from a given password
        '''
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        '''
        Verrify that the given password matches the users password (they have the same hash)
        '''
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=600):
        '''
            Generate an authentication token that expires after the set amount of time
        '''
        serial = Serializer(APP.config['SECRET_KEY'], expires_in=expiration)
        return serial.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        '''
            Verify that the authentication token is valid and has not expired
        '''
        serial = Serializer(APP.config['SECRET_KEY'])
        try:
            data = serial.loads(token)
        except SignatureExpired:
            return None    # valid token, but expired
        except BadSignature:
            return None    # invalid token
        user = User.query.get(data['id'])
        return user

class Image(DB.Model):
    '''
        Data about an image associated with a particular recognition
    '''
    __tablename__ = 'images'
    id = DB.Column(DB.Integer, primary_key=True)
    recognition_id = DB.Column(DB.Integer, DB.ForeignKey("recognitions.id"), nullable=False)
    location = DB.Column(DB.VARCHAR)
    encoding = DB.Column(DB.Integer, nullable=False)

class Recognition(DB.Model):
    '''
        The data for people who have been recognized by the system
    '''
    __tablename__ = 'recognitions'
    id = DB.Column(DB.Integer, primary_key=True)
    user_id = DB.Column(DB.Integer, DB.ForeignKey("users.id"), nullable=False)
    name = DB.Column(DB.String(32))
    encoding = DB.Column(DB.Integer, nullable=False, index=True)

    def recalculate(self):
        '''
            recalculate the average encoding for this person by taking
            the average encoding of each of their images
        '''
        images = Image.query.filter_by(recognition_id=self.id).all()

        if images is not None and len(images) > 0:
            sum_encodings = 0
            for image in images:
                sum_encodings += image.encoding
            self.encoding = sum/len(images)


@AUTH.verify_password
def verify_password(username_or_token, password):
    '''
        Verify that the given password is valid for the user with
        the specified username or authentication token
    '''
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@APP.route('/api/users', methods=['POST'])
def new_user():
    '''
        Register a new user in the database
    '''
    username = request.json.get('username')
    password = request.json.get('password')
    print("username: " + username)
    print("password: " + password)
    if username is None or password is None:
        abort(400)    # missing arguments
    if not User.query.filter_by(username=username).first() is None:
        abort(400)    # existing user
    user = User(username=username)
    user.hash_password(password)
    DB.session.add(user)
    DB.session.commit()
    return (jsonify({'username': user.username}), 201,
            {'Location': url_for('get_user', user_id=user.id, _external=True)})


@APP.route('/api/users/<int:user_id>')
def get_user(user_id):
    '''
        Get a user with the given id in the database
    '''
    user = User.query.get(user_id)
    if not user:
        abort(400)
    return jsonify({'username': user.username})


@APP.route('/api/token')
@AUTH.login_required
def get_auth_token():
    '''
        Generate and return a jsonified authentication token for the logged in user
    '''
    token = g.user.generate_auth_token(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})


@APP.route('/api/recognitions', methods=['POST'])
@AUTH.login_required
def new_recognition():
    '''
        Register a new recognition with the currently logged in user
    '''
    name = request.json.get('name')
    encoding = request.json.get('encoding')
    if encoding is None:
        abort(400)    # missing arguments
    recognition = Recognition(name=name, encoding=encoding, user_id=g.user.id)
    DB.session.add(recognition)
    DB.session.commit()
    return (jsonify({'name': recognition.name}), 201,
            {'Location': url_for('get_recognition', recognition_id=recognition.id, _external=True)})

@APP.route('/api/recognitions')
@AUTH.login_required
def get_recognitions():
    '''
        Get the ids of Recognitions with the information specified in the request.
        Must specify a name in the request
    '''
    name = request.json.get('name')
    if name is None:
        abort(400)
    recognitions = Recognition.query.filter_by(user_id=g.user.id).filter_by(name=name).all()

    ids = ""
    first = True
    for recognition in recognitions:
        if not first:
            ids += ","
        else:
            first = False
        ids += recognition.id

    return jsonify({'recognition_ids': recognitions})

@APP.route('/api/recognitions/<int:recognition_id>')
@AUTH.login_required
def get_recognition_by_id(recognition_id):
    '''
        Get a recognition with the given id in the database
    '''
    if recognition_id == -1:
        abort(400)
    recognition = Recognition.query.get(recognition_id)
    if not recognition:
        abort(404)
    if recognition.user_id == g.user.id:
        return jsonify({'name': recognition.name})
    else:
        abort(401)

@APP.route('/api/images', methods=['POST'])
@AUTH.login_required
def new_image():
    '''
        Register a new recognition with the currently logged in user
    '''
    recognition_id = request.json.get('recognition_id')
    location = request.json.get('location')
    image_file = request.files['image']
    if recognition_id is None or image_file is None:
        abort(400)    # missing arguments
    aligned = facenet.align_face(image_file)
    encoding = facenet.embedding(aligned)[0]

    image = Image(recognition_id=recognition_id, encoding=encoding, location=location)
    DB.session.add(image)
    DB.session.commit()
    return (jsonify({'encoding': image.encoding}), 201,
            {'Location': url_for('get_image', image_id=image.id, _external=True)})


@APP.route('/api/images/<int:image_id>')
@AUTH.login_required
def get_image_by_id(image_id):
    '''
        Get a image with the given id in the database
    '''
    if image_id == -1:
        abort(400)
    image = Image.query.get(image_id)
    if not image:
        abort(404)

    recognition = Recognition.query.get(image.registration_id)
    if not recognition:
        abort(404)

    if recognition.user_id == g.user.id:
        return jsonify({'encoding': image.encoding, 'location': image.location})
    else:
        abort(401)

@APP.route('/api/recognize')
@AUTH.login_required
def recognize():
    '''
        See if this user recognizes the given image
    '''
    threshold = 0.7
    images = request.files['image']
    aligned = facenet.align_face(images)

    if aligned == images:
        return jsonify({'is_person': False})

    encoding = facenet.embedding(aligned)[0]
    recognitions = Recognition.query.filter_by(user_id=g.user.id).all()

    closest_diff = 1
    closest_match = None
    for recognition in recognitions:
        diff = 1 - spatial.distance.cosine(encoding, recognition.encoding)
        if diff < threshold and diff < closest_diff:
            closest_match = recognition
    if closest_match is not None:
        return jsonify({'is_person': True, 'recogntion_id': closest_match.id})
    else:
        return jsonify({'is_person': True, 'recogntion_id': -1})

if __name__ == '__main__':
    if not os.path.exists('db.sqlite'):
        DB.create_all()
    APP.run(host='0.0.0.0', port=8000, threaded=True, debug=True)
