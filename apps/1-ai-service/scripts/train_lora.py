# scripts/train_lora.py
import os
import json
import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments, 
    DataCollatorForLanguageModeling,
    Trainer,
    BitsAndBytesConfig
)
from peft import get_peft_model, LoraConfig, TaskType
from datasets import load_dataset

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# Đọc cấu hình
config_path = os.getenv("MODEL_CONFIG_PATH", "configs/model_config.json")
with open(config_path, "r") as f:
    config = json.load(f)

model_config = config.get("model", {})
lora_config = model_config.get("lora_config", {})

# Tải model gốc
model_id = model_config.get("base_model_id", "mistralai/Mistral-7B-v0.1")
tokenizer = AutoTokenizer.from_pretrained(model_id)
tokenizer.pad_token = tokenizer.eos_token

base_model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    ),
    device_map="auto",
)

# Cấu hình LoRA
peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=lora_config.get("r", 8),
    lora_alpha=lora_config.get("lora_alpha", 32),
    lora_dropout=lora_config.get("lora_dropout", 0.05),
    target_modules=lora_config.get("target_modules", ["q_proj", "v_proj", "k_proj", "o_proj"]),
    bias="none",
)

# Áp dụng LoRA cho model
model = get_peft_model(base_model, peft_config)

# Chuẩn bị dữ liệu
def prepare_dataset(examples):
    print(f"Type of examples: {type(examples)}")
    print(f"Available columns: {examples.column_names}")
    # Mẫu prompt template mới phù hợp với định dạng dữ liệu của chúng ta
    prompt_template = """<system>
Bạn là trợ lý phân tích dữ liệu thông minh, giúp phát hiện ý định của người dùng từ câu hỏi và trả về đúng định dạng JSON.
</system>

<user>
Phân tích ý định từ câu hỏi sau: {query}
</user>

<assistant>
{{
    "intent": "{intent}",
    "confidence": 0.9,
    "entities": {entities}
    {viz_type}
}}
</assistant>"""
    
    result = []
    
    # Truy cập trực tiếp vào từng mẫu dữ liệu trong dataset
    for i in range(len(examples)):
        query = examples[i]["query"]
        intent = examples[i]["intent"]
        entities = json.dumps(examples[i]["entities"])
        
        # Xử lý visualization_type nếu có
        viz_type = ""
        if "visualization_type" in examples[i] and examples[i]["intent"] == "visualization":
            viz_type = f',\n  "visualization_type": "{examples[i]["visualization_type"]}"'
        
        # Format prompt template
        formatted_prompt = prompt_template.format(
            query=query,
            intent=intent,
            entities=entities,
            viz_type=viz_type
        )
        
        result.append(formatted_prompt)
    
    return {"text": result}

# Tải dataset
try:
    raw_dataset = load_dataset("json", data_files={"train": "data/lora_training.jsonl"})
except:
    print("The format of dataset is not standard JSONL")
    # Nếu format không phải là JSONL tiêu chuẩn, sử dụng cách đọc thủ công
    with open("data/lora_training.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    data = [line.strip() for line in lines if line.strip()]
    raw_dataset = {"data": data}
    raw_dataset = {"train": raw_dataset}

# Tạo dataset dưới định dạng mà Trainer cần
processed_dataset = prepare_dataset(raw_dataset["train"])

dataset = {
    "train": {
        "text": processed_dataset["text"]
    }
}

# Định dạng dataset cho Trainer
from datasets import Dataset
train_dataset = Dataset.from_dict({"text": dataset["train"]["text"]})

# Cấu hình huấn luyện
output_dir = model_config.get("peft_model_path", "models/lora-intent-detection")
training_args = TrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=True,
    save_steps=50,
    logging_steps=10,
    save_total_limit=3,
    report_to=["tensorboard"],
    no_cuda=False
)

# Tokenize dataset
def tokenize_function(examples):
    tokenized = tokenizer(examples["text"], truncation=True, max_length=512)
    return tokenized

tokenized_dataset = train_dataset.map(tokenize_function, batched=True)

# Huấn luyện
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

# Bắt đầu huấn luyện
print("Starting LoRA training...")
trainer.train()

# Lưu model
print(f"Saving LoRA adapter to {output_dir}")
trainer.save_model(output_dir)
print("Training complete!")