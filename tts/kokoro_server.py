# -*- coding: utf-8 -*-
"""
Kokoro-82M 中文 TTS 本地服务（供 liveTalking 主项目通过 tts/kokoro.py 调用）。

启动：
    python tts/kokoro_server.py

接口：
    POST /tts   {"text": "...", "voice": "zf_001", "speed": 1.0}
                -> 流式返回 16kHz / 单声道 / int16 裸 PCM，响应头带 X-Sample-Rate
    GET  /health
"""

import os
import time
from math import gcd
from threading import Lock

import numpy as np
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from scipy.signal import resample_poly

PORT = 9881
TARGET_SR = 16000
REPO_ID = 'hexgrad/Kokoro-82M-v1.1-zh'
DEFAULT_VOICE = 'zf_001'
VOICES = ['zf_001', 'zf_002', 'zf_003', 'zf_004', 'zf_005',
          'zm_009', 'zm_010', 'zm_011']

from kokoro import KPipeline  # noqa: E402

t0 = time.time()
pipeline = KPipeline(lang_code='z', repo_id=REPO_ID, device='cuda')
print(f'[kokoro] pipeline loaded in {time.time() - t0:.2f}s')

lock = Lock()
_voice_cache = {}


def synth(text: str, voice: str, speed: float):
    """逐段返回 24kHz float32 numpy 音频。"""
    with lock:
        for r in pipeline(text, voice=voice, speed=speed):
            if r.audio is None:
                continue
            yield r.audio.detach().cpu().numpy().astype(np.float32)


def to_pcm16k(a: np.ndarray) -> bytes:
    if a.ndim > 1:
        a = a.reshape(-1)
    if a.size == 0:
        return b''
    g = gcd(24000, TARGET_SR)
    a = resample_poly(a, TARGET_SR // g, 24000 // g).astype(np.float32)
    return (np.clip(a, -1.0, 1.0) * 32767).astype('<i2').tobytes()


# 预热：触发 jieba 词典加载 + cudnn 自动调优，避免首个音色首句慢
_t = time.time()
for _v in VOICES:
    for _ in synth('这是一段预热文本。', _v, 1.0):
        pass
print(f'[kokoro] warmup in {time.time() - _t:.2f}s')

app = FastAPI()


class TTSReq(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    speed: float = 1.0


@app.get('/health')
def health():
    import torch
    return {'ok': True, 'sr': 24000, 'cuda': torch.cuda.is_available(),
            'voice': DEFAULT_VOICE, 'voices': VOICES}


@app.post('/tts')
def tts(req: TTSReq):
    voice = (req.voice or DEFAULT_VOICE).strip()

    def gen():
        t = time.time()
        first = True
        try:
            for a in synth(req.text, voice, req.speed):
                if first:
                    print(f'[kokoro] first chunk {time.time() - t:.3f}s')
                    first = False
                pcm = to_pcm16k(a)
                if pcm:
                    yield pcm
        except Exception as e:  # noqa: BLE001
            print(f'[kokoro] synth error: {e!r}')
        print(f'[kokoro] total {time.time() - t:.3f}s | {req.text[:30]}')

    return StreamingResponse(gen(), media_type='application/octet-stream',
                             headers={'X-Sample-Rate': str(TARGET_SR)})


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=PORT, log_level='warning')
