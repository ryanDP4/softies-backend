from tensorflow.keras.models import load_model
import tensorflow_hub as hub

from flask import Flask, render_template, redirect, request, jsonify, session
from pymysql import connect
from pymysql.cursors import re, DictCursor
import numpy as np
import cv2
from PIL import Image
import dotenv
import os
# Load the environment variables
dotenv.load_dotenv()

app = Flask(__name__)
# Change this to your secret key (it can be anything, it's for extra protection)
app.secret_key = os.getenv("SECRET_KEY")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

image_size = (224)
channels = 3

# Connect to the database
connection = connect(host='localhost',
                             user='root',
                            #  password='passwd',
                             database='skanin_db',
                            #  charset='utf8mb4',
                             cursorclass=DictCursor)

# Model initialization
# Define the function to handle the KerasLayer when loading the model
def load_model_with_hub(path):
    class KerasLayerWrapper(hub.KerasLayer):
        def __init__(self, handle, **kwargs):
            super().__init__(handle, **kwargs)

    custom_objects = {'KerasLayer': KerasLayerWrapper}

    return load_model(path, custom_objects=custom_objects)

# Load the model using the defined function
model = load_model_with_hub('assets//model.h5')
# def initModel():
#     ## Model initialization function
#     # IMG_SHAPE = (image_size,image_size) + (channels,) ## RGB=3
#     tf_model = load_model('assets//model.h5')
#     return tf_model
# model = initModel()

def preprocessData(data):
    ## Main Preprocessing function for input images 
    processed_data = cv2.resize(data,(image_size,image_size)).reshape(1,image_size,image_size,3)
    return processed_data

@app.route('/skan', methods=["POST"])
def skan():
    if request.method == 'POST' and 'image' in request.files:
        ## Retrieving user_id
        user_id = session.get('user_id')
        print(user_id)
        ## Prediction route accepting images and outputs prediction of A.I.
        ## Read Image from input and convert to CV2
        image = request.files['image']
        image_name=image.filename
        pil_image = Image.open(image.stream).convert('RGB') 
        data = np.array(pil_image)
        data = preprocessData(data)

        ## Image for saving
        rice_image = data.tobytes()

        ## Model prediction
        result = np.argmax(model.predict(data))+1
        print(result)
        # print("INSERT HERE")
        # result = '3'
            ## End of prediction

        ## Getting Recommendation using output from model
        stress_id = int(result)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * from rice_stress WHERE `stress_id` = {stress_id}")
            stress = cursor.fetchone()
        stress_name = stress['stress_name']
        stress_type = stress['stress_type']
        stress_level = stress['stress_level']
        description = stress['description']
        description_src = stress['description_src']
        recommendation = stress['recommendation']
        recommendation_src = stress['recommendation_src']
        msg = 'Successfully retrieved recommendation'

        ## Creating history entry for transaction
        with connection.cursor() as cursor:
            # print("working")
            sql = "INSERT INTO `history` (`user_id`, `stress_id`, `rice_image`, `image_name`) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (user_id, stress_id, rice_image, image_name))
        connection.commit()
        
        return jsonify({'msg':msg, 'stress_name':stress_name, stress_type:'stress_type',
                        'stress_level':stress_level, 'description':description, 'description_src':description_src,
                        'recommendations':recommendation, 'recommendation_src':recommendation_src})
    msg = 'Invalid request'
    return jsonify({'msg':msg})


if __name__ == '__main__':
    app.run('localhost',port=8000)