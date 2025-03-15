import os
import sqlite3
import fitz  # PyMuPDF
import cv2
import numpy as np
import pytesseract

# Define paths
pdf_folder = r"E:\Innovatex\output\output"
db_path = r"E:\Innovatex\output\output\db.sqlite"  # Ensure the full path is given
tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Connect to SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pdf_texts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        text TEXT
    )
""")
conn.commit()

def pdf_to_images(pdf_path):
    """Convert PDF pages to images using PyMuPDF (fitz)"""
    doc = fitz.open(pdf_path)
    images = []
    
    for page in doc:
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        images.append(img)
    
    return images

def extract_text_from_image(image):
    """Extract text from an image using Tesseract OCR"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return text.strip()

# Process each PDF in the folder
for filename in os.listdir(pdf_folder):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder, filename)
        images = pdf_to_images(pdf_path)
        
        extracted_text = "\n".join([extract_text_from_image(img) for img in images])

        # Insert text into database
        cursor.execute("INSERT INTO pdf_texts (filename, text) VALUES (?, ?)", (filename, extracted_text))
        conn.commit()

# Close database connection
conn.close()

print("Scanned PDFs have been converted and stored in the database!")