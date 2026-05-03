import os
base_dir = os.environ.get('BASE_DIR', '/path/to/pipeline/data/')
if not base_dir.endswith('/'):
    base_dir += '/'
lkb_dir = base_dir + 'lkb/'
