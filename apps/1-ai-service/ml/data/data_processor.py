import logging, re
from typing import Dict, List, Optional, Tuple, Set

import numpy as np
import pandas as pd
import hashlib
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype
from sklearn.impute import KNNImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA

from ml.utils.datetime_utils import detect_datetime_columns, convert_to_datetime, analyze_datetime_distribution, is_datetime

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Enhanced data processor with advanced ML/DL capabilities, integrating features from:
    - Original DataProcessor
    - ColumnTypeDetector (merged)
    - EnhancedDataPipeline
    - Advanced ML techniques
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DataProcessor, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Khởi tạo cache và các thuộc tính khác"""
        self._cache = {}

    def __init__(self, config: Optional[Dict] = None):
        """Initialize processor with optional config"""
        self.config = config or {}

        self.max_category_threshold = self.config.get("data_processing", {}).get("categorical_threshold", 20)
        self.outlier_threshold = self.config.get("data_processing", {}).get("outlier_threshold", 3.0)
        self.missing_values_threshold = self.config.get("data_processing", {}).get("missing_values_threshold", 0.8)
        self.correlation_threshold = self.config.get("data_processing", {}).get("correlation_threshold", 0.7)
        
        self._label_encoders = {}
        self._scalers = {}
        self._pca_models = {}
        
        self.preprocessing_stats = {}
        self.column_types = {}
        self.feature_importance = {}
        
        self._compile_regex_patterns()
        
        logger.info("Enhanced DataProcessor initialized")

    def process(self, df: pd.DataFrame, 
               sample_size: Optional[int] = None,
               for_modeling: bool = False) -> pd.DataFrame:
        """
        Process data with options for analysis or modeling
        
        Args:
            df: Original DataFrame
            sample_size: Sample size if you want to reduce data size
            for_modeling: Whether to apply model preparation steps (encoding, normalization)
            
        Returns:
            Processed DataFrame
        """
        logger.info(f"Processing DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Phát hiện kiểu cột (luôn cần thiết)
        self.column_types = self.detect_column_types(df)
        logger.info(f"Detected column types: {self._summarize_column_types(df)}")
        
        # --- BƯỚC TIỀN XỬ LÝ CƠ BẢN (dành cho phân tích) ---
        
        # 1. Normalize column names
        df_processed = self.normalize_column_names(df)
        
        # Cập nhật column_types để khớp với tên cột đã normalize
        old_to_new_map = {old: new for old, new in zip(df.columns, df_processed.columns)}
        updated_column_types = {}
        
        for type_name, columns in self.column_types.items():
            updated_column_types[type_name] = [old_to_new_map.get(col, col) for col in columns]
        
        self.column_types = updated_column_types
        
        # 2. Sample if needed
        if sample_size and len(df_processed) > sample_size:
            df_processed = df_processed.sample(sample_size, random_state=42)
            logger.info(f"Sampled DataFrame to {len(df_processed)} rows")
        
        # 3. Remove duplicate columns
        df_processed = self.remove_duplicate_columns(df_processed)
        
        # 4. Handle missing values
        df_processed = self._handle_missing_values(df_processed)
        
        # 5. Handle outliers
        df_processed = self._handle_outliers(df_processed)
        
        # 6. Convert data types (không encoding)
        df_processed = self._convert_data_types(df_processed)
        
        # 7. Chỉ chuyển đổi binary_columns trong trường hợp đặc biệt
        # Ví dụ: Convert "Yes"/"No" → True/False (không phải 1/0)
        if self._should_convert_binary(df_processed):
            df_processed = self._convert_binary_to_boolean(df_processed)
        
        # 8. Extract datetime features
        df_processed = self._extract_datetime_features(df_processed)
        
        # --- NẾU CHỈ PHÂN TÍCH THÌ DỪNG Ở ĐÂY ---
        if not for_modeling:
            logger.info(f"Basic processing completed for analysis. Output DataFrame has {len(df_processed)} rows and {len(df_processed.columns)} columns")
            return df_processed
        
        # --- CÁC BƯỚC CHUẨN BỊ CHO MODEL (encoding, normalization) ---
        logger.info("Applying model preparation steps...")
        
        # 9. Encode categorical columns
        df_processed = self._encode_categorical_columns(df_processed)
        
        # 10. Convert binary columns to 0/1
        df_processed = self._convert_binary_columns(df_processed)
        
        # 11. Normalize numeric columns
        df_processed = self._normalize_numeric_columns(df_processed)
        
        # 12. Analyze features (feature importance)
        self._analyze_features(df_processed)
        
        logger.info(f"Model preparation completed. Output DataFrame has {len(df_processed)} rows and {len(df_processed.columns)} columns")
        return df_processed
    
    def get_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Lấy thông tin về kiểu dữ liệu của các cột.
        Sử dụng cache để tránh tính toán lại nếu đã phát hiện trước đó.
        
        Args:
            df: DataFrame cần phân tích
            
        Returns:
            Dict[str, List[str]]: Dictionary chứa danh sách cột theo từng kiểu
        """
        # Tạo hash key cho DataFrame
        df_hash = self._generate_df_hash(df)
        
        # Kiểm tra cache
        if df_hash in self._cache:
            logger.debug(f"Using cached column types for DataFrame hash: {df_hash}")
            return self._cache[df_hash]
        
        # Phát hiện kiểu dữ liệu nếu chưa có trong cache
        column_types = self.detect_column_types(df)
        
        # Lưu vào cache
        self._cache[df_hash] = column_types
        
        return column_types
    
    def _should_convert_binary(self, df: pd.DataFrame) -> bool:
        """Kiểm tra xem có nên convert binary về Boolean hay không"""
        binary_cols = self.column_types.get("binary", [])
        if not binary_cols:
            return False
        
        # Nếu có ít nhất một cột chứa chuỗi "Yes"/"No" thì nên convert
        for col in binary_cols:
            if col not in df.columns:
                continue
                
            unique_vals = set(df[col].dropna().astype(str).str.lower())
            if any(val in {"yes", "no", "true", "false", "có", "không"} for val in unique_vals):
                return True
        
        return False
        
    def _convert_binary_to_boolean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert binary columns to Boolean (True/False)"""
        df_result = df.copy()
        binary_cols = self.column_types.get("binary", [])
        
        if not binary_cols:
            return df_result
        
        conversion_stats = {}
        
        true_values = {"yes", "y", "true", "t", "1", 1, 1.0, "có", "co", "đúng", "dung", "ok"}
        false_values = {"no", "n", "false", "f", "0", 0, 0.0, "không", "khong", "sai", "none"}
        
        for col in binary_cols:
            if col not in df_result.columns:
                continue
                
            try:
                if pd.api.types.is_categorical_dtype(df_result[col]):
                    series_str = df_result[col].astype(str)
                    
                    bool_series = pd.Series(False, index=df_result.index)
                    
                    for val in true_values:
                        bool_series = bool_series | (series_str.str.lower() == str(val).lower())
                    
                    df_result[col] = bool_series.astype(bool)
                else:
                    mapping = {}
                    for val in df_result[col].unique():
                        if pd.isna(val):
                            continue
                        
                        norm_val = val
                        if isinstance(val, str):
                            norm_val = val.lower().strip()
                            
                        if norm_val in true_values:
                            mapping[val] = True
                        elif norm_val in false_values:
                            mapping[val] = False
                    
                    if mapping:
                        df_result[col] = df_result[col].map(mapping).fillna(df_result[col])
                        conversion_stats[col] = {
                            "from": str(df[col].dtype),
                            "to": "boolean", 
                            "method": "mapping",
                            "mapping": {str(k): bool(v) for k, v in mapping.items()}
                        }
                        
            except Exception as e:
                logger.warning(f"Binary to Boolean conversion failed for {col}: {str(e)}")
        
        # Lưu thống kê
        self.preprocessing_stats.setdefault("type_conversion", {}).update(conversion_stats)
        
        return df_result

    def _compile_regex_patterns(self):
        """Pre-complie regex patterns for better performance"""
        self.email_pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]\.[a-zA-Z0-9-.]+$')
        self.phone_pattern = re.compile(r'^(\+?(84|1|44)|0)?[\s.-]?\(?\d{2,4}\)?([\s.-]?\d{3,4}){2,3}$')
        self.url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
        self.id_term_regex = re.compile(r'\b(id|uuid|guid|key|code|sku|_id|index)\b', re.IGNORECASE)
        self.gender_term_regex = re.compile(r'\b(gender|sex|male|female|nam|nữ|boy|girl|man|woman|m|f|men|women)\b', re.IGNORECASE)
        self.email_term_regex = re.compile(r'\b(e[-_]?mail|email|mail)\b', re.IGNORECASE)
        self.phone_term_regex = re.compile(r'\b(phone|tel|mobile|cell|số[\s_]?điện[\s_]?thoại)\b', re.IGNORECASE)
        self.address_term_regex = re.compile(r'\b(address|addr|street|road|avenue|drive|lane|place|city|town|country|postcode|state|zip|postal|địa[\s_]?chỉ|đường|phố|quận|huyện|tỉnh|thành[\s_]?phố|phường|xã)\b', re.IGNORECASE)
        self.name_term_regex = re.compile(r'\b(name|first[\s_]?name|last[\s_]?name|full[\s_]?name|tên|họ|họ[\s_]?tên|họ[\s_]?và[\s_]?tên)\b', re.IGNORECASE)
        self.url_term_regex = re.compile(r'\b(url|link|website|site|web)\b', re.IGNORECASE)
        self.range_term_regex = re.compile(r'\b(range|interval|period|between|from|to|duration|time|span|length|distance|limit|min(imum)?|max(imum)?|bounds|threshold)\b', re.IGNORECASE)
        self.likert_term_regex = re.compile(r'(scale|rating|score|satisfaction|agreement|level|thang[\s_]?đo|đánh[\s_]?giá|mức[\s_]?độ|hài[\s_]?lòng|đồng[\s_]?ý)',re.IGNORECASE)

        self.non_negative_regex = re.compile(r'\b(age|height|weight|duration|time(_(spent|elapsed|taken|sec|secs|second|seconds|min|mins|minute|minutes|hr|hrs|hour|hours))?|timestamp|year|years|day|days|month|months|week|weeks|score|count|total|quantity|amount|size|distance|length)\b', re.IGNORECASE)

    def _summarize_column_types(self, df: pd.DataFrame) -> Dict[str, int]:
        """Create summary of the number of columns of each type"""

        if not self.column_types:
            self.column_types = self.get_column_types(df)

        total_columns = sum(len(cols) for cols in self.column_types.values())
        summary = {}

        for col_type, cols in self.column_types.items():
            if not cols:
                continue
            summary[col_type] = {
                "count": len(cols),
                "percentage": f"{round(len(cols) * 100 / total_columns, 1)}%",
                "columns": cols
            }

        return summary
    
    def detect_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Detect column types in DataFrame
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dict[str, List[str]]: Dictionary with column type as key and list of column names as value
        """
        column_types = {
            "numeric": [],
            "categorical": [],
            "datetime": [],
            "text": [],
            "binary": [],
            "id": [],
            "gender": [],
            "email": [],
            "phone": [],
            "address": [],
            "range": [],
            "name": [],
            "url": [],
            "likert": []
        }

        column_types["id"] = self._detect_id_columns(df)

        column_types["datetime"] = detect_datetime_columns(df)

        column_types["binary"] = self._detect_binary_columns(df)

        column_types["likert"] = self._detect_likert_scales(df)

        skip_columns = set(column_types["id"]) | set(column_types["datetime"]) | set(column_types["binary"]) | set(column_types["likert"])

        for col in df.columns:
            if col in skip_columns:
                continue
            
            try:
                if is_numeric_dtype(df[col]):
                    column_types["numeric"].append(col)
                elif df[col].dtype == 'object' or df[col].dtype.name == 'category':
                    handled_series = df[col].dropna()
                    if len(handled_series) == 0:
                        column_types["categorical"].append(col)
                        continue
                        
                    try:
                        sample = handled_series.sample(min(1000, len(handled_series)))

                        if self._is_email_column(sample, col):
                            column_types["email"].append(col)
                        elif self._is_phone_column(sample, col):
                            column_types["phone"].append(col)
                        elif self._is_gender_column(sample, col):
                            column_types["gender"].append(col)
                        elif self._is_range_column(sample, col):
                            column_types["range"].append(col)
                        elif self._is_address_column(sample, col):
                            column_types["address"].append(col)
                        elif self._is_name_column(sample, col):
                            column_types["name"].append(col)
                        elif self._is_url_column(sample, col):
                            column_types["url"].append(col)
                        elif sample.nunique() <= min(20, len(df) * 0.1):
                            column_types["categorical"].append(col)
                        else:
                            column_types["text"].append(col)
                    except (AttributeError, TypeError):
                        if handled_series.nunique() <= min(20, len(df) * 0.1):
                            column_types["categorical"].append(col)
                        else:
                            column_types["text"].append(col)
            except Exception as e:
                logger.warning(f"Error detecting column type for {col}: {str(e)}")
                # Default to categorical as a fallback
                column_types["categorical"].append(col)

        return column_types


    def _detect_id_columns(self, df: pd.DataFrame, threshold: float = 0.9) -> List[str]:
        """
        Detect ID columns based on heuristics

        Args:
            df: Original DataFrame
            threshold: Threshold ratio of unique values to identify ID
        
        Returns:
            List[str]: List of ID columns
        """
        id_columns = set()

        n_unique = df.nunique()
        n_rows = len(df)
        unique_ratios = n_unique / n_rows if n_rows > 0 else 0

        for col in df.columns:
            unique_ratio = unique_ratios[col]
            if unique_ratio > threshold:
                if is_numeric_dtype(df[col]):
                    id_columns.add(col)
                elif self.id_term_regex.search(col):
                    id_columns.add(col)
            elif unique_ratio > 0.95 and n_rows > 100:
                id_columns.add(col)

        return list(id_columns)

    def _detect_binary_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Phát hiện cột binary thực sự (chỉ có 2 giá trị phân biệt)

        Args:
            df: Original DataFrame
        
        Returns:
            List[str]: List of binary columns
        """
        binary_cols = []
        binary_mappings = {}

        true_vals = {
            1, 1.0, "1", "1.0", 
            "yes", "y", "true", "t", 
            "có", "co", "đúng", "dung", 
            "ok", "agree", "approved", "success", "pass",
            "đồng ý", "dong y", "chấp nhận", "chap nhan"
        }

        false_vals = {
            0, 0.0, "0", "0.0", 
            "no", "n", "false", "f", 
            "không", "khong", "sai", 
            "reject", "fail", "denied", "cancel",
            "từ chối", "tu choi", "hủy", "huy", "none"
        }

        binary_val_set = true_vals.union(false_vals)

        for col in df.columns:
            if col in self.column_types.get("id", []) or col in self.column_types.get("datetime", []):
                continue

            try:
                unique_vals = set(df[col].dropna().unique())

                if len(unique_vals) == 0:
                    continue
                    
                if len(unique_vals) > 2:
                    continue

                if is_numeric_dtype(df[col]):
                    numerical_vals = set()
                    
                    for val in unique_vals:
                        try:
                            num_val = float(val)
                            numerical_vals.add(num_val)
                        except (ValueError, TypeError):
                            pass
                    
                    if len(numerical_vals) == 2 and all(abs(val) < 1e-10 or abs(val - 1) < 1e-10 for val in numerical_vals):
                        binary_cols.append(col)
                        continue
                    else:
                        continue

                normalized_vals = set()
                for val in unique_vals:
                    if isinstance(val, str):
                        normalized_vals.add(val.lower().strip())
                    else:
                        normalized_vals.add(val)
                
                if len(normalized_vals) == 2 and all(val in binary_val_set for val in normalized_vals):
                    binary_cols.append(col)
                    
                    mapping = {}
                    for val in unique_vals:
                        norm_val = val.lower().strip() if isinstance(val, str) else val
                        if norm_val in true_vals:
                            mapping[val] = 1
                        elif norm_val in false_vals:
                            mapping[val] = 0
                    
                    binary_mappings[col] = mapping
                
            except Exception as e:
                logger.debug(f"Error detecting binary for column {col}: {str(e)}")
        
        self._binary_mappings = binary_mappings
        
        return binary_cols
    
    def _detect_likert_scales(self, df: pd.DataFrame) -> List[str]:
        """
        Phát hiện các cột thang đo Likert scale (ví dụ: 1-5, 1-7, 1-10)
        
        Args:
            df: DataFrame để phân tích
            
        Returns:
            List[str]: Danh sách các cột thang đo Likert
        """
        likert_cols = []
        numeric_cols = [col for col in df.columns if is_numeric_dtype(df[col])]
        
        for col in numeric_cols:
            if col in self.column_types.get("id", []) or col in self.column_types.get("datetime", []):
                continue
            
            try:
                unique_vals = sorted(df[col].dropna().unique())
                
                if 3 <= len(unique_vals) <= 10:
                    if all(isinstance(val, (int, float)) for val in unique_vals):
                        num_vals = [float(val) for val in unique_vals]
                        
                        is_consecutive = True
                        for i in range(1, len(num_vals)):
                            if not (0.9 <= num_vals[i] - num_vals[i-1] <= 1.1):
                                is_consecutive = False
                                break
                        
                        starts_near_one = 0.9 <= num_vals[0] <= 1.1
                        
                        ends_in_range = 2.9 <= num_vals[-1] <= 10.1
                        
                        if (is_consecutive and starts_near_one and ends_in_range) or self.likert_term_regex.search(col):

                            likert_cols.append(col)
            except Exception as e:
                logger.debug(f"Error detecting Likert scale for column {col}: {str(e)}")
            
        return likert_cols

    def _is_gender_column(self, series: pd.Series, col_name: str) -> bool:
        """Check if column is gender type"""
        if self.gender_term_regex.search(col_name):
            return True
        
        values = series.dropna().astype(str).str.lower().unique()

        if len(values) >= 2 and len(values) <= 5 and sum(1 for v in values if self.gender_term_regex.search(v)) >= 2:
            return True
        
        return False
    
    def _is_email_column(self, series: pd.Series, col_name: str) -> bool:
        """Check if column is email type"""
        if self.email_term_regex.search(col_name):
            return True
        
        if len(series) > 0:
            try:
                if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
                    matches = series.str.match(self.email_pattern)
                    match_ratios = matches.mean()

                    if match_ratios > 0.9:
                        return True
            except (AttributeError, TypeError):
                pass
        
        return False

    def _is_phone_column(self, series: pd.Series, col_name: str) -> bool:
        if self.phone_term_regex.search(col_name):
            return True
        
        if len(series) > 0:
            try:
                # Check if the series contains string values before using str accessor
                if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
                    matches = series.str.match(self.phone_pattern)
                    match_ratio = matches.mean()

                    if match_ratio > 0.9:
                        return True
            except (AttributeError, TypeError):
                pass
    
        return False
    
    def _is_address_column(self, series: pd.Series, col_name: str) -> bool:
        if self.address_term_regex.search(col_name):
            return True

        try:
            if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
                return False

            # Preprocess: lowercase once
            series_lower = series.str.lower()

            avg_len = series_lower.str.len().mean()
            if avg_len < 10:
                return False

            # Define patterns using non-capturing groups
            patterns = {
                'us_house_number': r'(?:^|\s)\d+\s+[a-z0-9\s]+(?:\s|,|$)',
                'us_zip': r'(?:^|\s)\d{5}(?:-\d{4})?(?:\s|,|$)',
                'us_state': r'(?:^|\s)[a-z]{2}(?:\s|,|$)',
                'uk_postcode': r'[a-z]{1,2}[0-9][a-z0-9]?\s?[0-9][a-z]{2}',
                'vn_district': r'(?:quận|huyện)\s+[0-9a-zà-ỹ\s]+',
                'vn_ward': r'(?:phường|xã)\s+[0-9a-zà-ỹ\s]+',
                'vn_city': r'(?:tỉnh|thành phố|tp\.?)\s+[a-zà-ỹ\s]+'
            }

            # Calculate match scores
            pattern_scores = {
                name: series_lower.str.contains(pattern, regex=True).mean()
                for name, pattern in patterns.items()
            }

            # Aggregate scores
            us_score = pattern_scores['us_house_number'] * 2 + pattern_scores['us_zip'] * 3 + pattern_scores['us_state']
            uk_score = pattern_scores['uk_postcode'] * 3
            vn_score = pattern_scores['vn_district'] * 2 + pattern_scores['vn_ward'] * 2 + pattern_scores['vn_city'] * 2

            # Extra features
            house_number_pattern = series_lower.str.contains(r'(?:^|\s)\d+\s+[a-zà-ỹ]+', regex=True).mean()
            comma_separated = series_lower.str.count(',').mean()

            overall_score = max(us_score, uk_score, vn_score) + house_number_pattern * 2 + min(comma_separated, 3) * 0.5

            return overall_score > 1.0

        except (AttributeError, TypeError):
            return False

    
    def _is_range_column(self, series: pd.Series, col_name: str) -> bool:
        """
        Kiểm tra nếu cột chứa dữ liệu phạm vi giá trị (ranges, thresholds, bounds)
        """
        if self.range_term_regex.search(col_name):
            return True
        
        try:
            # Check if the series contains string values before using str accessor
            if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
                return False
                
            has_hyphen_range = series.str.contains(r'\d+\s*[-–—]\s*\d+').mean()
            has_to_range = series.str.lower().str.contains(r'\d+\s+(?:to|đến)\s+\d+').mean()
            comparison_patterns = {
                'less_than': r'(?:less|fewer|smaller|lower)\s+than\s+\d+',
                'less_than_vi': r'(?:nhỏ|ít|thấp)\s+(?:hơn|dưới)\s+\d+',

                'more_than': r'(?:more|greater|larger|higher|bigger)\s+than\s+\d+',
                'more_than_vi': r'(?:lớn|nhiều|cao)\s+(?:hơn|trên)\s+\d+',

                'less_equal': r'(?:less|fewer|smaller|lower)\s+than\s+(?:or\s+equal\s+to\s+)?\d+',
                'max': r'(?:maximum|max|up to|not more than|no more than|at most)\s+\d+',
                'less_equal_vi': r'(?:không\s+quá|tối\s+đa|nhiều\s+nhất|cao\s+nhất)\s+\d+',

                'more_equal': r'(?:more|greater|larger|higher)\s+than\s+(?:or\s+equal\s+to\s+)?\d+',
                'min': r'(?:minimum|min|at least|no less than|not less than)\s+\d+',
                'more_equal_vi': r'(?:ít\s+nhất|tối\s+thiểu|thấp\s+nhất)\s+\d+',

                'between': r'between\s+\d+\s+and\s+\d+',
                'between_vi': r'(?:trong\s+khoảng|trong\s+phạm\s+vi|giữa)\s+\d+\s+(?:và|và\s+giữa|đến)\s+\d+',

                'symbol_less': r'[<≤]\s*\d+',
                'symbol_more': r'[>≥]\s*\d+',
                'symbol_range': r'\d+\s*[<≤]\s*[^<>≤≥]+\s*[<≤]\s*\d+',

                'from_upwards': r'from\s+\d+\s+(?:upwards|up|and\s+above)?',
                'from_upwards_vi': r'từ\s+\d+\s+(?:trở\s+lên|trở\s+đi)?'
            }

            
            pattern_scores = {}
            for name, pattern in comparison_patterns.items():
                pattern_scores[name] = series.str.lower().str.contains(pattern, regex=True).mean()
            
            has_comparison = any(score > 0.2 for score in pattern_scores.values())
            
            if has_hyphen_range > 0.4 or has_to_range > 0.4 or has_comparison:
                return True
            
            total_comparison_score = sum(pattern_scores.values())
            if total_comparison_score > 0.3:
                return True
            
            units = [
                'percent', '%', 'kg', 'g', 'lb', 'oz', 'm', 'km', 'cm', 'mm', 'inch', 'ft', 
                'liter', 'ml', 'hour', 'minute', 'second', 'day', 'week', 'month', 'year',
                'vnd', 'usd', 'eur', '$', '€', '₫', 'đồng', 'dollar'
            ]
            
            unit_pattern = '|'.join([r'\d+\s*' + re.escape(unit) for unit in units])
            has_units = series.str.lower().str.contains(unit_pattern, regex=True).mean()
            
            if has_units > 0.5 and (has_hyphen_range > 0.1 or has_to_range > 0.1 or total_comparison_score > 0.1):
                return True
            
            return False
        except (AttributeError, TypeError):
            return False

    def _is_name_column(self, series: pd.Series, col_name: str) -> bool:
        """Check if column is person name type"""
        if self.name_term_regex.search(col_name):
            return True
        
        try:
            # Check if the series contains string values before using str accessor
            if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
                return False
                
            word_counts = series.str.split().str.len()
            avg_words = word_counts.mean()

            contains_digits = series.str.contains(r'\d').mean()

            if 1 <= avg_words <= 4 and contains_digits < 0.05:
                return True

            return False
        except (AttributeError, TypeError):
            return False
    
    def _is_url_column(self, series: pd.Series, col_name: str) -> bool:
        """Check if column is url"""
        if self.url_term_regex.search(col_name):
            return True
        
        try:
            # Check if the series contains string values before using str accessor
            if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
                return False
                
            if len(series) > 0:
                matches = series.str.match(self.url_pattern)
                match_ratio = matches.mean()

                if match_ratio > 0.9:
                    return True
            
            return False
        except (AttributeError, TypeError):
            return False

    
    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names"""
        new_columns = {}
        for col in df.columns:
            new_col = str(col).lower()
            new_col = re.sub(r'\s+', ' ', new_col.strip())
            new_col = re.sub(r'\s+([!?])', r'\1', new_col)
            new_col = new_col.replace(' ', '_')
            new_col = re.sub(r'[^a-z0-9_]', '', new_col)

            base_col = new_col
            counter = 1

            # Chỉ thêm counter nếu cần thiết
            while new_col in new_columns.values():
                counter += 1
                new_col = f"{base_col}_{counter}"

            # Kiểm tra nếu bắt đầu bằng số
            if new_col and new_col[0].isdigit():
                new_col = f"col_{new_col}"
            
            if not new_col:
                new_col = f"column_{df.columns.get_loc(col)}"

            new_columns[col] = new_col

        return df.rename(columns=new_columns)
    
    def remove_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate columns using efficient hashing and equality checking
        
        Args:
            df: Original DataFrame
        
        Returns:
            pd.DataFrame: DataFrame with duplicate columns removed
        """
        if len(df.columns) <= 1:
            return df
        
        if len(df.columns) <= 30:
            dup_cols = {}
            columns = df.columns

            for i, col1 in enumerate(columns):
                for col2 in columns[i+1:]:
                    if col1 != col2 and col1 not in dup_cols and col2 not in dup_cols:
                        if df[col1].equals(df[col2]):
                            dup_cols[col2] = col1

        else:
            dup_cols = {}
            col_signatures = {}

            for col in df.columns:
                try:
                    col_hash = pd.util.hash_array(df[col].fillna(pd.NA).values)
                except AttributeError:
                    col_hash = hash(tuple(df[col].fillna(0).values.tolist()))
                    
                signature = hash(col_hash)
                
                if signature in col_signatures:
                    for existing_col in col_signatures[signature]:
                        if df[col].equals(df[existing_col]):
                            dup_cols[col] = existing_col
                            break
                    else:
                        col_signatures.setdefault(signature, []).append(col)
                else:
                    col_signatures[signature] = [col]

        if dup_cols:
            df = df.drop(columns=list(dup_cols.keys()))
        
        return df
    
    def detect_duplicate_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Phát hiện các cột trùng lặp trong dataset mà không thay đổi DataFrame
        
        Args:
            df: DataFrame cần kiểm tra
            
        Returns:
            Dict[str, str]: Dictionary với key là tên cột trùng lặp, value là cột gốc
        """
        dup_cols = {}
        
        if len(df.columns) <= 1:
            return dup_cols
        
        if len(df.columns) <= 30:
            columns = df.columns

            for i, col1 in enumerate(columns):
                for col2 in columns[i+1:]:
                    if col1 != col2 and col1 not in dup_cols and col2 not in dup_cols:
                        if df[col1].equals(df[col2]):
                            dup_cols[col2] = col1
        else:
            col_signatures = {}

            for col in df.columns:
                try:
                    col_hash = pd.util.hash_array(df[col].fillna(pd.NA).values)
                except AttributeError:
                    col_hash = hash(tuple(df[col].fillna(0).values.tolist()))
                    
                signature = hash(col_hash)
                
                if signature in col_signatures:
                    for existing_col in col_signatures[signature]:
                        if df[col].equals(df[existing_col]):
                            dup_cols[col] = existing_col
                            break
                    else:
                        col_signatures.setdefault(signature, []).append(col)
                else:
                    col_signatures[signature] = [col]
        
        return dup_cols

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values with advanced imputation"""
        missing_stats = {}
        columns_to_drop = []
        column_transforms = {}

        missing_counts = df.isna().sum()
        missing_pcts = missing_counts / len(df) * 100

        total_missing = missing_counts.sum()
        missing_stats["total_before"] = total_missing
        missing_stats["percent_before"] = total_missing / (len(df) * len(df.columns)) * 100

        for col in df.columns:
            missing_count = missing_counts[col]
            if missing_count == 0:
                continue

            missing_pct = missing_pcts[col]
            missing_stats[col] = {
                "count": int(missing_count),
                "percent": float(missing_pct)
            }

            if missing_pct > self.missing_values_threshold * 100:
                columns_to_drop.append(col)
                missing_stats[col]["action"] = "drop_column"
            elif missing_pct > 50:
                if is_numeric_dtype(df[col]):
                    if self.non_negative_regex.search(col):
                        column_transforms[col] = {
                            "action": "fill_value",
                            "value": 0
                        }
                    else:
                        column_transforms[col] = {
                            "action": "fill_value",
                            "value": -999
                        }
                    missing_stats[col]["action"] = "fill_special_value"
                else:
                    missing_stats[col]["action"] = "keep_na"
            else:
                if is_numeric_dtype(df[col]):
                    if len(df) > 100 and missing_pct < 30:
                        try:
                            numeric_cols = self.column_types["numeric"]
                            numeric_cols = [c for c in numeric_cols if c != col and 
                                        missing_pcts.get(c, 0) < 30]
                            
                            if len(numeric_cols) >= 2:
                                column_transforms[col] = {"action": "knn_impute", "columns": numeric_cols}
                                missing_stats[col]["action"] = "knn_impute"
                            else:
                                column_transforms[col] = {"action": "median_impute"}
                                missing_stats[col]["action"] = "median_impute"
                        except Exception as e:
                            logger.warning(f"KNN imputation failed for {col}: {str(e)}")
                            column_transforms[col] = {"action": "median_impute"}
                            missing_stats[col]["action"] = "median_impute"
                    else:
                        column_transforms[col] = {"action": "median_impute"}
                        missing_stats[col]["action"] = "median_impute"
                elif col in self.column_types.get("categorical", []) or col in self.column_types.get("gender", []):
                    column_transforms[col] = {"action": "mode_impute"}
                    missing_stats[col]["action"] = "mode_impute"
                elif col in self.column_types.get("datetime", []):
                    column_transforms[col] = {"action": "median_date_impute"}
                    missing_stats[col]["action"] = "median_date_impute"
                else:
                    column_transforms[col] = {"action": "fill_value", "value": "Unknown"}
                    missing_stats[col]["action"] = "unknown_impute"
        
        if columns_to_drop or column_transforms:
            df_processed = df.copy()

            knn_cols = [col for col, transform in column_transforms.items() 
                    if transform["action"] == "knn_impute"]
            if knn_cols:
                for col in knn_cols:
                    transform = column_transforms[col]
                    numeric_cols = transform["columns"] + [col]
                    
                    imputer = KNNImputer(n_neighbors=min(5, len(df_processed) // 20))
                    df_subset = df_processed[numeric_cols].copy()
                    df_filled = pd.DataFrame(
                        imputer.fit_transform(df_subset),
                        columns=numeric_cols,
                        index=df_subset.index
                    )
                    df_processed[col] = df_filled[col]
            
            median_cols = [col for col, transform in column_transforms.items() 
                        if transform["action"] == "median_impute"]
            if median_cols:
                medians = df_processed[median_cols].median()
                for col in median_cols:
                    df_processed[col] = df_processed[col].fillna(medians[col])
            
            mode_cols = [col for col, transform in column_transforms.items() 
                    if transform["action"] == "mode_impute"]
            for col in mode_cols:
                mode_value = df_processed[col].mode()[0] if not df_processed[col].mode().empty else "Unknown"
                # Đảm bảo giá trị mode nằm trong danh sách categories nếu là categorical
                if pd.api.types.is_categorical_dtype(df_processed[col]):
                    if mode_value not in df_processed[col].cat.categories:
                        # Thêm giá trị vào danh sách categories
                        df_processed[col] = df_processed[col].cat.add_categories([mode_value])
                df_processed[col] = df_processed[col].fillna(mode_value)
            
            date_cols = [col for col, transform in column_transforms.items() 
                    if transform["action"] == "median_date_impute"]
            for col in date_cols:
                try:
                    median_date = df_processed[col].dropna().median()
                    df_processed[col] = df_processed[col].fillna(median_date)
                except Exception:
                    pass
            
            # Xử lý các cột cần điền giá trị cụ thể
            fill_value_groups = {}
            for col, transform in column_transforms.items():
                if transform["action"] == "fill_value":
                    value = transform.get("value")
                    if value not in fill_value_groups:
                        fill_value_groups[value] = []
                    fill_value_groups[value].append(col)
            
            # Điền giá trị với xử lý đặc biệt cho categorical columns
            for value, cols in fill_value_groups.items():
                for col in cols:
                    if pd.api.types.is_categorical_dtype(df_processed[col]):
                        # Nếu là categorical thì thêm giá trị mới vào danh sách categories
                        if value not in df_processed[col].cat.categories:
                            df_processed[col] = df_processed[col].cat.add_categories([value])
                        df_processed[col] = df_processed[col].fillna(value)
                    else:
                        # Với các loại khác, có thể điền trực tiếp
                        df_processed[col] = df_processed[col].fillna(value)
            
            if columns_to_drop:
                df_processed = df_processed.drop(columns=columns_to_drop)
        else:
            df_processed = df
        
        total_missing_after = df_processed.isna().sum().sum()
        missing_stats["total_after"] = total_missing_after
        missing_stats["percent_after"] = total_missing_after / (len(df_processed) * len(df_processed.columns)) * 100
        
        self.preprocessing_stats["missing_values"] = missing_stats
        
        return df_processed
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle outliers with advanced methods"""
        df_processed = df.copy()
        outlier_stats = {}
        
        numeric_cols = [col for col in df_processed.columns 
                    if is_numeric_dtype(df_processed[col])
                    and col not in self.column_types.get("id", [])
                    and col not in self.column_types.get("binary", [])]
        
        if len(df) < 30 or not numeric_cols:
            outlier_stats["action"] = "skipped_insufficient_data"
            self.preprocessing_stats["outliers"] = outlier_stats
            return df_processed
                
        if len(numeric_cols) >= 3 and len(df) >= 100:
            try:
                X = df_processed[numeric_cols].fillna(df_processed[numeric_cols].median())
                
                isolation_forest = IsolationForest(
                    contamination=0.05,
                    random_state=42
                )
                
                outlier_labels = isolation_forest.fit_predict(X)
                outlier_indices = np.where(outlier_labels == -1)[0]
                
                outlier_stats["isolation_forest"] = {
                    "outlier_count": len(outlier_indices),
                    "outlier_percent": len(outlier_indices) / len(df) * 100
                }
                
                if len(outlier_indices) / len(df) > 0.1:
                    extreme_outliers = []
                    
                    Q1 = X[numeric_cols].quantile(0.25)
                    Q3 = X[numeric_cols].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bounds = Q1 - 3 * IQR
                    upper_bounds = Q3 + 3 * IQR
                    
                    for idx in outlier_indices:
                        row = X.iloc[idx]
                        is_extreme = ((row < lower_bounds) | (row > upper_bounds)).any()
                        
                        if is_extreme:
                            extreme_outliers.append(idx)
                    
                    for idx in extreme_outliers:
                        for col in numeric_cols:
                            if df_processed.iloc[idx, df_processed.columns.get_loc(col)] < lower_bounds[col]:
                                df_processed.iloc[idx, df_processed.columns.get_loc(col)] = lower_bounds[col]
                            elif df_processed.iloc[idx, df_processed.columns.get_loc(col)] > upper_bounds[col]:
                                df_processed.iloc[idx, df_processed.columns.get_loc(col)] = upper_bounds[col]
                    
                    outlier_stats["action"] = "cap_extreme_outliers"
                    outlier_stats["extreme_outlier_count"] = len(extreme_outliers)
                else:
                    medians = df_processed[numeric_cols].median().values
                    df_processed.loc[df_processed.index[outlier_indices], numeric_cols] = medians
                    
                    outlier_stats["action"] = "replace_with_median"
            except Exception as e:
                logger.warning(f"Isolation Forest failed: {str(e)}. Using IQR method.")
                outlier_stats["isolation_forest"] = {"error": str(e)}
                outlier_stats["method"] = "iqr_fallback"
                
                Q1 = df_processed[numeric_cols].quantile(0.25)
                Q3 = df_processed[numeric_cols].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bounds = Q1 - 3 * IQR
                upper_bounds = Q3 + 3 * IQR
                
                col_outliers = {}
                for col in numeric_cols:
                    outliers = ((df_processed[col] < lower_bounds[col]) | (df_processed[col] > upper_bounds[col])).sum()
                    col_outliers[col] = outliers
                    
                    df_processed[col] = df_processed[col].clip(lower=lower_bounds[col], upper=upper_bounds[col])
                
                outlier_stats["column_outliers"] = col_outliers
                outlier_stats["action"] = "clip_to_bounds"
        else:
            outlier_stats["method"] = "iqr"
            
            Q1 = df_processed[numeric_cols].quantile(0.25)
            Q3 = df_processed[numeric_cols].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bounds = Q1 - 3 * IQR
            upper_bounds = Q3 + 3 * IQR
            
            col_outliers = {}
            for col in numeric_cols:
                outliers = ((df_processed[col] < lower_bounds[col]) | (df_processed[col] > upper_bounds[col])).sum()
                col_outliers[col] = outliers
                
                df_processed[col] = df_processed[col].clip(lower=lower_bounds[col], upper=upper_bounds[col])
            
            outlier_stats["column_outliers"] = col_outliers
            outlier_stats["action"] = "clip_to_bounds"
        
        self.preprocessing_stats["outliers"] = outlier_stats
        
        return df_processed

    def _convert_binary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Chuyển đổi các cột binary về dạng 0/1
        
        Args:
            df: DataFrame cần xử lý
            
        Returns:
            pd.DataFrame: DataFrame với các cột binary đã được chuyển đổi
        """
        df_result = df.copy()
        binary_cols = self.column_types.get("binary", [])
        
        if not binary_cols or not hasattr(self, '_binary_mappings'):
            return df_result
        
        conversion_stats = {}
        
        for col in binary_cols:
            if col not in df_result.columns:
                continue
                
            if is_numeric_dtype(df_result[col]):
                df_result[col] = df_result[col].map(lambda x: 1 if x == 1 or x == 1.0 else 0)
                conversion_stats[col] = {"from": str(df[col].dtype), "to": "int8", "method": "direct"}
                df_result[col] = df_result[col].astype(np.int8)
            else:
                if col in self._binary_mappings:
                    mapping = self._binary_mappings[col]
                    df_result[col] = df_result[col].map(mapping).fillna(df_result[col])
                    
                    try:
                        df_result[col] = df_result[col].map(lambda x: 1 if x == 1 else 0)
                        df_result[col] = df_result[col].astype(np.int8)
                        
                        conversion_stats[col] = {
                            "from": str(df[col].dtype), 
                            "to": "int8", 
                            "method": "mapping",
                            "mapping": {str(k): v for k, v in mapping.items()}
                        }
                    except:
                        pass
        
        self.preprocessing_stats.setdefault("type_conversion", {}).update(conversion_stats)
        
        return df_result

    def _convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert data types appropriately"""
        df_processed = df.copy()
        conversion_stats = {}

        datetime_cols = self.column_types.get("datetime", [])
        datetime_cols = [col for col in datetime_cols if col in df_processed.columns]

        for col in datetime_cols:
            if not is_datetime64_any_dtype(df_processed[col]):
                try:
                    df_processed[col] = convert_to_datetime(df_processed[df])
                    conversion_stats[col] = {"from": str(df[col].dtype), "to": "datetime64"}
                except Exception:
                    logger.warning(f"Failed to convert {col} to datetime")

        for col in df_processed.columns:
            if col in datetime_cols:
                continue

            if pd.api.types.is_integer_dtype(df_processed[col]):
                col_min = df_processed[col].min()
                col_max = df_processed[col].max()
                
                if col_min >= 0:
                    if col_max < 256:
                        new_type = np.uint8
                    elif col_max < 65536:
                        new_type = np.uint16
                    elif col_max < 4294967296:
                        new_type = np.uint32
                    else:
                        new_type = None
                else:
                    if col_min > -128 and col_max < 128:
                        new_type = np.int8
                    elif col_min > -32768 and col_max < 32768:
                        new_type = np.int16
                    elif col_min > -2147483648 and col_max < 2147483648:
                        new_type = np.int32
                    else:
                        new_type = None
                
                if new_type and df_processed[col].dtype != new_type:
                    df_processed[col] = df_processed[col].astype(new_type)
                    conversion_stats[col] = {"from": str(df[col].dtype), "to": str(new_type)}

            elif pd.api.types.is_float_dtype(df_processed[col]):
                if not (df_processed[col].abs() > 1e38).any() and not (df_processed[col].abs() < 1e-38).any():
                    df_processed[col] = df_processed[col].astype(np.float32)
                    if df_processed[col].dtype != df[col].dtype:
                        conversion_stats[col] = {"from": str(df[col].dtype), "to": str(df_processed[col].dtype)}

            elif pd.api.types.is_object_dtype(df_processed[col]):
                n_unique = df_processed[col].nunique()
                if n_unique <= min(100, len(df_processed) * 0.1):
                    df_processed[col] = df_processed[col].astype('category')
                    conversion_stats[col] = {"from": "object", "to": "category"}

        self.preprocessing_stats["type_conversion"] = conversion_stats
        
        return df_processed
    
    def _extract_datetime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract features from datetime columns"""
        df_processed = df.copy()
        
        datetime_cols = self.column_types.get("datetime", [])
        datetime_cols = [col for col in datetime_cols if col in df_processed.columns]
        
        if not datetime_cols:
            return df_processed
            
        datetime_stats = {"columns": {}}
        
        for col in datetime_cols:
            try:
                df_processed[col] = convert_to_datetime(df_processed[col])
                
                try:
                    distribution = analyze_datetime_distribution(df_processed[col])
                    datetime_stats["columns"][col] = {
                        "min_date": df_processed[col].min().isoformat() if not pd.isna(df_processed[col].min()) else None,
                        "max_date": df_processed[col].max().isoformat() if not pd.isna(df_processed[col].max()) else None,
                        "distribution": {
                            "year_distribution": distribution.get("distributions", {}).get("year", {}),
                            "month_distribution": distribution.get("distributions", {}).get("month", {}),
                            "day_of_week": distribution.get("distributions", {}).get("day_of_week", {}),
                            "time_gaps": distribution.get("time_gaps", {}),
                            "suggested_frequency": distribution.get("suggested_frequency", "unknown")
                        }
                    }
                except Exception as e:
                    logger.warning(f"Failed to analyze datetime distribution for {col}: {str(e)}")
                    datetime_stats["columns"][col] = {
                        "min_date": df_processed[col].min().isoformat() if not pd.isna(df_processed[col].min()) else None,
                        "max_date": df_processed[col].max().isoformat() if not pd.isna(df_processed[col].max()) else None
                    }
            except Exception as e:
                logger.warning(f"Failed to process datetime column {col}: {str(e)}")
        
        self.preprocessing_stats["datetime_features"] = datetime_stats
        
        return df_processed
    
    def _encode_categorical_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical columns"""
        encoding_stats = {
            "columns": {}
        }

        categorical_cols = []
        for col_type in ["categorical", "gender"]:
            categorical_cols.extend(self.column_types.get(col_type, []))

        binary_cols = self.column_types.get("binary", [])
        categorical_cols = [col for col in categorical_cols if col in df.columns and col not in binary_cols]
        
        if not categorical_cols:
            return df
        
        encoding_methods = {
            'one_hot': [],
            'binary': binary_cols,
            'label': []
        }

        for col in categorical_cols:
            n_unique = df[col].nunique()
            if n_unique == 2:
                encoding_methods['binary'].append(col)
            elif 3 <= n_unique <= 15:
                encoding_methods['one_hot'].append(col)
            else:
                encoding_methods['label'].append(col)

        columns_modified = any(len(cols) > 0 for cols in encoding_methods.values())
        if not columns_modified:
            return df
        
        df_processed = df.copy()
        
        if encoding_methods['binary']:
            for col in encoding_methods['binary']:
                try:
                    unique_vals = df_processed[col].unique()
                    
                    if len(unique_vals) < 2:
                        unique_vals = [unique_vals[0], f"not_{unique_vals[0]}"]
                    
                    mapping = {unique_vals[0]: 0, unique_vals[1]: 1}
                    
                    df_processed[col] = df_processed[col].map(mapping)
                    
                    encoding_stats["columns"][col] = {
                        "method": "binary",
                        "mapping": {str(k): int(v) for k, v in mapping.items()}
                    }
                except Exception as e:
                    logger.warning(f"Binary encoding failed for {col}: {str(e)}")
        
        if encoding_methods['one_hot']:
            try:
                one_hot_df = pd.get_dummies(df_processed[encoding_methods['one_hot']], prefix=encoding_methods['one_hot'])
                
                for col in encoding_methods['one_hot']:
                    prefix = col
                    new_cols = [c for c in one_hot_df.columns if c.startswith(f"{prefix}_")]
                    
                    encoding_stats["columns"][col] = {
                        "method": "one_hot",
                        "n_unique": df_processed[col].nunique(),
                        "new_columns": new_cols
                    }
                
                df_processed = pd.concat([df_processed.drop(columns=encoding_methods['one_hot']), one_hot_df], axis=1)
            except Exception as e:
                logger.warning(f"One-hot encoding failed: {str(e)}")
                for col in encoding_methods['one_hot']:
                    self._encode_label(df_processed, col, encoding_stats)
        
        if encoding_methods['label']:
            for col in encoding_methods['label']:
                self._encode_label(df_processed, col, encoding_stats)
        
        self.preprocessing_stats["encoding"] = encoding_stats
        
        return df_processed
    
    def _encode_label(self, df: pd.DataFrame, col: str, encoding_stats: Dict) -> None:
        """Encode column with label encoding"""
        try:
            fill_value = "unknown_category"
            series = df[col].fillna(fill_value)
            
            encoder = LabelEncoder()
            df[col] = encoder.fit_transform(series.astype(str))
            
            self._label_encoders[col] = encoder
            
            classes_list = encoder.classes_.tolist()
            classes_list = [str(x) for x in classes_list]
            
            encoding_stats["columns"][col] = {
                "method": "label",
                "n_unique": len(classes_list),
                "classes": classes_list
            }
        except Exception as e:
            logger.warning(f"Label encoding failed for {col}: {str(e)}")
            try:
                df[col] = -1
                encoding_stats["columns"][col] = {
                    "method": "label",
                    "error": str(e),
                    "fallback": "constant_value"
                }
            except Exception:
                pass
    
    def _normalize_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize numeric columns"""
        df_processed = df.copy()
        
        numeric_cols = [col for col in df_processed.columns 
                      if is_numeric_dtype(df_processed[col])
                      and col not in self.column_types.get("id", [])
                      and col not in self.column_types.get("binary", [])]
        
        if not numeric_cols:
            return df_processed
            
        try:
            scaler = StandardScaler()
            
            df_processed[numeric_cols] = scaler.fit_transform(df_processed[numeric_cols])
            
            self._scalers['standard'] = scaler
            
            self.preprocessing_stats["normalization"] = {
                "method": "standard_scaling",
                "columns": numeric_cols,
                "mean": dict(zip(numeric_cols, scaler.mean_)),
                "std": dict(zip(numeric_cols, scaler.scale_))
            }
        except Exception as e:
            logger.warning(f"Failed to normalize numeric columns: {str(e)}")
            for col in numeric_cols:
                min_val = df_processed[col].min()
                max_val = df_processed[col].max()
                if max_val > min_val:
                    df_processed[col] = (df_processed[col] - min_val) / (max_val - min_val)
            
            self.preprocessing_stats["normalization"] = {
                "method": "min_max_scaling",
                "columns": numeric_cols
            }
        
        return df_processed
    
    def _analyze_features(self, df: pd.DataFrame) -> None:
        """Analyze features and find important features"""
        if len(df) < 10 or len(df.columns) < 2:
            return
            
        numeric_cols = [col for col in df.columns 
                      if is_numeric_dtype(df[col])
                      and col not in self.column_types.get("id", [])
                      and col not in self.column_types.get("binary", [])]
        
        if len(numeric_cols) < 2:
            return
            
        try:
            if len(numeric_cols) >= 3:
                if "normalization" not in self.preprocessing_stats:
                    X = StandardScaler().fit_transform(df[numeric_cols])
                else:
                    X = df[numeric_cols].values
                
                pca = PCA(n_components=min(len(numeric_cols), 10))
                pca_result = pca.fit_transform(X)
                
                self._pca_models['main'] = pca
                
                loadings = pca.components_
                feature_importance = {}
                
                importance_values = np.sum(loadings[:, :] ** 2, axis=0)
                
                feature_importance = {numeric_cols[i]: float(importance_values[i]) 
                                    for i in range(len(numeric_cols))}
                
                total_importance = sum(feature_importance.values())
                if total_importance > 0:
                    feature_importance = {k: v / total_importance for k, v in feature_importance.items()}
                
                self.feature_importance = dict(sorted(
                    feature_importance.items(), key=lambda x: x[1], reverse=True
                ))
                
                self.preprocessing_stats["pca"] = {
                    "n_components": pca.n_components_,
                    "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
                    "cumulative_variance": np.cumsum(pca.explained_variance_ratio_).tolist()
                }
            else:
                corr_matrix = df[numeric_cols].corr().abs()
                
                feature_importance = {col: float(corr_matrix[col].sum() - 1) for col in numeric_cols}
                
                total_importance = sum(feature_importance.values())
                if total_importance > 0:
                    feature_importance = {k: v / total_importance for k, v in feature_importance.items()}
                
                self.feature_importance = dict(sorted(
                    feature_importance.items(), key=lambda x: x[1], reverse=True
                ))
        except Exception as e:
            logger.warning(f"Feature analysis failed: {str(e)}")

    def identify_performance_bottlenecks(self, df: pd.DataFrame) -> Dict:
        """
        Identify performance bottlenecks in data processing
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dict: Information about bottlenecks
        """
        import time
        
        bottlenecks = {
            "memory": {},
            "processing": {},
            "recommendations": []
        }
        
        memory_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)
        bottlenecks["memory"]["total_mb"] = memory_usage
        
        col_mem = df.memory_usage(deep=True) / (1024 * 1024)
        col_mem_sorted = col_mem.sort_values(ascending=False)
        bottlenecks["memory"]["columns"] = col_mem_sorted.to_dict()
        
        processing_times = {}
        
        for col in df.columns:
            start_time = time.time()
            
            if pd.api.types.is_numeric_dtype(df[col]):
                _ = df[col].mean()
                _ = df[col].std()
                _ = df[col].skew()
            elif pd.api.types.is_string_dtype(df[col]):
                _ = df[col].str.len().mean()
                _ = df[col].nunique()
            
            processing_times[col] = time.time() - start_time
        
        bottlenecks["processing"] = dict(sorted(
            processing_times.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        if memory_usage > 1000:
            bottlenecks["recommendations"].append(
                "Very large data. Consider using chunking or dask DataFrame."
            )
        
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                min_val = df[col].min()
                max_val = df[col].max()
                
                if min_val >= 0 and max_val < 256:
                    bottlenecks["recommendations"].append(
                        f"Column {col} could be converted to uint8 to save memory"
                    )
            elif pd.api.types.is_float_dtype(df[col]):
                if df[col].round(2).equals(df[col]):
                    bottlenecks["recommendations"].append(
                        f"Column {col} could be rounded to 2 decimal places to save memory"
                    )
        
        return bottlenecks
    
    def apply_pca(self, df: pd.DataFrame, numeric_columns: List[str], n_components: float = 0.95) -> Tuple[pd.DataFrame, Dict]:
        """
        Apply PCA for dimensionality reduction
        
        Args:
            df: Input DataFrame
            numeric_columns: List of numeric columns
            n_components: Number of components or variance to retain
            
        Returns:
            Tuple: Reduced DataFrame and component information
        """
        if len(numeric_columns) < 3:
            return df, {"error": "Not enough numeric columns for PCA"}
        
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(df[numeric_columns])
        
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(scaled_data)
        
        pca_df = pd.DataFrame(
            data=pca_result,
            columns=[f'PC{i+1}' for i in range(pca_result.shape[1])]
        )
        
        component_info = {
            'explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
            'cumulative_variance': np.cumsum(pca.explained_variance_ratio_).tolist(),
            'components': {
                f'PC{i+1}': {
                    numeric_columns[j]: pca.components_[i, j]
                    for j in range(len(numeric_columns))
                }
                for i in range(len(pca.components_))
            }
        }
        
        self._pca_models['main'] = pca
        
        return pca_df, component_info

    def select_important_features(self, df: pd.DataFrame, target_column: Optional[str] = None, max_features: int = 10) -> List[str]:
        """
        Select most important features from dataset
        
        Args:
            df: DataFrame with data
            target_column: Target column (if any)
            max_features: Maximum number of features to select
            
        Returns:
            List[str]: List of most important features
        """
        from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
        from scipy.stats import spearmanr
        
        if target_column and target_column in df.columns:
            numeric_cols = self.column_types["numeric"]
            
            if target_column in numeric_cols:
                numeric_cols.remove(target_column)
                
            if not numeric_cols:
                return []
                
            X = df[numeric_cols]
            y = df[target_column]
            
            X = X.fillna(X.mean())
            
            try:
                selector = SelectKBest(f_regression, k=min(max_features, len(numeric_cols)))
                selector.fit(X, y)
                
                scores = selector.scores_
                features_scores = list(zip(numeric_cols, scores))
                features_scores = sorted(features_scores, key=lambda x: x[1], reverse=True)
                
                return [f[0] for f in features_scores[:max_features]]
            except Exception:
                try:
                    selector = SelectKBest(mutual_info_regression, k=min(max_features, len(numeric_cols)))
                    selector.fit(X, y)
                    
                    scores = selector.scores_
                    features_scores = list(zip(numeric_cols, scores))
                    features_scores = sorted(features_scores, key=lambda x: x[1], reverse=True)
                    
                    return [f[0] for f in features_scores[:max_features]]
                except Exception:
                    pass
        
        numeric_cols = self.column_types["numeric"]
        if not numeric_cols:
            return []
            
        variances = df[numeric_cols].var().sort_values(ascending=False)
        high_var_features = variances.index[:min(max_features, len(variances))].tolist()
        
        final_features = []
        for feature in high_var_features:
            if not final_features:
                final_features.append(feature)
            else:
                correlated = False
                for selected in final_features:
                    try:
                        feature_var = df[feature].var()
                        selected_var = df[selected].var()
                        
                        if feature_var == 0 or selected_var == 0:
                            continue
                            
                        corr, _ = spearmanr(df[feature], df[selected])
                        if abs(corr) > 0.8:
                            correlated = True
                            break
                    except Exception:
                        pass
                        
                if not correlated:
                    final_features.append(feature)
                    
                if len(final_features) >= max_features:
                    break
                    
        return final_features
    
    def remove_noise(self, df: pd.DataFrame, numeric_columns: List[str], method: str = 'moving_avg') -> pd.DataFrame:
        """
        Remove noise from numeric data
        
        Args:
            df: Input DataFrame
            numeric_columns: Numeric columns to process
            method: Noise removal method ('wavelet', 'moving_avg', 'low_pass')
            
        Returns:
            pd.DataFrame: DataFrame with noise removed
        """
        result_df = df.copy()

        if not numeric_columns:
            return result_df
        
        if method == 'moving_avg':
            window_size = max(3, len(df) // 100)
            for col in numeric_columns:
                result_df[col] = df[col].rolling(window=window_size, center=True).mean()
                result_df[col] = result_df[col].fillna(df[col])
        
        elif method == 'wavelet' and len(df) >= 8:
            try:
                import pywt
                
                for col in numeric_columns:
                    data = df[col].dropna().values
                    
                    if len(data) >= 8:
                        wavelet = 'db4'
                        level = min(5, pywt.dwt_max_level(len(data), pywt.Wavelet(wavelet).dec_len))
                        
                        coeffs = pywt.wavedec(data, wavelet, level=level)
                        
                        for i in range(1, len(coeffs)):
                            coeffs[i] = pywt.threshold(coeffs[i], 0.2 * np.max(np.abs(coeffs[i])), mode='soft')
                        
                        reconstructed = pywt.waverec(coeffs, wavelet)
                        
                        if len(reconstructed) > len(data):
                            reconstructed = reconstructed[:len(data)]
                        
                        result_df.loc[df[col].dropna().index, col] = reconstructed
            except ImportError:
                logger.warning("PyWavelets not installed. Using moving average method instead.")
                window_size = max(3, len(df) // 100)
                for col in numeric_columns:
                    result_df[col] = df[col].rolling(window=window_size, center=True).mean()
                    result_df[col] = result_df[col].fillna(df[col])
        
        else:
            alpha = 0.1
            for col in numeric_columns:
                smoothed = [df[col].iloc[0]]

                for i in range(1, len(df)):
                    if pd.isna(df[col].iloc[i]):
                        smoothed.append(df[col].iloc[i])
                    else:
                        prev = smoothed[i-1] if not pd.isna(smoothed[i-1]) else df[col].iloc[i]
                        smoothed.append(alpha * df[col].iloc[i] + (1 - alpha) * prev)
                
                result_df[col] = smoothed
        
        return result_df
    
    def _generate_df_hash(self, df: pd.DataFrame) -> str:
        """
        Tạo hash key cho DataFrame dựa trên shape, columns và sample values
        
        Args:
            df: DataFrame cần tạo hash
            
        Returns:
            str: Hash key
        """
        # Tính toán hash từ các thuộc tính chính
        shape = df.shape
        columns = df.columns.tolist()
        dtypes = df.dtypes.astype(str).tolist()
        
        # Lấy mẫu dữ liệu để đưa vào hash
        sample_values = []
        if len(df) > 0:
            sample_rows = min(5, len(df))
            for i in range(sample_rows):
                row_idx = (i * len(df) // sample_rows)
                sample_values.append(str(df.iloc[row_idx].tolist()))
        
        # Tạo chuỗi hash
        hash_content = f"{shape}|{columns}|{dtypes}|{sample_values}"
        return hashlib.md5(hash_content.encode()).hexdigest()
    
    def clear_cache(self):
        """Xóa cache"""
        self._cache = {}
        logger.info("ColumnTypeManager cache cleared")