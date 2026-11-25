<p align="center">
    <img src="./assets/LiveTalking-logo.png" align="middle" width="600"/>
</p>

中文版 ｜ [English](./README-EN.md)

<p align="center">
    <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache%202-dfd.svg"></a>
    <a href=""><img src="https://img.shields.io/badge/python-3.10+-aff.svg"></a>
    <a href=""><img src="https://img.shields.io/badge/os-linux%2C%20win%2C%20mac-pink.svg"></a>
</p>

实时交互流式数字人引擎，实现音视频同步对话。

**效果演示**: [wav2lip](https://www.bilibili.com/video/BV1scwBeyELA/) | [ernerf](https://www.bilibili.com/video/BV1G1421z73r/) | [musetalk](https://www.bilibili.com/video/BV1bUwezvEnG/)

<details>
<summary>❤️赞助商</summary>

- [PackyCode](https://www.packyapi.ai/register?aff=4gqz) — 稳定高效的 API 中转服务商，一句话接入主流大模型
- [APIMart](https://go.apimart.ai/tw-livetalking) — AI 图片/视频生成低价 API 平台，GPT-Image-2 低至 $0.006/张

</details>

---

## 简介

用户输入文字/音频 → LLM 生成回复（可选）→ TTS 合成语音 → 数字人实时口型同步 → 音视频推流输出。

**适用场景**：虚拟主播 / AI 客服 / 在线教育 / 大屏讲解 / 短视频批量制作。

**特性**

1. 支持多种数字人模型: ernerf、musetalk、wav2lip、Ultralight-Digital-Human
2. 支持声音克隆、全身视频拼接、说话打断
3. 支持 WebRTC、RTMP、虚拟摄像头输出，支持多并发
4. 支持动作编排：不说话时播放自定义视频
5. 支持本地离线 TTS（Kokoro / Piper），无需联网、无需 API Key
6. 基于 [registry.py](registry.py) 的插件机制，可自行扩展 TTS、Avatar、Output 模块

---

## 1. 安装

已在 Ubuntu 22.04、Python 3.12、PyTorch 2.9.1、CUDA 12.8 测试通过。

```bash
git clone https://github.com/lipku/LiveTalking.git
conda create -n livetalking python=3.12
conda activate livetalking
# CUDA 版本不为 12.8 时（运行 nvidia-smi 确认），请按 https://pytorch.org/get-started/previous-versions 安装
pip install torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128
cd LiveTalking
pip install -r requirements.txt
```

安装常见问题见 [FAQ](https://doc.livetalking.ai/docs/faq/)。

---

## 2. 快速开始

### 2.1 下载模型

| 网盘 | 地址 |
|------|------|
| 夸克云盘 | <https://pan.quark.cn/s/83a750323ef0> |
| Google Drive | <https://drive.google.com/drive/folders/1FOC_MD6wdogyyX_7V1d4NDIO7P9NlSAJ?usp=sharing> |

1. `wav2lip256.pth` 放到 `models/` 目录，重命名为 `wav2lip.pth`
2. `wav2lip256_avatar1.tar.gz` 解压后整个文件夹放到 `data/avatars/`

### 2.2 启动服务

```bash
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
```

> 服务端需开放端口 TCP:8010、UDP:1-65536

### 2.3 客户端接入

| 方式 | 说明 |
|------|------|
| 浏览器 | 打开 `http://serverip:8010/index.html`，点击"开始连接"，在文本框输入文字提交 |
| API | 参考 [docs/api.md](docs/api.md) |
| 桌面客户端 | <https://pan.quark.cn/s/d7192d8ac19b> |

Web 页面：`/index.html` 连接与驱动、`/avatar.html` 生成形象、`/admin.html` 会话监控。

<img src="./assets/index.jpg" align="middle"/>

### 2.4 本地离线 TTS

本分支默认使用 `kokoro`（完全离线）。切换其他引擎只需改 `config.yaml` 的 `tts` 字段，可选值见 [avatars/base_avatar.py](avatars/base_avatar.py) 中的 `_tts_modules`。

| 引擎 | `tts` 取值 | 首包延迟 | 说明 |
|------|-----------|---------|------|
| Kokoro-82M | `kokoro` | ~0.5s | 中文音色 `zf_001`~`zf_005`、`zm_009`~`zm_011`，音质明显优于 Piper，推荐 |
| Piper | `piper` | ~0.3s | 单个 onnx 模型常驻内存，最轻量 |

Kokoro 需独立环境运行 HTTP 服务（避免与主项目依赖冲突）：

```bash
pip install kokoro "misaki[zh]"          # 独立 venv，需 torch>=2.1
python tts/kokoro_server.py              # 服务端，默认 127.0.0.1:9881
```

`config.yaml`：

```yaml
tts: kokoro
REF_FILE: 'zf_001'                        # Kokoro 音色名
TTS_SERVER: 'http://127.0.0.1:9881'
```

Piper 无需额外服务，把模型放到 `models/piper/zh_CN-huayan-medium.onnx`（或用 `piper_model` 指定路径），`tts` 改为 `piper`。

启动顺序：先起 TTS 服务，再起 `app.py`。

> 断句策略：`llm.py` 只在句末标点（`。！？；`）处切句，逗号不切分；超过 30 字仍未遇到句号时才回退到最近的逗号处软切。

### 2.5 在线体验

- [UCloud 镜像](https://www.compshare.cn/images/4458094e-a43d-45fe-9b57-de79253befe4?referral_code=3XW3852OBmnD089hMMrtuU&ytag=GPU_GitHub_livetalking)
- Windows 整合包 <https://pan.quark.cn/s/a040bf5cb065>
- 商用版体验 <https://www.livetalking.top>
- 使用文档 <https://doc.livetalking.ai>

---

## 3. 性能指标

`inferfps` = GPU 推理帧率，`finalfps` = 最终推流帧率，两者均需 >= 25 才算实时。

### 3.1 实时推理性能（官方）

| 模型 | 显卡 | FPS |
|:------|:------|:----|
| wav2lip256 | RTX 3060 | 60 |
| wav2lip256 | RTX 3080Ti | 120 |
| musetalk | RTX 3080Ti | 42 |
| musetalk | RTX 3090 | 45 |
| musetalk | RTX 4090 | 72 |

wav2lip256 推荐 RTX 3060 及以上，musetalk 推荐 RTX 3080Ti 及以上。

### 3.2 本机实测（Kokoro + wav2lip256）

测试环境：RTX 3070 8GB、Xeon E5-2696 v2、Windows 11、单路会话。

| 项目 | 实测值 |
|------|--------|
| TTS 首包延迟（Kokoro 中文） | 0.43 - 0.50s，均值 **0.47s** |
| TTS RTF | 0.067 - 0.094，均值 **0.08** |
| 推理帧率 inferfps | 37.6 - 43.6，均值 **41.5** |
| 推流帧率 finalfps | 稳定 **25** |
| 显存占用（Wav2Lip + Kokoro） | 峰值约 **5.0GB / 8GB** |
| 端到端出声延迟 | 约 **0.6 - 0.8s** |
| 日志报错 | 0 条 |

结论：渲染侧有约 40% 余量，TTS 不再是瓶颈。

> 参考：CosyVoice2-0.5B 在同机实测 RTF 2.6-4.5（首包 8-14s），无法实时。根因不是 GPU 算力（fp16 matmul 17.9 TFLOPS 正常），而是该机 CPU 单次 CUDA kernel launch 开销约 71µs，自回归模型每 token 需约 1100 次 kernel launch，属于硬件限制。

---

## 4. 系统架构

<img src="./assets/dataflow.png" align="middle" />

**API 层**：`/human` 接收文本（echo 复读 / chat LLM 对话），`/humanaudio` 接收音频直接播放；每个连接分配唯一 `sessionid`。

**逻辑层**：LLM 生成回复；TTS 模块化（EdgeTTS、Piper、Kokoro、GPT-SoVITS、CosyVoice、腾讯云、豆包等）；同步提取 Mel 频谱供口型推理。

**渲染层**：Wav2Lip / MuseTalk 等模型生成口型画面，再平滑贴回原始高清视频（仅融合下半脸，保留上半脸头动与眨眼）。

**推流层**：WebRTC 低延迟推流、RTMP 推流到 B站/YouTube、虚拟摄像头输出。

---

## 5. API 与 Docker

| 文档 | 说明 |
|------|------|
| [docs/api.md](docs/api.md) | 通用业务 API — WebRTC、文本/音频驱动、录制、动作编排 |
| [docs/avatar_api.md](docs/avatar_api.md) | Avatar 生成 API — 创建任务、查询进度、删除任务 |
| [docs/admin_api.md](docs/admin_api.md) | Admin 管理 API — 全局配置、会话监控、强制停止 |

Docker 镜像：AutoDL [镜像](https://www.codewithgpu.com/i/lipku/livetalking/base)、UCloud [镜像](https://www.compshare.cn/images/4458094e-a43d-45fe-9b57-de79253befe4?referral_code=3XW3852OBmnD089hMMrtuU&ytag=GPU_GitHub_livetalking)。

---

## 6. 商用版与声明

| 维度 | 开源版 | 商用版 |
|---|---|---|
| 定位 | 社区版，Apache 2.0 | 面向高性能、可运营交付的付费版 |
| 核心目标 | 快速体验、二次开发、学习研究 | 开箱即用：性能加速、自适应动作、实时语音互动 |
| 技术栈 | wav2lip / musetalk / ultralight | 新增 wav2lipls 及全套增强能力 |

更多详情 <https://doc.livetalking.ai/docs/service/>

基于本项目开发并发布在 B站、视频号、抖音等平台的视频需带上 LiveTalking 水印和标识。

---

## 7. 引用与社区

```
@software{livetalking,
  author = {Hengzhong Li},
  title = {LiveTalking: Real-Time Interactive Streaming Digital Human Framework},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/lipku/livetalking}
}
```

| 社区 | 链接 |
|------|------|
| 知识星球 | <https://t.zsxq.com/7NMyO> |
| 微信 | wxwubug (加群请备注) |
| Telegram | <https://t.me/livetalking> |
| Discord | <https://discord.gg/n5jSPCT3Uf> |
| Email | lipku@foxmail.com |
| 微信公众号 | 数字人技术 |

<img src="./assets/qrcode-wechat.jpg" align="middle" />
