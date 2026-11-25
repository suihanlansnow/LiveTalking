import time
import os
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from avatars.base_avatar import BaseAvatar
from utils.logger import logger

# 模块加载时完成 openai/httpx 导入，避免首个请求额外等待 ~2s
import httpx
from openai import OpenAI

# Built-in LLM providers. Each exposes an OpenAI-compatible chat completions
# endpoint; the active one is selected with --llm_provider (default: dashscope).
LLM_PROVIDERS = {
    "dashscope": {
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
    "orcarouter": {
        "api_key_env": "ORCAROUTER_API_KEY",
        "base_url": "https://api.orcarouter.ai/v1",
        "default_model": "orcarouter/auto",
    },
    # 本地 Ollama（OpenAI 兼容），无需 API Key，默认 11434 端口
    "ollama": {
        "api_key_env": "OLLAMA_API_KEY",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
        "default_model": "qwen2.5:3b",
        "api_key": "ollama",
    },
}


def _llm_provider(opt) -> str:
    """Return the configured provider name, defaulting to dashscope."""
    return getattr(opt, 'llm_provider', 'dashscope') or 'dashscope'


_CLIENTS = {}


def _llm_client(opt):
    """Create (and cache) the OpenAI-compatible client for the configured provider."""
    provider = _llm_provider(opt)
    if provider in _CLIENTS:
        return _CLIENTS[provider]
    cfg = LLM_PROVIDERS.get(provider, LLM_PROVIDERS['dashscope'])
    kwargs = {}
    # 本地服务（Ollama 等）不能被系统代理接管，否则请求 127.0.0.1 会被代理返回 502
    if any(h in cfg['base_url'] for h in ('127.0.0.1', 'localhost')):
        kwargs['http_client'] = httpx.Client(trust_env=False)
    client = OpenAI(
        api_key=os.getenv(cfg['api_key_env']) or cfg.get('api_key'),
        base_url=cfg['base_url'],
        **kwargs,
    )
    _CLIENTS[provider] = client
    return client


def _llm_model(opt) -> str:
    """Resolve the model name, falling back to the provider default."""
    cfg = LLM_PROVIDERS.get(_llm_provider(opt), LLM_PROVIDERS['dashscope'])
    return getattr(opt, 'llm_model', '') or cfg['default_model']


def llm_response(message,avatar_session:'BaseAvatar',datainfo:dict={}):
    try:
        opt = avatar_session.opt
        start = time.perf_counter()
        client = _llm_client(opt)
        model = _llm_model(opt)
        end = time.perf_counter()
        logger.info(f"llm Time init: {end-start}s,{message}")
        completion = client.chat.completions.create(
            model=model,
            messages=[{'role': 'system', 'content': '你是一个知识助手，尽量以简短、口语化的方式输出'},
                    {'role': 'user', 'content': message}],
            stream=True,
            # Display token usage in the last line of the streamed response.
            stream_options={"include_usage": True}
        )
        result=""
        softpos = -1
        first = True
        for chunk in completion:
            if len(chunk.choices)>0:
                #print(chunk.choices[0].delta.content)
                if first:
                    end = time.perf_counter()
                    logger.info(f"llm Time to first chunk: {end-start}s")
                    first = False
                msg = chunk.choices[0].delta.content
                if msg is None:
                    continue
                # 只在句末标点切句，逗号不切（避免把一句话切碎导致韵律断裂）；
                # 超过 30 字还没遇到句号时，才退回到最后一个逗号处切，防止等太久不出声。
                SENT_END = '。！？；\n!?;'
                SOFT_END = '，,、：:'
                for char in msg:
                    result += char
                    if char in SENT_END:
                        if len(result.strip()) >= 2:
                            logger.info(result)
                            avatar_session.put_msg_txt(result, datainfo)
                            result = ''
                            softpos = -1
                    elif char in SOFT_END:
                        softpos = len(result)
                    if len(result) >= 30 and softpos > 0:
                        logger.info(result[:softpos])
                        avatar_session.put_msg_txt(result[:softpos], datainfo)
                        result = result[softpos:]
                        softpos = -1
        end = time.perf_counter()
        logger.info(f"llm Time to last chunk: {end-start}s")
        if result:
            avatar_session.put_msg_txt(result,datainfo)

    except Exception as e:
        logger.exception('llm exceptiopn:')
        return
