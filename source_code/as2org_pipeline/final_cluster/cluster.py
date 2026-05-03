import os
import json
import re
import shutil
from copy import deepcopy
import tldextract
from as2org_pipeline.final_cluster.alias_cluster import cluster_main_alias, cluster_secondary_alias
from as2org_pipeline.final_cluster.clique_cluster import cluster_parent_and_child

def normalize(s: str) -> str:
    s = s.lower()
    return re.sub('[,.<>:"/\\\\|?*]', '', s).strip()

def sanitize_for_path(name):
    return re.sub('[<>:"/\\\\|?*]', '_', name)

def final_cluster(base_dir):
    llm_output_dir = base_dir + 'llm/classification/output/'
    as_to_org_file_path = base_dir + 'output/as_to_org.json'
    org_info_path = base_dir + 'output/org.json'
    final_out_dir = base_dir + 'output/'
    generate_as_to_org_file(as_to_org_file_path, final_out_dir)
    org_dict = prepare_org_dict(final_out_dir, org_info_path, llm_output_dir, as_to_org_file_path)
    print(f'number of org initially: {len(org_dict)}')
    main_alias_clusters = cluster_main_alias(org_dict)
    main_alias_groups = parse_org_family_to_alias_group_based_on_main_key(main_alias_clusters)
    print(f'number of cluster after main key clustering: {len(main_alias_groups)}')
    with open(os.path.join(final_out_dir, 'debug_main_alias_groups.json'), 'w', encoding='utf-8') as outfile:
        json.dump(main_alias_groups, outfile, indent=4, ensure_ascii=False)
    cluster_large_alias_groups = cluster_secondary_alias(main_alias_groups)
    with open(os.path.join(final_out_dir, 'debug_secondary_alias_groups.json'), 'w', encoding='utf-8') as outfile:
        json.dump(cluster_large_alias_groups, outfile, indent=4, ensure_ascii=False)
    final_alias_groups = flat_large_alias_group(cluster_large_alias_groups)
    print(f'number of cluster after secondary key clustering: {len(final_alias_groups)}')
    with open(os.path.join(final_out_dir, 'debug_flat_alias_groups.json'), 'w', encoding='utf-8') as outfile:
        json.dump(final_alias_groups, outfile, indent=4, ensure_ascii=False)
    with open(os.path.join(final_out_dir, 'result_alias_group_to_org.json'), 'w', encoding='utf-8') as outfile:
        json.dump(clean_alias_group_for_result(deepcopy(final_alias_groups)), outfile, indent=4, ensure_ascii=False)
    clique_list = cluster_parent_and_child(final_alias_groups)
    print(f'number of cluster after parent-child clustering: {len(clique_list)}')
    clique_list.sort(key=lambda item: item['clique_alias_group_size'], reverse=True)
    with open(os.path.join(final_out_dir, 'debug_raw_cliques.json'), 'w', encoding='utf-8') as outfile:
        json.dump(clique_list, outfile, indent=4, ensure_ascii=False)
    cleaned_clique_list = clean_clique_attr(clique_list)
    with open(os.path.join(final_out_dir, 'result_cliques_list.json'), 'w', encoding='utf-8') as outfile:
        json.dump(cleaned_clique_list, outfile, indent=4, ensure_ascii=False)

def clean_clique_attr(clique_list):
    return clique_list
    for clique in clique_list:
        for alias_group in clique['clique_alias_group_list']:
            del alias_group['alias_attr_list']
            del alias_group['parents_attr_list']
            for org_object in alias_group['organization_list']:
                del org_object['alias_attr_list']
                del org_object['parents_attr_list']
                del org_object['main_alias_attr_list']
                del org_object['secondary_alias_attr_list']
    return clique_list

def flat_large_alias_group(cluster_large_alias_groups):
    final_alias_groups = []
    alias_group = 0
    for large_alias_group in cluster_large_alias_groups:
        alias_attr_list = []
        org_members = []
        for sub_alias_group in large_alias_group['sub_alias_groups']:
            org_members += sub_alias_group['organization_list']
            alias_attr_list += sub_alias_group['alias_group_final_alias_keyword_list']
        final_alias_groups.append({'alias_group_index': alias_group, 'alias_group_size': len(org_members), 'organization_list': org_members, 'alias_attr_list': list(set(alias_attr_list))})
        alias_group += 1
    return final_alias_groups

def clean_alias_group_for_result(final_alias_groups):
    for alias_group in final_alias_groups:
        del alias_group['alias_attr_list']
        for org in alias_group['organization_list']:
            del org['alias_attr_list']
            del org['parents_attr_list']
            del org['main_alias_attr_list']
            del org['secondary_alias_attr_list']
    return final_alias_groups

def parse_org_family_to_alias_group_based_on_main_key(main_alias_clusters):
    main_alias_group = []
    main_alias_id = 0
    for main_alias_cluster in main_alias_clusters:
        main_keyword_frequency = {}
        for org_json in main_alias_cluster:
            for attr in org_json['main_alias_attr_list']:
                main_keyword_frequency.setdefault(attr, 0)
                main_keyword_frequency[attr] += 1
        main_alias_group.append({'alias_group_id': main_alias_id, 'alias_group_size': len(main_alias_cluster), 'organization_list': main_alias_cluster, 'alias_group_main_alias_attr_list': list(main_keyword_frequency.keys())})
        main_alias_id += 1
    main_alias_group.sort(key=lambda item: item['alias_group_size'], reverse=True)
    return main_alias_group

def prepare_org_dict(final_output_dir, org_list_dir, llm_output_dir, as_to_org_file_path):
    org_dict = {}
    with open(org_list_dir, 'r', encoding='utf-8') as f:
        org_meta_json = json.load(f)
        org_id_to_org_name_dict = {}
        for org_meta in org_meta_json:
            for org_id in org_meta['org_id']:
                org_id_to_org_name_dict[org_id] = org_meta['org_name']
        org_name_to_as_list_dict = {}
        with open(as_to_org_file_path, 'r', encoding='utf-8') as f:
            as_to_org_json = json.load(f)
            for as_obj in as_to_org_json:
                org_name_to_as_list_dict.setdefault(org_id_to_org_name_dict[as_obj['org_id']], []).append(as_obj['asn'])
        for org_meta in org_meta_json:
            assert org_meta['org_name'] != '' and org_meta['org_name'] not in org_dict
            websites = org_meta['website']
            websites = [f'{tldextract.extract(url).domain}.{tldextract.extract(url).suffix}' for url in websites]
            org_dict[org_meta['org_name']] = {'org_name': org_meta['org_name'], 'org_id': org_meta['org_id'], 'websites': websites, 'aka': org_meta['aka'], 'asn': org_name_to_as_list_dict[org_meta['org_name']]}
    for relative_org_dir in os.listdir(llm_output_dir):
        abs_org_dir = os.path.join(llm_output_dir, relative_org_dir)
        with open(os.path.join(abs_org_dir, 'ori_org_name.txt'), 'r') as file:
            org_name = file.readline().strip()
        with open(os.path.join(abs_org_dir, 'result.json'), 'r') as json_file:
            new_dict = json.load(json_file)
            if org_name in org_dict:
                org_dict[org_name] = {'org_name': org_dict[org_name]['org_name'], 'org_id': org_dict[org_name]['org_id'], 'asn': org_dict[org_name]['asn'], 'websites': org_dict[org_name]['websites'], 'aka': org_dict[org_name]['aka'], 'alias_attr_list': [normalize(org_name) for org_name in new_dict['alias_list']], 'parents_attr_list': [normalize(org_name) for org_name in new_dict['parent_company_list']]}
    for (org_name, org_info) in org_dict.items():
        if 'alias_attr_list' not in org_info:
            org_dict[org_name] = {'org_name': org_dict[org_name]['org_name'], 'org_id': org_dict[org_name]['org_id'], 'asn': org_dict[org_name]['asn'], 'websites': org_dict[org_name]['websites'], 'aka': org_dict[org_name]['aka'], 'alias_attr_list': [], 'parents_attr_list': []}
    for (org_name, org_info) in org_dict.items():
        org_dict[org_name]['alias_attr_list'].append(org_name.lower())
        if 'chinanet' in org_name.lower():
            org_dict[org_name]['alias_attr_list'] += ['chinanet coop', 'chinanet coop.', 'chinanet coop,']
        if 'google' in org_name.lower():
            org_dict[org_name]['alias_attr_list'] += ['google coop', 'google coop.', 'google coop,']
        if 'at&t' in org_name.lower():
            org_dict[org_name]['alias_attr_list'] += ['at&t coop', 'at&t coop.', 'at&t coop,', 'at & t corp']
        if 'internet systems consortium' in org_name.lower():
            org_dict[org_name]['alias_attr_list'] += ['internet systems consortium', 'internet systems consortium.', 'internet systems consortium,']
    with open(os.path.join(final_output_dir, 'debug_org_meta_with_attr.json'), 'w', encoding='utf-8') as outfile:
        json.dump(org_dict, outfile, indent=4, ensure_ascii=False)
    return org_dict

def generate_as_to_org_file(as_to_org_file_path, final_out_dir):
    shutil.copy(as_to_org_file_path, os.path.join(final_out_dir, 'result_as_to_org.json'))
