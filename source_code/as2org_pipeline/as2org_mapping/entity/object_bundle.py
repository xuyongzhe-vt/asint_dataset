import json
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.org import Org
from as2org_pipeline.as2org_mapping.entity.contact import Contact
from as2org_pipeline.as2org_mapping.entity.as_block import ASBlock
from datetime import datetime

def save_object_list_to_file(object_list, output_file_path):

    def custom_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        raise TypeError(f'Type {type(obj)} is not serializable')
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(object_list, f, default=custom_serializer, indent=4, ensure_ascii=False)

class ObjectBundle:

    def __init__(self, as_list: list[AS], org_list: list[Org], contact_list: list[Contact], as_block_list: list[ASBlock], ori_rir: str):
        self.as_list = as_list
        self.org_list = org_list
        self.contact_list = contact_list
        self.as_block_list = as_block_list
        self.ori_rir = ori_rir

    def print_statistic(self):
        print(len(self.as_list), len(self.org_list), len(self.contact_list), len(self.as_block_list))

    def save_to_file(self, output_file_path):

        def custom_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            raise TypeError(f'Type {type(obj)} is not serializable')
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(self, f, default=custom_serializer, indent=4, ensure_ascii=False)

    @classmethod
    def from_json_file(cls, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(as_list=[AS(**as_dict) for as_dict in data['as_list']], org_list=[Org(**org_dict) for org_dict in data['org_list']], contact_list=[Contact(**contact_dict) for contact_dict in data['contact_list']], as_block_list=[ASBlock(**as_block_dict) for as_block_dict in data['as_block_list']], ori_rir=data['ori_rir'])

    @classmethod
    def from_json_file_list(cls, file_path) -> list['ObjectBundle']:
        with open(file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
        return [cls(as_list=[AS(**as_dict) for as_dict in data['as_list']], org_list=[Org(**org_dict) for org_dict in data['org_list']], contact_list=[Contact(**contact_dict) for contact_dict in data['contact_list']], as_block_list=[ASBlock(**as_block_dict) for as_block_dict in data['as_block_list']], ori_rir=data['ori_rir']) for data in data_list]
