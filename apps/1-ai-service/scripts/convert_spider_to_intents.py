import json
import re
import os
import random

# Tạo thư mục data nếu chưa tồn tại
os.makedirs("data", exist_ok=True)

# Đọc dữ liệu Spider
train_data = []
with open("spider/train_spider.json", "r") as f:
    train_data.extend(json.load(f))
    
with open("spider/train_others.json", "r") as f:
    train_data.extend(json.load(f))

# Đọc thông tin bảng
with open("spider/tables.json", "r") as f:
    tables_info = json.load(f)

# Tạo mapping từ db_id đến thông tin schema
db_schemas = {}
for item in tables_info:
    db_id = item["db_id"]
    table_names = item["table_names_original"]
    column_names = item["column_names_original"]
    
    # Khởi tạo schema cho database
    db_schemas[db_id] = {"tables": {}}
    
    # Tạo dictionary cho từng bảng
    for i, table_name in enumerate(table_names):
        db_schemas[db_id]["tables"][table_name] = {"columns": []}
    
    # Thêm cột vào các bảng
    for col_info in column_names:
        table_index = col_info[0]
        col_name = col_info[1]
        
        # Bỏ qua cột * (thường có table_index = -1)
        if table_index >= 0:
            table_name = table_names[table_index]
            db_schemas[db_id]["tables"][table_name]["columns"].append(col_name)

# Hàm phát hiện intent từ câu hỏi và SQL
def detect_intent(question:str, sql:str, db_id=None):
    question = question.lower()
    sql = sql.lower()
    
    # Các pattern để phát hiện intent
    intent_patterns = {
        "question": [
            r"select\s+count\(", r"how many", "count",
            r"select\s+(avg|average|mean)\(", "average", "mean", "median",
            r"select\s+sum\(", "sum", "total",
            r"select\s+max\(", "maximum", "highest", "largest",
            r"select\s+min\(", "minimum", "lowest", "smallest",
            "query", "give me", "show me", "list", "find"
        ],
        "visualization": [
            "draw", "plot", "chart", "graph", "visualize", "display",
            "bar chart", "line chart", "pie chart", "histogram", "scatter plot",
            "visualization", "visualisation"
        ],
        "analysis": [
            "analyze", "analyse", "analysis", "examine",
            "compare", "correlation", "relationship",
            "trend", "pattern", r"group by", r"order by"
        ],
        "insight": [
            "insight", "key finding", "important", "highlight", "significant",
            "interesting", "notable", "summarize", "overview"
        ],
        "prediction": [
            "predict", "forecast", "future", "estimate",
            "will", "expected", "projection"
        ]
    }
    
    # Các mẫu trực quan hóa
    viz_patterns = {
        "bar": ["bar chart", "bar graph", "column chart"],
        "line": ["line chart", "line graph", "trend", "over time"],
        "pie": ["pie chart", "pie graph", "proportion", "distribution", "percentage"],
        "scatter": ["scatter plot", "scatter graph", "correlation", "relationship"],
        "histogram": ["histogram", "distribution"]
    }
    
    # Xác định intent
    detected_intents = {}
    for intent, patterns in intent_patterns.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, question) or re.search(pattern, sql):
                score += 1
        detected_intents[intent] = score
    
    # Chọn intent có điểm cao nhất
    if max(detected_intents.values()) > 0:
        best_intent = max(detected_intents.items(), key=lambda x: x[1])[0]
    else:
        # Mặc định là "question" nếu không có pattern nào khớp
        best_intent = "question"
    
    # Xác định loại operation
    operation = "query"  # Mặc định
    if best_intent == "question":
        if re.search(r"select\s+count\(", sql) or "how many" in question:
            operation = "count"
        elif re.search(r"select\s+(avg|average|mean)\(", sql) or "average" in question:
            operation = "average"
        elif re.search(r"select\s+sum\(", sql) or "sum" in question or "total" in question:
            operation = "sum"
        elif re.search(r"select\s+max\(", sql) or "maximum" in question:
            operation = "max"
        elif re.search(r"select\s+min\(", sql) or "minimum" in question:
            operation = "min"
    elif best_intent == "visualization":
        operation = "visualize"
    elif best_intent == "analysis":
        if "group by" in sql:
            operation = "group" 
        elif "order by" in sql:
            operation = "sort"
        elif "compare" in question:
            operation = "compare"
        else:
            operation = "analyze"
    elif best_intent == "insight":
        operation = "insight"
    elif best_intent == "prediction":
        operation = "predict"
    
    # Trích xuất cột được đề cập
    columns = []
    
    # Tìm cột từ SQL
    for pattern in [
        r'(?:sum|avg|max|min|count)\s*\(\s*([a-zA-Z0-9_\.]+)\s*\)',
        r'(?:select|where|group by|order by)\s+([a-zA-Z0-9_\.]+)'
    ]:
        cols = re.findall(pattern, sql)
        columns.extend(cols)
    
    # Loại bỏ trùng lặp và từ khóa SQL
    sql_keywords = ["from", "as", "where", "and", "or", "not", "in", "exists", "asc", "desc"]
    clean_columns = []
    
    for col in columns:
        # Bỏ qua các từ khóa SQL
        if col.lower() in sql_keywords:
            continue
            
        # Làm sạch tên cột (bỏ tên bảng nếu có)
        if "." in col:
            table_name, col_name = col.split(".")
            clean_columns.append(col_name)
        else:
            clean_columns.append(col)
    
    # Loại bỏ trùng lặp
    clean_columns = list(set(clean_columns))
    
    # Xác định loại biểu đồ nếu là intent visualization
    visualization_type = None
    if best_intent == "visualization":
        for viz_type, patterns in viz_patterns.items():
            for pattern in patterns:
                if pattern in question:
                    visualization_type = viz_type
                    break
            if visualization_type:
                break
        
        # Mặc định là bar chart nếu không xác định được
        if not visualization_type:
            visualization_type = "bar"
    
    # Tạo kết quả
    result = {
        "query": question,
        "intent": best_intent,
        "entities": {
            "operation": operation
        }
    }
    
    if clean_columns:
        result["entities"]["columns"] = clean_columns
    
    if visualization_type:
        result["visualization_type"] = visualization_type
    
    return result

# Chuyển đổi và lưu dữ liệu
intent_samples = []
for item in train_data:
    try:
        result = detect_intent(item["question"], item["query"], item.get("db_id"))
        intent_samples.append(result)
    except Exception as e:
        print(f"Error processing question: {item['question']}, Error: {str(e)}")

# Thêm dữ liệu visualization vì Spider thiếu intent này
visualization_samples = [
    {"query": "Show me a bar chart of product sales", "intent": "visualization", "visualization_type": "bar", "entities": {"operation": "visualize", "columns": ["product", "sales"]}},
    {"query": "Plot a line chart of sales over time", "intent": "visualization", "visualization_type": "line", "entities": {"operation": "visualize", "columns": ["sales", "date"]}},
    {"query": "Display pie chart of market share by region", "intent": "visualization", "visualization_type": "pie", "entities": {"operation": "visualize", "columns": ["market_share", "region"]}},
    {"query": "Create a scatter plot of price vs rating", "intent": "visualization", "visualization_type": "scatter", "entities": {"operation": "visualize", "columns": ["price", "rating"]}},
    {"query": "Visualize the distribution of ages", "intent": "visualization", "visualization_type": "histogram", "entities": {"operation": "visualize", "columns": ["age"]}},
    {"query": "Draw a bar chart showing sales by department", "intent": "visualization", "visualization_type": "bar", "entities": {"operation": "visualize", "columns": ["sales", "department"]}},
    {"query": "Generate a pie chart of expenses by category", "intent": "visualization", "visualization_type": "pie", "entities": {"operation": "visualize", "columns": ["expenses", "category"]}},
    {"query": "Create a line chart showing revenue trends", "intent": "visualization", "visualization_type": "line", "entities": {"operation": "visualize", "columns": ["revenue", "date"]}},
    {"query": "Make a bar graph of customer count by country", "intent": "visualization", "visualization_type": "bar", "entities": {"operation": "visualize", "columns": ["customer_count", "country"]}},
    {"query": "Plot a histogram of employee salaries", "intent": "visualization", "visualization_type": "histogram", "entities": {"operation": "visualize", "columns": ["salary"]}},
]

# Thêm vào dữ liệu gốc
intent_samples.extend(visualization_samples)

# Thêm dữ liệu insight vì Spider thiếu intent này
insight_samples = [
    {"query": "What are the key insights from this data?", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "Summarize the important findings in this dataset", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "Show me the most significant patterns in sales data", "intent": "insight", "entities": {"operation": "insight", "columns": ["sales"]}},
    {"query": "What interesting trends can you find in this data?", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "What are the key takeaways from this dataset?", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "Highlight the important aspects of this data", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "Give me an overview of what this data tells us", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "What stands out in this dataset?", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "Identify the main points in this data", "intent": "insight", "entities": {"operation": "insight"}},
    {"query": "What should I know about this dataset?", "intent": "insight", "entities": {"operation": "insight"}},
]

# Thêm vào dữ liệu gốc
intent_samples.extend(insight_samples)

# Thêm dữ liệu prediction vì Spider thiếu intent này
prediction_samples = [
    {"query": "Predict the sales for next month", "intent": "prediction", "entities": {"operation": "predict", "columns": ["sales"]}},
    {"query": "Forecast revenue for the next quarter", "intent": "prediction", "entities": {"operation": "predict", "columns": ["revenue"]}},
    {"query": "What will be the expected growth next year?", "intent": "prediction", "entities": {"operation": "predict", "columns": ["growth"]}},
    {"query": "Can you estimate future customer acquisition?", "intent": "prediction", "entities": {"operation": "predict", "columns": ["customer_acquisition"]}},
    {"query": "Predict the trend for these values", "intent": "prediction", "entities": {"operation": "predict"}},
    {"query": "How will these numbers evolve in the coming months?", "intent": "prediction", "entities": {"operation": "predict"}},
    {"query": "What's the projected value for Q4?", "intent": "prediction", "entities": {"operation": "predict"}},
    {"query": "Give me a forecast of demand for next season", "intent": "prediction", "entities": {"operation": "predict", "columns": ["demand"]}},
    {"query": "Predict how price changes will affect sales", "intent": "prediction", "entities": {"operation": "predict", "columns": ["price", "sales"]}},
    {"query": "What is the expected outcome if we continue this trend?", "intent": "prediction", "entities": {"operation": "predict"}},
]

# Thêm vào dữ liệu gốc
intent_samples.extend(prediction_samples)

# Xáo trộn dữ liệu
random.shuffle(intent_samples)

# Chia tập huấn luyện/kiểm tra
split_idx = int(len(intent_samples) * 0.9)
train_samples = intent_samples[:split_idx]
test_samples = intent_samples[split_idx:]

# Lưu tập huấn luyện và kiểm tra
with open("data/lora_training.jsonl", "w", encoding="utf-8") as f:
    for sample in train_samples:
        f.write(json.dumps(sample, ensure_ascii=False) + "\n")

with open("data/lora_testing.jsonl", "w", encoding="utf-8") as f:
    for sample in test_samples:
        f.write(json.dumps(sample, ensure_ascii=False) + "\n")

# Phân tích phân bố intent
intent_counts = {}
for sample in intent_samples:
    intent = sample["intent"]
    intent_counts[intent] = intent_counts.get(intent, 0) + 1

print("\nIntent distribution:")
for intent, count in intent_counts.items():
    print(f"{intent}: {count} samples ({count/len(intent_samples)*100:.2f}%)")

print(f"\nTotal: {len(intent_samples)} samples")
print(f"Training: {len(train_samples)} samples")
print(f"Testing: {len(test_samples)} samples")