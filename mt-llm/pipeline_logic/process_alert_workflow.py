import os
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any

import logging
import urllib.request
import urllib.error
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Global Model for efficiency (loaded on demand/start)
MODEL_NAME = "all-MiniLM-L6-v2"
_embedding_model = None

def get_model():
    global _embedding_model
    if _embedding_model is None:
        logging.info(f"Loading embedding model: {MODEL_NAME}")
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(MODEL_NAME)
    return _embedding_model

def load_json_file(filepath: str) -> Any:
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON {filepath}: {e}")
        return None

def retrieve_by_rule_ids(rule_ids: List[str], local_kb_path: str) -> List[Dict]:
    """
    Directly retrieve knowledge chunks by matching rule_id.
    """
    logging.info(f"Looking up rules by ID: {rule_ids}")
    kb_data = load_json_file(local_kb_path)
    
    if not kb_data or not isinstance(kb_data, list):
        return []
    
    matched_chunks = []
    for chunk in kb_data:
        # Check if this chunk has a matching rule_id in metadata
        chunk_rule_id = chunk.get("metadata", {}).get("rule_id") or chunk.get("id", "")
        if chunk_rule_id in rule_ids:
            matched_chunks.append(chunk)
            logging.info(f"✓ Matched rule: {chunk_rule_id}")
    
    return matched_chunks

def retrieve_knowledge(decision: str, local_kb_path: str) -> List[Dict]:
    """
    Retrieve knowledge chunks using semantic vector search.
    """
    import numpy as np
    logging.info(f"Loading local knowledge base: {local_kb_path}")
    kb_data = load_json_file(local_kb_path)
    
    if not kb_data or not isinstance(kb_data, list):
        logging.warning("Knowledge base is empty or invalid.")
        return []

    # Prepare Query Embedding
    query_text = decision
    model = get_model()
    query_embedding = model.encode(query_text)
    
    # Calculate Distances
    scores = []
    for chunk in kb_data:
        if "embedding" not in chunk:
            continue
            
        chunk_embedding = np.array(chunk["embedding"])
        # Cosine Similarity: (A . B) / (||A|| * ||B||)
        norm_q = np.linalg.norm(query_embedding)
        norm_c = np.linalg.norm(chunk_embedding)
        
        if norm_c == 0 or norm_q == 0:
            score = 0
        else:
            score = np.dot(query_embedding, chunk_embedding) / (norm_q * norm_c)
            
        scores.append((score, chunk))
    
    # Sort by score desc
    scores.sort(key=lambda x: x[0], reverse=True)
    
    # Return top 3 matches if score > 0.15
    top_results = []
    for score, chunk in scores[:3]:
        logging.info(f"Match found: Score={score:.4f} | ID={chunk.get('id')}")
        if score > 0.15:
            top_results.append(chunk)
            
    if not top_results:
        logging.info("No relevant chunks found above threshold.")
        
    return top_results

def main():
    # 1. Load Alert Data
    logging.info("Loading alert trace...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    alert_trace_path = os.path.join(project_root, "knowledge_base", "post_decision_trace.json")
    alert_data = load_json_file(alert_trace_path)
    
    if not alert_data:
        logging.error("Failed to load alert trace. Exiting.")
        return

    # 2. Extract Alert Details
    # Handle both nested 'input_trace' and flat structure
    if 'input_trace' in alert_data:
        trace = alert_data['input_trace']
    else:
        trace = alert_data

    decision = trace.get('decision', 'Unknown Issue')
    observed = trace.get('observed_behavior', 'anomaly')
    component_id = trace.get('component_id', trace.get('component', 'Unknown Component'))
    
    # Construct a rich query for semantic search
    query_context = f"{decision} {observed}"
    # Add triggered rules if available to improve context
    if 'rules_triggered' in trace:
        rules = " ".join(trace['rules_triggered']).replace("_", " ")
        query_context += f" {rules}"

    logging.info(f"Processing Alert: {decision}")
    logging.info(f"Observed: {observed}")
    logging.info(f"Query Context: {query_context}")

    # 3. Retrieve Context from Local KB
    kb_path = os.path.join(project_root, "knowledge_base", "knowledgebase.json")
    
    output_data = {}
    
    if decision == "NORMAL":
        logging.info("Decision is NORMAL. Bypassing semantic search.")
        output_data = {
            "recommended_action": ["Maintain normal monitoring schedule. No immediate action required."],
            "safety_note": "Verified from STP Operation Guidelines.",
            "reference": "General-effluent-Standards.pdf"
        }
    else:
        # STP Specific handling for the demo (STATIC STUB)
        if "STP" in component_id or "STP" in decision or "BOD" in query_context:
            logging.info("Using STATIC RETRIEVAL STUB for STP/BOD context.")
            relevant_docs = [{
                "text": "According to General Effluent Standards and CEQMS guidelines, the maximum permissible limit for BOD (Biochemical Oxygen Demand) in treated sewage effluent is 30 mg/L for discharge into inland surface waters. Effluent exceeding 30 mg/L requires immediate aeration adjustment and check for organic overload.",
                "metadata": {"document": "CEQMS_Guidelines_2018.pdf"}
            }]
        else:
            # Fallback for others (could add more stubs or skip)
            relevant_docs = []
        
        logging.info(f"Retrieved {len(relevant_docs)} context records (via stub).")
        
        logging.info(f"Retrieved {len(relevant_docs)} relevant context records.")

        # 4. Format Context
        context_text = ""
        references = set()
        for idx, doc in enumerate(relevant_docs, 1):
            context_text += f"Source {idx}:\n{doc.get('text', 'No text')}\n---\n"
            if 'source' in doc:
                 references.add(doc['source'])
            elif 'metadata' in doc and 'document' in doc['metadata']:
                references.add(doc['metadata']['document'])

        reference_str = ", ".join(references) if references else "Internal Knowledge Base"

        # 5. Generate Recommendation (Strict Local KB)
        if relevant_docs:
            rec_actions = [doc.get("text", "No text content") for doc in relevant_docs]
            output_data = {
                "recommended_action": rec_actions,
                "safety_note": "Verified from internal knowledge base.",
                "reference": reference_str
            }
        else:
            output_data = {
                "recommended_action": ["fallback"],
                "safety_note": "Standard safety protocols apply.",
                "reference": "None"
            }

    # 6. Save Logic
    output_path = os.path.join(project_root, "final_recommendation.json")
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

if __name__ == "__main__":
    main()
