from openai import OpenAI
from src.core.providers.base import BaseProvider
import json

class OpenAIProvider(BaseProvider):
    def __init__(self, api_key, base_url=None, model_name="gpt-4o"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        if not self._client:
            if not self.api_key:
                raise ValueError(f"API key for {self.base_url or 'OpenAI'} is missing.")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client
    
    def _sanitize_messages(self, messages):
        """Ensure tool call arguments are JSON strings for OpenAI API."""
        sanitized = []
        for msg in messages:
            msg_copy = msg.copy()
            if 'tool_calls' in msg_copy and msg_copy['tool_calls']:
                new_tool_calls = []
                for tc in msg_copy['tool_calls']:
                    tc_copy = tc.copy()
                    if 'function' in tc_copy:
                        func = tc_copy['function'].copy()
                        if isinstance(func.get('arguments'), dict):
                            func['arguments'] = json.dumps(func['arguments'])
                        tc_copy['function'] = func
                    new_tool_calls.append(tc_copy)
                msg_copy['tool_calls'] = new_tool_calls
            sanitized.append(msg_copy)
        return sanitized

    def generate_response(self, messages, tools=None):
        kwargs = {}
        if tools:
            kwargs['tools'] = tools
        
        response = self._get_client().chat.completions.create(
            model=self.model_name,
            messages=self._sanitize_messages(messages),
            **kwargs
        )
        return self._convert_to_ollama_format(response)

    def stream_response(self, messages, tools=None):
        kwargs = {'stream': True}
        if tools:
            kwargs['tools'] = tools
        
        stream = self._get_client().chat.completions.create(
            model=self.model_name,
            messages=self._sanitize_messages(messages),
            **kwargs
        )

        tool_calls = []
        
        for chunk in stream:
            # Handle content
            if chunk.choices and chunk.choices[0].delta.content:
                yield {
                    "message": {
                        "role": "assistant",
                        "content": chunk.choices[0].delta.content
                    }
                }
            
            # Handle tool calls aggregation
            if chunk.choices and chunk.choices[0].delta.tool_calls:
                tc_chunk_list = chunk.choices[0].delta.tool_calls
                for tc_chunk in tc_chunk_list:
                    if len(tool_calls) <= tc_chunk.index:
                        tool_calls.append({
                            "id": "", 
                            "type": "function", 
                            "function": {"name": "", "arguments": ""}
                        })
                    
                    tc = tool_calls[tc_chunk.index]
                    if tc_chunk.id:
                        tc["id"] += tc_chunk.id
                    if tc_chunk.function.name:
                        tc["function"]["name"] += tc_chunk.function.name
                    if tc_chunk.function.arguments:
                        tc["function"]["arguments"] += tc_chunk.function.arguments

        # If we collected tool calls, yield them in a final chunk
        if tool_calls:
            # Parse arguments from JSON string to Dict before yielding
            final_tool_calls = []
            for tc in tool_calls:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    print(f"Error parsing arguments for tool {tc['function']['name']}: {tc['function']['arguments']}")
                    args = {} # Fail soft
                
                final_tool_calls.append({
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": args
                    }
                })

            yield {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": final_tool_calls
                }
            }

    def _convert_to_ollama_format(self, response):
        message = response.choices[0].message
        res = {
            "message": {
                "role": message.role,
                "content": message.content or ""
            }
        }
        if message.tool_calls:
            res["message"]["tool_calls"] = []
            for tc in message.tool_calls:
                # Parse JSON arguments
                try:
                    args = json.loads(tc.function.arguments)
                except:
                    args = {}

                res["message"]["tool_calls"].append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": args
                    }
                })
        return res

    def list_models(self):
        try:
            if not self.api_key:
                return ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"]

            models = self._get_client().models.list()
            model_ids = [m.id for m in models]
            return sorted(model_ids, key=lambda x: (not x.startswith("gpt"), x))
        except Exception as e:
            print(f"Error listing OpenAI/Compatible models: {e}")
            return ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"]
