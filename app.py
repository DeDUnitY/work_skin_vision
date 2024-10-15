import torch
import base64
import cv2
import uvicorn
import numpy as np
from ultralytics import YOLO
from fastapi import FastAPI
from typing import Dict

app = FastAPI()
model = YOLO('yolov9.pt')
print('model loaded')
device = torch.device('cuda')
model.to(device)


@app.post('/detect')
def detect(data: Dict[str, str]):
    try:
        objects_dict = {}
        img_data = base64.b64decode(data['img_data'])
        img_data = np.frombuffer(img_data, np.uint8)
        img_arr = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        results = model.predict(img_arr, imgsz=640)

        for r in results:
            n = len(r.boxes.cls)

            for i in range(n):
                cls = int(r.boxes.cls[i].cpu())
                temp_obj = [r.boxes.conf[i].cpu().numpy().tolist(),
                            r.boxes.xyxy[i].cpu().numpy().tolist()]  # уверенность модели, координаты прямоугольника

                if cls not in objects_dict:
                    objects_dict[cls] = [temp_obj]
                else:
                    objects_dict[cls].append(temp_obj)
        return objects_dict

    except Exception as e:
        return {'error': str(e)}


@app.get("/test")
def test():
    return {'Hello': 'world'}


if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=5000)
