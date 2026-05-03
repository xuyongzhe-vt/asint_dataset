import asyncio
import logging
import aiohttp
from langchain_core.documents import Document
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict
from as2org_pipeline.config import lkb_dir
from as2org_pipeline.lkb import get_pairwise_context
llm_timeout = 300

class State(TypedDict):
    org_a_name: str
    org_b_name: str
    context: List[Document]
    answer: str
    prompt: str

class VLLMWrapper:

    def __init__(self, url='http://localhost:8001/v1/completions', temperature=0.0, max_tokens=2048):
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

def build_graph(prompt):
    llm = VLLMWrapper()

    async def retrieve(state: State):
        snippets = get_pairwise_context(lkb_dir, state['org_a_name'], state['org_b_name'])
        return {'context': [Document(page_content=s) for s in snippets]}

    async def generate(state: State):
        docs_content = '\n\n\t'.join((doc.page_content for doc in state['context']))
        prompt_text = prompt.format(org_a=state['org_a_name'], org_b=state['org_b_name'], context=docs_content)
        response = await asyncio.wait_for(llm.ainvoke(prompt_text), timeout=llm_timeout)
        return {'answer': response.content, 'prompt': prompt_text}
    graph_builder = StateGraph(State).add_sequence([retrieve, generate])
    graph_builder.add_edge(START, 'retrieve')
    return graph_builder.compile()
