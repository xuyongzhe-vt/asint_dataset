from as2org_pipeline.config import base_dir
import os
import json
from as2org_pipeline.config import base_dir
if __name__ == '__main__':
    split = 2
    org_json_path = os.path.join(base_dir, 'output', 'org.json')
    output_dir = os.path.join(base_dir, 'metadata')
    with open(org_json_path, 'r', encoding='utf-8') as f:
        org_data = json.load(f)
    total_orgs = len(org_data)
    if total_orgs == 0:
        raise Exception('No organizations to split.')
    chunk_size = (total_orgs + split - 1) // split
    for i in range(split):
        chunk = org_data[i * chunk_size:(i + 1) * chunk_size]
        out_path = os.path.join(output_dir, f'org_{i + 1}.json')
        with open(out_path, 'w', encoding='utf-8') as out_f:
            json.dump(chunk, out_f, indent=2, ensure_ascii=False)
        print(f'saved {len(chunk)} orgs in org_{i + 1}.json')
    print(f'Split {total_orgs} organizations into {split} files in {output_dir}')
