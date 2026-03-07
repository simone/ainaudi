"""
Content extractors for PDF and web pages.
"""
import pdfplumber
import PyPDF2
import requests
from bs4 import BeautifulSoup
import html2text
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF files."""

    @staticmethod
    def extract_text(pdf_source) -> str:
        """
        Extract text from PDF (file path, URL, or bytes).

        Args:
            pdf_source: File path string, URL string, or BytesIO

        Returns:
            str: Extracted text
        """
        try:
            # If URL, download first
            if isinstance(pdf_source, str) and pdf_source.startswith('http'):
                response = requests.get(pdf_source, timeout=30)
                response.raise_for_status()
                pdf_source = BytesIO(response.content)
            # If local path doesn't exist, try downloading from ainaudi.it
            elif isinstance(pdf_source, str) and not os.path.exists(pdf_source):
                ainaudi_url = f"https://ainaudi.it{pdf_source}"
                logger.info(f"Local file not found, trying to download from {ainaudi_url}")
                try:
                    response = requests.get(ainaudi_url, timeout=30)
                    response.raise_for_status()
                    pdf_source = BytesIO(response.content)
                    logger.info(f"Successfully downloaded PDF from {ainaudi_url}")
                except Exception as e:
                    logger.error(f"Failed to download from {ainaudi_url}: {e}")
                    raise FileNotFoundError(f"PDF not found locally at {pdf_source} and could not download from {ainaudi_url}")

            # Try pdfplumber (better quality)
            try:
                with pdfplumber.open(pdf_source) as pdf:
                    text = []
                    for page in pdf.pages:
                        text.append(page.extract_text() or '')
                    return '\n\n'.join(text)
            except Exception as e:
                logger.warning(f"pdfplumber failed, fallback to PyPDF2: {e}")

            # Fallback to PyPDF2
            if isinstance(pdf_source, str):
                with open(pdf_source, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = []
                    for page in reader.pages:
                        text.append(page.extract_text() or '')
                    return '\n\n'.join(text)
            else:
                # BytesIO (from download or URL)
                reader = PyPDF2.PdfReader(pdf_source)
                text = []
                for page in reader.pages:
                    text.append(page.extract_text() or '')
                return '\n\n'.join(text)

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}", exc_info=True)
            return ""


class WebExtractor:
    """Extract text from web pages."""

    @staticmethod
    def extract_text(url: str) -> str:
        """
        Extract text from web page URL.

        Args:
            url: Web page URL

        Returns:
            str: Extracted plain text
        """
        try:
            # Fetch page
            headers = {
                'User-Agent': 'Mozilla/5.0 (AInaudi Bot)'
            }
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()

            # Convert to plain text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0  # No wrapping
            text = h.handle(str(soup))

            return text.strip()

        except Exception as e:
            logger.error(f"Web scraping failed for {url}: {e}", exc_info=True)
            return ""
