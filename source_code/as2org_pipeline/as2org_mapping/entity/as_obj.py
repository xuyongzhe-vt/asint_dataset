from as2org_pipeline.as2org_mapping.config.config import as_attr_for_grouping
from datetime import datetime
ignored_fields = {}

class AS:

    def __init__(self, aut_num: list[str], description: list[str], admin_c: list[str], tech_c: list[str], owner_c: list[str], org_id: list[str], mnt_by: list[str], noc_c: list[str], notify: list[str], changed_email: list[str], aut_name: list[str], abuse_c: list[str], records_from_rir: str, changed_time: datetime):
        self.aut_num = aut_num
        self.description = description
        self.admin_c = admin_c
        self.tech_c = tech_c
        self.owner_c = owner_c
        self.org_id = org_id
        self.mnt_by = mnt_by
        self.noc_c = noc_c
        self.notify = notify
        self.changed_email = changed_email
        self.aut_name = aut_name
        self.abuse_c = abuse_c
        self.records_from_rir = records_from_rir
        self.changed_time = changed_time

    def __repr__(self):
        return f'aut_num: {self.aut_num} \n description: {self.description} \n admin_c: {self.admin_c} \n tech_c: {self.tech_c} \n owner_c: {self.owner_c} \n org_id: {self.org_id} \n mnt_by: {self.mnt_by} \n noc_c: {self.noc_c} \n notify: {self.notify} \n changed_email: {self.changed_email} \n aut_name: {self.aut_name} \n abuse_c: {self.abuse_c} \n records_from_rir: {self.records_from_rir} \n changed_time: {self.changed_time} \n'

    def remove_generic_values(self, exclusion_list):
        for attribute in ['aut_num', 'description', 'admin_c', 'tech_c', 'owner_c', 'org_id', 'mnt_by', 'noc_c', 'notify', 'changed_email', 'aut_name', 'abuse_c']:
            setattr(self, attribute, [value for value in getattr(self, attribute) if value not in exclusion_list])

    def is_empty(self):
        for attr in as_attr_for_grouping:
            value = getattr(self, attr)
            if not all((item == '' for item in value)):
                return False
        return True

    def get_canonical_key(self):
        return tuple(((k, tuple(sorted(v)) if isinstance(v, list) else v) for (k, v) in sorted(self.__dict__.items()) if k not in ignored_fields and v))

    def get_non_canonical_key(self):
        return tuple(((k, tuple(sorted(v)) if isinstance(v, list) else v) for (k, v) in sorted(self.__dict__.items()) if k in ignored_fields and v))
