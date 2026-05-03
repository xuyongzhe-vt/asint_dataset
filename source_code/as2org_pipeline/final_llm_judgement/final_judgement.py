import json
import asyncio
import logging
import time
import traceback
import re
import itertools
import networkx as nx
from tqdm import tqdm
from as2org_pipeline.final_llm_judgement.blacklist import black_list, exact_match_list, user_feedback_blacklist
from collections import defaultdict
import os
from pathlib import Path
from as2org_pipeline.final_llm_judgement.llm.llm import build_graph
from as2org_pipeline.final_llm_judgement.judge_parent import judge_parent_child
from as2org_pipeline.final_llm_judgement.llm.prompt import alias_prompt
from as2org_pipeline.multi_process_support.cpu_worker import WorkerPool
retry_limit = 1
batch_size = 20
worker_num = 10

def final_judge(ori_base_dir):
    alias_judgement_output_dir = ori_base_dir + 'llm/re-evaluation/alias_judge/'
    parent_judgement_output_dir = ori_base_dir + 'llm/re-evaluation/parent_judge/'
    with open(ori_base_dir + 'output/result_cliques_list.json', 'r', encoding='utf-8') as f:
        result_cliques = json.load(f)
    parsed_dict = {}
    for file in Path(alias_judgement_output_dir).glob('*.json'):
        try:
            with file.open('r', encoding='utf-8') as f:
                data = json.load(f)
                a = data.get('org_a_name')
                b = data.get('org_b_name')
                if a and b:
                    parsed_dict[a, b] = True
                    parsed_dict[b, a] = True
        except Exception as e:
            print(f'Failed to read {file}: {e}')
    alias_pair_to_judge = []
    already_processed = 0
    for clique in result_cliques:
        for alias_group in clique['clique_alias_group_list']:
            if alias_group['alias_group_size'] != 1:
                org_list = alias_group['organization_list']
                for (org1, org2) in itertools.combinations(org_list, 2):
                    org_name_1 = org1['org_name']
                    org_name_2 = org2['org_name']
                    if (org_name_1, org_name_2) in parsed_dict:
                        already_processed += 1
                        continue
                    alias_pair_to_judge.append([org_name_1, org_name_2])
    logging.warning(f'Num of already processed alias pairs: {already_processed}')
    logging.warning(f'Num of alias pairs to parse: {len(alias_pair_to_judge)}')
    check_alias(alias_pair_to_judge, alias_judgement_output_dir)
    judge_parent_child(ori_base_dir, parent_judgement_output_dir)

def final_cluster(ori_base_dir):
    alias_judgement_output_dir = ori_base_dir + 'llm/re-evaluation/alias_judge/'
    parent_judgement_output_dir = ori_base_dir + 'llm/re-evaluation/parent_judge/'
    final_alias_clusters = re_cluster_alias(ori_base_dir, alias_judgement_output_dir)
    re_cluster_parent(ori_base_dir, final_alias_clusters, parent_judgement_output_dir)

def in_blacklist(a, b):
    for black_list_keywords in black_list:
        if black_list_keywords in a.lower() or black_list_keywords in b.lower():
            return True
    for exact_match in exact_match_list:
        if a.lower() == exact_match or b.lower() == exact_match:
            return True
    return False

def re_cluster_parent(base_dir, final_alias_clusters, parent_judgement_output_dir):
    debug_bundle = []
    org_name_to_obj_dict = {}
    with open(base_dir + 'output/result_cliques_list.json', 'r', encoding='utf-8') as f:
        result_cliques = json.load(f)
        org_list = []
        for clique in result_cliques:
            for alias_group in clique['clique_alias_group_list']:
                org_list += alias_group['organization_list']
                for org in alias_group['organization_list']:
                    assert org['org_name'] not in org_name_to_obj_dict
                    cleaned_org = {'org_name': org['org_name']}
                    org_name_to_obj_dict[org['org_name']] = cleaned_org
    parent_child_list = []
    outdated_links_num = 0
    for file in Path(parent_judgement_output_dir).glob('*.json'):
        with file.open('r', encoding='utf-8') as f:
            data = json.load(f)
            a = data.get('org_a_name')
            b = data.get('org_b_name')
            if in_blacklist(a, b):
                continue
            if a not in org_name_to_obj_dict or b not in org_name_to_obj_dict:
                outdated_links_num += 1
                continue
            if a in user_feedback_blacklist or b in user_feedback_blacklist:
                A_is_parent_of_B_Score = 0
                B_is_parent_of_A_Score = 0
                No_Relationship_Score = 1
            else:
                A_is_parent_of_B_Score = float(data.get('A_is_parent_of_B_Score'))
                B_is_parent_of_A_Score = float(data.get('B_is_parent_of_A_Score'))
                No_Relationship_Score = float(data.get('No_Relationship_Score'))
            if A_is_parent_of_B_Score is not None and B_is_parent_of_A_Score is not None and (No_Relationship_Score is not None):
                max_score = max(A_is_parent_of_B_Score, B_is_parent_of_A_Score, No_Relationship_Score)
                if max_score == A_is_parent_of_B_Score:
                    parent_child_list.append((a, b, A_is_parent_of_B_Score))
                elif max_score == B_is_parent_of_A_Score:
                    parent_child_list.append((b, a, B_is_parent_of_A_Score))
            debug_bundle.append({'org_a_name': a, 'org_b_name': b, 'A_is_parent_of_B_Score': A_is_parent_of_B_Score, 'B_is_parent_of_A_Score': B_is_parent_of_A_Score, 'No_Relationship_Score': No_Relationship_Score, 'path': str(file)})
    logging.warning(f'invalid parent links {outdated_links_num}')
    print(f'num of parent links before filtering: {len(parent_child_list)}')
    best = {}
    for (p, c, s) in sorted(parent_child_list, key=lambda x: (-x[2], x[0])):
        if c not in best:
            best[c] = (p, s)
    filtered_parent_child_list = [(p, c, s) for (c, (p, s)) in best.items()]
    print(f'num of parent links after filtering: {len(filtered_parent_child_list)}')
    clique_list = group_alias_group_by_parent(filtered_parent_child_list, final_alias_clusters)
    print(len(clique_list))
    final_org_families = reconstruct_org_families(clique_list, final_alias_clusters)
    with open(base_dir + 'output/final_org_families.json', 'w', encoding='utf-8') as outfile:
        json.dump(final_org_families, outfile, indent=4, ensure_ascii=False)

def reconstruct_org_families(clique_list, final_alias_clusters):
    org_families = []
    clique_id = 0
    group_id_to_group = {}
    for group in final_alias_clusters:
        idx = group['index']
        assert idx not in group_id_to_group
        group_id_to_group[idx] = group
    for clique in clique_list:
        clique_alias_group_list = []
        for group in clique['clique_alias_group_list']:
            idx = group['alias_group_id']
            if 'parent_alias_group_id' in group:
                group_id_to_group[idx]['parent_alias_group_id'] = group['parent_alias_group_id']
            clique_alias_group_list.append(group_id_to_group[idx])
        org_families.append({'clique_id': clique_id, 'clique_alias_group_list': clique_alias_group_list, 'clique_alias_group_size': len(clique_alias_group_list)})
        clique_id += 1
    org_families.sort(key=lambda x: x['clique_alias_group_size'], reverse=True)
    return org_families

def group_alias_group_by_parent(parent_child_list, final_alias_clusters):
    org_to_group = {}
    group_to_orgs = {}
    for group in final_alias_clusters:
        idx = group['index']
        org_names = [org['org_name'] for org in group['org_list']]
        group_to_orgs[idx] = set(org_names)
        for org_name in org_names:
            org_to_group[org_name] = idx
    org_parent_map = defaultdict(set)
    for (parent_org, child_org, _) in parent_child_list:
        org_parent_map[child_org].add(parent_org)
    print('⏳ Finding candidate alias group pairs...')
    candidate_group_edges = set()
    for (child_org, parent_orgs) in org_parent_map.items():
        child_group = org_to_group.get(child_org)
        if child_group is None:
            continue
        for parent_org in parent_orgs:
            parent_group = org_to_group.get(parent_org)
            if parent_group is not None and parent_group != child_group:
                candidate_group_edges.add((parent_group, child_group))
    print(f'🔎 Candidate group pairs to check: {len(candidate_group_edges)}')
    alias_group_edges = set()
    for (parent_group, child_group) in tqdm(candidate_group_edges, desc='Validating parent-child group links'):
        parent_orgs = group_to_orgs[parent_group]
        child_orgs = group_to_orgs[child_group]
        required_ratio = 0.5
        valid = sum((len(org_parent_map.get(c_org, set()) & parent_orgs) / len(parent_orgs) >= required_ratio for c_org in child_orgs)) / len(child_orgs) >= required_ratio
        if valid:
            alias_group_edges.add((parent_group, child_group))
    print(f'✅ Valid alias group edges found: {len(alias_group_edges)}')
    G = nx.DiGraph()
    G.add_edges_from(alias_group_edges)
    all_group_indices = set(group_to_orgs.keys())
    used_in_graph = set(G.nodes)
    used_in_cliques = set()
    clique_list = []
    for component in tqdm(nx.weakly_connected_components(G), desc='Building graph-based cliques'):
        subgraph = G.subgraph(component)
        clique_alias_group_list = []
        for node in subgraph.nodes:
            used_in_cliques.add(node)
            alias_group = {'alias_group_id': node, 'organization_list': list(group_to_orgs[node]), 'alias_group_size': len(group_to_orgs[node])}
            parents = list(G.predecessors(node))
            if parents:
                alias_group['parent_alias_group_id'] = parents
            clique_alias_group_list.append(alias_group)
        clique_list.append({'clique_alias_group_list': clique_alias_group_list})
    remaining_groups = all_group_indices - used_in_cliques
    print(f'➕ Singleton groups to add as individual cliques: {len(remaining_groups)}')
    for idx in remaining_groups:
        clique_list.append({'clique_alias_group_list': [{'alias_group_id': idx, 'organization_list': list(group_to_orgs[idx]), 'alias_group_size': len(group_to_orgs[idx])}]})
    print(f'🔁 Total cliques formed (including singletons): {len(clique_list)}')
    return clique_list

def re_cluster_alias(base_dir, alias_judgement_output_dir):
    org_name_to_obj_dict = {}
    with open(base_dir + 'output/result_cliques_list.json', 'r', encoding='utf-8') as f:
        result_cliques = json.load(f)
        org_list = []
        for clique in result_cliques:
            for alias_group in clique['clique_alias_group_list']:
                org_list += alias_group['organization_list']
                for org in alias_group['organization_list']:
                    assert org['org_name'] not in org_name_to_obj_dict
                    cleaned_org = {'org_name': org['org_name']}
                    org_name_to_obj_dict[org['org_name']] = cleaned_org
    debug_bundle = []
    alias_judge_list = []
    outdated_links_num = 0
    for file in Path(alias_judgement_output_dir).glob('*.json'):
        with file.open('r', encoding='utf-8') as f:
            data = json.load(f)
            a = data.get('org_a_name')
            b = data.get('org_b_name')
            if in_blacklist(a, b):
                continue
            if a not in org_name_to_obj_dict or b not in org_name_to_obj_dict:
                outdated_links_num += 1
                continue
            if a in user_feedback_blacklist or b in user_feedback_blacklist:
                score = 0
            else:
                score = data.get('score')
            debug_bundle.append({'org_a_name': a, 'org_b_name': b, 'score': score, 'path': str(file)})
            try:
                score = float(score)
            except Exception:
                continue
            (a, b) = tuple(sorted((a, b)))
            alias_judge_list.append((a, b, score))
    with open(base_dir + 'output/alias_attr.json', 'w', encoding='utf-8') as outfile:
        json.dump(debug_bundle, outfile, indent=4, ensure_ascii=False)
    logging.warning(f'outdated alias pairs {outdated_links_num}')
    clustered_org_names = cluster_alias(alias_judge_list)
    clustered_names_set = set()
    for cluster in clustered_org_names:
        clustered_names_set.update(cluster)
    final_alias_clusters = []
    index = 0
    for cluster in clustered_org_names:
        new_alias = {'index': index, 'alias_size': len(cluster), 'org_list': [org_name_to_obj_dict[name] for name in cluster]}
        final_alias_clusters.append(new_alias)
        index += 1
    for org_name in org_name_to_obj_dict:
        if org_name not in clustered_names_set:
            new_alias = {'index': index, 'alias_size': 1, 'org_list': [org_name_to_obj_dict[org_name]]}
            final_alias_clusters.append(new_alias)
            index += 1
    final_alias_clusters.sort(key=lambda x: x['alias_size'], reverse=True)
    with open(base_dir + 'output/llm_judgement_alias_clustering.json', 'w', encoding='utf-8') as outfile:
        json.dump(final_alias_clusters, outfile, indent=4, ensure_ascii=False)
    return final_alias_clusters

def cluster_alias(alias_judge_list, threshold=0.6):
    G = nx.Graph()
    for (a, b, score) in alias_judge_list:
        if score > threshold:
            G.add_edge(a, b, weight=score)
    G = G.subgraph(sorted(G.nodes())).copy()
    all_cliques = list(nx.find_cliques(G))
    all_cliques = [sorted(clique) for clique in all_cliques]
    all_cliques = sorted(all_cliques, key=lambda c: (-len(c), c))
    assigned = set()
    cliques_named = []
    for clique in all_cliques:
        if all((node not in assigned for node in clique)):
            cliques_named.append(clique)
            assigned.update(clique)
    cliques_named = [c for c in cliques_named if len(c) > 1]

    def compute_loss(eva_clusters, G):
        node_to_cluster = {}
        for (idx, cluster) in enumerate(eva_clusters):
            for node in cluster:
                node_to_cluster[node] = idx
        L_intra = 0.0
        L_inter = 0.0
        for (u, v, data) in G.edges(data=True):
            same_cluster = node_to_cluster.get(u) == node_to_cluster.get(v)
            score = data['weight']
            if same_cluster:
                L_intra += 1 - score
            else:
                L_inter += score
        return (L_intra, L_inter, L_intra + L_inter)
    (L_intra, L_inter, total) = compute_loss(cliques_named, G)
    print(f'Intra loss: {L_intra:.2f}, Inter loss: {L_inter:.2f}, Total: {total:.2f}')
    print(f'✅ Found {len(cliques_named)} disjoint alias groups (all-pairs score > {threshold})')
    return cliques_named

def check_alias(alias_list, output_dir):
    graph = build_graph(alias_prompt)
    for i in range(0, len(alias_list), batch_size):
        t = time.time()
        before_count = len(os.listdir(output_dir))
        worker_pool = WorkerPool(worker_num, alias_list[i:i + batch_size], judge_per_process, [graph, output_dir])
        worker_pool.start_work()
        after_count = len(os.listdir(output_dir))
        rate = (after_count - before_count) / batch_size
        elapsed = time.time() - t
        remaining_batches = (len(alias_list) - (i + batch_size)) / batch_size
        est_remaining_time = remaining_batches * elapsed
        logging.warning(f'progress {i + batch_size}/{len(alias_list)}, \nbefore: {before_count}, after: {after_count}, successful rate {rate:.2f}, estimated time left: {est_remaining_time:.1f}s')

def judge_per_process(alias_list, extra_params):
    graph = extra_params[0]
    output_dir = extra_params[1]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_query_one_batch(alias_list, graph, output_dir))

async def async_query_one_batch(alias_list, graph, output_dir):
    tasks = []
    for (org_a, org_b) in alias_list:
        tasks.append(async_query_one_single_pair(org_a, org_b, graph, output_dir))
    await asyncio.gather(*tasks)

def sanitize_filename(name: str) -> str:
    return re.sub('[<>:"/\\\\|?*]', '_', name)

async def async_query_one_single_pair(org_a, org_b, graph, output_dir):
    tried = 0
    while tried <= retry_limit:
        tried += 1
        try:
            result = await graph.ainvoke({'org_a_name': org_a, 'org_b_name': org_b})
            (score, explanation, raw_prompt) = parse_result(result)
            result_to_store = {'org_a_name': org_a, 'org_b_name': org_b, 'score': score, 'explanation': explanation, 'raw_prompt': raw_prompt}
            org_a_safe = sanitize_filename(org_a)
            org_b_safe = sanitize_filename(org_b)
            filename = f'{org_a_safe}__{org_b_safe}.json'
            output_path = Path(output_dir + filename)
            with output_path.open('w', encoding='utf-8') as f:
                json.dump(result_to_store, f, indent=2, ensure_ascii=False)
            return
        except asyncio.TimeoutError:
            exception_message = f'LLM request timeout: {org_a} - {org_b}'
            logging.warning(exception_message)
        except Exception as e:
            error_message = traceback.format_exc()
            exception_message = f'async_query_one_single_pair error for {org_a} - {org_b} \n: {error_message}: {e}'
            logging.warning(exception_message)

def extract_first_json_object(text):
    stack = []
    start = None
    for (i, c) in enumerate(text):
        if c == '{':
            if not stack:
                start = i
            stack.append('{')
        elif c == '}':
            if stack:
                stack.pop()
                if not stack and start is not None:
                    candidate = text[start:i + 1]
                    obj = json.loads(candidate)
                    if 'Confidence Score' not in obj or 'Explanation' not in obj:
                        raise Exception(f'Json attr missing {text}')
                    return obj
    raise Exception(f'No valid JSON content: {text}')

def parse_result(result):
    result = extract_first_json_object(result['answer'])
    return (result['Confidence Score'], result['Explanation'], result)
