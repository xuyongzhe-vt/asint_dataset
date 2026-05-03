import os
from .backend import COLLECTION, get_client, normalize_mention

def list_orgs(lkb_dir: str) -> list[str]:
    if not os.path.isdir(lkb_dir):
        return []
    return sorted((name for name in os.listdir(lkb_dir) if os.path.isdir(os.path.join(lkb_dir, name))))

def load_candidate_mentions(lkb_dir: str, org_folder: str) -> list[str]:
    p = os.path.join(lkb_dir, org_folder, 'orgs.txt')
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_canonical_org_name(lkb_dir: str, org_folder: str) -> str:
    p = os.path.join(lkb_dir, org_folder, 'ori_org_name.txt')
    if not os.path.exists(p):
        return org_folder
    with open(p, encoding='utf-8') as f:
        return f.readline().strip() or org_folder

def _escape_for_filter(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')

def _query_by_mention(client, mention: str, top_k: int) -> list[str]:
    if not mention:
        return []
    # When a mention has far more matches than top_k, swap this scalar query
    # for an embedding-based similarity search against a relation-probing query
    # (e.g. "<base> is an alias of <mention>"); the schema already reserves a
    # vector field. Optional, currently unnecessary at observed scale.
    rows = client.query(COLLECTION, filter=f'mention == "{_escape_for_filter(mention)}"', output_fields=['text'], limit=top_k)
    return [r['text'] for r in rows]

def get_context(lkb_dir: str, base_org: str, target_org: str, top_k: int=10) -> list[str]:
    client = get_client(lkb_dir)
    target_hits = _query_by_mention(client, normalize_mention(target_org), top_k)
    base_hits = _query_by_mention(client, normalize_mention(base_org), top_k)
    (seen, merged) = (set(), [])
    for t in target_hits + base_hits:
        if t in seen:
            continue
        seen.add(t)
        merged.append(t)
        if len(merged) >= top_k:
            break
    return merged

def get_pairwise_context(lkb_dir: str, org_a: str, org_b: str, top_k: int=6) -> list[str]:
    return get_context(lkb_dir, org_a, org_b, top_k=top_k)
