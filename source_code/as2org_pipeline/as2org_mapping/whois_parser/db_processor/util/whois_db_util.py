from collections import OrderedDict
import gzip
import re
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
from as2org_pipeline.as2org_mapping.entity.contact import Contact
from as2org_pipeline.as2org_mapping.entity.as_block import ASBlock
import gc
split = re.compile('(.+?):\\s*(.*)')

class Entry(OrderedDict):

    def __repr__(self):
        output = []
        for (key, value) in self.items():
            output.append('{}:\t{}'.format(key, value))
        return '\n'.join(output)

    @property
    def date(self):
        changed = self.get('changed', None)
        if changed is not None:
            try:
                date = changed.split()[1]
            except IndexError:
                return '17000101'
        else:
            try:
                date = self['last-modified'].replace('-', '')
            except KeyError:
                return '16000101'
        return date

def read_items_whois_db_in_batch(filename: str, keywords_set, batch_size: int, processing_func):
    as_list: list[AS] = []
    org_list: list[Org] = []
    contact_list: list[Contact] = []
    as_block_list: list[ASBlock] = []
    with gzip.open(filename, 'rt', encoding='latin-1') as f:
        items = []
        item = Entry()
        for line in f:
            ol = line
            line = line.strip()
            if ol != '\n' and (not line or line[0] == '#'):
                continue
            if line:
                if re.match('^[^a-zA-Z0-9]', ol):
                    try:
                        item[k] += [line]
                        continue
                    except:
                        print(item)
                        continue
                m = split.match(line)
                if m:
                    (k, v) = m.groups()
                    if k in item and k != 'origin':
                        try:
                            item[k] += [v]
                        except:
                            print(item)
                    else:
                        try:
                            item[k] = [v]
                        except:
                            print(item)
                else:
                    try:
                        item[k] += [line]
                    except:
                        item[k] = [line]
            elif item:
                if keywords_set & set(item.keys()):
                    items.append(item)
                item = Entry()
                if len(items) >= batch_size:
                    (new_as, new_org, new_contact, new_as_block) = processing_func(items)
                    print(len(new_as))
                    as_list += new_as
                    org_list += new_org
                    contact_list += new_contact
                    as_block_list += new_as_block
                    items = []
                    gc.collect()
                    print('new batch')
    if len(items) > 0:
        (new_as, new_org, new_contact, new_as_block) = processing_func(items)
        as_list += new_as
        org_list += new_org
        contact_list += new_contact
        as_block_list += new_as_block
    return (as_list, org_list, contact_list, as_block_list)

def read_items_whois_db(filename: str, keywords_set):
    with gzip.open(filename, 'rt', encoding='latin-1') as f:
        items = []
        item = Entry()
        for line in f:
            ol = line
            line = line.strip()
            if ol != '\n' and (not line or line[0] == '#'):
                continue
            if line:
                if re.match('^[^a-zA-Z0-9]', ol):
                    try:
                        item[k] += [line]
                        continue
                    except:
                        print(item)
                        continue
                m = split.match(line)
                if m:
                    (k, v) = m.groups()
                    if k in item and k != 'origin':
                        try:
                            item[k] += [v]
                        except:
                            print(item)
                    else:
                        try:
                            item[k] = [v]
                        except:
                            print(item)
                else:
                    try:
                        item[k] += [line]
                    except:
                        item[k] = [line]
            elif item:
                if keywords_set & set(item.keys()):
                    items.append(item)
                item = Entry()
    return items

def read_list_from_item(key: str, item: Entry) -> list[str]:
    return item.get(key, [])

def read_as_obj_from_item(item: Entry, aut_num: list[str], des_key: str, admin_c_key: str, tech_c_key: str, owner_key: str, org_key: str, mnt_by_key: str, noc_c_key: str, notify_key: str, changed_key: str, as_name_key: str, abuse_c_key: str, records_from_rir: str, changed_time_process_func) -> AS:
    description = read_list_from_item(des_key, item)
    admin_c = read_list_from_item(admin_c_key, item)
    tech_c = read_list_from_item(tech_c_key, item)
    owner_c = read_list_from_item(owner_key, item)
    org_id = [cap_id.lower() for cap_id in read_list_from_item(org_key, item)]
    mnt_by = read_list_from_item(mnt_by_key, item)
    noc_c = read_list_from_item(noc_c_key, item)
    notify = read_list_from_item(notify_key, item)
    changed_email = [re.match('^\\S+@\\S+', entry).group(0) for entry in item.get(changed_key, []) if re.match('^\\S+@\\S+', entry)]
    aut_name = read_list_from_item(as_name_key, item)
    abuse_c = read_list_from_item(abuse_c_key, item)
    changed_time = changed_time_process_func(item)
    return AS(aut_num, description, admin_c, tech_c, owner_c, org_id, mnt_by, noc_c, notify, changed_email, aut_name, abuse_c, records_from_rir, changed_time)

def read_org_obj_from_item(item: Entry, admin_c_key: str, tech_c_key: list[str], phone_key: str, org_id_key: str, org_name_key: str, notify_key: str, noc_c_key: list[str], mnt_ref_key: str, street_key: str, changed_key: str, mnt_by_key: str, ori_rir: str, org_type_key: str, description_key: str) -> Org:
    admin_c = read_list_from_item(admin_c_key, item)
    tech_c = [entry for key in tech_c_key if key in item for entry in item[key]]
    phone = read_list_from_item(phone_key, item)
    org_id = [cap_id.lower() for cap_id in read_list_from_item(org_id_key, item)]
    org_name = read_list_from_item(org_name_key, item)
    notify = read_list_from_item(notify_key, item)
    noc_c = [entry for key in noc_c_key if key in item for entry in item[key]]
    mnt_ref = read_list_from_item(mnt_ref_key, item)
    street = read_list_from_item(street_key, item)
    changed_email = [re.match('^\\S+@\\S+', entry).group(0) for entry in item.get(changed_key, []) if re.match('^\\S+@\\S+', entry)]
    mnt_by = read_list_from_item(mnt_by_key, item)
    org_type_parsing_result = read_list_from_item(org_type_key, item)
    if len(org_type_parsing_result) != 0:
        org_type = org_type_parsing_result[0]
    else:
        org_type = ''
    description = read_list_from_item(description_key, item)
    return Org(admin_c, tech_c, phone, org_id, org_name, notify, noc_c, mnt_ref, street, changed_email, mnt_by, ori_rir, org_type, description)

def read_contact_obj_from_item(item: Entry, phone_key: list[str], admin_c_key: str, tech_c_key: str, contact_name_key: list[str], street_key: str, email_key: str, mnt_by_key: str, ori_rir: str) -> Contact:
    phone = [entry for key in phone_key if key in item for entry in item[key]]
    admin_c = read_list_from_item(admin_c_key, item)
    tech_c = read_list_from_item(tech_c_key, item)
    contact_name = [entry for key in contact_name_key if key in item for entry in item[key]]
    street = read_list_from_item(street_key, item)
    email = read_list_from_item(email_key, item)
    mnt_by = read_list_from_item(mnt_by_key, item)
    return Contact(phone, admin_c, tech_c, contact_name, street, email, mnt_by, ori_rir)

def read_as_block_obj_from_item(item: Entry, as_block_key: str, block_type_key: str, description_key: str, org_key: str, changed_key: str, ori_rir: str) -> ASBlock:
    as_block = read_list_from_item(as_block_key, item)
    block_type = read_list_from_item(block_type_key, item)
    description = read_list_from_item(description_key, item)
    org = read_list_from_item(org_key, item)
    changed = [re.match('^\\S+@\\S+\\s+(\\d{8})', entry).group(1) for entry in item.get(changed_key, []) if re.match('^\\S+@\\S+\\s+\\d{8}', entry)]
    return ASBlock(as_block, block_type, description, org, changed, ori_rir)

def has_only_one_key(d, keywords_set):
    present_keys = keywords_set & d.keys()
    if len(present_keys) == 2 and 'ASHandle' in present_keys and ('OrgID' in present_keys):
        return True
    return len(present_keys) == 1
