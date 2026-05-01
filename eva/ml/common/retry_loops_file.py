import asyncio
import json
import sys
from pathlib import Path
from openai import AsyncOpenAI
from common import BENCH_FILE, build_prompt, read_context, parse_response, OUTPUT_DIR
ENDPOINT = 'http://localhost:8001/v1'

async def call_once(client, model, pair, prompt_variant, skip_context):
    if skip_context:
        context = ''
    else:
        context = read_context(pair['org_a_dir'], pair['org_b_dir'])
    prompt = build_prompt(pair['task_type'], pair['org_a_name'], pair['org_b_name'], context, prompt_variant=prompt_variant)
    resp = await asyncio.wait_for(client.completions.create(model=model, prompt=prompt, max_tokens=2048, temperature=0.0, top_p=1.0, extra_body={'top_k': 1}), timeout=300)
    raw = resp.choices[0].text or ''
    label, scores, parsed, err = parse_response(pair['task_type'], raw)
    return {'pair_id': pair['pair_id'], 'task_type': pair['task_type'], 'model': model, 'prediction': label, 'scores': scores, 'parsed': parsed, 'raw_output': raw, 'input_tokens': resp.usage.prompt_tokens if resp.usage else None, 'output_tokens': resp.usage.completion_tokens if resp.usage else None, 'latency_ms': None, 'error': err}

async def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage: retry_loops_file.py <predictions_file.jsonl>')
    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = OUTPUT_DIR / path.name
    if not path.exists():
        raise SystemExit(f'No such file: {path}')
    recs = [json.loads(l) for l in open(path)]
    need = [i for i, r in enumerate(recs) if r.get('prediction') is None]
    if not need:
        print(f'{path.name}: 0 loops, nothing to do')
        return
    model = recs[0]['model']
    name = path.name.lower()
    prompt_variant = 'minimal' if 'minimal_prompt' in name else 'full'
    skip_context = 'no_context' in name
    print(f'{path.name}: {len(need)} loops; model={model}  prompt_variant={prompt_variant}  skip_context={skip_context}')
    pairs = {json.loads(l)['pair_id']: json.loads(l) for l in open(BENCH_FILE)}
    client = AsyncOpenAI(base_url=ENDPOINT, api_key='EMPTY', timeout=300.0)
    conc = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    sem = asyncio.Semaphore(conc)

    async def retry_one(idx):
        pid = recs[idx]['pair_id']
        pair = pairs.get(pid)
        if pair is None:
            return None
        async with sem:
            try:
                return (idx, await call_once(client, model, pair, prompt_variant, skip_context))
            except Exception as e:
                print(f'  retry {pid} failed: {e}')
                return None
    print(f'  retrying {len(need)} with concurrency={conc}')
    results = await asyncio.gather(*(retry_one(i) for i in need))
    retried = 0
    for r in results:
        if r is None:
            continue
        idx, new_rec = r
        recs[idx] = new_rec
        retried += 1
    with open(path, 'w') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'retried {retried} loops, rewrote {path.name}')
if __name__ == '__main__':
    asyncio.run(main())
