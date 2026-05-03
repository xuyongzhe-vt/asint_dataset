import os.path
from as2org_pipeline.as2org_mapping.mapper import as_to_org_mapping
from as2org_pipeline.config import base_dir
from as2org_pipeline.data_cleaner.cleaner import clean_html, recover_org_name_file
import logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename='logs/clean_html.log', level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class HTTPRequestFilter(logging.Filter):

    def filter(self, record):
        return 'HTTP Request' not in record.getMessage()
if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addFilter(HTTPRequestFilter())
    with open('logs/clean_html.log', 'w'):
        pass
    source_html_dir = os.path.join(base_dir, 'crawling/htmls')
    output_dir = os.path.join(base_dir, 'crawling/cleaned_content')
    os.makedirs(output_dir, exist_ok=True)
    recover_org_name_file(base_dir)
    clean_html(source_html_dir, output_dir)
