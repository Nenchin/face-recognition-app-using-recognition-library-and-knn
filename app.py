# -*- coding: utf-8 -*-
"""
Created on Sat Jan  7 10:09:44 2023

@author: Nenchin
"""


from flask import Flask, request, jsonify
import os
import base64
from flask_cors import CORS
import os.path
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from face_recognition_knn import train, predict, show_prediction_labels_on_image


app = Flask(__name__)
CORS(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
datasets = os.path.join(BASE_DIR, 'users/train')


class Employee_record(db.Model):
    employee_id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(100), unique=True, nullable=False)
    employee_role = db.Column(db.String(100),nullable=False)
    employee_unit = db.Column(db.String(100),nullable=False)
    entrancehistorys = db.relationship('Entrancehistory', backref='employee', lazy=True)

    def __init__(self, employee_name, employee_role, employee_unit):
        self.employee_name = employee_name
        self.employee_role = employee_role
        self.employee_unit = employee_unit
        
   
class EntranceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(100), unique=True, nullable=False)
    entrance_date = db.Column(db.DateTime, default=datetime.now(pytz.timezone("Etc/GMT-1")).strftime("%d-%m-%Y"))
    entrance_time = db.Column(db.Datetime, default=datetime.now(pytz.timezone("Etc/GMT-1")).strftime("%H:%M:%S"))
    employee_link = db.Column(db.String(100), db.ForeignKey('employee_record'), nullable=False)
    
    def __init__(self, employee_name, entrance_date, entrance_time):
        self.employee_name = employee_name
        self.entrance_date = entrance_date
        self.entrance_time = entrance_time
          

class_names = []
for folder in datasets:
    class_names.append(folder)


ALLOWED_EXT = set(['jpg', 'jpeg', 'png', 'jfif'])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXT



@app.route('/')
def home():
    return jsonify('Welcome to Image Recognition Endpoint')


@app.route('/capture', methods=['GET', 'POST'])
def capture():
    if request.method == 'POST':
        imageId = request.json['id']
        folder = request.json['folder_name']
        encoded_string = request.json['image']
        decoded_string = base64.b64decode(encoded_string)
        path = os.path.join(os.getcwd(), "users/train", folder)
        if not os.path.exists(path):
            return jsonify({"error": "Create Folder"}), 400
        else:
            with open(f"{path}/{folder}{imageId}.jpeg", "wb") as f:
                f.write(decoded_string)
            return f"{folder}{imageId} saved in {folder}"


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        user_name = request.json["folder_name"]
        user_role = request.json["role_name"]
        user_unit = request.json["unit_name"]
        if user_name == "":
            return jsonify({"error": "specify a folder name"}), 400
        
        else:
            employee = Employee_record(employee_name = user_name, employee_role = user_role, employee_unit = user_unit)
            db.session.add(employee)
            db.session.commit()
            
            user_name = user_name.strip().lower()
            path = os.path.join(os.getcwd(), "users/train", user_name)
            modelpath = os.path.join(os.getcwd(), "users", "model")
            if not os.path.exists(path):
                os.makedirs(path)
                if not os.path.exists(modelpath):
                    os.makedirs(modelpath) 
                    return jsonify(message="folder created")
                else:
                    return jsonify(message="folder created")
            else:
                return jsonify({"error": "folder already exists"}), 400




@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filename = file.filename
    path = os.path.join(os.getcwd(), "users/test")
    if not os.path.exists(path):
        os.makedirs(path)
    file.save('users/test/' + filename)
    return 'File uploaded successfully'




@app.route('/train', methods=["POST"])
def training():
    if request.method == "POST":
        "write a code to save the model"
        print("Training KNN classifier...")
        classifier, message = train(datasets, model_save_path="users/model/trained_knn_model.clf", n_neighbors=2)
        if message == "Done":
            return jsonify("Training complete!")
        else:
            return "an error occurred while training"


@app.route('/predict', methods=["POST"])
def prediction():
    error = 'error'
    target_img = os.path.join(os.getcwd(), 'users/test')
    if not os.path.exists(target_img):
        os.makedirs(target_img)
    if request.method == 'POST':
        file = request.files['file']
        
        if file and allowed_file(file.filename):
            file.save('users/test/' + file.filename)
            img_path = os.path.join(target_img, file.filename)
            img = file.filename
            print("Looking for faces in {}".format(img))
            predictions = predict(img_path, model_path="users/model/trained_knn_model.clf")

        else:
            error = "Please upload images of jpg , jfif, jpeg and png extension only"
        
        for name, (top, right, bottom, left) in predictions:
            predictedImage=show_prediction_labels_on_image(img_path, predictions)
            history = EntranceHistory(name_of_employee=name)
            db.session.add(history)
            db.session.commit()
            return jsonify({"result": {"name": f"{name}", "left": f"{left}", "top": f"{top}"}, "message":"Access granted", "image": f"{predictedImage}"})

            
   
        else: 
            return jsonify(error=error), 400

@app.route('/show_history', methods=['POST', 'GET'])
def show_entrance_history():
    if request.method == 'POST':
        return jsonify({"history_table": EntranceHistory.query.all()})

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)

