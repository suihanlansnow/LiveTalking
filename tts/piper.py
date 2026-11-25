import os
import time
import numpy as np
from scipy.signal import resample_poly

from utils.logger import logger
from .base_tts import BaseTTS, State
from registry import register

# 本地离线 TTS（Piper / onnxruntime，CPU 即可）。
# 相比云端 EdgeTTS，首包延迟从 ~12s 降到 ~0.4s，且无网络依赖。
DEFAULT_MODEL = os.path.join('models', 'piper', 'zh_CN-huayan-medium.onnx')


@register("tts", "piper")
class PiperTTS(BaseTTS):
    def __init__(self, opt, parent):
        super().__init__(opt, parent)
        from piper import PiperVoice
        model_path = getattr(opt, 'piper_model', '') or DEFAULT_MODEL
        t = time.time()
        self.voice = PiperVoice.load(model_path)
        logger.info(f'piper model loaded in {time.time()-t:.3f}s: {model_path}')

    def txt_to_audio(self, msg: tuple[str, dict]):
        text, textevent = msg
        t = time.time()
        try:
            parts = []
            sample_rate = self.sample_rate
            for chunk in self.voice.synthesize(text):
                parts.append(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16))
                sample_rate = chunk.sample_rate
        except Exception:
            logger.exception('piper tts')
            return

        if not parts:
            logger.error('piper tts: empty audio')
            return

        stream = np.concatenate(parts).astype(np.float32) / 32768.0
        if sample_rate != self.sample_rate:
            # 22050 -> 16000 = 320 / 441，scipy 重采样无需 numba JIT，避免首句额外 ~1.8s
            stream = resample_poly(stream, 320, 441).astype(np.float32)
        logger.info(f'-------piper tts time:{time.time()-t:.4f}s')

        streamlen = stream.shape[0]
        idx = 0
        while streamlen >= self.chunk and self.state == State.RUNNING:
            eventpoint = {}
            streamlen -= self.chunk
            if idx == 0:
                eventpoint = {'status': 'start', 'text': text}
            elif streamlen < self.chunk:
                eventpoint = {'status': 'end', 'text': text}
            eventpoint.update(**textevent)
            self.parent.put_audio_frame(stream[idx:idx+self.chunk], eventpoint)
            idx += self.chunk
