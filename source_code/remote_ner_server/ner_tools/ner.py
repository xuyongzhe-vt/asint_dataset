import os
import json
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from ner_tools.gpu_worker import GPUWorkerPool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ner_tools.embedding_based_filtering import construct_faiss, clean_up_org_name, filter_org_name_verbose, get_similar_name_list
from sentence_transformers import SentenceTransformer
import shutil
import re
import logging
import time
import traceback
import torch
from tqdm import tqdm

def sanitize_for_prompt(name: str) -> str:
    return re.sub('[<>:"/\\\\|?*,;]', '', name).strip()

def check_processed(org_name, base_dir):
    target_dir = os.path.join(base_dir, org_name)
    return os.path.exists(target_dir)

def extract_organizations(dirty_data_dir: str, cleaned_data_dir: str, org_name_list_path: str):
    org_name_and_dir_list = []
    all_dirty_dirs = os.listdir(dirty_data_dir)
    processed_dirs = set()
    if os.path.exists(cleaned_data_dir):
        processed_dirs = set(os.listdir(cleaned_data_dir))
    print(f'Found {len(all_dirty_dirs)} total directories. Checking for completion...')
    for org_dir in all_dirty_dirs:
        if org_dir in processed_dirs:
            success_marker = os.path.join(cleaned_data_dir, org_dir, 'ori_org_name.txt')
            if os.path.exists(success_marker):
                continue
            else:
                logging.warning(f'Found incomplete data for {org_dir}. Reprocessing.')
        try:
            with open(os.path.join(dirty_data_dir, org_dir, 'ori_org_name.txt'), 'r') as file:
                org_name = sanitize_for_prompt(file.readline().strip().lower())
            org_name_and_dir_list.append((org_name, org_dir))
        except FileNotFoundError:
            logging.error(f'Missing ori_org_name.txt in {org_dir}, skipping.')
            continue
    print(f'Resuming job. {len(org_name_and_dir_list)} directories left to process.')
    if len(org_name_and_dir_list) > 0:
        worker_pool = GPUWorkerPool(org_name_and_dir_list, process_ner_task, [dirty_data_dir, cleaned_data_dir, org_name_list_path], 1, 6)
        worker_pool.start_work()
    else:
        print('All tasks completed successfully. Nothing to process.')

def process_ner_task(org_name_and_dir_list: list[tuple[str, str]], gpu_index: int, extra_params: list[str]):
    dirty_data_dir = extra_params[0]
    cleaned_data_dir = extra_params[1]
    full_org_txt_path = extra_params[2]
    full_org_dict = {}
    with open(full_org_txt_path, 'r', encoding='utf-8') as file:
        full_org_list = json.load(file)
    for org_record in full_org_list:
        full_org_dict[sanitize_for_prompt(org_record['org_name'].lower())] = org_record
    print(len(full_org_dict))
    print('full org len')
    unique_full_org_names = clean_up_org_name(list(full_org_dict.keys()))
    (faiss_model, faiss_index) = construct_faiss(unique_full_org_names, gpu_index)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)
    model_name = 'dslim/bert-base-NER'
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    ner_model = AutoModelForTokenClassification.from_pretrained(model_name)
    ner_pipeline = pipeline('ner', model=ner_model, tokenizer=tokenizer, aggregation_strategy='simple', device=gpu_index)
    logging.info(f'Worker {os.getpid()} is assigned {len(org_name_and_dir_list)} works.')
    similarity_model = SentenceTransformer('all-MiniLM-L6-v2', device=f'cuda:{gpu_index}')
    counter = 0
    total_count = 0
    t = time.time()
    for (individual_org_name, individual_org_dir) in org_name_and_dir_list:
        try:
            dirty_org_dir_path = os.path.join(dirty_data_dir, individual_org_dir)
            cleaned_org_dir_path = os.path.join(cleaned_data_dir, individual_org_dir)
            web_crawled_text_list = []
            peering_db_text_list = []
            with open(os.path.join(dirty_org_dir_path, 'text.txt'), 'r') as file:
                for line in file.readlines():
                    split_content = text_splitter.split_text(line.strip())
                    web_crawled_text_list += split_content
            (web_potential_org_list, web_filtered_text_list, web_metadata_list) = extract_org_and_meta_from_str(individual_org_name, web_crawled_text_list, ner_pipeline, unique_full_org_names, faiss_model, faiss_index, similarity_model)
            print('web web_potential_org_list', web_potential_org_list)
            if 'notes' in full_org_dict[individual_org_name]:
                for notes in full_org_dict[individual_org_name]['notes']:
                    if notes.strip() != '':
                        cleaned_notes = notes.replace('\n', ' ').strip()
                        peering_db_text_list.append(cleaned_notes)
            (peering_db_potential_org_list, peering_db_filtered_text_list, peering_db_metadata_list) = extract_org_and_meta_from_str(individual_org_name, peering_db_text_list, ner_pipeline, unique_full_org_names, faiss_model, faiss_index, similarity_model)
            for aka in full_org_dict[individual_org_name]['aka']:
                if aka != '':
                    peering_db_potential_org_list.append(aka)
                    peering_db_filtered_text_list.append(f'{aka} is an alias of {individual_org_name}.')
                    peering_db_metadata_list.append([aka, individual_org_name])
            if 'cleaned_org_name' in full_org_dict[individual_org_name] and full_org_dict[individual_org_name]['cleaned_org_name'] != '':
                pre_llm_cleaned_name = [full_org_dict[individual_org_name]['cleaned_org_name']]
            else:
                pre_llm_cleaned_name = []
            total_potential_org_list = list(set(web_potential_org_list + pre_llm_cleaned_name + peering_db_potential_org_list))
            os.makedirs(cleaned_org_dir_path, exist_ok=True)
            print('mkdir ', cleaned_org_dir_path)
            with open(os.path.join(cleaned_org_dir_path, 'orgs.txt'), 'w') as file:
                for potential_org_name in total_potential_org_list:
                    file.write(potential_org_name + '\n')
            with open(os.path.join(cleaned_org_dir_path, 'web_text.txt'), 'w') as file:
                for text in web_filtered_text_list:
                    file.write(text + '\n')
            with open(os.path.join(cleaned_org_dir_path, 'web_meta.txt'), 'w') as file:
                for metadata in web_metadata_list:
                    file.write(' | '.join(metadata) + '\n')
            with open(os.path.join(cleaned_org_dir_path, 'peering_text.txt'), 'w') as file:
                for text in peering_db_filtered_text_list:
                    file.write(text + '\n')
            with open(os.path.join(cleaned_org_dir_path, 'peering_meta.txt'), 'w') as file:
                for metadata in peering_db_metadata_list:
                    file.write(' | '.join(metadata) + '\n')
            shutil.copy(os.path.join(dirty_org_dir_path, 'ori_org_name.txt'), os.path.join(cleaned_org_dir_path, 'ori_org_name.txt'))
            logging.info(f'proceed "{individual_org_name}" number of orgs {len(total_potential_org_list)}')
            counter += 1
            total_count += 1
            if counter == 50:
                counter = 0
                logging.info(f'worker {os.getpid()} progress {total_count} len {len(org_name_and_dir_list)}, time for cuurent batch {time.time() - t}')
                t = time.time()
        except Exception as e:
            error_message = traceback.format_exc()
            logging.error(f'Error processing {individual_org_name} at {individual_org_dir}, error {e}\nTraceback: {error_message}')

def extract_org_and_meta_from_str(org_name, text_list: list[str], ner_pipeline, unique_full_org_names, faiss_model, faiss_index, model):
    if len(text_list) == 0:
        return ([], [], [])
    potential_org_list = []
    filtered_text_list = []
    metadata_list = []
    unique_text_list = list(set(text_list))
    ner_result = ner_pipeline(unique_text_list)
    text_sum = 0
    for text in unique_text_list:
        text_sum += len(text)
    assert len(unique_text_list) == len(ner_result)
    for i in range(len(ner_result)):
        list_of_org = list(set([entity['word'].lower() for entity in ner_result[i] if entity['entity_group'] == 'ORG' and (not entity['word'].startswith('#'))]))
        list_of_org = [sanitize_for_prompt(org_name) for org_name in list_of_org]
        potential_org_list += list_of_org
    potential_org_set = set(potential_org_list)
    relevant_org = []
    print('potnetial org list: ', potential_org_set)
    if len(potential_org_set) != 0:
        (potential_org_set, _) = filter_org_name_verbose(org_name, list(potential_org_set), unique_full_org_names, faiss_model, faiss_index)
        print('potential_org_set ', potential_org_set)
        relevant_org = get_similar_name_list(org_name, list(potential_org_set), 0.6, model)
        print('relevant_org ', relevant_org)
    final_potential_org_list = []
    for i in range(len(unique_text_list)):
        list_of_org = list(set([entity['word'].lower() for entity in ner_result[i] if entity['entity_group'] == 'ORG' and (not entity['word'].startswith('#'))]))
        list_of_org = [sanitize_for_prompt(org_name) for org_name in list_of_org]
        if len(list_of_org) != 0:
            list_of_org = [org for org in list_of_org if org in potential_org_set and len(org) > 2]
        if len(list_of_org) < 2 or set([name for name in list_of_org]).isdisjoint(set(relevant_org)):
            continue
        if len(list_of_org) < 2:
            continue
        filtered_text_list.append(unique_text_list[i])
        metadata_list.append(list_of_org)
        final_potential_org_list += list_of_org
    return (list(set(final_potential_org_list)), filtered_text_list, metadata_list)
