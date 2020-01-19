from easyfacenet.simple import facenet
import urllib.parse
import getpass
from flask import Flask
app = Flask(__name__)


@app.route("/recognise")
def recognise():
    images = ['images/image1.jpg', 'images/image2.jpg', 'images/image3.jpg']
    aligned = facenet.align_face(images)
    embeddings = facenet.embedding(aligned)


username = input("Username: ")
password = getpass.getpass()

password = urllib.parse.quote(password)

print(username + ":" + password)