"""
Email sender with HTML template and PDF attachment.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('EMAIL_PORT', 587))
SMTP_USER = os.environ.get('EMAIL_HOST_USER', '')
SMTP_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'


def send_preview_email(to, subject, from_email, pdf_bytes, pdf_filename, confirm_url):
    """
    Send preview email with PDF attachment and confirmation link.

    Args:
        to: List of recipient emails
        subject: Email subject
        from_email: Sender email address
        pdf_bytes: PDF file content as bytes
        pdf_filename: Filename for attachment
        confirm_url: URL for confirmation link

    Raises:
        Exception: If email sending fails
    """
    logger.info(f"Sending preview email to {to}")

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to) if isinstance(to, list) else to

    # HTML body with confirmation button
    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: #48bb78;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .content {{
                padding: 20px;
                background: #f9f9f9;
            }}
            .button {{
                display: inline-block;
                margin: 30px 0;
                padding: 15px 40px;
                background: #48bb78;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                text-align: center;
            }}
            .button:hover {{
                background: #38a169;
            }}
            .warning {{
                background: #fffaf0;
                border: 1px solid #fbd38d;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Preview PDF Generato</h2>
            </div>

            <div class="content">
                <p>Il tuo documento PDF è pronto per la revisione.</p>
                <p><strong>Allegato:</strong> {pdf_filename}</p>

                <div style="text-align: center;">
                    <a href="{confirm_url}" class="button">
                        ✓ Conferma e Finalizza PDF
                    </a>
                </div>

                <div class="warning">
                    <strong>⚠️ Importante:</strong>
                    <ul>
                        <li>Questo link è valido per <strong>24 ore</strong></li>
                        <li>Dopo la conferma, il documento diventa <strong>immutabile</strong></li>
                        <li>Se trovi errori nel PDF, <strong>NON confermare</strong> e contatta l'amministratore</li>
                    </ul>
                </div>

                <p>
                    <strong>Cosa fare:</strong><br>
                    1. Apri l'allegato PDF e verifica che tutti i dati siano corretti<br>
                    2. Se tutto è corretto, clicca il pulsante "Conferma"<br>
                    3. Se ci sono errori, ignora questa email
                </p>
            </div>

            <div class="footer">
                <p>Movimento 5 Stelle - Sistema AInaudi</p>
                <p>Questo è un messaggio automatico, non rispondere a questa email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text alternative
    text = f"""
    Preview PDF Generato

    Il tuo documento PDF è pronto per la revisione.
    Allegato: {pdf_filename}

    Per confermare e finalizzare il documento, visita:
    {confirm_url}

    IMPORTANTE:
    - Link valido 24 ore
    - Dopo conferma, documento immutabile
    - Se trovi errori, NON confermare

    ---
    Movimento 5 Stelle - Sistema AInaudi
    """

    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    # Attach PDF
    pdf_attachment = MIMEApplication(pdf_bytes, _subtype='pdf')
    pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
    msg.attach(pdf_attachment)

    # Send email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if USE_TLS:
                server.starttls()

            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)

            recipients = to if isinstance(to, list) else [to]
            server.sendmail(from_email, recipients, msg.as_string())

        logger.info(f"Email sent successfully to {to}")

    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}", exc_info=True)
        raise
