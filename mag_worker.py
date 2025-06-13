from picamera2 import Picamera2
import time
import os
from datetime import datetime
import csv
import cv2

# Main camera function
def run_camera(start_event, start_time, interval, max_duration, shutdown_event):
    # Create base folder and session subfolder for saving images
    base_folder = "/media/bird/LOGGER1/Images"
    session_folder = os.path.join(base_folder, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(session_folder, exist_ok=True)
    log_path = os.path.join(session_folder, "Cam_data.csv")

    # Initialize PiCamera2
    picam = Picamera2()
    config = picam.create_still_configuration(main={"format": "RGB888"})
    picam.configure(config)
    picam.start()
    print("[Camera] Initialized. Waiting to start...")

    try:
        # Open CSV file for logging
        with open(log_path, mode="w", newline="") as log_file:
            writer = csv.writer(log_file)
            writer.writerow(["timestamp", "filename"])  # Write header row

            # Wait until start_event is triggered
            start_event.wait()
            base_time = start_time.value
            print(f"[Camera] Started at: {time.ctime(base_time)}")

            last_capture = 0.0
            while not shutdown_event.is_set():
                now = time.time()

                # Check if max duration has been reached
                if max_duration.value > 0 and now - base_time >= max_duration.value:
                    print("[Camera] Max duration reached.")
                    break

                # Check if it's time to capture next image
                if (now - last_capture) >= interval.value:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{session_folder}/{timestamp}.jpg"
                    image = picam.capture_array()

                    # Save image as JPEG with compression
                    cv2.imwrite(filename, image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                    # Log timestamp and filename
                    writer.writerow([datetime.now().isoformat(), os.path.basename(filename)])
                    log_file.flush()  # Ensure data is written immediately
                    print(f"[Camera] Saved and logged: {filename}")
                    last_capture = now

                time.sleep(0.01)  # Small delay to prevent busy-waiting
    finally:
        # Stop camera when done
        picam.stop()
        print(f"[Camera] Data saved to {session_folder}")
