import PyPDF2
import pdfplumber
import io

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from PDF file"""
    text = ""
    
    try:
        # Try pdfplumber first (better quality)
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        # Fallback to PyPDF2
        try:
            pdf_file.seek(0)
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            text = f"Error extracting PDF: {e}"
    
    return text