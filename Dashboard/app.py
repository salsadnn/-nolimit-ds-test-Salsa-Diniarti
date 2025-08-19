from flask import Flask, render_template, request
import os
import re
import string
import json
import numpy as np
import joblib
import faiss
from sentence_transformers import SentenceTransformer

# Inisialisasi Flask
app = Flask(__name__)

# Path model & output
OUT_DIR = r"D:\Data Salsa\Kuliah\Data Analyst\Project_Sentiment Analyst\Dashboard\repo_output"

# Load model & label encoder
clf = joblib.load(os.path.join(OUT_DIR, "clf_logreg.joblib"))
le = joblib.load(os.path.join(OUT_DIR, "label_encoder.joblib"))

# Metadata
with open(os.path.join(OUT_DIR, "metadata.json"), "r", encoding="utf-8") as f:
    meta = json.load(f)
label_names = meta["label_names"]

# Sentence Transformer
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embedder = SentenceTransformer(EMBED_MODEL)

# Load FAISS index (embeddings)
embeddings = np.load(os.path.join(OUT_DIR, "embeddings.npy"))
d = embeddings.shape[1]
index = faiss.IndexFlatL2(d)
index.add(embeddings)

# --- Fungsi Preprocessing ---
def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)  # hapus URL
    text = re.sub(r"\d+", " ", text)  # hapus angka
    text = text.translate(str.maketrans("", "", string.punctuation))  # hapus tanda baca
    text = re.sub(r"\s+", " ", text).strip()
    return text

# --- Prediksi dengan probabilitas ---
def predict_with_probs(text: str):
    text_clean = clean_text(text)
    emb = embedder.encode([text_clean], convert_to_numpy=True).astype("float32")
    probs = clf.predict_proba(emb)[0]
    return {label_names[i]: float(probs[i]) for i in range(len(label_names))}

# --- Cari teks serupa dengan FAISS ---
def search_similar(text: str, top_k=5):
    emb = embedder.encode([clean_text(text)], convert_to_numpy=True).astype("float32")
    D, I = index.search(emb, top_k)
    results = []
    for dist, idx in zip(D[0], I[0]):
        results.append({
            "index": int(idx),
            "text": meta.get("text_list", ["Unknown"])[idx] if meta.get("text_list") else "Unknown",
            "label": label_names[int(idx % len(label_names))],
            "distance": float(dist)
        })
    return results

# --- Route utama ---
@app.route("/", methods=["GET", "POST"])
def home():
    prediction = None
    probs = None
    similar_texts = None

    if request.method == "POST":
        ulasan = request.form.get("txtName")  # sesuai dengan form name di HTML
        if ulasan:
            probs = predict_with_probs(ulasan)
            prediction = max(probs, key=probs.get)
            similar_texts = search_similar(ulasan, top_k=3)

    return render_template(
        "index.html",
        prediction=prediction,
        probs=probs,
        similar_texts=similar_texts
    )

# --- Run Flask ---
if __name__ == "__main__":
    app.run(port=5000, debug=True)
