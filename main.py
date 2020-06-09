import requests
import flask
import logging
import csv
import re
from flask import jsonify, request
from threading import Timer


app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False
format_config = '%(asctime)s - %(levelname)s - %(message)s'
# logging.basicConfig(
#     format=format_config, level=logging.DEBUG, filename='run.log')
logging.basicConfig(format=format_config, level=logging.INFO)
logger = logging.getLogger()
Maskdata = None
NEXT_Update = None


@app.route('/states', methods=['GET'])
def states():
    if 'city' in request.args:
        city_name = request.args['city']
    else:
        return "Error: No city provided. Please specify a city_name."
    if city_name in Maskdata["city"]:
        return jsonify(Maskdata["state"][city_name])
    return "Error: Not found this city."


@app.route('/cities', methods=['GET'])
def cities():
    return jsonify(Maskdata["city"])


@app.route('/data', methods=['GET'])
def data():
    if 'city' in request.args:
        city_name = request.args['city']
    else:
        city_name = None
    if 'state' in request.args:
        state_name = request.args['state']
    else:
        state_name = None
    if city_name is not None:
        if city_name not in Maskdata["city"]:
            return "Error: Not found this city."
        if state_name is not None:
            if state_name not in Maskdata["state"][city_name]:
                return "Error: Not found this state."
            else:
                response = []
                for x in Maskdata["data"]:
                    if city_name == x["city"] and state_name == x["state"]:
                        response.append(x)
                return jsonify(response)
        response = []
        for x in Maskdata["data"]:
            if city_name == x["city"]:
                response.append(x)
        return jsonify(response)
    return jsonify(Maskdata["data"])


@app.route('/', methods=['GET'])
def intro():
    return "歡迎使用口罩查詢api<br>使用方式如下<br>/data:<br>\
    \tcity:城市名<br>\tstate:鄉鎮市區<br>/cities<br>/states:<br>\tcity:城市名"


def init():
    global Maskdata
    global NEXT_Update
    url = "https://data.nhi.gov.tw/resource/mask/maskdata.csv"
    try:
        with requests.Session() as s:
            download = s.get(url, timeout=10)
            decoded_content = download.content.decode('utf-8')
            cr = csv.reader(decoded_content.splitlines(), delimiter=',')
            my_list = list(cr)
            my_list = my_list[1:]
            city = set()
            state = {}
            for y in my_list:
                temp = y[2]
                x = re.search("縣|市", temp)
                y.append(temp[:x.span()[1]])
                if temp[x.span()[1]-1] == "市":
                    regrex = "區"
                else:
                    regrex = "鎮|市|鄉"
                temp = temp[x.span()[1]:]
                x = re.search(regrex, temp)
                y.append(temp[:x.span()[1]])
            city = list(set([x[-2] for x in my_list]))
            for i in city:
                state[i] = set()
            for y in my_list:
                state[y[-2]].add(y[-1])
            for i in city:
                state[i] = list(state[i])
            for i in range(len(my_list)):
                my_list[i] = {
                    "name": my_list[i][1],
                    "address": my_list[i][2],
                    "phone": my_list[i][3],
                    "adult": my_list[i][4],
                    "child": my_list[i][5],
                    "city": my_list[i][7],
                    "state": my_list[i][8]
                }
            Maskdata = {
                "data": my_list,
                "city": city,
                "state": state
            }
    except Exception as e:
        logger.error("can't update data" + str(e))
    NEXT_Update = Timer(120, init)
    NEXT_Update.start()
    print("update")


@app.before_first_request
def start():
    init()
    if Maskdata is None:
        logger.critical("can't get data")
        exit


if __name__ == "__main__":
    app.run()
