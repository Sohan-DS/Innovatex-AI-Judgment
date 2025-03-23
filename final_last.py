import os
import streamlit as st
import sqlite3
import faiss
import numpy as np
import speech_recognition as sr
import pdfplumber
from sentence_transformers import SentenceTransformer
from fuzzywuzzy import process

# Disable TensorFlow & Hugging Face warnings
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Load Sentence Transformer Model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Database Path
DB_PATH = r"E:\Innovatex\output\db.sqlite"

# ✅ Cache Database Loading
@st.cache_data
def load_case_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, case_summary FROM court_judgments")
    data = cursor.fetchall()
    conn.close()
    return data

# Load data once
data = load_case_data()
case_texts = [row[1] for row in data if row[1] is not None]
case_ids = [row[0] for row in data if row[1] is not None]

# ✅ Cache FAISS Index
@st.cache_resource
def build_faiss_index(case_texts):
    if case_texts:
        embeddings = model.encode(case_texts, convert_to_numpy=True)
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        return index
    return None

index = build_faiss_index(case_texts)

# ✅ Cache Query Embeddings
@st.cache_data
def get_query_embedding(query):
    return model.encode([query], convert_to_numpy=True)

# Function: Fuzzy Search
def fuzzy_search(query, texts, top_n=5):
    results = process.extract(query, texts, limit=top_n)
    return [(res[0], res[1]) for res in results]  

# Function: Keyword Search
def keyword_search(query, texts, top_n=5):
    results = [text for text in texts if query.lower() in text.lower()]
    return [(res, 100) for res in results[:top_n]] if results else [("No keyword matches found.", 0)]

# Function: Optimized Semantic Search
def semantic_search(query, top_n=5):
    if index is None or len(case_texts) == 0:
        return [("No case data available.", 0)]
    query_embedding = get_query_embedding(query)  # Cached embeddings
    _, indices = index.search(query_embedding, top_n)
    return [(case_texts[i], 100) for i in indices[0]]

# Function: Speech-to-Text
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Speak now!")
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return "Sorry, could not understand the speech."
        except sr.RequestError:
            return "Speech recognition service error."
        except sr.WaitTimeoutError:
            return "No speech detected."

# Function: Extract Text from PDF
def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text if text else "Could not extract text."

# Streamlit UI
st.title("🔍 Legal Search & AI Chatbot")

# Search Section
search_type = st.selectbox("Choose Search Type:", ["Fuzzy", "Keyword", "Semantic"])
search_query = st.text_input("Enter search query:")

if search_query:
    st.write("**🔍 Search Results:**")
    
    if search_type == "Fuzzy":
        results = fuzzy_search(search_query, case_texts)
    elif search_type == "Keyword":
        results = keyword_search(search_query, case_texts)
    else:
        results = semantic_search(search_query)

    for i, (text, score) in enumerate(results):
        with st.expander(f"🔹 **Result {i+1} (Relevance: {score}%)**"):
            st.write(text[:500] + "...")  

# Chatbot Section
st.subheader("💬 AI Chatbot")
if st.button("🎙️ Speak"):
    chatbot_input = speech_to_text()
    st.write(f"Recognized Speech: {chatbot_input}")
else:
    chatbot_input = st.text_input("Ask a legal question:")

if chatbot_input:
    st.subheader("🤖 Chatbot Response:")
    st.write("AI Chatbot Disabled for Speed Optimization.")

# File Upload for Case Summarization
uploaded_file = st.file_uploader("Upload a Case File (PDF)", type=["pdf"])

if uploaded_file is not None:
    case_text = extract_text_from_pdf(uploaded_file)
    st.subheader("📄 Case Summary:")
    st.write(case_text[:500] + "...")  

# **Restricted PDF Upload (Only Court Members)**
st.subheader("🔒 Court Member Document Upload")
auth_code = st.text_input("Enter Authorization Code to Upload:")

if auth_code == "COURT123":
    uploaded_doc = st.file_uploader("Upload a Court Document (PDF)", type=["pdf"])
    
    if uploaded_doc:
        doc_text = extract_text_from_pdf(uploaded_doc)
        if doc_text != "Could not extract text.":
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO court_judgments (case_summary) VALUES (?)", (doc_text,))
            conn.commit()
            conn.close()
            st.success("✅ Document successfully added to the database!")
        else:
            st.error("❌ Unable to extract text from the document.")
else:
    st.warning("⚠️ Only authorized court members can upload documents.")