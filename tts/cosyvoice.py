import time
import numpy as np
import requests

from utils.logger import logger
from .base_tts import BaseTTS, State
from registry import register

# 本地 CosyVoice2-0.5B 流式服务客户端（服务端见 H:\tools\cosyvoice_api.py）
DEFAULT_SERVER = 'http://127.0.0.1:9880'


@register("tts", "cosyvoice")
class CosyVoiceTTS(BaseTTS):
    def txt_to_audio(self, msg: tuple[str, dict]):
        text, textevent = msg
        server = (getattr(self.opt, 'TTS_SERVER', '') or DEFAULT_SERVER).rstrip('/')
        t = time.time()
        try:
            res = requests.post(f'{server}/tts', json={'text': text, 'speed': 1.0},
                                stream=True, timeout=120)
        except Exception:
            logger.exception('cosyvoice tts request failed')
            return
        if res.status_code != 200:
            logger.error(f'cosyvoice tts http {res.status_code}: {res.text[:200]}')
            return

        sr = int(res.headers.get('X-Sample-Rate', self.sample_rate))
        carry = np.zeros(0, dtype=np.float32)
        first = True
        try:
            for raw in res.iter_content(chunk_size=8192):
                if self.state != State.RUNNING:
                    break
                if not raw:
                    continue
                a = np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768.0
                if sr != self.sample_rate:
                    import resampy
                    a = resampy.resample(a, sr, self.sample_rate).astype(np.float32)
                carry = np.concatenate([carry, a]) if carry.size else a
                while carry.shape[0] >= self.chunk:
                    ep = {}
                    if first:
                        ep = {'status': 'start', 'text': text}
                        first = False
                    ep.update(**textevent)
                    self.parent.put_audio_frame(carry[:self.chunk], ep)
                    carry = carry[self.chunk:]
        finally:
            res.close()

        # 尾部不足一帧补零
        if carry.size:
            pad = np.zeros(self.chunk - carry.shape[0], np.float32)
            self.parent.put_audio_frame(np.concatenate([carry, pad]), {})

        ep = {'status': 'end', 'text': text}
        ep.update(**textevent)
        self.parent.put_audio_frame(np.zeros(self.chunk, np.float32), ep)
        logger.info(f'-------cosyvoice tts time:{time.time()-t:.4f}s')
