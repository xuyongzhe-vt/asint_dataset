import re

def graph_based_similarity_filtering(filtered_attr_list, similarity_threshold) -> list[list[any]]:
    if len(filtered_attr_list) == 0:
        return []
    n = len(filtered_attr_list)
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            sim = jaccard_similarity(filtered_attr_list[i], filtered_attr_list[j])
            if sim >= similarity_threshold:
                adjacency[i].append(j)
                adjacency[j].append(i)
    visited = [False] * n
    clusters = []

    def dfs(start: int) -> list[int]:
        stack = [start]
        component = []
        visited[start] = True
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    stack.append(neighbor)
        return component
    for i in range(n):
        if not visited[i]:
            component = dfs(i)
            clusters.append([filtered_attr_list[idx] for idx in component])
    return clusters

def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub('[^a-z0-9 ]', '', s)
    s = s.strip()
    return s

def jaccard_similarity(a, b):
    a_set = set(normalize(a.lower()).split())
    b_set = set(normalize(b.lower()).split())
    if not a_set and (not b_set):
        return 1.0
    return len(a_set & b_set) / len(a_set | b_set)
