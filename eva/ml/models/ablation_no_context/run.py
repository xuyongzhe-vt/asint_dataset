from common import RunConfig, run
if __name__ == '__main__':
    run(RunConfig(model_name='deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', out_name='deepseek_ablation_no_context', endpoint='http://localhost:8001/v1', max_tokens=2048, temperature=0.0, top_p=1.0, top_k=1, concurrency=8, skip_context=True))
