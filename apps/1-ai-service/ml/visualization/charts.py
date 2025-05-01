"""
Module tạo biểu đồ nâng cao tích hợp từ EnhancedDataPipeline và ChartGenerator.
Tập trung vào việc tạo các biểu đồ phổ biến với khả năng phát hiện pattern nâng cao.
"""

import logging
import time
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from uuid import uuid4 as v4
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype
from statsmodels.tsa.seasonal import seasonal_decompose

from app.models.analysis import ChartType, VisualizationData
from ml.utils.datetime_utils import convert_to_datetime
from ml.data.data_processor import DataProcessor

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generator cho các biểu đồ trực quan hóa dữ liệu nâng cao"""

    def __init__(self, config_path: Optional[Union[str, Dict]] = None):
        """Khởi tạo chart generator"""
        self.config = config_path if isinstance(config_path, dict) else {}
        self.visualization_cache = {}
        self.data_processor = DataProcessor()
        logger.info("Enhanced ChartGenerator initialized")

    def generate_automatic_charts(
        self, 
        df: pd.DataFrame, 
        file_id: Optional[str] = None,
        chart_types: Optional[List[str]] = None,
        sample_threshold: int = 50000
    ) -> List[VisualizationData]:
        """
        Tạo biểu đồ tự động dựa trên phân tích dữ liệu nâng cao
        
        Args:
            df: DataFrame cần tạo biểu đồ
            chart_types: Loại biểu đồ cần tạo (nếu None, tự động chọn)
            sample_threshold: Ngưỡng số lượng hàng để sampling
            
        Returns:
            List[VisualizationData]: Danh sách các biểu đồ đã tạo
        """
        start_time = time.time()
        visualizations = []
        
        # Sampling nếu cần
        if len(df) > sample_threshold:
            logger.info(f"DataFrame size ({len(df)} rows) exceeds threshold. Sampling for visualization.")
            df_viz = df.sample(sample_threshold, random_state=42)
        else:
            df_viz = df

        # Tạo hash key cho cache
        df_hash = self._generate_df_hash(df_viz)
        
        # Kiểm tra cache
        if df_hash in self.visualization_cache:
            logger.info(f"Using cached visualizations for DataFrame hash: {df_hash}")
            cached_viz = self.visualization_cache[df_hash]
            
            if chart_types:
                cached_viz = [viz for viz in cached_viz if viz.type in chart_types]
                
            return cached_viz

        try:
            column_types = self._detect_column_types(df_viz)
            numeric_cols = column_types["numeric"]
            datetime_cols = column_types["datetime"]
            categorical_cols = column_types["categorical"]
            binary_cols = column_types.get("binary", [])
            gender_cols = column_types.get("gender", [])
            likert_cols = column_types.get("likert", [])
            range_cols = column_types.get("range", [])
            text_cols = column_types.get("text", [])

            # Xác định số lượng biểu đồ tối đa để tạo
            max_charts = self.config.get("visualization", {}).get("max_charts_per_insight", 8)
            
            # 1. Tạo biểu đồ phân phối cho cột numeric
            if numeric_cols and (not chart_types or ChartType.HISTOGRAM in chart_types):
                # Chọn top numeric columns dựa trên variance
                sorted_by_variance = df_viz[numeric_cols].var().sort_values(ascending=False)
                top_numeric = sorted_by_variance.index[:min(2, len(sorted_by_variance))].tolist()
                
                for col in top_numeric:
                    hist_chart = self._create_distribution_chart(df_viz, col, file_id, f"Distribution chart of {col.replace('_', ' ')}")
                    if hist_chart:
                        visualizations.append(hist_chart)
            
            # 2. Tạo biểu đồ bánh cho cột categorical/gender
            if (not chart_types or ChartType.PIE in chart_types):
                # Ưu tiên cột gender nếu có
                if gender_cols:
                    pie_chart = self._create_pie_chart(df_viz, gender_cols[0], file_id, f"Gender distribution: {gender_cols[0].replace('_', ' ')}")
                    if pie_chart:
                        visualizations.append(pie_chart)
                # Nếu không có gender, tìm cột categorical phù hợp (ít giá trị unique)
                elif categorical_cols:
                    suitable_cols = [col for col in categorical_cols if df_viz[col].nunique() <= 8]
                    if suitable_cols:
                        pie_chart = self._create_pie_chart(df_viz, suitable_cols[0], file_id, f"Pie chart of {suitable_cols[0].replace('_', ' ')}")
                        if pie_chart:
                            visualizations.append(pie_chart)
            
            # 3. Tạo biểu đồ cột cho cột categorical
            if categorical_cols and (not chart_types or ChartType.BAR in chart_types):
                # Chọn cột categorical có nhiều giá trị unique nhất
                cat_col_nunique = [(col, df_viz[col].nunique()) for col in categorical_cols 
                                 if df_viz[col].nunique() <= 15]  # Giới hạn số lượng categories
                if cat_col_nunique:
                    # Sắp xếp theo số lượng unique values giảm dần
                    cat_col_nunique.sort(key=lambda x: x[1], reverse=True)
                    cat_col = cat_col_nunique[0][0]
                    
                    bar_chart = self._create_categorical_chart(df_viz, cat_col, file_id, f"Categorical chart of {cat_col.replace('_', ' ')}")
                    if bar_chart:
                        visualizations.append(bar_chart)
            
            # 4. Tạo biểu đồ time series nếu có cột datetime
            if datetime_cols and numeric_cols and (not chart_types or ChartType.LINE in chart_types):
                # Thử từng cột datetime với cột numeric có variance cao nhất
                for dt_col in datetime_cols[:1]:  # Chỉ dùng cột datetime đầu tiên
                    if numeric_cols:
                        time_chart = self.create_time_series_visualization(df_viz, dt_col, numeric_cols[0], file_id, f"Time Series visualization of {dt_col.replace('_', ' ')}")
                        if time_chart:
                            visualizations.append(time_chart)
            
            # 5. Tạo biểu đồ tương quan nếu có nhiều cột numeric
            if len(numeric_cols) >= 2 and (not chart_types or ChartType.SCATTER in chart_types):
                # Tìm cặp cột có tương quan mạnh nhất
                corr_matrix = df_viz[numeric_cols].corr().abs()
                
                # Tìm cặp cột với tương quan cao nhất (loại trừ tương quan với chính nó)
                strongest_pair = None
                strongest_corr = 0
                
                for i, col1 in enumerate(corr_matrix.columns):
                    for j, col2 in enumerate(corr_matrix.columns):
                        if i < j:  # Chỉ xét nửa trên của ma trận
                            corr = corr_matrix.loc[col1, col2]
                            if corr > strongest_corr:
                                strongest_corr = corr
                                strongest_pair = (col1, col2)
                
                if strongest_pair and strongest_corr > 0.5:
                    scatter_chart = self._create_scatter_chart(df_viz, strongest_pair[0], strongest_pair[1], file_id, f"Scatter chart of {strongest_pair[0].replace('_', ' ')} and {strongest_pair[1].replace('_', ' ')}")
                else:
                    # Nếu không tìm thấy tương quan mạnh, dùng 2 cột đầu tiên
                    scatter_chart = self._create_scatter_chart(df_viz, numeric_cols[0], numeric_cols[1], file_id, f"Scatter chart of {numeric_cols[0].replace('_', ' ')} and {numeric_cols[1].replace('_', ' ')}")
                
                if scatter_chart:
                    visualizations.append(scatter_chart)
            
            # 6. Tạo biểu đồ nhóm nếu có cột categorical và numeric
            if categorical_cols and numeric_cols and (not chart_types or ChartType.BAR in chart_types):
                # Chọn cột categorical có ít nhất 2 categories và không quá nhiều
                suitable_cat_cols = [col for col in categorical_cols 
                                   if 2 <= df_viz[col].nunique() <= 10]
                
                if suitable_cat_cols:
                    group_chart = self._create_group_chart(df_viz, suitable_cat_cols[0], numeric_cols[0], file_id,  f"Group chart of {suitable_cat_cols[0].replace('_', ' ')} and {numeric_cols[0].replace('_', ' ')}")
                    if group_chart:
                        visualizations.append(group_chart)
            
            # 7. Tạo biểu đồ heatmap correlation nếu có nhiều cột numeric
            if len(numeric_cols) >= 3 and (not chart_types or ChartType.HEATMAP in chart_types):
                corr_chart = self._create_correlation_chart(df_viz, numeric_cols[:5], file_id, "Correlation chart of numeric cols (5 cols)")  # Giới hạn 5 cột
                if corr_chart:
                    visualizations.append(corr_chart)
            
            # 8. Tạo biểu đồ box plot nếu có cột numeric
            if numeric_cols and (not chart_types or ChartType.BOX in chart_types):
                # Tìm cột có outliers
                has_outliers = False
                outlier_col = None
                
                for col in numeric_cols[:3]:  # Check top 3 numeric columns
                    Q1 = df_viz[col].quantile(0.25)
                    Q3 = df_viz[col].quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = ((df_viz[col] < Q1 - 1.5 * IQR) | (df_viz[col] > Q3 + 1.5 * IQR)).sum()
                    if outliers > 0:
                        has_outliers = True
                        outlier_col = col
                        break
                
                if has_outliers and outlier_col:
                    box_chart = self._create_box_plot(df_viz, outlier_col, file_id, f"Box plot of {outlier_col.replace('_', ' ')}")
                    if box_chart:
                        visualizations.append(box_chart)
            
            # 9. Tạo biểu đồ phân bố theo nhóm (combination of categorical and numeric)
            if categorical_cols and numeric_cols and (not chart_types or ChartType.HISTOGRAM in chart_types):
                suitable_cat = [col for col in categorical_cols if df_viz[col].nunique() == 2]
                if suitable_cat:  # Binary categorical column
                    binary_dist_chart = self._create_grouped_distribution(df_viz, suitable_cat[0], numeric_cols[0], file_id, f"Grouped distribution of {suitable_cat[0].replace('_', ' ')} and {numeric_cols[0].replace('_', ' ')}")
                    if binary_dist_chart:
                        visualizations.append(binary_dist_chart)
            
            # 10. Tạo biểu đồ đặc biệt cho Likert scales (horizontal bar)
            if likert_cols and (not chart_types or ChartType.BAR in chart_types):
                for col in likert_cols[:min(2, len(likert_cols))]:
                    likert_chart = self._create_likert_chart(df_viz, col, file_id, f"Rating scale: {col.replace('_', ' ')}")
                    if likert_chart:
                        visualizations.append(likert_chart)
            
            # 11. Tạo biểu đồ đặc biệt cho binary columns
            if binary_cols and (not chart_types or ChartType.BAR in chart_types):
                for col in binary_cols[:min(2, len(binary_cols))]:
                    binary_chart = self._create_binary_chart(df_viz, col, file_id, f"Binary distribution: {col.replace('_', ' ')}")
                    if binary_chart:
                        visualizations.append(binary_chart)
            
            # 12. Tạo biểu đồ độ dài cho text columns
            if text_cols and (not chart_types or ChartType.HISTOGRAM in chart_types):
                for col in text_cols[:min(1, len(text_cols))]:
                    try:
                        # Tạo cột độ dài
                        df_viz[f"{col}_length"] = df_viz[col].astype(str).str.len()
                        
                        # Tạo biểu đồ histogram cho độ dài
                        length_chart = self._create_distribution_chart(df_viz, f"{col}_length", file_id, f"Text length distribution: {col.replace('_', ' ')}")
                        if length_chart:
                            length_chart.type = ChartType.TEXT
                            visualizations.append(length_chart)
                        
                        # Xóa cột tạm
                        df_viz.drop(columns=[f"{col}_length"], inplace=True)
                    except Exception as e:
                        logger.warning(f"Error creating text length chart for {col}: {str(e)}")
            
            # 13. Tạo biểu đồ phân tích cho range
            if range_cols and (not chart_types or ChartType.BAR in chart_types):
                for col in range_cols[:min(1, len(range_cols))]:
                    try:
                        range_chart = self._create_categorical_chart(df_viz, col, file_id, f"Range distribution: {col.replace('_', ' ')}")
                        if range_chart:
                            range_chart.type = ChartType.RANGE
                            visualizations.append(range_chart)
                    except Exception as e:
                        logger.warning(f"Error creating range chart for {col}: {str(e)}")
            
            # 14. Tạo biểu đồ phân bố kết hợp cho likert scales
            if likert_cols and len(likert_cols) >= 2 and (not chart_types or ChartType.HEATMAP in chart_types):
                try:
                    # Tạo biểu đồ heatmap cho tương quan giữa các cột likert
                    likert_corr_chart = self._create_correlation_chart(df_viz, likert_cols[:min(5, len(likert_cols))], file_id, "Correlation between rating scales")
                    if likert_corr_chart:
                        likert_corr_chart.type = ChartType.LIKERT_CORRELATION
                        visualizations.append(likert_corr_chart)
                except Exception as e:
                    logger.warning(f"Error creating likert correlation chart: {str(e)}")
            
            # 15. Tạo biểu đồ word cloud cho text (nếu có)
            if text_cols and hasattr(self, '_create_word_cloud') and (not chart_types or ChartType.WORD_CLOUD in chart_types):
                for col in text_cols[:min(1, len(text_cols))]:
                    try:
                        word_cloud = self._create_word_cloud(df_viz, col, file_id, f"Word cloud for {col.replace('_', ' ')}")
                        if word_cloud:
                            visualizations.append(word_cloud)
                    except Exception as e:
                        logger.warning(f"Error creating word cloud for {col}: {str(e)}")
            
            # Giới hạn số lượng biểu đồ
            visualizations = visualizations[:max_charts]
            
            # Lưu vào cache
            self.visualization_cache[df_hash] = visualizations
            
            logger.info(f"Generated {len(visualizations)} charts in {time.time() - start_time:.2f}s")
            
            return visualizations
        except Exception as e:
            logger.error(f"Error generating automatic charts: {str(e)}", exc_info=True)
            return visualizations
            
    def _detect_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Phát hiện kiểu dữ liệu cho mỗi cột sử dụng ColumnTypeManager"""
        return self.data_processor.get_column_types(df)

    def _generate_df_hash(self, df: pd.DataFrame) -> str:
        """Tạo hash key cho DataFrame dựa trên shape, columns và sample values"""
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

    def _create_distribution_chart(
        self, df: pd.DataFrame, column: str, file_id: Optional[str] = None, title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """Tạo biểu đồ phân phối (histogram) cho cột numeric với phân tích nâng cao"""
        if not is_numeric_dtype(df[column]):
            return None
            
        try:
            # Tính histogram
            hist, bin_edges = np.histogram(df[column].dropna(), bins=15)
            
            # Tạo dữ liệu cho biểu đồ
            data = []
            for i in range(len(hist)):
                midpoint = (bin_edges[i] + bin_edges[i+1]) / 2
                data.append({
                    "bin": f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}",
                    "frequency": int(hist[i]),
                    "midpoint": float(midpoint)
                })
                
            # Tính thống kê bổ sung
            mean = df[column].mean()
            median = df[column].median()
            std_dev = df[column].std()
            skewness = df[column].skew()
            kurtosis = df[column].kurtosis()
            
            # Phát hiện dạng phân bố
            distribution_type = "normal"
            if abs(skewness) > 1.0:
                distribution_type = "skewed"
                if skewness > 0:
                    distribution_type = "right-skewed"
                else:
                    distribution_type = "left-skewed"
            
            if abs(kurtosis) > 1.0:
                if kurtosis > 0:
                    distribution_type += " heavy-tailed"
                else: 
                    distribution_type += " light-tailed"
            
            # Phát hiện multi-modal distribution
            multi_modal = False
            peaks = []
            for i in range(1, len(hist) - 1):
                if hist[i] > hist[i-1] and hist[i] > hist[i+1]:
                    peaks.append(i)
            if len(peaks) > 1:
                multi_modal = True
            
            # Tạo insight
            insight = (
                f"The distribution of {column} has a mean of {mean:.2f} and median of {median:.2f}. "
            )
            
            if multi_modal:
                insight += f"It shows a multi-modal distribution with {len(peaks)} peaks. "
            else:
                insight += f"It has a {distribution_type} distribution. "
            
            if abs(skewness) > 1.0:
                skew_type = "right-skewed (positive skew)" if skewness > 0 else "left-skewed (negative skew)"
                insight += f"It is {skew_type} with a skewness of {skewness:.2f}."
            else:
                insight += f"It has a relatively symmetric distribution (skewness: {skewness:.2f})."
            
            # Tạo biểu đồ
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.HISTOGRAM,
                title=title or f"Distribution of {column}",
                description=f"Histogram showing the distribution of values for {column}",
                data=data,
                config={
                    "xAxis": {"key": "midpoint", "name": column, "type": "number"},
                    "yAxis": {"key": "frequency", "name": "Frequency"},
                    "height": 400,
                    "width": 600,
                    "showMean": True,
                    "showMedian": True,
                    "meanValue": float(mean),
                    "medianValue": float(median)
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating distribution chart: {str(e)}")
            return None

    def _create_categorical_chart(
        self, df: pd.DataFrame, column: str, file_id: Optional[str] = None, title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """Tạo biểu đồ phân phối cho cột categorical"""
        try:
            # Đếm tần suất các giá trị
            value_counts = df[column].value_counts()
            
            # Giới hạn số lượng categories
            max_categories = self.config.get("visualization", {}).get("max_categories_in_chart", 12)
            if len(value_counts) > max_categories:
                top_values = value_counts.head(max_categories - 1)
                others_count = value_counts.iloc[max_categories - 1:].sum()
                value_counts = pd.concat([top_values, pd.Series({"Others": others_count})])
            
            # Tạo dữ liệu cho biểu đồ
            data = []
            for cat, count in value_counts.items():
                data.append({
                    "category": str(cat),
                    "value": int(count),
                    "percent": float(count / value_counts.sum() * 100)
                })
                
            # Tạo insight
            top_category = value_counts.index[0]
            top_pct = value_counts.iloc[0] / value_counts.sum() * 100
            
            # Tính toán entropy để đánh giá sự cân bằng
            probabilities = value_counts / value_counts.sum()
            entropy = -np.sum(probabilities * np.log2(probabilities))
            max_entropy = np.log2(len(value_counts))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
            
            # Tạo insight với entropy
            if len(value_counts) <= 5:
                insight = (
                    f"The most common value for {column} is '{top_category}' making up "
                    f"{top_pct:.1f}% of all values."
                )
                
                if normalized_entropy > 0.9:
                    insight += f" The distribution is very balanced (entropy: {entropy:.2f})."
                elif normalized_entropy > 0.7:
                    insight += f" The distribution is moderately balanced (entropy: {entropy:.2f})."
                else:
                    insight += f" The distribution is imbalanced (entropy: {entropy:.2f})."
            else:
                insight = (
                    f"The category '{top_category}' represents {top_pct:.1f}% of all data in {column}. "
                    f"There are {len(value_counts)} distinct categories in total."
                )
                
                if normalized_entropy > 0.8:
                    insight += f" The distribution is balanced across categories (entropy: {entropy:.2f})."
                else:
                    insight += f" The distribution is uneven across categories (entropy: {entropy:.2f})."
            
            # Tạo biểu đồ
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.BAR,
                title=title or f"Distribution of {column}",
                description=f"Bar chart showing the distribution of categories for {column}",
                data=data,
                config={
                    "xAxis": {"key": "category", "name": column},
                    "yAxis": {"key": "value", "name": "Count"},
                    "height": 400,
                    "width": 600,
                    "showPercentages": True,
                    "percentKey": "percent"
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating categorical chart: {str(e)}")
            return None

    def _create_time_series_chart(
        self, 
        df: pd.DataFrame, 
        time_column: str, 
        value_column: str,
        file_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """Tạo biểu đồ time series"""
        if not is_datetime64_any_dtype(df[time_column]) or not is_numeric_dtype(df[value_column]):
            return None
            
        try:
            # Sort by time
            df_sorted = df.sort_values(by=time_column)
            
            # Tự động chọn mức độ tổng hợp
            time_range = (df_sorted[time_column].max() - df_sorted[time_column].min()).total_seconds()
            
            # CHỈ chọn các cột cần thiết để tránh lỗi với category dtype
            df_subset = df_sorted[[time_column, value_column]].copy()
            
            # Quyết định aggregation
            if time_range < 86400:  # < 1 day
                aggregation = 'hourly'
                agg_df = df_subset.set_index(time_column).resample('h').mean().reset_index()
            elif time_range < 2592000:  # < 30 days
                aggregation = 'daily'
                agg_df = df_subset.set_index(time_column).resample('d').mean().reset_index()
            elif time_range < 31536000:  # < 1 year
                aggregation = 'weekly'
                agg_df = df_subset.set_index(time_column).resample('w').mean().reset_index()
            else:  # > 1 year
                aggregation = 'monthly'
                agg_df = df_subset.set_index(time_column).resample('ME').mean().reset_index()
            
            # Tạo dữ liệu cho biểu đồ
            data = []
            for _, row in agg_df.iterrows():
                data.append({
                    "time": row[time_column].isoformat(),
                    "value": float(row[value_column])
                })
            
            # Phát hiện trend
            has_trend = False
            trend_direction = "stable"
            if len(agg_df) >= 5:
                first_half = agg_df[value_column].iloc[:len(agg_df)//2].mean()
                second_half = agg_df[value_column].iloc[len(agg_df)//2:].mean()
                
                if second_half > first_half * 1.1:  # Tăng >10%
                    has_trend = True
                    trend_direction = "increasing"
                elif second_half < first_half * 0.9:  # Giảm >10%
                    has_trend = True
                    trend_direction = "decreasing"
                    
                trend_pct = (second_half - first_half) / first_half * 100 if first_half != 0 else 0
            
            # Phát hiện seasonality
            has_seasonality = False
            if len(agg_df) >= 10:
                try:
                    # Tạo time series có index là ngày
                    ts = agg_df.set_index(time_column)[value_column]
                    
                    # Xác định period cho decompose
                    if aggregation == 'hourly':
                        period = 24  # 24 giờ trong ngày
                    elif aggregation == 'daily':
                        period = 7   # 7 ngày trong tuần
                    elif aggregation == 'weekly':
                        period = 52  # 52 tuần trong năm
                    else:  # monthly
                        period = 12  # 12 tháng trong năm
                    
                    # Decompose time series
                    if len(ts) >= 2 * period:  # Cần đủ dữ liệu để phân tích
                        result = seasonal_decompose(ts, model='additive', period=period, extrapolate_trend='freq')
                        
                        # Tính sức mạnh của seasonal component
                        resid_std = result.resid.dropna().std()
                        seasonal_std = result.seasonal.std()
                        
                        # Nếu seasonal component đáng kể
                        has_seasonality = seasonal_std > 0.2 * resid_std
                except Exception as e:
                    logger.warning(f"Error detecting seasonality: {str(e)}")
                    pass
            
            # Tạo insight
            if has_trend:
                insight = (
                    f"The {value_column} shows a {trend_direction} trend over time "
                    f"({trend_pct:.1f}% {'increase' if trend_pct > 0 else 'decrease'})."
                )
            else:
                insight = f"The {value_column} remains relatively stable over time."
                
            if has_seasonality:
                insight += f" The data shows seasonal patterns with period of approximately {period} {aggregation[:-2]}s."
            
            # Tạo biểu đồ
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.LINE,
                title=title or f"{value_column} over Time",
                description=f"Line chart showing changes in {value_column} over {time_column} ({aggregation} aggregation)",
                data=data,
                config={
                    "xAxis": {"key": "time", "name": time_column, "dataKey": "time"},
                    "yAxis": {"key": "value", "name": value_column},
                    "height": 400,
                    "width": 800,
                    "showTrend": has_trend,
                    "seasonality": has_seasonality
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating time series chart: {str(e)}")
            return None
        
    def _create_correlation_chart(
        self, 
        df: pd.DataFrame, 
        columns: List[str],
        file_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """Tạo biểu đồ tương quan (heatmap) với phân tích nâng cao"""
        try:
            # Chỉ lấy các cột numeric
            numeric_columns = [col for col in columns if is_numeric_dtype(df[col])]
            
            # Cần ít nhất 2 cột numeric
            if len(numeric_columns) < 2:
                logger.warning(f"Cannot create correlation chart: need at least 2 numeric columns")
                return None
            
            # Tính ma trận tương quan
            corr_matrix = df[numeric_columns].corr().round(2)
            
            # Tạo dữ liệu cho biểu đồ
            data = []
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    data.append({
                        "x": col1,
                        "y": col2,
                        "value": float(corr_matrix.iloc[i, j])
                    })
            
            # Tìm các cặp tương quan mạnh
            strong_corrs = []
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    if i < j:  # Chỉ xét nửa trên của ma trận
                        corr = corr_matrix.iloc[i, j]
                        if abs(corr) > 0.7:
                            strong_corrs.append((col1, col2, corr))
            
            # Phát hiện multicollinearity
            has_multicollinearity = False
            multicollinear_groups = []
            if len(strong_corrs) > 1:
                # Tìm các nhóm biến có tương quan cao
                from collections import defaultdict
                graph = defaultdict(list)
                
                # Tạo graph từ các cặp tương quan cao
                for col1, col2, corr in strong_corrs:
                    graph[col1].append(col2)
                    graph[col2].append(col1)
                
                # Tìm các connected components (nhóm biến tương quan)
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
                        if len(component) > 2:  # Nhóm có ít nhất 3 biến
                            multicollinear_groups.append(component)
                            has_multicollinearity = True
            
            # Tạo insight
            if strong_corrs:
                top_corr = sorted(strong_corrs, key=lambda x: abs(x[2]), reverse=True)[0]
                corr_type = "positive" if top_corr[2] > 0 else "negative"
                
                insight = (
                    f"Strong {corr_type} correlation ({top_corr[2]:.2f}) found between "
                    f"{top_corr[0]} and {top_corr[1]}."
                )
                
                if len(strong_corrs) > 1:
                    insight += f" There are {len(strong_corrs)} pairs of strongly correlated variables."
                    
                if has_multicollinearity:
                    insight += f" Multicollinearity detected among {len(multicollinear_groups)} groups of variables."
            else:
                insight = "No strong correlations were found between the variables."
            
            # Tạo biểu đồ
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.HEATMAP,
                title=title or "Correlation Matrix",
                description="Heatmap showing correlations between numeric variables",
                data=data,
                config={
                    "xAxis": {"key": "x", "name": "Variables"},
                    "yAxis": {"key": "y", "name": "Variables"},
                    "colorScale": ["#2166ac", "#f7fbff", "#b2182b"],
                    "height": 500,
                    "width": 500
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating correlation chart: {str(e)}")
            return None

    def _create_scatter_chart(
        self, 
        df: pd.DataFrame, 
        x_column: str, 
        y_column: str,
        file_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """Tạo scatter plot với phân tích nâng cao"""
        if not is_numeric_dtype(df[x_column]) or not is_numeric_dtype(df[y_column]):
            return None
            
        try:
            # Tạo dữ liệu cho biểu đồ
            data = []
            for _, row in df.iterrows():
                if pd.notna(row[x_column]) and pd.notna(row[y_column]):
                    data.append({
                        "x": float(row[x_column]),
                        "y": float(row[y_column])
                    })
            
            # Giới hạn số lượng điểm
            max_points = self.config.get("visualization", {}).get("max_points_in_scatter", 5000)
            if len(data) > max_points:
                import random
                random.seed(42)  # Để kết quả nhất quán
                data = random.sample(data, max_points)
            
            # Tính hệ số tương quan
            correlation = df[[x_column, y_column]].corr().iloc[0, 1]
            
            # Phát hiện mối quan hệ phi tuyến tính
            non_linear = False
            relationship_type = "linear"
            
            try:
                from scipy.stats import spearmanr
                
                # So sánh Pearson và Spearman correlation
                spearman_corr = spearmanr(df[x_column].dropna(), df[y_column].dropna())[0]
                
                # Nếu Spearman correlation mạnh hơn đáng kể
                if abs(spearman_corr) > abs(correlation) + 0.2:
                    non_linear = True
                    relationship_type = "monotonic non-linear"
                
                # Thử fit mô hình bậc 2 để kiểm tra quan hệ quadratic
                from sklearn.linear_model import LinearRegression
                from sklearn.preprocessing import PolynomialFeatures
                
                # Chuẩn bị dữ liệu
                X = df[x_column].dropna().values.reshape(-1, 1)
                y = df[y_column].dropna().values
                
                if len(X) > 10:  # Cần đủ dữ liệu
                    # Fit linear model
                    linear_model = LinearRegression()
                    linear_model.fit(X, y)
                    linear_score = linear_model.score(X, y)
                    
                    # Fit quadratic model
                    poly_features = PolynomialFeatures(degree=2)
                    X_poly = poly_features.fit_transform(X)
                    
                    poly_model = LinearRegression()
                    poly_model.fit(X_poly, y)
                    poly_score = poly_model.score(X_poly, y)
                    
                    # Nếu mô hình bậc 2 tốt hơn đáng kể
                    if poly_score > linear_score + 0.1:
                        non_linear = True
                        relationship_type = "quadratic"
                        
                        # Xác định hướng của đường cong (concave up/down)
                        quad_coef = poly_model.coef_[2]
                        if quad_coef > 0:
                            relationship_type = "quadratic (U-shaped)"
                        else:
                            relationship_type = "quadratic (inverted U-shaped)"
            except:
                pass
            
            # Tạo insight
            if abs(correlation) > 0.7:
                strength = "strong"
            elif abs(correlation) > 0.5:
                strength = "moderate"
            elif abs(correlation) > 0.3:
                strength = "weak"
            else:
                strength = "very weak"
                
            direction = "positive" if correlation > 0 else "negative"
            
            insight = (
                f"There is a {strength} {direction} correlation (r={correlation:.2f}) "
                f"between {x_column} and {y_column}."
            )
            
            if non_linear:
                insight += f" The relationship appears to be {relationship_type} rather than purely linear."
            
            # Tạo biểu đồ
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.SCATTER,
                title=title or f"Relationship between {x_column} and {y_column}",
                description=f"Scatter plot showing the relationship between {x_column} and {y_column}",
                data=data,
                config={
                    "xAxis": {"key": "x", "name": x_column},
                    "yAxis": {"key": "y", "name": y_column},
                    "height": 400,
                    "width": 600,
                    "showTrendline": True,
                    "correlationValue": float(correlation),
                    "nonLinear": non_linear,
                    "relationshipType": relationship_type
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating scatter chart: {str(e)}")
            return None

    def _create_pie_chart(
        self, df: pd.DataFrame, column: str, file_id: Optional[str] = None, title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """Tạo biểu đồ tròn cho với phân tích nâng cao"""
        try:
            # Đếm tần suất các giá trị
            value_counts = df[column].value_counts()
            
            # Giới hạn số lượng categories
            max_categories = 8
            if len(value_counts) > max_categories:
                top_values = value_counts.head(max_categories - 1)
                others_count = value_counts.iloc[max_categories - 1:].sum()
                value_counts = pd.concat([top_values, pd.Series({"Others": others_count})])
            
            # Tạo dữ liệu cho biểu đồ
            data = []
            for cat, count in value_counts.items():
                data.append({
                    "name": str(cat),
                    "value": int(count),
                    "percent": float(count / value_counts.sum() * 100)
                })
                
            # Tính phần trăm cho top 2 categories
            top_cats = value_counts.head(2)
            top_pcts = (top_cats / value_counts.sum() * 100).round(1)
            
            # Tính chỉ số phân bố
            entropy = -np.sum((value_counts / value_counts.sum()) * np.log2(value_counts / value_counts.sum()))
            max_entropy = np.log2(len(value_counts))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
            
            # Tạo insight
            insight = (
                f"The top 2 categories in {column} are '{top_cats.index[0]}' ({top_pcts.iloc[0]}%) "
                f"and '{top_cats.index[1]}' ({top_pcts.iloc[1]}%), "
                f"together making up {(top_pcts.iloc[0] + top_pcts.iloc[1]):.1f}% of all data."
            )
            
            # Thêm thông tin về tính cân bằng
            if normalized_entropy > 0.9:
                insight += f" The distribution is very balanced (normalized entropy: {normalized_entropy:.2f})."
            elif normalized_entropy > 0.7:
                insight += f" The distribution is moderately balanced (normalized entropy: {normalized_entropy:.2f})."
            else:
                insight += f" The distribution is dominated by a few categories (normalized entropy: {normalized_entropy:.2f})."
            
            # Tạo biểu đồ
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.PIE,
                title=title or f"Distribution of {column}",
                description=f"Pie chart showing the distribution of categories for {column}",
                data=data,
                config={
                    "nameKey": "name",
                    "valueKey": "value",
                    "percentKey": "percent",
                    "height": 400,
                    "width": 500,
                    "showPercentages": True,
                    "entropy": float(entropy),
                    "normalizedEntropy": float(normalized_entropy)
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating pie chart: {str(e)}")
            return None
        
    def _create_group_chart(
        self, 
        df: pd.DataFrame, 
        category_column: str, 
        value_column: str,
        file_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """Tạo biểu đồ nhóm (giá trị theo category) với phân tích nâng cao"""
        if not is_numeric_dtype(df[value_column]):
            return None
            
        try:
            # Tính giá trị thống kê theo nhóm
            grouped = df.groupby(category_column, observed=True)[value_column].agg(['mean', 'median', 'std', 'count']).reset_index()
            
            # Sắp xếp theo giá trị trung bình (giảm dần)
            grouped = grouped.sort_values('mean', ascending=False)
            
            # Giới hạn số lượng nhóm
            if len(grouped) > 10:
                grouped = grouped.head(10)
            
            # Tạo dữ liệu cho biểu đồ
            data = []
            for _, row in grouped.iterrows():
                data.append({
                    "category": str(row[category_column]),
                    "value": float(row['mean']),
                    "std": float(row['std']) if not pd.isna(row['std']) else 0,
                    "median": float(row['median']),
                    "count": int(row['count'])
                })
            
            # Tính ANOVA để kiểm tra sự khác biệt giữa các nhóm
            from scipy import stats
            
            group_vals = [df[df[category_column] == cat][value_column].dropna().values 
                        for cat in grouped[category_column]]
            
            # Chỉ tính ANOVA nếu có ít nhất 2 nhóm với đủ dữ liệu
            has_significant_diff = False
            p_value = 1.0
            
            valid_groups = [g for g in group_vals if len(g) > 0]
            if len(valid_groups) >= 2:
                try:
                    anova_result = stats.f_oneway(*valid_groups)
                    p_value = anova_result.pvalue
                    has_significant_diff = p_value < 0.05
                except:
                    pass
            
            # Tìm nhóm có giá trị cao nhất và thấp nhất
            highest_group = grouped.iloc[0]
            lowest_group = grouped.iloc[-1]
            
            # Tính difference magnitude
            if len(grouped) >= 2:
                max_val = highest_group['mean']
                min_val = lowest_group['mean']
                overall_mean = df[value_column].mean()
                
                diff_magnitude = (max_val - min_val) / overall_mean if overall_mean != 0 else 0
            else:
                diff_magnitude = 0
            
            # Tạo insight
            insight = (
                f"The average {value_column} is highest for {highest_group[category_column]} "
                f"({highest_group['mean']:.2f}) and lowest for {lowest_group[category_column]} "
                f"({lowest_group['mean']:.2f})."
            )
            
            if has_significant_diff:
                insight += f" There is a statistically significant difference between groups (p-value: {p_value:.4f})."
            elif p_value < 1.0:
                insight += f" The difference between groups is not statistically significant (p-value: {p_value:.4f})."
            
            if diff_magnitude > 1.0:
                insight += f" The difference between the highest and lowest groups is very large ({diff_magnitude:.1f}x the overall average)."
            elif diff_magnitude > 0.5:
                insight += f" The difference between the highest and lowest groups is substantial ({diff_magnitude:.1f}x the overall average)."
            
            # Tạo biểu đồ
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.BAR,
                title=title or f"Average {value_column} by {category_column}",
                description=f"Bar chart showing average {value_column} for each {category_column} category",
                data=data,
                config={
                    "xAxis": {"key": "category", "name": category_column},
                    "yAxis": {"key": "value", "name": f"Average {value_column}"},
                    "height": 400,
                    "width": 600,
                    "showErrorBars": True,
                    "errorKey": "std",
                    "showMedian": True,
                    "medianKey": "median",
                    "hasSignificantDiff": has_significant_diff,
                    "pValue": float(p_value) if p_value < 1.0 else 1.0
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating group chart: {str(e)}")
            return None
            
    def _create_box_plot(
        self,
        df: pd.DataFrame,
        column: str,
        file_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """
        Tạo box plot cho cột numeric để hiển thị phân phối và outliers
        
        Args:
            df: DataFrame chứa dữ liệu
            column: Tên cột cần visualize
            title: Tiêu đề biểu đồ (optional)
            
        Returns:
            VisualizationData: Box plot visualization
        """
        if not is_numeric_dtype(df[column]):
            return None
            
        try:
            # Tính các thống kê cần thiết cho box plot
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            median = df[column].median()
            iqr = q3 - q1
            
            # Whiskers
            lower_whisker = df[df[column] >= q1 - 1.5 * iqr][column].min()
            upper_whisker = df[df[column] <= q3 + 1.5 * iqr][column].max()
            
            # Outliers
            lower_outliers = df[df[column] < q1 - 1.5 * iqr][column].tolist()
            upper_outliers = df[df[column] > q3 + 1.5 * iqr][column].tolist()
            
            # Limit outliers for visualization
            max_outliers = 50
            if len(lower_outliers) > max_outliers:
                lower_outliers = lower_outliers[:max_outliers]
            if len(upper_outliers) > max_outliers:
                upper_outliers = upper_outliers[:max_outliers]
                
            # Combine stats into data format
            data = [
                {"type": "boxplot", "name": "lowerWhisker", "value": float(lower_whisker)},
                {"type": "boxplot", "name": "q1", "value": float(q1)},
                {"type": "boxplot", "name": "median", "value": float(median)},
                {"type": "boxplot", "name": "q3", "value": float(q3)},
                {"type": "boxplot", "name": "upperWhisker", "value": float(upper_whisker)}
            ]

            for outlier in lower_outliers + upper_outliers:
                data.append({"type": "outlier", "value": float(outlier)})
            
            # Generate insight
            total_outliers = len(lower_outliers) + len(upper_outliers)
            outlier_pct = total_outliers / len(df[column].dropna()) * 100
            
            insight = (
                f"The distribution of {column} has a median of {median:.2f}, "
                f"with 50% of values between {q1:.2f} and {q3:.2f} (IQR: {iqr:.2f}). "
            )
            
            if total_outliers > 0:
                insight += (
                    f"There are {total_outliers} outliers ({outlier_pct:.1f}% of data), "
                    f"with {len(lower_outliers)} below {lower_whisker:.2f} and "
                    f"{len(upper_outliers)} above {upper_whisker:.2f}."
                )
            else:
                insight += "There are no outliers in the data."
                
            # Skewness assessment
            skewness = df[column].skew()
            if skewness > 0.5:
                insight += " The distribution is right-skewed."
            elif skewness < -0.5:
                insight += " The distribution is left-skewed."
            else:
                insight += " The distribution is approximately symmetric."
            
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.BOX,
                title=title or f"Box Plot of {column}",
                description=f"Box plot showing the distribution and outliers of {column}",
                data=data,
                config={
                    "xAxis": {"name": column},
                    "yAxis": {"name": "Value"},
                    "height": 400,
                    "width": 600,
                    "showOutliers": True
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating box plot: {str(e)}")
            return None
            
    def _create_grouped_distribution(
        self,
        df: pd.DataFrame,
        category_column: str,
        value_column: str,
        file_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """
        Create histogram comparing distributions across categories
        
        Args:
            df: DataFrame with data
            category_column: Categorical column for grouping
            value_column: Numeric column for distribution
            title: Chart title (optional)
            
        Returns:
            VisualizationData: Grouped histogram
        """
        if not is_numeric_dtype(df[value_column]):
            return None
            
        try:
            # Only works well for few categories (ideally binary)
            categories = df[category_column].unique()
            if len(categories) > 5:
                return None
                
            # Create bins that work for all categories
            all_values = df[value_column].dropna()
            hist, bin_edges = np.histogram(all_values, bins=10)
            
            # Create data structure for each category
            data = []
            
            for cat in categories:
                cat_values = df[df[category_column] == cat][value_column].dropna()
                if len(cat_values) == 0:
                    continue
                    
                cat_hist, _ = np.histogram(cat_values, bins=bin_edges)
                
                # Convert to percentages for fair comparison
                cat_hist = (cat_hist / cat_hist.sum()) * 100 if cat_hist.sum() > 0 else cat_hist
                
                for i in range(len(cat_hist)):
                    bin_name = f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}"
                    data.append({
                        "bin": bin_name,
                        "category": str(cat),
                        "frequency": float(cat_hist[i]),
                        "midpoint": float((bin_edges[i] + bin_edges[i+1]) / 2)
                    })
            
            # Run statistical test to compare distributions
            from scipy import stats
            
            # Calculate statistics per group
            group_stats = df.groupby(category_column, observed=True)[value_column].agg(['mean', 'std', 'count']).reset_index()
            
            # Run t-test if binary categorical
            has_significant_diff = False
            p_value = 1.0
            test_name = "None"
            
            if len(categories) == 2:
                group0 = df[df[category_column] == categories[0]][value_column].dropna()
                group1 = df[df[category_column] == categories[1]][value_column].dropna()
                
                if len(group0) > 0 and len(group1) > 0:
                    # Run t-test
                    t_stat, p_value = stats.ttest_ind(group0, group1, equal_var=False)
                    test_name = "t-test"
                    has_significant_diff = p_value < 0.05
            elif len(categories) > 2:
                # ANOVA for more than 2 categories
                groups = [df[df[category_column] == cat][value_column].dropna() for cat in categories]
                valid_groups = [g for g in groups if len(g) > 0]
                
                if len(valid_groups) > 1:
                    try:
                        _, p_value = stats.f_oneway(*valid_groups)
                        test_name = "ANOVA"
                        has_significant_diff = p_value < 0.05
                    except:
                        pass
            
            # Generate insight
            if len(categories) == 2:
                # Binary case
                cat0_mean = group_stats[group_stats[category_column] == categories[0]]['mean'].values[0]
                cat1_mean = group_stats[group_stats[category_column] == categories[1]]['mean'].values[0]
                
                insight = (
                    f"Comparing {value_column} distributions for {category_column} groups: "
                    f"{categories[0]} (mean: {cat0_mean:.2f}) vs {categories[1]} (mean: {cat1_mean:.2f}). "
                )
                
                if has_significant_diff:
                    insight += f"The difference is statistically significant ({test_name}, p-value: {p_value:.4f})."
                else:
                    insight += f"The difference is not statistically significant ({test_name}, p-value: {p_value:.4f})."
            else:
                # Multiple categories
                insight = f"Comparing {value_column} distributions across {len(categories)} {category_column} groups. "
                
                if has_significant_diff:
                    insight += f"There are significant differences between groups ({test_name}, p-value: {p_value:.4f})."
                elif p_value < 1.0:
                    insight += f"Differences between groups are not statistically significant ({test_name}, p-value: {p_value:.4f})."
            
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.GROUPED_HISTOGRAM,
                title=title or f"Distribution of {value_column} by {category_column}",
                description=f"Grouped histogram showing distribution of {value_column} for each {category_column} value",
                data=data,
                config={
                    "xAxis": {"key": "midpoint", "name": value_column},
                    "yAxis": {"key": "frequency", "name": "Percentage (%)"},
                    "groupKey": "category",
                    "binKey": "bin",
                    "height": 400,
                    "width": 600,
                    "statistics": group_stats.to_dict(orient='records'),
                    "hasSignificantDiff": has_significant_diff,
                    "pValue": float(p_value),
                    "testName": test_name
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Error creating grouped distribution chart: {str(e)}")
            return None
        
    def _create_likert_chart(self, df: pd.DataFrame, column: str, file_id: Optional[str] = None, title: str = "") -> Optional[VisualizationData]:
        """
        Tạo biểu đồ ngang (horizontal bar) đặc biệt cho thang đo Likert
        
        Args:
            df: DataFrame với dữ liệu
            column: Tên cột Likert scale
            file_id: ID tệp (nếu có)
            title: Tiêu đề biểu đồ
            
        Returns:
            VisualizationData: Đối tượng biểu đồ đã tạo hoặc None nếu thất bại
        """
        try:
            if column not in df.columns:
                logger.warning(f"Column {column} not found in DataFrame")
                return None
                
            # Đếm số lượng mỗi giá trị và tạo DataFrame mới cho biểu đồ
            value_counts = df[column].value_counts().sort_index()
            
            # Kiểm tra xem có giá trị thực sự hay không
            if len(value_counts) == 0:
                logger.warning(f"No data for Likert chart on column {column}")
                return None
            
            # Tạo dữ liệu cho chart
            chart_data = []
            for val, count in value_counts.items():
                chart_data.append({
                    "value": str(val),
                    "count": int(count),
                    "percentage": float(count / len(df) * 100)
                })
            
            # Tạo biểu đồ
            chart = VisualizationData(
                title=title,
                type=ChartType.LIKERT,
                x_axis="value",
                y_axis="count",
                x_axis_label=column.replace('_', ' '),
                y_axis_label="Frequency",
                file_id=file_id,
                column_names=[column],
                data=chart_data,
                config={
                    "horizontal": True,
                    "color_scheme": "PuBu",  # Hoặc RdYlGn nếu là thang đánh giá (xanh lá = tốt)
                    "sort_by_value": True,
                    "show_values": True
                }
            )
            
            return chart
        except Exception as e:
            logger.error(f"Error creating Likert chart for {column}: {str(e)}")
            return None

    def _create_binary_chart(self, df: pd.DataFrame, column: str, file_id: Optional[str] = None, title: str = "") -> Optional[VisualizationData]:
        """
        Tạo biểu đồ đặc biệt cho cột binary (dạng biểu đồ cột hoặc biểu đồ bánh)
        
        Args:
            df: DataFrame với dữ liệu
            column: Tên cột binary
            file_id: ID tệp (nếu có)
            title: Tiêu đề biểu đồ
            
        Returns:
            VisualizationData: Đối tượng biểu đồ đã tạo hoặc None nếu thất bại
        """
        try:
            if column not in df.columns:
                logger.warning(f"Column {column} not found in DataFrame")
                return None
                
            # Đếm số lượng mỗi giá trị
            value_counts = df[column].value_counts()
            
            # Kiểm tra xem có giá trị thực sự hay không
            if len(value_counts) == 0:
                logger.warning(f"No data for Binary chart on column {column}")
                return None
            
            # Tạo dữ liệu cho chart
            chart_data = []
            for val, count in value_counts.items():
                chart_data.append({
                    "value": str(val),
                    "count": int(count),
                    "percentage": float(count / len(df) * 100)
                })
            
            # Quyết định loại biểu đồ dựa trên số lượng giá trị
            chart_type = ChartType.PIE if len(value_counts) <= 2 else ChartType.BAR
            
            # Tạo biểu đồ
            chart = VisualizationData(
                title=title,
                type=chart_type,
                x_axis="value" if chart_type == ChartType.BAR else None,
                y_axis="count" if chart_type == ChartType.BAR else None,
                x_axis_label=column.replace('_', ' ') if chart_type == ChartType.BAR else None,
                y_axis_label="Frequency" if chart_type == ChartType.BAR else None,
                file_id=file_id,
                column_names=[column],
                data=chart_data,
                config={
                    "color_scheme": "Set2",
                    "show_percentage": True if chart_type == ChartType.PIE else False,
                    "show_values": True if chart_type == ChartType.BAR else False
                }
            )
            
            return chart
        except Exception as e:
            logger.error(f"Error creating Binary chart for {column}: {str(e)}")
            return None

    def _create_word_cloud(self, df: pd.DataFrame, column: str, file_id: Optional[str] = None, title: str = "") -> Optional[VisualizationData]:
        """
        Tạo biểu đồ word cloud cho cột text
        
        Args:
            df: DataFrame với dữ liệu
            column: Tên cột text
            file_id: ID tệp (nếu có)
            title: Tiêu đề biểu đồ
            
        Returns:
            VisualizationData: Đối tượng biểu đồ đã tạo hoặc None nếu thất bại
        """
        try:
            if column not in df.columns:
                logger.warning(f"Column {column} not found in DataFrame")
                return None
                
            # Gộp tất cả các văn bản thành một chuỗi
            text_data = ' '.join(df[column].astype(str).fillna('').tolist())
            
            # Kiểm tra xem có văn bản thực sự hay không
            if not text_data or len(text_data.strip()) == 0:
                logger.warning(f"No text data for Word Cloud on column {column}")
                return None
            
            # Xử lý văn bản: tách từ, loại bỏ stopwords, v.v.
            import re
            from collections import Counter
            
            # Tách từ và chuyển thành lowercase
            words = re.findall(r'\b[a-zA-Z0-9_]+\b', text_data.lower())
            
            # Loại bỏ các từ phổ biến (stopwords)
            stopwords = {'the', 'a', 'an', 'and', 'is', 'in', 'to', 'of', 'for', 'with', 'on', 'at', 'this', 'that', 'it', 'as', 'by'}
            filtered_words = [word for word in words if word not in stopwords and len(word) > 1]
            
            # Đếm tần suất từ
            word_counts = Counter(filtered_words)
            
            # Lấy top từ phổ biến nhất
            top_words = word_counts.most_common(100)
            
            # Tạo dữ liệu cho biểu đồ
            chart_data = []
            for word, count in top_words:
                chart_data.append({
                    "text": word,
                    "value": count
                })
            
            # Tạo biểu đồ
            chart = VisualizationData(
                title=title,
                type=ChartType.WORD_CLOUD,
                file_id=file_id,
                column_names=[column],
                data=chart_data,
                config={
                    "color_scheme": "Category20",
                    "max_words": 100,
                    "word_count": len(chart_data)
                }
            )
            
            return chart
        except Exception as e:
            logger.error(f"Error creating Word Cloud for {column}: {str(e)}")
            return None
    
    def create_time_series_visualization(
        self, 
        df: pd.DataFrame, 
        time_column: str, 
        value_column: str,
        aggregation: str = 'auto',
        file_id: Optional[str] = None
    ) -> Optional[VisualizationData]:
        """
        Tạo biểu đồ time series nâng cao với phân tích trend và seasonality
        
        Args:
            df: DataFrame chứa dữ liệu
            time_column: Tên cột thời gian
            value_column: Tên cột giá trị
            aggregation: Phương pháp tổng hợp dữ liệu ('auto', 'hourly', 'daily', 'weekly', 'monthly')
            
        Returns:
            VisualizationData: Dữ liệu biểu đồ
        """
        try:
            # Đảm bảo dữ liệu đúng định dạng datetime
            df_copy = df.copy()
            if not pd.api.types.is_datetime64_any_dtype(df_copy[time_column]):
                df_copy[time_column] = convert_to_datetime(df_copy[time_column])
            
            # Loại bỏ NaT trong cột thời gian
            df_copy = df_copy.dropna(subset=[time_column])
            if len(df_copy) == 0:
                logger.warning(f"Không có dữ liệu hợp lệ sau khi loại bỏ NaT trong cột {time_column}")
                return None
            
            # Đảm bảo cột giá trị là numeric
            if not is_numeric_dtype(df_copy[value_column]):
                try:
                    df_copy[value_column] = pd.to_numeric(df_copy[value_column], errors='coerce')
                except:
                    logger.warning(f"Không thể chuyển đổi cột {value_column} thành numeric")
                    return None
            
            # Loại bỏ NaN trong cột giá trị
            df_copy = df_copy.dropna(subset=[value_column])
            if len(df_copy) == 0:
                logger.warning(f"Không có dữ liệu hợp lệ sau khi loại bỏ NaN trong cột {value_column}")
                return None
            
            # Sắp xếp theo thời gian
            df_copy = df_copy.sort_values(by=time_column)
            
            # Tự động xác định mức độ tổng hợp phù hợp dựa trên dữ liệu
            if aggregation == 'auto':
                time_range = (df_copy[time_column].max() - df_copy[time_column].min()).total_seconds()
                
                if time_range < 86400:  # < 1 day
                    aggregation = 'hourly'
                elif time_range < 2592000:  # < 30 days
                    aggregation = 'daily'
                elif time_range < 31536000:  # < 1 year
                    aggregation = 'weekly'
                else:
                    aggregation = 'monthly'
            
            # CHỈ chọn các cột cần thiết cho resampling để tránh lỗi với cột category
            df_subset = df_copy[[time_column, value_column]].copy()
            
            # Áp dụng mức độ tổng hợp
            if aggregation == 'hourly':
                df_agg = df_subset.set_index(time_column).resample('h').mean().reset_index()
            elif aggregation == 'daily':
                df_agg = df_subset.set_index(time_column).resample('d').mean().reset_index()
            elif aggregation == 'weekly':
                df_agg = df_subset.set_index(time_column).resample('w').mean().reset_index()
            else:  # monthly
                df_agg = df_subset.set_index(time_column).resample('ME').mean().reset_index()
            
            # Phát hiện trend và seasonality
            has_seasonality = False
            trend_direction = "không rõ"
            
            # Tạo dữ liệu cho biểu đồ - XỬ LÝ NaT VÀ NaN
            data = []
            for _, row in df_agg.iterrows():
                # Đảm bảo cả time và value đều không phải NaT/NaN
                if pd.notna(row[time_column]) and pd.notna(row[value_column]):
                    data.append({
                        "time": row[time_column].isoformat() if hasattr(row[time_column], 'isoformat') else str(row[time_column]),
                        "value": float(row[value_column])
                    })
            
            # Kiểm tra nếu không có dữ liệu sau khi lọc
            if not data:
                logger.warning("Không có dữ liệu hợp lệ sau khi lọc NaT/NaN trong quá trình tổng hợp")
                return None
            
            # Phân tích trend
            if len(df_agg) >= 5:
                first_half = df_agg[value_column].iloc[:len(df_agg)//2].mean()
                second_half = df_agg[value_column].iloc[len(df_agg)//2:].mean()
                
                trend_pct = ((second_half - first_half) / first_half * 100) if first_half != 0 else 0
                
                if second_half > first_half * 1.1:
                    trend_direction = "tăng"
                elif second_half < first_half * 0.9:
                    trend_direction = "giảm"
                else:
                    trend_direction = "ổn định"
            
            # Thử phát hiện seasonality nếu có đủ dữ liệu
            if len(df_agg) >= 10:
                try:
                    from statsmodels.tsa.seasonal import seasonal_decompose
                    
                    # Tạo time series có index là ngày
                    ts = df_agg.set_index(time_column)[value_column]
                    
                    # Xác định period cho seasonal_decompose
                    if aggregation == 'hourly':
                        period = 24  # 24 giờ trong ngày
                    elif aggregation == 'daily':
                        period = 7   # 7 ngày trong tuần
                    elif aggregation == 'weekly':
                        period = 52  # 52 tuần trong năm
                    else:  # monthly
                        period = 12  # 12 tháng trong năm
                    
                    # Decompose time series nếu có đủ dữ liệu
                    if len(ts) >= 2 * period:
                        # Sử dụng extrapolate_trend để tránh NaN ở đầu/cuối
                        decomposition = seasonal_decompose(ts, model='additive', period=period, extrapolate_trend='freq')
                        
                        # Kiểm tra seasonality
                        residuals_std = decomposition.resid.dropna().std()
                        seasonal_std = decomposition.seasonal.std()
                        
                        # Có seasonality nếu thành phần seasonal đáng kể
                        has_seasonality = seasonal_std > 0.1 * residuals_std
                except Exception as e:
                    logger.warning(f"Lỗi khi phát hiện seasonality: {str(e)}")
            
            # Tạo insight
            if trend_direction == "tăng":
                insight = f"Dữ liệu {value_column} theo thời gian cho thấy xu hướng tăng"
                if 'trend_pct' in locals():
                    insight += f" ({abs(trend_pct):.1f}%)"
            elif trend_direction == "giảm":
                insight = f"Dữ liệu {value_column} theo thời gian cho thấy xu hướng giảm"
                if 'trend_pct' in locals():
                    insight += f" ({abs(trend_pct):.1f}%)"
            else:
                insight = f"Dữ liệu {value_column} theo thời gian tương đối ổn định"
                
            if has_seasonality:
                insight += " và có yếu tố chu kỳ"
                
                if aggregation == 'daily':
                    insight += " theo tuần"
                elif aggregation == 'weekly':
                    insight += " theo năm"
                elif aggregation == 'monthly':
                    insight += " theo năm"
                    
            insight += "."
            
            # Bổ sung thông tin tổng hợp
            agg_label = {
                'hourly': 'theo giờ', 
                'daily': 'theo ngày', 
                'weekly': 'theo tuần', 
                'monthly': 'theo tháng'
            }.get(aggregation, aggregation)
            
            insight += f" Dữ liệu được tổng hợp {agg_label}."
            
            return VisualizationData(
                id=str(v4()),
                fileId=file_id,
                type=ChartType.LINE,
                title=f"{value_column} theo thời gian",
                description=f"Biểu đồ time series cho {value_column} (tổng hợp {aggregation})",
                data=data,
                config={
                    "xAxis": {"key": "time", "name": time_column},
                    "yAxis": {"key": "value", "name": value_column},
                    "height": 400,
                    "width": 800,
                    "showTrend": True,
                    "showPoints": len(data) < 100,  # Hiện điểm nếu không quá nhiều dữ liệu
                    "seasonality": has_seasonality
                },
                insight=insight
            )
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ time series: {str(e)}", exc_info=True)
            return None