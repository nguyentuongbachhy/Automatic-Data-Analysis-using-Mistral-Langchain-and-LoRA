"""
Module chuyên về kiểm tra và đánh giá chất lượng dữ liệu.
Tách riêng khỏi processor để tập trung vào phát hiện vấn đề.
"""

import logging
from typing import Dict, List, Optional, Any
import re
import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from ml.utils.datetime_utils import convert_to_datetime, analyze_datetime_distribution, is_datetime

logger = logging.getLogger(__name__)


class DataValidator:
    """Chuyên về kiểm tra và đánh giá chất lượng dữ liệu"""

    def __init__(self, config: Optional[Dict] = None):
        """Khởi tạo với config tùy chọn"""
        self.config = config or {}
        self.validation_results = {}
        self._validation_cache = {}
        
        self._compile_regex_patterns()
        
        logger.info("DataValidator initialized")
        
    def _compile_regex_patterns(self):
        """Biên dịch trước các regex pattern để tối ưu hiệu suất"""
        self.email_pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
        self.delimiter_pattern = re.compile(r'[,;]')
        self.newline_pattern = re.compile(r'[\n\r]')
        self.json_pattern = re.compile(r'[{].*[}]')

    def validate_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Đánh giá toàn diện chất lượng dữ liệu
        
        Args:
            df: DataFrame cần kiểm tra
            
        Returns:
            Dict: Báo cáo đánh giá chất lượng
        """
        try:
            completeness_results = self._validate_completeness(df)
            consistency_results = self._validate_consistency(df)
            uniqueness_results = self._validate_uniqueness(df)
            integrity_results = self._validate_integrity(df)
            accuracy_results = self._validate_accuracy(df)
            
            quality_metrics = {
                "completeness": completeness_results,
                "consistency": consistency_results,
                "uniqueness": uniqueness_results,
                "integrity": integrity_results,
                "accuracy": accuracy_results,
                "overall_score": 0.0
            }
            
            weights = {
                "completeness": 0.3,
                "consistency": 0.2,
                "uniqueness": 0.2,
                "integrity": 0.2,
                "accuracy": 0.1
            }
            
            scores = np.array([quality_metrics[key]["score"] for key in weights.keys()])
            weights_array = np.array(list(weights.values()))
            overall_score = np.sum(scores * weights_array)
            
            quality_metrics["overall_score"] = min(100, overall_score)
            
            issues = self._detect_issues(df, quality_metrics)
            recommendations = self._generate_recommendations(df, quality_metrics)
            
            report = {
                "quality_metrics": quality_metrics,
                "issues": issues,
                "recommendations": recommendations
            }
            
            self.validation_results = report
            
            return report
        except Exception as e:
            logger.error(f"Error validating dataset: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def get_quality_summary(self) -> Dict[str, Any]:
        """
        Trả về bản tóm tắt chất lượng dữ liệu
        
        Returns:
            Dict: Tóm tắt chất lượng dữ liệu
        """
        if not self.validation_results:
            return {"error": "No validation has been performed yet"}
            
        metrics = self.validation_results.get("quality_metrics", {})
        issues = self.validation_results.get("issues", [])
        recommendations = self.validation_results.get("recommendations", [])
            
        summary = {
            "overall_score": metrics.get("overall_score", 0),
            "completeness_score": metrics.get("completeness", {}).get("score", 0),
            "consistency_score": metrics.get("consistency", {}).get("score", 0),
            "uniqueness_score": metrics.get("uniqueness", {}).get("score", 0), 
            "integrity_score": metrics.get("integrity", {}).get("score", 0),
            "accuracy_score": metrics.get("accuracy", {}).get("score", 0),
            "major_issues": issues[:5],
            "top_recommendations": recommendations[:3]
        }
        
        return summary

    def _validate_completeness(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Đánh giá tính đầy đủ của dữ liệu (thiếu giá trị)"""
        try:
            missing_values = df.isna().sum()
            total_cells = df.size
            missing_cells = missing_values.sum()
            
            completeness_score = 100 * (1 - missing_cells / total_cells)
            
            cols_missing_values = missing_values[missing_values > 0].sort_values(ascending=False)
            
            missing_pcts = cols_missing_values / len(df)
            problematic_cols = cols_missing_values[missing_pcts > 0.2]
            
            columns_with_missing = [
                {"column": col, "missing_count": int(count), "missing_percent": float(100 * count / len(df))}
                for col, count in cols_missing_values.items()
            ]
            
            return {
                "score": completeness_score,
                "missing_cells": int(missing_cells),
                "missing_percent": float(100 * missing_cells / total_cells),
                "columns_with_missing": columns_with_missing,
                "problematic_columns": problematic_cols.index.tolist()
            }
        except Exception as e:
            logger.error(f"Error validating completeness: {str(e)}")
            return {"score": 0, "error": str(e)}

    def _validate_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Đánh giá tính nhất quán của dữ liệu"""
        try:
            inconsistency_count = 0
            inconsistent_columns = []
            
            for col in df.columns:
                if df[col].dtype == 'object':
                    values = df[col].dropna()
                    if len(values) == 0:
                        continue
                        
                    if "email" in col.lower():
                        valid_emails = values.str.match(self.email_pattern).fillna(False).sum()
                        
                        if valid_emails > 0 and valid_emails < len(values):
                            inconsistency_count += (len(values) - valid_emails)
                            inconsistent_columns.append({"column": col, "issue": "inconsistent_email_format"})
                    
                    elif any(x in col.lower() for x in ["date", "time", "day", "month", "year"]):
                        try:
                            dates = convert_to_datetime(values)
                            invalid_dates = dates.isna().sum()
                            if invalid_dates > 0 and invalid_dates < len(values):
                                inconsistency_count += invalid_dates
                                inconsistent_columns.append({"column": col, "issue": "inconsistent_date_format"})
                        except Exception:
                            pass
                            
                    elif any(x in col.lower() for x in ["phone", "tel", "mobile"]):
                        cleaned_values = values.str.replace(r'\D', '', regex=True)
                        lengths = cleaned_values.str.len()
                        
                        if lengths.nunique() > 1:
                            most_common_len = lengths.mode()[0]
                            inconsistency_count += (lengths != most_common_len).sum()
                            inconsistent_columns.append({"column": col, "issue": "inconsistent_phone_format"})
                    
                    if values.str.lower().nunique() < values.nunique():
                        case_inconsistency = values.nunique() - values.str.lower().nunique()
                        inconsistency_count += case_inconsistency
                        inconsistent_columns.append({"column": col, "issue": "inconsistent_capitalization"})
            
            for col in df.select_dtypes(include=['number']).columns:
                values = df[col].dropna()
                if len(values) <= 10:
                    continue
                    
                try:
                    positive_values = values[values > 0]
                    if len(positive_values) > 0:
                        log_values = np.log10(positive_values)
                        log_range = log_values.max() - log_values.min()
                        
                        if log_range > 3:
                            inconsistency_count += 1
                            inconsistent_columns.append({"column": col, "issue": "potential_unit_inconsistency"})
                except Exception:
                    pass
            
            total_cells = df.size
            consistency_score = 100 * (1 - min(1, inconsistency_count / total_cells))
            
            return {
                "score": consistency_score,
                "inconsistency_count": inconsistency_count,
                "inconsistent_columns": inconsistent_columns
            }
        except Exception as e:
            logger.error(f"Error validating consistency: {str(e)}")
            return {"score": 50, "error": str(e)}

    def _validate_uniqueness(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Đánh giá tính duy nhất của dữ liệu"""
        try:
            duplicate_rows = df.duplicated().sum()
            duplicate_pct = duplicate_rows / len(df) * 100 if len(df) > 0 else 0
            
            non_null_counts = df.count()
            unique_counts = df.nunique()
            
            uniqueness_stats = []
            potential_identifiers = []
            
            for col in df.columns:
                non_null_count = non_null_counts[col]
                if non_null_count < len(df) * 0.5:
                    continue
                    
                unique_values = unique_counts[col]
                unique_pct = unique_values / non_null_count * 100
                
                uniqueness_stats.append({
                    "column": col,
                    "unique_values": unique_values,
                    "unique_percent": float(unique_pct)
                })
                
                if 90 <= unique_pct <= 100 and non_null_count > len(df) * 0.9:
                    potential_identifiers.append(col)
            
            uniqueness_stats.sort(key=lambda x: x["unique_percent"], reverse=True)
            
            uniqueness_score = 100 * (1 - duplicate_pct / 100)
            if not potential_identifiers:
                uniqueness_score *= 0.8

            return {
                "score": uniqueness_score,
                "duplicate_rows": int(duplicate_rows),
                "duplicate_percent": float(duplicate_pct),
                "uniqueness_stats": uniqueness_stats[:10],
                "potential_identifiers": potential_identifiers
            }
        except Exception as e:
            logger.error(f"Error validating uniqueness: {str(e)}")
            return {"score": 50, "error": str(e)}

    def _validate_integrity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Đánh giá tính toàn vẹn của dữ liệu"""
        try:
            integrity_issues = []
            
            outlier_stats = {}
            
            numeric_cols = [col for col in df.select_dtypes(include=['number']).columns
                           if df[col].nunique() >= 10]
            
            if numeric_cols:
                Q1 = df[numeric_cols].quantile(0.25)
                Q3 = df[numeric_cols].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bounds = Q1 - 3 * IQR
                upper_bounds = Q3 + 3 * IQR
                
                for col in numeric_cols:
                    outliers = ((df[col] < lower_bounds[col]) | (df[col] > upper_bounds[col])).sum()
                    outlier_pct = outliers / df[col].count() * 100 if df[col].count() > 0 else 0
                    
                    outlier_stats[col] = {
                        "outlier_count": int(outliers),
                        "outlier_percent": float(outlier_pct)
                    }
                    
                    if outlier_pct > 5:
                        integrity_issues.append({"column": col, "issue": "high_outlier_percentage"})
            
            range_violations = []
            
            pct_indicators = {'percent', 'pct', '%'}
            
            for col in df.columns:
                if any(indicator in col.lower() for indicator in pct_indicators) and is_numeric_dtype(df[col]):
                    values = df[col].dropna()
                    if len(values) == 0:
                        continue
                        
                    if values.max() <= 1:
                        invalid = ((values < 0) | (values > 1)).sum()
                    else:
                        invalid = ((values < 0) | (values > 100)).sum()
                        
                    if invalid > 0:
                        range_violations.append({
                            "column": col,
                            "issue": "out_of_range_percent",
                            "invalid_count": int(invalid)
                        })
                        integrity_issues.append({"column": col, "issue": "out_of_range_percent"})
            
            date_violations = []
            for col in df.columns:
                if is_datetime(df[col]):
                    if not is_datetime64_any_dtype(df[col]):
                        try:
                            datetime_col = convert_to_datetime(df[col])
                        except Exception:
                            continue
                    else:
                        datetime_col = df[col]
                    
                    try:
                        future_dates = (datetime_col > pd.Timestamp.now()).sum()
                        if future_dates > 0:
                            non_null_count = len(datetime_col.dropna())
                            date_violations.append({
                                "column": col,
                                "issue": "future_dates",
                                "invalid_count": int(future_dates),
                                "percent": float(future_dates * 100 / non_null_count) if non_null_count > 0 else 0
                            })
                            integrity_issues.append({"column": col, "issue": "future_dates"})
                    except Exception:
                        pass
                    
                    try:
                        old_dates = (datetime_col < pd.Timestamp('1900-01-01')).sum()
                        if old_dates > 0:
                            non_null_count = len(datetime_col.dropna())
                            date_violations.append({
                                "column": col,
                                "issue": "old_dates",
                                "invalid_count": int(old_dates),
                                "percent": float(old_dates * 100 / non_null_count) if non_null_count > 0 else 0
                            })
                            integrity_issues.append({"column": col, "issue": "old_dates"})
                    except Exception:
                        pass
                        
                    try:
                        distribution = analyze_datetime_distribution(datetime_col)
                        
                        if "time_gaps" in distribution:
                            time_gaps = distribution["time_gaps"]
                            if time_gaps.get("regularity", 1) < 0.5:
                                date_violations.append({
                                    "column": col,
                                    "issue": "irregular_time_intervals",
                                    "details": time_gaps
                                })
                                integrity_issues.append({"column": col, "issue": "irregular_time_intervals"})
                    except Exception:
                        pass
            
            outlier_penalty = sum(
                outlier_stats[col]["outlier_percent"] for col in outlier_stats
            ) / 2 if outlier_stats else 0
            
            integrity_score = 100 - min(50, len(integrity_issues) * 5 + outlier_penalty)
            
            return {
                "score": integrity_score,
                "integrity_issues": integrity_issues,
                "outlier_stats": outlier_stats,
                "range_violations": range_violations,
                "date_violations": date_violations
            }
        except Exception as e:
            logger.error(f"Error validating integrity: {str(e)}")
            return {"score": 50, "error": str(e)}

    def _validate_accuracy(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Đánh giá độ chính xác của dữ liệu"""
        try:
            accuracy_issues = []
            suspect_columns = []
            
            for col in df.columns:
                if df[col].dtype == 'object':
                    non_null = df[col].dropna()
                    if len(non_null) == 0:
                        continue
                    
                    json_check = non_null.astype(str).str.contains('{') & non_null.astype(str).str.contains('}')
                    if json_check.any():
                        accuracy_issues.append({"column": col, "issue": "potential_json_in_string"})
                        suspect_columns.append(col)
                    
                    delimited_check = non_null.astype(str).str.contains(self.delimiter_pattern) & ~non_null.astype(str).str.contains(self.newline_pattern)
                    delimited_ratio = delimited_check.mean()
                    
                    if delimited_ratio > 0.5:
                        accuracy_issues.append({"column": col, "issue": "multiple_values_in_cell"})
                        suspect_columns.append(col)
                    
                    if "email" in col.lower() and len(non_null) > 0:
                        email_valid_check = non_null.astype(str).str.match(self.email_pattern)
                        valid_ratio = email_valid_check.mean()
                        
                        if valid_ratio < 0.9 and valid_ratio > 0:
                            accuracy_issues.append({"column": col, "issue": "invalid_emails"})
                            suspect_columns.append(col)
            
            accuracy_score = 100 - min(50, len(accuracy_issues) * 10)
            
            return {
                "score": accuracy_score,
                "accuracy_issues": accuracy_issues,
                "suspect_columns": suspect_columns
            }
        except Exception as e:
            logger.error(f"Error validating accuracy: {str(e)}")
            return {"score": 70, "error": str(e)}

    def _detect_issues(self, df: pd.DataFrame, quality_metrics: Dict) -> List[str]:
        """Phát hiện các vấn đề chính trong dataset"""
        issues = []
        
        missing_percent = quality_metrics["completeness"].get("missing_percent", 0)
        if missing_percent > 10:
            issues.append(f"High level of missing data: {missing_percent:.1f}% of values are missing")
        
        problematic_columns = quality_metrics["completeness"].get("problematic_columns", [])
        if problematic_columns:
            cols_displayed = problematic_columns[:5]
            cols_str = ", ".join(cols_displayed)
            
            if len(problematic_columns) > 5:
                cols_str += f" and {len(problematic_columns) - 5} others"
                
            issues.append(f"Columns with excessive missing values: {cols_str}")

        duplicate_percent = quality_metrics["uniqueness"].get("duplicate_percent", 0)
        if duplicate_percent > 5:
            issues.append(f"High level of duplicate rows: {duplicate_percent:.1f}% of rows are duplicates")
        
        outlier_stats = quality_metrics["integrity"].get("outlier_stats", {})
        if outlier_stats:
            high_outlier_cols = [col for col, stats in outlier_stats.items() 
                               if stats["outlier_percent"] > 10]
                               
            if high_outlier_cols:
                cols_displayed = high_outlier_cols[:3]
                cols_str = ", ".join(cols_displayed)
                
                if len(high_outlier_cols) > 3:
                    cols_str += f" and {len(high_outlier_cols) - 3} others"
                    
                issues.append(f"High percentage of outliers in columns: {cols_str}")
        
        inconsistent_columns = quality_metrics["consistency"].get("inconsistent_columns", [])
        if len(inconsistent_columns) > 0:
            cols_displayed = [str(col["column"]) for col in inconsistent_columns[:3]]
            cols_str = ", ".join(cols_displayed)
            
            if len(inconsistent_columns) > 3:
                cols_str += f" and {len(inconsistent_columns) - 3} others"
                
            issues.append(f"Data consistency issues in columns: {cols_str}")
        
        accuracy_issues = quality_metrics["accuracy"].get("accuracy_issues", [])
        if len(accuracy_issues) > 0:
            cols_displayed = [str(issue["column"]) for issue in accuracy_issues[:3]]
            cols_str = ", ".join(cols_displayed)
            
            if len(accuracy_issues) > 3:
                cols_str += f" and {len(accuracy_issues) - 3} others"
                
            issues.append(f"Potential data accuracy issues in columns: {cols_str}")
        
        return issues

    def _generate_recommendations(self, df: pd.DataFrame, quality_metrics: Dict) -> List[str]:
        """Tạo các khuyến nghị cho việc cải thiện chất lượng dữ liệu"""
        recommendations = []
        
        if quality_metrics["completeness"]["missing_percent"] > 5:
            recommendations.append("Consider imputing missing values or removing columns with excessive missing data")
        
        if quality_metrics["uniqueness"]["duplicate_percent"] > 1:
            recommendations.append("Remove duplicate rows to improve data quality")
        
        outlier_stats = quality_metrics["integrity"].get("outlier_stats", {})
        high_outlier_cols = [col for col, stats in outlier_stats.items() 
                           if stats["outlier_percent"] > 5]
                           
        if high_outlier_cols:
            recommendations.append("Examine and potentially cap or remove outliers in numeric columns")

        inconsistent_columns = quality_metrics["consistency"].get("inconsistent_columns", [])
        if inconsistent_columns:
            issues = {issue["issue"] for issue in inconsistent_columns}
            
            if "inconsistent_date_format" in issues:
                recommendations.append("Standardize date formats across the dataset")
            
            if any(issue in issues for issue in ["inconsistent_email_format", "inconsistent_phone_format"]):
                recommendations.append("Apply consistent formatting to contact information (emails, phone numbers)")
            
            if "inconsistent_capitalization" in issues:
                recommendations.append("Standardize capitalization in text columns")
        
        if any(' ' in col for col in df.columns):
            recommendations.append("Standardize column names by replacing spaces with underscores")
        
        potential_ids = quality_metrics["uniqueness"].get("potential_identifiers", [])
        if not potential_ids:
            recommendations.append("Consider adding a unique identifier column for better data tracking")
        
        recommendations.append("Optimize memory usage by converting numeric columns to appropriate dtypes")
        
        if quality_metrics["overall_score"] < 70:
            recommendations.append("Conduct a comprehensive data quality audit to address the numerous issues found")
        
        return recommendations