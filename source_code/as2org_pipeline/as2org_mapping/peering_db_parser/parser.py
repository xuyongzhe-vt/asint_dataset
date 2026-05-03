import json
from as2org_pipeline.as2org_mapping.peering_db_parser.peering_org import PeeringOrg
from as2org_pipeline.as2org_mapping.peering_db_parser.peering_net import PeeringNet
import re

def normalize_org_name(name: str) -> str:
    cleaned = re.sub('[,\\.\\|/\\\\;]', '', name)
    cleaned = re.sub('\\s+', ' ', cleaned).strip()
    return cleaned

def parse_peering_db(peering_db_path: str) -> tuple[list[PeeringOrg], list[PeeringNet]]:
    with open(peering_db_path, 'r') as file:
        json_data = file.read()
    data = json.loads(json_data)
    result_org = []
    result_net = []
    for org_json in data['org']['data']:
        result_org.append(PeeringOrg(org_json['id'], normalize_org_name(org_json['name']), org_json['website']))
    for net_json in data['net']['data']:
        result_net.append(PeeringNet(net_json['asn'], net_json['name'], net_json['org_id'], net_json['notes'], net_json['aka'], net_json['website']))
    return (result_org, result_net)
