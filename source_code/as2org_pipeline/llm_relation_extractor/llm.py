import asyncio
import logging
import os
import aiohttp
from langchain_core.documents import Document
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from as2org_pipeline.config import lkb_dir
from as2org_pipeline.lkb import get_context
from as2org_pipeline.llm_relation_extractor.prompt import prompt_template_single
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
llm_timeout = 300

class VLLMWrapper:

    def __init__(self, url='http://localhost:8001/v1/completions', temperature=0.0, max_tokens=1024):
        self.url = url
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def ainvoke(self, prompt: str):
        payload = {'prompt': prompt, 'temperature': self.temperature, 'max_tokens': self.max_tokens, 'top_p': 1.0, 'top_k': 1}
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=payload) as resp:
                status = resp.status
                response_json = await resp.json()
                if status != 200:
                    logging.warning(f'request status {status}, prompt: {payload}, result: {response_json}')
                return type('LLMResponse', (), {'content': response_json['choices'][0]['text']})

class State(TypedDict):
    base_org_name: str
    target_org_name: str
    context: List[Document]
    answer: str
    prompt: str

def build_graph():
    llm = VLLMWrapper()

    async def retrieve(state: State):
        snippets = get_context(lkb_dir, state['base_org_name'], state['target_org_name'])
        return {'context': [Document(page_content=s) for s in snippets]}

    async def generate(state: State):
        docs_content = '\n\n\t'.join((doc.page_content for doc in state['context']))
        prompt_text = prompt_template_single.format(base_org=state['base_org_name'], target_org=state['target_org_name'], context=docs_content)
        response = await asyncio.wait_for(llm.ainvoke(prompt_text), timeout=llm_timeout)
        return {'answer': response.content, 'prompt': prompt_text}
    graph_builder = StateGraph(State).add_sequence([retrieve, generate])
    graph_builder.add_edge(START, 'retrieve')
    return graph_builder.compile()
