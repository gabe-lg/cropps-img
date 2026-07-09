# CIAB Demo Protocol — Plant Communication Lab

**Course:** Undergraduate plant science lab demonstration
**Instructor:** Prof. Margaret Frank, School of Integrative Plant Science, Cornell University
**Platform:** CROPPS-in-a-Box (CIAB), Demo version
**Approx. time:** 60–90 minutes

---

## 1. What you will see today

You will text-message a living *Arabidopsis thaliana* plant from your phone, ask it to respond to either a mild electrical current or a brief burn, and watch in real time as the plant fluoresces back at you and replies with its own SMS describing what just happened to it.

By the end of the session you should be able to:

1. Explain why a plant lights up when it is wounded.
2. Operate the CIAB Demo box to record a calcium-signalling event.
3. Interpret the live camera image and the SMS reply from the plant.

---

## 2. The biology — why the plant glows

The plant on the stage is *Arabidopsis thaliana*, a small mustard relative that is the most-studied model plant in the world. The line we use has been **genetically modified** to express a **fluorescent calcium reporter** (a GCaMP-style sensor) in its cytosol.

- Under normal conditions the cytosolic calcium concentration of a plant cell is very low (~100 nM) and the sensor is dim.
- When the plant is injured — by a cut, a burn, or an electrical current — calcium ions rush into the cytosol from internal stores and the apoplast. Within seconds the sensor binds calcium and **fluoresces brightly** under blue excitation light.
- The signal does not stay at the wound site. It **propagates from leaf to leaf** along the vasculature, at roughly 1 mm per second, in what is known as a **systemic wound response**. This is the plant equivalent of an "ouch" travelling through the body — a real, long-distance, intercellular calcium wave first described by Toyota et al. (*Science*, 2018).

The CIAB Demo box catches this calcium wave on camera and tells the operator about it by SMS.

---

## 3. What's inside the box

The Demo box contains, all wired together:

| Component | Role |
|---|---|
| Scientific microscope camera (Thorlabs DCx / IDS uEye, 8-bit) | Records the leaf at 2 frames per second |
| Blue LED ring + emission filter | Excites the calcium reporter; only green fluorescence reaches the camera |
| Two thin electrodes on a positioner | Deliver a constant-current pulse from a Keithley source-meter for the **current-injection** trigger |
| Small electric lighter on a positioner | Provides a brief heat pulse for the **burn** trigger |
| Arduino microcontroller | Receives the burn command from the PC and fires the lighter |
| Android phone (USB-tethered) | The plant's "phone" — sends and receives SMS through the PC via ADB |
| Windows PC | Runs the CIAB Demo app you will interact with |

You do **not** need to install or build anything. Everything is already set up on this PC. You will only operate the application.

---

## 4. Procedure

### 4.1 Pre-flight check (instructor does this)

Before students arrive, the instructor confirms:

- The PC is on, the camera is plugged in, and the Android phone is connected via USB with **USB debugging enabled** and the lock screen unlocked.
- The Keithley and the Arduino burn box are powered and connected to their COM ports.
- An *Arabidopsis* seedling at the 4–6 leaf stage is ready in its growth tray.

### 4.2 Launch the application

1. On the Windows desktop, open the folder `cropps-img-nov6-demo`.
2. Right-click `main.py` and choose **Open with → Python**, or open a terminal in the folder and type:

   ```bash
   python main.py
   ```

3. A loading screen with a rotating circle appears while the camera initialises (5–15 seconds).
4. When loading finishes you will see the main window:

   - **Left side:** the live microscope feed, labelled "Scientific Camera".
   - **Right side:** an image of a phone screen labelled "Hi, I'm Ari!" — this is where Ari, the plant's name in the Demo, will display text messages.
   - The interface is intentionally clean: there are no visible buttons.

### 4.3 Pair your phone with Ari

1. **Click anywhere on the main window.** A small dialog titled "Enter SMS Details" pops up.
2. Tick the checkbox **"Would you like to receive text messages from a plant?"**.
3. Enter your **first name** and your **mobile number** (country code included, e.g. `+16075551234`).
4. Click **Save**.
5. Within a few seconds you should receive **two SMS messages** from Ari on your phone:
   - An introduction from the plant ("Hi $NAME, it's me, your plant Ari…").
   - A prompt explaining the controls: **reply `1` for a tickle, `2` for a jolt**.

If no SMS arrives within ~30 seconds, ask the instructor to check the phone's USB connection and ADB authorisation prompt.

### 4.4 Mount the plant under the microscope

1. Place the *Arabidopsis* seedling tray on the stage so that one fully expanded leaf is directly under the objective.
2. Look at the live feed on the screen and **gently move the tray** until the leaf venation is visible and roughly centred.
3. The image will be dim and mostly black — that is correct. The calcium reporter is silent until the plant is stimulated, so background fluorescence is low.

### 4.5 Position the trigger hardware

The Demo has two triggers. Set up the one your group is testing first; the other can be tested in a second run.

**Current injection ("tickle"):**
- Bring the two electrodes down onto **the petiole** (leaf stalk) of an adjacent, untargeted leaf. Both electrodes should make light contact with the leaf surface — they must not pierce through.
- The current that will flow is small (40 µA, ~30 seconds) but the voltage compliance is set to 200 V. **Keep your fingers off both electrodes once positioning is done.**

**Burn ("jolt"):**
- Position the lighter tip ~3–5 mm above the petiole of an adjacent, untargeted leaf. The lighter will glow red for ~1 second when fired — long enough to wound a small region but not enough to ignite the plant.
- **Keep loose hair, sleeves and paper clear of the lighter.**

Note: the current Demo version does **not** include the mechanical cutter that earlier prototypes used. The two stimuli are current injection and burn only.

### 4.6 Trigger a response and record

1. From your phone, **send `1` or `2`** to Ari's number.
   - `1` → current injection (the "tickle")
   - `2` → burn (the "jolt")
2. Ari immediately replies on the phone screen and on your phone: **"Got it! Watch me to see what happens next!"**
3. The PC starts recording at 2 frames per second. The hardware fires after a short delay.
4. Within seconds you should see a **bright green/white wave of fluorescence** spreading across the targeted leaf in the live feed. The signal originates near the stimulation site and propagates along the midvein and into adjacent leaflets.
5. The Demo automatically records for **20 seconds**, then runs an image analysis on the saved frames. A "Please wait…" dialog appears for a few seconds.
6. When analysis finishes, Ari sends a final SMS telling you what the box detected:
   - "You gave me a tickle!" if it identified a current-injection pattern.
   - "You hit me with a jolt!" if it identified a burn pattern.
   - "All quiet here…" if no signal was detected (try again with a longer or more central electrode contact).

### 4.7 Repeat

- To send another trigger, just text `1` or `2` again from your phone.
- Reply `s` (or `stop`) to end an analysis early.
- Reply `q` (or `quit`) to close the application.
- To restart with a different student, click anywhere on the main window again and replace the name/number.

---

## 5. What to look for in the recording

The recorded images live under:

```
cropps-img-nov6-demo/assets/captured_data/analysis_<YYYYMMDD_HHMMSS>/
```

Compare the first few frames (background) with frames recorded a few seconds after the stimulus. You should see:

- **A localised bright spot** near the contact point of the electrode or lighter.
- **Propagation along the midvein** towards the leaf base, then onward to neighbouring leaflets.
- A **decay in intensity** over ~20–30 seconds as cytosolic calcium is pumped back into stores.

Discussion prompts for students:
- Why does the signal travel along the vasculature rather than spreading radially through the mesophyll?
- The current-injection signal is typically slower and broader than the burn signal — why might that be biologically?
- The Demo never directly measures pain — what is it actually measuring, and what assumption links that measurement to "the plant felt something"?

---

## 6. Safety

- The lighter element reaches several hundred degrees Celsius for ~1 second. Treat it like a soldering iron. **Do not touch it for at least 10 seconds after a burn trigger.**
- The Keithley delivers up to 200 V at very low current. Although the current is below the threshold of human sensation, **do not touch both electrodes simultaneously while the output is on**.
- The blue excitation LED is bright. **Do not look directly into the objective** when the LED is on.
- *Arabidopsis* is a non-toxic model organism. Wash hands after handling soil.

---

## 7. Quick troubleshooting

| Problem | Try this |
|---|---|
| No SMS arrives after clicking Save | Check that the Android phone screen is unlocked and the USB cable is fully seated. Ask the instructor to re-run `adb devices` in a terminal. |
| Camera window is fully black even after waiting | The camera may have been claimed by another process. Restart the application (close the window with the Exit button or send `q`, then re-launch). |
| App says "All quiet here…" after every trigger | The electrodes are not making contact, or the lighter is too far from the leaf. Re-position so contact/proximity is unambiguous. |
| Ari sends a "?" reply | You texted something other than `1`, `2`, `s` or `q`. Ari only understands those four commands. |
| Application freezes | Press `q` on the keyboard, or close the window. The instructor can re-launch `python main.py`. |

---

## 8. Suggested illustration images for the write-up

The following frames from previous experiments on this same box are good illustrations of what students should observe. They live on the Desktop of this PC and can be embedded directly into the course Word document.

**Current-injection signal — three time-points from the same trial** (Apr 21, 2026; TSI camera, 10-bit, 2 fps):
- Pre-stimulus baseline: `Desktop/Data CIAB figure/20-20260421_111903.png`
- Mid-propagation: `Desktop/Data CIAB figure/50-20260421_111909.png`
- Peak signal: `Desktop/Data CIAB figure/80-20260421_111914.png`

**Burn signal — three time-points from the same trial** (Mar 30, 2026; vain-pattern series, leaves 3 and 6):
- Pre-stimulus baseline: `Desktop/Data CIAB figure/image_0000_20260330_140620.png`
- Mid-propagation: `Desktop/Data CIAB figure/image_0027_20260330_140635.png`
- Late propagation: `Desktop/Data CIAB figure/image_0055_20260330_140650.png`

**Quantitative trace** (pixel count above threshold vs. time, showing signal envelope):
- `Desktop/Burn_CIAB_VainPattern_L3_L6/pixel_count_40_170_vs_bg_plot.png`

These are raw frames with no contrast stretching, so what the page shows is what the camera saw.

---

## 9. References

- Toyota, M. et al. (2018). Glutamate triggers long-distance, calcium-based plant defense signaling. *Science*, 361, 1112–1115.
- Choi, W. G. et al. (2014). Salt stress-induced Ca²⁺ waves are associated with rapid, long-distance root-to-shoot signaling in plants. *PNAS*, 111, 6497–6502.
- CIAB Demo source repository: `https://github.com/gabe-lg/cropps-img`
