from as2org_pipeline.as2org_mapping.config.config import org_attr_for_grouping
ignored_fields = {}

class Org:

    def __init__(self, admin_c: list[str], tech_c: list[str], phone: list[str], org_id: list[str], org_name: list[str], notify: list[str], noc_c: list[str], mnt_ref: list[str], street: list[str], changed_email: list[str], mnt_by: list[str], ori_rir: str, org_type: str, description: list[str], aka='', notes='', website=None):
        self.admin_c = admin_c
        self.tech_c = tech_c
        self.phone = phone
        self.org_id = org_id
        self.org_name = org_name
        self.notify = notify
        self.noc_c = noc_c
        self.mnt_ref = mnt_ref
        self.street = street
        self.changed_email = changed_email
        self.mnt_by = mnt_by
        self.ori_rir = ori_rir
        self.org_type = org_type
        self.description = description
        self.aka = aka
        self.notes = notes
        self.website = website if website is not None else []

    def __repr__(self):
        return f'org_name: {self.org_name} \n admin_c: {self.admin_c} \n tech_c: {self.tech_c} \n phone: {self.phone}org_id: {self.org_id} \n notify: {self.notify} \n noc_c: {self.noc_c}mnt_ref: {self.mnt_ref} \n street: {self.street} \n changed_email: {self.changed_email}mnt_by: {self.mnt_by} \n '

    def remove_generic_values(self, generic_value: set[str]):
        for attribute in ['admin_c', 'tech_c', 'phone', 'org_name', 'notify', 'noc_c', 'mnt_ref', 'street', 'changed_email', 'mnt_by']:
            setattr(self, attribute, [value for value in getattr(self, attribute) if value not in generic_value])

    def is_empty(self) -> bool:
        for attr in org_attr_for_grouping:
            value = getattr(self, attr)
            if not all((item == '' for item in value)):
                return False
        return True

    def get_canonical_key(self):
        return tuple(((k, tuple(sorted(v)) if isinstance(v, list) else v) for (k, v) in sorted(self.__dict__.items()) if k not in ignored_fields and v))

    def get_non_canonical_key(self):
        return tuple(((k, tuple(sorted(v)) if isinstance(v, list) else v) for (k, v) in sorted(self.__dict__.items()) if k in ignored_fields and v))

    def __eq__(self, other):
        if not isinstance(other, Org):
            return NotImplemented
        return all((getattr(self, k) == getattr(other, k) for k in self.__dict__))

    def __hash__(self):
        items = []
        for (k, v) in sorted(self.__dict__.items()):
            if isinstance(v, list):
                items.append((k, tuple(v)))
            else:
                items.append((k, v))
        return hash(tuple(items))
