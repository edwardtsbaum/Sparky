import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

class Emailer:

    def __init__(self, smtp_server="smtp.zoho.com", smtp_port=465):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.context = ssl.create_default_context()
        
    def create_message(self, recipient_email: str, subject: str, body: str) -> MIMEMultipart:
        """Create a MIME message for email"""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = os.getenv("ZOHO_EMAIL")
        message["To"] = recipient_email
        


        # Attach the email body (plain text)
        text_part = MIMEText(body, "plain")
        message.attach(text_part)
        
        return message
        
    def send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        """Send email via SMTP server"""
        try:
            # Create the email message
            message = self.create_message(recipient_email, subject, body)
            
            
            # Connect to SMTP server using SSL
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=self.context) as server:
                # Log in to account
                server.login(os.getenv("ZOHO_EMAIL"), os.getenv("ZOHO_PASSWORD"))
                # Send the email
                server.sendmail(os.getenv("ZOHO_EMAIL"), recipient_email, message.as_string())
                

            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def test_email(self, recipient_email: str) -> bool:
        """Send a test email to verify configuration"""
        subject = "Test Email"
        body = "This is a test email to verify the email configuration is working correctly."
        

        success = self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            body=body

        )
        
        if success:
            logger.info("Test email sent successfully")
        else:
            logger.error("Test email failed")
            
        return success


# Example usage
# if __name__ == "__main__":
#     emailer = Emailer()
    
#     # Configuration
#     recipient_email = "edwardt.s.baum@gmail.com"
    
#     # Send test email
#     emailer.test_email(recipient_email)
