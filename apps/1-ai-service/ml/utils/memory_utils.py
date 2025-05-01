import logging
import sys
from typing import Optional, Union, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

def estimate_dataframe_size(df: pd.DataFrame) -> float:
    """
    Ước tính kích thước của DataFrame trong bộ nhớ (MB)
    
    Args:
        df: DataFrame cần ước tính kích thước
        
    Returns:
        float: Kích thước ước tính (MB)
    """
    try:
        # Cách 1: Sử dụng memory_usage có sẵn của pandas
        memory_usage = df.memory_usage(deep=True).sum()
        memory_mb = memory_usage / (1024 * 1024)  # Convert bytes to MB
        
        return memory_mb
    except Exception as e:
        logger.warning(f"Error using pandas memory_usage: {str(e)}. Using alternative method.")
        
        # Cách 2: Ước tính thông qua kích thước của từng cột
        total_bytes = 0
        
        # Kích thước của index
        index_size = df.index.memory_usage()
        total_bytes += index_size
        
        # Tính kích thước của từng cột
        for col in df.columns:
            # Tính kích thước của mảng
            col_size = 0
            try:
                # Sử dụng nbytes nếu có sẵn (cho NumPy arrays)
                if hasattr(df[col], 'nbytes'):
                    col_size = df[col].nbytes
                else:
                    # Ước tính dựa trên kiểu dữ liệu
                    dtype = df[col].dtype
                    if pd.api.types.is_numeric_dtype(dtype):
                        bytes_per_element = dtype.itemsize
                        col_size = len(df) * bytes_per_element
                    elif pd.api.types.is_string_dtype(dtype):
                        # Ước tính cho string (giả sử trung bình 50 bytes/string)
                        sample = df[col].dropna().head(100)
                        if len(sample) > 0:
                            avg_size = sum(len(str(x).encode('utf-8')) for x in sample) / len(sample)
                            col_size = len(df) * avg_size
                        else:
                            col_size = len(df) * 50  # Giá trị mặc định
                    else:
                        # Kiểu khác (object, datetime, etc.)
                        col_size = len(df) * 100  # Giá trị ước tính thô
            except Exception as col_error:
                logger.warning(f"Error estimating column {col} size: {str(col_error)}")
                col_size = len(df) * 50  # Giá trị mặc định khi xảy ra lỗi
                
            total_bytes += col_size
        
        # Convert to MB
        memory_mb = total_bytes / (1024 * 1024)
        return memory_mb

def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tối ưu hóa bộ nhớ sử dụng bởi DataFrame bằng cách giảm kích thước các kiểu dữ liệu
    
    Args:
        df: DataFrame cần tối ưu
        
    Returns:
        pd.DataFrame: DataFrame đã được tối ưu bộ nhớ
    """
    # Tạo bản sao để không ảnh hưởng đến df gốc
    result = df.copy()
    
    # Ghi log kích thước ban đầu
    initial_size = estimate_dataframe_size(result)
    logger.info(f"Initial DataFrame size: {initial_size:.2f} MB")
    
    # Tối ưu cho các cột số nguyên
    int_columns = result.select_dtypes(include=['int']).columns
    for col in int_columns:
        # Lấy giá trị min, max
        col_min = result[col].min()
        col_max = result[col].max()
        
        # Chọn kiểu dữ liệu nhỏ nhất có thể chứa range giá trị
        if col_min >= 0:
            if col_max < 2**8:
                result[col] = result[col].astype(np.uint8)
            elif col_max < 2**16:
                result[col] = result[col].astype(np.uint16)
            elif col_max < 2**32:
                result[col] = result[col].astype(np.uint32)
            else:
                result[col] = result[col].astype(np.uint64)
        else:
            if col_min > -2**7 and col_max < 2**7:
                result[col] = result[col].astype(np.int8)
            elif col_min > -2**15 and col_max < 2**15:
                result[col] = result[col].astype(np.int16)
            elif col_min > -2**31 and col_max < 2**31:
                result[col] = result[col].astype(np.int32)
            else:
                result[col] = result[col].astype(np.int64)
    
    # Tối ưu cho các cột số thực
    float_columns = result.select_dtypes(include=['float']).columns
    for col in float_columns:
        # Kiểm tra nếu có thể dùng float32 thay vì float64
        result[col] = result[col].astype(np.float32)
    
    # Tối ưu cho các cột object/string
    obj_columns = result.select_dtypes(include=['object']).columns
    for col in obj_columns:
        # Nếu số lượng giá trị unique nhỏ, sử dụng categorical
        num_unique = result[col].nunique()
        if num_unique < len(result) * 0.5:  # Nếu unique values < 50% tổng số rows
            result[col] = result[col].astype('category')
    
    # Ghi log kích thước sau khi tối ưu
    optimized_size = estimate_dataframe_size(result)
    memory_saved = initial_size - optimized_size
    saved_pct = (memory_saved / initial_size * 100) if initial_size > 0 else 0
    
    logger.info(f"Optimized DataFrame size: {optimized_size:.2f} MB")
    logger.info(f"Memory saved: {memory_saved:.2f} MB ({saved_pct:.1f}%)")
    
    return result

def check_memory_usage() -> dict:
    """
    Kiểm tra mức sử dụng bộ nhớ của hệ thống hiện tại
    
    Returns:
        dict: Thông tin về việc sử dụng bộ nhớ
    """
    try:
        import psutil
        
        # Memory info
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # GPU info if available
        gpu_info = {}
        try:
            import torch
            if torch.cuda.is_available():
                gpu_info["available"] = True
                gpu_info["count"] = torch.cuda.device_count()
                
                # Get GPU memory for each device
                gpu_info["devices"] = []
                for i in range(torch.cuda.device_count()):
                    device_info = {
                        "index": i,
                        "name": torch.cuda.get_device_name(i),
                        "total_memory_mb": torch.cuda.get_device_properties(i).total_memory / (1024 * 1024),
                        "allocated_memory_mb": torch.cuda.memory_allocated(i) / (1024 * 1024),
                        "reserved_memory_mb": torch.cuda.memory_reserved(i) / (1024 * 1024)
                    }
                    gpu_info["devices"].append(device_info)
            else:
                gpu_info["available"] = False
        except ImportError:
            gpu_info["available"] = False
            gpu_info["error"] = "PyTorch not installed"
        except Exception as e:
            gpu_info["available"] = False
            gpu_info["error"] = str(e)
        
        return {
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent_used": memory.percent,
            },
            "swap": {
                "total_gb": swap.total / (1024**3),
                "used_gb": swap.used / (1024**3),
                "percent_used": swap.percent if swap.total > 0 else 0
            },
            "cpu": {
                "percent_used": cpu_percent,
                "cores": cpu_count
            },
            "gpu": gpu_info,
            "process": {
                "memory_gb": psutil.Process().memory_info().rss / (1024**3)
            }
        }
    except ImportError:
        logger.warning("psutil not installed, cannot get detailed memory usage")
        
        # Fallback to simpler info
        memory_info = {
            "memory": {
                "available": "Unknown (psutil not installed)"
            },
            "process": {
                "memory_mb": sys.getsizeof(0) / (1024 * 1024)  # Just to return something
            }
        }
        
        return memory_info
    except Exception as e:
        logger.error(f"Error checking memory usage: {str(e)}")
        return {"error": str(e)}

def chunk_dataframe(
    df: pd.DataFrame, 
    max_chunk_size_mb: float = 100, 
    min_rows_per_chunk: int = 1000
) -> List[pd.DataFrame]:
    """
    Chia DataFrame thành các chunks nhỏ hơn để xử lý
    
    Args:
        df: DataFrame cần chia
        max_chunk_size_mb: Kích thước tối đa của mỗi chunk (MB)
        min_rows_per_chunk: Số lượng hàng tối thiểu trong mỗi chunk
        
    Returns:
        List[pd.DataFrame]: Danh sách các DataFrame chunks
    """
    total_rows = len(df)
    
    if total_rows == 0:
        return []
    
    # Ước tính kích thước mỗi hàng
    row_size_mb = estimate_dataframe_size(df) / total_rows if total_rows > 0 else 0
    
    # Tính số lượng hàng tối đa cho mỗi chunk
    max_rows_per_chunk = int(max_chunk_size_mb / row_size_mb) if row_size_mb > 0 else total_rows
    
    # Đảm bảo mỗi chunk có ít nhất min_rows_per_chunk hàng
    rows_per_chunk = max(min_rows_per_chunk, max_rows_per_chunk)
    
    # Nếu toàn bộ DataFrame nhỏ hơn ngưỡng, trả về nguyên DataFrame
    if total_rows <= rows_per_chunk:
        return [df]
    
    # Tạo danh sách các chunks
    chunks = []
    for start_idx in range(0, total_rows, rows_per_chunk):
        end_idx = min(start_idx + rows_per_chunk, total_rows)
        chunk = df.iloc[start_idx:end_idx].copy()
        chunks.append(chunk)
    
    logger.info(f"Split DataFrame with {total_rows} rows into {len(chunks)} chunks")
    return chunks