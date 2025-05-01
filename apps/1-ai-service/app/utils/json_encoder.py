import json
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from fastapi.encoders import jsonable_encoder
from datetime import datetime, date

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        elif isinstance(obj, pd.Series):
            return obj.to_list()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, (np.bool_)):
            return bool(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        return super().default(obj)

# 2. Hàm để đệ quy xử lý tất cả đối tượng pandas/numpy trong cấu trúc lồng nhau
def convert_special_types(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    elif isinstance(obj, pd.Series):
        return obj.to_list()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.number):
        return obj.item()
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_special_types(v) for k, v in obj.items()}
    elif isinstance(obj, list) or isinstance(obj, tuple):
        return [convert_special_types(i) for i in obj]
    elif hasattr(obj, 'model_dump'):
        return convert_special_types(obj.model_dump())
    return obj

# 3. Ghi đè jsonable_encoder của FastAPI 
def custom_jsonable_encoder(obj, **kwargs):
    # Đầu tiên xử lý các kiểu dữ liệu đặc biệt
    converted_obj = convert_special_types(obj)
    # Sau đó sử dụng jsonable_encoder ban đầu
    return jsonable_encoder(converted_obj, **kwargs)

# 4. Cấu hình cho FastAPI app
def configure_custom_json_serialization(app):
    """
    Cấu hình custom JSON serialization cho FastAPI app
    """
    # Ghi đè encoder của FastAPI
    import fastapi.encoders
    fastapi.encoders.jsonable_encoder = custom_jsonable_encoder
    
    # Cấu hình JSON_ENCODERS cho Pydantic
    from fastapi.responses import JSONResponse
    
    # Ghi đè phương thức render của JSONResponse
    original_render = JSONResponse.render
    
    def custom_render(content: Any, *args, **kwargs):
        # Xử lý đặc biệt trước khi render
        processed_content = convert_special_types(content)
        return original_render(processed_content, *args, **kwargs)
    
    JSONResponse.render = custom_render
    
    return app