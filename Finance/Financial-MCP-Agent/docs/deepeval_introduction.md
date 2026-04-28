# DeepEval 介绍

## 1. DeepEval 是什么

DeepEval 是一个开源的 LLM 评估框架，主要用来测试和评估：

- LLM 应用
- RAG 流程
- AI Agent
- 工具调用链
- 多轮对话
- 复杂工作流

它的定位不是“训练模型”，而是：

**把 AI 应用变成可以写测试、可以打分、可以回归验证的对象。**

官方的几个核心特点可以概括为：

- `Pytest` 风格的单元测试
- 50+ 现成指标
- 支持端到端评估和组件级评估
- 支持 tracing
- 支持合成数据集
- 本地优先运行

官方介绍页：

- [DeepEval Introduction](https://deepeval.com/docs/introduction)
- [DeepEval Home](https://deepeval.com/)

---

## 2. DeepEval 解决什么问题

传统软件可以很容易用断言测试：

- 输入固定
- 输出固定
- 对不对一眼能判断

但 LLM 应用不一样。

LLM 的输出通常具有这些特点：

- 同一个输入可能有多个合理答案
- 结果是语义性的，不是纯字符串比较
- 答案质量可能依赖检索上下文、工具调用、历史消息
- 单纯的 `assert ==` 往往没意义

DeepEval 的目标就是把这些“难测”的行为，变成可以测试和打分的东西。

---

## 3. DeepEval 的核心思想

DeepEval 的核心可以理解为三件事：

1. 把 AI 应用封装成 `Test Case`
2. 用 `Metric` 作为评分标准
3. 用 `Trace` 或上下文去评估整个链路

换句话说，它不是只看最终答案，而是可以看：

- 输入是什么
- 检索了什么上下文
- 最终输出是什么
- 工具有没有被正确调用
- 中间过程是否忠实于证据

---

## 4. DeepEval 的基本构件

## 4.1 Test Case

`Test Case` 是一个要评估的样本。

它通常包含：

- `input`：用户输入
- `actual_output`：模型输出
- `expected_output`：期望输出或参考答案
- `retrieval_context`：检索上下文
- `metadata`：额外信息

在 RAG 场景里，`retrieval_context` 很关键，因为 DeepEval 不只评估“答得像不像”，还会评估“有没有用对上下文”。

---

## 4.2 Metrics

`Metric` 是评分逻辑。

DeepEval 提供很多现成指标，覆盖：

- RAG
- agent
- tool use
- conversation
- safety
- multimodal

官方介绍明确提到它提供 50+ 指标，并且支持 LLM-as-a-judge、agent、tool-use、RAG 等场景。

---

## 4.3 Traces

`Trace` 记录的是运行过程。

这对复杂 agent 特别重要，因为你不只想知道最后答得对不对，还想知道：

- 中间调用了哪些工具
- 哪一步出错了
- 检索器有没有召回正确内容
- planner 有没有做错决策

DeepEval 官方也明确支持端到端评估和组件级评估，并且可以通过 tracing 找出失败点。

---

## 5. DeepEval 怎么进行评估

DeepEval 的评估流程通常分成下面几步。

## 5.1 构造测试样本

先定义一批测试样本，也就是 test cases。

例如 RAG 场景里，一个 test case 可能包括：

- 用户问题
- 标准答案
- 检索上下文
- 模型回答

---

## 5.2 跑应用

DeepEval 本身不会替你业务逻辑，它会让你的应用先跑一遍。

例如：

- 先检索上下文
- 再生成回答
- 再把结果交给评估器

这意味着 DeepEval 评的是“真实应用行为”，不是脱离上下文的孤立文本。

---

## 5.3 让指标打分

DeepEval 会把 test case 交给配置好的 metric。

对于很多指标来说，实际打分并不只是简单规则判断，而是会用 LLM-as-a-judge。

也就是说，它常常会让一个 judge model 去判断：

- 答案是否相关
- 上下文是否充分
- 回答是否忠实于证据
- 输出是否遵循预期

官方介绍里提到它提供 `G-Eval`、`DAG`、`QAG` 等技术，用来支持不同类型的评估。

---

## 5.4 产出评分和解释

最后 DeepEval 会输出：

- metric 分数
- 是否通过阈值
- 失败原因
- 解释信息

这点很重要，因为 LLM 评估不是单纯一个分数就够了，通常还需要知道为什么失败。

---

## 6. DeepEval 的两种评估模式

官方把评估分成两类。

## 6.1 End-to-End LLM Evals

这是端到端评估。

适合：

- 简单 LLM API
- 聊天机器人
- 黑盒质量检查
- 常规 RAG 回答

特点是：

- 直接看输入和输出
- 更像传统测试
- 不一定需要完整 trace

---

## 6.2 Component-Level LLM Evals

这是组件级评估。

适合：

- Agent
- 工具调用工作流
- MCP 系统
- 多步骤复杂应用

特点是：

- 看内部步骤
- 看检索器、planner、generator、tool 是否各自正常
- 可以定位问题发生在哪一层

DeepEval 官方明确提到这两种模式可以单独使用，也可以结合起来。

---

## 7. DeepEval 在 RAG 里通常评什么

DeepEval 的 RAG 评估通常围绕四个核心维度。

## 7.1 Contextual Precision

看检索到的上下文里，真正有用的信息占比高不高。

简单说就是：

**检索结果是不是“准”。**

如果一堆上下文里大部分都无关，那 precision 会低。

### 计算方式

DeepEval 的官方定义里，`Contextual Precision` 会先让 judge model 判断每个检索节点是否相关，然后按排序位置计算加权精度，核心思想接近 Average Precision。

可以理解成：

1. 先给 `retrieval_context` 里的每个片段打相关/不相关标签
2. 越靠前的相关片段，贡献越大
3. 最终分数是相关片段的加权平均

官方公式可以概括为：

```text
Contextual Precision = (1 / relevant_nodes_count) * Σ (precision@k × relevance_k)
```

其中：

- `precision@k` 表示前 `k` 个检索结果里相关项的比例
- `relevance_k` 表示第 `k` 个片段是否相关，相关记为 `1`，不相关记为 `0`

所以这个指标不仅看“有没有召回到”，还看“相关内容排得靠不靠前”。

---

## 7.2 Contextual Recall

看所有该召回的关键信息有没有被召回。

简单说就是：

**该找的证据有没有找全。**

如果答案需要的关键信息没被检索到，recall 会低。

### 计算方式

DeepEval 的 `Contextual Recall` 会先把 `expected_output` 拆成独立陈述，再判断这些陈述能不能被 `retrieval_context` 支撑。

可以理解成：

1. 把标准答案拆成若干条独立事实
2. 用 judge model 判断每条事实是否能从上下文中找到依据
3. 用“被支持的事实数 / 总事实数”作为得分

官方公式可以概括为：

```text
Contextual Recall = attributable_statements / total_statements
```

所以这个指标重点看的是：

**上下文有没有把该有的信息尽量找全。**

---

## 7.3 Answer Relevancy

看最终回答和问题本身的相关程度。

简单说就是：

**有没有答偏题。**

### 计算方式

DeepEval 的 `Answer Relevancy` 会先把 `actual_output` 拆成若干独立陈述，然后判断这些陈述是否和输入问题相关。

可以理解成：

1. 把回答拆成句子或原子陈述
2. 用 judge model 判断每条陈述是否在回答问题
3. 统计相关陈述占比

官方公式可以概括为：

```text
Answer Relevancy = relevant_statements / total_statements
```

如果回答里出现很多跑题、废话、无关延伸，分数就会下降。

---

## 7.4 Faithfulness

看回答是否忠实于检索上下文。

简单说就是：

**回答有没有胡编，或者有没有超出证据乱说。**

这个指标特别适合检查 RAG 幻觉问题。

### 计算方式

DeepEval 的 `Faithfulness` 会先从 `actual_output` 中抽取若干事实性主张，再判断这些主张是否都能被 `retrieval_context` 支撑。

可以理解成：

1. 从回答里抽取 claims
2. 用 judge model 检查这些 claims 是否被上下文支持
3. 用“被支持的 claims 数 / 总 claims 数”作为分数

官方公式可以概括为：

```text
Faithfulness = truthful_claims / total_claims
```

如果回答引入了上下文里没有、甚至相矛盾的信息，faithfulness 就会下降。

---

## 8. DeepEval 是怎么用 LLM 参与评估的

DeepEval 很多指标本质上是 LLM-as-a-judge。

它不是只依赖硬编码规则，而是会让 judge model 按标准判断：

- 这个回答是否相关
- 这个上下文是否包含证据
- 回答是否被上下文支持
- 回答是否满足 criteria

这也是为什么它比纯字符串匹配更适合 LLM 应用。

---

## 9. 你们项目里是怎么用 DeepEval 的

你们项目当前用的是 [src/eval_rag_deepeval.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/eval_rag_deepeval.py:279)。

它的流程大致是：

1. 读取评估数据
2. 根据模式检索上下文
3. 生成或读取回答
4. 封装成 `LLMTestCase`
5. 用 DeepEval 的指标打分

相关代码里明确用了：

- `ContextualPrecisionMetric`
- `ContextualRecallMetric`
- `AnswerRelevancyMetric`
- `FaithfulnessMetric`

具体位置见：

- [src/eval_rag_deepeval.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/eval_rag_deepeval.py:279)

---

## 10. 你们项目里的评估流程

按照代码逻辑，整体流程是这样的：

### 第一步：准备评估数据

每条数据一般包含：

- `input`
- `expected_output`
- `stock_code`
- 可能还有其他元信息

### 第二步：执行检索

根据模式决定：

- `vector`：走向量上下文
- `graph`：走图上下文
- `hybrid`：两者合并

代码位置：

- [src/eval_rag_deepeval.py](/home/irving/workspace/agent_demo/Finance/Financial-MCP-Agent/src/eval_rag_deepeval.py:303)

### 第三步：生成回答

如果样本里没有现成 `actual_output`，脚本会先调用 `generate_rag_answer(...)` 生成回答。

### 第四步：构造 `LLMTestCase`

把以下内容塞给 DeepEval：

- `input`
- `actual_output`
- `expected_output`
- `retrieval_context`

### 第五步：跑指标

然后用 DeepEval 评估：

- 上下文是否够准
- 上下文是否够全
- 回答是否相关
- 回答是否忠实于证据

---

## 11. DeepEval 的优点

### 11.1 很适合 LLM 应用

它不是传统机器学习评估那套简单准确率，而是专门为 LLM 工作流设计的。

### 11.2 支持 RAG 和 Agent

它不仅能评 RAG，也适合复杂 agent、工具调用和多步流程。

### 11.3 本地优先

评估可以在你自己的环境里跑，不一定依赖平台。

### 11.4 可解释

很多指标是 LLM judge 驱动，通常会附带理由，便于定位问题。

### 11.5 方便做回归测试

很适合把 AI 质量测试纳入 CI/CD。

---

## 12. DeepEval 的局限

### 12.1 评估本身也依赖 judge model

如果 judge model 不稳定，评分也会受影响。

### 12.2 成本比纯规则评估高

尤其是要跑 LLM judge 时，会有额外调用成本。

### 12.3 需要测试集设计

如果你的 test case 质量差，评估结果也不会可靠。

### 12.4 指标不是业务真相本身

分数只能说明某种维度的质量，不等于最终业务指标。

---

## 13. 什么时候该用 DeepEval

适合：

- 要做 RAG 回归测试
- 要比较不同 prompt / 检索策略 / 模型
- 要评估 agent 的整体质量
- 要把 AI 测试自动化
- 要跟踪回答是否忠实于证据

不太适合：

- 你只想做一个简单 demo
- 你完全没有测试集
- 你只想看最终文本是否包含某个关键词

---

## 14. 一句话总结

DeepEval 是一个面向 LLM 应用的评估框架，它通过 `Test Case + Metric + Trace` 的方式，把原本难以测试的 RAG、Agent、工具调用和多轮对话变成可打分、可回归、可解释的评估流程。你们项目里当前用它来评估 RAG 的上下文精度、召回率、回答相关性和忠实性。

---

## 15. 参考链接

- [DeepEval Home](https://deepeval.com/)
- [DeepEval Introduction](https://deepeval.com/docs/introduction)
