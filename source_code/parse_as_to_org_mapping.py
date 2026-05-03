from as2org_pipeline.as2org_mapping.mapper import as_to_org_mapping
from as2org_pipeline.config import base_dir
import os
import logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename='logs/parse_as_to_org_pipeline.log', level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class HTTPRequestFilter(logging.Filter):

    def filter(self, record):
        return 'HTTP Request' not in record.getMessage()
if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addFilter(HTTPRequestFilter())
    with open('logs/parse_as_to_org_pipeline.log', 'w'):
        pass
    as_to_org_mapping(base_dir)
