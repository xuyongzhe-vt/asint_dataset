import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from openai import APIError, AsyncOpenAI
ROOT = Path(__file__).resolve().parent.parent
BENCH_FILE = ROOT / 'benchmark_pairs.jsonl'
OUTPUT_DIR = ROOT / 'predictions'
ALIAS_PROMPT = '\nYou are given context information about two organizations. Your task is to assess whether the two organizations refer to the same real-world entity.\nThis includes cases where the names are aliases (e.g., abbreviations, legal vs. brand names) or represent different departments or units within the same organization.\nYou will receive the following inputs:\n\nOrganization A: the name of the first organization\nOrganization B: the name of the second organization\nContext: background text (such as web content or peering information) related to Organization A or B\n\nYour job is to carefully read the context and decide how likely it is that the two organizations are aliases or part of the same entity.\n\nRespond in the following JSON format:\n{{\n    "Confidence Score": "a number between 0 and 1, where:\n    1.0 means they clearly refer to the same organization or closely related units,\n    0.0 means they are completely unrelated, or one of the org is government or government-related org.\n    Values in between reflect varying degrees of confidence",\n    "Explanation": "a brief rationale for your score, based on name similarity and/or contextual overlap. Be honest and precise.\n    Do not assume they are related unless there is strong evidence in the context.\n    Note that for governmental department, like department of financial, always give 0 as Confidence Score, even if context say so.\n"\n}}\n\n# Example output\n{{\n    "Confidence Score": "0.1",\n    "Explanation": "Apple Inc is not an alias of Microsoft, and the context does not mention any such relationship."\n}}\n\n# Input\nOrganization A: {org_a}\nOrganization A: {org_b}\nContext: {context}\n\nNow start your reasoning:\n'
PARENT_CHILD_PROMPT = '\n### Task\nYou are given context about two organizations. Your job is to determine whether there is a **current parent-child relationship** between them — where one **currently owns, controls, or oversees** the other.\n\n### You will receive:\n- **Organization A**\n- **Organization B**\n- **Context**: background information (such as web content, news articles, or company descriptions) about either or both organizations\n\n### Your job is to assess one of these **directional** relationships:\n\n1. **Organization A is the parent of Organization B**\n   (A currently owns, controls, or oversees B)\n2. **Organization B is the parent of Organization A**\n   (B currently owns, controls, or oversees A)\n3. **No parent-child relationship exists**\n\n### Strict Evaluation Criteria\n\nYou **must not infer or assume anything** beyond the context. Follow these rules:\n\n1. Use only current relationship indicators\n- Ignore past-tense relationships (e.g., "was acquired by", "used to be a subsidiary of") unless the **present-tense relationship is confirmed elsewhere**.\n- Accept only statements that **clearly describe a current relationship** (e.g., "is a subsidiary of", "is owned by", "is part of").\n- If one organization was acquired in the past, but is no longer owned, treat it as no parent-child relationship.\n\n2. Require exact organization name matches\n- Do **not** infer connections based on partial matches or name similarity.\n- Only accept relationships where the **exact organization names** (as given) appear in the relationship sentence.\n\n3. Directionality must be explicit\n- You must clearly identify which organization is the **parent** and which is the **child**, based on direct statements.\n- Reverse relationships (e.g., "B owns A" vs. "A owns B") must result in different scores.\n\n4. Special case: Government agencies\n- If **either organization** is a government department or agency, return:\n  {{\n    "No_Relationship_Score": "1.0",\n    "A_is_parent_of_B_Score": "0.0",\n    "B_is_parent_of_A_Score": "0.0"\n  }}\n\n### Output Format\n\nYou must return a single JSON object with the following fields:\n\n{{\n  "A_is_parent_of_B_Score": "<float between 0 and 1 — set to 1.0 only if the context clearly shows that Organization A currently owns or controls Organization B. Otherwise, use 0.0>",\n  "B_is_parent_of_A_Score": "<float between 0 and 1 — set to 1.0 only if the context clearly shows that Organization B currently owns or controls Organization A. Otherwise, use 0.0>",\n  "No_Relationship_Score": "<float between 0 and 1 — set to 1.0 if there is no present-tense parent-child relationship or if names do not exactly match. Otherwise, use 0.0>",\n  "Explanation": "Clearly explain what phrases in the context support your decision, and show the context. Only use exact name matches and present-tense relationships. If no evidence is found, explain this and set No_Relationship_Score to 1.0."\n}}\n\n### Self-Check Before Submitting:\n- Are you using only **present-tense** relationship cues?\n- Are you using **exact org name matches only**?\n- Is the **directionality** (parent vs. child) reflected correctly in the score fields?\n- If no valid match, is `No_Relationship_Score = 1.0`?\n- If a government org is involved, are all scores set appropriately?\n\n### input\n------------------------- Begin of User Input ------------------------------------\n\n- **Organization A**: {org_a}\n- **Organization B**: {org_b}\n- **Context**: {context}\n\n------------------------- End of User Input ------------------------------------\n\n### Now start your reasoning\n'
ALIAS_KEYS = {'Confidence Score', 'Explanation'}
PC_KEYS = {'A_is_parent_of_B_Score', 'B_is_parent_of_A_Score', 'No_Relationship_Score', 'Explanation'}
ALIAS_PROMPT_MINIMAL = 'Organization A: {org_a}\nOrganization B: {org_b}\nContext: {context}\n\nRespond with a single JSON object:\n{{\n    "Confidence Score": "<number between 0 and 1>",\n    "Explanation": "<brief rationale>"\n}}\n'
PARENT_CHILD_PROMPT_MINIMAL = 'Organization A: {org_a}\nOrganization B: {org_b}\nContext: {context}\n\nRespond with a single JSON object:\n{{\n    "A_is_parent_of_B_Score": "<0 or 1>",\n    "B_is_parent_of_A_Score": "<0 or 1>",\n    "No_Relationship_Score": "<0 or 1>",\n    "Explanation": "<brief rationale>"\n}}\n'

def _read_dir(org_dir: str) -> List[str]:
    out = []
    if not org_dir:
        return out
    p = Path(org_dir)
    for fname in ('peering_text.txt', 'web_text.txt'):
        f = p / fname
        if f.exists():
            t = f.read_text(encoding='utf-8', errors='ignore').strip()
            if t:
                out.append(t)
    return out

def read_context(org_a_dir: str, org_b_dir: str) -> str:
    chunks = _read_dir(org_a_dir) + _read_dir(org_b_dir)
    return '\n\n\t'.join(set(chunks))

def build_prompt(task_type: str, org_a: str, org_b: str, context: str, prompt_variant: str='full') -> str:
    if prompt_variant == 'minimal':
        tmpl = ALIAS_PROMPT_MINIMAL if task_type == 'alias' else PARENT_CHILD_PROMPT_MINIMAL
    else:
        tmpl = ALIAS_PROMPT if task_type == 'alias' else PARENT_CHILD_PROMPT
    return tmpl.format(org_a=org_a, org_b=org_b, context=context)

def _extract_json_objects(text: str):
    text = re.sub('<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub('<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL)
    results = []
    stack = []
    start = None
    for i, ch in enumerate(text):
        if ch == '{':
            if not stack:
                start = i
            stack.append(ch)
        elif ch == '}':
            if stack:
                stack.pop()
                if not stack and start is not None:
                    try:
                        results.append(json.loads(text[start:i + 1]))
                    except json.JSONDecodeError:
                        pass
                    start = None
    return results

def extract_final_json(text: str, required_keys: set) -> Optional[dict]:
    for obj in _extract_json_objects(text):
        if required_keys.issubset(obj.keys()):
            return obj
    return None

def _to_float(x):
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        m = re.search('-?\\d+\\.?\\d*', x)
        if m:
            try:
                return float(m.group())
            except ValueError:
                pass
    return None

def parse_response(task_type: str, raw_text: str):
    keys = ALIAS_KEYS if task_type == 'alias' else PC_KEYS
    obj = extract_final_json(raw_text, keys)
    if obj is None:
        return (None, {}, None, 'no valid JSON with required keys')
    if task_type == 'alias':
        s = _to_float(obj.get('Confidence Score'))
        if s is None:
            return (None, {}, obj, 'non-numeric Confidence Score')
        pred = 'alias' if s >= 0.5 else 'not_alias'
        return (pred, {'confidence': s}, obj, None)
    sa = _to_float(obj.get('A_is_parent_of_B_Score'))
    sb = _to_float(obj.get('B_is_parent_of_A_Score'))
    sn = _to_float(obj.get('No_Relationship_Score'))
    if None in (sa, sb, sn):
        return (None, {}, obj, 'non-numeric PC scores')
    mx = max(sa, sb, sn)
    if mx == sa:
        pred = 'A_parent_B'
    elif mx == sb:
        pred = 'B_parent_A'
    else:
        pred = 'no_relationship'
    return (pred, {'A_parent_B': sa, 'B_parent_A': sb, 'no_relationship': sn}, obj, None)

@dataclass
class RunConfig:
    model_name: str
    out_name: str
    endpoint: str = 'http://localhost:8001/v1'
    api_key: str = 'EMPTY'
    max_tokens: int = 2048
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = 1
    concurrency: int = 16
    request_timeout: float = 300.0
    limit: Optional[int] = None
    context_char_limit: Optional[int] = None
    skip_context: bool = False
    prompt_variant: str = 'full'

@dataclass
class Prediction:
    pair_id: str
    task_type: str
    model: str
    prediction: Optional[str]
    scores: dict = field(default_factory=dict)
    parsed: Optional[dict] = None
    raw_output: str = ''
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

def load_pairs(limit: Optional[int]=None):
    pairs = []
    with open(BENCH_FILE, encoding='utf-8') as f:
        for line in f:
            pairs.append(json.loads(line))
    if limit is not None:
        pairs = pairs[:limit]
    return pairs

def load_existing_predictions(path: Path):
    done = set()
    if path.exists():
        with open(path, encoding='utf-8') as f:
            for line in f:
                try:
                    done.add(json.loads(line)['pair_id'])
                except Exception:
                    pass
    return done

async def _call_one(client, cfg: RunConfig, pair: dict, sem: asyncio.Semaphore) -> Prediction:
    async with sem:
        if cfg.skip_context:
            context = ''
        else:
            context = read_context(pair['org_a_dir'], pair['org_b_dir'])
            if cfg.context_char_limit is not None and len(context) > cfg.context_char_limit:
                context = context[:cfg.context_char_limit]
        prompt = build_prompt(pair['task_type'], pair['org_a_name'], pair['org_b_name'], context, prompt_variant=cfg.prompt_variant)
        pred = Prediction(pair_id=pair['pair_id'], task_type=pair['task_type'], model=cfg.model_name, prediction=None)
        t0 = time.time()
        try:
            resp = await asyncio.wait_for(client.completions.create(model=cfg.model_name, prompt=prompt, max_tokens=cfg.max_tokens, temperature=cfg.temperature, top_p=cfg.top_p, extra_body={'top_k': cfg.top_k}), timeout=cfg.request_timeout)
            pred.latency_ms = (time.time() - t0) * 1000
            if resp.usage is not None:
                pred.input_tokens = resp.usage.prompt_tokens
                pred.output_tokens = resp.usage.completion_tokens
            raw = resp.choices[0].text or ''
            pred.raw_output = raw
            label, scores, parsed, err = parse_response(pair['task_type'], raw)
            pred.prediction = label
            pred.scores = scores
            pred.parsed = parsed
            pred.error = err
        except asyncio.TimeoutError:
            pred.error = f'timeout after {cfg.request_timeout}s'
            pred.latency_ms = (time.time() - t0) * 1000
        except APIError as e:
            pred.error = f'api_error: {e}'
        except Exception as e:
            pred.error = f'{type(e).__name__}: {e}'
        return pred

async def _run_async(cfg: RunConfig):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f'predictions_{cfg.out_name}.jsonl'
    done = load_existing_predictions(out_path)
    pairs = load_pairs(cfg.limit)
    todo = [p for p in pairs if p['pair_id'] not in done]
    print(f'[{cfg.out_name}] total={len(pairs)} done={len(done)} todo={len(todo)}')
    if not todo:
        return
    client = AsyncOpenAI(base_url=cfg.endpoint, api_key=cfg.api_key, timeout=cfg.request_timeout)
    sem = asyncio.Semaphore(cfg.concurrency)
    start = time.time()
    processed = 0
    with open(out_path, 'a', encoding='utf-8') as f:
        tasks = [asyncio.create_task(_call_one(client, cfg, p, sem)) for p in todo]
        for fut in asyncio.as_completed(tasks):
            pred = await fut
            f.write(json.dumps(pred.__dict__, ensure_ascii=False) + '\n')
            f.flush()
            processed += 1
            if processed % 20 == 0 or processed == len(todo):
                elapsed = time.time() - start
                rate = processed / elapsed if elapsed > 0 else 0
                eta = (len(todo) - processed) / rate if rate > 0 else float('inf')
                print(f'[{cfg.out_name}] {processed}/{len(todo)} rate={rate:.2f}/s eta={eta:.0f}s')

def run(cfg: RunConfig):
    asyncio.run(_run_async(cfg))
