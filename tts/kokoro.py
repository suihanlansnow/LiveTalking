import time
import numpy as np
import requests

from utils.logger import logger
from .base_tts import BaseTTS, State
from registry import register

# 本地 Kokoro-82M 中文 TTS 客户端（服务端见 H:\tools\kokoro_api.py）
# 非自回归模型，一次前向出整句，RTF ~0.05，首包约 0.2s。
DEFAULT_SERVER = 'http://127.0.0.1:9881'
DEFAULT_VOICE = 'zf_001'


@register("tts", "kokoro")
class KokoroTTS(BaseTTS):
    def txt_to_audio(self, msg: tuple[str, dict]):
        text, textevent = msg
        server = (getattr(self.opt, 'TTS_SERVER', '') or DEFAULT_SERVER).rstrip('/')
        voice = getattr(self.opt, 'REF_FILE', '') or DEFAULT_VOICE
        speed = float(getattr(self.opt, 'tts_speed', 1.0) or 1.0)
        t = time.time()
        try:
            res = requests.post(f'{server}/tts',
                                json={'text': text, 'voice': voice, 'speed': speed},
                                stream=True, timeout=120)
        except Exception:
            logger.error(f'kokoro tts 服务不可用，请先启动: python H:\\tools\\kokoro_api.py')
            return
        if res.status_code != 200:
            logger.error(f'kokoro tts http {res.status_code}: {res.text[:200]}')
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
        logger.info(f'-------kokoro tts time:{time.time()-t:.4f}s')
