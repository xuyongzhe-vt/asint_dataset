from as2org_pipeline.as2org_mapping.mapper import as_to_org_mapping
from as2org_pipeline.config import base_dir
from as2org_pipeline.llm_relation_extractor.relation_extractor import extract_relation_using_llm
import os
import logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename='logs/llm_classification.log', level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class HTTPRequestFilter(logging.Filter):

    def filter(self, record):
        return 'HTTP Request' not in record.getMessage()
if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addFilter(HTTPRequestFilter())
    with open('logs/llm_classification.log', 'w'):
        pass
    extract_relation_using_llm()
