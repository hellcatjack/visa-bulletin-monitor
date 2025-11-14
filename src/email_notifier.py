import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Union, List

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send email notifications using SMTP"""

    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str,
                 smtp_password: str, from_email: str, to_email: Union[str, List[str]], use_tls: bool = True):
        """
        Initialize Email notifier.

        Args:
            smtp_host: SMTP server hostname (e.g., smtp.gmail.com)
            smtp_port: SMTP server port (e.g., 587 for TLS, 465 for SSL)
            smtp_user: SMTP username (usually email address)
            smtp_password: SMTP password or app-specific password
            from_email: Sender email address
            to_email: Recipient email address(es) - can be a single email string or a list of emails
            use_tls: Whether to use TLS (default: True)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email

        # Convert to_email to list if it's a string
        if isinstance(to_email, str):
            self.to_emails = [email.strip() for email in to_email.split(',') if email.strip()]
        else:
            self.to_emails = to_email

        self.use_tls = use_tls

        logger.info(f"Email notifier initialized: {smtp_host}:{smtp_port}")
        logger.info(f"Recipients: {', '.join(self.to_emails)}")

    def send_email(self, subject: str, message: str, html: bool = False) -> bool:
        """
        Send an email notification.

        Args:
            subject: Email subject
            message: Email body (plain text or HTML)
            html: Whether message is HTML (default: False)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending email to {len(self.to_emails)} recipient(s): {', '.join(self.to_emails)}")

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)  # Join all recipients for the header

            # Attach message body
            if html:
                msg.attach(MIMEText(message, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(message, 'plain', 'utf-8'))

            # Connect to SMTP server
            if self.use_tls:
                # Use STARTTLS (port 587)
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                # Use SSL (port 465)
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            # Login and send
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully to {len(self.to_emails)} recipient(s)")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_visa_update(self, message: str) -> bool:
        """
        Send visa bulletin update notification.

        Args:
            message: Formatted update message

        Returns:
            bool: True if sent successfully
        """
        subject = "🔔 美国签证排期更新通知 - US Visa Bulletin Update"

        # Convert plain text message to HTML for better formatting
        html_message = self._format_html_message(message)

        return self.send_email(subject, html_message, html=True)

    def _format_html_message(self, plain_message: str) -> str:
        """
        Convert plain text message to HTML with better formatting.

        Args:
            plain_message: Plain text message

        Returns:
            str: HTML formatted message
        """
        # Escape HTML special characters in the message
        import html
        escaped_message = html.escape(plain_message)

        # Replace emoji markers with actual emojis
        escaped_message = escaped_message.replace('📈', '📈')
        escaped_message = escaped_message.replace('📉', '📉')
        escaped_message = escaped_message.replace('✅', '✅')
        escaped_message = escaped_message.replace('❌', '❌')
        escaped_message = escaped_message.replace('🔄', '🔄')

        # Convert newlines to <br> and preserve formatting
        lines = escaped_message.split('\n')
        formatted_lines = []

        for line in lines:
            if line.startswith('===') or line.startswith('---'):
                formatted_lines.append('<hr>')
            elif line.startswith('【') or line.startswith('##'):
                formatted_lines.append(f'<h3 style="color: #2c3e50; margin-top: 15px;">{line}</h3>')
            elif line.strip().startswith('上期:') or line.strip().startswith('本期:'):
                formatted_lines.append(f'<p style="color: #34495e; font-weight: bold;">{line}</p>')
            elif line.strip().startswith('EB-') or line.strip().startswith('F'):
                formatted_lines.append(f'<p style="margin: 5px 0; padding-left: 20px; font-family: monospace;">{line}</p>')
            elif line.strip():
                formatted_lines.append(f'<p>{line}</p>')
            else:
                formatted_lines.append('<br>')

        html_body = '\n'.join(formatted_lines)

        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, 'Microsoft YaHei', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #e74c3c; margin: 0;">🔔 签证排期更新</h1>
            <p style="color: #7f8c8d; margin: 5px 0;">US Visa Bulletin Update</p>
        </div>
        <div style="background-color: #ecf0f1; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
            {html_body}
        </div>
        <div style="text-align: center; color: #95a5a6; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ecf0f1;">
            <p>此邮件由美国签证排期监控系统自动发送</p>
            <p>US Visa Bulletin Monitor - Automated Notification</p>
        </div>
    </div>
</body>
</html>
"""
        return html_template

    def send_test_message(self) -> bool:
        """Send a test email to verify configuration"""
        subject = "🧪 测试邮件 - Test Email from US Visa Bulletin Monitor"
        message = """
<h2>测试成功！ Test Successful!</h2>
<p>恭喜！您的邮件通知配置正确。</p>
<p>Congratulations! Your email notification is configured correctly.</p>
<br>
<p><strong>系统信息 System Info:</strong></p>
<ul>
    <li>发件人 From: {from_email}</li>
    <li>收件人 To: {to_emails}</li>
    <li>SMTP服务器 Server: {smtp_host}:{smtp_port}</li>
</ul>
<p>您将在签证排期发生变化时收到通知。</p>
<p>You will receive notifications when visa bulletin changes are detected.</p>
""".format(from_email=self.from_email, to_emails=', '.join(self.to_emails),
           smtp_host=self.smtp_host, smtp_port=self.smtp_port)

        logger.info("Sending test email...")
        return self.send_email(subject, message, html=True)
