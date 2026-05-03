import logging
import os
from as2org_pipeline.multi_process_support.cpu_worker import WorkerPool
from bs4 import BeautifulSoup
import re
import shutil
import trafilatura
import json
worker_num = 30
min_word_count = 15

def sanitize(name: str) -> str:
    return re.sub('[<>:"/\\\\|?*]', '_', name)

def recover_org_name_file(base_dir):
    html_dir = os.path.join(base_dir, 'crawling/htmls')
    with open(os.path.join(base_dir, 'output/org.json'), 'r', encoding='utf-8') as file:
        org_entry = json.load(file)
    org_name_list = [entry['org_name'] for entry in org_entry]
    for org_name in org_name_list:
        org_path = os.path.join(html_dir, sanitize(org_name))
        output_path = os.path.join(org_path, 'ori_org_name.txt')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(org_name + '\n')
    check_ori_org_name_presence(base_dir)

def check_ori_org_name_presence(base_dir):
    checking_dir = os.path.join(base_dir, 'crawling/htmls')
    missing = []
    for entry in os.listdir(checking_dir):
        entry_path = os.path.join(checking_dir, entry)
        if os.path.isdir(entry_path):
            ori_file = os.path.join(entry_path, 'ori_org_name.txt')
            if not os.path.isfile(ori_file):
                missing.append(entry)
    if missing:
        print(f'{len(missing)} folders missing ori_org_name.txt:')
        for name in missing:
            print(f'  - {name}')
    else:
        print('✅ All folders contain ori_org_name.txt')

def clean_html(crawled_data_source_path: str, cleaned_dir: str):
    crawled_subdirs = set(os.listdir(crawled_data_source_path))
    cleaned_subdirs = set(os.listdir(cleaned_dir))
    missing = crawled_subdirs - cleaned_subdirs
    works = [os.path.join(crawled_data_source_path, name) for name in missing]
    logging.warning(f'num of work: {len(works)}')
    worker_pool = WorkerPool(worker_num, works, clean_all_html_in_folder, [cleaned_dir])
    worker_pool.start_work()

def clean_all_html_in_folder(dirty_org_dir_list: str, extra_params):
    cleaned_dir = extra_params[0]
    for dirty_org_dir in dirty_org_dir_list:
        dirty_org_name = os.path.basename(dirty_org_dir)
        (text_list, listing_list, table_list) = ([], [], [])
        for filename in os.listdir(dirty_org_dir):
            if filename == 'ori_org_name.txt':
                continue
            file_path = os.path.join(dirty_org_dir, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    (new_text_list, new_listing_list, new_table_list) = clean_individual_html(content)
                    text_list += new_text_list
                    listing_list += new_listing_list
                    table_list += new_table_list
        cleaned_org_dir_path = os.path.join(cleaned_dir, dirty_org_name)
        os.makedirs(cleaned_org_dir_path, exist_ok=True)
        with open(os.path.join(cleaned_org_dir_path, 'text.txt'), 'w') as text_file:
            for item in text_list:
                text_file.write(item + '\n')
        with open(os.path.join(cleaned_org_dir_path, 'listing.txt'), 'w') as listing_file:
            for item in listing_list:
                listing_file.write(item + '\n')
        with open(os.path.join(cleaned_org_dir_path, 'table.txt'), 'w') as table_file:
            for item in table_list:
                table_file.write(item + '\n')
        shutil.copy(os.path.join(dirty_org_dir, 'ori_org_name.txt'), os.path.join(cleaned_org_dir_path, 'ori_org_name.txt'))

def clean_individual_html(content: str):
    if content is None or content == '':
        return ([], [], [])
    try:
        soup = BeautifulSoup(content, 'xml')
    except Exception as e:
        logging.warning('exception ', e)
        return ([], [], [])
    last_header = None
    (text_list, listing_list, table_list) = ([], [], [])
    record_threshold = 2
    for element in soup.find('main').find_all(recursive=False):
        if element.name == 'p':
            paragraph = element.get_text(strip=True)
            text_list.append(paragraph)
            sentences = re.split('(?<=\\.)\\s+', paragraph)
            last_header = sentences[-1] if sentences else None
        elif element.name == 'head':
            header_text = element.get_text(strip=True)
            last_header = header_text
        elif element.name == 'list':
            list_items = [item.get_text(strip=True) for item in element.find_all('item')]
            if list_items:
                list_part = []
                part_count = 1
                for (i, item) in enumerate(list_items, 1):
                    list_part.append(item)
                    if len(list_part) >= record_threshold:
                        listing_list.append(f'LIST {last_header} (List Part {part_count}): {list_part}')
                        list_part = []
                        part_count += 1
                if list_part:
                    listing_list.append(f'LIST {last_header} (List Part {part_count}): {list_part}')
        elif element.name == 'table':
            rows = element.find_all('row')
            if len(rows) == 0:
                continue
            potential_header = [cell.get_text(strip=True) for cell in rows[0].find_all('cell')]
            if all((any((c.isalpha() for c in col)) for col in potential_header)):
                headers = potential_header
                data_start_idx = 1
            else:
                headers = [f'Column {i + 1}' for i in range(len(potential_header))]
                data_start_idx = 0
                table_list.append(f'TABLE {last_header}: [Table with no explicit header]')
            table_data = []
            table_count = 1
            for row in rows[data_start_idx:]:
                row_data = [cell.get_text(strip=True) for cell in row.find_all('cell')]
                if len(row_data) < len(headers):
                    row_data.extend([''] * (len(headers) - len(row_data)))
                record = {headers[i]: row_data[i] for i in range(len(headers))}
                table_data.append(record)
                if len(table_data) >= record_threshold:
                    table_list.append(f'TABLE {last_header} (Table Part {table_count}): {table_data}')
                    table_data = []
                    table_count += 1
            if table_data:
                table_list.append(f'TABLE {last_header} (Table Part {table_count}): {table_data}')
    filtered_text_list = [text for text in text_list if len(text.split()) >= min_word_count]
    return (filtered_text_list, listing_list, table_list)
