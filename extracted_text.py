import pytesseract
from pdf2image import convert_from_path
import os
import sqlite3

# Configure Tesseract path (only for Windows users)
# pytesseract.pytesseract.tesseract_cmd = r"D:\Hackathon\tesseract.exe"

def create_database():
    """Create the SQLite database and judgments table if not exists."""
    conn = sqlite3.connect("judgments.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS judgments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_name TEXT,
            judge TEXT,
            date TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def extract_text_from_pdf(pdf_path):
    """Convert PDF to images and extract text using Tesseract OCR."""
    try:
        images = convert_from_path(pdf_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return ""

def process_pdfs(pdf_folder):
    """Process all PDFs in a folder and store extracted text in SQLite."""
    conn = sqlite3.connect("judgments.db")
    cursor = conn.cursor()

    for pdf_file in os.listdir(pdf_folder):
        if pdf_file.endswith(".pdf"):
            pdf_path = os.path.join(pdf_folder, pdf_file)
            print(f"Processing: {pdf_path}")
            
            text = extract_text_from_pdf(pdf_path)

            if text:  # Only insert if text was extracted
                case_name = pdf_file.replace(".pdf", "")
                judge = "Unknown"  # Future improvement: Extract using regex/ML
                date = "Unknown"

                cursor.execute("INSERT INTO judgments (case_name, judge, date, content) VALUES (?, ?, ?, ?)",
                               (case_name, judge, date, text))
                conn.commit()

    conn.close()
    print("PDF Processing Completed!")

# Run database setup and process PDFs
create_database()
process_pdfs("output")
