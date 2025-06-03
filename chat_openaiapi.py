from openai import AsyncOpenAI
import chainlit as cl
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# cl.instrument_openai()
client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=api_key,
)

@cl.on_message
async def on_message(msg: cl.Message):
    res = cl.Message(content="")
    stream = await client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "you are a helpful assistant"},
            *cl.chat_context.to_openai(),
            
        
        ],
        stream=True,
    )
    
    async for event in stream:
        delta = event.choices[0].delta
        if delta:
            await res.stream_token(delta.content)
    await res.send()        
    
    
if __name__ == "__main__":
    on_message()