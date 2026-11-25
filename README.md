<p align="center">
    <img src="./assets/LiveTalking-logo.png" align="middle" width="600"/>
</p>

中文版 ｜ [English](./README-EN.md)

实时交互流式数字人引擎：文本/语音 → LLM（可选）→ TTS → 口型同步 → WebRTC/RTMP 推流。支持 ernerf、musetalk、wav2lip、Ultralight-Digital-Human 等模型。

**演示**：[wav2lip](https://www.bilibili.com/video/BV1scwBeyELA/) | [ernerf](https://www.bilibili.com/video/BV1G1421z73r/) | [musetalk](https://www.bilibili.com/video/BV1bUwezvEnG/)

**特性**：多模型切换 · 声音克隆 · 说话打断 · 全身视频拼接 · 多并发 · 动作编排 · 自定义形象 · 插件化扩展（[registry.py](registry.py)）· 本地离线 TTS（Kokoro / Piper）

---

## 1. 安装

```bash
git clone https://github.com/lipku/LiveTalking.git
conda create -n livetalking python=3.12
conda activate livetalking
# CUDA 版本不为 12.8 时（nvidia-smi 确认），按 https://pytorch.org/get-started/previous-versions 安装
pip install torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128
cd LiveTalking
pip install -r requirements.txt
```

常见问题：[FAQ](https://doc.livetalking.ai/docs/faq/)

## 2. 下载模型

| 网盘 | 地址 |
|------|------|
| 夸克云盘 | <https://pan.quark.cn/s/83a750323ef0> |
| Google Drive | <https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ?usp=sharing> |

1. `wav2lip256.pth` 放到 `models/`，重命名为 `wav2lip.pth`
2. `wav2lip256_avatar1.tar.gz` 解压后整个文件夹放到 `data/avatars/`

## 3. 启动

```bash
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
```

> 需开放端口 TCP:8010、UDP:1-65536

浏览器打开 `http://serverip:8010/index.html`，点击"开始连接"，在文本框输入文字即可。其他接入方式见 [API 文档](docs/api.md)。

页面：`/index.html` 连接与驱动 · `/avatar.html` 生成形象 · `/admin.html` 会话监控

## 4. 本地离线 TTS

默认 `kokoro`，完全离线。切换引擎改 `config.yaml` 的 `tts` 字段，可选值见 [avatars/base_avatar.py](avatars/base_avatar.py) 的 `_tts_modules`。

| 引擎 | `tts` 取值 | 首包 | 说明 |
|------|-----------|------|------|
| Kokoro-82M | `kokoro` | ~0.5s | 音色 `zf_001`~`zf_005`、`zm_009`~`zm_011`，推荐 |
| Piper | `piper` | ~0.3s | 单个 onnx 模型常驻内存，最轻量 |

Kokoro 需独立环境起 HTTP 服务（避免依赖冲突）：

```bash
pip install kokoro "misaki[zh]"          # 独立 venv，需 torch>=2.1
python tts/kokoro_server.py              # 默认 127.0.0.1:9881
```

```yaml
# config.yaml
tts: kokoro
REF_FILE: 'zf_001'                       # Kokoro 音色名
TTS_SERVER: 'http://127.0.0.1:9881'
```

Piper 无需额外服务，模型放到 `models/piper/zh_CN-huayan-medium.onnx`（或用 `piper_model` 指定），`tts` 改为 `piper`。

启动顺序：先起 TTS 服务，再起 `app.py`。

> 断句策略：只在句末标点（`。！？；`）切句，逗号不切；超过 30 字仍未遇句号时才回退到最近逗号软切。

## 5. 性能

`inferfps` = GPU 推理帧率，`finalfps` = 推流帧率，均需 ≥25。

| 模型 | 显卡 | FPS |
|:------|:------|:----|
| wav2lip256 | RTX 3060 | 60 |
| wav2lip256 | RTX 3080Ti | 120 |
| musetalk | RTX 3080Ti | 42 |
| musetalk | RTX 4090 | 72 |

**本机实测**（RTX 3070 8GB / Xeon E5-2696 v2 / Windows 11，Kokoro + wav2lip256，单路）：

| 项目 | 实测值 |
|------|--------|
| TTS 首包 / RTF | 0.47s / 0.08 |
| inferfps / finalfps | 41.5 / 25 |
| 显存占用 | 峰值 5.0GB / 8GB |
| 端到端出声延迟 | 0.6-0.8s |
| 日志报错 | 0 条 |

> CosyVoice2-0.5B 同机实测 RTF 2.6-4.5、首包 8-14s，无法实时。根因是该机 CPU 单次 CUDA kernel launch 约 71µs，自回归模型每 token 约 1100 次 launch，属硬件限制。

## 6. 架构

`/human` 接收文本（echo 复读 / chat LLM 对话），`/humanaudio` 直接播放音频，每个连接分配唯一 `sessionid`。
TTS 模块化输出音频 → 同步提取 Mel 频谱 → Wav2Lip/MuseTalk 生成口型 → 仅融合下半脸贴回原视频（保留头动眨眼）→ WebRTC/RTMP/虚拟摄像头输出。

<img src="./assets/dataflow.png" align="middle" />

## 7. 相关链接

- 文档：<https://doc.livetalking.ai> ｜ [业务 API](docs/api.md) ｜ [Avatar API](docs/avatar_api.md) ｜ [Admin API](docs/admin_api.md)
- Docker：[AutoDL](https://www.codewithgpu.com/i/lipku/livetalking/base) ｜ [UCloud](https://www.compshare.cn/images/4458094e-a43d-45fe-9b57-de79253befe4?referral_code=3XW3852OBmnD089hMMrtuU&ytag=GPU_GitHub_livetalking)
- Windows 整合包：<https://pan.quark.cn/s/a040bf5cb065> ｜ 商用版：<https://www.livetalking.top>
- 社区：[Telegram](https://t.me/livetalking) ｜ [Discord](https://discord.gg/n5jSPCT3Uf) ｜ 微信 wxwubug ｜ 邮箱 lipku@foxmail.com

基于本项目发布的视频需带上 LiveTalking 水印和标识。License: [Apache 2.0](./LICENSE)
