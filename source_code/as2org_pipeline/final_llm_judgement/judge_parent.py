import time
import os
import re
import json
import asyncio
import itertools
import logging
import traceback
from pathlib import Path
from as2org_pipeline.multi_process_support.cpu_worker import WorkerPool
from as2org_pipeline.final_llm_judgement.llm.llm import build_graph
from as2org_pipeline.final_llm_judgement.llm.prompt import parent_child_prompt
retry_limit = 1
batch_size = 20
worker_num = 10

def judge_parent_child(ori_base_dir, output_dir):
    with open(ori_base_dir + 'output/result_cliques_list.json', 'r', encoding='utf-8') as f:
        result_cliques = json.load(f)
    parsed_dict = {}
    for file in Path(output_dir).glob('*.json'):
        try:
            with file.open('r', encoding='utf-8') as f:
                data = json.load(f)
                a = data.get('org_a_name')
                b = data.get('org_b_name')
                if a and b:
                    parsed_dict[a, b] = True
                    parsed_dict[b, a] = True
        except Exception as e:
            print(f'Failed to read {file}: {e}')
    alias_id_to_orgs = {}
    for clique in result_cliques:
        for alias_group in clique['clique_alias_group_list']:
            alias_id_to_orgs[alias_group['alias_group_index']] = alias_group
    parent_pair_set = set()
    already_processed = 0
    for clique in result_cliques:
        for alias_group in clique['clique_alias_group_list']:
            if 'parent_alias_group_id' in alias_group:
                child_orgs = alias_group['organization_list']
                parent_orgs = alias_id_to_orgs[alias_group['parent_alias_group_id'][0]]['organization_list']
                for parent in parent_orgs:
                    for child in child_orgs:
                        name1 = parent['org_name']
                        name2 = child['org_name']
                        if name1 > name2:
                            (name1, name2) = (name2, name1)
                        if (name1, name2) in parsed_dict:
                            already_processed += 1
                            continue
                        parent_pair_set.add((name1, name2))
    parent_pair_list_to_judge = [list(pair) for pair in parent_pair_set]
    logging.warning(f'Num of already processed parent-child pairs: {already_processed}')
    logging.warning(f'Num of parent-child pairs to parse: {len(parent_pair_list_to_judge)}')
    graph = build_graph(parent_child_prompt)
    for i in range(0, len(parent_pair_list_to_judge), batch_size):
        t = time.time()
        before_count = len(os.listdir(output_dir))
        worker_pool = WorkerPool(worker_num, parent_pair_list_to_judge[i:i + batch_size], judge_per_process, [graph, output_dir])
        worker_pool.start_work()
        after_count = len(os.listdir(output_dir))
        rate = (after_count - before_count) / batch_size
        elapsed = time.time() - t
        remaining_batches = (len(parent_pair_list_to_judge) - (i + batch_size)) / batch_size
        est_remaining_time = remaining_batches * elapsed
        logging.warning(f'progress {i + batch_size}/{len(parent_pair_list_to_judge)}, \nbefore: {before_count}, after: {after_count}, successful rate {rate:.2f}, estimated time left: {est_remaining_time:.1f}s')

def judge_per_process(alias_list, extra_params):
    graph = extra_params[0]
    output_dir = extra_params[1]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_query_one_batch(alias_list, graph, output_dir))

async def async_query_one_batch(alias_list, graph, output_dir):
    tasks = []
    for (org_a, org_b) in alias_list:
        tasks.append(async_query_one_single_pair(org_a, org_b, graph, output_dir))
    await asyncio.gather(*tasks)

def sanitize_filename(name: str) -> str:
    return re.sub('[<>:"/\\\\|?*]', '_', name)

async def async_query_one_single_pair(org_a, org_b, graph, output_dir):
    tried = 0
    while tried <= retry_limit:
        tried += 1
        try:
            result = await graph.ainvoke({'org_a_name': org_a, 'org_b_name': org_b})
            (A_is_parent_of_B_Score, B_is_parent_of_A_Score, No_Relationship_Score, explanation, raw_prompt) = parse_result(result)
            result_to_store = {'org_a_name': org_a, 'org_b_name': org_b, 'A_is_parent_of_B_Score': A_is_parent_of_B_Score, 'B_is_parent_of_A_Score': B_is_parent_of_A_Score, 'No_Relationship_Score': No_Relationship_Score, 'explanation': explanation, 'raw_prompt': raw_prompt}
            org_a_safe = sanitize_filename(org_a)
            org_b_safe = sanitize_filename(org_b)
            filename = f'{org_a_safe}__{org_b_safe}.json'
            output_path = Path(output_dir + filename)
            with output_path.open('w', encoding='utf-8') as f:
                json.dump(result_to_store, f, indent=2, ensure_ascii=False)
            return
        except asyncio.TimeoutError:
            exception_message = f'LLM request timeout: {org_a} - {org_b}'
            logging.warning(exception_message)
        except Exception as e:
            error_message = traceback.format_exc()
            exception_message = f'async_query_one_single_pair error for {org_a} - {org_b} \n: {error_message}: {e}'
            logging.warning(exception_message)

def extract_first_json_object(text):
    stack = []
    start = None
    for (i, c) in enumerate(text):
        if c == '{':
            if not stack:
                start = i
            stack.append('{')
        elif c == '}':
            if stack:
                stack.pop()
                if not stack and start is not None:
                    candidate = text[start:i + 1]
                    obj = json.loads(candidate)
                    if 'A_is_parent_of_B_Score' not in obj or 'B_is_parent_of_A_Score' not in obj or 'No_Relationship_Score' not in obj or ('Explanation' not in obj):
                        raise Exception(f'Json attr missing {text}')
                    return obj
    raise Exception(f'No valid JSON content: {text}')

def parse_result(result):
    result = extract_first_json_object(result['answer'])
    return (result['A_is_parent_of_B_Score'], result['B_is_parent_of_A_Score'], result['No_Relationship_Score'], result['Explanation'], result)
