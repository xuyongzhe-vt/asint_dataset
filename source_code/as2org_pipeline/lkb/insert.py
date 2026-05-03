import hashlib
import os
from datetime import datetime
from .backend import COLLECTION, get_client, normalize_mention
_PLACEHOLDER_VECTOR = [0.0, 0.0]
_ACQ_TAG = f"[{datetime.now().strftime('%Y-%m')}] "

def _row_id(text: str, mention: str, source_org: str, kind: str) -> int:
    payload = f'{mention}\x00{text}\x00{source_org}\x00{kind}'.encode('utf-8')
    h = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(h, byteorder='big', signed=True)

def _read_text_meta_pair(text_path: str, meta_path: str) -> list[tuple[str, list[str]]]:
    if not os.path.exists(text_path) or not os.path.exists(meta_path):
        return []
    with open(text_path, encoding='utf-8') as f:
        texts = [line.rstrip('\n') for line in f]
    with open(meta_path, encoding='utf-8') as f:
        metas = [line.strip() for line in f]
    pairs = []
    for (text, meta) in zip(texts, metas):
        if not text or not meta:
            continue
        mentions = [m.strip() for m in meta.split('|') if m.strip()]
        if mentions:
            pairs.append((text, mentions))
    return pairs

def _merge_orgs_txt(src: str, dst: str) -> None:
    if not os.path.exists(src):
        return
    with open(src, encoding='utf-8') as f:
        new_lines = [line.rstrip('\n') for line in f]
    existing = []
    if os.path.exists(dst):
        with open(dst, encoding='utf-8') as f:
            existing = [line.rstrip('\n') for line in f]
    seen = {line for line in existing if line}
    appended = [line for line in new_lines if line and line not in seen]
    if not appended and existing:
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        for line in existing + appended:
            if line:
                f.write(line + '\n')

def _copy_if_missing(src: str, dst: str) -> None:
    if not os.path.exists(src) or os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, encoding='utf-8') as f_in, open(dst, 'w', encoding='utf-8') as f_out:
        f_out.write(f_in.read())

def insert_lkb(ner_output_dir: str, lkb_dir: str) -> None:
    if not os.path.isdir(ner_output_dir):
        raise FileNotFoundError(f'NER output dir does not exist: {ner_output_dir}')
    client = get_client(lkb_dir)
    rows: list[dict] = []
    org_folders = sorted((d for d in os.listdir(ner_output_dir) if os.path.isdir(os.path.join(ner_output_dir, d))))
    for org_folder in org_folders:
        src_org_dir = os.path.join(ner_output_dir, org_folder)
        dst_org_dir = os.path.join(lkb_dir, org_folder)
        _merge_orgs_txt(os.path.join(src_org_dir, 'orgs.txt'), os.path.join(dst_org_dir, 'orgs.txt'))
        _copy_if_missing(os.path.join(src_org_dir, 'ori_org_name.txt'), os.path.join(dst_org_dir, 'ori_org_name.txt'))
        for kind in ('web', 'peering'):
            for (text, mentions) in _read_text_meta_pair(os.path.join(src_org_dir, f'{kind}_text.txt'), os.path.join(src_org_dir, f'{kind}_meta.txt')):
                for m in mentions:
                    key = normalize_mention(m)
                    if not key:
                        continue
                    truncated = (_ACQ_TAG + text)[:60000]
                    src = org_folder[:512]
                    rows.append({'id': _row_id(truncated, key, src, kind), 'mention': key, 'text': truncated, 'source_org': src, 'kind': kind, 'vector': _PLACEHOLDER_VECTOR})
    if not rows:
        print('no snippets to insert')
        return
    by_id = {row['id']: row for row in rows}
    rows = list(by_id.values())
    print(f'upserting {len(rows)} snippet rows ...')
    batch = 1000
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        client.upsert(COLLECTION, data=chunk)
        print(f'  upserted {min(i + batch, len(rows))}/{len(rows)}')
