from as2org_pipeline.config import base_dir
from as2org_pipeline.final_llm_judgement.final_judgement import final_cluster
from as2org_pipeline.post_processing.post_processing import post_process
import os
import logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename='logs/final_process.log', level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class HTTPRequestFilter(logging.Filter):

    def filter(self, record):
        return 'HTTP Request' not in record.getMessage()
if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addFilter(HTTPRequestFilter())
    with open('logs/final_process.log', 'w'):
        pass
    final_cluster(base_dir)
    post_process(base_dir)
