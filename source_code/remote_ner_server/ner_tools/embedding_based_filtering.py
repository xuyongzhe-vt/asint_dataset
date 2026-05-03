import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import torch
import copy

def construct_faiss(unique_org_names: list[str], gpu_index):
    model = SentenceTransformer('all-MiniLM-L6-v2', device=f'cuda:{gpu_index}')
    embeddings_A = model.encode(unique_org_names, show_progress_bar=True)
    embeddings_A = np.array(embeddings_A).astype('float32')
    index = faiss.IndexFlatL2(embeddings_A.shape[1])
    index.add(embeddings_A)
    return (model, index)

def get_similar_name_list(base_org_name: str, candidate_org_name_list: list[str], threshold, model):
    if len(candidate_org_name_list) == 0:
        return []
    base_embedding = model.encode([base_org_name])
    candidate_embeddings = model.encode(candidate_org_name_list)
    similarities = cosine_similarity(base_embedding, candidate_embeddings)
    similar_names = [candidate_org_name_list[i] for i in range(len(candidate_org_name_list)) if (similarities[0][i] >= threshold or candidate_org_name_list[i] in base_org_name) and len(candidate_org_name_list[i]) > 2]
    return similar_names

def clean_up_org_name(org_name_list: list[str]):
    return [org_name for org_name in org_name_list]

def filter_org_name_verbose(base_org_name, org_list: list[str], comparing_org_list: list[str], faiss_model, faiss_index):
    return search_faiss_verbose(base_org_name, org_list, comparing_org_list, faiss_model, faiss_index, 1, 0.1)

def search_faiss_verbose(base_org_name, candidate_org_names, comparing_org_list, ner_model, ner_index, top_k, threshold):
    embeddings_B = ner_model.encode(candidate_org_names).astype('float32')
    (distances, indices) = ner_index.search(embeddings_B, top_k)
    (matched_orgs, matching_orgs) = ([], [])
    for (i, dist) in enumerate(distances[:, 0]):
        if len(candidate_org_names[i]) > 2:
            if dist < threshold:
                matched_orgs.append(candidate_org_names[i])
                matching_orgs.append(comparing_org_list[indices[i][0]])
            elif candidate_org_names[i] in base_org_name:
                matched_orgs.append(candidate_org_names[i])
                matching_orgs.append(base_org_name)
    unmatched_orgs = set(candidate_org_names) - set(matched_orgs)
    for unmatched_org in unmatched_orgs:
        for matched_org in matched_orgs:
            if matched_org in unmatched_org.split():
                matched_orgs.append(unmatched_org)
                matching_orgs.append(matched_org)
                break
    return (matched_orgs, matching_orgs)
