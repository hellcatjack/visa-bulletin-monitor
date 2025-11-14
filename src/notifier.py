import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class SMSNotifier:
    """Send SMS notifications using Twilio"""

    def __init__(self, account_sid: str, auth_token: str, from_number: str, to_number: str):
        """
        Initialize Twilio SMS notifier.

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number (sender)
            to_number: Recipient phone number
        """
        self.from_number = from_number
        self.to_number = to_number

        try:
            self.client = Client(account_sid, auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            raise

    def send_sms(self, message: str) -> bool:
        """
        Send an SMS message.

        Args:
            message: Message content to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Twilio has a 1600 character limit for SMS
        # Split into multiple messages if needed
        max_length = 1500  # Leave some buffer

        if len(message) <= max_length:
            return self._send_single_sms(message)
        else:
            # Split into multiple messages
            return self._send_multipart_sms(message, max_length)

    def _send_single_sms(self, message: str) -> bool:
        """Send a single SMS message"""
        try:
            logger.info(f"Sending SMS to {self.to_number}")

            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )

            logger.info(f"SMS sent successfully. SID: {msg.sid}")
            return True

        except TwilioRestException as e:
            logger.error(f"Twilio error: {e.msg} (Code: {e.code})")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    def _send_multipart_sms(self, message: str, max_length: int) -> bool:
        """
        Send a long message as multiple SMS parts.

        Args:
            message: Full message to send
            max_length: Maximum length per message

        Returns:
            bool: True if all parts sent successfully
        """
        # Split message into chunks
        lines = message.split('\n')
        parts = []
        current_part = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > max_length:
                # Start new part
                parts.append('\n'.join(current_part))
                current_part = [line]
                current_length = line_length
            else:
                current_part.append(line)
                current_length += line_length

        # Add remaining part
        if current_part:
            parts.append('\n'.join(current_part))

        # Send each part
        logger.info(f"Sending message in {len(parts)} parts")
        success = True

        for i, part in enumerate(parts, 1):
            header = f"[{i}/{len(parts)}]\n"
            success = self._send_single_sms(header + part) and success

        return success

    def send_test_message(self) -> bool:
        """Send a test message to verify configuration"""
        test_message = "Test message from US Visa Bulletin Monitor. Configuration is working correctly!"
        logger.info("Sending test message...")
        return self.send_sms(test_message)
