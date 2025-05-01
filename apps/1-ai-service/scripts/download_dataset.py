import os
import json
from datasets import load_dataset
from typing import Dict, List

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Load CLINC intent dataset
print("Loading CLINC dataset...")
dataset = load_dataset("clinc_oos", "plus")

# Get the actual intent names from the dataset feature
# Dataset structure shows 'intent' is a ClassLabel with names
intent_names = dataset['train'].features['intent'].names
print(f"Found {len(intent_names)} unique intents in the dataset")
print(f"Sample intents: {intent_names[:10]}")

# Comprehensive intent mapping with expanded categories
intent_mapping = {
    # Interaction Intents (Chào hỏi, tạm biệt)
    "greeting": "interaction",
    "goodbye": "interaction",
    "thank_you": "interaction",
    "yes": "interaction",
    "no": "interaction",
    "maybe": "interaction",
    "are_you_a_bot": "interaction",
    "what_is_your_name": "interaction",
    "what_can_i_ask_you": "interaction",
    "who_made_you": "interaction",
    "how_old_are_you": "interaction",
    "where_are_you_from": "interaction",
    "meaning_of_life": "interaction",
    "who_do_you_work_for": "interaction", 
    "what_are_your_hobbies": "interaction",
    "do_you_have_pets": "interaction",
    "tell_joke": "interaction",
    "fun_fact": "interaction",
    "repeat": "interaction",
    
    # Questions - mục hỏi đáp về dữ liệu
    "bill_balance": "question",
    "credit_limit": "question",
    "balance": "question",
    "routing": "question",
    "rewards_balance": "question",
    "credit_score": "question",
    "shopping_list": "question",
    "current_location": "question",
    "time": "question",
    "date": "question",
    "expiration_date": "question",
    "last_maintenance": "question",
    "roll_dice": "question",
    "flip_coin": "question",
    "definition": "question",
    "measurement_conversion": "question",
    "calculator": "question",
    "nutrition_info": "question",
    "calories": "question",
    "ingredient_substitution": "question",
    "ingredients_list": "question",
    "recipe": "question",
    "meal_suggestion": "question",
    "cook_time": "question",
    "food_last": "question",
    "bill_due": "question",
    "pto_balance": "question",
    "pto_used": "question",
    "payday": "question",
    "w2": "question",
    "mpg": "question",
    "distance": "question",
    "tire_pressure": "question",
    "restaurant_suggestion": "question",
    "translate": "question",
    "exchange_rate": "question",
    "next_holiday": "question",
    "weather": "question",
    "traffic": "question",
    
    # Visualizations - biểu đồ, trực quan hóa
    "transactions": "visualization",
    "spending_history": "visualization",
    "transfer": "visualization",
    "income": "visualization",
    "credit_limit_change": "visualization",
    "restaurant_reviews": "visualization",
    "calendar": "visualization",
    
    # Analysis - phân tích, so sánh
    "interest_rate": "analysis",
    "apr": "analysis",
    "taxes": "analysis",
    "min_payment": "analysis",
    "improve_credit_score": "analysis",
    "international_fees": "analysis",
    "gas_type": "analysis",
    "gas": "analysis",
    "oil_change_how": "analysis",
    "oil_change_when": "analysis",
    "tire_change": "analysis",
    "insurance": "analysis",
    "insurance_change": "analysis",
    "rollover_401k": "analysis",
    "international_visa": "analysis",
    
    # Insights - thông tin chuyên sâu
    "direct_deposit": "insight",
    "schedule_meeting": "insight",
    "meeting_schedule": "insight",
    "reminder": "insight",
    "calendar_update": "insight",
    "reminder_update": "insight",
    "todo_list": "insight",
    "todo_list_update": "insight",
    "smart_home": "insight",
    "sync_device": "insight",
    "play_music": "insight",
    "next_song": "insight",
    "update_playlist": "insight",
    "what_song": "insight",
    
    # Predictions - dự báo
    "freeze_account": "prediction",
    "report_fraud": "prediction",
    "travel_notification": "prediction",
    "order_status": "prediction",
    "travel_alert": "prediction",
    "application_status": "prediction",
    "flight_status": "prediction",
    "pto_request_status": "prediction",
    "lost_luggage": "prediction",
    "book_flight": "prediction",
    "book_hotel": "prediction",
    "carry_on": "prediction",
    "travel_suggestion": "prediction",
    "restaurant_reservation": "prediction",
    "accept_reservations": "prediction",
    "confirm_reservation": "prediction",
    "cancel_reservation": "prediction",
    "how_busy": "prediction",
    "car_rental": "prediction",
    "uber": "prediction"
}

# Prepare training data
training_data = []

# Keep track of unmapped intents
unmapped_intents = set()

# Create label mapping dictionary (index -> intent name)
label_mapping = {i: intent_name for i, intent_name in enumerate(intent_names)}

# Save label mapping for reference
with open("data/label_mapping.json", "w") as f:
    json.dump(label_mapping, f, indent=2)

for split in ['train', 'validation', 'test']:
    print(f"Processing {split} split...")
    for i, item in enumerate(dataset[split]):
        # Get the numerical intent from the item
        intent_id = item['intent']
        
        # Map to the actual intent name using the label_mapping
        intent_name = label_mapping[intent_id]
        
        # Map original intent to our custom intent types
        mapped_intent = intent_mapping.get(intent_name, 'unknown')
        
        if mapped_intent == 'unknown':
            unmapped_intents.add(intent_name)
        
        # Prepare training example
        example = {
            "query": item['text'],
            "intent": mapped_intent,
            "original_label": intent_name,
            "label_id": intent_id
        }
        
        # Add visualization type for visualization intents
        if mapped_intent == "visualization":
            # Simple visualization type mapping
            text_lower = item['text'].lower()
            if "transfer" in text_lower or "transactions" in text_lower:
                example["visualization_type"] = "bar"
            elif "spending" in text_lower or "history" in text_lower:
                example["visualization_type"] = "line"
            elif "income" in text_lower or "distribution" in text_lower:
                example["visualization_type"] = "pie"
            elif "compare" in text_lower or "correlation" in text_lower:
                example["visualization_type"] = "scatter"
            elif "calendar" in text_lower:
                example["visualization_type"] = "calendar"
            else:
                example["visualization_type"] = "bar"
        
        training_data.append(example)
        
        # Print progress for large datasets
        if i % 5000 == 0 and i > 0:
            print(f"  Processed {i} items from {split} split")

# Save to JSONL file
output_path = 'data/lora_training_v2.jsonl'
with open(output_path, 'w', encoding='utf-8') as f:
    for item in training_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\nDataset processed and saved to {output_path}")
print(f"Total training examples: {len(training_data)}")

# Print unmapped intents
print(f"\nUnmapped intents ({len(unmapped_intents)}):")
for intent in sorted(unmapped_intents):
    print(f"  - {intent}")

# Optional: Print some statistics
intent_counts = {}
original_label_counts = {}
for item in training_data:
    intent_counts[item['intent']] = intent_counts.get(item['intent'], 0) + 1
    original_label_counts[item['original_label']] = original_label_counts.get(item['original_label'], 0) + 1

print("\nIntent Distribution:")
for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{intent}: {count}")

# Check how many are unknown
unknown_pct = (intent_counts.get('unknown', 0) / len(training_data)) * 100
print(f"\nUnknown intents: {intent_counts.get('unknown', 0)} ({unknown_pct:.2f}%)")

print("\nTop 20 Original Label Distribution:")
for label, count in sorted(original_label_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
    print(f"{label}: {count}")

# Print a snippet of the training data for inspection
print("\nSample training examples:")
for i, example in enumerate(training_data[:5]):
    print(f"\nExample {i+1}:")
    print(f"  Query: {example['query']}")
    print(f"  Intent: {example['intent']}")
    print(f"  Original Label: {example['original_label']}")
    if example['intent'] == 'visualization' and 'visualization_type' in example:
        print(f"  Visualization Type: {example['visualization_type']}")