from as2org_pipeline.as2org_mapping.entity.object_bundle import ObjectBundle
from as2org_pipeline.as2org_mapping.entity.as_obj import AS
from as2org_pipeline.as2org_mapping.entity.as_block import ASBlock
from bisect import bisect_left
import re
NULLIFIED = 'NULLIFIED'

def normalize_as_obj(obj_bundle: ObjectBundle):
    pattern = '\\d+'
    filtered_as_list = []
    for as_obj in obj_bundle.as_list:
        if len(as_obj.aut_num) == 0:
            continue
        numbers = re.findall(pattern, as_obj.aut_num[0])
        asn = ''.join(numbers)
        asn = str(asn)
        as_obj.aut_num = [asn]
        filtered_as_list.append(as_obj)
    obj_bundle.as_list = filtered_as_list

def resolve_as_num_discrepancy(obj_bundle_list: list[ObjectBundle]):
    as_dict = {}
    as_block_list = []
    for obj_bundle in obj_bundle_list:
        for as_obj in obj_bundle.as_list:
            as_dict.setdefault(as_obj.aut_num[0], []).append(as_obj)
        as_block_list += obj_bundle.as_block_list
    as_block_sorted_list = sorted(as_block_list, key=lambda x: x.from_as_num)
    for (k, v) in as_dict.items():
        if len(v) > 1:
            process_as_obj_with_same_aut_num(v, as_block_sorted_list)
    for obj_bundle in obj_bundle_list:
        obj_bundle.as_list = [as_obj for as_obj in obj_bundle.as_list if as_obj.aut_num[0] != NULLIFIED]

def process_as_obj_with_same_aut_num(as_obj_list: list[AS], sorted_as_block_list: list[ASBlock]):
    aut_num_string = as_obj_list[0].aut_num[0]
    aut_num = int(re.search('\\d+', aut_num_string).group())
    idx = bisect_left([as_block.from_as_num for as_block in sorted_as_block_list], aut_num)
    matches = []
    while True:
        if sorted_as_block_list[idx].from_as_num <= aut_num <= sorted_as_block_list[idx].to_as_num:
            matches.append(sorted_as_block_list[idx])
        if sorted_as_block_list[idx].from_as_num > aut_num:
            break
        idx += 1
    sorted_as_obj = sorted(as_obj_list, key=lambda x: x.changed_time, reverse=True)
    if len(matches) == 0:
        for as_obj in sorted_as_obj[1:]:
            as_obj.aut_num = [NULLIFIED]
    else:
        valid_as_block = sorted(matches, key=lambda x: x.changed_date, reverse=True)[0]
        matched = False
        for as_obj in as_obj_list:
            if as_obj.records_from_rir != valid_as_block.block_assigned_to:
                as_obj.aut_num = [NULLIFIED]
            else:
                matched = True
        if not matched:
            sorted_as_obj[0].aut_num = [aut_num_string]
