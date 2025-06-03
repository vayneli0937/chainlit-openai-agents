from pydantic import BaseModel
import asyncio
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, ModelSettings,trace
from agents import set_default_openai_client, set_tracing_disabled
from dotenv import load_dotenv
import os
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
custom_client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
set_default_openai_client(custom_client)
set_tracing_disabled(True)

story_outline_agent = Agent(
    name="story_outline_agent",
    model=OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=custom_client
      
    ),
    instructions="Generate a very short story outline based on the user's input",
    model_settings=ModelSettings(temperature=0.7)
)

class OutlineCheckerOutput(BaseModel):
    goodquality: bool
    is_scify: bool
    
outline_checker_agent = Agent(
    name="outline_checker_agent",
    model=OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=custom_client,
        
    ),
    instructions="Read the given story outline, and judge the quality. Also, determine if it is a scifi story.",

    output_type=OutlineCheckerOutput,
)

story_agent=Agent(
    name="story_agent",
    model=OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=custom_client,
        
    ),
    instructions="Write a short story based on the given outline.",
    output_type=str

)

async def main():
    input_prompt = input("帮我写一个科幻寓言故事")
    with trace("Determinstic story flow"):
        outline_result = await Runner.run(story_outline_agent, input_prompt)
        print("outline generated")
        
        outline_checker_result = await Runner.run(
            outline_checker_agent,
            outline_result.final_output
        
        )
        print(outline_result.final_output,outline_checker_result.final_output)
        
        
        
        # assert isinstance(outline_checker_result.final_output, OutlineCheckerOutput)
        
        # if not outline_checker_result.final_output.goodquality:
        #     print("Outline is not good quality, so we stop here.")
        #     exit(0)
        # if not outline_checker_result.final_output.is_scify:
        #     print("Outline is not a scifi story, so we stop here.")
        #     exit(0)
            
        print("Outline is good quality and a scifi story, so we continue to write the story.")
        
        story_result=await Runner.run(story_agent, outline_result.final_output)
        
        print(f"story: {story_result.final_output}")
        
if __name__ == "__main__":
    asyncio.run(main())