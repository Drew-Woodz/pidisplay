# input_handler.py - Threaded touchscreen event polling and gesture detection

import os
import struct
import time
import logging
import queue
import threading
import select

EVENT_DEVICE = "/dev/input/event0"
EVENT_SIZE = 16  # 32-bit
EVENT_FORMAT = "IIHHi"  # unsigned int sec/usec, ushort type/code, int value
W, H = 480, 320

# Input constants
EV_KEY = 0x01
EV_ABS = 0x03
ABS_X = 0x00
ABS_Y = 0x01
BTN_TOUCH = 0x14a

# Calibration
X_MIN, X_MAX = 50, 4000
Y_MIN, Y_MAX = 50, 4000

# Zones (cal_x 0-W, cal_y 0-H)
ZONE_LEFT = (0, W//3)
ZONE_CENTER = (W//3, 2*W//3)
ZONE_RIGHT = (2*W//3, W)
ZONE_TOP = (0, H//2)
ZONE_BOTTOM = (H//2, H)

# Gestures
LONG_PRESS_SEC = 1.0
TWO_FINGER_SEC = 0.3  # Between ups for multi-tap
MIN_TAP_SEC = 0.05    # Debounce noise
SWIPE_THRESHOLD = 200 # Pixels for swipe (increased for longer gestures)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

def input_handler(event_queue: queue.Queue):
    """Thread to poll /dev/input/event0 and queue unified events."""
    touch_fd = None
    try:
        touch_fd = os.open(EVENT_DEVICE, os.O_RDONLY | os.O_NONBLOCK)
        logging.info(f"Input thread opened {EVENT_DEVICE}")
    except Exception as e:
        logging.error(f"Input thread failed to open {EVENT_DEVICE}: {e}")
        return

    touch_down_time = 0.0
    last_up_time = 0.0
    touch_count = 0
    x_list = []
    y_list = []
    delta_x = 0
    delta_y = 0

    try:
        while True:
            ready, _, _ = select.select([touch_fd], [], [], 0.1)
            if ready:
                buf = os.read(touch_fd, EVENT_SIZE * 10)
                num_events = len(buf) // EVENT_SIZE
                events = [struct.unpack(EVENT_FORMAT, buf[i*EVENT_SIZE:(i+1)*EVENT_SIZE]) for i in range(num_events)]
                for ev_time_sec, ev_time_usec, ev_type, ev_code, ev_value in events:
                    ev_time = ev_time_sec + ev_time_usec / 1e6
                    if ev_type == EV_ABS:
                        if ev_code == ABS_X:
                            x_list.append(ev_value)
                            if len(x_list) > 1:
                                delta_x += x_list[-1] - x_list[-2]
                        elif ev_code == ABS_Y:
                            y_list.append(ev_value)
                            if len(y_list) > 1:
                                delta_y += y_list[-1] - y_list[-2]
                    elif ev_type == EV_KEY and ev_code == BTN_TOUCH:
                        if ev_value == 1:  # Down
                            if touch_down_time == 0.0:
                                touch_down_time = ev_time
                                touch_count += 1
                                x_list, y_list = [x_list[-1]] if x_list else [], [y_list[-1]] if y_list else []  # Carry last for multi
                        else:  # Up
                            if touch_down_time > 0.0:
                                duration = ev_time - touch_down_time
                                if duration < MIN_TAP_SEC:
                                    continue  # Debounce
                                # Average position
                                avg_raw_x = sum(x_list) / len(x_list) if x_list else 0
                                avg_raw_y = sum(y_list) / len(y_list) if y_list else 0
                                # Calibrate
                                temp = avg_raw_x
                                avg_raw_x = 4095 - avg_raw_y
                                avg_raw_y = temp
                                cal_x = max(0, min(W, int((avg_raw_x - X_MIN) * W / (X_MAX - X_MIN))))
                                cal_y = max(0, min(H, int((avg_raw_y - Y_MIN) * H / (Y_MAX - Y_MIN))))
                                zone = 'left' if cal_x < ZONE_LEFT[1] else 'center' if cal_x < ZONE_CENTER[1] else 'right'
                                vertical_zone = 'top' if cal_y < ZONE_TOP[1] else 'bottom'
                                # Rotate deltas 90 CCW to match logical (flip/invert signs post-cal)
                                temp_dx = delta_x
                                delta_x = -delta_y  # Adjust based on rotation
                                delta_y = temp_dx
                                event_type = 'tap'
                                if duration > LONG_PRESS_SEC:
                                    event_type = 'long_press'
                                elif touch_count >= 2 and (ev_time - last_up_time) < TWO_FINGER_SEC:
                                    event_type = 'two_finger_tap'
                                elif abs(delta_x) > SWIPE_THRESHOLD and abs(delta_y) < SWIPE_THRESHOLD / 2:
                                    event_type = 'swipe_left' if delta_x < 0 else 'swipe_right'
                                elif abs(delta_y) > SWIPE_THRESHOLD and abs(delta_x) < SWIPE_THRESHOLD / 2:
                                    event_type = 'swipe_up' if delta_y < 0 else 'swipe_down'
                                event = {'type': event_type, 'zone': zone, 'vertical_zone': vertical_zone, 'duration': duration, 'count': touch_count, 'cal_x': cal_x, 'cal_y': cal_y, 'delta_x': delta_x, 'delta_y': delta_y}
                                event_queue.put(event)
                                logging.info(f"Queued input event: {event}")
                                touch_down_time = 0.0
                                last_up_time = ev_time
                                if event_type != 'two_finger_tap':  # Reset count after non-multi
                                    touch_count = 0
                                x_list, y_list = [], []
                                delta_x, delta_y = 0, 0
    except KeyboardInterrupt:
        pass
    finally:
        if touch_fd:
            os.close(touch_fd)
        logging.info("Input thread stopped")

if __name__ == "__main__":
    q = queue.Queue()
    t = threading.Thread(target=input_handler, args=(q,))
    t.start()
    try:
        while True:
            try:
                event = q.get(timeout=1)
                print(f"Received event: {event}")
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        print("Stopped")
    t.join()