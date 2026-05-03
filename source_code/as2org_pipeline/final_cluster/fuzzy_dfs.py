import re
import json
from collections import defaultdict
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub('\\b(inc|llc|ltd|corp|company|co)\\b\\.?', '', s)
    s = re.sub('[^a-z0-9 ]+', '', s)
    s = re.sub('\\s+', ' ', s)
    return s.strip()

def extract_unique_attrs(org_dict, attr_keys) -> list[str]:
    unique_attrs = set()
    for org in org_dict.values():
        for attr_key in attr_keys:
            if attr_key in org:
                for val in org[attr_key]:
                    norm_val = normalize(val)
                    if norm_val:
                        unique_attrs.add(norm_val)
    print(len(unique_attrs))
    return list(unique_attrs)
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_strings(strings: list[str]) -> np.ndarray:
    return model.encode(strings, show_progress_bar=True, batch_size=256)

def build_faiss_ivf_index(embeddings: np.ndarray, nlist: int=100):
    dim = embeddings.shape[1]
    quantizer = faiss.IndexFlatL2(dim)
    index = faiss.IndexIVFFlat(quantizer, dim, nlist)
    index.train(embeddings)
    index.add(embeddings)
    return index

def union_find_clustering(embeddings: np.ndarray, strings: list[str], threshold: float=0.1):
    index = build_faiss_ivf_index(embeddings)
    n = embeddings.shape[0]
    parent = list(range(n))

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        parent[find(x)] = find(y)
    (D, I) = index.search(embeddings, 10)
    for i in range(n):
        for (j, dist) in zip(I[i], D[i]):
            if i != j and dist < threshold:
                union(i, j)
    clusters = defaultdict(set)
    for (i, s) in enumerate(strings):
        root = find(i)
        clusters[root].add(s)
    string_to_cluster = {}
    for (root, members) in clusters.items():
        canonical = sorted(members)[0]
        for member in members:
            string_to_cluster[member] = 'VIRTUAL_NODE_' + canonical
    return string_to_cluster

def build_graph(org_dict, attr_keys):
    graph = defaultdict(list)
    nodes = set()
    obj_dict = {}
    print('extract_unique_attrs started')
    all_attrs = extract_unique_attrs(org_dict, attr_keys)
    print('embed_strings started')
    embeddings = embed_strings(all_attrs)
    print('union_find_clustering started')
    attr_to_virtual = union_find_clustering(embeddings, all_attrs)
    print('union_find_clustering finished')
    i = 0
    for (org_name, org_json) in org_dict.items():
        obj_id = 'CONCRETE_NODE_' + org_name
        graph[obj_id] = []
        nodes.add(obj_id)
        for attr_key in attr_keys:
            if attr_key in org_json:
                for val in org_json[attr_key]:
                    norm_val = normalize(val)
                    virtual_id = attr_to_virtual.get(norm_val)
                    if virtual_id:
                        graph[obj_id].append(virtual_id)
                        graph[virtual_id].append(obj_id)
                        nodes.add(virtual_id)
        obj_dict[obj_id] = org_json
        i += 1
    for k in graph:
        graph[k] = list(set(graph[k]))
    return (graph, nodes, obj_dict)

def find_families(graph):
    visited = set()
    families = []

    def iterative_dfs(start_node):
        stack = [start_node]
        family = []
        visited.add(start_node)
        while stack:
            node = stack.pop()
            family.append(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        return family
    for node in graph:
        if node not in visited:
            families.append(iterative_dfs(node))
    return families

def parse_families(families, obj_dict):
    result = []
    for family in families:
        group = []
        for node in family:
            if node.startswith('CONCRETE_NODE_'):
                group.append(obj_dict[node])
        if group:
            result.append(group)
    return result

def dsf_search(org_dict: dict[str, dict[str, list[str]]], attr_type_to_cluster: list[str]) -> list[list[dict[str, list[str]]]]:
    (graph, nodes, obj_dict) = build_graph(org_dict, attr_type_to_cluster)
    families = find_families(graph)
    return parse_families(families, obj_dict)
