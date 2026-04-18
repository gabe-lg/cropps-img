import time

try:
    import serial
except ModuleNotFoundError:
    print("Module serial not found.")

BAUD_RATE = 9600


def main(port: str, duration: float = 2):
    """
    :param port: serial port name (e.g., "COM6")
    :param duration: lighter duration (unused by current Arduino firmware,
                     which uses a fixed pulse width via the 'L1' command)
    """
    try:
        # Initialize serial connection
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize
        print(f"[burn] connected to Arduino on {port}")

        # Read initial Arduino messages
        while ser.in_waiting:
            print(f"[burn] Arduino init msg: {ser.readline().decode('utf-8').strip()}")

        # Send L1 command to fire lighter (Arduino firmware uses L1 protocol)
        ser.write(b'L1\n')
        print(f"[burn] sent command 'L1' (duration param {duration}s unused by current firmware)")

        # Read and display Arduino response
        time.sleep(0.1)  # Brief delay to allow Arduino to respond
        while ser.in_waiting:
            print(f"[burn] Arduino response: {ser.readline().decode('utf-8').strip()}")

    except serial.SerialException as e:
        print(f"[burn] Serial error: {e}")
    except KeyboardInterrupt:
        print("[burn] interrupted")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("[burn] serial connection closed")
