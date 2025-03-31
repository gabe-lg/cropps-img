import os
import dotenv
dotenv.load_dotenv()


from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.base.exceptions import TwilioException

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)

def send_sms(to: str, from_: str, body: str) -> None:
    """
    Send an SMS message using Twilio.

    Args:
        to (str): The recipient's phone number.
        body (str): The message body.
        from_ (str): The sender's phone number.

    Raises:
        TwilioRestException: If there is an error sending the message.
        TwilioException: If there is a general Twilio error.
    """
    try:
        message = client.messages.create(
            body=body,
            from_=from_,
            to=to
        )
        print(f"Message sent with SID: {message.sid}")
    except TwilioRestException as e:
        print(f"TwilioRestException: {e}")
    except TwilioException as e:
        print(f"TwilioException: {e}")

if __name__ == "__main__":
    to_number = "+18777804236"  # Replace with the recipient's number
    from_number = "+18556089086"  # Replace with your Twilio number
    message_body = "hello world"

    send_sms(to_number, from_number, message_body)