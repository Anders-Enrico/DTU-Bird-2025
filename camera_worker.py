from picamera2 import Picamera2
import time
import os
from datetime import datetime
import csv
import cv2

# Main camera logging function
def run_camera(start_event, start_time, interval, max_duration, shutdown_event):
    # Create folder structure for image storage
    base_folder = "/media/bird/LOGGER1/Images"
    session_folder = os.path.join(base_folder, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(session_folder, exist_ok=True)  # Create session folder if not existing
    log_path = os.path.join(session_folder, "Cam_data.csv")  # Path to CSV log file

    # Initialize PiCamera2 and configure it
    picam = Picamera2()
    config = picam.create_still_configuration(main={"format": "RGB888"})  # Set image format
    picam.configure(config)
    picam.start()
    print("[Camera] Initialized. Waiting to start...")

    try:
        # Open CSV file for logging
        with open(log_path, mode="w", newline="") as log_file:
            writer = csv.writer(log_file)
            writer.writerow(["timestamp", "filename"])  # Write header row to CSV

            # Wait until external start signal is received
            start_event.wait()
            base_time = start_time.value
            print(f"[Camera] Started at: {time.ctime(base_time)}")

            last_capture = 0.0  # Initialize last capture timestamp

            while not shutdown_event.is_set():
                now = time.time()

                # Check if maximum recording duration has been reached
                if max_duration.value > 0 and now - base_time >= max_duration.value:
                    print("[Camera] Max duration reached.")
                    break

                # Capture image at specified interval
                if (now - last_capture) >= interval.value:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  # Generate timestamp for filename
                    filename = f"{session_folder}/{timestamp}.jpg"  # Full path for image file
                    image = picam.capture_array()  # Capture image frame

                    # Compress and save image as JPEG (85% quality)
                    cv2.imwrite(filename, image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

                    # Log image capture with timestamp and filename
                    writer.writerow([datetime.now().isoformat(), os.path.basename(filename)])
                    log_file.flush()  # Immediately write data to file
                    print(f"[Camera] Saved and logged: {filename}")
                    last_capture = now  # Update last capture timestamp

                time.sleep(0.01)  # Short sleep to reduce CPU usage
    finally:
        # Stop camera when finished
        picam.stop()
        print(f"[Camera] Data saved to {session_folder}")
