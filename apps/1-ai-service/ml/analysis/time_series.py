"""
Module phân tích và dự báo chuỗi thời gian nâng cao, tích hợp các tính năng từ EnhancedDataPipeline.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.ensemble import IsolationForest

from ml.utils.datetime_utils import convert_to_datetime

logger = logging.getLogger(__name__)


class TimeSeriesAnalyzer:
    """Phân tích và dự báo chuỗi thời gian nâng cao"""

    def __init__(self, config: Optional[Dict] = None):
        """Khởi tạo với config tùy chọn"""
        self.config = config or {}
        self._analysis_cache = {}
        logger.info("Enhanced TimeSeriesAnalyzer initialized")

    def analyze_time_series(self, df: pd.DataFrame, date_col: str, value_col: str) -> Dict:
        """
        Phân tích chuỗi thời gian
        
        Args:
            df: DataFrame chứa dữ liệu
            date_col: Tên cột thời gian
            value_col: Tên cột giá trị
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Tạo cache key
            cache_key = f"{date_col}_{value_col}_{hash(str(df.shape))}"
            if cache_key in self._analysis_cache:
                return self._analysis_cache[cache_key]
            
            # Kiểm tra các đầu vào
            if date_col not in df.columns:
                return {"error": f"Date column '{date_col}' not found in dataframe"}
            
            if value_col not in df.columns:
                return {"error": f"Value column '{value_col}' not found in dataframe"}
            
            # Kiểm tra kiểu dữ liệu cột giá trị
            if not is_numeric_dtype(df[value_col]):
                try:
                    # Thử chuyển đổi cột giá trị thành numeric
                    if df[value_col].dtype == 'category':
                        df = df.copy()
                        df[value_col] = df[value_col].astype(str).astype(float)
                    else:
                        df = df.copy()
                        df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
                    
                    # Kiểm tra sau khi chuyển đổi
                    if df[value_col].isna().sum() > 0.5 * len(df):
                        return {"error": f"Column '{value_col}' could not be converted to numeric type. Too many NaN values after conversion."}
                except Exception as e:
                    return {"error": f"Column '{value_col}' must be numeric. {str(e)}"}
            
            # Chuyển đổi thành datetime nếu chưa phải
            if not is_datetime64_any_dtype(df[date_col]):
                try:
                    df = df.copy()
                    df[date_col] = convert_to_datetime(df[date_col])
                except Exception as e:
                    return {"error": f"Could not convert '{date_col}' to datetime: {str(e)}"}
            
            # Sắp xếp theo thời gian
            df_sorted = df.sort_values(by=date_col).copy()
            
            # Loại bỏ NaN values
            valid_data = df_sorted[[date_col, value_col]].dropna()
            if len(valid_data) == 0:
                return {"error": "No valid data points after removing NaN values"}
            
            # Chuẩn bị series
            ts = valid_data.set_index(date_col)[value_col]
            
            # Resampling về tần suất phù hợp
            resampled_ts, frequency = self._auto_resample_time_series(ts)
            
            # Phát hiện outliers trong chuỗi thời gian
            outliers_result = self._detect_time_series_outliers(resampled_ts)
            
            # Phát hiện tính ổn định (stationarity)
            stationarity_result = self._check_stationarity(resampled_ts)
            
            # Phân tích thành phần
            decomposition_result = self._decompose_time_series(resampled_ts, frequency)
            
            # Phân tích autocorrelation
            acf_pacf_result = self._analyze_autocorrelation(resampled_ts)
            
            # Phát hiện changepoints
            changepoints_result = self._detect_changepoints(resampled_ts)
            
            # Phát hiện chu kỳ
            periodicity_result = self._detect_periodicity(resampled_ts)
            
            # Tạo báo cáo phân tích
            analysis_report = {
                "time_series_info": {
                    "original_length": len(ts),
                    "resampled_length": len(resampled_ts),
                    "frequency": frequency,
                    "start_date": ts.index.min().isoformat(),
                    "end_date": ts.index.max().isoformat(),
                    "date_range_days": (ts.index.max() - ts.index.min()).days
                },
                "statistics": {
                    "mean": float(resampled_ts.mean()),
                    "std": float(resampled_ts.std()),
                    "min": float(resampled_ts.min()),
                    "max": float(resampled_ts.max()),
                    "median": float(resampled_ts.median()),
                    "skewness": float(resampled_ts.skew()),
                    "kurtosis": float(resampled_ts.kurtosis())
                },
                "outliers": outliers_result,
                "stationarity": stationarity_result,
                "decomposition": decomposition_result,
                "autocorrelation": acf_pacf_result,
                "changepoints": changepoints_result,
                "periodicity": periodicity_result,
                "recommendations": self._generate_time_series_recommendations(
                    resampled_ts, stationarity_result, decomposition_result, 
                    changepoints_result, periodicity_result
                )
            }
            
            # Lưu vào cache
            self._analysis_cache[cache_key] = analysis_report
            
            return analysis_report
        except Exception as e:
            logger.error(f"Error analyzing time series: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def forecast_time_series(
        self, 
        df: pd.DataFrame, 
        date_col: str, 
        value_col: str, 
        forecast_periods: int = 10,
        return_confidence: bool = True,
        exogenous_vars: Optional[List[str]] = None
    ) -> Dict:
        """
        Dự báo chuỗi thời gian
        
        Args:
            df: DataFrame chứa dữ liệu
            date_col: Tên cột thời gian
            value_col: Tên cột giá trị
            forecast_periods: Số kỳ dự báo
            return_confidence: Có trả về khoảng tin cậy không
            exogenous_vars: Danh sách các biến exogenous (ngoại sinh) nếu có
            
        Returns:
            Dict: Kết quả dự báo
        """
        try:
            # Kiểm tra kiểu dữ liệu cột giá trị
            if not is_numeric_dtype(df[value_col]):
                try:
                    # Thử chuyển đổi cột giá trị thành numeric
                    if df[value_col].dtype == 'category':
                        df = df.copy()
                        df[value_col] = df[value_col].astype(str).astype(float)
                    else:
                        df = df.copy()
                        df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
                    
                    # Kiểm tra sau khi chuyển đổi
                    if df[value_col].isna().sum() > 0.5 * len(df):
                        return {"error": f"Column '{value_col}' could not be converted to numeric type. Too many NaN values after conversion."}
                except Exception as e:
                    return {"error": f"Column '{value_col}' must be numeric. {str(e)}"}
            
            # Phân tích chuỗi thời gian
            analysis_result = self.analyze_time_series(df, date_col, value_col)
            
            if "error" in analysis_result:
                return analysis_result
            
            # Chuẩn bị dữ liệu
            df_sorted = df.sort_values(by=date_col).copy()
            
            # Chuyển đổi thành datetime nếu chưa phải
            if not is_datetime64_any_dtype(df_sorted[date_col]):
                df_sorted[date_col] = convert_to_datetime(df_sorted[date_col])
            
            # Loại bỏ NaN values
            valid_data = df_sorted[[date_col, value_col]].dropna()
            ts = valid_data.set_index(date_col)[value_col]
            
            resampled_ts, frequency = self._auto_resample_time_series(ts)
            
            # Xử lý outliers trước khi dự báo để cải thiện độ chính xác
            if analysis_result["outliers"]["has_outliers"]:
                resampled_ts = self._handle_time_series_outliers(resampled_ts)
            
            # Xác định mô hình phù hợp dựa trên phân tích
            is_stationary = analysis_result["stationarity"]["is_stationary"]
            has_seasonality = analysis_result["decomposition"]["has_seasonality"]
            
            # Tính toán order và seasonal_order cho ARIMA/SARIMA
            best_order, best_seasonal_order = self._find_best_arima_orders(
                resampled_ts, has_seasonality, frequency
            )
            
            # Chuẩn bị biến exogenous nếu có
            exog_data = None
            forecast_exog = None
            if exogenous_vars and all(var in df_sorted.columns for var in exogenous_vars):
                # Kiểm tra kiểu dữ liệu của các biến ngoại sinh
                non_numeric_exogs = [var for var in exogenous_vars if not is_numeric_dtype(df_sorted[var])]
                
                if non_numeric_exogs:
                    df_sorted = df_sorted.copy()
                    # Chuyển đổi các biến categorical thành numeric
                    for var in non_numeric_exogs:
                        if df_sorted[var].dtype == 'category':
                            df_sorted[var] = df_sorted[var].cat.codes
                        else:
                            df_sorted[var] = pd.to_numeric(df_sorted[var], errors='coerce')
                
                # Lấy dữ liệu exogenous và đảm bảo cùng index với chuỗi thời gian
                valid_exog_data = df_sorted.dropna(subset=[date_col] + exogenous_vars)
                exog_data = valid_exog_data[exogenous_vars].set_index(valid_exog_data[date_col])
                exog_data = exog_data.reindex(resampled_ts.index, method='ffill')
                
                # Đối với forecast_exog, sử dụng phương pháp đơn giản (lặp lại giá trị cuối)
                # Trong thực tế, nên có phương pháp dự báo riêng cho exogenous variables
                last_values = exog_data.iloc[-1].to_dict()
                forecast_exog = pd.DataFrame([last_values] * forecast_periods)
            
            # Thực hiện cross-validation để đánh giá model
            if len(resampled_ts) >= 10:
                cv_metrics = self._perform_time_series_cross_validation(
                    resampled_ts, 
                    best_order,
                    best_seasonal_order if has_seasonality else None,
                    exog_data
                )
            else:
                cv_metrics = None
            
            # Dự báo
            forecast_result = self._make_forecast(
                resampled_ts, 
                forecast_periods, 
                is_stationary,
                has_seasonality,
                best_order,
                best_seasonal_order,
                return_confidence,
                exog_data,
                forecast_exog
            )
            
            # Thêm thông tin phân tích vào kết quả
            forecast_result["analysis"] = {
                "is_stationary": is_stationary,
                "has_seasonality": has_seasonality,
                "model_params": {
                    "order": best_order,
                    "seasonal_order": best_seasonal_order if has_seasonality else None
                },
                "cross_validation": cv_metrics
            }
            
            return forecast_result
        except Exception as e:
            logger.error(f"Error forecasting time series: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def _auto_resample_time_series(self, ts: pd.Series) -> Tuple[pd.Series, str]:
        """
        Tự động resample time series về tần suất phù hợp
        
        Args:
            ts: Time series đầu vào
            
        Returns:
            Tuple[pd.Series, str]: Time series đã resample và tần suất
        """
        # Kiểm tra xem index có phải là datetime
        if not isinstance(ts.index, pd.DatetimeIndex):
            ts.index = pd.DatetimeIndex(convert_to_datetime(ts.index))
        
        # Kiểm tra dữ liệu categorical và chuyển đổi nếu cần
        if ts.dtype == 'category':
            ts = ts.astype('float')
        
        # Tìm tần suất dữ liệu
        if len(ts) <= 1:
            return ts, "d"  # Default to daily if too few points
            
        time_diffs = pd.Series(ts.index[1:]) - pd.Series(ts.index[:-1])
        median_diff = time_diffs.median()
        
        # Quyết định tần suất resample
        if median_diff.days == 0 and median_diff.seconds <= 3600:
            # Dữ liệu theo giờ hoặc nhỏ hơn
            frequency = "h"
        elif median_diff.days == 0:
            # Dữ liệu theo ngày
            frequency = "d"
        elif 1 <= median_diff.days <= 7:
            # Dữ liệu theo tuần
            frequency = "w"
        elif 28 <= median_diff.days <= 31:
            # Dữ liệu theo tháng
            frequency = "m"
        elif 89 <= median_diff.days <= 92:
            # Dữ liệu theo quý
            frequency = "q"
        elif median_diff.days >= 350:
            # Dữ liệu theo năm
            frequency = "y"
        else:
            # Mặc định theo ngày
            frequency = "d"
        
        # Resample dữ liệu với xử lý numeric_only=True để tránh lỗi với categorical
        resampled_ts = ts.resample(frequency).mean()
        
        # Điền missing values nếu có
        resampled_ts = resampled_ts.interpolate(method='linear')
        
        return resampled_ts, frequency
    
    def _detect_time_series_outliers(self, ts: pd.Series) -> Dict:
        """
        Phát hiện outliers trong chuỗi thời gian
        
        Args:
            ts: Time series cần kiểm tra
            
        Returns:
            Dict: Kết quả phát hiện outliers
        """
        try:
            # Đảm bảo ts là numeric
            if not is_numeric_dtype(ts):
                try:
                    ts = pd.to_numeric(ts, errors='coerce')
                except:
                    return {
                        "has_outliers": False,
                        "outlier_count": 0,
                        "error": "Data must be numeric to detect outliers"
                    }
            
            # Tính Z-score - sử dụng vectorized operations
            z_scores = np.abs((ts - ts.mean()) / ts.std())
            z_outliers = ts[z_scores > 3]
            
            # Tính IQR (Interquartile Range) - vectorized
            Q1 = ts.quantile(0.25)
            Q3 = ts.quantile(0.75)
            IQR = Q3 - Q1
            iqr_outliers = ts[(ts < Q1 - 1.5 * IQR) | (ts > Q3 + 1.5 * IQR)]
            
            # Kết hợp kết quả từ hai phương pháp - hiệu quả hơn với set operation
            combined_outliers_indices = set(z_outliers.index).union(set(iqr_outliers.index))
            combined_outliers = ts.loc[list(combined_outliers_indices)].sort_index()
            
            # Nếu có đủ dữ liệu, sử dụng Isolation Forest
            if len(ts) >= 30:
                try:
                    # Chuẩn bị dữ liệu cho Isolation Forest
                    X = ts.values.reshape(-1, 1)
                    
                    # Huấn luyện model
                    isolation_forest = IsolationForest(
                        contamination=0.05,  # Giả sử khoảng 5% là outliers
                        random_state=42,
                        n_jobs=-1  # Sử dụng tất cả CPU cores
                    )
                    
                    # Dự đoán outliers (-1 là outlier, 1 là inlier)
                    outlier_labels = isolation_forest.fit_predict(X)
                    outlier_indices = np.where(outlier_labels == -1)[0]
                    
                    # Chuyển đổi indices thành thời gian trong chuỗi gốc
                    if_outliers = ts.iloc[outlier_indices]
                    
                    # Thêm vào kết quả kết hợp
                    all_outliers_indices = combined_outliers_indices.union(set(if_outliers.index))
                    combined_outliers = ts.loc[list(all_outliers_indices)].sort_index()
                except Exception as e:
                    logger.debug(f"Isolation Forest failed: {str(e)}. Using standard methods only.")
            
            # Tạo kết quả
            outlier_values = combined_outliers.to_dict()
            has_outliers = len(combined_outliers) > 0
            outlier_pct = len(combined_outliers) / len(ts) * 100 if len(ts) > 0 else 0
            
            result = {
                "has_outliers": has_outliers,
                "outlier_count": len(combined_outliers),
                "outlier_percent": float(outlier_pct),
                "z_score_outliers": len(z_outliers),
                "iqr_outliers": len(iqr_outliers),
                "max_outlier_value": float(max(outlier_values.values())) if outlier_values else None,
                "min_outlier_value": float(min(outlier_values.values())) if outlier_values else None,
                "top_outliers": dict(list(outlier_values.items())[:10])  # Limit to top 10
            }
            
            return result
        except Exception as e:
            logger.warning(f"Error detecting time series outliers: {str(e)}")
            return {
                "has_outliers": False,
                "outlier_count": 0,
                "error": str(e)
            }

    def _handle_time_series_outliers(self, ts: pd.Series) -> pd.Series:
        """
        Xử lý outliers trong chuỗi thời gian
        
        Args:
            ts: Time series cần xử lý
            
        Returns:
            pd.Series: Time series đã xử lý outliers
        """
        if not is_numeric_dtype(ts):
            return ts  # Return original if not numeric
            
        # Tạo bản sao để không ảnh hưởng đến dữ liệu gốc
        ts_clean = ts.copy()
        
        # Áp dụng kỹ thuật rolling median
        window_size = min(7, max(1, len(ts) // 5))
        
        # Tính Z-score
        z_scores = np.abs((ts - ts.mean()) / ts.std())
        z_outliers = ts[z_scores > 3]
        
        # Tính IQR (Interquartile Range)
        Q1 = ts.quantile(0.25)
        Q3 = ts.quantile(0.75)
        IQR = Q3 - Q1
        iqr_outliers = ts[(ts < Q1 - 1.5 * IQR) | (ts > Q3 + 1.5 * IQR)]
        
        # Kết hợp outliers từ cả hai phương pháp - sử dụng set operations hiệu quả hơn
        combined_outliers_indices = set(z_outliers.index).union(set(iqr_outliers.index))
        
        # Tính giá trị rolling median một lần cho toàn bộ chuỗi
        rolling_median = ts.rolling(window=window_size, center=True, min_periods=1).median()
        
        # Thay thế tất cả outliers bằng giá trị rolling median - vectorized operation
        ts_clean.loc[list(combined_outliers_indices)] = rolling_median.loc[list(combined_outliers_indices)]
        
        return ts_clean

    def _check_stationarity(self, ts: pd.Series) -> Dict:
        """
        Kiểm tra tính ổn định (stationarity) của time series
        
        Args:
            ts: Time series cần kiểm tra
            
        Returns:
            Dict: Kết quả kiểm tra
        """
        # Đảm bảo không có NaN
        ts_clean = ts.dropna()
        
        if len(ts_clean) < 8:  # Cần ít nhất 8 điểm để phân tích
            return {
                "is_stationary": False,
                "error": "Not enough data points for stationarity test",
                "recommendation": "Cannot determine stationarity with limited data. Consider collecting more data."
            }
        
        result = adfuller(ts_clean)
        
        # p-value < 0.05 => time series là stationary
        is_stationary = result[1] < 0.05
        
        # Kiểm tra thêm về tính constant variance (homoscedasticity)
        # Chia chuỗi thành n phần và kiểm tra phương sai
        n_splits = min(5, len(ts_clean) // 20)
        homoscedastic = True
        var_ratio = None
        
        if n_splits >= 2:
            split_size = len(ts_clean) // n_splits
            # Vectorized calculation of variances
            variances = [ts_clean.iloc[i*split_size:(i+1)*split_size].var() for i in range(n_splits)]
            
            if any(v <= 0 for v in variances):
                # Handle zero variance segments
                homoscedastic = False
            else:
                max_var = max(variances)
                min_var = min(variances)
                
                # Nếu phương sai thay đổi nhiều, có thể không stationary
                var_ratio = max_var / min_var
                homoscedastic = var_ratio < 3.0  # Ngưỡng thực nghiệm
        
        result_dict = {
            "is_stationary": is_stationary and homoscedastic,
            "adf_test": {
                "adf_statistic": float(result[0]),
                "p_value": float(result[1]),
                "critical_values": {k: float(v) for k, v in result[4].items()}
            },
            "homoscedastic": homoscedastic,
            "variance_ratio": float(var_ratio) if var_ratio is not None else None,
            "recommendation": "The time series is " + 
                             ("stationary" if is_stationary and homoscedastic else "non-stationary") +
                             " based on statistical tests."
        }
        
        # Thêm khuyến nghị nếu non-stationary
        if not is_stationary or not homoscedastic:
            result_dict["recommendation"] += (
                " Consider differencing the series or applying transformations like "
                "log transform to achieve stationarity."
            )
            
            if not homoscedastic:
                result_dict["recommendation"] += (
                    " The series shows heteroscedasticity (changing variance over time), "
                    "which might be addressed with a log or Box-Cox transformation."
                )
        
        return result_dict

    def _decompose_time_series(self, ts: pd.Series, frequency: str) -> Dict:
        """
        Phân tích thành phần của time series (trend, seasonality, residual)
        
        Args:
            ts: Time series cần phân tích
            frequency: Tần suất của time series
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Kiểm tra dữ liệu và xử lý NaN
            ts_clean = ts.dropna()
            
            if len(ts_clean) < 4:  # Need at least 4 points for basic decomposition
                return {
                    "has_seasonality": False,
                    "has_trend": False,
                    "seasonality_strength": 0.0,
                    "trend_strength": 0.0,
                    "trend_direction": "insufficient_data",
                    "components": None,
                    "insight": "Not enough data points for decomposition analysis."
                }
            
            # Xác định period thích hợp cho decompose
            period_map = {"D": 7, "W": 52, "M": 12, "Q": 4, "Y": 1, "H": 24}
            period = period_map.get(frequency, 7)
            
            # Đảm bảo đủ dữ liệu cho period
            if len(ts_clean) < 2 * period:
                return {
                    "has_seasonality": False,
                    "has_trend": False,
                    "seasonality_strength": 0.0,
                    "trend_strength": 0.0,
                    "trend_direction": "insufficient_data",
                    "components": None,
                    "insight": f"Not enough data points for seasonal decomposition with period={period}. Need at least {2*period} points."
                }
            
            # Decompose
            decomposition = seasonal_decompose(
                ts_clean, model='additive', period=period, extrapolate_trend='freq'
            )
            
            # Phân tích seasonality strength
            detrended = ts_clean.values - decomposition.trend.values
            residual_variance = np.var(decomposition.resid.dropna())
            detrended_variance = np.var(detrended) if not np.isclose(np.var(detrended), 0) else 1.0
            strength_of_seasonality = max(0, 1 - residual_variance / detrended_variance)
            
            # Phân tích trend strength
            if np.var(ts_clean.values) > 0:
                strength_of_trend = max(0, 1 - residual_variance / np.var(ts_clean.values))
            else:
                strength_of_trend = 0.0
            
            # Phân tích trend direction
            trend_values = decomposition.trend.dropna()
            if len(trend_values) > 1:
                # Fit linear model to trend
                from scipy import stats
                x = np.arange(len(trend_values))
                slope, _, r_value, p_value, _ = stats.linregress(x, trend_values)
                
                if p_value < 0.05 and abs(r_value) > 0.5:
                    trend_direction = "increasing" if slope > 0 else "decreasing"
                else:
                    trend_direction = "no significant direction"
            else:
                trend_direction = "insufficient data"
            
            has_trend = strength_of_trend > 0.3
            has_seasonality = strength_of_seasonality > 0.3
            
            result = {
                "has_seasonality": has_seasonality,
                "has_trend": has_trend,
                "seasonality_strength": float(strength_of_seasonality),
                "trend_strength": float(strength_of_trend),
                "trend_direction": trend_direction,
                "components": {
                    "trend": decomposition.trend.dropna().tolist()[:100],  # Giới hạn số lượng điểm trả về
                    "seasonal": decomposition.seasonal.dropna().tolist()[:100],
                    "residual": decomposition.resid.dropna().tolist()[:100]
                },
                "insight": self._generate_decomposition_insight(
                    has_trend, has_seasonality, trend_direction, 
                    strength_of_trend, strength_of_seasonality
                )
            }
            
            return result
        except Exception as e:
            logger.warning(f"Error in seasonal decomposition: {str(e)}")
            # Fallback nếu có lỗi
            return {
                "has_seasonality": False,
                "has_trend": False,
                "seasonality_strength": 0.0,
                "trend_strength": 0.0,
                "trend_direction": "error",
                "components": None,
                "insight": f"Could not decompose time series: {str(e)}"
            }
    
    def _generate_decomposition_insight(
        self, has_trend: bool, has_seasonality: bool, trend_direction: str, 
        trend_strength: float, seasonality_strength: float
    ) -> str:
        """Generate insight from decomposition results"""
        insight = "The time series "
        
        if has_trend:
            if trend_direction == "increasing":
                insight += f"shows an increasing trend (strength: {trend_strength:.2f})"
            elif trend_direction == "decreasing":
                insight += f"shows a decreasing trend (strength: {trend_strength:.2f})"
            else:
                insight += f"has a trend component (strength: {trend_strength:.2f}) without clear direction"
        else:
            insight += "does not show a significant trend"
        
        if has_seasonality:
            insight += f" and exhibits seasonality (strength: {seasonality_strength:.2f})"
        else:
            insight += " and does not show significant seasonality"
        
        insight += "."
        
        # Additional insights based on combination
        if has_trend and has_seasonality:
            insight += " This suggests a time series with both long-term directional movement and regular cyclical patterns."
        elif has_trend and not has_seasonality:
            insight += " This suggests a time series with long-term directional movement but lacking regular cycles."
        elif not has_trend and has_seasonality:
            insight += " This suggests a time series with regular cycles around a stable mean."
        else:
            insight += " This suggests a relatively stable time series without strong patterns."
        
        return insight

    def _analyze_autocorrelation(self, ts: pd.Series) -> Dict:
        """
        Phân tích autocorrelation và partial autocorrelation
        
        Args:
            ts: Time series cần phân tích
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Đảm bảo đủ dữ liệu
            ts_clean = ts.dropna()
            
            if len(ts_clean) < 3:
                return {
                    "insight": "Not enough data points for autocorrelation analysis."
                }
            
            # Tính ACF và PACF
            n_lags = min(40, len(ts_clean) // 4)
            acf_values = acf(ts_clean, nlags=n_lags, fft=True)  # Use FFT for better performance
            pacf_values = pacf(ts_clean, nlags=n_lags, method="ywmle")  # Use Yule-Walker method for stability
            
            # Lấy các significant lags
            # Confidence intervals at 95% = 1.96/sqrt(n)
            confidence_limit = 1.96 / np.sqrt(len(ts_clean))
            
            # Sử dụng numpy operations hiệu quả hơn
            significant_acf = np.abs(acf_values[1:]) > confidence_limit
            significant_acf_lags = np.where(significant_acf)[0] + 1  # +1 because we skipped lag 0
            
            significant_pacf = np.abs(pacf_values[1:]) > confidence_limit
            significant_pacf_lags = np.where(significant_pacf)[0] + 1
            
            # Phát hiện mô hình ARIMA dựa trên ACF/PACF
            ar_order, ma_order = self._suggest_arima_orders_from_acf_pacf(acf_values, pacf_values, confidence_limit)
            
            # Insight về ACF/PACF
            insight = ""
            if len(significant_acf_lags) > 0:
                insight += (
                    f"Significant autocorrelation detected at lags: "
                    f"{', '.join(map(str, significant_acf_lags[:5]))}"
                )
                if len(significant_acf_lags) > 5:
                    insight += f" and {len(significant_acf_lags) - 5} more."
                else:
                    insight += "."
                    
                insight += " This suggests the presence of a pattern or dependency in the data."
            else:
                insight += "No significant autocorrelation detected. The observations appear to be independent."
            
            # Thêm gợi ý về mô hình
            model_suggestion = f"Based on ACF/PACF analysis, an ARIMA({ar_order},d,{ma_order}) model might be appropriate, where d depends on stationarity."
            
            return {
                "acf": acf_values.tolist(),
                "pacf": pacf_values.tolist(),
                "significant_acf_lags": significant_acf_lags.tolist(),
                "significant_pacf_lags": significant_pacf_lags.tolist(),
                "confidence_limit": float(confidence_limit),
                "suggested_ar_order": ar_order,
                "suggested_ma_order": ma_order,
                "insight": insight,
                "model_suggestion": model_suggestion
            }
        except Exception as e:
            logger.warning(f"Error in autocorrelation analysis: {str(e)}")
            return {
                "error": str(e),
                "insight": "Could not compute autocorrelation functions."
            }
    
    def _suggest_arima_orders_from_acf_pacf(self, acf_values, pacf_values, confidence_limit):
        """Suggest AR and MA orders based on ACF and PACF patterns"""
        # For AR process: PACF cuts off, ACF tails off
        # For MA process: ACF cuts off, PACF tails off
        
        # Find where ACF and PACF "cut off" (become insignificant)
        # Sử dụng numpy operations hiệu quả hơn
        acf_cutoff = np.argmax(np.abs(acf_values[1:]) <= confidence_limit) + 1 if np.any(np.abs(acf_values[1:]) <= confidence_limit) else len(acf_values)
        pacf_cutoff = np.argmax(np.abs(pacf_values[1:]) <= confidence_limit) + 1 if np.any(np.abs(pacf_values[1:]) <= confidence_limit) else len(pacf_values)
        
        # Determine characteristics
        acf_tails_off = acf_cutoff > 5  # If significant beyond lag 5, we consider it "tailing off"
        pacf_tails_off = pacf_cutoff > 5
        
        # Simple heuristic for order suggestion
        ar_order = 0
        ma_order = 0
        
        # Pure AR process (if PACF cuts off and ACF tails off)
        if pacf_cutoff <= 5 and acf_tails_off:
            ar_order = pacf_cutoff
        
        # Pure MA process (if ACF cuts off and PACF tails off)
        if acf_cutoff <= 5 and pacf_tails_off:
            ma_order = acf_cutoff
        
        # Mixed ARMA process
        if (pacf_cutoff > 5 and acf_cutoff > 5) or (pacf_cutoff <= 5 and acf_cutoff <= 5):
            ar_order = min(2, pacf_cutoff)
            ma_order = min(2, acf_cutoff)
        
        # Simplify model if possible
        if ar_order == 0 and ma_order == 0:
            # Default to AR(1) if no clear pattern
            ar_order = 1
        
        return ar_order, ma_order

    def _detect_changepoints(self, ts: pd.Series) -> Dict:
        """
        Phát hiện điểm thay đổi trong chuỗi thời gian
        
        Args:
            ts: Time series cần phân tích
            
        Returns:
            Dict: Kết quả phát hiện changepoints
        """
        try:
            # Kiểm tra xem có đủ dữ liệu không
            ts_clean = ts.dropna()
            if len(ts_clean) < 30:
                return {
                    "has_changepoints": False,
                    "insight": "Not enough data points to detect changepoints reliably."
                }
            
            # Thử sử dụng thư viện ruptures nếu có
            try:
                import ruptures as rpt
                
                # Phát hiện changepoints
                model = "l2"  # squared error
                algo = rpt.Pelt(model=model, min_size=5).fit(ts_clean.values)
                result = algo.predict(pen=10)
                
                # Chuyển đổi indices thành thời gian
                changepoints = []
                for cp in result[:-1]:  # Loại bỏ điểm cuối cùng (kết thúc chuỗi)
                    if cp < len(ts_clean):
                        changepoints.append({
                            "index": int(cp),
                            "date": ts_clean.index[cp].isoformat() if isinstance(ts_clean.index[cp], pd.Timestamp) else str(ts_clean.index[cp]),
                            "value": float(ts_clean.iloc[cp])
                        })
                
                if changepoints:
                    # Tính magnitude của các changepoints - sử dụng vectorized operations
                    for i, cp in enumerate(changepoints):
                        if i == 0:
                            before_cp = ts_clean.iloc[:cp["index"]].mean()
                        else:
                            before_cp = ts_clean.iloc[changepoints[i-1]["index"]:cp["index"]].mean()
                        
                        if i == len(changepoints) - 1:
                            after_cp = ts_clean.iloc[cp["index"]:].mean()
                        else:
                            after_cp = ts_clean.iloc[cp["index"]:changepoints[i+1]["index"]].mean()
                        
                        cp["magnitude"] = float(abs(after_cp - before_cp))
                        cp["percent_change"] = float(abs(after_cp - before_cp) / abs(before_cp) * 100 if before_cp != 0 else 0)
                
                # Sắp xếp changepoints theo magnitude giảm dần
                changepoints = sorted(changepoints, key=lambda x: x["magnitude"], reverse=True)
                
                result = {
                    "has_changepoints": len(changepoints) > 0,
                    "changepoint_count": len(changepoints),
                    "changepoints": changepoints[:5],  # Chỉ trả về 5 changepoints quan trọng nhất
                    "method": "PELT algorithm"
                }
            except ImportError:
                # Fallback: phương pháp đơn giản hơn nếu không có ruptures
                # Sử dụng rolling z-score
                window = min(10, len(ts_clean) // 5)
                window = max(window, 2)  # Đảm bảo window ít nhất là 2
                
                rolling_mean = ts_clean.rolling(window=window).mean()
                rolling_std = ts_clean.rolling(window=window).std()
                
                # Tránh chia cho 0
                rolling_std_safe = rolling_std.replace(0, np.nan)
                z_scores = np.abs((ts_clean - rolling_mean) / rolling_std_safe)
                z_scores = z_scores.fillna(0)
                
                potential_cps = z_scores[window:][z_scores[window:] > 3]
                
                # Chọn các CP đáng kể
                if len(potential_cps) > 0:
                    # Gộp các CP gần nhau
                    from scipy.signal import find_peaks
                    peaks, _ = find_peaks(z_scores.fillna(0).values, height=3, distance=window)
                    
                    changepoints = []
                    for cp in peaks:
                        if cp < len(ts_clean):
                            changepoints.append({
                                "index": int(cp),
                                "date": ts_clean.index[cp].isoformat() if isinstance(ts_clean.index[cp], pd.Timestamp) else str(ts_clean.index[cp]),
                                "value": float(ts_clean.iloc[cp]),
                                "z_score": float(z_scores.iloc[cp]) if cp < len(z_scores) else None
                            })
                    
                    # Sort by z-score
                    changepoints = sorted(changepoints, key=lambda x: x["z_score"] if x["z_score"] is not None else 0, reverse=True)
                    
                    result = {
                        "has_changepoints": len(changepoints) > 0,
                        "changepoint_count": len(changepoints),
                        "changepoints": changepoints[:5],  # Top 5 only
                        "method": "Rolling Z-score"
                    }
                else:
                    result = {
                        "has_changepoints": False,
                        "changepoint_count": 0,
                        "method": "Rolling Z-score"
                    }
            
            # Generate insight
            if result["has_changepoints"]:
                top_cp = result["changepoints"][0]
                cp_date = top_cp.get("date", "unknown date")
                
                if "percent_change" in top_cp:
                    pct_change = top_cp["percent_change"]
                    insight = f"A significant change point was detected at {cp_date} with a {pct_change:.1f}% change."
                else:
                    insight = f"A significant change point was detected at {cp_date}."
                
                if result["changepoint_count"] > 1:
                    insight += f" In total, {result['changepoint_count']} change points were identified."
            else:
                insight = "No significant change points were detected in the time series."
            
            result["insight"] = insight
            return result
            
        except Exception as e:
            logger.warning(f"Error in changepoint detection: {str(e)}")
            return {
                "has_changepoints": False,
                "error": str(e),
                "insight": "Could not perform changepoint detection."
            }

    def _detect_periodicity(self, ts: pd.Series) -> Dict:
        """
        Phát hiện chu kỳ trong chuỗi thời gian
        
        Args:
            ts: Time series cần phân tích
            
        Returns:
            Dict: Kết quả phát hiện chu kỳ
        """
        try:
            # Đảm bảo dữ liệu không có NaN
            ts_clean = ts.dropna()
            
            # Kiểm tra xem có đủ dữ liệu không
            if len(ts_clean) < 20:
                return {
                    "has_periodicity": False,
                    "insight": "Not enough data points to detect periodicity reliably."
                }
            
            # Sử dụng phương pháp periodogram
            from scipy import signal
            
            # Khử trend để phát hiện periodicity tốt hơn
            detrended = signal.detrend(ts_clean.values)
            
            # Tính periodogram
            f, Pxx = signal.periodogram(detrended)
            
            # Tìm các peaks
            peaks, properties = signal.find_peaks(Pxx, height=0.1*max(Pxx), distance=5)
            
            # Sắp xếp peaks theo cường độ giảm dần
            if len(peaks) > 0:
                # Sử dụng numpy operations hiệu quả hơn
                peak_powers = Pxx[peaks]
                sorted_indices = np.argsort(-peak_powers)  # Sắp xếp giảm dần
                sorted_peaks = peaks[sorted_indices]
            else:
                sorted_peaks = []
            
            if len(sorted_peaks) > 0:
                # Tính chu kỳ từ các peaks - sử dụng vectorized operations
                periods = []
                for peak in sorted_peaks[:3]:  # Top 3 peaks
                    if f[peak] > 0:  # Tránh chia cho 0
                        period = 1.0 / f[peak]
                        periods.append(float(period))
                
                result = {
                    "has_periodicity": True,
                    "periods": periods,
                    "dominant_period": float(periods[0]) if periods else None,
                    "peak_powers": [float(Pxx[p]) for p in sorted_peaks[:3]]
                }
                
                # Generate insight
                if len(periods) > 0:
                    dominant_period = periods[0]
                    if dominant_period < 2:
                        insight = f"No clear periodicity detected in the time series."
                    else:
                        insight = f"The time series shows a dominant periodicity of approximately {dominant_period:.1f} time units."
                        
                        if len(periods) > 1:
                            insight += f" Secondary periodicities were detected at {', '.join([f'{p:.1f}' for p in periods[1:]])} time units."
                else:
                    insight = "No clear periodicity detected in the time series."
            else:
                result = {
                    "has_periodicity": False,
                    "insight": "No clear periodicity detected in the time series."
                }
                insight = result["insight"]
            
            result["insight"] = insight
            return result
            
        except Exception as e:
            logger.warning(f"Error in periodicity detection: {str(e)}")
            return {
                "has_periodicity": False,
                "error": str(e),
                "insight": "Could not perform periodicity detection."
            }

    def _find_best_arima_orders(
        self, ts: pd.Series, has_seasonality: bool, frequency: str
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]:
        """
        Tìm các parameters tối ưu cho ARIMA/SARIMA
        
        Args:
            ts: Time series cần phân tích
            has_seasonality: Có seasonality không
            frequency: Tần suất của time series
            
        Returns:
            Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]: 
                (p,d,q) cho ARIMA và (P,D,Q,s) cho SARIMA
        """
        try:
            # Đảm bảo dữ liệu không có NaN
            ts_clean = ts.dropna()
            
            if len(ts_clean) < 8:  # Cần ít nhất 8 điểm
                return (1, 0, 0), (0, 0, 0, 0)
            
            # Kiểm tra tính stationary
            d = 0
            adf_result = adfuller(ts_clean)
            if adf_result[1] >= 0.05:  # Non-stationary
                # Thử differencing
                ts_diff = ts_clean.diff().dropna()
                if len(ts_diff) >= 8:  # Đảm bảo có đủ dữ liệu
                    adf_result_diff = adfuller(ts_diff)
                    if adf_result_diff[1] < 0.05:
                        d = 1
                    else:
                        # Thử differencing lần 2
                        ts_diff2 = ts_diff.diff().dropna()
                        if len(ts_diff2) >= 8:  # Đảm bảo có đủ dữ liệu
                            adf_result_diff2 = adfuller(ts_diff2)
                            if adf_result_diff2[1] < 0.05:
                                d = 2
                            else:
                                d = 1  # Mặc định nếu vẫn không stationary
                        else:
                            d = 1
                else:
                    d = 0
            
            # Dựa vào ACF/PACF để xác định parameters
            n_lags = min(40, len(ts_clean) // 4)
            
            # Áp dụng differencing nếu cần
            ts_used = ts_clean
            if d == 1:
                ts_used = ts_clean.diff().dropna()
            elif d == 2:
                ts_used = ts_clean.diff().diff().dropna()
            
            # Kiểm tra lại xem có đủ dữ liệu sau differencing
            if len(ts_used) < 8:
                return (1, d, 1), (1, 0, 1, 12) if has_seasonality else (0, 0, 0, 0)
                
            acf_values = acf(ts_used, nlags=n_lags, fft=True)
            pacf_values = pacf(ts_used, nlags=n_lags, method="ywmle")
            
            # Xác định AR order (p) từ PACF
            # p là lag đầu tiên mà PACF giảm xuống dưới confidence limit
            confidence_limit = 1.96 / np.sqrt(len(ts_used))
            
            # Sử dụng numpy operations hiệu quả hơn
            p = 0
            for i in range(1, min(10, len(pacf_values))):
                if abs(pacf_values[i]) < confidence_limit:
                    p = i - 1
                    break
            if p == 0:  # Nếu không tìm thấy, sử dụng giá trị mặc định
                p = 1
            
            # Xác định MA order (q) từ ACF
            # q là lag đầu tiên mà ACF giảm xuống dưới confidence limit
            q = 0
            for i in range(1, min(10, len(acf_values))):
                if abs(acf_values[i]) < confidence_limit:
                    q = i - 1
                    break
            if q == 0:  # Nếu không tìm thấy, sử dụng giá trị mặc định
                q = 1
            
            # Giới hạn p và q để tránh quá phức tạp
            p = min(p, 3)
            q = min(q, 3)
            
            # ARIMA order
            best_order = (p, d, q)
            
            # SARIMA seasonal order nếu có seasonality
            best_seasonal_order = (0, 0, 0, 0)
            
            if has_seasonality:
                # Xác định seasonal period dựa vào frequency
                period_map = {"D": 7, "W": 52, "M": 12, "Q": 4, "Y": 1, "H": 24}
                seasonal_period = period_map.get(frequency, 12)  # Default to 12 if unknown
                
                # Đơn giản hóa, sử dụng (1,0,1,seasonal_period)
                # Thực tế, nên thử nhiều kết hợp P và Q
                best_seasonal_order = (1, 0, 1, seasonal_period)
            
            return best_order, best_seasonal_order
        except Exception as e:
            logger.warning(f"Error finding ARIMA orders: {str(e)}")
            # Fallback to default values
            return (1, 1, 1), (1, 0, 1, 12) if has_seasonality else (0, 0, 0, 0)

    def _perform_time_series_cross_validation(
        self,
        ts: pd.Series,
        order: Tuple[int, int, int],
        seasonal_order: Optional[Tuple[int, int, int, int]] = None,
        exog_data: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Thực hiện cross-validation cho mô hình time series
        
        Args:
            ts: Time series cần đánh giá
            order: ARIMA order (p,d,q)
            seasonal_order: SARIMA seasonal order (P,D,Q,s)
            exog_data: Dữ liệu exogenous nếu có
            
        Returns:
            Dict: Kết quả cross-validation
        """
        try:
            # Đảm bảo dữ liệu không có NaN
            ts_clean = ts.dropna()
            
            # Số fold cho CV, ít nhất 3, tối đa 5
            k_folds = min(5, max(3, len(ts_clean) // 20))
            
            # Minimum size for initial window
            min_train_size = max(8, len(ts_clean) // 2)  # Đảm bảo ít nhất 8 điểm
            
            # Setup cross-validation
            errors = {"mae": [], "rmse": [], "mape": []}
            
            for i in range(k_folds):
                # Split data
                train_end = min_train_size + i * (len(ts_clean) - min_train_size) // k_folds
                
                # Ensure we have enough data
                if train_end < 8 or len(ts_clean) - train_end < 1:
                    continue
                
                train = ts_clean.iloc[:train_end]
                test = ts_clean.iloc[train_end:train_end+1]  # One-step forecast
                
                # Prepare exogenous variables if needed
                train_exog = None
                test_exog = None
                if exog_data is not None:
                    if len(exog_data) >= train_end:
                        train_exog = exog_data.iloc[:train_end]
                        
                        if train_end < len(exog_data):
                            test_exog = exog_data.iloc[train_end:train_end+1]
                
                # Fit model
                try:
                    if seasonal_order and seasonal_order[-1] > 0:
                        model = SARIMAX(
                            train, 
                            order=order, 
                            seasonal_order=seasonal_order,
                            exog=train_exog,
                            enforce_stationarity=False,
                            enforce_invertibility=False
                        )
                    else:
                        model = ARIMA(
                            train,
                            order=order,
                            exog=train_exog
                        )
                    
                    model_fit = model.fit(disp=False)
                    
                    # Forecast
                    forecast = model_fit.forecast(steps=1, exog=test_exog)
                    
                    # Calculate errors
                    actual = test.values[0]
                    predicted = forecast[0]
                    
                    errors["mae"].append(abs(actual - predicted))
                    errors["rmse"].append((actual - predicted) ** 2)
                    
                    if actual != 0:
                        errors["mape"].append(abs((actual - predicted) / actual) * 100)
                except Exception as e:
                    logger.warning(f"Error in fold {i} of cross-validation: {str(e)}")
                    continue
            
            # Calculate average errors
            if errors["mae"]:
                avg_mae = sum(errors["mae"]) / len(errors["mae"])
                avg_rmse = (sum(errors["rmse"]) / len(errors["rmse"])) ** 0.5
                
                if errors["mape"]:
                    avg_mape = sum(errors["mape"]) / len(errors["mape"])
                else:
                    avg_mape = None
                
                return {
                    "mae": float(avg_mae),
                    "rmse": float(avg_rmse),
                    "mape": float(avg_mape) if avg_mape is not None else None,
                    "n_folds": len(errors["mae"])
                }
            else:
                return {
                    "error": "Cross-validation failed for all folds"
                }
        except Exception as e:
            logger.warning(f"Error in time series cross-validation: {str(e)}")
            return {"error": str(e)}

    def _make_forecast(
        self,
        ts: pd.Series,
        forecast_periods: int,
        is_stationary: bool,
        has_seasonality: bool,
        order: Tuple[int, int, int],
        seasonal_order: Tuple[int, int, int, int],
        return_confidence: bool,
        exog_data: Optional[pd.DataFrame] = None,
        forecast_exog: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Tạo dự báo theo model phù hợp
        
        Args:
            ts: Time series cần dự báo
            forecast_periods: Số kỳ dự báo
            is_stationary: Series có stationary không
            has_seasonality: Series có seasonality không
            order: (p,d,q) order cho ARIMA
            seasonal_order: (P,D,Q,s) seasonal order cho SARIMA
            return_confidence: Có trả về khoảng tin cậy không
            exog_data: Dữ liệu exogenous cho training
            forecast_exog: Dữ liệu exogenous cho forecast
            
        Returns:
            Dict: Kết quả dự báo
        """
        try:
            # Đảm bảo dữ liệu không có NaN
            ts_clean = ts.dropna()
            
            # Lựa chọn model thích hợp
            if has_seasonality and seasonal_order[-1] > 0:
                logger.info(f"Using SARIMA model with order={order}, seasonal_order={seasonal_order}")
                model = SARIMAX(
                    ts_clean, 
                    order=order, 
                    seasonal_order=seasonal_order,
                    exog=exog_data,
                    enforce_stationarity=is_stationary,
                    enforce_invertibility=False
                )
            else:
                logger.info(f"Using ARIMA model with order={order}")
                model = ARIMA(
                    ts_clean,
                    order=order,
                    exog=exog_data,
                    enforce_stationarity=is_stationary,
                    enforce_invertibility=False
                )
            
            # Fit model
            model_fit = model.fit(disp=False, method='powell')  # Use robust powell method
            
            # Dự báo
            forecast = model_fit.forecast(steps=forecast_periods, exog=forecast_exog)
            
            # Tạo dữ liệu dự báo
            last_date = ts_clean.index[-1]
            if isinstance(ts_clean.index, pd.DatetimeIndex):
                # Try to infer frequency first from the index
                freq = pd.infer_freq(ts_clean.index)
                
                if not freq:
                    # If we can't infer the frequency, calculate average time delta
                    if len(ts_clean) >= 2:
                        time_deltas = pd.Series(ts_clean.index[1:]) - pd.Series(ts_clean.index[:-1])
                        avg_delta = time_deltas.median()
                        future_dates = [last_date + (i+1) * avg_delta for i in range(forecast_periods)]
                    else:
                        # Default to daily if only one point
                        future_dates = pd.date_range(start=last_date, periods=forecast_periods + 1, freq='D')[1:]
                else:
                    future_dates = pd.date_range(start=last_date, periods=forecast_periods + 1, freq=freq)[1:]
            else:
                # If not datetime index, use numeric index
                last_idx = len(ts_clean) - 1
                future_dates = list(range(last_idx + 1, last_idx + forecast_periods + 1))
            
            # Format kết quả
            forecast_data = []
            
            for i, (date, value) in enumerate(zip(future_dates, forecast)):
                forecast_point = {
                    "period": i + 1,
                    "date": date.isoformat() if isinstance(date, pd.Timestamp) else str(date),
                    "forecast": float(value)
                }
                
                # Thêm khoảng tin cậy nếu cần
                if return_confidence:
                    try:
                        conf_int = model_fit.get_forecast(steps=forecast_periods, exog=forecast_exog).conf_int()
                        if i < len(conf_int):
                            forecast_point["lower_bound"] = float(conf_int.iloc[i, 0])
                            forecast_point["upper_bound"] = float(conf_int.iloc[i, 1])
                    except Exception as e:
                        logger.warning(f"Could not generate confidence intervals: {str(e)}")
                
                forecast_data.append(forecast_point)
            
            # Metrics từ model fit
            metrics = {
                "aic": float(model_fit.aic) if hasattr(model_fit, 'aic') else None,
                "bic": float(model_fit.bic) if hasattr(model_fit, 'bic') else None,
                "mae": float(np.mean(np.abs(model_fit.resid))),
                "mse": float(np.mean(model_fit.resid**2))
            }
            
            # Summary và insights
            insights = self._generate_forecast_insights(forecast, ts_clean.iloc[-1], forecast_periods)
            
            return {
                "forecast_data": forecast_data,
                "metrics": metrics,
                "insights": insights
            }
        except Exception as e:
            logger.error(f"Error making forecast: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def _generate_forecast_insights(self, forecast: np.ndarray, last_value: float, forecast_periods: int) -> List[str]:
        """Generate insights from forecast results"""
        insights = []
        
        # Trend direction
        if forecast[-1] > last_value:
            pct_change = (forecast[-1] / last_value - 1) * 100
            insights.append(
                f"The forecast predicts an overall increasing trend of {pct_change:.1f}% "
                f"over the next {forecast_periods} periods."
            )
        elif forecast[-1] < last_value:
            pct_change = (1 - forecast[-1] / last_value) * 100
            insights.append(
                f"The forecast predicts an overall decreasing trend of {pct_change:.1f}% "
                f"over the next {forecast_periods} periods."
            )
        else:
            insights.append(
                f"The forecast predicts a stable pattern over the next {forecast_periods} periods."
            )
        
        # Pattern in the forecast
        if len(forecast) >= 3:
            # Check for consistent pattern
            is_increasing = np.all(np.diff(forecast) > 0)
            is_decreasing = np.all(np.diff(forecast) < 0)
            
            if is_increasing:
                insights.append("The forecast shows a consistent increasing pattern.")
            elif is_decreasing:
                insights.append("The forecast shows a consistent decreasing pattern.")
            else:
                # Check for oscillating pattern - sử dụng numpy operations
                direction_changes = np.sum(np.diff(np.sign(np.diff(forecast))) != 0)
                
                if direction_changes >= len(forecast) // 2:
                    insights.append("The forecast shows a fluctuating pattern with frequent changes in direction.")
                else:
                    insights.append("The forecast shows some fluctuations without a clear consistent pattern.")
        
        # Add extreme values if present
        max_forecast = np.max(forecast)
        min_forecast = np.min(forecast)
        max_idx = np.argmax(forecast) + 1
        min_idx = np.argmin(forecast) + 1
        
        if max_forecast > last_value * 1.2:  # 20% increase
            insights.append(f"The forecast reaches a peak value in period {max_idx}.")
        
        if min_forecast < last_value * 0.8:  # 20% decrease
            insights.append(f"The forecast reaches a minimum value in period {min_idx}.")
        
        return insights

    def _generate_time_series_recommendations(
        self, 
        ts: pd.Series, 
        stationarity_result: Dict, 
        decomposition_result: Dict, 
        changepoint_result: Dict, 
        periodicity_result: Dict
    ) -> List[str]:
        """
        Tạo khuyến nghị cho phân tích chuỗi thời gian
        
        Args:
            ts: Time series đã phân tích
            stationarity_result: Kết quả phân tích stationarity
            decomposition_result: Kết quả phân tích decomposition
            changepoint_result: Kết quả phát hiện changepoints
            periodicity_result: Kết quả phát hiện chu kỳ
            
        Returns:
            List[str]: Danh sách khuyến nghị
        """
        recommendations = []
        
        # Khuyến nghị về stationarity
        if stationarity_result.get("is_stationary") is False:
            recommendations.append(
                "Apply differencing to make the time series stationary before modeling."
            )
            
            # Nếu heteroscedastic, đề xuất transform
            if not stationarity_result.get("homoscedastic", True):
                recommendations.append(
                    "Consider applying log or Box-Cox transformation to stabilize variance."
                )
        
        # Khuyến nghị về seasonality
        has_seasonality = decomposition_result.get("has_seasonality", False)
        if has_seasonality:
            recommendations.append(
                "Use seasonal models (like SARIMA) to capture the seasonal patterns in the data."
            )
        
        # Khuyến nghị về trend
        has_trend = decomposition_result.get("has_trend", False)
        if has_trend:
            trend_direction = decomposition_result.get("trend_direction", "unknown")
            if trend_direction in ["increasing", "decreasing"]:
                recommendations.append(
                    f"The series shows a {trend_direction} trend. Consider using models that can capture this directional movement."
                )
        
        # Khuyến nghị về model selection
        if has_seasonality:
            recommendations.append(
                "SARIMA is recommended for this time series due to its seasonal patterns."
            )
        elif has_trend:
            recommendations.append(
                "ARIMA with appropriate differencing is suitable for capturing the trend in this time series."
            )
        else:
            recommendations.append(
                "Simple forecasting methods like ARIMA or exponential smoothing may be sufficient for this time series."
            )
        
        # Khuyến nghị nếu có changepoints
        if changepoint_result.get("has_changepoints", False):
            recommendations.append(
                "The time series contains structural changes. Consider using piecewise models or including regime variables."
            )
        
        # Khuyến nghị nếu có periodicity
        if periodicity_result.get("has_periodicity", False):
            recommendations.append(
                "The detected periodicity should be incorporated into the modeling approach, possibly using Fourier terms."
            )
        
        # Khuyến nghị về outliers
        if ts is not None and len(ts) > 0:
            # Sử dụng numpy operations hiệu quả hơn
            z_scores = np.abs((ts - ts.mean()) / ts.std())
            if np.any(z_scores > 3):
                recommendations.append(
                    "Consider treating outliers before modeling to improve forecast accuracy."
                )
        
        # Khuyến nghị về exogenous variables
        recommendations.append(
            "If available, include relevant external variables to improve forecast accuracy."
        )
        
        # Khuyến nghị về evaluation
        recommendations.append(
            "Use time series cross-validation techniques to evaluate model performance more reliably."
        )
        
        return recommendations