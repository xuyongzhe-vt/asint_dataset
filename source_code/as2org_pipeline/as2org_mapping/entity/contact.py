from as2org_pipeline.as2org_mapping.config.config import contact_attr_for_grouping
ignored_fields = {}

class Contact:

    def __init__(self, phone: list[str], admin_c: list[str], tech_c: list[str], contact_name: list[str], street: list[str], email: list[str], mnt_by: list[str], ori_rir: str):
        self.phone = phone
        self.admin_c = admin_c
        self.tech_c = tech_c
        self.contact_name = contact_name
        self.street = street
        self.email = email
        self.mnt_by = mnt_by
        self.ori_rir = ori_rir

    def __repr__(self):
        return f'phone: {self.phone} \n admin_c: {self.admin_c} \n tech_c: {self.tech_c} \ncontact_name: {self.contact_name} \n street: {self.street} \n email: {self.email} \nmnt_by: {self.mnt_by}'

    def remove_generic_values(self, exclusion_list):
        for attribute in ['phone', 'admin_c', 'tech_c', 'contact_name', 'street', 'email', 'mnt_by']:
            setattr(self, attribute, [value for value in getattr(self, attribute) if value not in exclusion_list])

    def is_empty(self):
        for attr in contact_attr_for_grouping:
            value = getattr(self, attr)
            if not all((item == '' for item in value)):
                return False
        return True

    def get_canonical_key(self):
        return tuple(((k, tuple(sorted(v)) if isinstance(v, list) else v) for (k, v) in sorted(self.__dict__.items()) if k not in ignored_fields and v))

    def get_non_canonical_key(self):
        return tuple(((k, tuple(sorted(v)) if isinstance(v, list) else v) for (k, v) in sorted(self.__dict__.items()) if k in ignored_fields and v))
