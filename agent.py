from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Annotated, Sequence
from operator import add as add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage
from dotenv import load_dotenv
from utils import (
    search_across_user_collections,
    search_in_collection,
    save_chat_history,
    load_chat_history,
    logger,
    get_similar_feedback_documents,
)

load_dotenv()
tools = [search_across_user_collections, search_in_collection]
llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
llm = llm.bind_tools(tools)

tool_dict = {tool.name: tool for tool in tools}


class RagAgent(TypedDict):
    user_id: str
    messages: Annotated[Sequence[BaseMessage], add_messages]


def build_system_prompt(
    user_id: str, available_tools: list[str] = None, extra_instructions: str = ""
) -> str:
    """
    Build a system prompt with user-specific context and tool descriptions.
    """
    tools_description = "\n".join(
        f"- {tool}: for searching documents as described in its docstring or functionality."
        for tool in (
            available_tools
            or ["search_across_user_collections", "search_in_collection"]
        )
    )

    return f"""
You are NeuroDesk, an intelligent AI assistant that helps users (currently user ID: {user_id}) find and understand information from their personal PDF document collections.

Your core responsibilities:
- Answer user questions by searching their uploaded documents for the most relevant information.
- Use the specialized tools provided in the `utils` module to perform all document retrieval and search operations. These tools include:
{tools_description}
- Always select the most appropriate tool for the user’s query. Use cross-collection search for general questions, and specific collection search when the user references a particular document.
- Always cite the document or collection name, and if possible, the section or page where the information was found.
- Summarize or quote the most relevant passages, rather than copying large blocks of text.
- Respect user privacy: only access and search documents belonging to the authenticated user (user_id: {user_id}).
- If a question cannot be answered from the available documents, politely inform the user and suggest uploading more relevant material if needed.
- If the user’s query is ambiguous or could refer to multiple documents, ask clarifying questions to narrow down the search.
- Provide clear, concise, and helpful answers, and avoid speculation beyond the content of the user’s documents.

Formatting guidelines:
- When citing, use the document or collection name and, if available, the section or page.
- If you use multiple sources, clearly indicate which information comes from which document.
- If you cannot find an answer, say so transparently and offer next steps.

{extra_instructions.strip()}

You are helpful, trustworthy, and always focused on providing the best possible information from the user’s own knowledge base.
""".strip()


def init_agent(state: RagAgent) -> RagAgent:
    """Initialize rag agent with user chat history if exists"""
    user_id = state["user_id"]
    chat_history = load_chat_history(user_id)
    logger.info(f"Loaded chat history for user {user_id}: {len(chat_history)} messages")
    state["messages"] = chat_history + list(state["messages"])
    return state


def rag_agent(state: RagAgent) -> RagAgent:
    """Rag agent that uses tools to answer user questions"""
    messages = list(state["messages"])
    last_message = state["messages"][-1]
    past_feedbacks = get_similar_feedback_documents(last_message.content)
    extra_instructions=""
    if past_feedbacks:
        logger.info(f"feedbacks: {len(past_feedbacks)}")
        extra_instructions = "\n Consider these past user feedbacks and generate better response. \n".join(
            [
                f"Feedback: {feedback.page_content}"
                for feedback in past_feedbacks
            ]
        )
    system_prompt = build_system_prompt(
        state["user_id"], tool_dict.keys(), extra_instructions
    )
    messages.append(SystemMessage(content=system_prompt))

    response = llm.invoke(messages)
    state["messages"] = messages + [response]
    return state


def retriever_agent(state: RagAgent) -> RagAgent:
    """Execute tool calls from ai response"""
    last_message = state["messages"][-1]
    response = []
    for tool_call in last_message.tool_calls:
        tool_call_id = tool_call["id"]
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        print(f"Calling {tool_name} with query: {tool_input}")

        if tool_name in tool_dict:
            result = tool_dict[tool_name].invoke(tool_input)
        else:
            print(f"Tool {tool_name} not found")
            result = f"Tool {tool_name} not found"
        response.append(
            ToolMessage(
                content=str(result), tool_call_id=tool_call_id, tool_name=tool_name
            )
        )
    print(f"Tool execution completed. Back to model")
    state["messages"] = response
    return state


def should_continue(state: RagAgent) -> RagAgent:
    """Check if the last message contains any tool calls"""
    last_message = state["messages"][-1]
    can_continue = (
        hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0
    )
    if not can_continue:
        save_chat_history(state["user_id"], state["messages"])
    return can_continue


graph = StateGraph(RagAgent)
graph.add_node("init_agent", init_agent)
graph.add_node("rag_agent", rag_agent)
graph.add_node("retriever_agent", retriever_agent)

graph.add_edge(START, "init_agent")
graph.add_edge("init_agent", "rag_agent")
graph.add_edge("retriever_agent", "rag_agent")
graph.add_conditional_edges(
    "rag_agent", should_continue, {True: "retriever_agent", False: END}
)

rag_ai = graph.compile()
