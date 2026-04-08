import os
from pathlib import Path

import pandas as pd
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_MODEL_PATH = REPO_ROOT / "models" / "Qwen3-0.6B"
DEFAULT_ADAPTER_PATH = REPO_ROOT / "models" / "qwen_risk_model_qlora"
DEFAULT_REAL_DATA_PATH = REPO_ROOT / "data" / "risk_nasdaq" / "risk_deepseek_cleaned_nasdaq_news_full.csv"


def load_trained_risk_model(base_model_path=None, adapter_path=None):
    """加载 QLoRA 风险评估模型"""
    base_model_path = Path(base_model_path or os.getenv("QWEN_MODEL_PATH", str(DEFAULT_BASE_MODEL_PATH)))
    adapter_path = Path(adapter_path or os.getenv("RISK_ADAPTER_PATH", str(DEFAULT_ADAPTER_PATH)))

    print("正在加载训练好的 QLoRA 风险评估模型...")
    print(f"基础模型路径: {base_model_path}")
    print(f"Adapter 路径: {adapter_path}")

    if not base_model_path.exists():
        raise FileNotFoundError(f"基础模型目录不存在: {base_model_path}")
    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter 目录不存在: {adapter_path}")

    tokenizer = AutoTokenizer.from_pretrained(str(adapter_path), trust_remote_code=True)
    if tokenizer.pad_token is None:
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

    base_model = AutoModelForCausalLM.from_pretrained(
        str(base_model_path),
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base_model, str(adapter_path))
    model.eval()
    return model, tokenizer


def create_risk_test_prompt(text, stock_symbol="STOCK"):
    """创建风险评估测试提示"""
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

    return f"""System: {system_prompt}

User: News to Stock Symbol -- AAPL: Apple (AAPL) increases 22%
Assistant: 3

User: News to Stock Symbol -- AAPL: Apple (AAPL) price decreased 30%
Assistant: 4

User: News to Stock Symbol -- AAPL: Apple (AAPL) announced iPhone 15
Assistant: 3

User: {user_content}
Assistant:"""


def predict_risk(model, tokenizer, text, stock_symbol="STOCK"):
    """预测风险分数"""
    prompt = create_risk_test_prompt(text, stock_symbol)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=5,
            do_sample=False,
            temperature=0.1,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    assistant_response = generated_text.split("Assistant:")[-1].strip()

    try:
        risk_score = int(assistant_response.split()[0])
        if 1 <= risk_score <= 5:
            return risk_score
    except Exception:
        pass

    return None


def test_risk_model():
    """测试风险评估模型"""
    model, tokenizer = load_trained_risk_model()

    test_cases = [
        ("Apple reported strong quarterly earnings with revenue growth of 15%", "AAPL"),
        ("Apple faces major supply chain disruptions and production delays", "AAPL"),
        ("Apple announces bankruptcy filing and CEO resignation", "AAPL"),
        ("Apple stock price remains stable amid market volatility", "AAPL"),
        ("Apple receives regulatory approval for new product launch", "AAPL"),
        ("Tesla recalls 500,000 vehicles due to safety concerns", "TSLA"),
        ("Microsoft announces layoffs affecting 10,000 employees", "MSFT"),
    ]

    print("\n=== QLoRA 风险评估模型测试结果 ===")
    for i, (text, symbol) in enumerate(test_cases, 1):
        print(f"\n测试 {i}:")
        print(f"新闻: {text}")
        print(f"股票: {symbol}")

        predicted_risk = predict_risk(model, tokenizer, text, symbol)

        if predicted_risk:
            risk_map = {1: "极低风险", 2: "低风险", 3: "中等风险", 4: "高风险", 5: "极高风险"}
            print(f"预测风险: {predicted_risk} ({risk_map[predicted_risk]})")
        else:
            print("预测风险: 解析失败")

    print("\n=== 真实数据测试 ===")
    real_data_path = Path(os.getenv("RISK_TEST_DATA_PATH", str(DEFAULT_REAL_DATA_PATH)))
    try:
        df = pd.read_csv(real_data_path, nrows=5)
        df = df[df["Lsa_summary"].notna() & df["risk_deepseek"].notna()]

        for i, (_, row) in enumerate(df.head(3).iterrows(), 1):
            text = row["Lsa_summary"]
            true_risk = int(row["risk_deepseek"])
            stock_symbol = row.get("Stock_symbol", "STOCK")

            predicted_risk = predict_risk(model, tokenizer, text, stock_symbol)

            print(f"\n真实测试 {i}:")
            print(f"股票: {stock_symbol}")
            print(f"新闻摘要: {text[:100]}...")
            print(f"真实风险: {true_risk}")
            print(f"预测风险: {predicted_risk}")
            print(f"准确性: {'✓' if predicted_risk == true_risk else '✗'}")

    except Exception as e:
        print(f"真实数据测试失败: {e}")


if __name__ == "__main__":
    test_risk_model()
