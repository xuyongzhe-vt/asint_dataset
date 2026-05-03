import json
import logging
from as2org_pipeline.as2org_mapping.whois_parser.parser import parse_whois
from as2org_pipeline.as2org_mapping.peering_db_parser.parser import parse_peering_db
from as2org_pipeline.as2org_mapping.peering_db_parser.peering_net import PeeringNet
from as2org_pipeline.as2org_mapping.peering_db_parser.peering_org import PeeringOrg
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
import re
import os
from as2org_pipeline.as2org_mapping.caida_parser.parser import parse_caida

def normalize_org_name(name: str) -> str:
    cleaned = re.sub('[,\\.\\|/\\\\;]', '', name)
    cleaned = re.sub('\\s+', ' ', cleaned).strip()
    return cleaned

def starts_with_letter(s):
    return bool(re.match('^[a-zA-Z]', s))

def as_to_org_mapping(base_dir):
    logging.warning('=' * 60)
    logging.warning('[STEP 1] WHOIS Parsing')
    as_org_dict = parse_whois(base_dir + 'input/afrinic.db.gz', base_dir + 'input/ripe.db.gz', base_dir + 'input/arin.db.gz', base_dir + 'input/apnic.db.gz', base_dir + 'input/jpirr.db.gz', base_dir + 'input/lacnic.db.gz', base_dir)
    logging.warning(f'→ Total ASNs from WHOIS: {len(as_org_dict)}')
    starting_index = parse_as_org_dict_with_caida(base_dir, as_org_dict, 0)
    starting_index = parse_as_org_dict_with_peering(base_dir, as_org_dict, starting_index)
    parse_as_org_dict_by_as_name(as_org_dict, starting_index)
    generate_meta_file(base_dir, as_org_dict)
    for (_, org_list) in as_org_dict.items():
        assert len(org_list) == 1 or len(org_list) == 0
    check_mapping(base_dir)

def check_mapping(base_dir: str):
    org_file = os.path.join(base_dir, 'output', 'org.json')
    as_to_org_file = os.path.join(base_dir, 'output', 'as_to_org.json')
    with open(org_file, 'r', encoding='utf-8') as f:
        org_data = json.load(f)
    with open(as_to_org_file, 'r', encoding='utf-8') as f:
        as_to_org_data = json.load(f)
    asn_to_org = {}
    for entry in as_to_org_data:
        asn = entry['asn']
        org_id = entry['org_id']
        asn_to_org.setdefault(asn, set()).add(org_id)
    bad_asns = {asn: orgs for (asn, orgs) in asn_to_org.items() if len(orgs) != 1}
    if bad_asns:
        raise ValueError(f'Invalid ASN→Org mapping: some ASNs map to !=1 org: {bad_asns}')
    org_ids_from_org = set()
    for org in org_data:
        for oid in org['org_id']:
            org_ids_from_org.add(oid)
    org_to_asn = {}
    for entry in as_to_org_data:
        oid = entry['org_id']
        asn = entry['asn']
        org_to_asn.setdefault(oid, set()).add(asn)
    bad_orgs = {oid: asns for (oid, asns) in org_to_asn.items() if len(asns) != 1}
    if bad_orgs:
        raise ValueError(f'Invalid Org→ASN mapping: some org_ids map to !=1 ASN: {bad_orgs}')
    missing_orgs = org_ids_from_org - set(org_to_asn.keys())
    if missing_orgs:
        raise ValueError(f'Orgs in org.json missing from as_to_org.json: {missing_orgs}')
    logging.warning('✅ Mapping check passed: each ASN has exactly one org, and each org_id has exactly one ASN')

def generate_meta_file(base_dir, as_dict: dict[AS, list[Org]]):
    final_org_set = set()
    for (_, org_list) in as_dict.items():
        final_org_set.update(org_list)
    final_org_list = list(final_org_set)
    org_dict = {}
    for org in final_org_list:
        org_dict.setdefault(org.org_name[0], []).append(org)
    org_json = []
    for (org_name, org_list) in org_dict.items():
        org_json.append({'org_name': org_name, 'org_id': list(set([org.org_id[0] for org in org_list])), 'aka': list(set((s for org in org_list for s in org.aka if s != ''))), 'notes': list(set([''.join(org.notes) for org in org_list if ''.join(org.notes) != ''])), 'website': list(set((website for org in org_list for website in org.website if website != '')))})
    with open(base_dir + 'output/org.json', 'w', encoding='utf-8') as json_file:
        json.dump(org_json, json_file, indent=4, ensure_ascii=False)
    as_to_org_mapping_json = []
    for (as_obj, org_list) in as_dict.items():
        if len(org_list) == 0:
            continue
        for org in org_list:
            as_to_org_mapping_json.append({'asn': as_obj.aut_num[0], 'as_name': as_obj.aut_name, 'org_id': org.org_id[0], 'rir': as_obj.records_from_rir})
    with open(base_dir + 'output/as_to_org.json', 'w', encoding='utf-8') as json_file:
        json.dump(as_to_org_mapping_json, json_file, indent=4, ensure_ascii=False)
    logging.warning(f'org num:{len(org_json)}')
    logging.warning(f'as num: {len(as_to_org_mapping_json)}')

def parse_as_org_dict_with_caida(base_dir, as_dict: dict[AS, list[Org]], starting_index):
    caida_dict = parse_caida(base_dir + 'input/caida.jsonl')
    for (as_obj, org_list) in as_dict.items():
        asn = as_obj.aut_num[0]
        if asn in caida_dict:
            org_obj = Org([], [], [], ['AS2ORG_LLM_' + str(starting_index)], [normalize_org_name(caida_dict[asn])], [], [], [], [], [], [], 'caida', '', [])
            org_list = [org_obj]
            starting_index += 1
            as_dict[as_obj] = org_list
    return starting_index

def parse_as_org_dict_with_peering(base_dir, as_dict: dict[AS, list[Org]], starting_index):
    (peering_org_list, peering_net_list) = parse_peering_db(base_dir + 'input/peeringdb.json')
    print(f'Peering DB org num: {len(peering_org_list)}, AS num: {len(peering_net_list)}')
    peering_org_dict: dict[str, list[PeeringOrg]] = {}
    peering_net_dict: dict[str, list[PeeringNet]] = {}
    for peering_org in peering_org_list:
        if peering_org.org_id != '' and peering_org.name != '':
            peering_org_dict.setdefault(str(peering_org.org_id), []).append(peering_org)
    for peering_net in peering_net_list:
        if peering_net.asn != '' and peering_net.org_id != '':
            peering_net_dict.setdefault(str(peering_net.asn), []).append(peering_net)
    for (as_obj, org_list) in as_dict.items():
        asn = as_obj.aut_num[0]
        test_org_name = [org.org_name[0] for org in org_list]
        assert len(test_org_name) == len(set(test_org_name))
        if asn in peering_net_dict and str(peering_net_dict[asn][0].org_id) in peering_org_dict:
            peering_org = peering_org_dict[str(peering_net_dict[asn][0].org_id)][0]
            aka_list = []
            if len(org_list) == 0:
                org_obj = Org([], [], [], ['AS2ORG_LLM_' + str(starting_index)], [peering_org.name], [], [], [], [], [], [], 'peeringDB', '', [])
                starting_index += 1
                if peering_org.website != '':
                    org_obj.website.append(peering_org.website)
                org_list = [org_obj]
                as_dict[as_obj] = org_list
            elif peering_org.name != '':
                aka_list.append(peering_org.name)
            websites = []
            peering_net = peering_net_dict[asn][0]
            if peering_net.website != '':
                websites.append(peering_net.website)
            for org in org_list:
                if len(org.website) != 0:
                    websites += org.website
            for org in org_list:
                if len(peering_net.aka) > 0 and peering_net.aka != '' and (peering_net.aka[0] != ''):
                    if isinstance(peering_net.aka, list):
                        aka_list.append(''.join(peering_net.aka))
                    else:
                        aka_list.append(peering_net.aka)
                org.aka = aka_list
                org.notes = peering_net.notes
                org.website = list(set(websites))
    return starting_index

def parse_as_org_dict_by_as_name(as_dict: dict[AS, list[Org]], starting_index):
    for (as_obj, org_list) in as_dict.items():
        if len(org_list) == 0:
            if len(as_obj.aut_num) != 0 and len(as_obj.description) != 0 and starts_with_letter(as_obj.description[0]) and (as_obj.records_from_rir == 'apnic'):
                org_obj = Org([], [], [], ['AS2ORG_LLM_' + str(starting_index)], [normalize_org_name(as_obj.description[0])], [], [], [], [], [], [], 'from AS desc', '', [])
                starting_index += 1
                org_list = [org_obj]
                as_dict[as_obj] = org_list
            elif len(as_obj.aut_num) != 0 and len(as_obj.aut_name) != 0:
                org_obj = Org([], [], [], ['AS2ORG_LLM_' + str(starting_index)], [normalize_org_name(as_obj.aut_name[0])], [], [], [], [], [], [], 'from AS name', '', [])
                starting_index += 1
                org_list = [org_obj]
                as_dict[as_obj] = org_list
    return starting_index
