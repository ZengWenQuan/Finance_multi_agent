# vLLM 部署限制、替代方案对比与 10G 左右显存模型建议

## 1. 为什么有的模型不适合 vLLM

不是所有模型都天然适合 `vLLM`。常见原因有下面几类：

### 1.1 模型架构不在 vLLM 原生支持范围内

`vLLM` 优先针对常见的生成式架构做原生实现。虽然它也支持 `Transformers modeling backend`，但前提是模型本身要满足 Transformers 兼容结构、`config.json` 配置完整、必要时还要 `trust_remote_code=True`。  

官方文档说明：
- `vLLM` 支持原生实现，也支持 `Transformers` 后端。
- 使用 `Transformers` 后端时，性能通常在原生实现的 `<5%` 范围内，但模型仍然要满足兼容条件。  

来源：
- https://docs.vllm.ai/en/latest/models/supported_models/

### 1.2 模型是 GGUF 生态优先，而不是 HF Safetensors / AWQ / GPTQ 优先

很多社区模型首先发布的是 `GGUF`，这类模型更适合 `llama.cpp` / `Ollama`。  
虽然现在 `vLLM` 也支持 `GGUF`，但它的主流体验仍然更偏向 Hugging Face 的 `Safetensors + Transformers/AWQ/GPTQ` 路线。  

换句话说：
- `GGUF` 模型通常“能跑”不代表“最适合 vLLM”
- 如果一个模型主要围绕 `llama.cpp`、`Ollama`、`GGUF` 发布，优先考虑本地引擎而不是 vLLM

来源：
- https://docs.vllm.ai/en/v0.15.0/features/quantization/
- https://docs.ollama.com/modelfile

### 1.3 量化格式与显卡/后端不匹配

`vLLM` 支持很多量化，但不是所有量化都支持所有硬件。  
例如官方量化兼容表里明确写到：

- `AWQ` 不支持 Volta，也不支持 AMD GPU
- `FP8` 只支持 Ada / Hopper / AMD GPU
- `GGUF` 虽然支持很多 NVIDIA GPU 和 AMD GPU，但不支持 Intel GPU / x86 CPU 作为该表中的高性能路径

来源：
- https://docs.vllm.ai/en/v0.15.0/features/quantization/

### 1.4 模型本身是多模态或 hybrid-only

有些模型虽然能做纯文本，但模型里自带视觉塔或多模态模块。  
这类模型在 `vLLM` 里如果不手动切文字模式，会白白占显存。

官方文档明确写到：
- 对 `Llama-4`、`Step3`、`Mistral-3`、`Qwen-3.5` 这类 hybrid-only 模型，可以用 `--language-model-only`
- 这样不会加载多模态模块，可以把显存腾给 KV cache

来源：
- https://docs.vllm.ai/en/latest/models/supported_models/

### 1.5 默认上下文太长，KV cache 把显存吃光

有些模型本身支持超长上下文，但你本地卡只有 10G 左右。  
这时就算模型权重能装下，`KV cache` 也会把显存顶爆。  

这不是模型“不能跑”，而是部署参数不合理：
- `max-model-len` 太大
- 并发太高
- `gpu-memory-utilization` 太激进

对于 10G 左右显存，通常不建议直接保留官方默认超长上下文。

### 1.6 新模型太新，需要 nightly 版 vLLM

部分新模型或新量化格式，模型卡会直接写明要 `vLLM nightly` 或指定开发版。  
这意味着：
- 兼容性可能不稳定
- 依赖更脆弱
- 生产环境排障成本更高

比如社区量化的 `Qwen3.5-9B-AWQ` 模型卡就直接要求较新的 `vLLM` 开发版本。

来源：
- https://huggingface.co/QuantTrio/Qwen3.5-9B-AWQ

## 2. vLLM 的优势与限制

### 2.1 优势

- 高吞吐，适合 API 服务和并发推理
- OpenAI 兼容接口成熟
- 对 `AWQ / GPTQ / GGUF / BitsAndBytes / FP8` 等量化支持较多
- 对常见 Hugging Face 架构兼容性好
- 支持 prefix caching、分页注意力、并发 batching 等典型 serving 优化

### 2.2 限制

- 更偏向“服务引擎”，不是最省事的单机随手跑方案
- 对非常新的架构、冷门自定义架构、纯 GGUF 社区模型，不一定是最佳路径
- 量化支持受硬件强约束
- 多模态 hybrid-only 模型要记得开 `--language-model-only`
- 超长上下文模型如果不手动收缩 `max-model-len`，容易 OOM

## 3. 其他部署方式的限制、优缺点

## 3.1 Transformers + bitsandbytes

### 优点

- 最灵活
- 几乎所有 HF Transformers 模型都能先试
- `BitsAndBytesConfig` 对 8-bit / 4-bit 很方便
- 适合单卡实验、脚本调用、研究原型

### 限制

- 不是高吞吐 serving 引擎
- 并发、batching、OpenAI API、监控能力都不如 vLLM/TGI
- 更适合“本地脚本推理”，不太适合直接拿来做服务
- 依赖 `Accelerate` 和模型结构兼容 `torch.nn.Linear`

官方文档说明：
- bitsandbytes 可通过 `BitsAndBytesConfig` 量化
- 只要模型支持 `Accelerate` 且含 `torch.nn.Linear`
- 8-bit 可把权重内存减半
- `LLM.int8()` 至少需要 NVIDIA Turing
- `NF4/FP4` 至少需要 NVIDIA Pascal

来源：
- https://huggingface.co/docs/transformers/main/en/quantization/bitsandbytes

### 适用场景

- 先验证模型能否跑通
- 本地 notebook / 脚本实验
- 低并发工具链

## 3.2 Ollama / llama.cpp

这里可以把 `Ollama` 理解为更易用的 `llama.cpp` 包装层。

### 优点

- 对 `GGUF` 生态最友好
- 配置简单，适合本地桌面环境
- CPU + GPU 混合跑模型很方便
- 对显存很紧的场景更友好
- 社区量化模型极多

### 限制

- 高并发服务能力通常不如 vLLM
- 如果模型只有 HF Safetensors，不一定是最直接路径
- Ollama 对直接导入的 Safetensors 架构支持有限

Ollama 官方文档当前写的 Safetensors 直接导入架构主要是：
- Llama
- Mistral
- Gemma
- Phi3

但它支持从 GGUF 导入，因此实际最适合的还是 GGUF 模型。

来源：
- https://docs.ollama.com/modelfile
- https://docs.ollama.com/import

### 适用场景

- 本地聊天
- 显存紧张
- 社区 GGUF 模型试用
- 不追求很高并发

## 3.3 TGI

### 优点

- 生产化能力强
- OpenAI 接口、监控、批处理、流式输出很成熟
- 支持 bitsandbytes / GPTQ 等量化

### 限制

- Hugging Face 文档已经明确标注 `maintenance mode`
- 官方已经建议新部署优先考虑 `vLLM` 或 `SGLang`
- 对非特定 GPU，某些优化内核未必可用

官方文档说明：
- TGI 已进入 maintenance mode
- 推荐优先考虑 `vLLM` 或 `SGLang`
- 在 NVIDIA 上的优化模型主要针对 `H100 / A100 / A10G / T4`
- 其他 NVIDIA GPU 上，continuous batching 仍可用，但 `flash attention` 和 `paged attention` 等操作可能不会执行

来源：
- https://huggingface.co/docs/text-generation-inference/index
- https://huggingface.co/docs/inference-endpoints/main/en/engines/tgi
- https://huggingface.co/docs/text-generation-inference/installation_nvidia

### 适用场景

- 已有 TGI 存量系统
- 需要成熟的 HF 生态兼容
- 不想自己写很多服务层逻辑

## 3.4 TensorRT-LLM

### 优点

- NVIDIA GPU 上性能非常强
- 更偏生产极致性能
- 对固定模型、固定硬件、固定 batch 的场景很好

### 限制

- 强绑定 NVIDIA 生态
- 要先编译 engine
- engine 还绑定 GPU 架构、batch size、输入/输出长度等参数
- 部署复杂度高于 vLLM
- 支持模型需要看官方 support matrix

官方文档明确写到，每个 engine 都需要针对以下参数编译：
- GPU architecture
- Maximum batch size
- Maximum input length
- Maximum output length
- Maximum beams width

来源：
- https://huggingface.co/docs/text-generation-inference/en/backends/trtllm
- https://nvidia.github.io/TensorRT-LLM/latest/models/supported-models.html

### 适用场景

- 固定模型的高性能生产部署
- 你明确在 NVIDIA 卡上长期运行
- 能接受编译和调参成本

## 4. 10G 左右显存，更适合 vLLM 的开源模型推荐

这里的推荐标准是：
- 尽量偏 `text-only` 或可稳定 text-only
- 优先选择有明确 `vLLM` / `AWQ` / `TGI` 支持描述的模型卡
- 目标显存在 10G 左右
- 允许通过缩小 `max-model-len` 把实际显存压到 10G 档

注意：
- 下面“显存建议”大多是工程估算，不是官方统一基准
- 真正显存占用还受 `max-model-len`、并发、CUDA graphs、KV cache 影响

## 4.1 最推荐

### A. Meta-Llama-3.1-8B-Instruct-AWQ-INT4

模型：
- `jburmeister/Meta-Llama-3.1-8B-Instruct-AWQ-INT4`

为什么推荐：
- 模型卡明确写了 `vLLM` 用法
- 模型卡明确写了仅加载 checkpoint 约需 `4 GiB VRAM`
- 这意味着在较短上下文下，10G 档显卡是现实可跑的

适合：
- 通用对话
- 英文能力较稳
- 想在 10G 附近做 API 服务

风险：
- 如果把上下文开很大，仍然会被 KV cache 顶爆

来源：
- https://huggingface.co/jburmeister/Meta-Llama-3.1-8B-Instruct-AWQ-INT4

### B. Mistral-7B-Instruct-v0.3-AWQ

模型：
- `solidrust/Mistral-7B-Instruct-v0.3-AWQ`

为什么推荐：
- 模型卡明确写了支持 `vLLM`
- 7B + AWQ 4-bit 是很典型的 10G 档选择
- 社区普遍把它归入“小 12GB GPU 友好”一类

适合：
- 通用问答
- 延迟和显存都想控住

来源：
- https://huggingface.co/solidrust/Mistral-7B-Instruct-v0.3-AWQ

### C. Qwen2.5-7B-Instruct-AWQ

模型：
- `Qwen/Qwen2.5-7B-Instruct-AWQ`

为什么推荐：
- 官方 AWQ
- 模型卡直接写了“部署推荐 vLLM”
- 7B + AWQ 4-bit 对 10G 档很友好
- 中文能力通常比同档很多西方模型更稳

适合：
- 中文/中英双语
- 工具调用、结构化输出

来源：
- https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ

### D. Qwen2.5-Coder-7B-Instruct-AWQ

模型：
- `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`

为什么推荐：
- 官方 AWQ
- 同样明确推荐 `vLLM`
- 如果你更偏代码任务，它比通用 7B 更合适

适合：
- 代码问答
- 代码补全
- 本地 coding assistant

来源：
- https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-AWQ

## 4.2 可以考虑，但不是 10G 最稳

### E. Qwen3.5-4B

模型：
- `Qwen/Qwen3.5-4B`

为什么可以考虑：
- 官方模型卡明确写了兼容 `vLLM`
- 4B 本身更容易控制显存
- 如果你只跑文本，可以配 `--language-model-only`

不足：
- 它本质上是带 vision encoder 的 hybrid-only 模型
- 虽然可以文字模式运行，但在部署心智上不如纯 text-only 模型直接

适合：
- 你想体验 Qwen3.5 新架构
- 显存更保守

来源：
- https://huggingface.co/Qwen/Qwen3.5-4B
- https://docs.vllm.ai/en/latest/models/supported_models/

### F. Qwen3.5-9B-AWQ

模型：
- `QuantTrio/Qwen3.5-9B-AWQ`

为什么不是 10G 最稳：
- 模型卡直接写了文件大小 `12GiB`
- 还要求比较新的 `vLLM nightly`
- 更适合“允许稍微超一点显存”的情况，不是严格 10G 档

适合：
- 你能接受约 12G 级别
- 能接受 nightly vLLM 和更高排障成本

来源：
- https://huggingface.co/QuantTrio/Qwen3.5-9B-AWQ

## 4.3 如果你偏推理模型

### G. DeepSeek-R1-Distill-Llama-8B AWQ

可关注：
- `benyamini/DeepSeek-R1-Distill-Llama-8B-AWQ-w4g128`
- `casperhansen/deepseek-r1-distill-llama-8b-awq`

其中一个模型卡直接写到：
- 模型大小约 `4GB`
- 内存从 `16GB -> 4GB`

这类模型更偏 reasoning，适合你想要“推理味”更浓一些的 8B 方案。  
不过社区量化版本的质量和兼容性稳定性不如前面几个“更主流的 AWQ 官方/成熟社区量化”。

来源：
- https://huggingface.co/benyamini/DeepSeek-R1-Distill-Llama-8B-AWQ-w4g128
- https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B

## 5. 我对 10G 左右显存的实际建议

如果你主要是 `vLLM + 单卡 + 10G 左右`，优先顺序建议是：

1. `Qwen/Qwen2.5-7B-Instruct-AWQ`
2. `jburmeister/Meta-Llama-3.1-8B-Instruct-AWQ-INT4`
3. `solidrust/Mistral-7B-Instruct-v0.3-AWQ`
4. `Qwen/Qwen2.5-Coder-7B-Instruct-AWQ`  
   如果你更偏代码，就把它提到前面
5. `Qwen/Qwen3.5-4B`  
   如果你想更稳地压显存

不建议作为 10G 首选的：

- `Qwen3.5-9B-AWQ`
  原因：文件就已经 `12GiB`，更像 12G+ 档

- 纯 GGUF 社区模型
  原因：如果你的目标是 `vLLM`，它们通常不是最佳路径，优先考虑 `llama.cpp/Ollama`

## 6. 部署选型结论

### 结论一句话

- 你要做 API 服务、高吞吐、OpenAI 兼容：优先 `vLLM`
- 你要本地最省事、GGUF 模型多、显存紧：优先 `Ollama / llama.cpp`
- 你要最灵活、先跑起来验证：优先 `Transformers + bitsandbytes`
- 你在 NVIDIA 上追求极致性能并愿意编译：考虑 `TensorRT-LLM`
- `TGI` 现在不建议作为新项目首选

### 你这个 10G 档的推荐落地

最稳的路线是：

1. 先试 `Qwen2.5-7B-Instruct-AWQ` 或 `Llama-3.1-8B-Instruct-AWQ-INT4`
2. `vLLM` 启动时把 `--max-model-len` 先压到 `4096` 或 `8192`
3. 并发先小一点，再逐步放大

## 7. 参考资料

- vLLM Supported Models  
  https://docs.vllm.ai/en/latest/models/supported_models/
- vLLM Quantization  
  https://docs.vllm.ai/en/v0.15.0/features/quantization/
- Transformers bitsandbytes  
  https://huggingface.co/docs/transformers/main/en/quantization/bitsandbytes
- TGI 文档首页  
  https://huggingface.co/docs/text-generation-inference/index
- TGI Inference Endpoints 文档  
  https://huggingface.co/docs/inference-endpoints/main/en/engines/tgi
- TGI NVIDIA GPU 支持说明  
  https://huggingface.co/docs/text-generation-inference/installation_nvidia
- TensorRT-LLM backend  
  https://huggingface.co/docs/text-generation-inference/en/backends/trtllm
- TensorRT-LLM 支持模型  
  https://nvidia.github.io/TensorRT-LLM/latest/models/supported-models.html
- Ollama Modelfile  
  https://docs.ollama.com/modelfile
- Ollama Import  
  https://docs.ollama.com/import

### 推荐模型链接

- Llama 3.1 8B AWQ  
  https://huggingface.co/jburmeister/Meta-Llama-3.1-8B-Instruct-AWQ-INT4
- Mistral 7B Instruct AWQ  
  https://huggingface.co/solidrust/Mistral-7B-Instruct-v0.3-AWQ
- Qwen2.5 7B Instruct AWQ  
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-AWQ
- Qwen2.5 Coder 7B Instruct AWQ  
  https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
- Qwen3.5 4B  
  https://huggingface.co/Qwen/Qwen3.5-4B
- Qwen3.5 9B AWQ  
  https://huggingface.co/QuantTrio/Qwen3.5-9B-AWQ
- DeepSeek R1 Distill Llama 8B AWQ  
  https://huggingface.co/benyamini/DeepSeek-R1-Distill-Llama-8B-AWQ-w4g128
