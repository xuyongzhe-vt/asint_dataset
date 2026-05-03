from as2org_pipeline.final_cluster.attr_cleaner import graph_based_similarity_filtering
from collections import defaultdict, Counter, deque
import os
import json
import networkx as nx

def cluster_parent_and_child(final_alias_groups):
    alias_dict = {}
    for alias_group in final_alias_groups:
        alias_dict[alias_group['alias_group_index']] = alias_group
    alias_group_list = generate_parent_keywords(final_alias_groups)
    child_to_parents_dict = _cluster_parent_and_child(alias_group_list)
    for (child, parent) in child_to_parents_dict.items():
        assert len(parent) == 1
    print(len(child_to_parents_dict))
    parsed_cliques_list = parse_cliques_from_parent_map(child_to_parents_dict)
    ensure_global_uniqueness(parsed_cliques_list)
    final_clique_list = []
    clique_id = 0
    already_seen_org_id_set = set()
    for clique in parsed_cliques_list:
        clique_member = []
        for org_id in clique:
            already_seen_org_id_set.add(org_id)
            alias_obj = alias_dict[org_id]
            if org_id in child_to_parents_dict:
                alias_obj['parent_alias_group_id'] = child_to_parents_dict[org_id]
            clique_member.append(alias_obj)
        final_clique_list.append({'clique_id': clique_id, 'clique_alias_group_size': len(clique_member), 'clique_alias_group_list': clique_member})
        clique_id += 1
    remaining_org_id_list = list(set(list(alias_dict.keys())) - already_seen_org_id_set)
    for remaining_org_id in remaining_org_id_list:
        final_clique_list.append({'clique_id': clique_id, 'clique_alias_group_size': 1, 'clique_alias_group_list': [alias_dict[remaining_org_id]]})
        clique_id += 1
    return final_clique_list

def generate_parent_keywords(alias_group_list, freq_threshold=0.5):
    for alias_group in alias_group_list:
        org_num = len(alias_group['organization_list'])
        keyword_dict = {}
        for org_json in alias_group['organization_list']:
            org_name = org_json['org_name']
            for keyword in org_json['parents_attr_list']:
                keyword = keyword.strip().lower()
                keyword_dict.setdefault(keyword, []).append(org_name)
        all_keywords = list(keyword_dict.keys())
        attr_clusters = graph_based_similarity_filtering(all_keywords, 0.5)
        final_attr = []
        for attr_cluster in attr_clusters:
            supporting_orgs = set()
            for attr in attr_cluster:
                supporting_orgs.update(keyword_dict[attr])
            if len(supporting_orgs) >= freq_threshold * org_num:
                final_attr += attr_cluster
        if final_attr:
            alias_group['parents_attr_list'] = [attr.lower() for attr in final_attr]
        else:
            alias_group['parents_attr_list'] = []
    return alias_group_list

def _cluster_parent_and_child(alias_group_list, match_threshold=1):
    keyword_to_group_ids = defaultdict(set)
    group_id_to_alias_keywords = {}
    for group in alias_group_list:
        group_id = group['alias_group_index']
        alias_keywords = set(map(str.lower, group['alias_attr_list']))
        group_id_to_alias_keywords[group_id] = alias_keywords
        for alias_keyword in alias_keywords:
            keyword_to_group_ids[alias_keyword].add(group_id)
    child_to_parents = defaultdict(list)
    for group in alias_group_list:
        child_id = group['alias_group_index']
        parent_keywords = set(map(str.lower, group['parents_attr_list']))
        parent_counter = Counter()
        for parent_keyword in parent_keywords:
            for possible_parent_id in keyword_to_group_ids.get(parent_keyword, []):
                if possible_parent_id == child_id:
                    continue
                parent_counter[possible_parent_id] += 1
        valid_parents = [(parent_id, count) for (parent_id, count) in parent_counter.items() if count >= match_threshold]
        if len(valid_parents) != 0:
            max_count = max(valid_parents, key=lambda x: x[1])[1]
            top_parent = sorted((parent_id for (parent_id, count) in valid_parents if count == max_count))[0]
            child_to_parents[child_id].extend([top_parent])
    return dict(child_to_parents)

def parse_cliques_from_parent_map(child_to_parents):
    G = nx.Graph()
    for (child, parent) in child_to_parents.items():
        assert len(parent) == 1
        G.add_edge(child, parent[0])
    return [sorted(list(c)) for c in nx.connected_components(G)]

def ensure_global_uniqueness(list_of_lists):
    flat = [item for sublist in list_of_lists for item in sublist]
    counter = Counter(flat)
    assert not any((count > 1 for count in counter.values())), 'Duplicate elements found across sublists'
