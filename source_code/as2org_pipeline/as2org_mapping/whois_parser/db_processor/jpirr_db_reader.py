from datetime import datetime
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
from as2org_pipeline.as2org_mapping.entity.contact import Contact
from as2org_pipeline.as2org_mapping.entity.as_block import ASBlock
from as2org_pipeline.as2org_mapping.entity.object_bundle import ObjectBundle
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.util.whois_db_util import read_as_obj_from_item, read_contact_obj_from_item, has_only_one_key, read_items_whois_db_in_batch
as_keywords = {'aut-num'}
org_keywords = {''}
contact_keywords = {'mntner', 'role', 'person'}
as_block_keywords = {''}
keywords_set = as_keywords | org_keywords | contact_keywords | as_block_keywords

def process_read_items(items):
    as_list: list[AS] = []
    org_list: list[Org] = []
    contact_list: list[Contact] = []
    as_block_list: list[ASBlock] = []
    for item in items:
        if not has_only_one_key(item, keywords_set):
            print(item)
            print('*******************')
        if as_keywords & item.keys():
            aut_num = item['aut-num']
            as_list.append(read_as_obj_from_item(item, aut_num, 'descr', 'admin-c', 'tech-c', 'NON-EXIST', 'NON-EXIST', 'mnt-by', 'NOCHandle', 'NON-EXIST', 'changed', 'as-name', 'AbuseHandle', 'jpirr', changed_time_process_func))
        elif contact_keywords & item.keys():
            contact_list.append(read_contact_obj_from_item(item, ['fax-no', 'phone'], 'admin-c', 'tech-c', ['NON-EXIST'], 'address', 'e-mail', 'mnt-by', 'jpirr'))
    return (as_list, org_list, contact_list, as_block_list)

def changed_time_process_func(item):
    timestamps = [datetime.strptime(entry.split()[1], '%Y%m%d') for entry in item['changed']]
    latest_timestamp = max(timestamps)
    return latest_timestamp

def read_jpirr_whois_data(filename: str) -> ObjectBundle:
    (as_list, org_list, contact_list, as_block_list) = read_items_whois_db_in_batch(filename, keywords_set, 500000, process_read_items)
    return ObjectBundle(as_list, org_list, contact_list, as_block_list, 'jpirr')
