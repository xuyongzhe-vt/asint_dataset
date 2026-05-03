import argparse
import logging
import os
from as2org_pipeline.config import base_dir
from as2org_pipeline.crawler.processor import Processor

class HTTPRequestFilter(logging.Filter):

    def filter(self, record):
        return 'HTTP Request' not in record.getMessage()
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='logging file')
    parser.add_argument('--log_file', type=str, default='', help='Log file name')
    args = parser.parse_args()
    logger = logging.getLogger()
    logger.addFilter(HTTPRequestFilter())
    os.makedirs('logs', exist_ok=True)
    log_path = 'logs/' + args.log_file
    logging.basicConfig(filename=log_path, level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    with open(log_path, 'w'):
        pass
    processor = Processor(os.path.join(base_dir, 'crawling'))
    processor.crawl_urls()
    print('crawling done')
    processor.download_htmls()
    print('downloading done')
