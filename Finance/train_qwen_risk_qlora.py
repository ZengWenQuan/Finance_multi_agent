import os
from pathlib import Path

# 在导入 torch 前启用 CUDA 显存碎片优化，减少大块显存分配失败的概率
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:128") # 设置显存管理策略：开启扩展段以减少碎片，设置最大切分大小以优化分配

import warnings

import pandas as pd
import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from sklearn.model_selection import train_test_split
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = REPO_ROOT / "models" / "Qwen3-0.6B"
DEFAULT_DATA_PATH = REPO_ROOT / "data" / "risk_nasdaq" / "risk_deepseek_cleaned_nasdaq_news_full.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "qwen_risk_model_qlora"


def load_and_preprocess_data(csv_path, sample_size=1000):
    """加载和预处理数据"""
    print("正在加载数据...")
    df = pd.read_csv(csv_path)

    if sample_size is not None:
        df = df[:sample_size]

    df = df[df["Lsa_summary"].notna() & df["risk_deepseek"].notna()] # 过滤掉摘要或分数缺失的无效行
    df = df[df["risk_deepseek"] != 0] # 过滤掉分数为 0 的异常数据，只保留 1-5 分的有效数据

    print(f"有效数据数量: {len(df)}")
    print(f"风险分布: {df['risk_deepseek'].value_counts().sort_index()}")
    return df


def create_prompt_template(text, risk_score, stock_symbol="STOCK"):
    """创建训练提示模板"""
    system_prompt = (
        "Forget all your previous instructions. You are a financial expert specializing "
        "in risk assessment for stock recommendations. Based on a specific stock, provide "
        "a risk score from 1 to 5, where: 1 indicates very low risk, 2 indicates low risk, "
        "3 indicates moderate risk (default if the news lacks any clear indication of risk), "
        "4 indicates high risk, and 5 indicates very high risk. 1 summarized news will be "
        "passed in each time. Provide the score in the format shown below in the response "
        "from the assistant."
    )

    user_content = f"News to Stock Symbol -- {stock_symbol}: {text}"

    return f"""System: {system_prompt} # 设置系统提示语，定义模型身份为金融风险评估专家

User: News to Stock Symbol -- AAPL: Apple (AAPL) increases 22% # 少量样本示例 (Few-shot)，引导模型学习输出格式
Assistant: 3

User: News to Stock Symbol -- AAPL: Apple (AAPL) price decreased 30%
Assistant: 4

User: News to Stock Symbol -- AAPL: Apple (AAPL) announced iPhone 15
Assistant: 3

User: {user_content}
Assistant: {risk_score}"""


def prepare_dataset(df, tokenizer, max_length=256):
    """准备训练数据集"""
    print("正在准备数据集...")

    texts = []
    labels = []

    for _, row in df.iterrows():
        text = row["Lsa_summary"]
        risk_score = int(row["risk_deepseek"])
        stock_symbol = row.get("Stock_symbol", "STOCK")

        if pd.isna(text) or text == "":
            continue

        texts.append(create_prompt_template(text, risk_score, stock_symbol))
        labels.append(risk_score)

    train_texts, eval_texts, train_labels, eval_labels = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=None,
    )

    print(f"训练集大小: {len(train_texts)}")
    print(f"验证集大小: {len(eval_texts)}")

    train_dataset = Dataset.from_dict({"text": train_texts, "label": train_labels})
    eval_dataset = Dataset.from_dict({"text": eval_texts, "label": eval_labels})

    def tokenize_function(examples):
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )

        loss_labels = tokenized["input_ids"].clone()
        pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

        for i, text in enumerate(examples["text"]):
            assistant_marker = "Assistant: "
            last_assistant_pos = text.rfind(assistant_marker)

            if last_assistant_pos == -1:
                loss_labels[i, :] = -100
                continue

            answer_start_pos = last_assistant_pos + len(assistant_marker)
            input_part = text[:answer_start_pos]
            input_part_tokens = tokenizer.encode(input_part, add_special_tokens=False)
            mask_length = len(input_part_tokens)

            input_ids = loss_labels[i]
            actual_length = (input_ids != pad_token_id).sum().item()

            if mask_length <= actual_length:
                # 核心逻辑：将 Prompt 及 User 部分的损失设为 -100 (被跨过)，
                # 这样模型在训练时只针对 Assistant 后的“分数”部分计算梯度和更新权重。
                loss_labels[i, :mask_length] = -100
            else:
                # 兜底逻辑：处理边界情况，查找 "Assistant" 标记并屏蔽其之前的所有 Token
                assistant_tokens = tokenizer.encode("Assistant", add_special_tokens=False)
                if assistant_tokens:
                    for j in range(actual_length - 1, -1, -1):
                        if input_ids[j].item() == assistant_tokens[0]:
                            mask_end = min(j + len(assistant_tokens) + 3, actual_length)
                            loss_labels[i, :mask_end] = -100
                            break

            if actual_length < len(input_ids):
                # 屏蔽填充 (Padding) 部分的损失
                loss_labels[i, actual_length:] = -100

        tokenized["labels"] = loss_labels
        return tokenized

    train_tokenized = train_dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=train_dataset.column_names,
    )
    eval_tokenized = eval_dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=eval_dataset.column_names,
    )

    return train_tokenized, eval_tokenized


def create_model_and_tokenizer(model_path):
    """创建 QLoRA 模型和分词器"""
    print("正在加载 QLoRA 模型和分词器...")

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    compute_dtype = torch.float16
    if torch.cuda.is_available():
        major, _ = torch.cuda.get_device_capability()
        if major >= 8:
            compute_dtype = torch.bfloat16

    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,                   # 开启 4-bit 量化加载，显存需求直降为原来的 1/4 左右
        bnb_4bit_quant_type="nf4",           # 使用 NF4 量化数据类型，比普通 4bit 具有更好的模型精度保持能力
        bnb_4bit_use_double_quant=True,      # 开启二次量化，进一步减少量化参数占用的显存
        bnb_4bit_compute_dtype=compute_dtype, # 设置运算时的半精度（BF16/FP16），确保训练稳定性
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
    )

    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,        # 指定为因果语言模型任务
        r=8,                                 # 秩 (Rank)：控制微调参数量。8 是常用平衡值，参数少且效果好
        lora_alpha=16,                       # 缩放系数：类似于学习率的缩放，通常取秩的 2 倍
        lora_dropout=0.05,                   # Dropout 率：防止微调层过拟合
        # target_modules：指定在哪层插入 LoRA 支路。我们选择了 Qwen 的所有投影层，微调效果更精确
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",                         # 不微调 bias 参数，保持模型纯净
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model, tokenizer


def train_model(model, tokenizer, train_dataset, eval_dataset, output_dir):
    """训练模型"""
    print("开始训练模型...")

    use_bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8
    use_fp16 = torch.cuda.is_available() and not use_bf16

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=3,                  # 训练轮数：3 轮可以较好地拟合垂直领域规律，防止过欠拟合
        per_device_train_batch_size=1,       # 单卡 Batch Size：因显存有限设为 1，主要依靠梯度累积
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=16,      # 梯度累积：等效 Batch Size = 1*16=16，提高训练稳定性
        warmup_steps=50,                     # 学习率热身：前 50 步缓慢提升 LR，让训练初始更加平稳
        learning_rate=2e-4,                  # 学习率：LoRA 微调的标准推荐值
        fp16=use_fp16,                       # 自动混合精度：在老显卡上节省显存并加速
        bf16=use_bf16,                       # BF16 模式：在 A10/H100/30系/40系显卡上效果更优
        logging_steps=20,                    # 每隔 20 步在控制台打印 Loss 等日志
        save_steps=200,                      # 每隔 200 步保存模型 Checkpoint
        eval_steps=200,                      # 每隔 200 步在验证集上测一次 Loss
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,         # 训练结束自动加载评价指标最好的权重
        metric_for_best_model="eval_loss",   # 以验证集损失作为选优指标
        greater_is_better=False,
        report_to="none",                    # 不向外部监控系统（如 WandB）上报，保持本地性
        dataloader_pin_memory=False,
        remove_unused_columns=False,
        gradient_checkpointing=True,         # 开启梯度检查点：用计算换显存，支持训练更大的 Context
        optim="paged_adamw_8bit",           # 分页 8bit 优化器：显存不足时的秘密武器，极大降低显存压力
        save_total_limit=2,                  # 最多保留 2 个 Checkpoint，清理硬盘旧文件
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer( # 实例化内置 Trainer，它封装了 Dataloader 加载、设备分配、多步训练等所有复杂逻辑
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    trainer.train() # 启动核心训练循环，自动处理反向传播、梯度更新及日志输出
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    print(f"模型已保存到: {output_dir}")


def main():
    model_path = Path(os.getenv("QWEN_MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    csv_path = Path(os.getenv("RISK_DATA_PATH", str(DEFAULT_DATA_PATH)))
    output_dir = Path(os.getenv("RISK_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
    sample_size_env = os.getenv("RISK_TRAIN_SAMPLE_SIZE", "1000")
    sample_size = None if sample_size_env.lower() == "all" else int(sample_size_env)

    print(f"模型路径: {model_path}")
    print(f"数据路径: {csv_path}")
    print(f"输出路径: {output_dir}")
    print(f"样本数量: {'all' if sample_size is None else sample_size}")

    if not model_path.exists():
        raise FileNotFoundError(f"模型目录不存在: {model_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"数据文件不存在: {csv_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_and_preprocess_data(csv_path, sample_size=sample_size)
    model, tokenizer = create_model_and_tokenizer(str(model_path))
    train_dataset, eval_dataset = prepare_dataset(df, tokenizer, max_length=256)
    train_model(model, tokenizer, train_dataset, eval_dataset, output_dir)

    print("训练完成！")


if __name__ == "__main__":
    main()
