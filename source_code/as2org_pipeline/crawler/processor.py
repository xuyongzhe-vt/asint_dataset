import logging
import os
import json
import re
import shutil
from typing import List
from multiprocessing import Process
from as2org_pipeline.crawler.search_engine import search_key_word
from as2org_pipeline.crawler.html_downloader import HtmlDownloader
MAX_PROCESSES = 30
html_file_threshold = 8

def sanitize(name: str) -> str:
    return re.sub('[<>:"/\\\\|?*]', '_', name)

def _wait(procs) -> None:
    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        logging.warning('Interrupted. Terminating children…')
        for p in procs:
            if p.is_alive():
                p.terminate()
        for p in procs:
            p.join()

class Processor:

    def __init__(self, crawling_dir):
        self.orgs_needs_downloading_html = None
        self.html_storing_dir = None
        self.crawling_dir = crawling_dir
        org_file = os.path.join(crawling_dir, 'org.json')
        with open(org_file, 'r', encoding='utf-8') as infile:
            data = json.load(infile)
        self.total_org = [org['org_name'] for org in data]
        logging.warning(f'{len(self.total_org)} total orgs.')
        self.urls_dir = os.path.join(crawling_dir, 'urls')
        os.makedirs(self.urls_dir, exist_ok=True)
        self.org_to_crawl_url = []

    def crawl_urls(self):
        self.org_to_crawl_url = []
        for org in self.total_org:
            filename = f'{sanitize(org)}_crawl_results.json'
            filepath = os.path.join(self.urls_dir, filename)
            if not os.path.exists(filepath):
                self.org_to_crawl_url.append(org)
        logging.warning(f'{len(self.org_to_crawl_url)} orgs still need URL crawling.')
        if len(self.org_to_crawl_url) == 0:
            return
        procs: List[Process] = []
        chunk = (len(self.org_to_crawl_url) + MAX_PROCESSES - 1) // MAX_PROCESSES
        for i in range(0, len(self.org_to_crawl_url), chunk):
            p = Process(target=self._crawl_worker_func, args=(self.org_to_crawl_url[i:i + chunk],))
            p.start()
            procs.append(p)
            logging.warning('Spawned crawl worker pid=%s (%d orgs)', p.pid, len(self.org_to_crawl_url[i:i + chunk]))
        _wait(procs)

    def _crawl_worker_func(self, org_list: list[str]):
        total = len(org_list)
        for (idx, org) in enumerate(org_list, start=1):
            try:
                kws = ['Wikipedia', 'is acquired', 'parent company', 'historical name and alias']
                res = search_key_word(org, kws)
                out_path = os.path.join(self.crawling_dir, 'urls', f'{sanitize(org)}_crawl_results.json')
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(res, f, indent=2)
                logging.info('Crawled %s → %s', org, out_path)
                if idx % 100 == 0 or idx == total:
                    logging.warning('Worker %s progress: %d/%d orgs (%.1f%%)', os.getpid(), idx, total, 100 * idx / total)
            except Exception:
                logging.exception('Failed to crawl %s', org)

    def download_htmls(self):
        self.html_storing_dir = os.path.join(self.crawling_dir, 'htmls')
        os.makedirs(self.html_storing_dir, exist_ok=True)
        self.orgs_needs_downloading_html = []
        for org in self.total_org:
            sub_dir = os.path.join(self.html_storing_dir, sanitize(org))
            if not os.path.exists(sub_dir):
                self.orgs_needs_downloading_html.append(org)
                continue
            html_files = [f for f in os.listdir(sub_dir) if f.endswith('.html') and os.path.isfile(os.path.join(sub_dir, f))]
            if len(html_files) < html_file_threshold:
                shutil.rmtree(sub_dir)
                self.orgs_needs_downloading_html.append(org)
        logging.warning(f'{len(self.orgs_needs_downloading_html)} orgs need HTML downloading (threshold={html_file_threshold}).')
        for org_to_download in self.orgs_needs_downloading_html:
            storing_dir = os.path.join(self.html_storing_dir, sanitize(org_to_download))
            os.makedirs(storing_dir, exist_ok=True)
        if len(self.orgs_needs_downloading_html) == 0:
            return
        procs: List[Process] = []
        chunk = (len(self.orgs_needs_downloading_html) + MAX_PROCESSES - 1) // MAX_PROCESSES
        for i in range(0, len(self.orgs_needs_downloading_html), chunk):
            p = Process(target=self.scrape_worker_func, args=(self.orgs_needs_downloading_html[i:i + chunk],))
            p.start()
            procs.append(p)
            logging.warning('Spawned crawl worker pid=%s (%d orgs)', p.pid, len(self.orgs_needs_downloading_html[i:i + chunk]))
        _wait(procs)

    def scrape_worker_func(self, org_list: list[str]):
        downloader = HtmlDownloader(len(org_list))
        for org in org_list:
            try:
                url_path = os.path.join(self.crawling_dir, 'urls', f'{sanitize(org)}_crawl_results.json')
                output_dir = os.path.join(self.crawling_dir, 'htmls', sanitize(org))
                os.makedirs(output_dir, exist_ok=True)
                with open(url_path, 'r') as file:
                    urls_json = json.load(file)
                for (keywords, urls) in urls_json.items():
                    counter = 1
                    for url in urls:
                        try:
                            content = downloader.crawl_webpage(url)
                            if content:
                                keyword_base = sanitize(keywords)
                                output_path = os.path.join(output_dir, f'{keyword_base}_{counter}.html')
                                with open(output_path, 'w', encoding='utf-8') as out_file:
                                    out_file.write(content)
                                counter += 1
                        except Exception as e:
                            logging.error('Failed to crawl URL %s for org %s: %s', url, org, e)
            except Exception as e:
                logging.error('Failed to process org %s: %s', org, e)
        downloader.close()
