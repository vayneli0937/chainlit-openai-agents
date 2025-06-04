from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, ModelSettings, TResponseInputItem
import asyncio
from agents import set_default_openai_client, set_tracing_disabled
import mlflow.openai
from openai.types.responses import ResponseTextDeltaEvent
from dotenv import load_dotenv
load_dotenv()
import os
import chainlit as cl
from agents.mcp import MCPServer, MCPServerStdio
import mlflow

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: LLM api-key not found in environment variables.")

url = os.getenv("GEMINI_URL")
if not url:
    print("Warning: LLM api-key url not found in environment variables.")

# Get API key from environment variables
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
if not firecrawl_api_key:
    print("Warning: FIRECRAWL_API_KEY not found in environment variables. Using fallback method.")


# mlflow.openai.autolog()
# mlflow.set_tracking_uri("http://localhost:5000")
# mlflow.set_experiment("OpenAI")

@cl.password_auth_callback
def password_auth(username: str, password: str):
    if(username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin",
            display_name="vayne",
            metadata={"role": "admin", "provider": "credentials"}
        )
    return None


@cl.on_message
async def main(message: cl.Message):
    custom_client = AsyncOpenAI(
        api_key=api_key,
        base_url=url

    )
    
    set_default_openai_client(custom_client)
    set_tracing_disabled(True)
    res=cl.Message(content="")
    input_items = cl.user_session.get("input_items", [])
    user_input = message.content
    input_items.append({"content": user_input, "role": "user"})
    try:
        # 使用 OpenAIChatCompletionsModel 配置代理
        async def run(mcp_server1: MCPServer, mcp_server2: MCPServer):
            agent = Agent(
                name="Assistant",
                instructions="you use tools to answer questions",
                model=OpenAIChatCompletionsModel(
                    model="gemini-2.0-flash",
                    openai_client=custom_client,
                ),
                model_settings=ModelSettings(temperature=0.7),
                mcp_servers=[mcp_server1, mcp_server2],
            )
            
            result = Runner.run_streamed(
                starting_agent=agent,
                input=input_items)
            
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    delta = event.data.delta
                    if delta:
                        await res.stream_token(delta)
                        await res.send()                
            cl.user_session.set("input_items", result.to_input_list())
            

        async with MCPServerStdio(
            name="SequentialThinking MCP Server, via npx",
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
            }
        ) as sequential_thinking_server, MCPServerStdio(
            name="Firecrawl MCP Server",
            params={
                "command": "npx",
                "args": ["-y", "firecrawl-mcp"],
                "env": {
                    "FIRECRAWL_API_KEY": firecrawl_api_key
                }
            }
        ) as firecrawl_server:
            await run(sequential_thinking_server, firecrawl_server)
              
    except Exception as e:
        print(f"发生错误: {str(e)}")
        
    
'''
📘 Chainlit 项目中 input_items 管理知识点总结（文本版）
一、变量作用域 & 初始化位置
input_items 是用于保存用户-助手对话的上下文记录。

如果你在函数内部初始化它（如 input_items = []），每次函数调用都会重置它，无法保留上下文。

所以：

全局变量方式：初始化放在函数外（适合单用户测试）

推荐方式：使用 cl.user_session 存储上下文（支持多用户）

二、是否需要使用 global
当你在函数中修改函数外定义的变量（如 input_items.append(...)）时：

必须写 global input_items，否则 Python 会当作局部变量处理，导致出错或无效。

如果你完全在函数内部使用局部变量，则无需使用 global。

三、Chainlit 的 @cl.on_message 工作机制
@cl.on_message 是 Chainlit 的事件回调装饰器。

每当用户发来新消息，主函数（如 main(message)）就会重新执行。

所以不要在函数内使用 input_items = []，否则每次都重置对话上下文。

四、保留上下文的两种方法
方法一：使用全局变量（适合本地测试）
python
Copy
Edit
input_items = []

@cl.on_message
async def main(message):
    global input_items
    input_items.append({"role": "user", "content": message.content})
方法二：使用 cl.user_session（推荐，支持多用户）
python
Copy
Edit
@cl.on_message
async def main(message):
    input_items = cl.user_session.get("input_items", [])
    input_items.append({"role": "user", "content": message.content})
    cl.user_session.set("input_items", input_items)
五、input_items 的类型注解（TResponseInputItem）
原代码写法中使用了 input_items: list[TResponseInputItem]。

如果 TResponseInputItem 没有定义或导入，会导致类型错误。

解决方案：
简单方式（不写类型）：
python
Copy
Edit
input_items = cl.user_session.get("input_items", [])
标准方式（自定义类型）：
python
Copy
Edit
from typing import TypedDict

class TResponseInputItem(TypedDict):
    role: str
    content: str

input_items: list[TResponseInputItem] = cl.user_session.get("input_items", [])
六、总结建议
功能	推荐做法
单用户调试	使用全局变量
多用户对话管理	使用 cl.user_session
变量作用域	修改全局变量需加 global
对话上下文格式	使用 {"role": "user/assistant", "content": "..."}
类型标注	可自定义 TypedDict 类型用于提示

七、推荐主函数结构示例
python
Copy
Edit
@cl.on_message
async def main(message: cl.Message):
    # 获取当前用户会话上下文
    input_items = cl.user_session.get("input_items", [])

    # 添加用户输入
    input_items.append({"role": "user", "content": message.content})

    # 设置 LLM 和 Agent 执行过程（略）

    # 保存对话历史
    cl.user_session.set("input_items", input_items)

'''        
# if __name__ == "__main__":
#     asyncio.run(main())


# external_client = AsyncOpenAI(
#     api_key="AIzaSyB9q2IHi3djY_TuVaS_euD0Z-nUy8HvbCY",
#     base_url='https://generativelanguage.googleapis.com/v1beta'
# )

# chines_agent = Agent(
#     name="Chinese agent",
#     instructions='you are speak chinise'
#     model=OpenAIChatCompletionsModel(
#         model_name="gemini-2.0-flash",
#         openai_client=external_client,

#     ),
#     model_settings=model_settings()
# )


# if __name__ == "__main__":
#     main()
