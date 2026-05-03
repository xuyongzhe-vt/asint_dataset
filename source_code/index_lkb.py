from as2org_pipeline.config import base_dir, lkb_dir
from as2org_pipeline.lkb import insert_lkb
if __name__ == '__main__':
    insert_lkb(base_dir + 'llm/classification/unfinished/', lkb_dir)
