from common import RunConfig, run
if __name__ == '__main__':
    run(RunConfig(model_name='Qwen/Qwen2.5-7B-Instruct', out_name='qwen25_7b', endpoint='http://localhost:8001/v1', max_tokens=2048, temperature=0.0, top_p=1.0, top_k=1, concurrency=30))
