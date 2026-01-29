import time
from tkinter.scrolledtext import ScrolledText


class Chatbox(ScrolledText):
    def __init__(self, chat_frame, sms_sender, bg):
        super().__init__(chat_frame, wrap="word",
                         state="disabled",
                         font=("Segoe UI Emoji", 20),
                         bg=bg, bd=0)
        self.sms_sender = sms_sender

    def poll_messages(self, exec_func, truncate_msgs):
        """Periodically refresh chatbox with updated message history."""
        print("[poll_messages]: waiting")
        self.sms_sender.msg_changed_event.wait()
        self.sms_sender.msg_changed_event.clear()
        print("[poll_messages]: finished waiting")

        try:
            if self.sms_sender.new_msg_event.is_set():
                self.sms_sender.new_msg_event.clear()
                exec_func()

            if self.sms_sender and self.sms_sender.phone:
                msgs = self.sms_sender.get_msg_history(
                    self.sms_sender.phone)

                # Only update if there’s new content
                # UPDATE v2.1.0: added `wait` above.
                # This checks for correct phone number
                if msgs != getattr(self, "_last_msg_history", []):
                    self._last_msg_history = msgs
                    self.refresh_chatbox(truncate_msgs)

        except Exception as e:
            print("Error polling messages:", e)

    def refresh_chatbox(self, truncate_msgs):
        """Replace chatbox content with current message history."""
        self.configure(state="normal")
        self.delete("1.0", "end")

        # Message color
        self.tag_config('r', foreground="red")
        self.tag_config('b', foreground="blue")

        for m in getattr(self, "_last_msg_history", []):
            sender = "You" if m["type"] == "sent" \
                else self.sms_sender.name or "Contact"
            tag = 'b' if m["type"] == "sent" else 'r'
            ts = time.strftime("%H:%M:%S",
                               time.localtime(m["timestamp"] / 1000))

            body = m["body"]

            # truncate input (magic number)
            max_length = 64

            if truncate_msgs and len(body) > max_length:
                body = body[:max_length] + "..."
            self.insert("end", f"[{ts}]\n{sender}:\n{body}\n\n", tag)

        self.configure(state="disabled")
        self.yview("end")
