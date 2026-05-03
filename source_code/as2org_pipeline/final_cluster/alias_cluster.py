from as2org_pipeline.final_cluster.fuzzy_dfs import dsf_search
from as2org_pipeline.final_cluster.attr_cleaner import graph_based_similarity_filtering
attr_filter_list = ['Telemedia', 'sprint', 'cloud', 'network', 'tech', 'telemedia', 'powernet', 'unicom', 'link net', 'telkom', 'telin', 'datacom', 'ultranet', 'intercom', 'informatica', 'cable', 'telecom', 'fiber', 'meganet', 'citizens', 'citizens bank', 'delta', 'gmbh', 'cnet', 'pty ltd', 'inc', 'coop', 'limited', 'square', 'department of information and communication', 'telenet', 'department of information and communications', 'ministry of education', 'watchtower bible and tract society', 'signal', 'ministry of finance', 'unity', 'nova', 'bull', 'metronet', 'quest', 'start', 'syntax', 'teleperformance', 'freedom', 'dialog', 'interlink', 'spark', 'optimum', 'globe', 'apnic', 'spark', 'cablevision', 'ministry of communication', 'internet solutions', 'switch', 'national information technology center', 'planet', 'opera', 'ministry of health', 'next', 'sas institute', 'ministry of foreign affairs', 'supernet', 'netcom', 'extreme', 'link', 'epic', 'deutsche bundespost', 'business solutions', 'ministry of interior', 'interior ministry', 'microsoft network', 'the microsoft network', 'horizon tv', 'ltda me', 'cooperativa de obras y servicios publicos', 'cooperativa de obras y servicios publicos de canals limitada']
org_name_filter_list = ['university', 'college', 'city', 'wireless (us) inc']
import re

def cluster_main_alias(org_dict):
    for (org_name, org_json) in org_dict.items():
        org_json['alias_attr_list'] = list(set([name.lower() for name in org_json['alias_attr_list']]))
        (main_attr, secondary_attr) = separate_main_attr_and_sibling_attr(org_name, org_json)
        if len(org_json['websites']) != 0:
            main_attr += org_json['websites']
        if len(org_json['aka']) != 0:
            main_attr += org_json['aka']
        main_attr.append(org_name)
        org_json['main_alias_attr_list'] = list(set(main_attr))
        org_json['secondary_alias_attr_list'] = list(set(secondary_attr))
    result_families = dsf_search(org_dict, ['main_alias_attr_list'])
    return result_families

def cluster_secondary_alias(main_alias_groups, freq_threshold=0.75):
    alias_group_dict = {}
    for alias_group in main_alias_groups:
        org_num = len(alias_group['organization_list'])
        keyword_dict = {}
        for org_json in alias_group['organization_list']:
            org_name = org_json['org_name']
            for keyword in org_json['secondary_alias_attr_list']:
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
                final_attr.append(attr_cluster)
        if final_attr:
            final_attr = max(final_attr, key=lambda c: (len(c), sorted(c)))
            alias_group['alias_group_final_alias_keyword_list'] = final_attr
        else:
            alias_group['alias_group_final_alias_keyword_list'] = []
        alias_group['alias_group_final_alias_keyword_list'] += alias_group['alias_group_main_alias_attr_list']
        alias_group_dict[str(alias_group['alias_group_id'])] = alias_group
    result_families = dsf_search(alias_group_dict, ['alias_group_final_alias_keyword_list'])
    result = []
    large_alias_index = 0
    for family in result_families:
        result.append({'large_alias_group_id': large_alias_index, 'sub_group_size': len(family), 'sub_alias_groups': family})
        large_alias_index += 1
    return result

def separate_main_attr_and_sibling_attr(org_name: str, org_json, similarity_threshold=0.5, min_cluster_size=2, min_keywords_length=4):
    for org_keywords_to_eliminate in org_name_filter_list:
        if org_keywords_to_eliminate in org_name.lower():
            return ([], [])
    attr_list_before_filtering = org_json['alias_attr_list']
    filtered_attr_list = [attr for attr in attr_list_before_filtering if len(attr.strip()) >= min_keywords_length]
    filtered_attr_list = [attr for attr in filtered_attr_list if len(attr.strip().split(' ')) >= 2]
    filtered_attr_list = [attr for attr in filtered_attr_list if attr not in attr_filter_list]
    if len(org_name.lower()) >= min_keywords_length and org_name.lower() not in attr_filter_list:
        filtered_attr_list += [org_name.lower()]
    filtered_clusters = graph_based_similarity_filtering(filtered_attr_list, similarity_threshold)
    filtered_clusters = [c for c in filtered_clusters if len(c) >= min_cluster_size]
    if len(filtered_clusters) == 0:
        return ([], [])
    max_len = max((len(c) for c in filtered_clusters))
    max_clusters = [c for c in filtered_clusters if len(c) == max_len]
    preferred_cluster = None
    for cluster in max_clusters:
        if org_name.lower() in cluster:
            preferred_cluster = cluster
            break
    if preferred_cluster is None:
        preferred_cluster = min(max_clusters, key=lambda c: sorted(c))
    largest_cluster = preferred_cluster
    rest = list(set([item for lst in filtered_clusters if lst is not largest_cluster for item in lst]))
    return (largest_cluster, rest)
