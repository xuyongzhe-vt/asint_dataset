import re
from datetime import datetime
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
from as2org_pipeline.as2org_mapping.entity.contact import Contact
from as2org_pipeline.as2org_mapping.entity.as_block import ASBlock
from as2org_pipeline.as2org_mapping.entity.object_bundle import ObjectBundle
from as2org_pipeline.as2org_mapping.whois_parser.db_processor.util.whois_db_util import Entry, read_items_whois_db, read_as_obj_from_item, read_org_obj_from_item, read_contact_obj_from_item, has_only_one_key
as_keywords = {'aut-num'}
org_keywords = {'organisation'}
contact_keywords = {'role', 'mntner'}
as_block_keywords = {'as-block'}
keywords_set = as_keywords | org_keywords | contact_keywords | as_block_keywords

def read_ripe_whois_data(filename: str) -> ObjectBundle:
    items: list[Entry] = read_items_whois_db(filename, keywords_set)
    as_list: list[AS] = []
    org_list: list[Org] = []
    contact_list: list[Contact] = []
    as_block_list: list[ASBlock] = []
    for item in items:
        if not has_only_one_key(item, keywords_set):
            print(item)
            print('*******************')
        if 'aut-num' in item:
            aut_num = item['aut-num']
            as_list.append(read_as_obj_from_item(item, aut_num, 'descr', 'admin-c', 'tech-c', 'NON-EXIST', 'org', 'mnt-by', 'NON-EXIST', 'notify', 'changed', 'as-name', 'NON-EXIST', 'ripe', changed_time_process_func))
        elif 'role' in item or 'mntner' in item:
            contact_list.append(read_contact_obj_from_item(item, ['phone'], 'admin-c', 'tech-c', ['person', 'mntner'], 'address', 'e-mail', 'mnt-by', 'ripe'))
        elif 'organisation' in item:
            org_list.append(read_org_obj_from_item(item, 'admin-c', ['tech-c'], 'phone', 'organisation', 'org-name', 'notify', ['NON-EXIST'], 'mnt-ref', 'address', 'changed', 'mnt-by', 'ripe', '', ''))
        elif 'as-block' in item:
            assert len(item.get('as-block')) == 1
            as_block_value = item.get('as-block')[0]
            numbers = re.findall('\\d+', as_block_value)
            assert len(numbers) == 2 and int(numbers[0]) <= int(numbers[1])
            block_assigned_to = determine_ori_rir(item.get('remarks', []) + item.get('descr', []))
            if block_assigned_to == '':
                continue
            timestamps = [datetime.strptime(entry, '%Y-%m-%dT%H:%M:%SZ') for entry in item['last-modified']]
            latest_timestamp = max(timestamps)
            as_block_list.append(ASBlock(int(numbers[0]), int(numbers[1]), 'ripe', latest_timestamp, block_assigned_to))
    return ObjectBundle(as_list, org_list, contact_list, as_block_list, 'ripe')

def changed_time_process_func(item):
    timestamps = [datetime.strptime(entry, '%Y-%m-%dT%H:%M:%SZ') for entry in item['last-modified']]
    return max(timestamps)

def determine_ori_rir(remarks_and_descr: list[str]):
    for descr in remarks_and_descr:
        if 'ripe' in descr or 'RIPE' in descr:
            return 'ripe'
        elif 'apnic' in descr or 'APNIC' in descr:
            return 'apnic'
        elif 'lacnic' in descr or 'LACNIC' in descr:
            return 'lacnic'
        elif 'arin' in descr or 'ARIN' in descr:
            return 'arin'
        elif 'afrinic' in descr or 'AFRINIC' in descr:
            return 'afrinic'
    return ''
