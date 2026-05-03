from as2org_pipeline.config import base_dir
from as2org_pipeline.final_cluster.cluster import final_cluster
import os
import logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename='logs/pre_cluster.log', level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class HTTPRequestFilter(logging.Filter):

    def filter(self, record):
        return 'HTTP Request' not in record.getMessage()
if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addFilter(HTTPRequestFilter())
    with open('logs/pre_cluster.log', 'w'):
        pass
    final_cluster(base_dir)
