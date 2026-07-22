"""
Auto-detect which COM port the KORAD KA6003P (current injection) and Arduino
(burn) are on. Probes are designed to be fast and to fail-fast on busy/stuck
ports so a misbehaving USB device can't hang the app.

(The current-injection instrument was previously a Keithley SMU; the legacy
Keithley probe is kept below but detect_ports() now looks for the KORAD supply.)

Other USB devices (Thorlabs camera, ADB phone, audio, HID) don't appear as
COM ports and are not touched.
"""
import time

try:
    import serial
    from serial.tools import list_ports
except ModuleNotFoundError:
    serial = None
    list_ports = None

# Keithley's own USB vendor ID (used by direct-USB-CDC Keithley instruments).
_KEITHLEY_VID = 0x05E6

# USB vendor IDs commonly found on Arduino-class boards or the USB-serial
# bridge chips Arduinos ship with.
_ARDUINO_VIDS = {
    0x2341,  # Arduino LLC / Arduino SA
    0x2A03,  # Arduino SRL
    0x1A86,  # QinHeng (CH340/CH341)
    0x0403,  # FTDI
    0x10C4,  # Silicon Labs (CP210x)
    0x067B,  # Prolific (PL2303)
    0x16C0,  # Teensy / Van Ooijen Technische Informatica
}

# VIDs that commonly host a Keithley behind a USB-RS232 adapter (subset of
# Arduino VIDs since they're the same bridge chips).
_RS232_BRIDGE_VIDS = {0x0403, 0x10C4, 0x067B, 0x1A86}

# Short timeout per port: if open() or read() blocks longer, give up. Keeps
# detection bounded so a stuck COM port can't hang the app.
_PROBE_TIMEOUT_S = 0.4


def _list_com_ports():
    if list_ports is None:
        return []
    return list(list_ports.comports())


def _try_keithley_probe(port_device):
    """
    Try to identify a Keithley by sending *IDN?. Uses exclusive=True so it
    fails fast if the port is already in use. Returns True if the response
    contains 'KEITHLEY'.
    """
    try:
        with serial.Serial(port_device, 9600,
                           timeout=_PROBE_TIMEOUT_S,
                           write_timeout=_PROBE_TIMEOUT_S,
                           exclusive=True) as s:
            time.sleep(0.05)
            s.reset_input_buffer()
            s.write(b'*IDN?\n')
            resp = s.read(200).decode('utf-8', errors='ignore')
            if 'KEITHLEY' in resp.upper():
                print(f"[port_detector] Keithley confirmed on {port_device}: "
                      f"{resp.strip()}")
                return True
    except Exception as e:
        print(f"[port_detector] {port_device} probe skipped: {e}")
    return False


def find_keithley_port():
    """
    Return the COM port hosting the Keithley, or None.
    1) If any port advertises Keithley's own USB VID, use it directly (no probe).
    2) Otherwise probe ports whose VID looks like a USB-RS232 adapter.
    Skips unknown-VID ports entirely (avoids hanging on random USB-CDC devices).
    """
    if serial is None:
        return None

    ports = _list_com_ports()

    # Pass 1: direct USB Keithley instruments
    for p in ports:
        if p.vid == _KEITHLEY_VID:
            print(f"[port_detector] Keithley found on {p.device} via VID match "
                  f"(0x{p.vid:04X}, {p.description})")
            return p.device

    # Pass 2: probe RS232-bridge candidates only
    for p in ports:
        if p.vid in _RS232_BRIDGE_VIDS:
            if _try_keithley_probe(p.device):
                return p.device

    return None


def _try_korad_probe(port_device):
    """
    Try to identify a KORAD KA6003P (or KAxxxxP) supply by sending *IDN?.
    Uses exclusive=True so it fails fast if the port is already in use.
    Returns True if the response contains 'KORAD'.
    """
    try:
        with serial.Serial(port_device, 9600,
                           timeout=_PROBE_TIMEOUT_S,
                           write_timeout=_PROBE_TIMEOUT_S,
                           exclusive=True) as s:
            time.sleep(0.05)
            s.reset_input_buffer()
            s.write(b'*IDN?')  # KORAD uses no line terminator
            resp = s.read(200).decode('utf-8', errors='ignore')
            if 'KORAD' in resp.upper():
                print(f"[port_detector] KORAD supply confirmed on {port_device}: "
                      f"{resp.strip()}")
                return True
    except Exception as e:
        print(f"[port_detector] {port_device} probe skipped: {e}")
    return False


def find_korad_port():
    """
    Return the COM port hosting the KORAD KA6003P supply, or None.

    KORAD supplies ship behind a generic USB-serial bridge (usually a Silicon
    Labs CP210x, VID 0x10C4) rather than an instrument-specific VID, so we probe
    the RS232-bridge candidates with *IDN? and match 'KORAD'. Unknown-VID ports
    are skipped so a random USB-CDC device can't hang detection.
    """
    if serial is None:
        return None

    for p in _list_com_ports():
        if p.vid in _RS232_BRIDGE_VIDS:
            if _try_korad_probe(p.device):
                return p.device
    return None


def find_arduino_port(exclude=None):
    """
    Identify the Arduino by USB vendor ID. Returns the port name or None.
    Only considers ports with known Arduino-class VIDs; never probes.
    """
    if list_ports is None:
        return None

    candidates = [p for p in _list_com_ports()
                  if p.device != exclude and p.vid in _ARDUINO_VIDS]

    if candidates:
        p = candidates[0]
        print(f"[port_detector] Arduino found on {p.device} "
              f"(VID=0x{p.vid:04X}, {p.description})")
        return p.device

    # Fallback: if exactly one other COM port exists and we haven't claimed it
    # for Keithley, assume it's the Arduino (best-effort guess).
    others = [p for p in _list_com_ports() if p.device != exclude]
    if len(others) == 1:
        p = others[0]
        print(f"[port_detector] Arduino assumed on {p.device} "
              f"(only remaining COM port)")
        return p.device

    return None


def detect_ports(default_injection: str, default_burn: str):
    """
    Run both detections and return (injection_port, burn_port). Falls back to
    the supplied defaults if a device can't be located. Designed to be called
    from a background thread so a slow probe never blocks the UI.
    """
    if serial is None:
        print("[port_detector] pyserial not available; using hardcoded defaults")
        return default_injection, default_burn

    print("[port_detector] Scanning COM ports...")
    available = _list_com_ports()
    print(f"[port_detector] Found {len(available)} COM port(s): "
          f"{[(p.device, p.description, f'VID=0x{p.vid:04X}' if p.vid else 'no VID') for p in available]}")

    korad = find_korad_port()
    arduino = find_arduino_port(exclude=korad)

    injection = korad or default_injection
    burn = arduino or default_burn

    if not korad:
        print(f"[port_detector] WARNING: KORAD supply not detected, "
              f"falling back to {default_injection}")
    if not arduino:
        print(f"[port_detector] WARNING: Arduino not detected, "
              f"falling back to {default_burn}")

    print(f"[port_detector] Using injection={injection}, burn={burn}")
    return injection, burn
