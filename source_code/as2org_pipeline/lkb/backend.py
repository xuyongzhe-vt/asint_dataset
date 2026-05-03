import os
from pymilvus import DataType, MilvusClient
COLLECTION = 'lkb_snippets'

def get_client(lkb_dir: str) -> MilvusClient:
    os.makedirs(lkb_dir, exist_ok=True)
    db_path = os.path.join(lkb_dir, 'milvus.db')
    client = MilvusClient(db_path)
    if not client.has_collection(COLLECTION):
        schema = MilvusClient.create_schema()
        schema.add_field('id', DataType.INT64, is_primary=True)
        schema.add_field('mention', DataType.VARCHAR, max_length=512)
        schema.add_field('text', DataType.VARCHAR, max_length=65535)
        schema.add_field('source_org', DataType.VARCHAR, max_length=512)
        schema.add_field('kind', DataType.VARCHAR, max_length=16)
        schema.add_field('vector', DataType.FLOAT_VECTOR, dim=2)
        index_params = MilvusClient.prepare_index_params()
        index_params.add_index(field_name='mention', index_type='INVERTED')
        index_params.add_index(field_name='vector', index_type='FLAT', metric_type='L2')
        client.create_collection(collection_name=COLLECTION, schema=schema, index_params=index_params)
    return client

def normalize_mention(m: str) -> str:
    return m.strip().lower()
