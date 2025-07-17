from azure.communication.email import EmailClient
import logging

class AcsEmailService:
    def __init__(self, connection_string, sender_address):
        self.client = EmailClient.from_connection_string(connection_string)
        self.sender = sender_address

    def send_email(self, recipient, subject, plain_text, html=None, display_name="Recipient"):
        message = {
            "senderAddress": self.sender,
            "content": {
                "subject": subject,
                "plainText": plain_text,
                "html": html or f"<html><body><p>{plain_text}</p></body></html>"
            },
            "recipients": {
                "to": [
                    {
                        "address": recipient,
                        "displayName": display_name
                    }
                ]
            }
        }

        try:
            poller = self.client.begin_send(message)
            result = poller.result()
            message_id = result.get("id", "No ID returned")
            logging.info(f"ACS Email sent. Message ID: {message_id}")
            return True, message_id
        except Exception as e:
            logging.error(f"ACS email failed: {e}")
            return False, str(e)
