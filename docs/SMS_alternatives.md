# SMS Alternatives to ADB + Phone Setup

**Status:** Reference only — not implemented. Keep as future-work plan.
**Date:** 2026-04-18

---

## Current setup

- Android phone with a SIM, physically tethered via USB to the CIAB computer
- `src/tools/sms_sender.py` runs `adb shell content query …` and `adb shell am startservice com.android.shellms/.sendSMS …` to poll inbox and send
- Requires: working ADB daemon, phone screen unlocked (sometimes), SIM plan

**Problems:**
- Recurring monthly SIM cost (~$5–15)
- Phone must stay connected and charged
- ADB is fragile: phone reboots, USB disconnects, SIM swap all break the pipeline
- Scaling is awful — one phone per box means one SIM per box

---

## Recommendation: Twilio

Best cost/reliability/documentation balance for this use case.

### Why Twilio

- ~$0.0083 per message (both send and receive) + ~$1.15/month for a phone number
- At the current demo volume (a handful of messages per session), cost is **< $5/month**
- Clean Python SDK: `pip install twilio`
- Excellent webhook-based inbound SMS handling
- Free trial credits to validate before committing

### How it works

```
Your app ─── REST POST ───► Twilio API ──► Recipient phone
                                               │
Your app ◄── HTTPS POST ── Twilio Webhook ◄────┘ (user replies)
       (Flask endpoint)
```

1. Rent a phone number from Twilio (a real SMS-capable number)
2. **Outbound:** `twilio_client.messages.create(to=..., from_=..., body=...)`
3. **Inbound:** Twilio posts every received SMS to a webhook URL you expose

### What would change in our code

Only `src/tools/sms_sender.py` changes. The rest of the app (`_execute_trigger`, dispatch, chatbox refresh) stays exactly the same — same method names, same behavior.

**Replace in `sms_sender.py`:**

```python
# Current
subprocess.run([self.adb, "shell", "am", "startservice", ...], cwd=self.dir)

# New
from twilio.rest import Client
self.client = Client(os.environ["TWILIO_ACCOUNT_SID"],
                     os.environ["TWILIO_AUTH_TOKEN"])
self.twilio_number = os.environ["TWILIO_NUMBER"]

def send_msg(self, message, phone=None):
    phone = phone or self.phone
    self.client.messages.create(
        to=phone, from_=self.twilio_number,
        body=fix_encoding(message).replace("$NAME", self.name or ""))
    self.msg_changed_event.set()
```

**Replace `read_msg` / `get_msg_history`:** No more polling ADB. Instead, a small Flask app that Twilio posts to:

```python
# New file: sms_webhook.py
from flask import Flask, request
app = Flask(__name__)

@app.route("/sms", methods=["POST"])
def incoming():
    body = request.form["Body"].strip().lower()
    from_number = request.form["From"]
    # push to the same queue the existing code consumes
    sms_sender.new_msgs.put(body)
    sms_sender.new_msg_event.set()
    sms_sender.msg_changed_event.set()
    return "", 204
```

The main app runs this Flask server on a thread. Twilio → webhook → same `new_msgs` queue that `_poll_messages` already watches. **No changes upstream.**

### The webhook exposure problem

Twilio's server needs to reach yours over HTTPS. Options:

| Approach | Pros | Cons |
|----------|------|------|
| **[ngrok](https://ngrok.com/)** free tier | Zero setup, works on CIAB machine as-is | URL changes each restart; paid for stable URL |
| **Cloudflare Tunnel** | Free, stable URL, no account churn | Requires Cloudflare account; one-time setup |
| **Small cloud VM** (~$5/mo) | Always on, stable | Adds infrastructure, another moving part |
| **Serverless webhook → queue → poll** | Clean separation | App must poll the cloud queue |

For the CIAB demo, **Cloudflare Tunnel** is probably the sweet spot — set it up once, permanent URL, free.

### Estimated effort

- Swap `sms_sender.py` internals: 2–3 hours
- Add Flask webhook + integrate with existing `new_msgs` queue: 2 hours
- Cloudflare Tunnel setup: 30 minutes
- End-to-end testing: 1–2 hours

**Total: ~1 solid working day.**

---

## Alternatives considered

| Provider | Rate (US) | Verdict |
|----------|-----------|---------|
| **[Twilio](https://www.twilio.com/)** | $0.0083 send + $0.0083 receive | **Recommended.** Most docs, cleanest API. |
| **[Telnyx](https://www.telnyx.com/)** | $0.004 / $0.004 | Cheapest serious option. Less Python tutorial content. |
| **[Plivo](https://www.plivo.com/)** | $0.0055 / $0.0055 | "Twilio but cheaper." Good if cost matters. |
| **[Vonage](https://www.vonage.com/)** | $0.007 / $0.0075 | Enterprise-oriented, overkill here. |
| **[MySMSGate](https://mysmsgate.net/)** | $0.03 flat, uses your phone | Same phone-gateway model we have now, but over WiFi instead of USB. Useful if we want to avoid SIM subscription but keep physical phone. |
| **AWS SNS** | $0.00645 send only | **Not suitable** — can't receive inbound SMS to our app. |

---

## When to revisit this

- We ship the CIAB box to a new site (no point in fighting USB tethering)
- We support multiple boxes (SIM per box doesn't scale)
- The current phone breaks or the SIM plan lapses
- Inbound SMS reliability becomes a blocker (it's not great with ADB polling)

Until one of the above, the current ADB-based flow is fine for demos.

---

## Quick-start when we do this

1. Sign up at https://console.twilio.com
2. Buy a US phone number (~$1.15/month)
3. `pip install twilio flask`
4. Export env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER`
5. Set up Cloudflare Tunnel to expose `localhost:5000`
6. In Twilio console: set the "A MESSAGE COMES IN" webhook URL to `https://<tunnel>/sms`
7. Swap `sms_sender.py` per the sketch above
8. Start Flask webhook from `main.py` alongside the Tk app
