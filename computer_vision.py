import cv2
import time
import asyncio
from ultralytics import YOLO

class ComputerVision:
    def __init__(self, model_path, task='obb', width=320, height=240):
        self.model = YOLO(model_path, task=task)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.prev_time = 0

    def process_frame(self, frame):
        """Rulează YOLO OBB și returnează doar eticheta text dacă găsește ceva."""
        results = self.model(frame, imgsz=1088, stream=True, verbose=False, conf=0.5)
        
        for r in results:
            if r.obb is not None and len(r.obb.cls) > 0:
                class_id = int(r.obb.cls[0].cpu().numpy())
                return r.names[class_id]
                
        return None

    async def run_vision_task(self, coada_rezultate):
        """TASK ASINCRON: Rulează camera continuu și trimite rezultatele în coada comună."""
        print("[TASK CV] Camera și YOLO au pornit...")
        try:
            while True:
                ret, img = self.cap.read()
                if not ret:
                    print("[TASK CV] Eroare: Nu s-a putut citi cadrul.")
                    await asyncio.sleep(0.1)
                    continue

                curr_time = time.time()
                fps = 1 / (curr_time - self.prev_time) if (curr_time - self.prev_time) > 0 else 0
                self.prev_time = curr_time

                eticheta = self.process_frame(img)
                
                if eticheta:
                    await coada_rezultate.put(eticheta)

                cv2.putText(img, f'FPS: {int(fps)}', (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow('Brat Curcan - CV Class', img)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                await asyncio.sleep(0.01)
        finally:
            self.release_resources()

    def release_resources(self):
        self.cap.release()
        cv2.destroyAllWindows()
        print("[TASK CV] Resurse eliberate cu succes.")