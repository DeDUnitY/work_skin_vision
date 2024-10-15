import threading
import time
import cv2
import requests
import cv2
import base64
import json

import board
import busio
import adafruit_pca9685

ya_url = 'http://192.168.1.54:5000/detect'

motor_matrix = [0 for i in range(16)]  # Состояние моторов вкл/выкл


# Ползунки
engine_power = 3
on_time = 1
pause_time = 1
start = True

# Адрес PCA9685
PCA9685_ADDR = 0x40
# Регистры
PCA9685_MODE1 = 0x00
PCA9685_PRESCALE = 0xFE
# Инициализация I2C шины
i2c = busio.I2C(board.SCL, board.SDA)
# Инициализация PCA9685
pca = adafruit_pca9685.PCA9685(i2c)
# Установка частоты PWM
pca.frequency = 60

door_flag = [False, False]


def your_code():
    global door_flag
    ya_url = 'http://192.168.1.54:5000/detect'
    labels = {0: 'door', 1: 'hinged', 2: 'knob', 3: 'lever'}
    cap = cv2.VideoCapture(0)
    iter = 1
    skip2X = 20
    flag = 0
    while True:
        flag = False
        ret, frame = cap.read()
        _, buffer = cv2.imencode('.jpeg', frame)
        img = base64.b64encode(buffer).decode('utf-8')

        t = time.time()
        response = requests.post(ya_url, json={"img_data": img})
        print("time:", time.time() - t)
        objects_dict = response.json()
        iter += 1
        for cls, obj_list in objects_dict.items():
            if int(cls) == 0:
                print(1)
                door_flag = [True, False]
                iter = 0

        if iter == skip2X and door_flag[0]:
            door_flag = [False, True]


# Поток Pca
def vibro_part():
    global motor_matrix, pause_time, on_time, engine_power, door_flag, start
    start = True
    s_iter = 1
    clock = time.time()
    dict = json.load(open('vibr_img.json', 'r'))
    yes_vibro = dict["yes"]  # [0, 4, 5, 8, 10, 12, 13, 14, 15]
    no_vibro = dict["no"]  # [0, 3, 5, 6, 9, 10, 12, 15]
    mode = 2
    while True:
        if mode == 1:
            if not start:
                clock = time.time()
                send = [False, True]
                start = True
            if time.time() - clock < float(on_time):
                if not send[0]:
                    for i in range(16):
                        if yes_vibro[i] != 0:
                            # pca.channels[i].duty_cycle = int(inputPower / 10 * 0xFFFF)
                            pass
                    send = [True, False]
            if (float(on_time) + float(on_time)) < time.time() - clock:
                clock = time.time()
            if time.time() - clock > float(on_time):
                if not send[1]:
                    for i in range(16):
                        pass
                        # pca.channels[i].duty_cycle = 0
                    send = [False, True]
        if mode == 2:
            if not start:
                send = [False, True]
                clock = time.time()
                start = True
                s_iter = 1
                limm = sum(map(lambda x: x != 0, motor_matrix))
            if time.time() - clock < float(on_time):
                if not send[0]:
                    if motor_matrix.index(s_iter):
                        pass
                        # pca.channels[motor_matrix.index(s_iter)].duty_cycle = int(inputPower / 10 * 0xFFFF)
                        s_iter += 1
                    send = [True, False]
            if (float(on_time) + float(on_time)) < time.time() - clock:
                clock = time.time()
                if s_iter > limm:
                    s_iter = 1
            if time.time() - clock > float(on_time):
                if not send[1]:
                    for i in range(16):
                        pass
                        # pca.channels[s_iter-1].duty_cycle = 0
                    send = [False, True]


if __name__ == '__main__':
    thread1 = threading.Thread(target=your_code)
    thread2 = threading.Thread(target=vibro_part)
    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()
