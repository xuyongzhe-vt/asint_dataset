import logging
import time
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.afrinic_db_reader import read_afrinic_whois_data
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.ripe_db_reader import read_ripe_whois_data
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.apnic_db_reader import read_apnic_whois_data
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.arin_db_reader import read_arin_whois_data
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.jpirr_db_reader import read_jpirr_whois_data
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.lacnic_db_reader import read_lacnic_whois_data
from as2org_pipeline.as2org_mapping.whois_parser.filter.obj_bundle_filter import resolve_as_num_discrepancy, normalize_as_obj
import re
from as2org_pipeline.as2org_mapping.entity.object_bundle import ObjectBundle
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
from as2org_pipeline.as2org_mapping.peering_db_parser.parser import parse_peering_db

def extract_number(text):
    match = re.search('\\d+', text)
    return int(match.group()) if match else None

def parse_whois(afrinic_db_path: str, ripe_db_path: str, arin_db_path: str, apnic_db_path: str, jpirr_db_path: str, lacnic_db_path: str, base_dir: str) -> dict[AS, list[Org]]:
    afrinic_bundle: ObjectBundle = read_afrinic_whois_data(afrinic_db_path)
    ripe_bundle: ObjectBundle = read_ripe_whois_data(ripe_db_path)
    apnic_bundle: ObjectBundle = read_apnic_whois_data(apnic_db_path)
    arin_bundle: ObjectBundle = read_arin_whois_data(arin_db_path)
    jpirr_bundle: ObjectBundle = read_jpirr_whois_data(jpirr_db_path)
    lacnic_bundle: ObjectBundle = read_lacnic_whois_data(lacnic_db_path)
    normalize_as_obj(afrinic_bundle)
    normalize_as_obj(ripe_bundle)
    normalize_as_obj(apnic_bundle)
    normalize_as_obj(arin_bundle)
    normalize_as_obj(jpirr_bundle)
    normalize_as_obj(lacnic_bundle)
    resolve_as_num_discrepancy([afrinic_bundle, ripe_bundle, apnic_bundle, arin_bundle, jpirr_bundle, lacnic_bundle])
    afrinic_bundle.save_to_file(base_dir + 'input/afrinic.json')
    ripe_bundle.save_to_file(base_dir + 'input/ripe.json')
    apnic_bundle.save_to_file(base_dir + 'input/apnic.json')
    arin_bundle.save_to_file(base_dir + 'input/arin.json')
    jpirr_bundle.save_to_file(base_dir + 'input/jpirr.json')
    lacnic_bundle.save_to_file(base_dir + 'input/lacnic.json')
    afrinic_bundle = ObjectBundle.from_json_file(base_dir + 'input/afrinic.json')
    ripe_bundle = ObjectBundle.from_json_file(base_dir + 'input/ripe.json')
    apnic_bundle = ObjectBundle.from_json_file(base_dir + 'input/apnic.json')
    arin_bundle = ObjectBundle.from_json_file(base_dir + 'input/arin.json')
    jpirr_bundle = ObjectBundle.from_json_file(base_dir + 'input/jpirr.json')
    lacnic_bundle = ObjectBundle.from_json_file(base_dir + 'input/lacnic.json')
    result_as_dict: dict[AS, list[Org]] = {}
    match_as_and_org(afrinic_bundle, result_as_dict)
    match_as_and_org(ripe_bundle, result_as_dict)
    match_as_and_org(apnic_bundle, result_as_dict)
    match_as_and_org(arin_bundle, result_as_dict)
    match_as_and_org(jpirr_bundle, result_as_dict)
    match_as_and_org(lacnic_bundle, result_as_dict)
    return result_as_dict

def match_as_and_org(obj_bundle: ObjectBundle, result_dict: dict[AS, list[Org]]):
    org_dict: dict[str, list[Org]] = {}
    for org in obj_bundle.org_list:
        if len(org.org_id) != 0 and org.org_id[0] != '' and (len(org.org_name) != 0):
            org_dict.setdefault(org.org_id[0], []).append(org)
    for as_obj in obj_bundle.as_list:
        if len(as_obj.aut_num) != 0 and as_obj.aut_num != '':
            result_dict.setdefault(as_obj, [])
