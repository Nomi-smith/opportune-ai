import os, httpx
from llm.base import BaseLLM
class OpenRouterLLM(BaseLLM):
    name='openrouter'
    def __init__(self,api_key,model=None): self.api_key=api_key; self.model=model or os.getenv('OPENROUTER_LLM_MODEL','openrouter/free')
    async def generate(self,prompt,system=''):
        payload={'model':self.model,'messages':[{'role':'system','content':system or 'You are a helpful assistant.'},{'role':'user','content':prompt}]}
        headers={'Authorization':f'Bearer {self.api_key}','HTTP-Referer':'https://opportune-ai.local','X-Title':'Opportune AI'}
        async with httpx.AsyncClient(timeout=12) as client:
            r=await client.post('https://openrouter.ai/api/v1/chat/completions',headers=headers,json=payload); r.raise_for_status(); return r.json()['choices'][0]['message']['content']
