import logging
from ner_tools.ner import extract_organizations
logging.basicConfig(filename='pipeline.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
if __name__ == '__main__':
    with open('pipeline.log', 'w'):
        pass
    extract_organizations('${NER_WORK_DIR}/input', '${NER_WORK_DIR}/output', '${NER_HOME}/org.json')
