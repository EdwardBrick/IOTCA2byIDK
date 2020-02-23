from flask import Flask, render_template, jsonify,request

app = Flask(__name__)

import dynamodb as db
import jsonconverter as jsonc

@app.route("/api/getdata",methods=['POST','GET'])
def apidata_getdata():
    print("ENTERED GET DATA")
    if request.method == 'POST' or request.method == 'GET':
        try:
            data = {'chart_data': jsonc.data_to_json(db.get_data_from_dynamodb()), 
             'title': "IOT Data"}
            return jsonify(data)

        except:
            import sys
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

@app.route("/")
def home():
    return render_template("index.html")


app.run(debug=True,host="0.0.0.0")