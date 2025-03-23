import os
import pdfplumber
import sqlite3
import pytesseract
from PIL import Image
import re
import spacy

# Paths
PDF_DIR = r"E:\Innovatex\output"  # Folder containing PDFs
DB_PATH = r"E:\Innovatex\output\db.sqlite"

# Set Tesseract OCR path (Update this path based on your system)
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Load spaCy model for NER
nlp = spacy.load("en_core_web_sm")

# Connect to SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create table for storing metadata + full text
cursor.execute('''
    CREATE TABLE IF NOT EXISTS court_judgments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        court_name TEXT,
        case_number TEXT,
        date_of_judgment TEXT,
        petitioner TEXT,
        respondent TEXT,
        judge_name TEXT,
        case_summary TEXT,
        keywords TEXT
    )
''')
conn.commit()

# Function to extract text using pdfplumber
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
            else:
                # If no text is extracted, use OCR on image
                img = page.to_image(resolution=300).annotated  # Convert to PIL Image
                text += pytesseract.image_to_string(img) + "\n"
    return text.strip()

# Function to extract metadata using regex & NER
def extract_metadata(text):
    doc = nlp(text)
    metadata = {
        "court_name": None,
        "case_number": None,
        "date_of_judgment": None,
        "petitioner": None,
        "respondent": None,
        "judge_name": None,
        "case_summary": None,
        "keywords": None
    }

    # Extract court name, judge name using spaCy
    for ent in doc.ents:
        if ent.label_ == "ORG" and ("court" in ent.text.lower() or "tribunal" in ent.text.lower()):
            metadata["court_name"] = ent.text
        elif ent.label_ == "PERSON" and ("judge" in ent.text.lower() or "hon'ble" in ent.text.lower()):
            metadata["judge_name"] = ent.text

    # Extract Case Number (Regex)
    case_number_match = re.search(r"Case\s*(No|Number)?\s*[:\s]*([\w/-]+)", text, re.IGNORECASE)
    metadata["case_number"] = case_number_match.group(2) if case_number_match else "Unknown"

    # Extract Date of Judgment (Regex)
    date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    metadata["date_of_judgment"] = date_match.group(1) if date_match else "Unknown"

    # Extract Petitioner & Respondent (Simple Heuristic)
    petitioner_match = re.search(r"Petitioner\s*[:\s]*([\w\s]+)", text, re.IGNORECASE)
    respondent_match = re.search(r"Respondent\s*[:\s]*([\w\s]+)", text, re.IGNORECASE)
    metadata["petitioner"] = petitioner_match.group(1).strip() if petitioner_match else "Unknown"
    metadata["respondent"] = respondent_match.group(1).strip() if respondent_match else "Unknown"

    # Generate Case Summary (First 300 words)
    words = text.split()
    metadata["case_summary"] = " ".join(words[:300]) if words else "Unknown"

    # Generate Keywords (Most Frequent Words)
    words = re.findall(r'\b\w+\b', text.lower())
    common_words = {"the", "and", "in", "of", "to", "a", "is", "for", "on", "with"}  # Stopwords
    keywords = [word for word in words if word not in common_words]
    freq = {word: keywords.count(word) for word in set(keywords)}
    sorted_keywords = sorted(freq, key=freq.get, reverse=True)
    metadata["keywords"] = ", ".join(sorted_keywords[:5]) if sorted_keywords else "Unknown"

    return metadata

# Process all PDFs
for pdf_file in os.listdir(PDF_DIR):
    if pdf_file.endswith(".pdf"):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        
        # Extract text (either directly or via OCR)
        extracted_text = extract_text_from_pdf(pdf_path)

        # Extract metadata from text
        metadata = extract_metadata(extracted_text)

        # Store in SQLite database
        cursor.execute('''
            INSERT INTO court_judgments (court_name, case_number, date_of_judgment, petitioner, respondent, judge_name, case_summary, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata["court_name"], metadata["case_number"], metadata["date_of_judgment"],
            metadata["petitioner"], metadata["respondent"], metadata["judge_name"],
            metadata["case_summary"], metadata["keywords"]
        ))

conn.commit()
conn.close()

print("PDF Metadata Extraction + SQLite Storage DONE!")