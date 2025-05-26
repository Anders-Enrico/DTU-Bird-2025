from picamera2 import Picamera2
import time
import os
from datetime import datetime
import csv
import cv2

def run_camera(start_event, start_time, interval, max_duration, shutdown_event):
    base_folder = "/media/bird/D0E44DDBE44DC506/Images"
    session_folder = os.path.join(base_folder, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(session_folder, exist_ok=True)
    log_path = os.path.join(session_folder, "Cam_data.csv")

    picam = Picamera2()
    config = picam.create_still_configuration(main={"format": "RGB888"})
    picam.configure(config)
    picam.start()
    print("[Camera] Initialized. Waiting to start...")

    try:
        with open(log_path, mode="w", newline="") as log_file:
            writer = csv.writer(log_file)
            writer.writerow(["timestamp", "filename"])

            start_event.wait()
            base_time = start_time.value
            print(f"[Camera] Started at: {time.ctime(base_time)}")

            last_capture = 0.0
            while not shutdown_event.is_set():
                now = time.time()
                if max_duration.value > 0 and now - base_time >= max_duration.value:
                    print("[Camera] Max duration reached.")
                    break

                if (now - last_capture) >= interval.value:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{session_folder}/{timestamp}.jpg"
                    image = picam.capture_array()

                    # Compress and save as JPEG
                    cv2.imwrite(filename, image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                    writer.writerow([datetime.now().isoformat(), os.path.basename(filename)])
                    log_file.flush()
                    print(f"[Camera] Saved and logged: {filename}")
                    last_capture = now

                time.sleep(0.01)
    finally:
        picam.stop()
        print(f"[Camera] Data saved to {session_folder}")
