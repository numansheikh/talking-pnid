from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Dict, Optional, List
from utils.config import load_config, load_prompts
from openai import OpenAI

# Global message history store for sessions
session_histories: Dict[str, List] = {}

def get_chat_model(config: Optional[Dict] = None) -> ChatOpenAI:
    """Create and return a LangChain ChatOpenAI model"""
    if config is None:
        config = load_config()
    
    api_key = config.get("openai", {}).get("apiKey", "")
    model_name = config.get("openai", {}).get("model", "gpt-4")
    max_tokens = config.get("settings", {}).get("maxTokens", 2000)
    temperature = config.get("settings", {}).get("temperature", 0.7)
    
    if not api_key:
        raise ValueError("OpenAI API key not found")
    
    return ChatOpenAI(
        openai_api_key=api_key,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )

def get_system_prompt_template(prompts: Optional[Dict] = None) -> str:
    """Get the system prompt content"""
    if prompts is None:
        prompts = load_prompts()
    
    system_prompt = (
        prompts.get("systemPrompt", {}).get("content") if prompts else None
    ) or (
        prompts.get("defaultSystemPrompt", {}).get("content") if prompts else None
    ) or "You are an expert assistant for Piping & Instrumentation Diagrams (P&IDs). Answer questions based on the provided markdown documentation and your knowledge of P&IDs."
    
    return system_prompt

def get_session_init_prompt(prompts: Optional[Dict] = None, count: int = 0) -> str:
    """Get the session initialization prompt"""
    if prompts is None:
        prompts = load_prompts()
    
    session_init_prompt = (
        prompts.get("sessionInitPrompt", {}).get("content") if prompts else None
    ) or "I'm starting a new session to discuss plant operations. Please acknowledge that you've received the plant data."
    
    return session_init_prompt.replace("{count}", str(count))

def get_message_history(session_id: str) -> List:
    """Get or create message history for a session"""
    if session_id not in session_histories:
        session_histories[session_id] = []
    return session_histories[session_id]

def clear_history(session_id: str):
    """Clear message history for a session"""
    if session_id in session_histories:
        del session_histories[session_id]

def add_to_history(session_id: str, human_message: str, ai_message: str):
    """Add messages to session history"""
    history = get_message_history(session_id)
    history.append(HumanMessage(content=human_message))
    history.append(AIMessage(content=ai_message))

def create_messages_with_history(system_prompt: str, user_input: str, session_id: str) -> List:
    """Create messages list with system prompt, history, and current input"""
    messages = [SystemMessage(content=system_prompt)]
    
    # Add conversation history
    history = get_message_history(session_id)
    messages.extend(history)
    
    # Add current user input
    messages.append(HumanMessage(content=user_input))
    
    return messages

def create_prompt_template(system_prompt: str) -> ChatPromptTemplate:
    """Create a LangChain prompt template"""
    system_template = SystemMessagePromptTemplate.from_template(system_prompt)
    human_template = HumanMessagePromptTemplate.from_template("{input}")
    
    return ChatPromptTemplate.from_messages([
        system_template,
        human_template,
    ])

def get_openai_client(config: Optional[Dict] = None) -> OpenAI:
    """Create and return an OpenAI client"""
    if config is None:
        config = load_config()
    
    api_key = config.get("openai", {}).get("apiKey", "")
    if not api_key:
        raise ValueError("OpenAI API key not found")
    
    return OpenAI(api_key=api_key)

def invoke_with_reasoning(client: OpenAI, model: str, messages: List[Dict], effort_level: str = "medium") -> str:
    """Invoke OpenAI API with reasoning models (o1/o3 or gpt-5.2)"""
    try:
        # Convert messages to the format expected by the API
        input_messages = []
        system_content = None
        
        for msg in messages:
            if hasattr(msg, 'content'):
                # LangChain message objects
                if isinstance(msg, SystemMessage):
                    system_content = msg.content
                else:
                    role = "user" if isinstance(msg, HumanMessage) else "assistant"
                    input_messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                # Already in dict format
                if msg.get("role") == "system":
                    system_content = msg.get("content")
                else:
                    input_messages.append(msg)
        
        # For o1/o3 models, use chat.completions.create
        # o1/o3 models don't support system messages, so prepend to first user message
        if model.startswith("o1") or model.startswith("o3"):
            # Prepend system message to first user message if present
            if system_content and input_messages and input_messages[0].get("role") == "user":
                input_messages[0]["content"] = f"{system_content}\n\n{input_messages[0]['content']}"
            
            response = client.chat.completions.create(
                model=model,
                messages=input_messages
            )
            return response.choices[0].message.content
        else:
            # For gpt-5.2, use responses.create
            response = client.responses.create(
                model=model,
                reasoning={"effort": effort_level},
                input=input_messages
            )
            return response.output_text
    except Exception as e:
        raise Exception(f"Error calling OpenAI API: {e}")
