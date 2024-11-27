import base64
import json
import random
import requests
import socket
import threading
import time

import cv2
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
local_ip = s.getsockname()[0]
s.close()

data_loc = '/home/skin-vision/python/viboro_creator/'

go_door = False
inputPower = 8
inputTime = 0.2
inputPause = 0.1
inputDopPause = 0.5
repeats = 1
motor_matrix = [0 for i in range(16)]
pause_matrix = [False for i in range(16)]
matrix_name = ''
mode = 0
rotation = 0
start = False
send = [False, True]
# Адрес PCA9685
PCA9685_ADDR = 0x40

# Регистры
PCA9685_MODE1 = 0x00
PCA9685_PRESCALE = 0xFE

side_margin = 0
top_margin = 0
MAX_DISTANCE = 2000


def num_rot(num, rot):
    for i in range(rot):
        stro = num // 4  # строка
        stolb = num % 4  # столбец
        num = stolb * 4 + 4 - stro - 1
    return num


ai_url = 'http://192.168.1.54:5000/detect'

import board, busio, adafruit_pca9685

# Инициализация I2C шины
i2c = busio.I2C(board.SCL, board.SDA)

# Инициализация PCA9685
pca = adafruit_pca9685.PCA9685(i2c)
# Установка частоты PWM
pca.frequency = 60


@app.route('/', methods=['GET'])
def index():
    global inputPower, inputTime, inputPause
    return render_template('index.html', inputPower=inputPower, inputTime=inputTime, inputPause=inputPause,
                           repeats=repeats, inputDopPause=inputDopPause, inputSide=side_margin, inputTop=top_margin)


@app.route('/test', methods=['GET'])
def test():
    global matrix_name, motor_matrix
    dict = json.load(open(data_loc + 'vibr_img.json', 'r'))
    matrix_names = [i for i in dict.keys() if "z_door" not in i]
    matrix_name = random.choice(matrix_names)
    load_by_name(matrix_name)
    return render_template('test.html')


@app.route('/send_matrix', methods=['POST'])
def send_matrix():
    global motor_matrix, pause_matrix
    data = request.get_json()
    motor_matrix = data['data']
    pause_matrix = [False for i in range(16)]
    for i in range(16):
        if "," in str(motor_matrix[i]):
            motor_matrix[i] = motor_matrix[i][:-1]
            pause_matrix[i] = True
    return jsonify({'success': True})


@app.route('/save_all', methods=['POST'])
def save_all():
    global motor_matrix
    dict = json.load(open(data_loc + 'vibr_img.json', 'r'))
    data = request.get_json()
    text = data['text']
    out_matrix = ['' for i in range(16)]
    for i in range(16):
        out_matrix[i] = str(motor_matrix[i])
        if pause_matrix[i]:
            out_matrix[i] = out_matrix[i] + ","
    print(out_matrix)
    dict.update({text: out_matrix})
    json.dump(dict, open(data_loc + 'vibr_img.json', 'w'))
    return jsonify({'success': True})


@app.route('/del', methods=['POST'])
def dell():
    global motor_matrix
    dict = json.load(open(data_loc + 'vibr_img.json', 'r'))
    data = request.get_json()
    del dict[data['text']]
    json.dump(dict, open(data_loc + 'vibr_img.json', 'w'))
    return jsonify({'success': True})


@app.route('/get_name', methods=['GET'])
def get_name():
    global matrix_name
    return jsonify({'name': matrix_name})


@app.route('/start_detect', methods=['POST'])
def start_detect():
    global go_door
    go_door = not go_door


@app.route('/load_matrix', methods=['GET'])
def load_matrix():
    global motor_matrix, matrix_name
    temp_name = request.args.get('name')
    return jsonify({'grid_data': load_by_name(temp_name)})


def load_by_name(name=''):
    global motor_matrix, matrix_name, pause_matrix
    out_matix = ['' for i in range(16)]
    if name != '':
        dict = json.load(open(data_loc + 'vibr_img.json', 'r'))
        matrix_name = name
        out_matix = dict[matrix_name]
        pause_matrix = [False for i in range(16)]
        motor_matrix = out_matix.copy()
        for i in range(16):
            if "," in str(motor_matrix[i]):
                motor_matrix[i] = motor_matrix[i][:-1]
                pause_matrix[i] = True
    else:
        for i in range(16):
            out_matix[i] = str(motor_matrix[i])
            if pause_matrix[i]:
                out_matix[i] = out_matix[i] + ","
    return out_matix


@app.route('/load_matrix_list', methods=['GET'])
def load_matrix_list():
    dict = json.load(open(data_loc + 'vibr_img.json', 'r'))
    matrix_names = [i for i in dict.keys() if "z_door" not in i]  # Примерные имена
    return jsonify({'matrix_names': sorted(matrix_names)})


@app.route('/set_slider_value', methods=['POST'])
def set_slider_value():
    global inputPower, inputTime, inputPause, repeats, inputDopPause, rotation, side_margin, top_margin
    data = request.get_json()
    if data['slider'] == 'inputPower':
        inputPower = int(data['value'])
    elif data['slider'] == 'inputTime':
        inputTime = float(data['value'])
    elif data['slider'] == 'inputPause':
        inputPause = float(data['value'])
    elif data['slider'] == 'repeats':
        repeats = int(data['value'])
    elif data['slider'] == 'rotate':
        rotation = int(data['value'])
    elif data['slider'] == 'inputSides':
        side_margin = int(data['value'])
    elif data['slider'] == 'inputTop':
        top_margin = int(data['value'])
    else:
        inputDopPause = float(data['value'])
    return jsonify({'success': True})


@app.route('/get_url', methods=['POST'])
def get_url():
    global ai_url
    url = request.args.get('url')
    ai_url = "http://" + url + "/detect"


@app.route('/button_clicked', methods=['POST'])
def button_clicked():
    global mode, start
    data = request.get_json()
    mode = data['button']
    start = False
    return jsonify({'success': True})


@app.route('/process', methods=['POST'])
def process_image():
    global matrix_name, motor_matrix, pause_matrix
    data = request.get_json()
    image_name = data['imageName']
    dict = json.load(open(data_loc + 'vibr_img.json', 'r'))
    matrix_names = sorted([i for i in dict.keys() if "z_door" not in i])
    save = matrix_name
    matrix_name = random.choice(matrix_names)
    motor_matrix = dict[matrix_name]
    pause_matrix = [False for i in range(16)]
    for i in range(16):
        if "," in str(motor_matrix[i]):
            motor_matrix[i] = motor_matrix[i][:-1]
            pause_matrix[i] = True
    return jsonify({'ins': matrix_names.index(image_name), 'ans': matrix_names.index(save), 'name': save}), 200


def web_part():
    app.run(host=local_ip, port=80)


def vibro_part():
    global motor_matrix, inputPower, inputTime, inputPause, repeats, start, send, mode, local_repeats, detect_mode
    start = False
    s_iter = 1
    clock = time.time()
    local_repeats = repeats
    distance_sensor = VL53L0XV2()
    distance_sensor.start_ranging()
    while True:
        if mode == 1:
            if not start:
                clock = time.time()
                send = [False, True]
                local_repeats = repeats
                start = True
            if time.time() - clock < inputTime and local_repeats > 0:
                if not send[0]:
                    for i in range(16):
                        if motor_matrix[i] != "0":
                            pca.channels[num_rot(i, rotation)].duty_cycle = int(inputPower / 10 * 0xFFFF)
                    send = [True, False]
            if (inputTime + inputPause) < time.time() - clock and local_repeats > 0:
                local_repeats -= 1
                clock = time.time()
        if mode == 2:
            if not start:
                send = [False, True]
                clock = time.time()
                start = True
                s_iter = 1
                limm = sum(map(lambda x: str(x) != "0", motor_matrix))
                local_repeats = repeats
            if time.time() - clock < inputTime and local_repeats > 0:
                if not send[0]:
                    cell = motor_matrix.index(str(s_iter))
                    pca.channels[num_rot(cell, rotation)].duty_cycle = int(inputPower / 10 * 0xFFFF)
                    s_iter += 1
                    send = [True, False]
            if (inputTime + inputPause + inputDopPause * pause_matrix[
                cell]) < time.time() - clock and local_repeats > 0:
                clock = time.time()
                if s_iter > limm:
                    s_iter = 1
                    local_repeats -= 1
        if mode == 1 or mode == 2:
            if time.time() - clock > inputTime and local_repeats > 0:
                if not send[1]:
                    for i in range(16):
                        pca.channels[i].duty_cycle = 0
                    send = [False, True]
            if local_repeats == 0:
                mode = 0
                start = False
        if detect_mode == 3:
            if not start:
                send = [False, True]
                clock = time.time()
                start = True

            # Получение значения от датчика и приведение его к диапазону от 0 до 1
            distance = distance_sensor.get_distance()  # Получаем расстояние от VL53L0XV2
            distance_normalized = max(0, min(distance / MAX_DISTANCE, 1))  # Нормализуем в диапазоне 0-1

            # Установка duty_cycle на основе нормализованного расстояния
            if time.time() - clock < inputTime:
                for i in range(16):
                    if motor_matrix[i] != "0":
                        pca.channels[num_rot(i, rotation)].duty_cycle = int(distance_normalized * 0xFFFF)
            elif time.time() - clock < inputTime + inputPause:
                # Отключение вибрации на время паузы
                for i in range(16):
                    pca.channels[i].duty_cycle = 0
            else:
                # Сброс таймера для повторного включения-выключения
                clock = time.time()


def object_search():
    global go_door, start, local_repeats, repeats, detect_mode, ai_url, side_margin, top_margin
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    frame_height, frame_width, _ = frame.shape
    center_x = frame_width / 2
    center_y = frame_height / 2

    play = False
    # 1 режим: cls 0: дверь
    # 2 режим: cls 0: человек, 24: рюкзак, 39: бутылка, 41: кружка, 56: стул
    while True:
        if go_door:
            ret, frame = cap.read()
            _, buffer = cv2.imencode('.jpeg', frame)
            img = base64.b64encode(buffer).decode('utf-8')

            t = time.time()
            response = requests.post(ai_url, json={"img_data": img, "int_param": detect_mode})
            objects_dict = response.json()
            for cls, obj_list in objects_dict.items():
                for conf, box in obj_list:
                    x1, y1, x2, y2 = map(int, box)
                    object_center_x = x1 + x2 / 2
                    object_center_y = y1 + y2 / 2

                    # Проверяем, что объект находится в центре экрана и имеет разумные размеры
                    if ((center_x * (1 - side_margin * 0.1)) <= object_center_x <= (
                            center_x * (1 + side_margin * 0.1)) and
                            (center_y * (1 - top_margin * 0.1)) <= object_center_y <= (
                                    center_y * (1 + top_margin * 0.1)) and conf >= 0.5):
                        if int(cls) == 0 and detect_mode == 1 and not start:
                            load_by_name('z_door_on')
                            start = True
                            play = True

                        if detect_mode == 2 and not start:
                            if int(cls) == 0:
                                load_by_name('z_person')
                                start = True
                            elif int(cls) == 24:
                                load_by_name('z_backpack')
                                start = True
                            elif int(cls) == 39:
                                load_by_name('z_bottle')
                                start = True
                            elif int(cls) == 41:
                                load_by_name('z_cup')
                                start = True
                            elif int(cls) == 56:
                                load_by_name('z_chair')
                                start = True

            if local_repeats == 0 and play and detect_mode == 1:
                play = False
                load_by_name('z_door_off')
        else:
            time.sleep(1)


if __name__ == '__main__':
    thread1 = threading.Thread(target=web_part)
    thread2 = threading.Thread(target=vibro_part)
    # thread3 = threading.Thread(target=object_search)
    thread1.start()
    thread2.start()
    # thread3.start()

    thread1.join()
    thread2.join()
    # thread3.join()
