import os
import logging

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

_api_key = os.environ.get("DEEPSEEK_API_KEY")
if not _api_key:
    raise RuntimeError(
        "环境变量 DEEPSEEK_API_KEY 未设置。"
        "请先设置: set DEEPSEEK_API_KEY=your_api_key"
    )


class _DeepSeekChatOpenAI(ChatOpenAI):

    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)

        response_dict = (
            response
            if isinstance(response, dict)
            else response.model_dump()
        )
        choices = response_dict.get("choices", [])

        for i, choice in enumerate(choices):
            if i >= len(result.generations):
                break
            msg_dict = choice.get("message", {})
            reasoning = msg_dict.get("reasoning_content", "")
            if reasoning:
                result.generations[i].message.additional_kwargs["reasoning_content"] = reasoning

        return result

    def _convert_chunk_to_generation_chunk(
        self, chunk, default_chunk_class, base_generation_info
    ):
        result = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )

        if result is not None and isinstance(result.message, AIMessageChunk):
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                reasoning = delta.get("reasoning_content", "")
                if reasoning:
                    result.message.additional_kwargs["reasoning_content"] = reasoning

        return result

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = self._convert_input(input_).to_messages()
        api_messages = payload.get("messages", [])

        ai_msg_iter = iter(m for m in messages if isinstance(m, AIMessage))
        for api_msg in api_messages:
            if api_msg.get("role") == "assistant":
                ai_msg = next(ai_msg_iter, None)
                if ai_msg:
                    reasoning = ai_msg.additional_kwargs.get("reasoning_content", "")
                    if reasoning:
                        api_msg["reasoning_content"] = reasoning

        return payload


llm = _DeepSeekChatOpenAI(
    model="deepseek-v4-pro",
    base_url="https://api.deepseek.com",
    api_key=_api_key,
    streaming=True,
)
