import pandas as pd
import json

def parse_caida(jsonl_path: str) -> dict[str, str]:
    org_map = {}
    as_list = []
    as_record_count = 0
    org_record_count = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj.get('type') == 'ASN':
                    org_id = obj.get('organizationId', '')
                    if org_id and (not org_id.startswith('@del')):
                        as_record_count += 1
                        as_list.append({'asn': obj['asn'], 'org_id': org_id})
                elif obj.get('type') == 'Organization':
                    org_record_count += 1
                    org_id = obj.get('organizationId', '')
                    org_name = obj.get('name', '')
                    if org_id and org_name and (not org_name.startswith('±')):
                        org_map[org_id] = org_name
            except Exception as e:
                print(f'Skipping invalid line: {e}')
    print(f'Loaded {len(as_list)} AS records')
    print(f'CAIDA AS num: {as_record_count}, org num: {org_record_count}')
    result = {}
    for entry in as_list:
        org_name = org_map.get(entry['org_id'])
        if org_name:
            result[str(entry['asn'])] = org_name
    return result
