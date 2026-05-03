from datetime import datetime
import re
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
from as2org_pipeline.as2org_mapping.entity.contact import Contact
from as2org_pipeline.as2org_mapping.entity.as_block import ASBlock
from as2org_pipeline.as2org_mapping.entity.object_bundle import ObjectBundle
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.util.whois_db_util import read_as_obj_from_item, read_contact_obj_from_item, has_only_one_key, read_items_whois_db_in_batch, read_org_obj_from_item
as_keywords = {'ASHandle'}
org_keywords = {'OrgID'}
contact_keywords = {'POCHandle'}
as_block_keywords = {''}
keywords_set = as_keywords | org_keywords | contact_keywords | as_block_keywords

def parse_range(text):
    match = re.search('(\\d+)\\s*-\\s*(\\d+)', text)
    if match:
        (start, end) = map(int, match.groups())
        return list(range(start, end + 1))
    return []

def extract_number(text):
    match = re.search('\\d+', text)
    return int(match.group()) if match else None

def process_read_items(items):
    as_list: list[AS] = []
    org_list: list[Org] = []
    contact_list: list[Contact] = []
    as_block_list: list[ASBlock] = []
    for item in items:
        if not has_only_one_key(item, keywords_set):
            print(item)
            print('*******************')
        if 'ASHandle' in item:
            aut_num = item['ASHandle']
            if 'OrgID' in item and (item['OrgID'][0] == 'RIPE' or item['OrgID'][0] == 'APNIC' or item['OrgID'][0] == 'LACNIC' or (item['OrgID'][0] == 'AFRINIC') or (item['OrgID'][0] == 'IANA')):
                continue
            base_asn = extract_number(aut_num[0])
            if base_asn > 10000000:
                continue
            new_as_obj = read_as_obj_from_item(item, aut_num, 'Comment', 'NON-EXIST', 'TechHandle', 'Source', 'OrgID', 'NON-EXIST', 'NOCHandle', 'NON-EXIST', 'NON-EXIST', 'ASName', 'AbuseHandle', 'arin', changed_time_process_func)
            as_list.append(new_as_obj)
            if 'ASNumber' in item:
                candidate_asn = parse_range(item['ASNumber'][0])
                if len(candidate_asn) != 0:
                    for candidate in candidate_asn:
                        if candidate != base_asn:
                            as_list.append(AS(['AS' + str(candidate)], new_as_obj.description, new_as_obj.admin_c, new_as_obj.tech_c, new_as_obj.owner_c, new_as_obj.org_id, new_as_obj.mnt_by, new_as_obj.noc_c, new_as_obj.notify, new_as_obj.changed_email, new_as_obj.aut_name, new_as_obj.abuse_c, new_as_obj.records_from_rir, new_as_obj.changed_time))
        elif 'OrgID' in item and 'NetHandle' not in item and ('V6NetHandle' not in item):
            org_list.append(read_org_obj_from_item(item, 'OrgAdminHandle', ['TechHandle', 'OrgTechHandle'], 'NON-EXIST', 'OrgID', 'OrgName', 'NON-EXIST', ['OrgNOCHandle', 'NOCHandle'], 'NON-EXIST', 'Street', 'NON-EXIST', 'NON-EXIST', 'arin', '', 'Comment'))
        elif 'POCHandle' in item:
            contact_list.append(read_contact_obj_from_item(item, ['MobilePhone', 'FaxPhone', 'OfficePhone'], 'NON-EXIST', 'NON-EXIST', ['POCHandle'], 'Street', 'Mailbox', 'NON-EXIST', 'arin'))
    return (as_list, org_list, contact_list, as_block_list)

def changed_time_process_func(item):
    timestamps = [datetime.strptime(entry, '%Y-%m-%d') for entry in item['Updated']]
    return max(timestamps)

def read_arin_whois_data(filename: str) -> ObjectBundle:
    (as_list, org_list, contact_list, as_block_list) = read_items_whois_db_in_batch(filename, keywords_set, 500000, process_read_items)
    return ObjectBundle(as_list, org_list, contact_list, as_block_list, 'arin')
