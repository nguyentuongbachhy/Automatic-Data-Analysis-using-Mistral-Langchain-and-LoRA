"""
Module tạo insights từ dữ liệu sử dụng MistralAI thay vì hardcode.
"""

import logging
from typing import Dict, List, Optional, Union, Any

from uuid import uuid4 as v4
import textwrap
import pandas as pd
import re
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype
from scipy import stats

from app.models.analysis import InsightData, InsightType
from ml.utils.datetime_utils import detect_datetime_columns
from ml.data.data_processor import DataProcessor  # Import thêm DataProcessor để sử dụng

logger = logging.getLogger(__name__)


class InsightGenerator:
    """Generator cho các insights từ dữ liệu sử dụng Mistral AI"""

    def __init__(self, config_path: Optional[Union[str, Dict]] = None):
        """Khởi tạo insight generator với Mistral"""
        from ml.model.mistral_inference import MistralInference

        self.mistral = MistralInference(config_path)
        self.config = config_path if isinstance(config_path, dict) else {}
        # Khởi tạo DataProcessor để phát hiện các loại cột
        self.data_processor = DataProcessor()
        logger.info("MistralInsightGenerator initialized")

    def generate_insights(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
        file_id: Optional[str] = None,
        insight_types: Optional[List[str]] = None
    ) -> List[InsightData]:
        """Tạo các insights từ dataframe với Mistral AI"""
        insights = []

        try:
            # Đảm bảo Mistral model được tải
            if not self.mistral.manager.is_model_available:
                self.mistral.load_model()
            
            # Tạo summary về dataset
            summary_insight = self._create_summary_insight_with_mistral(df, file_id)
            if summary_insight:
                insights.append(summary_insight)
            
            # Tạo insights về các phân phối
            if insight_types is None or InsightType.DISTRIBUTION in insight_types:
                distribution_insights = self._create_distribution_insights_with_mistral(df, file_id)
                insights.extend(distribution_insights)
            
            # Tạo insights về tương quan
            if insight_types is None or InsightType.CORRELATION in insight_types:
                correlation_insights = self._create_correlation_insights_with_mistral(
                    df, config.get("data_processing", {}).get("correlation_threshold", 0.7), file_id
                )
                insights.extend(correlation_insights)
            
            # Tạo insights về xu hướng
            if insight_types is None or InsightType.TREND in insight_types:
                trend_insights = self._create_trend_insights_with_mistral(df, file_id)
                insights.extend(trend_insights)
            
            # Tạo insights về outliers
            if insight_types is None or InsightType.OUTLIER in insight_types:
                outlier_insights = self._create_outlier_insights_with_mistral(df, file_id)
                insights.extend(outlier_insights)
            
            # Tạo insights về patterns
            if insight_types is None or InsightType.PATTERN in insight_types:
                pattern_insights = self._create_pattern_insights_with_mistral(df, file_id)
                insights.extend(pattern_insights)
                
            # Tạo comprehesive insights sử dụng Mistral
            comprehensive_insights = self._generate_comprehensive_insights(df, insight_types, file_id)
            insights.extend(comprehensive_insights)
            
            # Sắp xếp insights theo importance
            insights = sorted(insights, key=lambda x: x.importance, reverse=True)
            
            return insights
        except Exception as e:
            logger.error(f"Error generating insights with Mistral: {str(e)}", exc_info=True)
            logger.info("Returning empty insights due to error")
            return []
        
    def generate_rule_based_insights(self, df: pd.DataFrame, file_id: Optional[str] = None, insight_types: Optional[List[str]] = None) -> List[InsightData]:
        """Generate insights using rule-based methods without ML for faster performance"""
        insights = []
        
        try:
            # Phát hiện các loại cột
            column_types = self.data_processor.get_column_types(df)
            
            # 1. Generate summary insight
            insights.append(self._create_summary_insight(df, file_id))
            
            # 2. Generate distribution insights for numeric columns
            if insight_types is None or InsightType.DISTRIBUTION in insight_types:
                distribution_insights = self._create_distribution_insights(df, file_id)
                insights.extend(distribution_insights)
            
            # 3. Generate correlation insights
            if insight_types is None or InsightType.CORRELATION in insight_types:
                correlation_insights = self._create_correlation_insights(df, file_id)
                insights.extend(correlation_insights)
            
            # 4. Generate trend insights for time series data
            if insight_types is None or InsightType.TREND in insight_types:
                trend_insights = self._create_trend_insights(df, file_id)
                insights.extend(trend_insights)
            
            # 5. Generate outlier insights
            if insight_types is None or InsightType.OUTLIER in insight_types:
                outlier_insights = self._create_outlier_insights(df, file_id)
                insights.extend(outlier_insights)
            
            # 6. Generate pattern insights for categorical data
            if insight_types is None or InsightType.PATTERN in insight_types:
                pattern_insights = self._create_pattern_insights(df, file_id)
                insights.extend(pattern_insights)
            
            # 7. Generate insights for binary columns
            binary_insights = self._create_binary_insights(df, column_types.get("binary", []), file_id)
            insights.extend(binary_insights)
            
            # 8. Generate insights for likert scale columns
            likert_insights = self._create_likert_insights(df, column_types.get("likert", []), file_id)
            insights.extend(likert_insights)
            
            # 9. Generate insights for gender columns
            gender_insights = self._create_gender_insights(df, column_types.get("gender", []), file_id)
            insights.extend(gender_insights)
            
            # 10. Generate insights for range columns
            range_insights = self._create_range_insights(df, column_types.get("range", []), file_id)
            insights.extend(range_insights)
            
            # 11. Generate insights for text columns
            text_insights = self._create_text_insights(df, column_types.get("text", []), file_id)
            insights.extend(text_insights)
            
            # Sort insights by importance
            insights = sorted(insights, key=lambda x: x.importance, reverse=True)
            
            return insights
        except Exception as e:
            logger.error(f"Error generating rule-based insights: {str(e)}", exc_info=True)
            return []

    def _create_summary_insight_with_mistral(self, df: pd.DataFrame, file_id: Optional[str]=None) -> Optional[InsightData]:
        """Tạo insight tổng quan về dataset với Mistral"""
        try:
            # Tính số lượng dòng và cột
            num_rows, num_cols = df.shape
            
            # Phân loại cột theo kiểu dữ liệu
            column_types = self.data_processor.get_column_types(df)
            num_numeric = len(column_types.get("numeric", []))
            num_categorical = len(column_types.get("categorical", []))
            num_datetime = len(column_types.get("datetime", []))
            num_binary = len(column_types.get("binary", []))
            num_likert = len(column_types.get("likert", []))
            num_gender = len(column_types.get("gender", []))
            
            # Tính missing values
            missing_count = df.isna().sum().sum()
            missing_pct = missing_count / (num_rows * num_cols) * 100 if num_rows * num_cols > 0 else 0
            
            # Tạo prompt cho Mistral
            prompt = textwrap.dedent(f"""\
                    As a data analyst, provide a comprehensive summary of this dataset:
                    Dataset Information:
                    - Rows: {num_rows}
                    - Columns: {num_cols}
                    - Numeric columns: {num_numeric}
                    - Categorical columns: {num_categorical}
                    - Datetime columns: {num_datetime}
                    - Binary columns: {num_binary}
                    - Likert scale columns: {num_likert}
                    - Gender columns: {num_gender}
                    - Missing values: {missing_count} ({missing_pct:.1f}% of all values)

                    Provide a concise and informative summary of this dataset that would be useful for someone seeing this data for the first time. 
                    Include information about its structure, completeness, and any initial observations that might be important.
                    Keep your response under 100 words and focus on being informative rather than just repeating the statistics.
                """)
            
            # Generate insight with Mistral
            content = self.mistral.generate(prompt, temperature=0.7, max_tokens=200)
            
            return InsightData(
                id=str(v4()),
                fileId=file_id,
                type=InsightType.SUMMARY,
                title="Dataset Overview",
                content=content.strip(),
                importance=10  # Highest importance
            )
        except Exception as e:
            logger.error(f"Error creating summary insight with Mistral: {str(e)}", exc_info=True)
            return None
    
    def _create_summary_insight(self, df: pd.DataFrame, file_id: Optional[str] = None) -> InsightData:
        """Create summary insight about the dataset"""
        try:
            num_rows, num_cols = df.shape
            
            # Phát hiện các loại cột
            column_types = self.data_processor.get_column_types(df)
            
            # Count column types
            numeric_cols = column_types.get("numeric", [])
            categorical_cols = column_types.get("categorical", [])
            datetime_cols = column_types.get("datetime", [])
            binary_cols = column_types.get("binary", [])
            likert_cols = column_types.get("likert", [])
            gender_cols = column_types.get("gender", [])
            
            # Calculate missing values
            missing_count = df.isna().sum().sum()
            missing_pct = missing_count / (num_rows * num_cols) * 100 if num_rows * num_cols > 0 else 0
            
            # Create summary content
            content = (
                f"This dataset contains {num_rows} rows and {num_cols} columns. "
                f"It has {len(numeric_cols)} numeric columns"
            )
            
            # Add special column types if they exist
            special_types = []
            if len(categorical_cols) > 0:
                special_types.append(f"{len(categorical_cols)} categorical")
            if len(datetime_cols) > 0:
                special_types.append(f"{len(datetime_cols)} datetime")
            if len(binary_cols) > 0:
                special_types.append(f"{len(binary_cols)} binary")
            if len(likert_cols) > 0:
                special_types.append(f"{len(likert_cols)} likert scale")
            if len(gender_cols) > 0:
                special_types.append(f"{len(gender_cols)} gender")
                
            # Join special types with commas
            if special_types:
                content += ", " + ", ".join(special_types) + " columns. "
            else:
                content += ". "
            
            if missing_pct > 0:
                content += f"There are {missing_count} missing values ({missing_pct:.1f}% of all data). "
            else:
                content += "The dataset is complete with no missing values. "
                
            if datetime_cols:
                min_date = df[datetime_cols[0]].min()
                max_date = df[datetime_cols[0]].max()
                if not pd.isna(min_date) and not pd.isna(max_date):
                    content += f"The data spans from {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}."
            
            return InsightData(
                id=str(v4()),
                fileId=file_id,
                type=InsightType.SUMMARY,
                title="Dataset Overview",
                content=content,
                importance=10  # Highest importance
            )
        except Exception as e:
            logger.error(f"Error creating summary insight: {str(e)}")
            return InsightData(
                type=InsightType.SUMMARY,
                title="Dataset Overview",
                content="Could not generate summary statistics for this dataset.",
                importance=5
            )

    def _create_distribution_insights_with_mistral(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Tạo insights về phân phối dữ liệu với Mistral"""
        insights = []
        
        try:
            # Lấy các cột numeric
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            for col in numeric_cols[:3]:  # Giới hạn chỉ 3 cột đầu
                # Chuẩn bị dữ liệu cho Mistral
                summary = self._prepare_column_summary(df, col)
                
                # Tạo prompt cho Mistral
                prompt = textwrap.dedent(f"""\
                        As a data analyst, analyze the distribution of this column:
                        {summary}
                        Provide 1-2 key insights about the distribution of this variable.
                        Focus on skewness, normality, modality, and what the distribution tells us about the data.
                        Make the insights specific and informative.
                        Keep your response under 100 words.
                        """)
                
                # Generate insight with Mistral
                content = self.mistral.generate(prompt, temperature=0.7, max_tokens=150)
                
                # Đánh giá importance dựa trên đặc trưng phân phối
                skewness = df[col].skew()
                importance = 7  # Default
                
                if abs(skewness) > 1.5:  # Phân phối lệch mạnh
                    importance = 8
                
                # Kiểm tra outliers
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                outlier_count = ((df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)).sum()
                if outlier_count > len(df) * 0.05:  # >5% outliers
                    importance = max(importance, 8)
                
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.DISTRIBUTION,
                    title=f"Distribution Analysis of {col}",
                    content=content.strip(),
                    importance=importance,
                    columns=[col]
                ))
            
            return insights
        except Exception as e:
            logger.error(f"Error creating distribution insights with Mistral: {str(e)}", exc_info=True)
            return []
        
    def _create_distribution_insights(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about distributions of numeric columns"""
        insights = []
        
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            for col in numeric_cols[:3]:  # Limit to top 3 numeric columns
                # Calculate basic statistics
                mean = df[col].mean()
                median = df[col].median()
                std_dev = df[col].std()
                skewness = df[col].skew()
                
                # Determine distribution properties
                distribution_type = "normally distributed"
                if abs(skewness) > 1.0:
                    distribution_type = "right-skewed" if skewness > 0 else "left-skewed"
                
                # Create content
                content = (
                    f"The {col} variable has an average of {mean:.2f} and a median of {median:.2f}. "
                    f"It appears to be {distribution_type} (skewness: {skewness:.2f}). "
                )
                
                # Check for outliers
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                outliers = ((df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)).sum()
                outlier_pct = outliers / len(df) * 100
                
                if outlier_pct > 0:
                    content += f"There are {outliers} outliers ({outlier_pct:.1f}% of the data)."
                else:
                    content += "No significant outliers were detected."
                
                # Create insight with appropriate importance
                importance = 7  # Default importance
                if abs(skewness) > 1.5 or outlier_pct > 5:
                    importance = 8  # Higher importance for unusual distributions
                    
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.DISTRIBUTION,
                    title=f"Distribution of {col}",
                    content=content,
                    importance=importance,
                    columns=[col]
                ))
        except Exception as e:
            logger.error(f"Error creating distribution insights: {str(e)}")
        
        return insights
    
    def _prepare_column_summary(self, df: pd.DataFrame, column: str) -> str:
        """Chuẩn bị tóm tắt về cột cho Mistral"""
        summary = f"Column: {column}\n"
        
        # Xử lý khác nhau dựa trên kiểu dữ liệu
        if is_numeric_dtype(df[column]):
            # Lấy thống kê cơ bản
            stats_df = df[column].describe()
            
            summary += f"Type: numeric\n"
            summary += f"Count: {stats_df['count']}\n"
            summary += f"Mean: {stats_df['mean']}\n"
            summary += f"Std: {stats_df['std']}\n"
            summary += f"Min: {stats_df['min']}\n"
            summary += f"25%: {stats_df['25%']}\n"
            summary += f"Median: {stats_df['50%']}\n"
            summary += f"75%: {stats_df['75%']}\n"
            summary += f"Max: {stats_df['max']}\n"
            
            # Thống kê bổ sung
            skewness = df[column].skew()
            kurtosis = df[column].kurtosis()
            
            summary += f"Skewness: {skewness}\n"
            summary += f"Kurtosis: {kurtosis}\n"
            
            # Kiểm tra tính normal
            try:
                _, p_value = stats.normaltest(df[column].dropna())
                summary += f"Normality test p-value: {p_value}\n"
            except:
                pass
            
        elif is_datetime64_any_dtype(df[column]):
            # Cột datetime
            summary += f"Type: datetime\n"
            summary += f"Earliest: {df[column].min()}\n"
            summary += f"Latest: {df[column].max()}\n"
            summary += f"Range (days): {(df[column].max() - df[column].min()).days}\n"
            
        else:
            # Categorical hoặc text
            summary += f"Type: categorical/text\n"
            summary += f"Unique values: {df[column].nunique()}\n"
            
            # Giá trị phổ biến nhất
            top_values = df[column].value_counts().head(5)
            summary += "Top values:\n"
            for val, count in top_values.items():
                summary += f"  {val}: {count} ({count/len(df)*100:.1f}%)\n"
        
        return summary

    def _create_correlation_insights_with_mistral(
        self, df: pd.DataFrame, correlation_threshold: float, file_id: Optional[str] = None
    ) -> List[InsightData]:
        """Tạo insights về tương quan với Mistral"""
        insights = []
        
        try:
            # Lấy các cột numeric
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            # Nếu không đủ cột numeric để tính tương quan
            if len(numeric_cols) < 2:
                return insights
                
            # Tính ma trận tương quan
            corr_matrix = df[numeric_cols].corr()
            
            # Tìm các cặp có tương quan mạnh
            strong_corrs = []
            
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    if i < j:  # Chỉ xét nửa trên của ma trận
                        corr = corr_matrix.iloc[i, j]
                        if abs(corr) >= correlation_threshold:
                            strong_corrs.append((col1, col2, corr))
            
            # Nếu không có tương quan mạnh
            if not strong_corrs:
                return insights
                
            # Sắp xếp theo độ mạnh của tương quan
            strong_corrs = sorted(strong_corrs, key=lambda x: abs(x[2]), reverse=True)
            
            # Chỉ lấy top 3 tương quan mạnh nhất
            for i, (col1, col2, corr) in enumerate(strong_corrs[:3]):
                # Chuẩn bị dữ liệu cho Mistral
                corr_type = "positive" if corr > 0 else "negative"
                
                # Lấy thêm thống kê cho 2 cột
                col1_stats = df[col1].describe()
                col2_stats = df[col2].describe()
                
                prompt = textwrap.dedent(f"""\
                        As a data analyst, analyze this correlation between two variables:
                        Correlation Information:
                        - Variable 1: {col1} (mean: {col1_stats['mean']}, min: {col1_stats['min']}, max: {col1_stats['max']})
                        - Variable 2: {col2} (mean: {col2_stats['mean']}, min: {col2_stats['min']}, max: {col2_stats['max']})
                        - Correlation Coefficient: {corr:.4f} ({corr_type})
                        Provide a meaningful insight about this correlation. Explain what this relationship might indicate and any potential implications.
                        Focus on being specific and informative rather than general statements.
                        Keep your response under 100 words.
                        """)
                
                # Generate insight with Mistral
                content = self.mistral.generate(prompt, temperature=0.7, max_tokens=150)
                
                # Đánh giá importance dựa trên độ mạnh của tương quan
                importance = min(9, int(abs(corr) * 10))
                
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.CORRELATION,
                    title=f"Correlation between {col1} and {col2}",
                    content=content.strip(),
                    importance=importance,
                    columns=[col1, col2]
                ))
            
            return insights
        except Exception as e:
            logger.error(f"Error creating correlation insights with Mistral: {str(e)}", exc_info=True)
            return []
        
    def _create_correlation_insights(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about correlations between numeric columns"""
        insights = []
        
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            # Need at least 2 numeric columns for correlations
            if len(numeric_cols) < 2:
                return insights
                
            # Calculate correlation matrix
            corr_matrix = df[numeric_cols].corr()
            
            # Find pairs with strong correlations
            strong_correlations = []
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    if i < j:  # Only check upper triangle of matrix
                        corr = corr_matrix.loc[col1, col2]
                        if abs(corr) >= 0.7:  # Strong correlation threshold
                            strong_correlations.append((col1, col2, corr))
            
            # Sort by correlation strength
            strong_correlations.sort(key=lambda x: abs(x[2]), reverse=True)
            
            # Create insights for top 3 strongest correlations
            for col1, col2, corr in strong_correlations[:3]:
                corr_type = "positive" if corr > 0 else "negative"
                
                content = (
                    f"There is a strong {corr_type} correlation ({corr:.2f}) between {col1} and {col2}. "
                    f"This means that as {col1} {'increases' if corr > 0 else 'decreases'}, "
                    f"{col2} tends to {'increase' if corr > 0 else 'decrease'} as well."
                )
                
                # Calculate importance based on correlation strength
                importance = min(9, int(abs(corr) * 10))
                
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.CORRELATION,
                    title=f"Correlation between {col1} and {col2}",
                    content=content,
                    importance=importance,
                    columns=[col1, col2]
                ))
        except Exception as e:
            logger.error(f"Error creating correlation insights: {str(e)}")
        
        return insights

    def _create_trend_insights_with_mistral(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Tạo insights về xu hướng thời gian với Mistral"""
        insights = []
        
        try:
            # Tìm các cột datetime
            datetime_cols = [col for col in df.columns if is_datetime64_any_dtype(df[col])]
            
            # Nếu không có cột datetime
            if not datetime_cols:
                return insights
                
            # Lấy các cột numeric
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            for dt_col in datetime_cols[:1]:  # Chỉ dùng cột datetime đầu tiên
                # Sắp xếp theo thời gian
                df_sorted = df.sort_values(by=dt_col)
                
                for num_col in numeric_cols[:2]:  # Chỉ xét 2 cột numeric đầu tiên
                    # Kiểm tra xem có đủ dữ liệu không NA không
                    valid_data = df_sorted[[dt_col, num_col]].dropna()
                    if len(valid_data) < 10:
                        continue
                        
                    # Tính trung bình trượt (nếu có đủ dữ liệu)
                    if len(valid_data) >= 20:
                        # Chia thành 4 phần để xem xu hướng
                        chunk_size = len(valid_data) // 4
                        chunks = [
                            valid_data[num_col].iloc[i:i+chunk_size].mean() 
                            for i in range(0, len(valid_data), chunk_size)
                        ]
                        
                        # Chuẩn bị dữ liệu cho Mistral
                        earliest_date = valid_data[dt_col].min()
                        latest_date = valid_data[dt_col].max()
                        date_range = (latest_date - earliest_date).days
                        
                        values_info = {
                            "First Quarter": float(chunks[0]) if len(chunks) > 0 else None,
                            "Second Quarter": float(chunks[1]) if len(chunks) > 1 else None,
                            "Third Quarter": float(chunks[2]) if len(chunks) > 2 else None,
                            "Fourth Quarter": float(chunks[3]) if len(chunks) > 3 else None
                        }
                        
                        trend_direction = "unknown"
                        if len(chunks) >= 2:
                            if chunks[-1] > chunks[0] * 1.1:
                                trend_direction = "increasing"
                                pct_change = (chunks[-1] / chunks[0] - 1) * 100
                            elif chunks[-1] < chunks[0] * 0.9:
                                trend_direction = "decreasing"
                                pct_change = (1 - chunks[-1] / chunks[0]) * 100
                            else:
                                trend_direction = "stable"
                                pct_change = abs(chunks[-1] / chunks[0] - 1) * 100
                        
                        prompt = textwrap.dedent(f"""\
                                As a data analyst, analyze this time series data:
                                Time Series Information:
                                - Variable: {num_col}
                                - Time Period: From {earliest_date} to {latest_date} ({date_range} days)
                                - Observed Trend: {trend_direction.capitalize()}
                                Average Values by Quarter:
                                - First Quarter: {values_info['First Quarter']}
                                - Second Quarter: {values_info['Second Quarter']}
                                - Third Quarter: {values_info['Third Quarter']}
                                - Fourth Quarter: {values_info['Fourth Quarter']}
                                Provide an insightful analysis of this time series data. Identify patterns, trends, or anomalies.
                                Explain what these changes might indicate and any potential implications.
                                Keep your response under 100 words.
                            """)
                        
                        # Generate insight with Mistral
                        content = self.mistral.generate(prompt, temperature=0.7, max_tokens=150)
                        
                        # Đánh giá importance dựa trên mức độ thay đổi
                        importance = 7  # Default
                        
                        if trend_direction in ["increasing", "decreasing"] and pct_change > 50:
                            importance = 9  # Thay đổi lớn
                        elif trend_direction in ["increasing", "decreasing"] and pct_change > 20:
                            importance = 8  # Thay đổi đáng kể
                        
                        insights.append(InsightData(
                            id=str(v4()),
                            fileId=file_id,
                            type=InsightType.TREND,
                            title=f"Trend Analysis of {num_col} over Time",
                            content=content.strip(),
                            importance=importance,
                            columns=[dt_col, num_col]
                        ))
            
            return insights
        except Exception as e:
            logger.error(f"Error creating trend insights with Mistral: {str(e)}", exc_info=True)
            return []
    
    def _create_trend_insights(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about trends in time series data"""
        insights = []
        
        try:
            # Find id columns
            id_columns = self._detect_id_columns(df)

            # Find datetime columns
            datetime_cols = self._detect_datetime_columns(df)

            skip_columns = set(id_columns) | set(datetime_cols)

            # Need at least one datetime column
            if not datetime_cols:
                return insights
                
            # Get numeric columns
            numeric_cols = [col for col in df.select_dtypes(include=['number']).columns if col not in skip_columns]

            # For the first datetime column
            dt_col = datetime_cols[0]
            
            # Check trends for up to 2 numeric columns
            for num_col in numeric_cols[:2]:
                # Sort data by datetime
                df_sorted = df.sort_values(by=dt_col)
                
                # Check if we have enough data
                if len(df_sorted) < 10:
                    continue
                    
                # Compare first half to second half to detect trend
                first_half = df_sorted[num_col].iloc[:len(df_sorted)//2].mean()
                second_half = df_sorted[num_col].iloc[len(df_sorted)//2:].mean()
                
                # Calculate percent change
                pct_change = ((second_half - first_half) / first_half * 100) if first_half != 0 else 0
                
                # Determine trend direction
                if abs(pct_change) < 5:
                    trend = "stable"
                elif pct_change > 0:
                    trend = "increasing"
                else:
                    trend = "decreasing"


                # Create content
                content = f"The {num_col} shows a {trend} trend over time. "
                # Lấy earliest_date và latest_date
                earliest_date = df_sorted[dt_col].iloc[0]
                latest_date = df_sorted[dt_col].iloc[-1]

                date_part = "Over the analyzed time period, "
                
                if pd.notna(earliest_date) and pd.notna(latest_date):
                    try:
                        date_part = f"From {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}, "
                    except Exception:
                        pass
                
                content += date_part
                
                if trend == "stable":
                    content += "there was no significant change in values."
                else:
                    content += f"there was a {abs(pct_change):.1f}% {trend} trend."
                
                # Determine importance based on change magnitude
                importance = 7  # Default
                if abs(pct_change) > 50:
                    importance = 9  # Major change
                elif abs(pct_change) > 20:
                    importance = 8  # Significant change
                
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.TREND,
                    title=f"Trend in {num_col} over Time",
                    content=content,
                    importance=importance,
                    columns=[dt_col, num_col]
                ))
        except Exception as e:
            logger.error(f"Error creating trend insights: {str(e)}")
        
        return insights

    def _detect_id_columns(self, df: pd.DataFrame, threshold: float = 0.8) -> List[str]:
        """
        Detect ID columns based on heuristics
        
        Args:
            df: Original DataFrame
            threshold: Threshold ratio of unique values to identify ID
            
        Returns:
            List[str]: List of ID columns
        """
        id_columns = []
        
        # Based on column names
        id_patterns = ['id', 'uuid', 'guid', 'key', 'code', 'sku', '_id', 'index']
        pattern_cols = [col for col in df.columns 
                      if any(pattern in col.lower() for pattern in id_patterns)]
        
        # Based on unique value ratio
        for col in df.columns:
            n_unique = df[col].nunique()
            n_rows = len(df)
            unique_ratio = n_unique / n_rows if n_rows > 0 else 0
            
            # If numeric column with high unique ratio
            if is_numeric_dtype(df[col]) and unique_ratio > threshold:
                id_columns.append(col)
            # If string column with ID pattern and high unique ratio
            elif col in pattern_cols and unique_ratio > threshold * 0.8:
                id_columns.append(col)
            # If column has extremely high unique ratio
            elif unique_ratio > 0.95 and n_rows > 100:
                id_columns.append(col)
                
        return list(set(id_columns))
    
    def _detect_datetime_columns(self, df: pd.DataFrame) -> List[str]:
        return detect_datetime_columns(df)

    def _create_outlier_insights_with_mistral(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Tạo insights về outliers với Mistral"""
        insights = []
        
        try:
            # Lấy các cột numeric
            numeric_cols = df.select_dtypes(include=['number']).columns
            
            for col in numeric_cols:
                # Kiểm tra xem có đủ dữ liệu không NA không
                non_na = df[col].dropna()
                if len(non_na) < 10:
                    continue
                    
                # Tính IQR (Interquartile Range)
                Q1 = non_na.quantile(0.25)
                Q3 = non_na.quantile(0.75)
                IQR = Q3 - Q1
                
                # Xác định outliers
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers_low = non_na[non_na < lower_bound]
                outliers_high = non_na[non_na > upper_bound]
                
                # Tổng số outliers
                total_outliers = len(outliers_low) + len(outliers_high)
                outlier_pct = total_outliers / len(non_na) * 100
                
                # Nếu có outliers đáng kể
                if total_outliers > 0 and outlier_pct > 1.0:
                    # Chuẩn bị dữ liệu cho Mistral
                    outlier_info = {
                        "total": total_outliers,
                        "percentage": outlier_pct,
                        "low_count": len(outliers_low),
                        "high_count": len(outliers_high),
                        "low_bound": float(lower_bound),
                        "upper_bound": float(upper_bound)
                    }
                    
                    # Thêm thông tin về các outliers
                    if len(outliers_low) > 0:
                        outlier_info["min_outlier"] = float(outliers_low.min())
                        outlier_info["low_examples"] = [float(x) for x in outliers_low.head(3).values]
                        
                    if len(outliers_high) > 0:
                        outlier_info["max_outlier"] = float(outliers_high.max())
                        outlier_info["high_examples"] = [float(x) for x in outliers_high.head(3).values]
                    
                    prompt = textwrap.dedent(f"""\
                            As a data analyst, analyze these outliers in the data:
                            Column: {col}
                            Outlier Information:
                            - Total outliers: {outlier_info['total']} ({outlier_info['percentage']:.1f}% of values)
                            - Lower bound: {outlier_info['low_bound']}
                            - Upper bound: {outlier_info['upper_bound']}
                            - Low outliers: {outlier_info['low_count']}
                            - High outliers: {outlier_info['high_count']}
                            {f"Extreme low values: {outlier_info.get('low_examples', [])}" if outlier_info.get('low_count', 0) > 0 else ""}
                            {f"Extreme high values: {outlier_info.get('high_examples', [])}" if outlier_info.get('high_count', 0) > 0 else ""}
                            Provide an insight about these outliers. What might they represent? How should they be interpreted or handled?
                            Keep your response under 100 words.
                        """)
                    
                    # Generate insight with Mistral
                    content = self.mistral.generate(prompt, temperature=0.7, max_tokens=150)
                    
                    # Đánh giá importance dựa trên phần trăm outliers
                    importance = min(8, 5 + int(outlier_pct / 2))
                    
                    insights.append(InsightData(
                        id=str(v4()),
                        fileId=file_id,
                        type=InsightType.OUTLIER,
                        title=f"Outliers in {col}",
                        content=content.strip(),
                        importance=importance,
                        columns=[col]
                    ))
            
            return insights
        except Exception as e:
            logger.error(f"Error creating outlier insights with Mistral: {str(e)}", exc_info=True)
            return []
        
    def _create_outlier_insights(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about outliers in numeric data"""
        insights = []
        
        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            
            for col in numeric_cols:
                # Check for valid data
                valid_data = df[col].dropna()
                if len(valid_data) < 10:
                    continue
                    
                # Calculate IQR
                q1 = valid_data.quantile(0.25)
                q3 = valid_data.quantile(0.75)
                iqr = q3 - q1
                
                # Define outlier thresholds
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                # Find outliers
                low_outliers = valid_data[valid_data < lower_bound]
                high_outliers = valid_data[valid_data > upper_bound]
                total_outliers = len(low_outliers) + len(high_outliers)
                
                # Only create insight if there are significant outliers
                if total_outliers > 0 and (total_outliers / len(valid_data)) > 0.01:  # More than 1% are outliers
                    outlier_pct = total_outliers / len(valid_data) * 100
                    
                    content = (
                        f"The {col} variable has {total_outliers} outliers ({outlier_pct:.1f}% of data). "
                        f"There are {len(low_outliers)} values below {lower_bound:.2f} "
                        f"and {len(high_outliers)} values above {upper_bound:.2f}. "
                    )
                    
                    if len(high_outliers) > 0:
                        content += f"The highest outlier is {high_outliers.max():.2f}. "
                        
                    if len(low_outliers) > 0:
                        content += f"The lowest outlier is {low_outliers.min():.2f}."
                    
                    # Determine importance based on percentage of outliers
                    importance = min(8, 5 + int(outlier_pct / 2))
                    
                    insights.append(InsightData(
                        id=str(v4()),
                        fileId=file_id,
                        type=InsightType.OUTLIER,
                        title=f"Outliers in {col}",
                        content=content,
                        importance=importance,
                        columns=[col]
                    ))
        except Exception as e:
            logger.error(f"Error creating outlier insights: {str(e)}")
        
        return insights

    def _create_pattern_insights_with_mistral(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Tạo insights về mẫu và giá trị phổ biến với Mistral"""
        insights = []
        
        try:
            # Kiểm tra cho categorical
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            
            for col in categorical_cols:
                # Kiểm tra xem có đủ dữ liệu không NA không
                non_na = df[col].dropna()
                if len(non_na) < 10:
                    continue
                    
                # Tính tần suất
                value_counts = non_na.value_counts()
                
                # Kiểm tra xem có nhiều giá trị phổ biến không
                if len(value_counts) >= 3:
                    # Tính tỷ lệ top 3
                    top3_count = value_counts.iloc[:3].sum()
                    top3_pct = top3_count / len(non_na) * 100
                    
                    if top3_pct > 60:  # Nếu top 3 chiếm >60%
                        # Chuẩn bị dữ liệu cho Mistral
                        top_values = []
                        for i, (val, count) in enumerate(value_counts.iloc[:5].items()):
                            top_values.append({
                                "value": str(val),
                                "count": int(count),
                                "percentage": float(count / len(non_na) * 100)
                            })
                        
                        prompt = textwrap.dedent(f"""\
                                As a data analyst, analyze the distribution of values in this categorical column:
                                Column: {col}
                                Total Unique Values: {value_counts.shape[0]}
                                Total Values: {len(non_na)}
                                Top Values:
                                1. {top_values[0]['value']}: {top_values[0]['count']} ({top_values[0]['percentage']:.1f}%)
                                2. {top_values[1]['value']}: {top_values[1]['count']} ({top_values[1]['percentage']:.1f}%)
                                3. {top_values[2]['value']}: {top_values[2]['count']} ({top_values[2]['percentage']:.1f}%)
                                {f"4. {top_values[3]['value']}: {top_values[3]['count']} ({top_values[3]['percentage']:.1f}%)" if len(top_values) > 3 else ""}
                                {f"5. {top_values[4]['value']}: {top_values[4]['count']} ({top_values[4]['percentage']:.1f}%)" if len(top_values) > 4 else ""}
                                Top 3 values account for {top3_pct:.1f}% of all values.
                                Provide an insight about the distribution of values in this column. What patterns or imbalances do you observe?
                                What might this distribution tell us about the data?
                                Keep your response under 100 words.
                            """)
                        
                        # Generate insight with Mistral
                        content = self.mistral.generate(prompt, temperature=0.7, max_tokens=150)
                        
                        # Đánh giá importance dựa trên mức độ tập trung
                        importance = 6  # Default
                        if top3_pct > 90:
                            importance = 8  # Rất tập trung
                        elif top3_pct > 75:
                            importance = 7  # Khá tập trung
                        
                        insights.append(InsightData(
                            id=str(v4()),
                            fileId=file_id,
                            type=InsightType.PATTERN,
                            title=f"Distribution Pattern in {col}",
                            content=content.strip(),
                            importance=importance,
                            columns=[col]
                        ))
            
            return insights
        except Exception as e:
            logger.error(f"Error creating pattern insights with Mistral: {str(e)}", exc_info=True)
            return []
            
    
    def _create_pattern_insights(self, df: pd.DataFrame, file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about patterns in categorical data"""
        insights = []
        
        try:
            # Get categorical columns
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            for col in categorical_cols:
                # Check for valid data
                valid_data = df[col].dropna()
                if len(valid_data) < 10:
                    continue
                    
                # Calculate value counts
                value_counts = valid_data.value_counts()
                total_count = len(valid_data)
                
                # Only proceed if there are at least 3 categories
                if len(value_counts) >= 3:
                    # Calculate percentage of top categories
                    top3_values = value_counts.head(3)
                    top3_pct = (top3_values.sum() / total_count) * 100
                    
                    # Create insight for categories with significant patterns
                    if top3_pct > 60:  # Top 3 make up more than 60%
                        content = f"The top 3 values in {col} account for {top3_pct:.1f}% of all data: "
                        
                        # Add details about top categories
                        for i, (value, count) in enumerate(top3_values.items()):
                            pct = (count / total_count) * 100
                            content += f"'{value}' ({pct:.1f}%)"
                            if i < len(top3_values) - 1:
                                content += ", "
                        content += "."
                        
                        # Add diversity info
                        if len(value_counts) > 10:
                            content += f" There are {len(value_counts)} unique values in total."
                        
                        # Calculate importance based on concentration
                        importance = 6  # Default
                        if top3_pct > 90:
                            importance = 8  # Very concentrated
                        elif top3_pct > 75:
                            importance = 7  # Moderately concentrated
                        
                        insights.append(InsightData(
                            id=str(v4()),
                            fileId=file_id,
                            type=InsightType.PATTERN,
                            title=f"Value Distribution in {col}",
                            content=content,
                            importance=importance,
                            columns=[col]
                        ))
        except Exception as e:
            logger.error(f"Error creating pattern insights: {str(e)}")
        
        return insights

    def _generate_comprehensive_insights(
        self, 
        df: pd.DataFrame, 
        insight_types: Optional[List[str]] = None,
        file_id: Optional[str] = None
    ) -> List[InsightData]:
        """Tạo comprehensive insights với Mistral"""
        insights = []
        
        try:
            # Chuẩn bị tóm tắt dataset
            summary = self._prepare_dataset_summary(df)
            
            # Phát hiện loại insight cần tạo
            if insight_types:
                insight_types_str = ", ".join(insight_types)
                type_filter = f"Focus specifically on generating insights related to: {insight_types_str}."
            else:
                type_filter = "Provide a balanced set of insights covering different aspects of the data."
            
            # Tạo prompt cho Mistral
            prompt = textwrap.dedent(f"""\
                    As a data analyst, analyze the following dataset summary and provide 3-5 key insights:
                    {summary}
                    {type_filter}
                    For each insight:
                    1. Provide a clear, concise title
                    2. Write a detailed explanation (2-3 sentences)
                    3. Assign an importance score from 1-10, where 10 is most important
                    4. Specify what type of insight it is (distribution, correlation, trend, outlier, pattern, or any other relevant type)
                    5. List the relevant columns
                    Format each insight as:
                    TITLE: [insight title]
                    TYPE: [insight type]
                    IMPORTANCE: [score]
                    COLUMNS: [relevant column names]
                    CONTENT: [detailed explanation]
                """)
            
            # Generate insights
            response = self.mistral.generate(prompt, temperature=0.7, max_tokens=1000)
            
            # Parse kết quả
            insights_raw = response.strip().split("\n\n")
            
            for insight_text in insights_raw:
                try:
                    # Parse insight
                    lines = insight_text.strip().split("\n")
                    
                    title = ""
                    insight_type = InsightType.SUMMARY  # Default
                    importance = 5  # Default
                    columns = []
                    content = ""
                    
                    for line in lines:
                        if line.startswith("TITLE:"):
                            title = line[6:].strip()
                        elif line.startswith("TYPE:"):
                            type_str = line[5:].strip().upper()
                            # Map to InsightType
                            if "DISTRIBUTION" in type_str:
                                insight_type = InsightType.DISTRIBUTION
                            elif "CORRELATION" in type_str:
                                insight_type = InsightType.CORRELATION
                            elif "TREND" in type_str:
                                insight_type = InsightType.TREND
                            elif "OUTLIER" in type_str:
                                insight_type = InsightType.OUTLIER
                            elif "PATTERN" in type_str:
                                insight_type = InsightType.PATTERN
                            elif "BINARY" in type_str:
                                insight_type = InsightType.BINARY
                            elif "LIKERT" in type_str:
                                insight_type = InsightType.LIKERT
                            elif "GENDER" in type_str:
                                insight_type = InsightType.GENDER
                            elif "RANGE" in type_str:
                                insight_type = InsightType.RANGE
                            elif "TEXT" in type_str:
                                insight_type = InsightType.TEXT
                            else:
                                insight_type = InsightType.SUMMARY
                        elif line.startswith("IMPORTANCE:"):
                            try:
                                importance_value = int(line[11:].strip())
                                importance = max(1, min(10, importance_value))
                            except:
                                importance = 5
                        elif line.startswith("COLUMNS:"):
                            columns_str = line[8:].strip()
                            columns = [col.strip() for col in columns_str.split(",")]
                        elif line.startswith("CONTENT:"):
                            content = line[8:].strip()
                    
                    # Chỉ thêm nếu có title và content
                    if title and content:
                        insights.append(InsightData(
                            id=str(v4()),
                            fileId=file_id,
                            type=insight_type,
                            title=title,
                            content=content,
                            importance=importance,
                            columns=columns
                        ))
                except Exception as e:
                    logger.error(f"Error parsing insight: {str(e)}")
                    continue
            
            return insights
        except Exception as e:
            logger.error(f"Error generating comprehensive insights: {str(e)}", exc_info=True)
            return []
    
    def _prepare_dataset_summary(self, df: pd.DataFrame) -> str:
        """Chuẩn bị tóm tắt về dataset cho Mistral"""
        summary = f"Dataset Summary:\n"
        summary += f"- Rows: {len(df)}\n"
        summary += f"- Columns: {len(df.columns)}\n\n"
        
        # Phát hiện các loại cột
        column_types = self.data_processor.get_column_types(df)
        
        # Numeric columns
        numeric_cols = column_types.get("numeric", [])
        if len(numeric_cols) > 0:
            summary += f"Numeric Columns ({len(numeric_cols)}):\n"
            for col in numeric_cols[:5]:  # Giới hạn 5 cột
                stats = df[col].describe()
                summary += f"  - {col}: Mean={stats['mean']:.2f}, Median={stats['50%']:.2f}, Min={stats['min']:.2f}, Max={stats['max']:.2f}\n"
            if len(numeric_cols) > 5:
                summary += f"  - ... and {len(numeric_cols) - 5} more numeric columns\n"
            summary += "\n"
        
        # Categorical columns
        cat_cols = column_types.get("categorical", [])
        if len(cat_cols) > 0:
            summary += f"Categorical Columns ({len(cat_cols)}):\n"
            for col in cat_cols[:5]:  # Giới hạn 5 cột
                n_unique = df[col].nunique()
                top_val = df[col].value_counts().index[0] if n_unique > 0 else "N/A"
                top_pct = df[col].value_counts().iloc[0] / len(df) * 100 if n_unique > 0 else 0
                summary += f"  - {col}: {n_unique} unique values, most common: '{top_val}' ({top_pct:.1f}%)\n"
            if len(cat_cols) > 5:
                summary += f"  - ... and {len(cat_cols) - 5} more categorical columns\n"
            summary += "\n"
        
        # Binary columns
        binary_cols = column_types.get("binary", [])
        if len(binary_cols) > 0:
            summary += f"Binary Columns ({len(binary_cols)}):\n"
            for col in binary_cols[:5]:
                value_counts = df[col].value_counts()
                if len(value_counts) >= 1:
                    most_common = value_counts.index[0]
                    most_common_pct = value_counts.iloc[0] / len(df) * 100
                    summary += f"  - {col}: most common: '{most_common}' ({most_common_pct:.1f}%)\n"
            if len(binary_cols) > 5:
                summary += f"  - ... and {len(binary_cols) - 5} more binary columns\n"
            summary += "\n"
            
        # Likert scale columns
        likert_cols = column_types.get("likert", [])
        if len(likert_cols) > 0:
            summary += f"Likert Scale Columns ({len(likert_cols)}):\n"
            for col in likert_cols[:3]:
                min_val = df[col].min()
                max_val = df[col].max()
                avg_val = df[col].mean()
                summary += f"  - {col}: Range {min_val}-{max_val}, Average rating: {avg_val:.2f}\n"
            if len(likert_cols) > 3:
                summary += f"  - ... and {len(likert_cols) - 3} more likert scale columns\n"
            summary += "\n"
            
        # Datetime columns
        dt_cols = column_types.get("datetime", [])
        if len(dt_cols) > 0:
            summary += f"Datetime Columns ({len(dt_cols)}):\n"
            for col in dt_cols:
                min_date = df[col].min()
                max_date = df[col].max()
                summary += f"  - {col}: Range from {min_date} to {max_date}\n"
            summary += "\n"
        
        # Other special columns
        special_cols = {
            "gender": "Gender",
            "email": "Email",
            "phone": "Phone",
            "address": "Address",
            "name": "Name",
            "url": "URL",
            "range": "Range",
            "text": "Text"
        }
        
        for col_type, type_name in special_cols.items():
            cols = column_types.get(col_type, [])
            if cols:
                summary += f"{type_name} Columns ({len(cols)}):\n"
                for col in cols[:2]:
                    summary += f"  - {col}\n"
                if len(cols) > 2:
                    summary += f"  - ... and {len(cols) - 2} more {col_type} columns\n"
                summary += "\n"
        
        # Correlation information
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            # Tìm tương quan mạnh
            strong_corrs = []
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    if i < j and abs(corr_matrix.loc[col1, col2]) > 0.7:
                        strong_corrs.append((col1, col2, corr_matrix.loc[col1, col2]))
            
            if strong_corrs:
                summary += "Strong Correlations:\n"
                for col1, col2, corr in strong_corrs[:3]:  # Giới hạn top 3
                    corr_type = "positive" if corr > 0 else "negative"
                    summary += f"  - {col1} and {col2}: {corr_type} correlation ({corr:.2f})\n"
                if len(strong_corrs) > 3:
                    summary += f"  - ... and {len(strong_corrs) - 3} more strong correlations\n"
                summary += "\n"
        
        return summary
        
    # Các phương thức mới để tạo insights cho các loại cột đặc biệt
    
    def _create_binary_insights(self, df: pd.DataFrame, binary_cols: List[str], file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about binary columns"""
        insights = []
        
        try:
            for col in binary_cols:
                if col not in df.columns:
                    continue
                    
                # Get value counts
                value_counts = df[col].value_counts(dropna=True)
                if len(value_counts) != 2:  # Đảm bảo đúng là binary (2 giá trị)
                    continue
                    
                total_count = value_counts.sum()
                
                # Calculate percentages
                value1, count1 = value_counts.index[0], value_counts.iloc[0]
                value2, count2 = value_counts.index[1], value_counts.iloc[1]
                
                pct1 = count1 / total_count * 100
                pct2 = count2 / total_count * 100
                
                # Detect imbalance
                imbalance = abs(pct1 - pct2)
                
                # Create content based on imbalance level
                if imbalance > 40:  # Highly imbalanced
                    majority = value1 if count1 > count2 else value2
                    minority = value2 if count1 > count2 else value1
                    majority_pct = max(pct1, pct2)
                    
                    content = (
                        f"The {col} variable shows a strong imbalance with '{majority}' representing "
                        f"{majority_pct:.1f}% of all values. This significant imbalance may indicate "
                        f"a potential bias in the data collection or a natural class distribution."
                    )
                    
                    importance = min(8, 5 + int(imbalance / 10))
                    
                    insights.append(InsightData(
                        id=str(v4()),
                        fileId=file_id,
                        type=InsightType.PATTERN,
                        title=f"Imbalance in {col}",
                        content=content,
                        importance=importance,
                        columns=[col]
                    ))
                else:  # Relatively balanced
                    content = (
                        f"The {col} variable has a relatively balanced distribution with "
                        f"'{value1}' at {pct1:.1f}% and '{value2}' at {pct2:.1f}%."
                    )
                    
                    importance = 5  # Lower importance for balanced distributions
                    
                    insights.append(InsightData(
                        id=str(v4()),
                        fileId=file_id,
                        type=InsightType.PATTERN,
                        title=f"Distribution of {col}",
                        content=content,
                        importance=importance,
                        columns=[col]
                    ))
                    
        except Exception as e:
            logger.error(f"Error creating binary insights: {str(e)}")
            
        return insights
        
    def _create_likert_insights(self, df: pd.DataFrame, likert_cols: List[str], file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about Likert scale columns"""
        insights = []
        
        try:
            for col in likert_cols:
                if col not in df.columns:
                    continue
                    
                # Get basic statistics
                valid_values = df[col].dropna()
                if len(valid_values) < 10:
                    continue
                    
                min_val = valid_values.min()
                max_val = valid_values.max()
                mean_val = valid_values.mean()
                median_val = valid_values.median()
                
                # Get distribution
                value_counts = valid_values.value_counts(normalize=True).sort_index() * 100
                
                # Detect if responses are skewed to high or low values
                if mean_val > (max_val + min_val) * 0.6 / (max_val - min_val):
                    # Positively skewed (higher ratings)
                    content = (
                        f"Responses for {col} are generally positive with an average rating of {mean_val:.2f} "
                        f"on a scale from {min_val} to {max_val}. "
                        f"The most common response was {value_counts.idxmax()} ({value_counts.max():.1f}% of responses)."
                    )
                    title = f"Positive Ratings in {col}"
                elif mean_val < (max_val + min_val) * 0.4 / (max_val - min_val):
                    # Negatively skewed (lower ratings)
                    content = (
                        f"Responses for {col} tend to be negative with an average rating of {mean_val:.2f} "
                        f"on a scale from {min_val} to {max_val}. "
                        f"The most common response was {value_counts.idxmax()} ({value_counts.max():.1f}% of responses)."
                    )
                    title = f"Negative Ratings in {col}"
                else:
                    # Neutral or balanced
                    content = (
                        f"Responses for {col} are relatively balanced with an average rating of {mean_val:.2f} "
                        f"on a scale from {min_val} to {max_val}. "
                        f"The most common response was {value_counts.idxmax()} ({value_counts.max():.1f}% of responses)."
                    )
                    title = f"Balanced Ratings in {col}"
                
                # Calculate importance based on how extreme the mean is
                deviation_from_center = abs(mean_val - (min_val + max_val) / 2) / ((max_val - min_val) / 2)
                importance = min(8, 5 + int(deviation_from_center * 5))
                
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.PATTERN,
                    title=title,
                    content=content,
                    importance=importance,
                    columns=[col]
                ))
                
                # Check for polarized responses (high at both extremes)
                extremes_pct = value_counts.iloc[0] + value_counts.iloc[-1]
                middle_pct = value_counts.iloc[1:-1].sum()
                
                if extremes_pct > middle_pct and extremes_pct > 50:
                    polarization_content = (
                        f"The responses for {col} show polarization, with {extremes_pct:.1f}% of responses "
                        f"at the extreme values ({min_val} and {max_val}). This suggests divided opinions "
                        f"or experiences among respondents."
                    )
                    
                    insights.append(InsightData(
                        id=str(v4()),
                        fileId=file_id,
                        type=InsightType.PATTERN,
                        title=f"Polarized Responses in {col}",
                        content=polarization_content,
                        importance=7,  # Polarization is usually interesting
                        columns=[col]
                    ))
                    
        except Exception as e:
            logger.error(f"Error creating Likert scale insights: {str(e)}")
            
        return insights
        
    def _create_gender_insights(self, df: pd.DataFrame, gender_cols: List[str], file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about gender distributions"""
        insights = []
        
        try:
            for col in gender_cols:
                if col not in df.columns:
                    continue
                    
                # Normalize to lowercase for consistency
                gender_values = df[col].astype(str).str.lower()
                
                # Define common gender terms
                male_terms = {'male', 'm', 'man', 'men', 'boy', 'nam', 'masculine'}
                female_terms = {'female', 'f', 'woman', 'women', 'girl', 'nữ', 'feminine'}
                other_terms = {'other', 'non-binary', 'nonbinary', 'n/a', 'prefer not to say', 'khác'}
                
                # Count occurrences
                male_count = sum(gender_values.isin(male_terms))
                female_count = sum(gender_values.isin(female_terms))
                other_count = sum(gender_values.isin(other_terms))
                
                total_identified = male_count + female_count + other_count
                
                # Calculate percentages
                if total_identified > 0:
                    male_pct = male_count / total_identified * 100
                    female_pct = female_count / total_identified * 100
                    other_pct = other_count / total_identified * 100
                    
                    # Check gender balance
                    gender_ratio = male_count / female_count if female_count > 0 else float('inf')
                    
                    if abs(male_pct - female_pct) > 20:  # Significant imbalance
                        dominant_gender = "male" if male_pct > female_pct else "female"
                        content = (
                            f"There is a significant gender imbalance in the {col} column, with "
                            f"{male_pct:.1f}% male and {female_pct:.1f}% female (ratio {gender_ratio:.1f}:1). "
                            f"The data is skewed towards {dominant_gender} participants."
                        )
                        
                        if other_pct > 2:
                            content += f" Additionally, {other_pct:.1f}% of entries are non-binary or other genders."
                        
                        importance = min(8, 5 + int(abs(male_pct - female_pct) / 10))
                        
                        insights.append(InsightData(
                            id=str(v4()),
                            fileId=file_id,
                            type=InsightType.PATTERN,
                            title=f"Gender Imbalance in {col}",
                            content=content,
                            importance=importance,
                            columns=[col]
                        ))
                    else:  # Relatively balanced
                        content = (
                            f"The gender distribution in {col} is relatively balanced with "
                            f"{male_pct:.1f}% male and {female_pct:.1f}% female."
                        )
                        
                        if other_pct > 2:
                            content += f" Additionally, {other_pct:.1f}% of entries are non-binary or other genders."
                        
                        insights.append(InsightData(
                            id=str(v4()),
                            fileId=file_id,
                            type=InsightType.PATTERN,
                            title=f"Gender Distribution in {col}",
                            content=content,
                            importance=5,
                            columns=[col]
                        ))
                        
        except Exception as e:
            logger.error(f"Error creating gender insights: {str(e)}")
            
        return insights
        
    def _get_country_name(self, country_code: str) -> str:
        """Get country name from country code (simple implementation)"""
        country_codes = {
            '1': 'USA/Canada',
            '44': 'UK',
            '49': 'Germany',
            '33': 'France',
            '81': 'Japan',
            '86': 'China',
            '91': 'India',
            '61': 'Australia',
            '55': 'Brazil',
            '7': 'Russia',
            '82': 'South Korea',
            '39': 'Italy',
            '34': 'Spain',
            '52': 'Mexico',
            '971': 'UAE',
            '65': 'Singapore',
            '31': 'Netherlands',
            '48': 'Poland',
            '966': 'Saudi Arabia',
            '46': 'Sweden',
            '41': 'Switzerland',
            '84': 'Vietnam',
            '63': 'Philippines',
            '62': 'Indonesia',
            '60': 'Malaysia',
            '66': 'Thailand',
            '234': 'Nigeria',
            '27': 'South Africa',
            '20': 'Egypt',
            '972': 'Israel'
        }
        return country_codes.get(country_code, 'Unknown')
    
    def _create_range_insights(self, df: pd.DataFrame, range_cols: List[str], file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about range columns"""
        insights = []
        
        try:
            for col in range_cols:
                if col not in df.columns:
                    continue
                    
                # Convert to string for regex
                range_values = df[col].astype(str)
                
                # Extract ranges using regex
                range_pattern = r'(\d+)\s*[-–—]\s*(\d+)'
                ranges = range_values.str.extract(range_pattern)
                
                # Skip if we couldn't extract ranges
                if ranges.empty or ranges[0].isna().all() or ranges[1].isna().all():
                    continue
                    
                # Convert to numeric
                min_vals = pd.to_numeric(ranges[0], errors='coerce')
                max_vals = pd.to_numeric(ranges[1], errors='coerce')
                
                # Calculate range widths
                range_widths = max_vals - min_vals
                
                # Basic statistics
                avg_min = min_vals.mean()
                avg_max = max_vals.mean()
                avg_width = range_widths.mean()
                min_width = range_widths.min()
                max_width = range_widths.max()
                
                # Create range width insight
                width_content = (
                    f"The ranges in the {col} column span from an average minimum of {avg_min:.1f} "
                    f"to an average maximum of {avg_max:.1f}, with an average width of {avg_width:.1f}. "
                )
                
                # Add info about variation in widths
                if max_width > avg_width * 2:
                    width_content += f"There's significant variation in range widths, from {min_width:.1f} to {max_width:.1f}."
                else:
                    width_content += f"Range widths are relatively consistent, with all between {min_width:.1f} and {max_width:.1f}."
                
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.PATTERN,
                    title=f"Range Analysis for {col}",
                    content=width_content,
                    importance=6,
                    columns=[col]
                ))
                
                # If there's a clear pattern in ranges
                if range_widths.std() / avg_width < 0.2 and len(range_widths) >= 10:
                    pattern_content = (
                        f"The ranges in {col} follow a consistent pattern with an average width of {avg_width:.1f} "
                        f"and low variation (CV: {range_widths.std() / avg_width:.2f}). This suggests "
                        f"these ranges represent a standardized measurement or classification system."
                    )
                    
                    insights.append(InsightData(
                        id=str(v4()),
                        fileId=file_id,
                        type=InsightType.PATTERN,
                        title=f"Consistent Range Pattern in {col}",
                        content=pattern_content,
                        importance=7,
                        columns=[col]
                    ))
                        
        except Exception as e:
            logger.error(f"Error creating range insights: {str(e)}")
            
        return insights
        
    def _create_text_insights(self, df: pd.DataFrame, text_cols: List[str], file_id: Optional[str] = None) -> List[InsightData]:
        """Create insights about text columns"""
        insights = []
        
        try:
            for col in text_cols:
                if col not in df.columns:
                    continue
                    
                # Convert to string and analyze
                text_values = df[col].astype(str)
                
                # Get text lengths
                char_lengths = text_values.str.len()
                word_counts = text_values.str.split().str.len()
                
                avg_chars = char_lengths.mean()
                avg_words = word_counts.mean()
                max_chars = char_lengths.max()
                
                # Check for very short texts
                short_texts_pct = (word_counts <= 3).mean() * 100
                
                # Check for very long texts
                long_texts_pct = (word_counts >= 50).mean() * 100
                
                # Create length insight
                length_content = (
                    f"Text in the {col} column averages {avg_chars:.1f} characters and {avg_words:.1f} words per entry. "
                )
                
                if short_texts_pct > 50:
                    length_content += f"Most entries ({short_texts_pct:.1f}%) are very short (3 or fewer words), suggesting brief responses or keywords."
                elif long_texts_pct > 20:
                    length_content += f"A significant portion ({long_texts_pct:.1f}%) are long texts (50+ words), suggesting detailed responses or paragraphs."
                else:
                    length_content += f"Entries are moderate in length, with {short_texts_pct:.1f}% very short and {long_texts_pct:.1f}% very long."
                
                # Set importance based on text variety
                if char_lengths.std() / avg_chars > 1.0:  # High variation
                    importance = 7  # Higher importance for varied text lengths
                else:
                    importance = 5
                
                insights.append(InsightData(
                    id=str(v4()),
                    fileId=file_id,
                    type=InsightType.PATTERN,
                    title=f"Text Length Analysis for {col}",
                    content=length_content,
                    importance=importance,
                    columns=[col]
                ))
                
                # Word frequency analysis (if we have enough text)
                if len(text_values) >= 20 and avg_words >= 5:
                    try:
                        # Combine all text and tokenize
                        all_text = ' '.join(text_values)
                        words = re.findall(r'\b[a-zA-Z0-9_]+\b', all_text.lower())
                        
                        # Filter out common stop words
                        stop_words = {'the', 'a', 'an', 'and', 'is', 'in', 'to', 'of', 'for', 'with', 
                                     'on', 'at', 'this', 'that', 'it', 'as', 'by', 'are', 'was', 'were'}
                        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
                        
                        # Get word frequencies
                        from collections import Counter
                        word_counts = Counter(filtered_words)
                        top_words = word_counts.most_common(5)
                        
                        if top_words:
                            word_content = f"Common words in {col} include: "
                            for i, (word, count) in enumerate(top_words):
                                word_pct = count / len(filtered_words) * 100
                                word_content += f"'{word}' ({word_pct:.1f}%)"
                                if i < len(top_words) - 1:
                                    word_content += ", "
                            
                            word_content += ". These frequent terms may indicate common themes or topics in the text."
                            
                            insights.append(InsightData(
                                id=str(v4()),
                                fileId=file_id,
                                type=InsightType.PATTERN,
                                title=f"Common Words in {col}",
                                content=word_content,
                                importance=6,
                                columns=[col]
                            ))
                    except Exception as word_err:
                        logger.error(f"Error in word frequency analysis: {str(word_err)}")
                        
        except Exception as e:
            logger.error(f"Error creating text insights: {str(e)}")
            
        return insights