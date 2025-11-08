#!/usr/bin/env python3
# test_touch.py - Standalone poll for /dev/input/event0 events with calibration

import os
import struct
import select
import time

EVENT_DEVICE = "/dev/input/event0"
EVENT_SIZE = 16  # 32-bit size
EVENT_FORMAT = "IIHHi"  # unsigned int sec/usec, ushort type/code, int value
W, H = 480, 320  # Screen res per PNGs

# From linux/input.h
EV_SYN = 0x00
EV_KEY = 0x01
EV_ABS = 0x03
ABS_X = 0x00
ABS_Y = 0x01
BTN_TOUCH = 0x14a

def main():
    try:
        fd = os.open(EVENT_DEVICE, os.O_RDONLY | os.O_NONBLOCK)
        print(f"Opened {EVENT_DEVICE} - Tap/hold corners to test calibration (Ctrl+C to stop)")
    except Exception as e:
        print(f"Failed to open {EVENT_DEVICE}: {e}")
        return

    x_raw, y_raw = 0, 0
    down_time = 0.0

    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0.1)
            if ready:
                buf = os.read(fd, EVENT_SIZE * 10)
                num_events = len(buf) // EVENT_SIZE
                events = [struct.unpack(EVENT_FORMAT, buf[i*EVENT_SIZE:(i+1)*EVENT_SIZE]) for i in range(num_events)]
                for ev_time_sec, ev_time_usec, ev_type, ev_code, ev_value in events:
                    ev_time = ev_time_sec + ev_time_usec / 1e6
                    if ev_type == EV_ABS:
                        if ev_code == ABS_X:
                            x_raw = ev_value
                        elif ev_code == ABS_Y:
                            y_raw = ev_value
                    elif ev_type == EV_KEY and ev_code == BTN_TOUCH:
                        if ev_value == 1:  # Down
                            down_time = ev_time
                            print(f"Touch down at {ev_time}")
                        else:  # Up
                            duration = ev_time - down_time
                            # Calibrate: Swap for rotate=90, invert Y, scale to screen
                            temp = x_raw
                            x_raw = 4095 - y_raw  # Invert + swap
                            y_raw = temp
                            cal_x = int(x_raw * W / 4095.0)
                            cal_y = int(y_raw * H / 4095.0)
                            print(f"Touch up at {ev_time} (duration {duration:.2f}s) - Raw X/Y: {x_raw}/{y_raw}, Cal X/Y: {cal_x}/{cal_y}")
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        os.close(fd)

if __name__ == "__main__":
    main()