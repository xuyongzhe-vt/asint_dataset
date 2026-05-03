import json
from as2org_pipeline.as2org_mapping.peering_db_parser.parser import parse_peering_db
import tldextract
import csv
import uuid
import re
import shutil
from collections import defaultdict
from as2org_pipeline.as2org_mapping.peering_db_parser.peering_net import PeeringNet
from as2org_pipeline.as2org_mapping.peering_db_parser.peering_org import PeeringOrg

def normalize_org_name(name: str) -> str:
    return name

def normalize_org_name_merger(name: str) -> str:
    name = name.strip()
    name = re.sub('[,./]', ' ', name)
    name = re.sub('\\s+', ' ', name)
    return name.lower().strip()

def post_process(base_dir):
    with open(base_dir + 'output/final_org_families.json', 'r', encoding='utf-8') as f:
        result_cliques = json.load(f)
    result_cliques = merge_org_with_similar_name(result_cliques)
    with open(base_dir + 'final_output/final_org_families.json', 'w', encoding='utf-8') as outfile:
        json.dump(result_cliques, outfile, indent=4, ensure_ascii=False)
    shutil.copy(base_dir + 'output/as_to_org.json', base_dir + 'final_output/as_to_org.json')
    shutil.copy(base_dir + 'output/org.json', base_dir + 'final_output/org.json')
    print(f'Post-precessing: init cliques_num: {len(result_cliques)}')
    final_check_and_generate_output(base_dir, result_cliques)

def merge_org_with_similar_name(result_cliques):
    merged_org_name = set()
    name_to_family = {}
    merge_pairs = []
    for (i, fam) in enumerate(result_cliques):
        if len(fam['clique_alias_group_list']) != 1:
            continue
        names = {normalize_org_name_merger(org['org_name']) for org in fam['clique_alias_group_list'][0]['org_list']}
        for n in names:
            if n in name_to_family:
                j = name_to_family[n]
                merge_pairs.append((result_cliques[j], fam))
            else:
                name_to_family[n] = i
    print(f'num of pairs {len(merge_pairs)}')

    def get_normalized_names(fam):
        assert len(fam['clique_alias_group_list']) == 1, 'Family must have exactly 1 alias group'
        names = set()
        for org in fam['clique_alias_group_list'][0]['org_list']:
            names.add(normalize_org_name_merger(org['org_name']))
        return names
    for (fam_1, fam_2) in merge_pairs:
        assert len(fam_1['clique_alias_group_list']) == 1 and len(fam_2['clique_alias_group_list']) == 1, 'Both families must have exactly one alias group'
        n1 = get_normalized_names(fam_1)
        n2 = get_normalized_names(fam_2)
        inter = n1 & n2
        assert inter, f'No shared normalized names between families. fam_1={n1} fam_2={n2}'
    for (fam_1, fam_2) in merge_pairs:
        fam_1['to_remove'] = True
        fam_1_size = len(fam_1['clique_alias_group_list'][0]['org_list'])
        fam_2_size = len(fam_2['clique_alias_group_list'][0]['org_list'])
        fam_2['clique_alias_group_list'][0]['org_list'] += fam_1['clique_alias_group_list'][0]['org_list']
        fam_2['clique_alias_group_list'][0]['alias_size'] = len(fam_2['clique_alias_group_list'][0]['org_list'])
        assert fam_1_size + fam_2_size == fam_2['clique_alias_group_list'][0]['alias_size']
    print(f'before: {len(result_cliques)}')
    result_cliques = [fam for fam in result_cliques if not fam.get('to_remove')]
    print(f'after: {len(result_cliques)}')
    return result_cliques

def final_check_and_generate_output(base_dir, org_families):
    with open(base_dir + 'final_output/as_to_org.json', 'r', encoding='utf-8') as f:
        as_to_org_pair_list = json.load(f)
    org_name_to_id_dict = {}
    with open(base_dir + 'final_output/org.json', 'r', encoding='utf-8') as f:
        org_list = json.load(f)
        for org in org_list:
            for org_id in org['org_id']:
                org_name_to_id_dict.setdefault(org['org_name'], []).append(org_id)
    as_to_org_id_dict = {}
    orgid_to_aliasid = {}
    orgid_to_orgname = {}
    for as_to_org in as_to_org_pair_list:
        asn = as_to_org['asn']
        rir = as_to_org['rir']
        if len(as_to_org['as_name']) == 0:
            as_name = ''
        else:
            as_name = as_to_org['as_name'][0]
        as_to_org_id_dict.setdefault((asn, rir, as_name), []).append(as_to_org['org_id'])
    for org_family in org_families:
        for alias_group in org_family['clique_alias_group_list']:
            alias_id = alias_group['index']
            for org in alias_group['org_list']:
                org_ids = org_name_to_id_dict[org['org_name']]
                for org_id in org_ids:
                    orgid_to_aliasid[org_id] = alias_id
                    orgid_to_orgname[org_id] = org['org_name']
    convert_to_csv_file(base_dir, as_to_org_id_dict, orgid_to_aliasid, orgid_to_orgname, org_families)
    check_csv_file(base_dir)
    generate_saint_org_families(base_dir)
    final_check(base_dir)

def final_check(base_dir):
    errors = []
    org_json = base_dir + 'final_output/org.json'
    as_to_org_json = base_dir + 'final_output/as_to_org.json'
    final_org_families_json = base_dir + 'final_output/final_org_families.json'
    saint_json = base_dir + 'final_output/saint.org_families.json'
    with open(org_json, encoding='utf-8') as f:
        org_list = json.load(f)
    with open(as_to_org_json, encoding='utf-8') as f:
        as_to_org_list = json.load(f)
    with open(final_org_families_json, encoding='utf-8') as f:
        families = json.load(f)
    with open(saint_json, encoding='utf-8') as f:
        saint = json.load(f)
    org_name_set = {normalize_org_name(o['org_name']) for o in org_list}
    as_to_orgid = {a['asn']: a['org_id'] for a in as_to_org_list}
    orgid_to_name = {}
    for o in org_list:
        for oid in o['org_id']:
            orgid_to_name[oid] = o['org_name']
    alias_to_family = {}
    for fam in families:
        for group in fam['clique_alias_group_list']:
            alias_to_family[group['index']] = fam['clique_id']
    for fam in families:
        for group in fam['clique_alias_group_list']:
            for org in group['org_list']:
                if normalize_org_name(org['org_name']) not in org_name_set:
                    errors.append(f"Org {org['org_name']} in final_org_families not in org.json")
    for entry in saint:
        for asn_entry in entry['asn_entries']:
            asn = str(asn_entry['asn'])
            if asn not in as_to_orgid:
                errors.append(f'ASN {asn} in saint missing from as_to_org.json')
            else:
                expected_org_name = orgid_to_name.get(as_to_orgid[asn])
                if normalize_org_name(expected_org_name) != normalize_org_name(asn_entry['org_name']):
                    errors.append(f"ASN {asn} maps to {expected_org_name}, but saint has {asn_entry['org_name']}")
    for entry in saint:
        alias_id = entry['alias_id']
        fam_id = entry['org_family_id']
        if alias_id not in alias_to_family:
            errors.append(f'Alias {alias_id} missing in final_org_families.json')
        elif alias_to_family[alias_id] != fam_id:
            errors.append(f'Alias {alias_id} family mismatch: saint={fam_id}, final={alias_to_family[alias_id]}')
    saint_aliases = {e['alias_id']: e for e in saint}
    for entry in saint:
        for child in entry['children']:
            if entry['alias_id'] not in saint_aliases.get(child, {}).get('parent', []):
                errors.append(f"Child {child} missing parent link back to {entry['alias_id']}")
        for parent in entry['parent']:
            if entry['alias_id'] not in saint_aliases.get(parent, {}).get('children', []):
                errors.append(f"Parent {parent} missing child link back to {entry['alias_id']}")
    all_saint_orgs = {normalize_org_name(asn['org_name']) for e in saint for asn in e['asn_entries']}
    missing_orgs = org_name_set - all_saint_orgs
    if missing_orgs:
        errors.append(f'Missing orgs in saint: {missing_orgs}')
    all_saint_asns = {str(asn['asn']) for e in saint for asn in e['asn_entries']}
    missing_asns = set(as_to_orgid.keys()) - all_saint_asns
    if missing_asns:
        errors.append(f'Missing ASNs in saint: {missing_asns}')
    all_saint_aliases = {e['alias_id'] for e in saint}
    missing_aliases = set(alias_to_family.keys()) - all_saint_aliases
    if missing_aliases:
        errors.append(f'Missing alias_ids in saint: {missing_aliases}')
    if errors:
        print('❌ Validation failed: ', len(errors))
        for e in errors:
            print('  -', e)
    else:
        print('✅ saint.org_families.json passed all checks!')
    with open(base_dir + 'final_output/saint.org_families.json', encoding='utf-8') as f:
        saint = json.load(f)
    unique_families = {entry['org_family_id'] for entry in saint}
    print(f'Total org families: {len(unique_families)}')

def generate_saint_org_families(base_dir):
    AS_TABLE_path = base_dir + 'final_output/as_table.csv'
    ORG_ALIAS_TABLE_path = base_dir + 'final_output/org_alias_table.csv'
    ALIAS_REL_TABLE_path = base_dir + 'final_output/alias_relationships.csv'
    OUTPUT_path = base_dir + 'final_output/saint.org_families.json'
    alias_to_asnentries = {}
    with open(AS_TABLE_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {'asn': int(row['asn']), 'as_name': row['as_name'], 'org_name': normalize_org_name(row['org_name']), 'rir': row['rir']}
            alias_to_asnentries.setdefault(row['alias_id'], []).append(entry)
    alias_to_family = {}
    with open(ORG_ALIAS_TABLE_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias_to_family[row['alias_id']] = int(row['org_family_id'])
    child_to_parents = {}
    parent_to_children = {}
    with open(ALIAS_REL_TABLE_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            child = row['child_alias_id']
            parent = row['parent_alias_id']
            child_to_parents.setdefault(child, []).append(int(parent))
            parent_to_children.setdefault(parent, []).append(int(child))
    results = []
    alias_ids_from_family = set(alias_to_family.keys())
    alias_ids_from_asn = set(alias_to_asnentries.keys())
    missing_in_family = alias_ids_from_asn - alias_ids_from_family
    assert not missing_in_family, f'Alias IDs with ASNs but missing from family table: {missing_in_family}'
    missing_in_asn = alias_ids_from_family - alias_ids_from_asn
    all_alias_ids = alias_ids_from_family
    seen_ids = set()
    for alias_id in all_alias_ids:
        oid = uuid.uuid4().hex[:24]
        while oid in seen_ids:
            oid = uuid.uuid4().hex[:24]
        seen_ids.add(oid)
        alias_id_int = int(alias_id)
        obj = {'_id': {'$oid': oid}, 'alias_id': alias_id_int, 'asn_entries': alias_to_asnentries[alias_id], 'children': parent_to_children.get(alias_id, []), 'parent': child_to_parents.get(alias_id, []), 'org_family_id': alias_to_family[alias_id]}
        results.append(obj)
    with open(OUTPUT_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f'✅ Wrote {len(results)} alias groups to {OUTPUT_path}')

def check_csv_file(base_dir):
    ORG_JSON_path = base_dir + 'final_output/org.json'
    orgid_to_orgname = {}
    with open(ORG_JSON_path, 'r', encoding='utf-8') as f:
        for org in json.load(f):
            for org_id in org['org_id']:
                orgid_to_orgname[org_id] = org['org_name']
    AS_TABLE_path = base_dir + 'final_output/as_table.csv'
    ORG_ALIAS_TABLE_path = base_dir + 'final_output/org_alias_table.csv'
    ALIAS_REL_TABLE_path = base_dir + 'final_output/alias_relationships.csv'
    as_table = []
    alias_ids_in_as = set()
    org_names_in_as = set()
    with open(AS_TABLE_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            as_table.append(row)
            alias_ids_in_as.add(row['alias_id'])
            org_names_in_as.add(row['org_name'])
    alias_to_family = {}
    families = set()
    with open(ORG_ALIAS_TABLE_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias_to_family[row['alias_id']] = row['org_family_id']
            families.add(row['org_family_id'])
    alias_rels = []
    with open(ALIAS_REL_TABLE_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias_rels.append((row['child_alias_id'], row['parent_alias_id']))
    errors = []
    for row in as_table:
        alias_id = row['alias_id']
        if alias_id not in alias_to_family:
            errors.append(f"ASN {row['asn']} points to alias_id {alias_id} not in org_alias_table")
    unmatched_orgs = set(orgid_to_orgname.values()) - org_names_in_as
    for org in unmatched_orgs:
        errors.append(f"Org '{org}' missing from AS table")
    for (child, parent) in alias_rels:
        if child not in alias_to_family:
            errors.append(f'Child alias_id {child} in relationships not in org_alias_table')
        if parent not in alias_to_family:
            errors.append(f'Parent alias_id {parent} in relationships not in org_alias_table')
    graph = {}
    for (child, parent) in alias_rels:
        graph.setdefault(parent, []).append(child)
    visited = set()
    stack = set()

    def dfs(node):
        if node in stack:
            errors.append(f'Cycle detected at alias_id {node}')
            return
        if node in visited:
            return
        visited.add(node)
        stack.add(node)
        for child in graph.get(node, []):
            dfs(child)
        stack.remove(node)
    for alias in alias_to_family:
        dfs(alias)
    if errors:
        print('❌ Consistency check failed:')
        for e in errors:
            print('  -', e)
    else:
        print('✅ All consistency checks passed.')

def convert_to_csv_file(base_dir, as_to_org_id_dict, orgid_to_aliasid, orgid_to_orgname, org_families):
    AS_TABLE_path = base_dir + 'final_output/as_table.csv'
    ORG_ALIAS_TABLE_path = base_dir + 'final_output/org_alias_table.csv'
    ALIAS_REL_TABLE_path = base_dir + 'final_output/alias_relationships.csv'
    with open(AS_TABLE_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['asn', 'as_name', 'rir', 'org_name', 'alias_id'])
        for ((asn, rir, as_name), org_id_list) in as_to_org_id_dict.items():
            assert len(org_id_list) == 1
            org_name = orgid_to_orgname[org_id_list[0]]
            alias_id = orgid_to_aliasid[org_id_list[0]]
            writer.writerow([asn, as_name, rir, org_name, alias_id])
    with open(ORG_ALIAS_TABLE_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['org_family_id', 'alias_id'])
        for org_family in org_families:
            org_family_id = org_family['clique_id']
            for group in org_family['clique_alias_group_list']:
                alias_id = group['index']
                writer.writerow([org_family_id, alias_id])
    with open(ALIAS_REL_TABLE_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['child_alias_id', 'parent_alias_id'])
        for org_family in org_families:
            for group in org_family['clique_alias_group_list']:
                child_id = group['index']
                if 'parent_alias_group_id' in group:
                    writer.writerow([child_id, group['parent_alias_group_id'][0]])
