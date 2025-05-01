import json
import logging
import os
from typing import Dict, List, Optional, Union, Tuple, Set

import pandas as pd
import numpy as np
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype

from app.models.analysis import ChartType, VisualizationData
from ml.visualization.charts import ChartGenerator
from ml.utils.datetime_utils import convert_to_datetime, is_datetime_column
from ml.data.data_processor import DataProcessor
from ml.data.data_validator import DataValidator

logger = logging.getLogger(__name__)


class ChartRecommender:
    """Khuyến nghị và tạo các loại biểu đồ phù hợp với dữ liệu - phiên bản nâng cao"""

    def __init__(self, config_path: Optional[Union[str, Dict]] = None):
        """Khởi tạo chart recommender với tích hợp các module nâng cao"""
        # Tải config
        self.config = self._load_config(config_path)
        
        # Khởi tạo các module cần thiết
        self.chart_generator = ChartGenerator(config_path)
        self.data_processor = DataProcessor(config_path)
        self.data_validator = DataValidator(config_path)
        
        # Thiết lập các giá trị mặc định
        self.default_chart_width = self.config.get("visualization", {}).get("default_chart_width", 600)
        self.default_chart_height = self.config.get("visualization", {}).get("default_chart_height", 400)
        self.enable_interactive = self.config.get("visualization", {}).get("enable_interactive_charts", True)
        self.color_palette = self.config.get("visualization", {}).get("color_palette", "tableau10")
        
        # Lưu trữ kết quả validtor để tái sử dụng
        self.validation_results = {}
        self.column_types = {}
        self.column_correlations = {}
        self.feature_importance = {}
        
        logger.info("EnhancedChartRecommender initialized with all modules")

    def _load_config(self, config_path: Optional[Union[str, Dict]]) -> Dict:
        """Tải config từ file hoặc dict"""
        try:
            if isinstance(config_path, dict):
                return config_path
            
            if not config_path:
                config_path = os.getenv("MODEL_CONFIG_PATH", "configs/model_config.json")
                
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file {config_path} not found, using default configuration")
                
            # Cấu hình mặc định nâng cao với nhiều tùy chọn hơn
            return {
                "visualization": {
                    "default_chart_height": 400,
                    "default_chart_width": 600,
                    "color_palette": "tableau10",
                    "max_categories_in_chart": 12,
                    "max_charts_per_insight": 8,
                    "max_points_in_scatter": 5000,
                    "enable_interactive_charts": True,
                    "chart_styles": {
                        "default_theme": "light",
                        "title_font_size": 16,
                        "axis_label_font_size": 12,
                        "show_grid": True,
                        "bar_opacity": 0.8,
                        "line_width": 2
                    },
                    "chart_quality_weights": {
                        "data_relevance": 0.4,
                        "visual_clarity": 0.3,
                        "information_density": 0.3
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {
                "visualization": {
                    "default_chart_height": 400,
                    "default_chart_width": 600
                }
            }

    def recommend_charts(self, df: pd.DataFrame, columns: Optional[List[str]] = None, file_id: Optional[str] = None) -> Dict[str, Dict]:
        """
        Khuyến nghị các loại biểu đồ phù hợp với dữ liệu
        
        Args:
            df: DataFrame cần phân tích
            columns: Danh sách cột cần phân tích (nếu None, sử dụng tất cả)
            file_id: ID của file data (nếu có)
            
        Returns:
            Dict[str, Dict]: Khuyến nghị biểu đồ
        """
        try:
            # Đánh giá chất lượng dữ liệu để điều chỉnh khuyến nghị
            self._validate_data_quality(df)
            
            # Phát hiện kiểu dữ liệu của các cột
            self._analyze_column_types(df)
            
            # Sử dụng tất cả cột nếu không có cột nào được chỉ định
            if not columns:
                columns = df.columns.tolist()
            
            # Lọc các cột tồn tại trong dataframe
            valid_columns = [col for col in columns if col in df.columns]
            
            # Khuyến nghị biểu đồ cho từng tổ hợp cột
            chart_recommendations = {}
            
            # 1. Khuyến nghị cho cột đặc biệt (likert, binary, text)
            for col in valid_columns:
                if col in self.column_types.get('likert', []):
                    chart_recommendations[col] = self._recommend_likert_column(df, col)
                elif col in self.column_types.get('binary', []):
                    chart_recommendations[col] = self._recommend_binary_column(df, col)
                elif col in self.column_types.get('text', []):
                    chart_recommendations[col] = self._recommend_text_column(df, col)
                elif col in self.column_types.get('range', []):
                    chart_recommendations[col] = self._recommend_range_column(df, col)
            
            # 2. Khuyến nghị cho cột đơn lẻ
            for col in valid_columns:
                # Bỏ qua nếu đã có khuyến nghị từ các loại đặc biệt
                if col in chart_recommendations:
                    continue
                    
                if col in self.column_types.get('numeric', []):
                    # Khuyến nghị cho cột numeric đơn lẻ
                    chart_recommendations[col] = self._recommend_numeric_column(df, col)
                elif col in self.column_types.get('categorical', []) or col in self.column_types.get('gender', []):
                    # Khuyến nghị cho cột categorical đơn lẻ
                    chart_recommendations[col] = self._recommend_categorical_column(df, col)
                elif col in self.column_types.get('datetime', []):
                    # Khuyến nghị cho cột datetime đơn lẻ
                    chart_recommendations[col] = self._recommend_datetime_column(df, col)
            
            # 3. Khuyến nghị cho cặp cột
            if len(valid_columns) >= 2:
                for i, col1 in enumerate(valid_columns):
                    for col2 in valid_columns[i+1:]:
                        key = f"{col1} vs {col2}"
                        
                        # Numeric vs Numeric
                        if col1 in self.column_types.get('numeric', []) and col2 in self.column_types.get('numeric', []):
                            chart_recommendations[key] = self._recommend_numeric_vs_numeric(df, col1, col2)
                        
                        # Categorical vs Numeric
                        elif ((col1 in self.column_types.get('categorical', []) or col1 in self.column_types.get('gender', [])) and 
                              col2 in self.column_types.get('numeric', [])) or \
                             ((col2 in self.column_types.get('categorical', []) or col2 in self.column_types.get('gender', [])) and 
                              col1 in self.column_types.get('numeric', [])):
                            
                            cat_col = col1 if col1 in self.column_types.get('categorical', []) or col1 in self.column_types.get('gender', []) else col2
                            num_col = col2 if col1 in self.column_types.get('categorical', []) or col1 in self.column_types.get('gender', []) else col1
                            chart_recommendations[key] = self._recommend_categorical_vs_numeric(df, cat_col, num_col)
                        
                        # Datetime vs Numeric
                        elif (col1 in self.column_types.get('datetime', []) and col2 in self.column_types.get('numeric', [])) or \
                             (col2 in self.column_types.get('datetime', []) and col1 in self.column_types.get('numeric', [])):
                            
                            dt_col = col1 if col1 in self.column_types.get('datetime', []) else col2
                            num_col = col2 if col1 in self.column_types.get('datetime', []) else col1
                            chart_recommendations[key] = self._recommend_datetime_vs_numeric(df, dt_col, num_col)
                        
                        # Categorical vs Categorical
                        elif (col1 in self.column_types.get('categorical', []) or col1 in self.column_types.get('gender', [])) and \
                             (col2 in self.column_types.get('categorical', []) or col2 in self.column_types.get('gender', [])):
                            
                            chart_recommendations[key] = self._recommend_categorical_vs_categorical(df, col1, col2)
                        
                        # Datetime vs Datetime
                        elif col1 in self.column_types.get('datetime', []) and col2 in self.column_types.get('datetime', []):
                            chart_recommendations[key] = self._recommend_datetime_vs_datetime(df, col1, col2)
                        
                        # Datetime vs Categorical 
                        elif (col1 in self.column_types.get('datetime', []) and 
                              (col2 in self.column_types.get('categorical', []) or col2 in self.column_types.get('gender', []))) or \
                             (col2 in self.column_types.get('datetime', []) and 
                              (col1 in self.column_types.get('categorical', []) or col1 in self.column_types.get('gender', []))):
                            
                            dt_col = col1 if col1 in self.column_types.get('datetime', []) else col2
                            cat_col = col2 if col1 in self.column_types.get('datetime', []) else col1
                            chart_recommendations[key] = self._recommend_datetime_vs_categorical(df, dt_col, cat_col)
                        
                
                # 4. Binary x Numeric recommendations (special case)
                for bin_col in self.column_types.get('binary', []):
                    for num_col in self.column_types.get('numeric', []):
                        if bin_col != num_col:
                            key = f"{bin_col} vs {num_col}"
                            chart_recommendations[key] = self._recommend_binary_vs_numeric(df, bin_col, num_col)
                
                # 5. Likert x Likert recommendations (special case)
                likert_cols = self.column_types.get('likert', [])
                if len(likert_cols) >= 2:
                    for i, col1 in enumerate(likert_cols):
                        for col2 in likert_cols[i+1:]:
                            key = f"{col1} vs {col2}"
                            chart_recommendations[key] = self._recommend_likert_vs_likert(df, col1, col2)
            
            # 6. Khuyến nghị cho tổ hợp 3 cột
            if len(valid_columns) >= 3:
                for i, col1 in enumerate(valid_columns):
                    for j, col2 in enumerate(valid_columns[i+1:], i+1):
                        for col3 in valid_columns[j+1:]:
                            # Chỉ xử lý các tổ hợp hữu ích
                            # Một cột numeric, một datetime, một categorical
                            num_cols = [col for col in [col1, col2, col3] if col in self.column_types.get('numeric', [])]
                            dt_cols = [col for col in [col1, col2, col3] if col in self.column_types.get('datetime', [])]
                            cat_cols = [col for col in [col1, col2, col3] 
                                      if col in self.column_types.get('categorical', []) or 
                                         col in self.column_types.get('gender', [])]
                            
                            # Nếu có đúng một cột của mỗi loại
                            if len(num_cols) == 1 and len(dt_cols) == 1 and len(cat_cols) == 1:
                                key = f"{num_cols[0]} vs {dt_cols[0]} vs {cat_cols[0]}"
                                chart_recommendations[key] = self._recommend_numeric_datetime_categorical(
                                    df, num_cols[0], dt_cols[0], cat_cols[0]
                                )
                        
                            
                            # 2 numeric + 1 categorical -> bubble chart or scatter with color
                            elif len(num_cols) >= 2 and len(cat_cols) == 1:
                                key = f"{num_cols[0]} vs {num_cols[1]} vs {cat_cols[0]}"
                                chart_recommendations[key] = self._recommend_two_numeric_one_categorical(
                                    df, num_cols[0], num_cols[1], cat_cols[0]
                                )
                            
                            # 3 numeric -> 3D scatter or matrix plot
                            elif len(num_cols) == 3:
                                key = f"{num_cols[0]} vs {num_cols[1]} vs {num_cols[2]}"
                                chart_recommendations[key] = self._recommend_three_numeric(
                                    df, num_cols[0], num_cols[1], num_cols[2]
                                )
            
            # 7. Khuyến nghị phân tích tương quan cho nhiều cột numeric
            numeric_cols = self.column_types.get('numeric', [])
            if len(numeric_cols) >= 3:
                key = "Correlation Analysis"
                chart_recommendations[key] = self._recommend_correlation_analysis(df, numeric_cols)

            # 8. Khuyến nghị phân tích trending cho cột datetime + nhiều cột numeric
            dt_cols = self.column_types.get('datetime', [])
            if dt_cols and len(numeric_cols) >= 2:
                key = f"Time Series Analysis ({dt_cols[0]})"
                chart_recommendations[key] = self._recommend_time_series_analysis(df, dt_cols[0], numeric_cols[:3])
            
            return chart_recommendations
        except Exception as e:
            logger.error(f"Error recommending charts: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def get_best_charts(
        self, df: pd.DataFrame, columns: Optional[List[str]] = None, top_k: int = 6, file_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Lấy top k biểu đồ tốt nhất với cải tiến trong đánh giá và tính đa dạng
        
        Args:
            df: DataFrame cần phân tích
            columns: Danh sách cột cần phân tích (nếu None, sử dụng tất cả)
            top_k: Số lượng biểu đồ tối đa cần trả về
            file_id: ID file (nếu có)
            
        Returns:
            List[Dict]: Danh sách các biểu đồ tốt nhất
        """
        try:
            # Khuyến nghị tất cả biểu đồ
            all_recommendations = self.recommend_charts(df, columns, file_id)

            # Loại bỏ key error nếu có
            if "error" in all_recommendations:
                return [{"error": all_recommendations["error"]}]
            
            # Tạo danh sách các biểu đồ với score
            all_charts = []
            
            for key, recommendations in all_recommendations.items():
                
                for chart_info in recommendations.get("charts", []):
                    all_charts.append({
                        "columns": recommendations.get("columns", key),
                        "chart_type": chart_info["type"],
                        "score": chart_info["score"],
                        "description": chart_info["description"],
                        "title": chart_info.get("title", f"Chart for {key}"),
                        "column_types": recommendations.get("column_types", ["unknown"]),
                        "file_id": file_id,
                        # Thêm metadata cho phân loại nâng cao
                        "category": chart_info.get("category", "general"),
                        "subcategory": chart_info.get("subcategory", "standard"),
                        "complexity": chart_info.get("complexity", "medium")
                    })
            
            # Cải tiến phân loại biểu đồ dựa trên chất lượng dữ liệu
            if self.validation_results:
                quality_score = self.validation_results.get("quality_metrics", {}).get("overall_score", 80)
                
                for chart in all_charts:
                    # Điều chỉnh score dựa vào chất lượng dữ liệu
                    chart["score"] = chart["score"] * (0.8 + quality_score / 500)  # Max boost is 20%
            
            # Sắp xếp biểu đồ theo score giảm dần
            all_charts = sorted(all_charts, key=lambda x: x["score"], reverse=True)
            
            # Cải tiến đa dạng: chọn biểu đồ dựa trên loại và phức tạp
            diverse_charts = []
            chart_types_selected = set()
            chart_categories_selected = set()
            chart_complexities = {"low": 0, "medium": 0, "high": 0}
            
            # Ưu tiên các loại biểu đồ khác nhau
            for chart in all_charts:
                if chart["chart_type"] not in chart_types_selected and len(diverse_charts) < top_k:
                    diverse_charts.append(chart)
                    chart_types_selected.add(chart["chart_type"])
                    chart_categories_selected.add(chart["category"])
                    chart_complexities[chart["complexity"]] += 1
            
            # Thêm vào các loại biểu đồ thuộc category khác
            for chart in all_charts:
                if chart["category"] not in chart_categories_selected and len(diverse_charts) < top_k and chart not in diverse_charts:
                    diverse_charts.append(chart)
                    chart_categories_selected.add(chart["category"])
                    chart_complexities[chart["complexity"]] += 1
            
            # Cân bằng độ phức tạp
            if chart_complexities["high"] == 0 and len(diverse_charts) < top_k:
                high_complexity_charts = [c for c in all_charts if c["complexity"] == "high" and c not in diverse_charts]
                if high_complexity_charts:
                    diverse_charts.append(high_complexity_charts[0])
                    chart_complexities["high"] += 1
            
            # Thêm vào biểu đồ score cao nhất chưa được chọn
            remaining_slots = top_k - len(diverse_charts)
            if remaining_slots > 0:
                for chart in all_charts:
                    if chart not in diverse_charts and len(diverse_charts) < top_k:
                        diverse_charts.append(chart)
            
            # Sắp xếp lại kết quả theo score
            diverse_charts = sorted(diverse_charts, key=lambda x: x["score"], reverse=True)
            
            return diverse_charts[:top_k]
        except Exception as e:
            logger.error(f"Error getting best charts: {str(e)}", exc_info=True)
            return [{"error": str(e)}]

    def create_custom_visualization(
        self, 
        df: pd.DataFrame, 
        columns: List[str], 
        chart_type: str,
        file_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """
        Tạo biểu đồ tùy chỉnh với đầy đủ dữ liệu để render
        
        Args:
            df: DataFrame chứa dữ liệu
            columns: Danh sách cột cần sử dụng
            chart_type: Loại biểu đồ (tên enum hoặc chuỗi)
            file_id: ID của file dữ liệu
            title: Tiêu đề biểu đồ
            description: Mô tả biểu đồ
            
        Returns:
            Optional[VisualizationData]: Đối tượng biểu đồ đã tạo
        """
        try:
            logger.info(f"Creating custom visualization with type: {chart_type}, columns: {columns}")
            
            # Validate columns
            valid_columns = [col for col in columns if col in df.columns]
            if not valid_columns:
                logger.warning(f"Không có cột hợp lệ trong danh sách: {columns}")
                return None
            
            # Sử dụng subset DataFrame với các cột cần thiết
            df_subset = df[valid_columns].copy()
            
            # Chuyển đổi chuỗi chart_type thành enum ChartType
            chart_type_enum = None
            if isinstance(chart_type, str):
                chart_type_upper = chart_type.upper()
                if hasattr(ChartType, chart_type_upper):
                    chart_type_enum = getattr(ChartType, chart_type_upper)
                else:
                    # Thử các biến thể khác
                    possible_values = [t.name for t in ChartType]
                    closest_match = next((t for t in possible_values if t.upper() == chart_type_upper), None)
                    
                    if closest_match:
                        chart_type_enum = getattr(ChartType, closest_match)
                    else:
                        logger.warning(f"Loại biểu đồ không được hỗ trợ: {chart_type}")
                        return None
            else:
                chart_type_enum = chart_type  # Giả sử đã là enum
            
            # Đảm bảo đã phân tích kiểu cột (nếu chưa)
            if not self.column_types:
                self._analyze_column_types(df_subset)
                
            # Khởi tạo chart_generator nếu chưa có
            if not hasattr(self, 'chart_generator'):
                self.chart_generator = self.chart_generator
            
            # Tạo biểu đồ dựa trên loại biểu đồ
            chart = None
            
            # HISTOGRAM - biểu đồ phân phối cho cột numeric
            if chart_type_enum == ChartType.HISTOGRAM and len(valid_columns) >= 1:
                col = valid_columns[0]
                if is_numeric_dtype(df_subset[col]):
                    chart = self.chart_generator._create_distribution_chart(df_subset, col, file_id, title)
                elif len(valid_columns) >= 2:
                    num_cols = [c for c in valid_columns if is_numeric_dtype(df_subset[c])]
                    cat_cols = [c for c in valid_columns if c in self.column_types.get('categorical', [])]
                    if num_cols and cat_cols:
                        chart = self.chart_generator._create_grouped_distribution(df_subset, cat_cols[0], num_cols[0], file_id, title)
            
            # BAR - biểu đồ cột
            elif chart_type_enum == ChartType.BAR and len(valid_columns) >= 1:
                col = valid_columns[0]
                if col in self.column_types.get('categorical', []) or col in self.column_types.get('gender', []):
                    chart = self.chart_generator._create_categorical_chart(df_subset, col, file_id, title)
                elif len(valid_columns) >= 2:
                    # Tìm cột categorical và numeric
                    cat_cols = [c for c in valid_columns if c in self.column_types.get('categorical', []) 
                            or c in self.column_types.get('gender', [])]
                    num_cols = [c for c in valid_columns if is_numeric_dtype(df_subset[c])]
                    
                    if cat_cols and num_cols:
                        chart = self.chart_generator._create_group_chart(df_subset, cat_cols[0], num_cols[0], file_id, title)
            
            # PIE - biểu đồ tròn
            elif chart_type_enum == ChartType.PIE and len(valid_columns) >= 1:
                col = valid_columns[0]
                if col in self.column_types.get('categorical', []) or col in self.column_types.get('gender', []):
                    chart = self.chart_generator._create_pie_chart(df_subset, col, file_id, title)
                elif col in self.column_types.get('binary', []):
                    chart = self.chart_generator._create_binary_chart(df_subset, col, file_id, title)
            
            # LINE - biểu đồ đường
            elif chart_type_enum == ChartType.LINE and len(valid_columns) >= 2:
                # Tìm cột datetime và numeric
                dt_cols = [c for c in valid_columns if c in self.column_types.get('datetime', [])]
                num_cols = [c for c in valid_columns if is_numeric_dtype(df_subset[c])]
                
                if dt_cols and num_cols:
                    chart = self.chart_generator.create_time_series_visualization(df_subset, dt_cols[0], num_cols[0], file_id=file_id)
                elif len(num_cols) >= 2:
                    # Có thể tạo biểu đồ line từ 2 cột numeric
                    chart = self.chart_generator._create_scatter_chart(df_subset, num_cols[0], num_cols[1], file_id, title)
                    if chart:
                        chart.type = ChartType.LINE  # Chuyển sang LINE
            
            # SCATTER - biểu đồ tán xạ
            elif chart_type_enum == ChartType.SCATTER and len(valid_columns) >= 2:
                num_cols = [c for c in valid_columns if is_numeric_dtype(df_subset[c])]
                if len(num_cols) >= 2:
                    chart = self.chart_generator._create_scatter_chart(df_subset, num_cols[0], num_cols[1], file_id, title)
                    
                    # Nếu có cột thứ 3 là categorical, dùng làm màu
                    if len(valid_columns) >= 3:
                        cat_cols = [c for c in valid_columns if c in self.column_types.get('categorical', [])]
                        if cat_cols and chart:
                            # Cập nhật config của chart để sử dụng cat_cols[0] làm colorKey
                            if hasattr(chart, 'config') and isinstance(chart.config, dict):
                                chart.config['colorKey'] = cat_cols[0]
            
            # HEATMAP - biểu đồ nhiệt
            elif chart_type_enum == ChartType.HEATMAP and len(valid_columns) >= 2:
                num_cols = [c for c in valid_columns if is_numeric_dtype(df_subset[c])]
                if len(num_cols) >= 2:
                    chart = self.chart_generator._create_correlation_chart(df_subset, num_cols, file_id, title)
                else:
                    # Kiểm tra xem có phải là heatmap cho cột categorical
                    cat_cols = [c for c in valid_columns if c in self.column_types.get('categorical', [])]
                    if len(cat_cols) >= 2:
                        # Tạo cross-tabulation cho 2 cột categorical
                        try:
                            crosstab = pd.crosstab(df_subset[cat_cols[0]], df_subset[cat_cols[1]])
                            
                            # Tạo dữ liệu cho heatmap
                            heatmap_data = []
                            for i, row_idx in enumerate(crosstab.index):
                                for j, col_idx in enumerate(crosstab.columns):
                                    heatmap_data.append({
                                        "x": str(row_idx),
                                        "y": str(col_idx),
                                        "value": float(crosstab.iloc[i, j])
                                    })
                            
                            if heatmap_data:
                                import uuid
                                
                                chart = VisualizationData(
                                    id=str(uuid.uuid4()),
                                    fileId=file_id,
                                    type=ChartType.HEATMAP,
                                    title=title or f"Relationship between {cat_cols[0]} and {cat_cols[1]}",
                                    description=description or f"Heatmap showing relationship between {cat_cols[0]} and {cat_cols[1]}",
                                    data=heatmap_data,
                                    config={
                                        "xAxis": {"key": "x", "name": cat_cols[0]},
                                        "yAxis": {"key": "y", "name": cat_cols[1]},
                                        "colorScale": ["#f7fbff", "#2166ac"],
                                        "height": 500,
                                        "width": 500
                                    }
                                )
                        except Exception as e:
                            logger.warning(f"Error creating categorical heatmap: {str(e)}")
            
            # BOX - biểu đồ hộp
            elif chart_type_enum == ChartType.BOX and len(valid_columns) >= 1:
                num_cols = [c for c in valid_columns if is_numeric_dtype(df_subset[c])]
                if num_cols:
                    chart = self.chart_generator._create_box_plot(df_subset, num_cols[0], file_id, title)
                    
                    # Nếu có cột thứ 2 là categorical, tạo grouped box plot
                    if len(valid_columns) >= 2:
                        cat_cols = [c for c in valid_columns if c in self.column_types.get('categorical', [])]
                        if cat_cols:
                            # Tạo nhóm box plot - hiện tại không có sẵn phương thức này nên bỏ qua
                            pass
            
            # LIKERT - biểu đồ thang đánh giá
            elif chart_type_enum == ChartType.LIKERT and len(valid_columns) >= 1:
                likert_cols = self.column_types.get('likert', [])
                overlapping = [c for c in valid_columns if c in likert_cols]
                if overlapping:
                    chart = self.chart_generator._create_likert_chart(df_subset, overlapping[0], file_id, title)
            
            # WORD_CLOUD - biểu đồ đám mây từ
            elif chart_type_enum == ChartType.WORD_CLOUD and len(valid_columns) >= 1:
                text_cols = self.column_types.get('text', [])
                overlapping = [c for c in valid_columns if c in text_cols]
                if overlapping and hasattr(self.chart_generator, '_create_word_cloud'):
                    chart = self.chart_generator._create_word_cloud(df_subset, overlapping[0], file_id, title)
            
            # Nếu không tạo được biểu đồ với các phương pháp trực tiếp, sử dụng generate_automatic_charts
            if not chart:
                logger.info(f"Using automatic chart generation for type {chart_type_enum}")
                auto_charts = self.chart_generator.generate_automatic_charts(
                    df_subset, 
                    chart_types=[chart_type_enum],
                    file_id=file_id
                )
                
                if auto_charts and isinstance(auto_charts, list) and len(auto_charts) > 0:
                    chart = auto_charts[0]
            
            # Nếu vẫn không tạo được, sử dụng phương thức create_recommended_chart
            if not chart:
                logger.info(f"Falling back to create_recommended_chart for type {chart_type_enum}")
                chart = self.create_recommended_chart(
                    df_subset, valid_columns, chart_type_enum, file_id
                )
            
            # Cập nhật tiêu đề và mô tả nếu được cung cấp
            if chart:
                if title:
                    chart.title = title
                if description:
                    chart.description = description
            
            return chart
        
        except Exception as e:
            logger.error(f"Error creating custom visualization: {str(e)}", exc_info=True)
            return None

    def create_recommended_chart(
        self, 
        df: pd.DataFrame, 
        columns: Optional[List[str]] = None,
        chart_type: Optional[str] = None,
        file_id: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """
        Tạo biểu đồ dựa trên khuyến nghị hoặc loại biểu đồ được chỉ định
        
        Args:
            df: DataFrame chứa dữ liệu
            columns: Cột sử dụng (nếu None, cột tốt nhất sẽ được chọn)
            chart_type: Loại biểu đồ cần tạo (nếu None, loại tốt nhất sẽ được chọn)
            file_id: ID file (nếu có)
            
        Returns:
            Optional[VisualizationData]: Dữ liệu biểu đồ
        """
        try:
            # Nếu không có cột được chỉ định, sử dụng tất cả cột
            if not columns:
                columns = df.columns.tolist()
            
            # Nếu không chỉ định loại biểu đồ, lấy khuyến nghị tốt nhất
            if not chart_type:
                best_charts = self.get_best_charts(df, columns, top_k=1, file_id=file_id)
                
                if best_charts and "error" not in best_charts[0]:
                    chart_type = best_charts[0]["chart_type"]
                    columns_to_use = best_charts[0]["columns"].split(" vs ")
                else:
                    # Mặc định là bar chart nếu không có khuyến nghị
                    chart_type = ChartType.BAR
                    columns_to_use = columns[:2] if len(columns) >= 2 else columns
            else:
                columns_to_use = columns
            
            # Đảm bảo đã phân tích kiểu cột (nếu chưa)
            if not self.column_types:
                self._analyze_column_types(df)
            
            # Chọn phương thức tạo biểu đồ phù hợp dựa trên loại biểu đồ
            chart_data = None
            
            # PHẦN MỚI: Tận dụng các loại biểu đồ chuyên biệt từ ChartGenerator
            
            # 1. Xử lý các loại biểu đồ đặc biệt
            if chart_type == ChartType.LIKERT:
                if len(columns_to_use) >= 1 and columns_to_use[0] in self.column_types.get('likert', []):
                    chart_data = self.chart_generator._create_likert_chart(df, columns_to_use[0], file_id)
            
            elif chart_type == ChartType.WORD_CLOUD:
                if len(columns_to_use) >= 1 and columns_to_use[0] in self.column_types.get('text', []):
                    if hasattr(self.chart_generator, '_create_word_cloud'):
                        chart_data = self.chart_generator._create_word_cloud(df, columns_to_use[0], file_id)
            
            elif chart_type == ChartType.HISTOGRAM:
                if len(columns_to_use) >= 1 and is_numeric_dtype(df[columns_to_use[0]]):
                    chart_data = self.chart_generator._create_distribution_chart(df, columns_to_use[0], file_id)
                elif len(columns_to_use) >= 2 and columns_to_use[0] in self.column_types.get('categorical', []) and is_numeric_dtype(df[columns_to_use[1]]):
                    chart_data = self.chart_generator._create_grouped_distribution(df, columns_to_use[0], columns_to_use[1], file_id)
            
            elif chart_type == ChartType.BAR:
                if len(columns_to_use) >= 1 and not is_numeric_dtype(df[columns_to_use[0]]):
                    chart_data = self.chart_generator._create_categorical_chart(df, columns_to_use[0], file_id)
                elif len(columns_to_use) >= 2:
                    # Bar chart cho categorical vs numeric
                    cat_col = None
                    num_col = None
                    
                    for col in columns_to_use[:2]:
                        if is_numeric_dtype(df[col]):
                            num_col = col
                        else:
                            cat_col = col
                    
                    if cat_col and num_col:
                        chart_data = self.chart_generator._create_group_chart(df, cat_col, num_col, file_id)
            
            elif chart_type == ChartType.PIE:
                if len(columns_to_use) >= 1 and columns_to_use[0] in self.column_types.get('categorical', []):
                    chart_data = self.chart_generator._create_pie_chart(df, columns_to_use[0], file_id)
            
            elif chart_type == ChartType.LINE:
                if len(columns_to_use) >= 2:
                    dt_col = None
                    num_col = None
                    
                    # Tìm cột datetime và numeric
                    for col in columns_to_use:
                        if col in self.column_types.get('datetime', []):
                            dt_col = col
                        elif is_numeric_dtype(df[col]):
                            num_col = col
                    
                    if dt_col and num_col:
                        chart_data = self.chart_generator.create_time_series_visualization(df, dt_col, num_col, file_id=file_id)
            
            elif chart_type == ChartType.SCATTER:
                if len(columns_to_use) >= 2 and all(is_numeric_dtype(df[col]) for col in columns_to_use[:2]):
                    # Nếu có cột thứ 3 là categorical, sử dụng color coding
                    if len(columns_to_use) >= 3 and not is_numeric_dtype(df[columns_to_use[2]]):
                        chart_data = self.chart_generator._create_scatter_chart(df, columns_to_use[0], columns_to_use[1], file_id)
                    else:
                        chart_data = self.chart_generator._create_scatter_chart(df, columns_to_use[0], columns_to_use[1], file_id)
            
            elif chart_type == ChartType.HEATMAP:
                if len(columns_to_use) >= 2:
                    if all(is_numeric_dtype(df[col]) for col in columns_to_use):
                        chart_data = self.chart_generator._create_correlation_chart(df, columns_to_use, file_id)
            
            elif chart_type == ChartType.BOX:
                if len(columns_to_use) >= 1 and is_numeric_dtype(df[columns_to_use[0]]):
                    chart_data = self.chart_generator._create_box_plot(df, columns_to_use[0], file_id)
            
            # Nếu không tạo được biểu đồ, dùng phương thức khuyến nghị tự động
            if not chart_data:
                logger.warning(f"Couldn't create chart type {chart_type}. Using automatic chart generation.")
                chart_data = self.chart_generator.generate_automatic_charts(
                    df, 
                    chart_types=[chart_type] if chart_type else None,
                    file_id=file_id
                )
                
                if isinstance(chart_data, list) and chart_data:
                    chart_data = chart_data[0]
                
            # Thêm file_id nếu có và chưa được đặt
            if chart_data and file_id and not chart_data.fileId:
                chart_data.fileId = file_id
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error creating recommended chart: {str(e)}", exc_info=True)
            return None

    def generate_all_charts(self, df: pd.DataFrame, file_id: Optional[str]=None, top_k: int = 6) -> List[VisualizationData]:
        """
        Tạo top k biểu đồ được khuyến nghị tốt nhất
        
        Args:
            df: DataFrame chứa dữ liệu
            file_id: ID file (nếu có)
            top_k: Số lượng biểu đồ tối đa cần tạo
            
        Returns:
            List[VisualizationData]: Danh sách các biểu đồ đã tạo
        """
        charts = []
        
        try:
            # Lấy top k khuyến nghị
            best_charts = self.get_best_charts(df, None, top_k, file_id)
            
            # Tạo biểu đồ cho mỗi khuyến nghị
            for recommendation in best_charts:
                if "error" in recommendation:
                    continue
                
                chart_type = recommendation["chart_type"]
                columns = recommendation["columns"].split(" vs ")
                
                # Tạo biểu đồ
                chart = self.create_recommended_chart(df, columns, chart_type, file_id)
                if chart:
                    # Thêm thông tin từ khuyến nghị vào chart
                    chart.title = recommendation.get("title", chart.title)
                    chart.description = recommendation.get("description", chart.description)
                    
                    charts.append(chart)
            
            # Nếu không tạo được biểu đồ với khuyến nghị, thử tạo biểu đồ tự động
            if not charts:
                auto_charts = self.chart_generator.generate_automatic_charts(df, file_id=file_id)
                if auto_charts and isinstance(auto_charts, list):
                    charts.extend(auto_charts[:top_k])
            
            return charts
        except Exception as e:
            logger.error(f"Error generating all charts: {str(e)}", exc_info=True)
            return charts

    def _validate_data_quality(self, df: pd.DataFrame) -> None:
        """
        Đánh giá chất lượng dữ liệu để cải thiện khuyến nghị biểu đồ
        
        Args:
            df: DataFrame cần đánh giá
        """
        try:
            df_hash = self._generate_df_hash(df)
            
            # Kiểm tra xem đã phân tích dữ liệu này chưa
            if df_hash in self.validation_results:
                logger.debug(f"Using cached validation results for DataFrame hash: {df_hash}")
                return
            
            # Thực hiện đánh giá chất lượng
            validation_report = self.data_validator.validate_dataset(df)
            
            # Lưu kết quả vào cache
            self.validation_results[df_hash] = validation_report
            
            logger.info(f"Data quality validated. Overall score: {validation_report.get('quality_metrics', {}).get('overall_score', 0)}")
        except Exception as e:
            logger.error(f"Error validating data quality: {str(e)}")
            self.validation_results = {}

    def _analyze_column_types(self, df: pd.DataFrame) -> None:
        """
        Phân tích kiểu dữ liệu của các cột
        
        Args:
            df: DataFrame cần phân tích
        """
        try:
            df_hash = self._generate_df_hash(df)
            
            # Kiểm tra xem đã phân tích dữ liệu này chưa
            if df_hash in self.column_types:
                logger.debug(f"Using cached column types for DataFrame hash: {df_hash}")
                return
            
            # Sử dụng DataProcessor để phát hiện kiểu cột nâng cao
            self.column_types = self.data_processor.get_column_types(df)
            
            # Phân tích tương quan giữa các cột numeric
            numeric_cols = self.column_types.get('numeric', [])
            if len(numeric_cols) > 1:
                self.column_correlations = df[numeric_cols].corr().to_dict()
            
            # Phân tích feature importance
            self.feature_importance = self._analyze_feature_importance(df, numeric_cols)
            
            logger.info(f"Column analysis completed. Found {len(numeric_cols)} numeric, "
                      f"{len(self.column_types.get('categorical', []))} categorical, "
                      f"{len(self.column_types.get('datetime', []))} datetime columns.")
        except Exception as e:
            logger.error(f"Error analyzing column types: {str(e)}")
            self.column_types = {}

    def _analyze_feature_importance(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, float]:
        """
        Phân tích tầm quan trọng của các features
        
        Args:
            df: DataFrame chứa dữ liệu
            numeric_cols: Danh sách cột numeric
            
        Returns:
            Dict[str, float]: Từ điển với key là tên cột, value là điểm quan trọng
        """
        if len(numeric_cols) < 2:
            return {}
            
        try:
            # Phương pháp 1: Dựa trên phương sai
            variances = df[numeric_cols].var()
            total_variance = variances.sum()
            if total_variance == 0:
                return {}
                
            importance_by_variance = {col: var / total_variance for col, var in variances.items()}
            
            # Phương pháp 2: Dựa trên tương quan
            if len(numeric_cols) > 2:
                corr_matrix = df[numeric_cols].corr().abs()
                
                # Điểm quan trọng dựa trên tổng tương quan với các cột khác
                importance_by_correlation = {}
                for col in numeric_cols:
                    # Loại bỏ tương quan với chính nó (= 1)
                    col_corr = corr_matrix[col].sum() - 1
                    importance_by_correlation[col] = col_corr
                
                # Chuẩn hóa để tổng bằng 1
                total_corr = sum(importance_by_correlation.values())
                if total_corr > 0:
                    importance_by_correlation = {k: v / total_corr for k, v in importance_by_correlation.items()}
                
                # Kết hợp hai phương pháp
                combined_importance = {}
                for col in numeric_cols:
                    var_score = importance_by_variance.get(col, 0)
                    corr_score = importance_by_correlation.get(col, 0)
                    combined_importance[col] = (var_score + corr_score) / 2
                
                return combined_importance
            else:
                return importance_by_variance
        except Exception as e:
            logger.error(f"Error analyzing feature importance: {str(e)}")
            return {}

    def _generate_df_hash(self, df: pd.DataFrame) -> str:
        """
        Tạo hash key cho DataFrame dựa trên shape, columns và sample values
        
        Args:
            df: DataFrame cần tạo hash
            
        Returns:
            str: Hash key
        """
        import hashlib
        
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

    # ===== PHƯƠNG THỨC KHUYẾN NGHỊ CỘT ĐƠN LẺ =====
    
    def _recommend_numeric_column(self, df: pd.DataFrame, column: str) -> Dict:
        """Khuyến nghị biểu đồ cho cột numeric đơn lẻ"""
        charts = []
        
        # Histogram với phát hiện phân phối
        histogram_chart = {
            "type": ChartType.HISTOGRAM,
            "score": 0.9,
            "title": f"Phân phối của {column}",
            "description": f"Biểu đồ histogram thể hiện phân phối các giá trị của {column}",
            "category": "distribution",
            "complexity": "low"
        }
        charts.append(histogram_chart)
        
        # Box Plot
        boxplot_chart = {
            "type": ChartType.BOX,
            "score": 0.8,
            "title": f"Box Plot của {column}",
            "description": f"Biểu đồ box plot thể hiện phân phối và outliers của {column}",
            "category": "distribution",
            "complexity": "medium"
        }
        charts.append(boxplot_chart)
        
        # Violin plot (mới)
        violin_chart = {
            "type": ChartType.VIOLIN,
            "score": 0.7,
            "title": f"Violin Plot của {column}",
            "description": f"Biểu đồ violin plot thể hiện phân phối chi tiết của {column}",
            "category": "distribution",
            "complexity": "high"
        }
        charts.append(violin_chart)
        
        # Skewness modifies scores
        try:
            skewness = df[column].skew()
            if abs(skewness) > 1.0:
                # If highly skewed, boost histogram score
                histogram_chart["score"] = 1.0
                # Add note about skewness
                skew_direction = "phải" if skewness > 0 else "trái"
                histogram_chart["description"] += f" (dữ liệu có độ lệch {skew_direction} cao: {skewness:.2f})"
        except:
            pass
        
        # Outliers modify scores
        try:
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            outliers = ((df[column] < q1 - 1.5 * iqr) | (df[column] > q3 + 1.5 * iqr)).sum()
            outlier_pct = outliers / len(df[column].dropna()) * 100
            
            if outlier_pct > 5:
                # If many outliers, boost box plot score
                boxplot_chart["score"] = 0.95
                boxplot_chart["description"] += f" ({outlier_pct:.1f}% outliers)"
        except:
            pass
        
        # Add ECDF chart for continuous distributions
        try:
            if df[column].nunique() > len(df) * 0.3:  # Likely continuous data
                ecdf_chart = {
                    "type": ChartType.LINE,  # Using line for ECDF
                    "score": 0.75,
                    "title": f"Phân phối tích lũy của {column}",
                    "description": f"Hàm phân phối tích lũy thực nghiệm (ECDF) cho {column}",
                    "category": "distribution",
                    "subcategory": "cumulative",
                    "complexity": "medium"
                }
                charts.append(ecdf_chart)
        except:
            pass
        
        # Điều chỉnh score dựa trên chất lượng dữ liệu
        if self.validation_results:
            validation = self.validation_results.get("quality_metrics", {})
            outlier_stats = validation.get("integrity", {}).get("outlier_stats", {})
            
            if column in outlier_stats:
                outlier_pct = outlier_stats[column].get("outlier_percent", 0)
                if outlier_pct > 10:
                    boxplot_chart["score"] += 0.1
                    boxplot_chart["description"] += f" (phát hiện {outlier_pct:.1f}% outliers)"
            
            missing_cols = validation.get("completeness", {}).get("columns_with_missing", [])
            for missing_info in missing_cols:
                if missing_info.get("column") == column and missing_info.get("missing_percent", 0) > 5:
                    missing_pct = missing_info.get("missing_percent")
                    for chart in charts:
                        chart["description"] += f" (Lưu ý: {missing_pct:.1f}% giá trị bị thiếu)"
                        chart["score"] -= 0.05  # Trừ nhẹ score do có missing values
        
        return {
            "columns": [column],
            "column_types": ["numeric"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }

    def _recommend_categorical_column(self, df: pd.DataFrame, column: str) -> Dict:
        """Khuyến nghị biểu đồ cho cột categorical đơn lẻ"""
        charts = []
        
        # Đếm số lượng category
        n_categories = df[column].nunique()
        
        # Bar Chart
        bar_chart = {
            "type": ChartType.BAR,
            "score": 0.9,
            "title": f"Tần suất của {column}",
            "description": f"Biểu đồ cột thể hiện phân phối các giá trị của {column}",
            "category": "categorical",
            "complexity": "low"
        }
        charts.append(bar_chart)
        
        # Pie Chart (nếu không quá nhiều category)
        if n_categories <= 8:
            pie_chart = {
                "type": ChartType.PIE,
                "score": 0.7,
                "title": f"Phân phối của {column}",
                "description": f"Biểu đồ tròn thể hiện phân phối của các giá trị {column}",
                "category": "categorical",
                "complexity": "low"
            }
            charts.append(pie_chart)
        
        # Treemap for many categories (new)
        if 8 < n_categories <= 20:
            treemap_chart = {
                "type": ChartType.TREEMAP,
                "score": 0.65,
                "title": f"Treemap của {column}",
                "description": f"Biểu đồ treemap thể hiện phân phối các giá trị của {column}",
                "category": "categorical",
                "complexity": "medium"
            }
            charts.append(treemap_chart)
        
        # Điều chỉnh score dựa trên số lượng category
        if n_categories <= 5:
            # Với ít category, pie chart tốt hơn
            for chart in charts:
                if chart["type"] == ChartType.PIE:
                    chart["score"] = 0.85
        elif n_categories > 15:
            # Với quá nhiều category, giảm điểm bar chart
            for chart in charts:
                if chart["type"] == ChartType.BAR:
                    chart["score"] = 0.7
                    chart["description"] += " (nên nhóm các giá trị nhỏ để biểu đồ dễ đọc hơn)"
        
        # Check value distribution
        try:
            value_counts = df[column].value_counts(normalize=True)
            # If one category dominates (>80%)
            if value_counts.iloc[0] > 0.8:
                for chart in charts:
                    if chart["type"] == ChartType.PIE:
                        chart["description"] += f" (chủ yếu là '{value_counts.index[0]}' với {value_counts.iloc[0]*100:.1f}%)"
        except:
            pass
        
        # Điều chỉnh score dựa trên chất lượng dữ liệu
        if self.validation_results:
            validation = self.validation_results.get("quality_metrics", {})
            
            # Kiểm tra tính nhất quán
            consistency_issues = validation.get("consistency", {}).get("inconsistent_columns", [])
            for issue in consistency_issues:
                if issue.get("column") == column:
                    issue_type = issue.get("issue", "")
                    if "inconsistent_capitalization" in issue_type:
                        for chart in charts:
                            chart["description"] += " (có vấn đề về viết hoa/thường không nhất quán)"
                            chart["score"] -= 0.05
            
            # Kiểm tra missing values
            missing_cols = validation.get("completeness", {}).get("columns_with_missing", [])
            for missing_info in missing_cols:
                if missing_info.get("column") == column and missing_info.get("missing_percent", 0) > 5:
                    missing_pct = missing_info.get("missing_percent")
                    for chart in charts:
                        chart["description"] += f" (Lưu ý: {missing_pct:.1f}% giá trị bị thiếu)"
        
        return {
            "columns": [column],
            "column_types": ["categorical"],
            "n_categories": n_categories,
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }

    def _recommend_datetime_column(self, df: pd.DataFrame, column: str) -> Dict:
        """Khuyến nghị biểu đồ cho cột datetime đơn lẻ"""
        charts = []
        
        # Lấy thông tin về datetime column
        df_with_dt = df.copy()
        if not is_datetime64_any_dtype(df_with_dt[column]):
            try:
                df_with_dt[column] = convert_to_datetime(df_with_dt[column])
            except:
                return {
                    "columns": [column],
                    "column_types": ["datetime"],
                    "charts": [{
                        "type": ChartType.HISTOGRAM,
                        "score": 0.5,
                        "title": f"Phân phối của {column}",
                        "description": f"Không thể parse giá trị datetime cho {column}"
                    }]
                }
        
        # Histogram by time period
        histogram_chart = {
            "type": ChartType.HISTOGRAM,
            "score": 0.8,
            "title": f"Phân phối của {column}",
            "description": f"Biểu đồ histogram thể hiện phân phối thời gian cho {column}",
            "category": "temporal",
            "complexity": "low"
        }
        charts.append(histogram_chart)
        
        # Timeline
        timeline_chart = {
            "type": ChartType.LINE,
            "score": 0.7,
            "title": f"Timeline của {column}",
            "description": f"Biểu đồ timeline thể hiện các sự kiện theo thời gian {column}",
            "category": "temporal",
            "complexity": "medium"
        }
        charts.append(timeline_chart)
        
        # Heatmap calendar (new)
        calendar_chart = {
            "type": ChartType.HEATMAP, 
            "score": 0.6,
            "title": f"Biểu đồ nhiệt lịch của {column}",
            "description": f"Biểu đồ nhiệt dạng lịch thể hiện phân phối các ngày/tháng cho {column}",
            "category": "temporal",
            "subcategory": "calendar",
            "complexity": "high"
        }
        charts.append(calendar_chart)
        
        # Điều chỉnh score dựa trên dải thời gian
        try:
            date_range = (df_with_dt[column].max() - df_with_dt[column].min()).total_seconds()
            
            if date_range <= 86400:  # 1 day
                # Nếu dữ liệu chỉ trong 1 ngày, khuyến nghị histogram theo giờ
                histogram_chart["score"] = 0.9
                histogram_chart["description"] = f"Biểu đồ histogram thể hiện phân phối theo giờ cho {column}"
                timeline_chart["score"] = 0.85
                timeline_chart["description"] = f"Biểu đồ timeline thể hiện các sự kiện theo giờ cho {column}"
                calendar_chart["score"] = 0.4  # Less useful for single day
            elif date_range <= 2592000:  # 30 days
                # Nếu dữ liệu trong 1 tháng, khuyến nghị histogram theo ngày
                histogram_chart["score"] = 0.9
                histogram_chart["description"] = f"Biểu đồ histogram thể hiện phân phối theo ngày cho {column}"
                calendar_chart["score"] = 0.75
                calendar_chart["description"] = f"Biểu đồ nhiệt dạng lịch thể hiện mẫu hàng ngày cho {column}"
            elif date_range <= 31536000:  # 1 year
                # Nếu dữ liệu trong 1 năm, khuyến nghị histogram theo tháng
                histogram_chart["score"] = 0.9
                histogram_chart["description"] = f"Biểu đồ histogram thể hiện phân phối theo tháng cho {column}"
                calendar_chart["score"] = 0.8
                calendar_chart["description"] = f"Biểu đồ nhiệt dạng lịch thể hiện mẫu theo tháng cho {column}"
            else:
                # Nếu dữ liệu trên 1 năm, khuyến nghị histogram theo năm
                histogram_chart["score"] = 0.9
                histogram_chart["description"] = f"Biểu đồ histogram thể hiện phân phối theo năm cho {column}"
                
                # Check for seasonality
                try:
                    # Count by month across all years
                    month_counts = df_with_dt[column].dt.month.value_counts()
                    if month_counts.std() / month_counts.mean() > 0.3:  # High variation by month
                        seasonal_chart = {
                            "type": ChartType.LINE,
                            "score": 0.85,
                            "title": f"Mẫu theo mùa trong {column}",
                            "description": f"Biểu đồ đường thể hiện mẫu theo mùa theo tháng cho {column}",
                            "category": "temporal",
                            "subcategory": "seasonality",
                            "complexity": "high"
                        }
                        charts.append(seasonal_chart)
                except:
                    pass
        except:
            pass
        
        # Điều chỉnh score dựa trên chất lượng dữ liệu
        if self.validation_results:
            validation = self.validation_results.get("quality_metrics", {})
            
            # Kiểm tra vấn đề về ngày tháng
            date_violations = validation.get("integrity", {}).get("date_violations", [])
            for violation in date_violations:
                if violation.get("column") == column:
                    issue_type = violation.get("issue", "")
                    if "future_dates" in issue_type and violation.get("percent", 0) > 1:
                        future_pct = violation.get("percent", 0)
                        for chart in charts:
                            chart["description"] += f" (Lưu ý: Có {future_pct:.1f}% ngày trong tương lai)"
                            chart["score"] -= 0.1
                    elif "old_dates" in issue_type and violation.get("percent", 0) > 5:
                        old_pct = violation.get("percent", 0)
                        for chart in charts:
                            chart["description"] += f" (Lưu ý: Có {old_pct:.1f}% ngày quá cũ (trước 1900))"
                            chart["score"] -= 0.05
                    elif "irregular_time_intervals" in issue_type:
                        for chart in charts:
                            chart["description"] += " (Dữ liệu có khoảng thời gian không đều)"
        
        return {
            "columns": [column],
            "column_types": ["datetime"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_likert_column(self, df: pd.DataFrame, column: str) -> Dict:
        """Khuyến nghị biểu đồ cho cột thang đo Likert"""
        charts = []
        
        # Tính số điểm trên thang đo
        unique_values = sorted(df[column].dropna().unique())
        n_points = len(unique_values)
        min_val = min(unique_values) if len(unique_values) > 0 else 0
        max_val = max(unique_values) if len(unique_values) > 0 else 5
        
        # Horizontal Bar Chart (đặc thù cho Likert)
        likert_chart = {
            "type": ChartType.LIKERT,
            "score": 0.95,
            "title": f"Phân phối thang đo {column}",
            "description": f"Biểu đồ ngang thể hiện phân phối trên thang đo {min_val}-{max_val} cho {column}",
            "category": "specialized",
            "subcategory": "likert",
            "complexity": "medium"
        }
        charts.append(likert_chart)
        
        # Bar Chart (thay thế)
        bar_chart = {
            "type": ChartType.BAR,
            "score": 0.8,
            "title": f"Phân phối điểm {column}",
            "description": f"Biểu đồ cột thể hiện phân phối điểm {min_val}-{max_val} cho {column}",
            "category": "categorical",
            "complexity": "low"
        }
        charts.append(bar_chart)
        
        # Histogram style (nếu nhiều điểm)
        if n_points >= 5:
            hist_chart = {
                "type": ChartType.HISTOGRAM,
                "score": 0.7,
                "title": f"Phân phối thang đo {column}",
                "description": f"Biểu đồ histogram thể hiện phân phối thang đo {column}",
                "category": "distribution",
                "complexity": "low"
            }
            charts.append(hist_chart)
        
        # Kiểm tra cách phân phối
        try:
            value_counts = df[column].value_counts().sort_index()
            
            # Nếu tập trung ở cực đoan
            if (value_counts.iloc[0] + value_counts.iloc[-1]) / value_counts.sum() > 0.6:
                for chart in charts:
                    chart["description"] += " (phân phối có xu hướng tập trung ở hai cực)"
            
            # Nếu có phân phối đều
            if value_counts.std() / value_counts.mean() < 0.3:
                for chart in charts:
                    chart["description"] += " (phân phối khá đều giữa các mức độ)"
                    
            # Nếu có một đỉnh rõ ràng
            max_val_idx = value_counts.argmax()
            max_val = value_counts.index[max_val_idx]
            max_pct = value_counts.iloc[max_val_idx] / value_counts.sum() * 100
            
            if max_pct > 40:
                for chart in charts:
                    chart["description"] += f" (tập trung ở mức {max_val} với {max_pct:.1f}%)"
        except:
            pass
        
        return {
            "columns": [column],
            "column_types": ["likert"],
            "n_points": n_points,
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_binary_column(self, df: pd.DataFrame, column: str) -> Dict:
        """Khuyến nghị biểu đồ cho cột binary"""
        charts = []
        
        # Pie Chart cho binary
        pie_chart = {
            "type": ChartType.PIE,
            "score": 0.9,
            "title": f"Phân phối {column}",
            "description": f"Biểu đồ tròn thể hiện phân phối giá trị nhị phân của {column}",
            "category": "specialized",
            "subcategory": "binary",
            "complexity": "low"
        }
        charts.append(pie_chart)
        
        # Bar Chart 
        bar_chart = {
            "type": ChartType.BAR,
            "score": 0.8,
            "title": f"Tần suất {column}",
            "description": f"Biểu đồ cột thể hiện tần suất giá trị nhị phân của {column}",
            "category": "specialized",
            "subcategory": "binary",
            "complexity": "low"
        }
        charts.append(bar_chart)
        
        # Donut Chart
        donut_chart = {
            "type": ChartType.DONUT,
            "score": 0.7,
            "title": f"Phân phối {column}",
            "description": f"Biểu đồ donut thể hiện phân phối giá trị nhị phân của {column}",
            "category": "specialized",
            "subcategory": "binary",
            "complexity": "low"
        }
        charts.append(donut_chart)
        
        # Kiểm tra cách phân phối
        try:
            value_counts = df[column].value_counts(normalize=True)
            
            # Nếu phân phối rất không cân bằng
            if value_counts.iloc[0] > 0.9:
                imbalance_label = value_counts.index[0]
                imbalance_pct = value_counts.iloc[0] * 100
                
                for chart in charts:
                    chart["description"] += f" (phân phối rất mất cân bằng: {imbalance_pct:.1f}% là '{imbalance_label}')"
                    chart["score"] -= 0.1  # Trừ score do phân phối mất cân bằng 
            
            # Nếu phân phối khá cân bằng
            elif 0.4 <= value_counts.iloc[0] <= 0.6:
                for chart in charts:
                    chart["description"] += " (phân phối khá cân bằng giữa hai giá trị)"
                    chart["score"] += 0.05  # Tăng score do phân phối cân bằng tốt
        except:
            pass
        
        return {
            "columns": [column],
            "column_types": ["binary"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_text_column(self, df: pd.DataFrame, column: str) -> Dict:
        """Khuyến nghị biểu đồ cho cột text"""
        charts = []
        
        # Word Cloud
        wordcloud_chart = {
            "type": ChartType.WORD_CLOUD,
            "score": 0.9,
            "title": f"Word Cloud của {column}",
            "description": f"Biểu đồ word cloud thể hiện từ khóa phổ biến trong {column}",
            "category": "specialized",
            "subcategory": "text",
            "complexity": "high"
        }
        charts.append(wordcloud_chart)
        
        # Text Length Distribution
        length_chart = {
            "type": ChartType.HISTOGRAM,
            "score": 0.8,
            "title": f"Phân phối độ dài {column}",
            "description": f"Biểu đồ histogram thể hiện phân phối độ dài văn bản trong {column}",
            "category": "specialized",
            "subcategory": "text",
            "complexity": "medium"
        }
        charts.append(length_chart)
        
        # Kiểm tra dữ liệu
        try:
            # Kiểm tra độ dài text
            text_lengths = df[column].astype(str).str.len()
            avg_len = text_lengths.mean()
            max_len = text_lengths.max()
            
            if avg_len < 20:
                for chart in charts:
                    if chart["type"] == ChartType.WORD_CLOUD:
                        chart["score"] = 0.7
                        chart["description"] += " (văn bản quá ngắn cho word cloud)"
            elif avg_len > 1000:
                for chart in charts:
                    if chart["type"] == ChartType.WORD_CLOUD:
                        chart["score"] = 0.95
                        chart["description"] += " (văn bản dài, thích hợp cho phân tích từ khóa)"
            
            # Thêm thông tin về độ dài
            for chart in charts:
                if chart["type"] == ChartType.HISTOGRAM:
                    chart["description"] += f" (độ dài trung bình: {avg_len:.1f} ký tự, tối đa: {max_len} ký tự)"
        except:
            pass
        
        return {
            "columns": [column],
            "column_types": ["text"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_range_column(self, df: pd.DataFrame, column: str) -> Dict:
        """Khuyến nghị biểu đồ cho cột range (ví dụ: "10-20", "dưới 30"...)"""
        charts = []
        
        if is_numeric_dtype(df[column]):
            # Range-Numeric: Treat more like numeric with special handling
            histogram_chart = {
                "type": ChartType.HISTOGRAM,
                "score": 0.9,
                "title": f"Phân phối của {column}",
                "description": f"Biểu đồ histogram thể hiện phân phối các giá trị của {column}",
                "category": "specialized",
                "subcategory": "range"
            }
            charts.append(histogram_chart)
            
            boxplot_chart = {
                "type": ChartType.BOX,
                "score": 0.8,
                "title": f"Box Plot của {column}",
                "description": f"Biểu đồ box plot thể hiện phân phối và outliers của {column}",
                "category": "specialized",
                "subcategory": "range"
            }
            charts.append(boxplot_chart)
        else:
            # Range-Categorical: Treat as specialized categorical
            bar_chart = {
                "type": ChartType.BAR,
                "score": 0.9,
                "title": f"Phân phối của {column}",
                "description": f"Biểu đồ cột thể hiện phân phối các khoảng giá trị của {column}",
                "category": "specialized", 
                "subcategory": "range"
            }
            charts.append(bar_chart)
            
            pie_chart = {
                "type": ChartType.PIE,
                "score": 0.7,
                "title": f"Phân phối của {column}",
                "description": f"Biểu đồ tròn thể hiện phân phối các khoảng giá trị của {column}",
                "category": "specialized",
                "subcategory": "range"
            }
            charts.append(pie_chart)
        
        # Thêm recommended range-specific visualizations
        range_chart = {
            "type": ChartType.RANGE,
            "score": 0.85,
            "title": f"Phân phối khoảng của {column}",
            "description": f"Biểu đồ đặc biệt thể hiện các khoảng giá trị trong {column}",
            "category": "specialized",
            "subcategory": "range",
            "complexity": "medium"
        }
        charts.append(range_chart)
        
        try:
            # Phân tích giá trị
            is_categorical = not is_numeric_dtype(df[column])
            
            if is_categorical:
                value_counts = df[column].value_counts()
                
                # Kiểm tra nếu có thứ tự tự nhiên (e.g. "0-10", "11-20", ...)
                if len(value_counts) >= 3:
                    ordered = True
                    for chart in charts:
                        chart["description"] += " (các khoảng có thứ tự tự nhiên)"
                        if chart["type"] == ChartType.RANGE:
                            chart["score"] = 0.95  # Boost range chart more
        except:
            pass
            
        return {
            "columns": [column],
            "column_types": ["range"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }

    # ===== PHƯƠNG THỨC KHUYẾN NGHỊ QUAN HỆ 2 CỘT =====
    
    def _recommend_numeric_vs_numeric(self, df: pd.DataFrame, col1: str, col2: str) -> Dict:
        """Khuyến nghị biểu đồ cho 2 cột numeric"""
        charts = []
        
        # Scatter Plot
        scatter_chart = {
            "type": ChartType.SCATTER,
            "score": 0.9,
            "title": f"Mối quan hệ giữa {col1} và {col2}",
            "description": f"Biểu đồ scatter plot thể hiện mối quan hệ giữa {col1} và {col2}",
            "category": "relationship",
            "subcategory": "numeric",
            "complexity": "medium"
        }
        charts.append(scatter_chart)
        
        # Line chart cho xu hướng
        line_chart = {
            "type": ChartType.LINE,
            "score": 0.7,
            "title": f"Xu hướng {col2} theo {col1}",
            "description": f"Biểu đồ đường xu hướng thể hiện mối quan hệ giữa {col1} và {col2}",
            "category": "relationship",
            "subcategory": "numeric",
            "complexity": "medium"
        }
        charts.append(line_chart)
        
        # Heatmap for dense data
        if len(df) > 1000:
            heatmap_chart = {
                "type": ChartType.HEATMAP,
                "score": 0.7,
                "title": f"Mật độ dữ liệu {col1} vs {col2}",
                "description": f"Biểu đồ nhiệt thể hiện mật độ điểm dữ liệu giữa {col1} và {col2}",
                "category": "relationship",
                "subcategory": "density",
                "complexity": "high"
            }
            charts.append(heatmap_chart)
        
        # Hexbin for very large datasets
        if len(df) > 5000:
            hexbin_chart = {
                "type": ChartType.HEXBIN,
                "score": 0.75,
                "title": f"Hexagonal Binning của {col1} vs {col2}",
                "description": f"Biểu đồ hexbin thể hiện mật độ phân phối giữa {col1} và {col2}",
                "category": "relationship",
                "subcategory": "density",
                "complexity": "high"
            }
            charts.append(hexbin_chart)
        
        # Điều chỉnh score dựa trên tương quan
        try:
            correlation = df[[col1, col2]].corr().iloc[0, 1]
            
            if not pd.isna(correlation):
                # Add correlation line to scatter
                scatter_chart["description"] += f" (tương quan: {correlation:.2f})"
                
                if abs(correlation) > 0.7:
                    # Tương quan mạnh
                    scatter_chart["score"] = 1.0
                    scatter_chart["description"] = f"Biểu đồ scatter plot thể hiện mối tương quan {'dương' if correlation > 0 else 'âm'} mạnh ({correlation:.2f}) giữa {col1} và {col2}"
                    
                    # Add regression line chart
                    regression_chart = {
                        "type": ChartType.LINE,
                        "score": 0.85,
                        "title": f"Hồi quy {col2} theo {col1}",
                        "description": f"Biểu đồ đường thể hiện quan hệ hồi quy giữa {col1} và {col2} (tương quan: {correlation:.2f})",
                        "category": "relationship",
                        "subcategory": "regression",
                        "complexity": "high"
                    }
                    charts.append(regression_chart)
                    
                elif abs(correlation) > 0.3:
                    # Tương quan trung bình
                    scatter_chart["score"] = 0.95
                    scatter_chart["description"] = f"Biểu đồ scatter plot thể hiện mối tương quan {'dương' if correlation > 0 else 'âm'} trung bình ({correlation:.2f}) giữa {col1} và {col2}"
                    
                    # Add regression line chart with lower score
                    regression_chart = {
                        "type": ChartType.LINE,
                        "score": 0.65,
                        "title": f"Hồi quy {col2} theo {col1}",
                        "description": f"Biểu đồ đường thể hiện quan hệ hồi quy giữa {col1} và {col2} (tương quan: {correlation:.2f})",
                        "category": "relationship",
                        "subcategory": "regression",
                        "complexity": "high"
                    }
                    charts.append(regression_chart)
        except:
            pass
        
        # Điều chỉnh score dựa trên số lượng dữ liệu
        if len(df) > 5000:
            # For very large datasets, hexbin/heatmap might be better than scatter
            for chart in charts:
                if chart["type"] == ChartType.HEXBIN:
                    chart["score"] = 0.95
                elif chart["type"] == ChartType.HEATMAP:
                    chart["score"] = 0.9
                elif chart["type"] == ChartType.SCATTER:
                    chart["score"] = 0.85
                    chart["description"] += " (dữ liệu lớn, sẽ áp dụng sampling)"
        
        # Kiểm tra có outliers không 
        try:
            if self.validation_results:
                outlier_stats = self.validation_results.get("quality_metrics", {}).get("integrity", {}).get("outlier_stats", {})
                
                if col1 in outlier_stats and col2 in outlier_stats:
                    outlier_pct1 = outlier_stats[col1].get("outlier_percent", 0)
                    outlier_pct2 = outlier_stats[col2].get("outlier_percent", 0)
                    
                    if outlier_pct1 > 5 or outlier_pct2 > 5:
                        for chart in charts:
                            chart["description"] += f" (Lưu ý: {col1} có {outlier_pct1:.1f}% và {col2} có {outlier_pct2:.1f}% outliers)"
        except:
            pass
        
        return {
            "columns": [col1, col2],
            "column_types": ["numeric", "numeric"],
            "correlation": None if not 'correlation' in locals() or pd.isna(correlation) else float(correlation),
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }

    def _recommend_categorical_vs_numeric(self, df: pd.DataFrame, cat_col: str, num_col: str) -> Dict:
        """Khuyến nghị biểu đồ cho 1 cột categorical và 1 cột numeric"""
        charts = []
        
        # Đếm số lượng category
        n_categories = df[cat_col].nunique()
        
        # Bar Chart
        bar_chart = {
            "type": ChartType.BAR,
            "score": 0.9,
            "title": f"{num_col} trung bình theo {cat_col}",
            "description": f"Biểu đồ cột thể hiện giá trị trung bình của {num_col} cho từng {cat_col}",
            "category": "comparison",
            "subcategory": "categories",
            "complexity": "medium"
        }
        charts.append(bar_chart)
        
        # Box Plot
        boxplot_chart = {
            "type": ChartType.BOX,
            "score": 0.8,
            "title": f"Phân phối {num_col} theo {cat_col}",
            "description": f"Biểu đồ box plot thể hiện phân phối của {num_col} cho từng nhóm {cat_col}",
            "category": "comparison",
            "subcategory": "distributions",
            "complexity": "medium"
        }
        charts.append(boxplot_chart)
        
        # Violin Plot for showing distribution details
        if n_categories <= 8:  # Only for reasonable number of categories
            violin_chart = {
                "type": ChartType.VIOLIN,
                "score": 0.75,
                "title": f"Phân phối chi tiết {num_col} theo {cat_col}",
                "description": f"Biểu đồ violin plot thể hiện phân phối chi tiết của {num_col} cho từng nhóm {cat_col}",
                "category": "comparison",
                "subcategory": "distributions",
                "complexity": "high"
            }
            charts.append(violin_chart)
        
        # Grouped histogram (mới)
        if n_categories <= 5:
            grouped_hist_chart = {
                "type": ChartType.GROUPED_HISTOGRAM,
                "score": 0.85,
                "title": f"So sánh phân phối {num_col} theo {cat_col}",
                "description": f"Biểu đồ histogram nhóm thể hiện sự khác biệt phân phối của {num_col} theo các giá trị {cat_col}",
                "category": "comparison",
                "subcategory": "distributions",
                "complexity": "high"
            }
            charts.append(grouped_hist_chart)
        
        # Điều chỉnh score dựa trên số lượng category
        if n_categories > 10:
            # Với quá nhiều category, giảm điểm bar chart
            bar_chart["score"] = 0.7
            bar_chart["description"] += " (nên nhóm các giá trị để biểu đồ dễ đọc hơn)"
            
            # Box plot có thể tốt hơn khi có nhiều category
            boxplot_chart["score"] = 0.85
        elif n_categories <= 5:
            # Với ít category, bar chart rất tốt
            bar_chart["score"] = 1.0
            
            # And violin plots are very informative
            if any(chart["type"] == ChartType.VIOLIN for chart in charts):
                for chart in charts:
                    if chart["type"] == ChartType.VIOLIN:
                        chart["score"] = 0.85
        
        # Check for significant differences between groups
        try:
            from scipy import stats
            
            # Group by category and get stats
            group_means = df.groupby(cat_col)[num_col].mean()
            group_std = df.groupby(cat_col)[num_col].std()
            
            # Calculate coefficient of variation of the means
            cv = group_means.std() / group_means.mean() if group_means.mean() != 0 else 0
            
            # If there's significant variation between groups
            if cv > 0.2:  # arbitrary threshold
                bar_chart["score"] += 0.05
                bar_chart["description"] += f" (có sự khác biệt đáng kể giữa các nhóm: {cv:.2f})"
                
                # Try ANOVA if we have enough groups
                if n_categories >= 3:
                    groups = [df[df[cat_col] == cat][num_col].dropna() for cat in df[cat_col].unique()]
                    groups = [g for g in groups if len(g) > 0]
                    
                    if len(groups) >= 2 and all(len(g) >= 5 for g in groups):
                        try:
                            f_val, p_val = stats.f_oneway(*groups)
                            if p_val < 0.05:
                                bar_chart["description"] += f" (khác biệt có ý nghĩa thống kê, p={p_val:.4f})"
                                boxplot_chart["description"] += f" (khác biệt có ý nghĩa thống kê, p={p_val:.4f})"
                                
                                # Thêm biểu đồ phân tích p-value (mới)
                                pvalue_chart = {
                                    "type": ChartType.HEATMAP,
                                    "score": 0.85,
                                    "title": f"Ý nghĩa thống kê cho {num_col} theo {cat_col}",
                                    "description": f"Biểu đồ p-value thể hiện ý nghĩa thống kê cho sự khác biệt {num_col} giữa các nhóm {cat_col} (p={p_val:.4f})",
                                    "category": "statistical",
                                    "subcategory": "significance",
                                    "complexity": "high"
                                }
                                charts.append(pvalue_chart)
                        except:
                            pass
        except:
            pass
        
        return {
            "columns": [cat_col, num_col],
            "column_types": ["categorical", "numeric"],
            "n_categories": n_categories,
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }

    def _recommend_datetime_vs_numeric(self, df: pd.DataFrame, dt_col: str, num_col: str) -> Dict:
        """Khuyến nghị biểu đồ cho 1 cột datetime và 1 cột numeric"""
        charts = []
        
        # Chuẩn bị dữ liệu datetime
        df_copy = df.copy()
        if not is_datetime64_any_dtype(df_copy[dt_col]):
            try:
                df_copy[dt_col] = convert_to_datetime(df_copy[dt_col])
            except:
                return {
                    "columns": [dt_col, num_col],
                    "column_types": ["datetime", "numeric"],
                    "charts": [{
                        "type": ChartType.LINE,
                        "score": 0.5,
                        "title": f"{num_col} theo thời gian",
                        "description": f"Không thể parse giá trị datetime cho {dt_col}"
                    }]
                }
        
        # Line Chart
        line_chart = {
            "type": ChartType.LINE,
            "score": 0.9,
            "title": f"{num_col} theo thời gian",
            "description": f"Biểu đồ đường thể hiện thay đổi {num_col} theo thời gian ({dt_col})",
            "category": "temporal",
            "subcategory": "trends",
            "complexity": "medium"
        }
        charts.append(line_chart)
        
        # Area Chart
        area_chart = {
            "type": ChartType.AREA,
            "score": 0.7,
            "title": f"{num_col} theo thời gian",
            "description": f"Biểu đồ vùng thể hiện thay đổi {num_col} theo thời gian ({dt_col})",
            "category": "temporal",
            "subcategory": "trends",
            "complexity": "medium"
        }
        charts.append(area_chart)
        
        # Scatter plot with time
        scatter_chart = {
            "type": ChartType.SCATTER,
            "score": 0.65,
            "title": f"{num_col} so với {dt_col}",
            "description": f"Biểu đồ scatter plot thể hiện giá trị {num_col} theo thời gian ({dt_col})",
            "category": "temporal",
            "subcategory": "distribution",
            "complexity": "medium"
        }
        charts.append(scatter_chart)
        
        # Tận dụng time_series_visualization nâng cao
        time_series_chart = {
            "type": ChartType.LINE,
            "score": 0.95,
            "title": f"Phân tích chuỗi thời gian {num_col}",
            "description": f"Biểu đồ chuỗi thời gian nâng cao với phát hiện xu hướng và tính thời vụ",
            "category": "temporal",
            "subcategory": "analysis",
            "complexity": "high"
        }
        charts.append(time_series_chart)
        
        # Kiểm tra khoảng thời gian
        try:
            date_range = (df_copy[dt_col].max() - df_copy[dt_col].min()).total_seconds()
            
            # Điều chỉnh score dựa trên mật độ dữ liệu
            if len(df) > 100 and date_range > 86400 * 30:  # > 30 days
                # Dữ liệu dày đặc theo thời gian dài
                area_chart["score"] = 0.8
                area_chart["description"] += " (thích hợp để hiển thị xu hướng trong thời gian dài)"
            
            # Thêm chart kiểu bar để so sánh theo khoảng thời gian
            if date_range > 86400 * 30 * 3:  # > 3 months
                bar_chart = {
                    "type": ChartType.BAR,
                    "score": 0.75,
                    "title": f"{num_col} trung bình theo tháng",
                    "description": f"Biểu đồ cột thể hiện giá trị trung bình {num_col} theo từng tháng",
                    "category": "temporal",
                    "subcategory": "comparison",
                    "complexity": "medium"
                }
                charts.append(bar_chart)
                
            # Kiểm tra xem có cần seasonality/decomposition chart không
            if date_range > 86400 * 365:  # > 1 year
                seasonal_chart = {
                    "type": ChartType.LINE, 
                    "score": 0.85,
                    "title": f"Phân tích thời vụ cho {num_col}",
                    "description": f"Biểu đồ phân tích thành phần thời vụ của {num_col} theo thời gian",
                    "category": "temporal",
                    "subcategory": "seasonality",
                    "complexity": "high"
                }
                charts.append(seasonal_chart)
        except:
            pass
        
        # Kiểm tra xu hướng thời gian
        try:
            # So sánh giá trị đầu/cuối để xem có xu hướng không
            df_sorted = df_copy.sort_values(by=dt_col)
            
            if len(df_sorted) >= 10:  # Need enough data points
                first_quarter = df_sorted[num_col].iloc[:len(df_sorted)//4].mean()
                last_quarter = df_sorted[num_col].iloc[-len(df_sorted)//4:].mean()
                
                if first_quarter != 0:  # Avoid division by zero
                    change_pct = abs(last_quarter - first_quarter) / abs(first_quarter) * 100
                    
                    if change_pct > 20:  # Significant change (>20%)
                        trend_direction = "tăng" if last_quarter > first_quarter else "giảm"
                        line_chart["score"] = 1.0
                        time_series_chart["score"] = 1.0
                        line_chart["description"] += f" (xu hướng {trend_direction} {change_pct:.1f}% trong toàn bộ thời gian)"
                        
                        # Add trend line chart
                        trend_chart = {
                            "type": ChartType.LINE,
                            "score": 0.9,
                            "title": f"Phân tích xu hướng {num_col}",
                            "description": f"Biểu đồ đường với đường xu hướng thể hiện mẫu {trend_direction} của {num_col} theo thời gian",
                            "category": "temporal",
                            "subcategory": "trend",
                            "complexity": "high"
                        }
                        charts.append(trend_chart)
        except:
            pass
        
        return {
            "columns": [dt_col, num_col],
            "column_types": ["datetime", "numeric"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }

    def _recommend_categorical_vs_categorical(self, df: pd.DataFrame, col1: str, col2: str) -> Dict:
        """Khuyến nghị biểu đồ cho 2 cột categorical"""
        charts = []
        
        # Đếm số lượng category
        n_categories1 = df[col1].nunique()
        n_categories2 = df[col2].nunique()
        
        # Heatmap
        heatmap_chart = {
            "type": ChartType.HEATMAP,
            "score": 0.9,
            "title": f"Mối quan hệ giữa {col1} và {col2}",
            "description": f"Biểu đồ nhiệt thể hiện tần suất xuất hiện giữa {col1} và {col2}",
            "category": "relationship",
            "subcategory": "categorical",
            "complexity": "medium"
        }
        charts.append(heatmap_chart)
        
        # Stacked Bar Chart
        stacked_bar_chart = {
            "type": ChartType.BAR,
            "score": 0.8,
            "title": f"Phân phối {col2} theo {col1}",
            "description": f"Biểu đồ cột chồng thể hiện phân phối {col2} cho từng giá trị {col1}",
            "category": "relationship",
            "subcategory": "composition",
            "complexity": "medium"
        }
        charts.append(stacked_bar_chart)
        
        # Grouped Bar Chart
        grouped_bar_chart = {
            "type": ChartType.BAR_GROUPED,
            "score": 0.75,
            "title": f"So sánh giữa {col1} và {col2}",
            "description": f"Biểu đồ cột nhóm so sánh phân phối giữa {col1} và {col2}",
            "category": "relationship",
            "subcategory": "comparison",
            "complexity": "medium"
        }
        charts.append(grouped_bar_chart)
        
        # Sankey Diagram for relationship flow visualization
        if max(n_categories1, n_categories2) <= 10:
            sankey_chart = {
                "type": ChartType.SANKEY,
                "score": 0.7,
                "title": f"Luồng giữa {col1} và {col2}",
                "description": f"Biểu đồ Sankey thể hiện luồng giữa các giá trị của {col1} và {col2}",
                "category": "relationship",
                "subcategory": "flow",
                "complexity": "high"
            }
            charts.append(sankey_chart)
            
            # Chord diagram (mới)
            chord_chart = {
                "type": ChartType.CHORD,
                "score": 0.65,
                "title": f"Mối quan hệ đa chiều giữa {col1} và {col2}",
                "description": f"Biểu đồ Chord thể hiện mối quan hệ hai chiều giữa các giá trị của {col1} và {col2}",
                "category": "relationship",
                "subcategory": "network",
                "complexity": "high"
            }
            charts.append(chord_chart)
        
        # Điều chỉnh score dựa trên số lượng category
        if n_categories1 > 10 or n_categories2 > 10:
            # Với quá nhiều category, heatmap có thể khó đọc
            heatmap_chart["score"] = 0.7
            heatmap_chart["description"] += " (nên nhóm các giá trị để biểu đồ dễ đọc hơn)"
            
            # Grouped bar cũng sẽ rất rối
            grouped_bar_chart["score"] = 0.6
            
            # Stacked bar có thể tốt hơn với nhiều category
            if n_categories1 <= 10 and n_categories2 > 10:
                stacked_bar_chart["score"] = 0.85
        elif max(n_categories1, n_categories2) <= 5:
            # Với ít category, grouped bar chart tốt hơn
            grouped_bar_chart["score"] = 0.85
            
            # Sankey diagram is very informative with few categories
            for chart in charts:
                if chart["type"] == ChartType.SANKEY:
                    chart["score"] = 0.9
        
        # Check for association between variables
        try:
            from scipy.stats import chi2_contingency
            
            # Create contingency table
            contingency = pd.crosstab(df[col1], df[col2])
            
            # Chi-square test
            chi2, p, dof, expected = chi2_contingency(contingency)
            
            # If there's significant association
            if p < 0.05:
                heatmap_chart["score"] += 0.05
                heatmap_chart["description"] += f" (có mối liên hệ có ý nghĩa thống kê, p={p:.4f})"
                
                # Add mosaic plot recommendation for showing associations
                mosaic_chart = {
                    "type": ChartType.MOSAIC,
                    "score": 0.85,
                    "title": f"Mối quan hệ giữa {col1} và {col2}",
                    "description": f"Biểu đồ Mosaic thể hiện mối liên kết có ý nghĩa thống kê giữa {col1} và {col2} (p={p:.4f})",
                    "category": "statistical",
                    "subcategory": "association",
                    "complexity": "high"
                }
                charts.append(mosaic_chart)
        except:
            pass
        
        return {
            "columns": [col1, col2],
            "column_types": ["categorical", "categorical"],
            "n_categories": [n_categories1, n_categories2],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
        
    def _recommend_datetime_vs_datetime(self, df: pd.DataFrame, col1: str, col2: str) -> Dict:
        """
        Khuyến nghị biểu đồ cho 2 cột datetime
        """
        charts = []
        
        # Scatter Plot (timepoints comparison)
        scatter_chart = {
            "type": ChartType.SCATTER,
            "score": 0.85,
            "title": f"So sánh {col1} và {col2}",
            "description": f"Biểu đồ scatter plot so sánh hai cột thời gian {col1} và {col2}",
            "category": "temporal",
            "subcategory": "comparison",
            "complexity": "medium"
        }
        charts.append(scatter_chart)
        
        # Dual Timeline
        timeline_chart = {
            "type": ChartType.LINE,
            "score": 0.8,
            "title": f"Timeline so sánh {col1} và {col2}",
            "description": f"Biểu đồ đường kép thể hiện {col1} và {col2} trên cùng một trục thời gian",
            "category": "temporal",
            "subcategory": "comparison",
            "complexity": "medium"
        }
        charts.append(timeline_chart)
        
        # Time Difference Histogram
        diff_chart = {
            "type": ChartType.HISTOGRAM,
            "score": 0.9,
            "title": f"Khoảng thời gian giữa {col1} và {col2}",
            "description": f"Biểu đồ histogram thể hiện phân phối khoảng thời gian giữa {col1} và {col2}",
            "category": "temporal",
            "subcategory": "intervals",
            "complexity": "medium"
        }
        charts.append(diff_chart)
        
        # Calculate time differences for better recommendations
        try:
            df_copy = df.copy()
            for col in [col1, col2]:
                if not is_datetime64_any_dtype(df_copy[col]):
                    df_copy[col] = convert_to_datetime(df_copy[col])
            
            # Calculate time difference
            df_copy['time_diff'] = (df_copy[col2] - df_copy[col1]).dt.total_seconds() / 3600  # in hours
            
            # If there's a clear pattern in the differences
            mean_diff = df_copy['time_diff'].mean()
            median_diff = df_copy['time_diff'].median()
            diff_std = df_copy['time_diff'].std()
            
            # If time difference is mostly consistent (low variation)
            if abs(diff_std) < abs(mean_diff) * 0.2 and abs(mean_diff - median_diff) < abs(mean_diff) * 0.1:
                diff_chart["score"] = 1.0
                diff_direction = "sau" if mean_diff > 0 else "trước"
                diff_chart["description"] += f" ({col2} luôn {abs(mean_diff):.1f} giờ {diff_direction} so với {col1})"
                
                # Add a specialized chart for consistent time differences
                gantt_chart = {
                    "type": ChartType.GANTT,
                    "score": 0.9,
                    "title": f"Khoảng thời gian giữa {col1} và {col2}",
                    "description": f"Biểu đồ Gantt thể hiện khoảng thời gian nhất quán giữa {col1} và {col2}",
                    "category": "temporal",
                    "subcategory": "intervals",
                    "complexity": "high"
                }
                charts.append(gantt_chart)
            else:
                # If time differences are variable
                diff_chart["description"] += f" (khoảng thời gian thay đổi với trung bình: {mean_diff:.1f} giờ)"
        except:
            pass
        
        return {
            "columns": [col1, col2],
            "column_types": ["datetime", "datetime"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
        
    def _recommend_datetime_vs_categorical(self, df: pd.DataFrame, dt_col: str, cat_col: str) -> Dict:
        """
        Khuyến nghị biểu đồ cho 1 cột datetime và 1 cột categorical
        """
        charts = []
        
        # Event Count Timeline
        timeline_chart = {
            "type": ChartType.LINE,
            "score": 0.85,
            "title": f"Timeline các giá trị {cat_col}",
            "description": f"Biểu đồ đường thể hiện số lượng của các giá trị {cat_col} theo thời gian",
            "category": "temporal",
            "subcategory": "categorical",
            "complexity": "medium"
        }
        charts.append(timeline_chart)
        
        # Stacked Area Chart
        stacked_chart = {
            "type": ChartType.AREA,
            "score": 0.8,
            "title": f"Thành phần {cat_col} theo thời gian",
            "description": f"Biểu đồ vùng chồng thể hiện thành phần các giá trị {cat_col} theo thời gian",
            "category": "temporal",
            "subcategory": "composition",
            "complexity": "medium"
        }
        charts.append(stacked_chart)
        
        # Heatmap Calendar by Category
        heatmap_chart = {
            "type": ChartType.HEATMAP,
            "score": 0.75,
            "title": f"Biểu đồ nhiệt dạng lịch cho {cat_col}",
            "description": f"Biểu đồ nhiệt dạng lịch thể hiện phân phối các giá trị {cat_col} theo thời gian",
            "category": "temporal",
            "subcategory": "distribution",
            "complexity": "high"
        }
        charts.append(heatmap_chart)
        
        # Number of categories affects recommendation
        n_categories = df[cat_col].nunique()
        
        if n_categories > 10:
            # Too many categories for stacked area
            stacked_chart["score"] = 0.6
            stacked_chart["description"] += " (nên nhóm các giá trị để biểu đồ dễ đọc hơn)"
        elif n_categories <= 5:
            # Good number of categories
            stacked_chart["score"] = 0.9
            timeline_chart["score"] = 0.95
        
        # Check for temporal patterns
        try:
            df_copy = df.copy()
            if not is_datetime64_any_dtype(df_copy[dt_col]):
                df_copy[dt_col] = convert_to_datetime(df_copy[dt_col])
            
            # Extract time components
            df_copy['year'] = df_copy[dt_col].dt.year
            df_copy['month'] = df_copy[dt_col].dt.month
            df_copy['day'] = df_copy[dt_col].dt.day
            df_copy['dayofweek'] = df_copy[dt_col].dt.dayofweek
            
            # Check if categories have different day-of-week patterns
            crosstab = pd.crosstab(df_copy['dayofweek'], df_copy[cat_col])
            
            # Calculate chi-square
            from scipy.stats import chi2_contingency
            chi2, p, dof, expected = chi2_contingency(crosstab)
            
            # If categories have different day patterns
            if p < 0.05:
                heatmap_chart["score"] = 0.9
                heatmap_chart["description"] += f" (có sự khác biệt có ý nghĩa thống kê trong mẫu theo ngày trong tuần, p={p:.4f})"
                
                # Add day-of-week pattern chart
                pattern_chart = {
                    "type": ChartType.BAR,
                    "score": 0.85,
                    "title": f"Mẫu ngày trong tuần theo {cat_col}",
                    "description": f"Biểu đồ cột thể hiện sự khác biệt về mẫu ngày trong tuần giữa các giá trị {cat_col}",
                    "category": "temporal",
                    "subcategory": "patterns",
                    "complexity": "high"
                }
                charts.append(pattern_chart)
        except:
            pass
        
        return {
            "columns": [dt_col, cat_col],
            "column_types": ["datetime", "categorical"],
            "n_categories": n_categories,
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }

    def _recommend_binary_vs_numeric(self, df: pd.DataFrame, bin_col: str, num_col: str) -> Dict:
        """
        Khuyến nghị biểu đồ cho 1 cột binary và 1 cột numeric
        """
        charts = []
        
        # Grouped Box Plot
        boxplot_chart = {
            "type": ChartType.BOX,
            "score": 0.95,
            "title": f"So sánh {num_col} theo {bin_col}",
            "description": f"Biểu đồ box plot so sánh phân phối {num_col} giữa hai nhóm {bin_col}",
            "category": "comparison",
            "subcategory": "binary",
            "complexity": "medium"
        }
        charts.append(boxplot_chart)
        
        # Bar Chart
        bar_chart = {
            "type": ChartType.BAR,
            "score": 0.85,
            "title": f"{num_col} trung bình theo {bin_col}",
            "description": f"Biểu đồ cột so sánh giá trị trung bình của {num_col} giữa hai nhóm {bin_col}",
            "category": "comparison",
            "subcategory": "binary",
            "complexity": "low"
        }
        charts.append(bar_chart)
        
        # Violin Plot
        violin_chart = {
            "type": ChartType.VIOLIN,
            "score": 0.8,
            "title": f"Phân phối chi tiết {num_col} theo {bin_col}",
            "description": f"Biểu đồ violin plot thể hiện phân phối chi tiết của {num_col} cho hai giá trị của {bin_col}",
            "category": "comparison",
            "subcategory": "distributions",
            "complexity": "high"
        }
        charts.append(violin_chart)
        
        # Grouped Histogram
        grouped_hist_chart = {
            "type": ChartType.GROUPED_HISTOGRAM,
            "score": 0.9,
            "title": f"So sánh phân phối {num_col} theo {bin_col}",
            "description": f"Biểu đồ histogram nhóm thể hiện sự khác biệt phân phối của {num_col} giữa hai giá trị {bin_col}",
            "category": "comparison",
            "subcategory": "distributions",
            "complexity": "medium"
        }
        charts.append(grouped_hist_chart)
        
        # Analyze statistical difference
        try:
            # Identify the two binary values
            binary_values = df[bin_col].dropna().unique()
            
            if len(binary_values) == 2:
                # Get the two groups
                group1 = df[df[bin_col] == binary_values[0]][num_col].dropna()
                group2 = df[df[bin_col] == binary_values[1]][num_col].dropna()
                
                # Calculate means
                mean1 = group1.mean()
                mean2 = group2.mean()
                
                # Calculate percentage difference
                if mean1 != 0:
                    pct_diff = abs(mean2 - mean1) / abs(mean1) * 100
                    diff_direction = "cao hơn" if mean2 > mean1 else "thấp hơn"
                    
                    # Add the difference to bar chart description
                    bar_chart["description"] += f" ({binary_values[1]} có giá trị trung bình {diff_direction} {pct_diff:.1f}% so với {binary_values[0]})"
                
                # T-test for statistical significance
                from scipy.stats import ttest_ind
                
                if len(group1) >= 8 and len(group2) >= 8:
                    t_stat, p_val = ttest_ind(group1, group2, equal_var=False)
                    
                    if p_val < 0.05:
                        # Add significance to descriptions
                        boxplot_chart["description"] += f" (khác biệt có ý nghĩa thống kê, p={p_val:.4f})"
                        bar_chart["description"] += f" (khác biệt có ý nghĩa thống kê, p={p_val:.4f})"
                        
                        # Add statistical comparison chart
                        stat_chart = {
                            "type": ChartType.BAR,
                            "score": 0.9,
                            "title": f"So sánh thống kê {num_col} theo {bin_col}",
                            "description": f"Biểu đồ cột với thanh lỗi thể hiện sự khác biệt có ý nghĩa thống kê (p={p_val:.4f})",
                            "category": "statistical",
                            "subcategory": "comparison",
                            "complexity": "high"
                        }
                        charts.append(stat_chart)
        except:
            pass
        
        return {
            "columns": [bin_col, num_col],
            "column_types": ["binary", "numeric"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_likert_vs_likert(self, df: pd.DataFrame, likert1: str, likert2: str) -> Dict:
        """
        Khuyến nghị biểu đồ cho mối quan hệ giữa 2 cột Likert scale
        """
        charts = []
        
        # Correlation Heatmap
        heatmap_chart = {
            "type": ChartType.HEATMAP,
            "score": 0.95,
            "title": f"Tương quan giữa {likert1} và {likert2}",
            "description": f"Biểu đồ nhiệt thể hiện tương quan giữa hai thang đánh giá {likert1} và {likert2}",
            "category": "specialized",
            "subcategory": "likert_correlation",
            "complexity": "high"
        }
        charts.append(heatmap_chart)
        
        # Scatter Plot
        scatter_chart = {
            "type": ChartType.SCATTER,
            "score": 0.85,
            "title": f"Mối quan hệ giữa {likert1} và {likert2}",
            "description": f"Biểu đồ scatter plot thể hiện mối quan hệ giữa hai thang đánh giá {likert1} và {likert2}",
            "category": "relationship",
            "subcategory": "likert",
            "complexity": "medium"
        }
        charts.append(scatter_chart)
        
        # Grouped Bar Chart
        grouped_bar_chart = {
            "type": ChartType.BAR_GROUPED,
            "score": 0.8,
            "title": f"So sánh các thang đánh giá {likert1} và {likert2}",
            "description": f"Biểu đồ cột nhóm so sánh phân phối giữa thang đánh giá {likert1} và {likert2}",
            "category": "comparison",
            "subcategory": "likert",
            "complexity": "medium"
        }
        charts.append(grouped_bar_chart)
        
        # Analyze correlation
        try:
            correlation = df[[likert1, likert2]].corr().iloc[0, 1]
            
            if not pd.isna(correlation):
                heatmap_chart["description"] += f" (tương quan: {correlation:.2f})"
                scatter_chart["description"] += f" (tương quan: {correlation:.2f})"
                
                if abs(correlation) > 0.7:
                    corr_type = "dương mạnh" if correlation > 0 else "âm mạnh"
                    heatmap_chart["description"] = f"Biểu đồ nhiệt thể hiện tương quan {corr_type} ({correlation:.2f}) giữa {likert1} và {likert2}"
                    
                    # Add trend line chart for strong correlation
                    trend_chart = {
                        "type": ChartType.LINE,
                        "score": 0.9,
                        "title": f"Xu hướng giữa {likert1} và {likert2}",
                        "description": f"Biểu đồ xu hướng thể hiện mối tương quan {corr_type} ({correlation:.2f}) giữa hai thang đánh giá",
                        "category": "statistical",
                        "subcategory": "correlation",
                        "complexity": "high"
                    }
                    charts.append(trend_chart)
                elif abs(correlation) > 0.3:
                    corr_type = "dương trung bình" if correlation > 0 else "âm trung bình"
                    heatmap_chart["description"] = f"Biểu đồ nhiệt thể hiện tương quan {corr_type} ({correlation:.2f}) giữa {likert1} và {likert2}"
        except:
            pass
            
        return {
            "columns": [likert1, likert2],
            "column_types": ["likert", "likert"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_numeric_datetime_categorical(
        self, df: pd.DataFrame, num_col: str, dt_col: str, cat_col: str
    ) -> Dict:
        """
        Khuyến nghị biểu đồ cho 1 cột numeric, 1 cột datetime và 1 cột categorical (3 biến)
        """
        charts = []
        
        # Multi-line Chart
        multiline_chart = {
            "type": ChartType.LINE,
            "score": 0.9,
            "title": f"Xu hướng {num_col} theo {cat_col} theo thời gian",
            "description": f"Biểu đồ đường nhiều đường thể hiện xu hướng {num_col} cho các giá trị {cat_col} theo thời gian",
            "category": "temporal",
            "subcategory": "multi_series",
            "complexity": "high"
        }
        charts.append(multiline_chart)
        
        # 3D Scatter (if supported)
        scatter3d_chart = {
            "type": ChartType.SCATTER_3D,
            "score": 0.8,
            "title": f"Quan hệ 3D giữa {num_col}, {dt_col}, và {cat_col}",
            "description": f"Biểu đồ scatter 3D thể hiện mối quan hệ giữa {num_col}, {dt_col}, và {cat_col}",
            "category": "relationship",
            "subcategory": "3d",
            "complexity": "high"
        }
        charts.append(scatter3d_chart)
        
        # Scatter with color
        scatter_color_chart = {
            "type": ChartType.SCATTER,
            "score": 0.85,
            "title": f"{num_col} so với {dt_col} theo {cat_col}",
            "description": f"Biểu đồ scatter plot thể hiện {num_col} theo {dt_col} với màu phân loại theo {cat_col}",
            "category": "relationship",
            "subcategory": "colored",
            "complexity": "medium"
        }
        charts.append(scatter_color_chart)
        
        # Faceted Charts
        facet_chart = {
            "type": ChartType.FACET,
            "score": 0.75,
            "title": f"Phân tích {num_col} theo thời gian theo {cat_col}",
            "description": f"Biểu đồ facet nhiều biểu đồ thể hiện {num_col} theo thời gian, phân tách theo các giá trị {cat_col}",
            "category": "temporal",
            "subcategory": "facet",
            "complexity": "high"
        }
        charts.append(facet_chart)
        
        # Number of categories affects recommendations
        n_categories = df[cat_col].nunique()
        
        if n_categories > 10:
            # Too many categories
            multiline_chart["score"] = 0.7
            multiline_chart["description"] += " (nên giới hạn các giá trị {cat_col} để đảm bảo độ rõ ràng)"
            
            # Facets might work better with many categories
            facet_chart["score"] = 0.85
        elif n_categories <= 5:
            # Perfect for multiline
            multiline_chart["score"] = 1.0
            
            # Add animated chart recommendation for few categories
            animated_chart = {
                "type": ChartType.ANIMATION,
                "score": 0.9,
                "title": f"Diễn biến {num_col} theo {cat_col}",
                "description": f"Biểu đồ động thể hiện diễn biến {num_col} theo thời gian cho các giá trị {cat_col} khác nhau",
                "category": "temporal",
                "subcategory": "animation",
                "complexity": "high"
            }
            charts.append(animated_chart)
        
        # Check for diverging patterns between categories
        try:
            df_copy = df.copy()
            if not is_datetime64_any_dtype(df_copy[dt_col]):
                df_copy[dt_col] = convert_to_datetime(df_copy[dt_col])
            
            # Sort by date
            df_copy = df_copy.sort_values(by=dt_col)
            
            # Calculate first and last quarter averages for each category
            results = []
            for cat in df_copy[cat_col].unique():
                subset = df_copy[df_copy[cat_col] == cat]
                if len(subset) >= 8:  # Need enough data points
                    first_quarter = subset[num_col].iloc[:len(subset)//4].mean()
                    last_quarter = subset[num_col].iloc[-len(subset)//4:].mean()
                    
                    if first_quarter != 0:  # Avoid division by zero
                        change_pct = (last_quarter - first_quarter) / abs(first_quarter) * 100
                        results.append((cat, change_pct))
            
            # If we have results for multiple categories
            if len(results) >= 2:
                # Check if there are diverging trends
                trends = [r[1] for r in results]
                if max(trends) > 20 and min(trends) < -20:  # Some up, some down
                    multiline_chart["score"] = 1.0
                    multiline_chart["description"] += " (thể hiện xu hướng phân kỳ giữa các giá trị {cat_col})"
                    
                    # Add a specialized chart for diverging trends
                    diverging_chart = {
                        "type": ChartType.DIVERGING,
                        "score": 0.95,
                        "title": f"Xu hướng phân kỳ trong {num_col} theo {cat_col}",
                        "description": f"Biểu đồ đặc biệt nhấn mạnh xu hướng phân kỳ giữa các giá trị {cat_col} theo thời gian",
                        "category": "specialized",
                        "subcategory": "diverging",
                        "complexity": "high"
                    }
                    charts.append(diverging_chart)
        except:
            pass
        
        return {
            "columns": [num_col, dt_col, cat_col],
            "column_types": ["numeric", "datetime", "categorical"],
            "n_categories": n_categories,
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_two_numeric_one_categorical(
        self, df: pd.DataFrame, num_col1: str, num_col2: str, cat_col: str
    ) -> Dict:
        """
        Khuyến nghị biểu đồ cho 2 cột numeric và 1 cột categorical
        """
        charts = []
        
        # Scatter Plot with Color
        scatter_chart = {
            "type": ChartType.SCATTER,
            "score": 0.95,
            "title": f"{num_col1} vs {num_col2} theo {cat_col}",
            "description": f"Biểu đồ scatter plot thể hiện mối quan hệ giữa {num_col1} và {num_col2} với màu phân loại theo {cat_col}",
            "category": "relationship",
            "subcategory": "colored",
            "complexity": "medium"
        }
        charts.append(scatter_chart)
        
        # Bubble Chart
        bubble_chart = {
            "type": ChartType.BUBBLE,
            "score": 0.85,
            "title": f"Biểu đồ bong bóng: {num_col1}, {num_col2}, và {cat_col}",
            "description": f"Biểu đồ bong bóng thể hiện {num_col1} (x), {num_col2} (y), và {cat_col} (màu)",
            "category": "relationship",
            "subcategory": "bubble",
            "complexity": "high"
        }
        charts.append(bubble_chart)
        
        # Faceted Scatter
        facet_scatter_chart = {
            "type": ChartType.FACET,
            "score": 0.75,
            "title": f"Scatter Plots {num_col1} vs {num_col2} theo {cat_col}",
            "description": f"Biểu đồ facet nhiều scatter plots thể hiện mối quan hệ giữa {num_col1} và {num_col2} phân tách theo các giá trị {cat_col}",
            "category": "relationship",
            "subcategory": "facet",
            "complexity": "high"
        }
        charts.append(facet_scatter_chart)
        
        # Number of categories affects recommendations
        n_categories = df[cat_col].nunique()
        
        if n_categories > 10:
            # Too many categories
            scatter_chart["description"] += " (nên giới hạn các giá trị {cat_col} để đảm bảo độ rõ ràng)"
            bubble_chart["score"] = 0.7
            
            # Facets might work better with many categories
            facet_scatter_chart["score"] = 0.9
        elif n_categories <= 5:
            # Perfect for colored scatter
            scatter_chart["score"] = 1.0
        
        # Check for correlation
        try:
            correlation = df[[num_col1, num_col2]].corr().iloc[0, 1]
            
            if not pd.isna(correlation):
                scatter_chart["description"] += f" (tương quan tổng thể: {correlation:.2f})"
                
                # Check if correlations differ by category
                corr_by_cat = {}
                for cat in df[cat_col].unique():
                    subset = df[df[cat_col] == cat]
                    if len(subset) >= 10:
                        cat_corr = subset[[num_col1, num_col2]].corr().iloc[0, 1]
                        if not pd.isna(cat_corr):
                            corr_by_cat[cat] = cat_corr
                
                if len(corr_by_cat) >= 2:
                    min_corr = min(corr_by_cat.values())
                    max_corr = max(corr_by_cat.values())
                    
                    if abs(max_corr - min_corr) > 0.3:
                        scatter_chart["description"] += f" (tương quan khác nhau giữa các nhóm, từ {min_corr:.2f} đến {max_corr:.2f})"
                        facet_scatter_chart["score"] += 0.1
                        
                        # Add specialized comparison chart
                        comparison_chart = {
                            "type": ChartType.BAR,
                            "score": 0.8,
                            "title": f"So sánh tương quan theo {cat_col}",
                            "description": f"Biểu đồ cột so sánh hệ số tương quan giữa {num_col1} và {num_col2} cho từng giá trị {cat_col}",
                            "category": "statistical",
                            "subcategory": "correlation_comparison",
                            "complexity": "high"
                        }
                        charts.append(comparison_chart)
        except:
            pass
        
        return {
            "columns": [num_col1, num_col2, cat_col],
            "column_types": ["numeric", "numeric", "categorical"],
            "n_categories": n_categories,
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_three_numeric(
        self, df: pd.DataFrame, num_col1: str, num_col2: str, num_col3: str
    ) -> Dict:
        """
        Khuyến nghị biểu đồ cho 3 cột numeric
        """
        charts = []
        
        # 3D Scatter Plot
        scatter3d_chart = {
            "type": ChartType.SCATTER_3D,
            "score": 0.9,
            "title": f"Biểu đồ 3D: {num_col1}, {num_col2}, và {num_col3}",
            "description": f"Biểu đồ scatter 3D thể hiện mối quan hệ giữa {num_col1}, {num_col2}, và {num_col3}",
            "category": "relationship",
            "subcategory": "3d",
            "complexity": "high"
        }
        charts.append(scatter3d_chart)
        
        # Bubble Chart
        bubble_chart = {
            "type": ChartType.BUBBLE,
            "score": 0.85,
            "title": f"Biểu đồ bong bóng: {num_col1}, {num_col2}, và {num_col3}",
            "description": f"Biểu đồ bong bóng thể hiện {num_col1} (x), {num_col2} (y), và {num_col3} (kích thước)",
            "category": "relationship",
            "subcategory": "bubble",
            "complexity": "high"
        }
        charts.append(bubble_chart)
        
        # Matrix Scatter Plot
        matrix_chart = {
            "type": ChartType.MATRIX,
            "score": 0.8,
            "title": f"Ma trận Scatter Plots",
            "description": f"Ma trận scatter plots thể hiện mối quan hệ giữa {num_col1}, {num_col2}, và {num_col3}",
            "category": "relationship",
            "subcategory": "matrix",
            "complexity": "medium"
        }
        charts.append(matrix_chart)
        
        # Correlation Heatmap
        heatmap_chart = {
            "type": ChartType.HEATMAP,
            "score": 0.75,
            "title": f"Tương quan giữa các biến numeric",
            "description": f"Biểu đồ nhiệt thể hiện tương quan giữa {num_col1}, {num_col2}, và {num_col3}",
            "category": "relationship",
            "subcategory": "correlation",
            "complexity": "medium"
        }
        charts.append(heatmap_chart)
        
        # Check correlations
        try:
            corr_matrix = df[[num_col1, num_col2, num_col3]].corr()
            
            # Check if there are strong correlations
            has_strong_corr = False
            for i in range(3):
                for j in range(i+1, 3):
                    if abs(corr_matrix.iloc[i, j]) > 0.7:
                        has_strong_corr = True
                        break
            
            if has_strong_corr:
                matrix_chart["score"] = 0.9
                heatmap_chart["score"] = 0.85
                heatmap_chart["description"] += " (phát hiện tương quan mạnh giữa các biến)"
                
                # Add regression plot
                regression_chart = {
                    "type": ChartType.REGRESSION,
                    "score": 0.85,
                    "title": f"Phân tích hồi quy cho biến numeric",
                    "description": f"Biểu đồ hồi quy thể hiện mối quan hệ tương quan giữa các biến numeric",
                    "category": "statistical",
                    "subcategory": "regression",
                    "complexity": "high"
                }
                charts.append(regression_chart)
        except:
            pass
        
        # PCA recommendation for 3 numeric variables
        pca_chart = {
            "type": ChartType.SCATTER,
            "score": 0.85,
            "title": f"PCA cho {num_col1}, {num_col2}, và {num_col3}",
            "description": f"Biểu đồ scatter PCA chiếu dữ liệu 3 chiều xuống 2 chiều, giữ lại thông tin quan trọng nhất",
            "category": "statistical",
            "subcategory": "dimensionality_reduction",
            "complexity": "high"
        }
        charts.append(pca_chart)
        
        return {
            "columns": [num_col1, num_col2, num_col3],
            "column_types": ["numeric", "numeric", "numeric"],
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_correlation_analysis(self, df: pd.DataFrame, numeric_cols: List[str]) -> Dict:
        """
        Khuyến nghị biểu đồ phân tích tương quan cho nhiều cột numeric
        
        Args:
            df: DataFrame chứa dữ liệu
            numeric_cols: Danh sách các cột numeric
            
        Returns:
            Dict: Khuyến nghị biểu đồ
        """
        charts = []
        
        # Correlation Heatmap
        heatmap_chart = {
            "type": ChartType.HEATMAP,
            "score": 0.95,
            "title": "Ma trận tương quan",
            "description": "Biểu đồ nhiệt thể hiện hệ số tương quan Pearson giữa các biến numeric",
            "category": "statistical",
            "subcategory": "correlation",
            "complexity": "medium"
        }
        charts.append(heatmap_chart)
        
        # Matrix Scatter Plot
        matrix_chart = {
            "type": ChartType.MATRIX,
            "score": 0.85,
            "title": "Ma trận Scatter Plots",
            "description": "Ma trận scatter plots thể hiện mối quan hệ giữa tất cả các biến numeric",
            "category": "relationship",
            "subcategory": "matrix",
            "complexity": "high"
        }
        charts.append(matrix_chart)
        
        # Network Graph for correlations
        network_chart = {
            "type": ChartType.NETWORK,
            "score": 0.8,
            "title": "Mạng lưới tương quan",
            "description": "Biểu đồ mạng lưới thể hiện tương quan giữa các biến numeric, với độ dày đường nối thể hiện mức độ tương quan",
            "category": "statistical",
            "subcategory": "correlation_network",
            "complexity": "high"
        }
        charts.append(network_chart)
        
        # PCA for dimensionality reduction
        pca_chart = {
            "type": ChartType.SCATTER,
            "score": 0.75,
            "title": "Biểu đồ PCA",
            "description": "Biểu đồ PCA giảm chiều dữ liệu, thể hiện các thành phần chính của biến thiên dữ liệu",
            "category": "statistical",
            "subcategory": "dimensionality_reduction",
            "complexity": "high"
        }
        charts.append(pca_chart)
        
        # Analyze correlations
        try:
            corr_matrix = df[numeric_cols].corr()
            
            # Count strong correlations
            strong_corr_count = 0
            multicollinearity_groups = []
            
            # Use graph algorithm to find groups of correlated variables
            strong_pairs = []
            
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    if i < j:  # Upper triangle only
                        corr = abs(corr_matrix.loc[col1, col2])
                        if corr > 0.7:
                            strong_corr_count += 1
                            strong_pairs.append((col1, col2, corr))
            
            if strong_corr_count > 0:
                heatmap_chart["description"] += f" (phát hiện {strong_corr_count} cặp biến có tương quan mạnh)"
                network_chart["score"] = 0.9
                
                if strong_corr_count > 3:
                    # Check for multicollinearity
                    from collections import defaultdict
                    graph = defaultdict(list)
                    
                    for col1, col2, _ in strong_pairs:
                        graph[col1].append(col2)
                        graph[col2].append(col1)
                    
                    # Find connected components (groups of correlated variables)
                    visited = set()
                    
                    def dfs(node, component):
                        visited.add(node)
                        component.append(node)
                        for neighbor in graph[node]:
                            if neighbor not in visited:
                                dfs(neighbor, component)
                    
                    for node in graph:
                        if node not in visited:
                            component = []
                            dfs(node, component)
                            if len(component) > 2:  # At least 3 variables
                                multicollinearity_groups.append(component)
                    
                    if multicollinearity_groups:
                        heatmap_chart["description"] += f" và phát hiện {len(multicollinearity_groups)} nhóm multicollinearity"
                        
                        # Add PCA recommendation with higher score
                        pca_chart["score"] = 0.9
                        pca_chart["description"] += " (khuyến nghị khi có multicollinearity)"
                        
                        # Factor Analysis recommendation
                        factor_chart = {
                            "type": ChartType.HEATMAP,
                            "score": 0.85,
                            "title": "Phân tích nhân tố",
                            "description": "Biểu đồ nhiệt thể hiện kết quả phân tích nhân tố cho các biến tương quan cao",
                            "category": "statistical",
                            "subcategory": "factor_analysis",
                            "complexity": "high"
                        }
                        charts.append(factor_chart)
        except:
            pass
            
        return {
            "columns": numeric_cols,
            "column_types": ["numeric"] * len(numeric_cols),
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }
    
    def _recommend_time_series_analysis(
        self, df: pd.DataFrame, dt_col: str, numeric_cols: List[str]
    ) -> Dict:
        """
        Khuyến nghị biểu đồ phân tích chuỗi thời gian cho 1 cột datetime và nhiều cột numeric
        
        Args:
            df: DataFrame chứa dữ liệu
            dt_col: Cột datetime
            numeric_cols: Danh sách các cột numeric
            
        Returns:
            Dict: Khuyến nghị biểu đồ
        """
        charts = []
        
        # Multi-line Chart
        multiline_chart = {
            "type": ChartType.LINE,
            "score": 0.95,
            "title": "Phân tích chuỗi thời gian đa biến",
            "description": f"Biểu đồ đường nhiều đường thể hiện xu hướng của nhiều biến theo thời gian ({dt_col})",
            "category": "temporal",
            "subcategory": "multi_series",
            "complexity": "medium"
        }
        charts.append(multiline_chart)
        
        # Stacked Area Chart
        area_chart = {
            "type": ChartType.AREA,
            "score": 0.85,
            "title": "Thành phần theo thời gian",
            "description": f"Biểu đồ vùng chồng thể hiện thành phần các biến numeric theo thời gian ({dt_col})",
            "category": "temporal",
            "subcategory": "composition",
            "complexity": "medium"
        }
        charts.append(area_chart)
        
        # Heatmap Calendar for multiple metrics
        calendar_chart = {
            "type": ChartType.HEATMAP,
            "score": 0.8,
            "title": "Biểu đồ nhiệt chuỗi thời gian",
            "description": f"Biểu đồ nhiệt dạng lịch thể hiện biến đổi các giá trị numeric theo thời gian ({dt_col})",
            "category": "temporal",
            "subcategory": "calendar",
            "complexity": "high"
        }
        charts.append(calendar_chart)
        
        # Advanced time series analysis
        decomposition_chart = {
            "type": ChartType.LINE,
            "score": 0.9,
            "title": "Phân rã chuỗi thời gian",
            "description": "Biểu đồ phân rã chuỗi thời gian thành xu hướng, tính thời vụ và thành phần ngẫu nhiên",
            "category": "temporal",
            "subcategory": "decomposition",
            "complexity": "high"
        }
        charts.append(decomposition_chart)
        
        # Analyze time range
        try:
            df_copy = df.copy()
            if not is_datetime64_any_dtype(df_copy[dt_col]):
                df_copy[dt_col] = convert_to_datetime(df_copy[dt_col])
            
            # Sort by date
            df_copy = df_copy.sort_values(by=dt_col)
            
            date_range = (df_copy[dt_col].max() - df_copy[dt_col].min()).total_seconds()
            
            if date_range > 86400 * 365:  # > 1 year
                decomposition_chart["score"] = 0.95
                decomposition_chart["description"] += " (khuyến nghị cho dữ liệu trên 1 năm để phát hiện mẫu theo mùa)"
                
                # Seasonal subseries plot
                seasonal_chart = {
                    "type": ChartType.LINE,
                    "score": 0.9,
                    "title": "Phân tích thời vụ",
                    "description": "Biểu đồ subseries theo mùa thể hiện mẫu lặp lại theo mùa trong chuỗi thời gian",
                    "category": "temporal",
                    "subcategory": "seasonality",
                    "complexity": "high"
                }
                charts.append(seasonal_chart)
                
                # Year-over-year comparison
                yoy_chart = {
                    "type": ChartType.LINE,
                    "score": 0.85,
                    "title": "So sánh năm-qua-năm",
                    "description": "Biểu đồ so sánh các giá trị năm hiện tại với năm trước, phát hiện thay đổi theo mùa",
                    "category": "temporal",
                    "subcategory": "comparison",
                    "complexity": "high"
                }
                charts.append(yoy_chart)
            elif date_range > 86400 * 30:  # > 30 days
                # Month-to-date analysis
                mtd_chart = {
                    "type": ChartType.BAR,
                    "score": 0.85,
                    "title": "Phân tích tháng-hiện-tại",
                    "description": "Biểu đồ so sánh giá trị tháng hiện tại với tháng trước, đánh giá hiệu suất",
                    "category": "temporal",
                    "subcategory": "comparison",
                    "complexity": "medium"
                }
                charts.append(mtd_chart)
        except:
            pass
        
        # Check for seasonal patterns in first variable
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose
            
            if len(df) >= 10 and date_range > 86400 * 60:  # At least 60 days
                # Convert to datetime index
                df_copy = df.copy()
                df_copy[dt_col] = convert_to_datetime(df_copy[dt_col])
                
                # Prepare time series for first numeric column
                ts_df = df_copy.sort_values(by=dt_col)
                ts_df = ts_df.set_index(dt_col)
                
                # Determine frequency
                if date_range < 86400 * 180:  # Less than 6 months
                    freq = 'D'  # Daily
                    period = 7  # Week
                elif date_range < 86400 * 900:  # Less than ~2.5 years
                    freq = 'W'  # Weekly
                    period = 4  # ~Month
                else:
                    freq = 'MS'  # Month start
                    period = 12  # Year
                
                # Resample and fill missing values
                ts_data = ts_df[numeric_cols[0]].resample(freq).mean()
                ts_data = ts_data.interpolate(method='linear')
                
                if len(ts_data) >= 2 * period:
                    # Decompose time series
                    result = seasonal_decompose(ts_data, model='additive', period=period, extrapolate_trend='freq')
                    
                    # Check if there's seasonality
                    seasonal_strength = result.seasonal.std() / result.resid.std()
                    
                    if seasonal_strength > 0.5:
                        decomposition_chart["score"] = 1.0
                        decomposition_chart["description"] += f" (phát hiện mẫu thời vụ mạnh trong {numeric_cols[0]})"
                        
                        # Seasonal chart
                        seasonal_chart = {
                            "type": ChartType.LINE,
                            "score": 0.95,
                            "title": f"Phân tích thời vụ cho {numeric_cols[0]}",
                            "description": f"Biểu đồ phân tích thành phần thời vụ của {numeric_cols[0]} theo thời gian",
                            "category": "temporal",
                            "subcategory": "seasonality",
                            "complexity": "high"
                        }
                        charts.append(seasonal_chart)
        except:
            pass
        
        return {
            "columns": [dt_col] + numeric_cols,
            "column_types": ["datetime"] + ["numeric"] * len(numeric_cols),
            "charts": sorted(charts, key=lambda x: x["score"], reverse=True)
        }