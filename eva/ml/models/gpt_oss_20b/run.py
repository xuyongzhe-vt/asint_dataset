\
\
\
\
\
\
   
from common import RunConfig, run

if __name__ == "__main__":
                                                                           
    run(RunConfig(
        model_name="openai/gpt-oss-20b",
        out_name="gpt_oss_20b",
        endpoint="http://localhost:8001/v1",
        max_tokens=2048,
        temperature=0.0,
        top_p=1.0,
        top_k=1,
        concurrency=4,
    ))
