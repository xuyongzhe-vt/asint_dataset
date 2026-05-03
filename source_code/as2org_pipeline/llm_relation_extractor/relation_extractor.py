import asyncio
import json
import logging
import os
import re
import shutil
import time
import traceback
from multiprocessing import Manager
from as2org_pipeline.config import base_dir, lkb_dir
from as2org_pipeline.lkb import get_canonical_org_name, list_orgs, load_candidate_mentions
from as2org_pipeline.llm_relation_extractor.llm import build_graph
from as2org_pipeline.multi_process_support.cpu_worker import WorkerPool
org_batch_size = 100
worker_num = 8
single_process_req_limit = 5
retry_limit = 1
output_dir = base_dir + 'llm/classification/output/'

def sanitize_for_path(name):
    return re.sub('[<>:"/\\\\|?*]', '_', name)

def _strip_org_chars(s):
    return s.replace(',', '').replace('"', '').replace("'", '')

def _result_path(org_folder):
    return os.path.join(output_dir, org_folder, 'result.json')

def extract_relation_using_llm():
    graph = build_graph()
    llm_result_dict = {}
    for org_folder in list_orgs(lkb_dir):
        if os.path.exists(_result_path(org_folder)):
            continue
        candidate_org_list = [_strip_org_chars(m) for m in load_candidate_mentions(lkb_dir, org_folder)]
        base_org_name = _strip_org_chars(get_canonical_org_name(lkb_dir, org_folder))
        llm_result_dict[org_folder] = {}
        for candidate_org in candidate_org_list:
            llm_result_dict[org_folder][base_org_name, candidate_org] = ('', '')
    llm_org_items = list(llm_result_dict.items())
    for i in range(0, len(llm_org_items), org_batch_size):
        t = time.time()
        prev_count = len([d for d in os.listdir(output_dir) if os.path.exists(os.path.join(output_dir, d, 'result.json'))])
        process_org_llm_in_batch(llm_org_items[i:i + org_batch_size], graph)
        new_count = len([d for d in os.listdir(output_dir) if os.path.exists(os.path.join(output_dir, d, 'result.json'))])
        succ_rate = (new_count - prev_count) / org_batch_size
        logging.warning(f'INFO: progress {i + org_batch_size}/{len(llm_org_items)}, time spent {time.time() - t}. successful rate: {succ_rate}')

def process_org_llm_in_batch(llm_org_chunks, graph):
    manager = Manager()
    result_dict = manager.dict()
    empty_org = 0
    total_work = []
    for (org_folder, org_entry) in llm_org_chunks:
        result_dict[org_folder] = manager.dict()
        if len(org_entry) == 0:
            empty_org += 1
        for (base_org_name, candidate_org_name) in org_entry.keys():
            total_work.append((org_folder, base_org_name, candidate_org_name))
            result_dict[org_folder][base_org_name, candidate_org_name] = ('', '', '')
    logging.warning(f'current batch empty entries {empty_org}')
    worker_pool = WorkerPool(worker_num, total_work, extract_relation_per_process, [graph, result_dict])
    worker_pool.start_work()
    for (org_folder, llm_result) in result_dict.items():
        process_individual_llm_result(org_folder, llm_result)

def process_individual_llm_result(org_folder, llm_result):
    raw_result_sum = ''
    org_result = {'alias_list': [], 'parent_company_list': [], 'subsidiary_list': [], 'no_relationship_list': []}
    for ((base_org_name, candidate_org_name), (relation, parent, raw_result)) in llm_result.items():
        base_org_name = re.sub('[^a-zA-Z ]', '', base_org_name).strip().lower()
        candidate_org_name = re.sub('[^a-zA-Z ]', '', candidate_org_name).strip().lower()
        parent = re.sub('[^a-zA-Z ]', '', parent).strip().lower()
        raw_result_sum += raw_result
        if relation == '':
            logging.error(f'{(base_org_name, candidate_org_name)} error. relation is empty')
            return
        elif relation == 'Alias':
            org_result['alias_list'].append(candidate_org_name)
        elif relation == 'Parent/Subsidiary':
            if parent == base_org_name:
                org_result['subsidiary_list'].append(candidate_org_name)
            elif parent == candidate_org_name:
                org_result['parent_company_list'].append(candidate_org_name)
            else:
                logging.error(f'{(base_org_name, candidate_org_name, parent)} error. parent/subsidiary name is wrong')
                return
        elif relation == 'No_relation':
            org_result['no_relationship_list'].append(candidate_org_name)
        else:
            logging.error(f'{(base_org_name, candidate_org_name)} error. unknown relation')
            return
    candidate_org_list = [m.replace(',', '') for m in load_candidate_mentions(lkb_dir, org_folder)]
    if len(set(candidate_org_list)) != len(org_result['alias_list']) + len(org_result['parent_company_list']) + len(org_result['subsidiary_list']) + len(org_result['no_relationship_list']):
        logging.error(f'{org_folder} error. unmatched candidate org num')
        return
    org_output_dir = os.path.join(output_dir, org_folder)
    os.makedirs(org_output_dir, exist_ok=True)
    src_ori = os.path.join(lkb_dir, org_folder, 'ori_org_name.txt')
    dst_ori = os.path.join(org_output_dir, 'ori_org_name.txt')
    if os.path.exists(src_ori):
        shutil.copy(src_ori, dst_ori)
    with open(os.path.join(org_output_dir, 'result.json'), 'w', encoding='utf-8') as f:
        json.dump(org_result, f, indent=4, ensure_ascii=False)
    with open(os.path.join(org_output_dir, 'raw_prompt_result.txt'), 'w', encoding='utf-8') as f:
        f.write(raw_result_sum)

def extract_relation_per_process(work, extra_params):
    graph = extra_params[0]
    result_dict = extra_params[1]
    for i in range(0, len(work), single_process_req_limit):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_query_one_batch(work[i:i + single_process_req_limit], graph, result_dict))

async def async_query_one_batch(work_pairs, graph, result_dict):
    tasks = []
    for (org_folder, base_org_name, candidate_org) in work_pairs:
        tasks.append(async_query_one_single_pair(base_org_name, org_folder, candidate_org, graph, result_dict))
    await asyncio.gather(*tasks)

async def async_query_one_single_pair(base_org_name, org_folder, candidate_org_name, graph, llm_result_dict):
    tried = 0
    while tried < retry_limit:
        tried += 1
        try:
            result = await graph.ainvoke({'base_org_name': base_org_name, 'target_org_name': candidate_org_name})
            (pair_type, parent_name) = parse_result(result)
            llm_result_dict[org_folder][base_org_name, candidate_org_name] = (pair_type, parent_name, json.dumps(result['answer']))
            return
        except asyncio.TimeoutError:
            logging.warning(f'LLM request timeout: {candidate_org_name}')
        except Exception as e:
            logging.warning(f'async_query_one_single_pair error for {candidate_org_name}\n{traceback.format_exc()}: {e}')

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
                    try:
                        obj = json.loads(candidate)
                    except Exception:
                        logging.warning(candidate)
                        raise Exception(f'No valid JSON content: {text}')
                    required = {'base_org_name', 'candidate_org_name', 'reasoning for Alias', 'reasoning for Parent/Subsidiary', 'relationship', 'parent', 'parent name'}
                    if not required.issubset(obj.keys()):
                        raise Exception(f'Json attr missing {text}')
                    return obj
    raise Exception(f'No valid JSON content: {text}')

def parse_result(result_json):
    result = extract_first_json_object(result_json['answer'])
    relationship = result['relationship']
    base_org_name = result['base_org_name']
    candidate_org_name = result['candidate_org_name']
    if relationship == 'Alias':
        return ('Alias', '')
    elif relationship == 'Parent/Subsidiary':
        parent_org_type = result['parent']
        parent_org_name = result['parent name']
        if parent_org_type == 'candidate' and parent_org_name.lower() == candidate_org_name.lower():
            return ('Parent/Subsidiary', parent_org_name)
        elif parent_org_type == 'base' and parent_org_name.lower() == base_org_name.lower():
            return ('Parent/Subsidiary', parent_org_name)
        else:
            raise Exception(f'{(parent_org_name, candidate_org_name, base_org_name)} LLM parent/subsidiary inconsistency')
    elif relationship == 'No_relation':
        return ('No_relation', '')
    else:
        raise Exception('LLM result type error')
