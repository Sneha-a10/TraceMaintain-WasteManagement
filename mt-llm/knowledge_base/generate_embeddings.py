import json
import os
import glob
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Please install sentence-transformers: pip install sentence-transformers")
    exit(1)

try:
    import PyPDF2
except ImportError:
    print("Please install PyPDF2: pip install PyPDF2")
    exit(1)

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return text

def chunk_text(text, chunk_size=300, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def process_pdfs_to_kb():
    # 1. Paths
    # We trace up to TraceMaintain-WasteManagement, then into source
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    source_dir = os.path.join(base_dir, "source")
    
    output_chunks = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maintenance_chunks.json")
    output_kb = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledgebase.json")
    
    print(f"Base Dir: {base_dir}")
    print(f"Source Dir: {source_dir}")

    if not os.path.exists(source_dir):
        print(f"Source folder not found: {source_dir}")
        return
        
    pdf_files = glob.glob(os.path.join(source_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {source_dir}")
        return

    print(f"\nFound {len(pdf_files)} PDFs. Processing...")

    all_chunks = []
    chunk_counter = 1

    # 2. Extract and Split
    for pdf_file in pdf_files:
        print(f"Reading {os.path.basename(pdf_file)}...")
        raw_text = extract_text_from_pdf(pdf_file)
        text_chunks = chunk_text(raw_text)
        print(f"-> Generated {len(text_chunks)} chunks.")
        
        for text_chunk in text_chunks:
            chunk_data = {
                "chunk_id": f"CHUNK_{chunk_counter}",
                "chunk_type": "document",
                "asset_type": "city_infrastructure",
                "rule_id": None, # None allows semantic search to pick it up instead of exact match
                "urgency": "medium",
                "text": text_chunk,
                "source": os.path.basename(pdf_file)
            }
            all_chunks.append(chunk_data)
            chunk_counter += 1

    # 3. Save raw chunks
    with open(output_chunks, 'w') as f:
        json.dump(all_chunks, f, indent=4)
    print(f"\nSaved {len(all_chunks)} raw chunks to {output_chunks}")

    # 4. Generate Embeddings for KB
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2' (this may take a moment)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    kb_data = []
    total = len(all_chunks)
    for i, chunk in enumerate(all_chunks):
        if i % 10 == 0:
            print(f"Computing embedding for chunk {i}/{total}...")
        embedding = model.encode(chunk["text"]).tolist()
        kb_entry = {
            "id": chunk["chunk_id"],
            "text": chunk["text"],
            "embedding": embedding,
            "metadata": {
                "source": chunk["source"],
                "chunk_type": chunk["chunk_type"],
                "asset_type": chunk["asset_type"],
                "rule_id": chunk["rule_id"],
                "urgency": chunk["urgency"]
            }
        }
        kb_data.append(kb_entry)

    # 5. Save Knowledge Base
    with open(output_kb, 'w') as f:
        json.dump(kb_data, f, indent=4)
    print(f"\nSuccessfully generated Knowledge Base with {len(kb_data)} vectors to {output_kb}")

if __name__ == "__main__":
    process_pdfs_to_kb()
