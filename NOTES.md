# CROPPS Demo — Notes, Tasks & Bugs

A living log for the demo app. Keep appending; newest context at the top of each
section. Dates are absolute.

_Last updated: 2026-07-22_

---

## Active Tasks

- [x] **Hardware-test the KORAD KA6003P injection path** — DONE 2026-07-22.
      Real supply on **COM9** (FTDI bridge, VID 0x0403). `*IDN?` →
      `KORAD KA6003P V6.0 SN:00100917`; auto-detect returns injection=COM9;
      `OUT1`/`OUT0` toggle, V/I polling, CSV logging, fail-safe OFF all verified
      with open terminals (15 V, 1 mA cap, I=0.000 mA as expected). Full GUI app
      NOT tested — camera + phone were not connected (injection path is
      independent of both).
- [ ] **Tune injection parameters** in `assets/injection_korad.py` for the plant.
      Starting values: `VOLTAGE = 15.0` V, `CURRENT_LIMIT = 0.001` A (1 mA),
      `MEASUREMENT_TIME = 20` s.
- [ ] **Update `CIAB_Demo_Protocol.md`** hardware references once the final
      voltage is chosen — it still says "Keithley" / "up to 200 V" (see Bugs).
- [ ] **Rebuild + smoke-test the `.exe`**, then get approval and **push** the
      `nov6-demo` branch.

## Recently Done

- **2026-07-22 — Fixed slow `_query` sampling in `assets/injection_korad.py`.**
  The original `ser.read(64)` blocked the full 1 s serial timeout every query
  (KORAD sends ~5 bytes, no terminator) → only ~9 samples in 20 s. Now reads the
  buffered bytes after a short settle → ~51 samples in 20 s. Verified on COM9.
- **2026-07-22 — Migrated current-injection from Keithley 2400 → KORAD KA6003P.**
  - Added `assets/injection_korad.py` (KORAD KAxxxxP ASCII protocol; same
    `main(port)` entry point).
  - `src/trigger.py` now launches `assets.injection_korad.main`.
  - `src/port_detector.py` detects the KORAD via `*IDN?` (matches `KORAD`).
  - `cropps-demo.spec` hiddenimports now includes `assets.injection_korad`
    (needed or the frozen `.exe` would `ModuleNotFoundError` — see Bugs).
  - Legacy `assets/injection.py` (Keithley) kept for reference, no longer wired in.
- **2026-07-22 — Pulled `nov6-demo`, installed deps, built `CROPPS-Demo.exe`.**

## Known Issues / Bugs / Watch-outs

- **`assets/` has no `__init__.py`.** Any `assets.*` module used at runtime MUST
  be added to `cropps-demo.spec` `hiddenimports`, or the frozen `.exe` throws
  `ModuleNotFoundError`. (`injection_korad` is now added.)
- **Direct-wire, no series resistor.** The plant is wired directly across the
  supply, so the `ISET1` current limit is the ONLY thing capping current into
  the plant. Min settable step is 1 mA. **Verify the limit before energizing.**
- **KORAD shares the CP210x bridge VID (`0x10C4`) with the Arduino list.** If the
  KORAD `*IDN?` probe fails, `find_arduino_port` could grab the KORAD's COM port.
  Detection excludes the KORAD port when the probe succeeds, so this only bites
  if the probe fails. Watch for it during hardware testing.
- **`CIAB_Demo_Protocol.md` is stale w.r.t. the new hardware** — equipment table
  and the safety note ("Keithley delivers up to 200 V") describe the old
  instrument. Update after the final KORAD voltage is locked in.

## Notes / Decisions

- **The KA6003P is a voltage source, not a current source.** It cannot reproduce
  the Keithley's 40 µA constant-current injection (min step ~1 mA, no µA range).
  The demo now does direct-wire voltage injection with `ISET1` as the current cap.
- **KORAD protocol:** KAxxxxP ASCII command set, 9600 8N1, **no line terminator**,
  ~50 ms gap required between commands. Commands used: `*IDN?`, `VSET1:`,
  `ISET1:`, `OUT1`/`OUT0`, `VOUT1?`, `IOUT1?`.
- **Injection CSVs** are written as `korad_injection_data_<timestamp>.csv` (the
  Keithley path used `keithley_data_<timestamp>.csv`).
