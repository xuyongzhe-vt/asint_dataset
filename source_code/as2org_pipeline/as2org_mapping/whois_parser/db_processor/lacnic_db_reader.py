import re
from datetime import datetime
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
from as2org_pipeline.as2org_mapping.entity.contact import Contact
from as2org_pipeline.as2org_mapping.entity.as_block import ASBlock
from as2org_pipeline.as2org_mapping.entity.object_bundle import ObjectBundle
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.util.whois_db_util import Entry, read_items_whois_db, read_as_obj_from_item, read_contact_obj_from_item, has_only_one_key
as_keywords = {'aut-num'}
org_keywords = {''}
contact_keywords = {'person', 'mntner'}
as_block_keywords = {''}
as_set_keywords = {''}
keywords_set = as_keywords | org_keywords | contact_keywords | as_block_keywords

def read_lacnic_whois_data(filename: str) -> ObjectBundle:
    items: list[Entry] = read_items_whois_db(filename, keywords_set)
    as_list: list[AS] = []
    org_list: list[Org] = []
    contact_list: list[Contact] = []
    as_block_list: list[ASBlock] = []
    existing_as_dict = {}
    for item in items:
        if not has_only_one_key(item, keywords_set):
            print(item)
            print('*******************')
        if 'aut-num' in item:
            aut_num = item['aut-num']
            existing_as_dict[re.search('\\d+', aut_num[0]).group()] = 1
            as_list.append(read_as_obj_from_item(item, aut_num, 'descr', 'NON-EXIST', 'tech-c', 'NON-EXIST', 'NON-EXIST', 'mnt-by', 'NON-EXIST', 'NON-EXIST', 'changed', 'as-name', 'NON-EXIST', 'lacnic', changed_time_process_func))
        elif 'person' in item or 'mntner' in item:
            contact_list.append(read_contact_obj_from_item(item, ['phone'], 'admin-c', 'tech-c', ['person', 'mntner'], 'address', 'e-mail', 'mnt-by', 'lacnic'))
    return ObjectBundle(as_list, org_list, contact_list, as_block_list, 'lacnic')

def changed_time_process_func(item):
    timestamps = [datetime.strptime(entry.split()[0], '%Y-%m-%d') for entry in item['changed']]
    latest_timestamp = max(timestamps)
    return latest_timestamp
