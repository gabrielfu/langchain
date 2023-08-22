import json
from typing import Any, Iterator, List, Optional

from langchain.callbacks.manager import (
    CallbackManagerForLLMRun,
)
from langchain.chat_models.base import BaseChatModel
from langchain.llms.ollama import _OllamaCommon
from langchain.schema import ChatResult
from langchain.schema.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)
from langchain.schema.output import ChatGenerationChunk


def _stream_response_to_chat_generation_chunk(
    stream_response: str,
) -> ChatGenerationChunk:
    """Convert a stream response to a generation chunk."""
    parsed_response = json.loads(stream_response)
    generation_info = parsed_response if parsed_response.get("done") is True else None
    return ChatGenerationChunk(
        message=AIMessageChunk(content=parsed_response.get("response", "")),
        generation_info=generation_info,
    )


class ChatOllama(BaseChatModel, _OllamaCommon):
    """Ollama locally runs large language models.

    To use, follow the instructions at https://ollama.ai/.

    Example:
        .. code-block:: python

            from langchain.chat_models import ChatOllama
            ollama = ChatOllama(model="llama2")
    """

    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "ollama-chat"

    @property
    def lc_serializable(self) -> bool:
        return True

    def _format_message_as_text(self, message: BaseMessage) -> str:
        if isinstance(message, ChatMessage):
            message_text = f"\n\n{message.role.capitalize()}: {message.content}"
        elif isinstance(message, HumanMessage):
            message_text = f"[INST] {message.content} [/INST]"
        elif isinstance(message, AIMessage):
            message_text = f"{message.content}"
        elif isinstance(message, SystemMessage):
            message_text = f"<<SYS>> {message.content} <</SYS>>"
        else:
            raise ValueError(f"Got unknown type {message}")
        return message_text

    def _format_messages_as_text(self, messages: List[BaseMessage]) -> str:
        return "\n".join(
            [self._format_message_as_text(message) for message in messages]
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = self._format_messages_as_text(messages)
        final_chunk: Optional[ChatGenerationChunk] = None
        for stream_resp in self._create_stream(prompt, stop, **kwargs):
            if stream_resp:
                chunk = _stream_response_to_chat_generation_chunk(stream_resp)
                if final_chunk is None:
                    final_chunk = chunk
                else:
                    final_chunk += chunk
                if run_manager:
                    run_manager.on_llm_new_token(
                        chunk.text,
                        verbose=self.verbose,
                    )
        return ChatResult(generations=[final_chunk])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        prompt = self._format_messages_as_text(messages)
        for stream_resp in self._create_stream(prompt, stop, **kwargs):
            if stream_resp:
                chunk = _stream_response_to_chat_generation_chunk(stream_resp)
                yield chunk
                if run_manager:
                    run_manager.on_llm_new_token(
                        chunk.text,
                        verbose=self.verbose,
                    )
