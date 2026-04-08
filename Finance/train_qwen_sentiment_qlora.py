import os
from pathlib import Path

# 在导入 torch 前启用 CUDA 显存碎片优化，减少大块显存分配失败的概率
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:128")

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
DEFAULT_DATA_PATH = REPO_ROOT / "data" / "nasdaq_news_sentiment" / "sentiment_deepseek_new_cleaned_nasdaq_news_full.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "qwen_sentiment_model_qlora"


def load_and_preprocess_data(csv_path, sample_size=1000):
    """加载和预处理数据"""
    print("正在加载数据...")
    df = pd.read_csv(csv_path)

    if sample_size is not None:
        df = df[:sample_size]

    df = df[df["Lsa_summary"].notna() & df["sentiment_deepseek"].notna()]
    df = df[df["sentiment_deepseek"] != 0]

    print(f"有效数据数量: {len(df)}")
    print(f"情感分布: {df['sentiment_deepseek'].value_counts().sort_index()}")
    return df


def create_prompt_template(text, sentiment, stock_symbol="STOCK"):
    """创建训练提示模板"""
    system_prompt = (
        "Forget all your previous instructions. You are a financial expert with stock "
        "recommendation experience. Based on a specific stock, score for range from 1 "
        "to 5, where 1 is negative, 2 is somewhat negative, 3 is neutral, 4 is somewhat "
        "positive, 5 is positive. 1 summarized news will be passed in each time, you "
        "will give score in format as shown below in the response from assistant."
    )

    user_content = f"News to Stock Symbol -- {stock_symbol}: {text}"

    return f"""System: {system_prompt}

User: News to Stock Symbol -- AAPL: Apple (AAPL) increase 22%
Assistant: 5

User: News to Stock Symbol -- AAPL: Apple (AAPL) price decreased 30%
Assistant: 1

User: News to Stock Symbol -- AAPL: Apple (AAPL) announced iPhone 15
Assistant: 4

User: {user_content}
Assistant: {sentiment}"""


def prepare_dataset(df, tokenizer, max_length=512):
    """准备训练数据集"""
    print("正在准备数据集...")

    texts = []
    labels = []

    for _, row in df.iterrows():
        text = row["Lsa_summary"]
        sentiment = int(row["sentiment_deepseek"])
        stock_symbol = row.get("Stock_symbol", "STOCK")

        if pd.isna(text) or text == "":
            continue

        texts.append(create_prompt_template(text, sentiment, stock_symbol))
        labels.append(sentiment)

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
                loss_labels[i, :mask_length] = -100
            else:
                assistant_tokens = tokenizer.encode("Assistant", add_special_tokens=False)
                if assistant_tokens:
                    for j in range(actual_length - 1, -1, -1):
                        if input_ids[j].item() == assistant_tokens[0]:
                            mask_end = min(j + len(assistant_tokens) + 3, actual_length)
                            loss_labels[i, :mask_end] = -100
                            break

            if actual_length < len(input_ids):
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
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
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
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
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
        num_train_epochs=3,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=16,
        warmup_steps=50,
        learning_rate=2e-4,
        fp16=use_fp16,
        bf16=use_bf16,
        logging_steps=20,
        save_steps=200,
        eval_steps=200,
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",
        dataloader_pin_memory=False,
        remove_unused_columns=False,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        save_total_limit=2,
    )

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    trainer.train()
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    print(f"模型已保存到: {output_dir}")


def main():
    model_path = Path(os.getenv("QWEN_MODEL_PATH", str(DEFAULT_MODEL_PATH)))
    csv_path = Path(os.getenv("SENTIMENT_DATA_PATH", str(DEFAULT_DATA_PATH)))
    output_dir = Path(os.getenv("SENTIMENT_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR)))
    sample_size_env = os.getenv("SENTIMENT_TRAIN_SAMPLE_SIZE", "1000")
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
    train_dataset, eval_dataset = prepare_dataset(df, tokenizer, max_length=512)
    train_model(model, tokenizer, train_dataset, eval_dataset, output_dir)

    print("训练完成！")


if __name__ == "__main__":
    main()
