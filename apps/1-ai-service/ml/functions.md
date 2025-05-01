# Functions with Parameters in the Data Processing Files

## DataProcessor Class (data_processor.py)

### Core Methods
1. **__init__(self, config: Optional[Dict] = None)**
   - `config`: Optional dictionary of configuration parameters

2. **process(self, df: pd.DataFrame, sample_size: Optional[int] = None, for_modeling: bool = False) -> pd.DataFrame**
   - `df`: Original DataFrame
   - `sample_size`: Optional size to reduce data
   - `for_modeling`: Whether to apply model preparation steps
   - Returns: Processed DataFrame

### Column Type Detection
3. **get_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]**
   - `df`: DataFrame to analyze
   - Returns: Dictionary mapping column types to column names
   - Explain: Retrieves column types with caching for performance optimization.

4. **detect_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]**
   - `df`: DataFrame to analyze
   - Returns: Dictionary mapping column types to column names 
   - Explain: Detects data types of all columns (numeric, categorical, datetime, text, binary, id, gender, email, phone, address, range, name, url, likert)

5. **_detect_id_columns(self, df: pd.DataFrame, threshold: float = 0.9) -> List[str]**
   - `df`: Original DataFrame
   - `threshold`: Ratio threshold to identify ID columns
   - Returns: List of ID columns
   - Explain: Identifies ID/key columns based on uniqueness

6. **_detect_binary_columns(self, df: pd.DataFrame) -> List[str]**
   - `df`: Original DataFrame
   - Returns: List of binary columns
   - Explain: Detects columns with binary values (yes/no, true/false, 0/1).

7. **_detect_likert_scales(self, df: pd.DataFrame) -> List[str]**
   - `df`: DataFrame to analyze
   - Returns: List of Likert scale columns
   - Explain: Identifies columns containing Likert scale ratings (1-5, 1-7, etc.).

8. **_is_gender_column(self, series: pd.Series, col_name: str) -> bool**
   - `series`: Data series to analyze
   - `col_name`: Column name
   - Returns: Boolean indicating if it's a gender column
   - Explain: Checks if a column contains gender information.

9. **_is_email_column(self, series: pd.Series, col_name: str) -> bool**
   - `series`: Data series to analyze
   - `col_name`: Column name
   - Returns: Boolean indicating if it's an email column
   - Explain: Determines if a column has email addresses.

10. **_is_phone_column(self, series: pd.Series, col_name: str) -> bool**
    - `series`: Data series to analyze
    - `col_name`: Column name
    - Returns: Boolean indicating if it's a phone column
    - Explain: Identifies columns with phone numbers.

11. **_is_address_column(self, series: pd.Series, col_name: str) -> bool**
    - `series`: Data series to analyze
    - `col_name`: Column name
    - Returns: Boolean indicating if it's an address column
    - Explain: Detects address columns.

12. **_is_range_column(self, series: pd.Series, col_name: str) -> bool**
    - `series`: Data series to analyze
    - `col_name`: Column name
    - Returns: Boolean indicating if it's a range column
    - Explain: Identifies columns containing value ranges.

13. **_is_name_column(self, series: pd.Series, col_name: str) -> bool**
    - `series`: Data series to analyze
    - `col_name`: Column name
    - Returns: Boolean indicating if it's a name column
    - Explain: Checks if a column contains person names.

14. **_is_url_column(self, series: pd.Series, col_name: str) -> bool**
    - `series`: Data series to analyze
    - `col_name`: Column name
    - Returns: Boolean indicating if it's a URL column
    - Explain: Determines if a column contains URLs.

### Data Cleaning & Preprocessing
15. **normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with normalized column names
    - Explain: Standardizes column names.

16. **remove_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with duplicate columns removed
    - Explain: Identifies and removes duplicate columns.

17. **detect_duplicate_columns(self, df: pd.DataFrame) -> Dict[str, str]**
    - `df`: DataFrame to check
    - Returns: Dictionary mapping duplicate columns to their original columns
    - Explain: Identifies duplicate columns without modifying the DataFrame.

18. **_handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with missing values handled
    - Explain: Imputes or handles missing values using various strategies.

19. **_handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with outliers handled
    - Explain: Detects and handles outliers with multiple methods.

20. **_convert_binary_columns(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: DataFrame to process
    - Returns: DataFrame with binary columns converted to 0/1

21. **_convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with optimized data types
    - Explain: Converts binary columns to 0/1 format.

22. **_should_convert_binary(self, df: pd.DataFrame) -> bool**
    - `df`: DataFrame to analyze
    - Returns: Boolean indicating if binary conversion should be performed
    - Explain: Optimizes data types for memory efficiency.

23. **_convert_binary_to_boolean(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: DataFrame to convert
    - Returns: DataFrame with binary columns converted to Boolean
    - Explain: Converts binary columns to True/False.

24. **_extract_datetime_features(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with extracted datetime features
    - Explain: Extracts features from datetime columns.

### Modeling Preparation
25. **_encode_categorical_columns(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with encoded categorical columns
    - Explain: Encodes categorical columns (one-hot, label, binary encoding).

26. **_encode_label(self, df: pd.DataFrame, col: str, encoding_stats: Dict) -> None**
    - `df`: DataFrame to modify
    - `col`: Column to encode
    - `encoding_stats`: Dictionary to store encoding statistics
    - Explain: Helper method for label encoding.

27. **_normalize_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame**
    - `df`: Original DataFrame
    - Returns: DataFrame with normalized numeric columns
    - Explain: Normalizes numeric columns.

28. **_analyze_features(self, df: pd.DataFrame) -> None**
    - `df`: DataFrame to analyze
    - Explain: Analyzes feature importance.

### Advanced Analysis
29. **identify_performance_bottlenecks(self, df: pd.DataFrame) -> Dict**
    - `df`: Input DataFrame
    - Returns: Dictionary with bottleneck information
    - Explain: Identifies memory and processing bottlenecks.

30. **apply_pca(self, df: pd.DataFrame, numeric_columns: List[str], n_components: float = 0.95) -> Tuple[pd.DataFrame, Dict]**
    - `df`: Input DataFrame
    - `numeric_columns`: List of numeric columns for PCA
    - `n_components`: Number of components or variance to retain
    - Returns: Tuple of reduced DataFrame and component information
    - Explain: Applies Principal Component Analysis for dimensionality reduction.

31. **select_important_features(self, df: pd.DataFrame, target_column: Optional[str] = None, max_features: int = 10) -> List[str]**
    - `df`: DataFrame with data
    - `target_column`: Optional target column
    - `max_features`: Maximum number of features to select
    - Returns: List of important features
    - Explain: Selects the most important features.

32. **remove_noise(self, df: pd.DataFrame, numeric_columns: List[str], method: str = 'moving_avg') -> pd.DataFrame**
    - `df`: Input DataFrame
    - `numeric_columns`: Numeric columns to process
    - `method`: Noise removal method ('wavelet', 'moving_avg', 'low_pass')
    - Returns: DataFrame with noise removed
    - Explain: Reduces noise in numeric data.

## DataValidator Class (data_validator.py)

### Core Methods
1. **__init__(self, config: Optional[Dict] = None)**
   - `config`: Optional dictionary of configuration parameters

2. **validate_dataset(self, df: pd.DataFrame) -> Dict[str, Any]**
   - `df`: DataFrame to validate
   - Returns: Dictionary with validation results
   - Explain: Comprehensive data quality evaluation.

3. **get_quality_summary(self) -> Dict[str, Any]**
   - Returns: Dictionary with quality summary
   - Explain: Provides a summary of data quality.

### Quality Validation Methods
4. **_validate_completeness(self, df: pd.DataFrame) -> Dict[str, Any]**
   - `df`: DataFrame to validate
   - Returns: Dictionary with completeness metrics
   - Explain: Evaluates data completeness (missing values).

5. **_validate_consistency(self, df: pd.DataFrame) -> Dict[str, Any]**
   - `df`: DataFrame to validate
   - Returns: Dictionary with consistency metrics
   - Explain: Assesses data consistency across columns.

6. **_validate_uniqueness(self, df: pd.DataFrame) -> Dict[str, Any]**
   - `df`: DataFrame to validate
   - Returns: Dictionary with uniqueness metrics
   - Explain: Checks for duplicate rows and unique values.

7. **_validate_integrity(self, df: pd.DataFrame) -> Dict[str, Any]**
   - `df`: DataFrame to validate
   - Returns: Dictionary with integrity metrics
   - Explain: Examines data integrity (outliers, range violations).

8. **_validate_accuracy(self, df: pd.DataFrame) -> Dict[str, Any]**
   - `df`: DataFrame to validate
   - Returns: Dictionary with accuracy metrics
   - Explain: Evaluates data accuracy.

### Analysis & Reporting
9. **_detect_issues(self, df: pd.DataFrame, quality_metrics: Dict) -> List[str]**
   - `df`: DataFrame to analyze
   - `quality_metrics`: Dictionary with quality metrics
   - Returns: List of identified issues
   - Explain: Identifies key issues in the dataset.

10. **_generate_recommendations(self, df: pd.DataFrame, quality_metrics: Dict) -> List[str]**
    - `df`: DataFrame to analyze
    - `quality_metrics`: Dictionary with quality metrics
    - Returns: List of recommendations
    - Explain: Creates recommendations for improving data quality.

11. **_compile_regex_patterns(self)**
    - Compiles regex patterns used for validation
    - Explain: Compiles regex patterns for validation.

# Summary of Functions in Data Analysis Files

## DataAnalyzer Class (analyzer.py)

### Core Methods
1. **__init__(self, config_path: Optional[Union[str, Dict]] = None)**
   - `config_path`: Optional path to configuration file or dictionary
   - Initializes the DataAnalyzer with components and configuration settings

2. **run_analysis(self, df: pd.DataFrame, analysis_type: str = "full", file_id: Optional[str] = None, filter_types: Optional[List[str]] = None, use_ml: bool = False, optimize_memory: bool = True, use_parallel: bool = True) -> Dict**
   - `df`: DataFrame to analyze
   - `analysis_type`: Type of analysis ("full", "quality", "statistics", "insights", "visualizations", "advanced", "time_series")
   - `file_id`: Optional file identifier
   - `filter_types`: Optional filter for types of insights/visualizations
   - `use_ml`: Whether to use ML-based insights
   - `optimize_memory`: Whether to optimize memory usage
   - `use_parallel`: Whether to use parallel processing
   - Returns: Comprehensive analysis results dictionary

### Configuration & Utilities
3. **_load_config(self, config_path: Optional[Union[str, Dict]]) -> Dict**
   - `config_path`: Path to config file or dict
   - Returns: Configuration dictionary
   - Loads configuration from file or uses defaults

4. **_sample_dataframe(self, df: pd.DataFrame) -> pd.DataFrame**
   - `df`: Original DataFrame
   - Returns: Sampled DataFrame
   - Takes a sample of large datasets using various methods (random, stratified, systematic, time-based)

5. **_optimize_memory_usage(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]**
   - `df`: Original DataFrame
   - Returns: Memory-optimized DataFrame and optimization metrics
   - Optimizes DataFrame memory usage by adjusting data types

6. **_run_parallel_analysis(self, df: pd.DataFrame, analysis_type: str, analysis_results: Dict, file_id: Optional[str] = None, filter_types: Optional[List[str]] = None, use_ml: bool = False) -> Dict**
   - Runs analysis tasks in parallel using ThreadPoolExecutor
   - Returns: Analysis results

7. **_run_sequential_analysis(self, df: pd.DataFrame, analysis_type: str, analysis_results: Dict, file_id: Optional[str] = None, filter_types: Optional[List[str]] = None, use_ml: bool = False) -> Dict**
   - Runs analysis tasks sequentially
   - Returns: Analysis results

### Column & Dataset Analysis
8. **_detect_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]**
   - `df`: DataFrame to analyze
   - Returns: Dictionary mapping column types to column names

9. **_analyze_dataset_info(self, df: pd.DataFrame) -> Dict**
   - `df`: DataFrame to analyze
   - Returns: Basic dataset information (rows, columns, memory usage, etc.)
   - Provides comprehensive dataset metadata

10. **_detect_duplicate_columns(self, df: pd.DataFrame) -> Dict[str, Any]**
    - `df`: DataFrame to check
    - Returns: Information about duplicate columns

### Statistical Analysis
11. **_run_statistical_analysis(self, df: pd.DataFrame) -> Dict**
    - `df`: DataFrame to analyze
    - Returns: Comprehensive statistical analysis
    - Performs detailed analysis for numeric, categorical, datetime, binary, and other column types

12. **_detect_distribution_type(self, data: pd.Series) -> str**
    - `data`: Series to analyze
    - Returns: Distribution type name ("normal", "log_normal", "uniform", etc.)

13. **_get_correlation_strength(self, corr_val: float) -> str**
    - `corr_val`: Correlation value
    - Returns: Correlation strength description ("strong", "moderate", "weak", "negligible")

### Advanced Analysis
14. **_run_advanced_analysis(self, df: pd.DataFrame) -> Dict**
    - `df`: DataFrame to analyze
    - Returns: Results of advanced analysis techniques
    - Performs PCA, feature importance, outlier detection, clustering, and specialized analysis for various data types

15. **_run_time_series_analysis(self, df: pd.DataFrame) -> Dict**
    - `df`: DataFrame to analyze
    - Returns: Time series analysis results
    - Performs time series analysis if datetime columns are present

### Insights & Recommendations
16. **_generate_insights(self, df: pd.DataFrame, file_id: Optional[str], filter_types: Optional[List[str]], use_ml: bool) -> List[Dict]**
    - Generates insights from data using ML or rule-based approach
    - Returns: List of insights

17. **_generate_visualizations(self, df: pd.DataFrame, file_id: Optional[str], filter_types: Optional[List[str]]) -> List[Dict]**
    - Generates automatic visualizations
    - Returns: List of visualization specifications

18. **_generate_analysis_recommendations(self, df: pd.DataFrame) -> List[str]**
    - `df`: DataFrame to analyze
    - Returns: List of analysis recommendations based on dataset characteristics

19. **_generate_advanced_recommendations(self, df: pd.DataFrame) -> List[str]**
    - `df`: DataFrame to analyze
    - Returns: List of advanced recommendations based on analysis results

### Public API Methods
20. **recommend_charts(self, df: pd.DataFrame, columns: Optional[List[str]] = None, file_id: Optional[str] = None) -> Dict[str, Dict]**
    - Recommends chart types appropriate for the data
    - Returns: Chart recommendations

21. **get_best_charts(self, df: pd.DataFrame, columns: Optional[List[str]] = None, file_id: Optional[str] = None, top_k: int = 5) -> List[Dict]**
    - Gets the top k best chart recommendations
    - Returns: List of best chart specifications

22. **forecast_time_series(self, df: pd.DataFrame, date_col: str, value_col: str, forecast_periods: int = 10, return_confidence: bool = True) -> Dict**
    - `df`: DataFrame with time series data
    - `date_col`: Date column name
    - `value_col`: Value column name
    - `forecast_periods`: Number of periods to forecast
    - `return_confidence`: Whether to include confidence intervals
    - Returns: Time series forecast results

## TimeSeriesAnalyzer Class (time_series.py)

### Core Methods
1. **__init__(self, config: Optional[Dict] = None)**
   - `config`: Optional configuration dictionary
   - Initializes the TimeSeriesAnalyzer

2. **analyze_time_series(self, df: pd.DataFrame, date_col: str, value_col: str) -> Dict**
   - `df`: DataFrame with time series data
   - `date_col`: Date column name
   - `value_col`: Value column name
   - Returns: Comprehensive time series analysis results
   - Performs stationarity checks, decomposition, outlier detection, etc.

3. **forecast_time_series(self, df: pd.DataFrame, date_col: str, value_col: str, forecast_periods: int = 10, return_confidence: bool = True, exogenous_vars: Optional[List[str]] = None) -> Dict**
   - `df`: DataFrame with time series data
   - `date_col`: Date column name
   - `value_col`: Value column name
   - `forecast_periods`: Number of periods to forecast
   - `return_confidence`: Whether to include confidence intervals
   - `exogenous_vars`: Optional list of exogenous variables
   - Returns: Forecast results

### Time Series Analysis Methods
4. **_auto_resample_time_series(self, ts: pd.Series) -> Tuple[pd.Series, str]**
   - `ts`: Time series data
   - Returns: Resampled time series and frequency string
   - Automatically determines appropriate frequency and resamples data

5. **_detect_time_series_outliers(self, ts: pd.Series) -> Dict**
   - `ts`: Time series data
   - Returns: Outlier detection results
   - Uses Z-score, IQR, and Isolation Forest methods

6. **_handle_time_series_outliers(self, ts: pd.Series) -> pd.Series**
   - `ts`: Time series data
   - Returns: Time series with outliers handled
   - Replaces outliers with rolling median values

7. **_check_stationarity(self, ts: pd.Series) -> Dict**
   - `ts`: Time series data
   - Returns: Stationarity test results
   - Uses ADF test and variance analysis

8. **_decompose_time_series(self, ts: pd.Series, frequency: str) -> Dict**
   - `ts`: Time series data
   - `frequency`: Data frequency string
   - Returns: Time series decomposition results
   - Breaks down series into trend, seasonality, and residual components

9. **_analyze_autocorrelation(self, ts: pd.Series) -> Dict**
   - `ts`: Time series data
   - Returns: Autocorrelation analysis results
   - Computes ACF and PACF with significance testing

10. **_suggest_arima_orders_from_acf_pacf(self, acf_values, pacf_values, confidence_limit)**
    - Suggests AR and MA orders based on ACF/PACF patterns
    - Returns: Recommended p and q orders for ARIMA models

11. **_detect_changepoints(self, ts: pd.Series) -> Dict**
    - `ts`: Time series data
    - Returns: Changepoint detection results
    - Identifies structural changes in the time series

12. **_detect_periodicity(self, ts: pd.Series) -> Dict**
    - `ts`: Time series data
    - Returns: Periodicity detection results
    - Identifies cyclic patterns using periodogram analysis

### Forecasting Methods
13. **_find_best_arima_orders(self, ts: pd.Series, has_seasonality: bool, frequency: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]**
    - `ts`: Time series data
    - `has_seasonality`: Whether seasonality is present
    - `frequency`: Data frequency string
    - Returns: ARIMA and SARIMA orders
    - Determines optimal parameters for ARIMA/SARIMA models

14. **_perform_time_series_cross_validation(self, ts: pd.Series, order: Tuple[int, int, int], seasonal_order: Optional[Tuple[int, int, int, int]] = None, exog_data: Optional[pd.DataFrame] = None) -> Dict**
    - `ts`: Time series data
    - `order`: ARIMA order
    - `seasonal_order`: SARIMA seasonal order
    - `exog_data`: Exogenous variables data
    - Returns: Cross-validation results
    - Evaluates forecast accuracy using time series cross-validation

15. **_make_forecast(self, ts: pd.Series, forecast_periods: int, is_stationary: bool, has_seasonality: bool, order: Tuple[int, int, int], seasonal_order: Tuple[int, int, int, int], return_confidence: bool, exog_data: Optional[pd.DataFrame] = None, forecast_exog: Optional[pd.DataFrame] = None) -> Dict**
    - `ts`: Time series data
    - Various model parameters
    - Returns: Forecast results
    - Creates forecasts with appropriate time series models

### Insight Generation
16. **_generate_forecast_insights(self, forecast: np.ndarray, last_value: float, forecast_periods: int) -> List[str]**
    - `forecast`: Forecast values
    - `last_value`: Last observed value
    - `forecast_periods`: Number of periods forecast
    - Returns: List of insights about the forecast

17. **_generate_time_series_recommendations(self, ts: pd.Series, stationarity_result: Dict, decomposition_result: Dict, changepoint_result: Dict, periodicity_result: Dict) -> List[str]**
    - Various analysis results
    - Returns: List of recommendations for time series modeling
    - Suggests appropriate modeling approaches based on analysis

18. **_generate_decomposition_insight(self, has_trend: bool, has_seasonality: bool, trend_direction: str, trend_strength: float, seasonality_strength: float) -> str**
    - Various decomposition parameters
    - Returns: Insight string about time series composition
    - Generates human-readable insight about time series components

# Summary of Functions in charts.py, insights.py, and recommender.py

## charts.py (ChartGenerator)

The `ChartGenerator` class creates advanced data visualizations with the following functions:

1. **Core Methods**
   - `__init__(config_path)`: Initializes the chart generator with configuration settings
   - `generate_automatic_charts(df, file_id, chart_types, sample_threshold)`: Automatically creates appropriate visualizations based on data analysis
   - `_detect_column_types(df)`: Detects column data types using the DataProcessor
   - `_generate_df_hash(df)`: Creates a hash key for caching visualizations

2. **Chart Creation Methods**
   - `_create_distribution_chart(df, column, file_id, title)`: Creates histogram for numeric column with distribution analysis
   - `_create_categorical_chart(df, column, file_id, title)`: Creates bar chart for categorical data with entropy analysis
   - `_create_time_series_chart(df, time_column, value_column, file_id, title)`: Creates time series chart with trend detection
   - `_create_correlation_chart(df, columns, file_id, title)`: Creates heatmap with multicollinearity detection
   - `_create_scatter_chart(df, x_column, y_column, file_id, title)`: Creates scatter plot with relationship analysis
   - `_create_pie_chart(df, column, file_id, title)`: Creates pie chart with distribution balance metrics
   - `_create_group_chart(df, category_column, value_column, file_id, title)`: Creates grouped chart with statistical testing
   - `_create_box_plot(df, column, file_id, title)`: Creates box plot with outlier analysis
   - `_create_grouped_distribution(df, category_column, value_column, file_id, title)`: Creates grouped histograms with statistical comparison
   - `_create_likert_chart(df, column, file_id, title)`: Creates specialized chart for Likert scales
   - `_create_binary_chart(df, column, file_id, title)`: Creates charts for binary columns
   - `_create_word_cloud(df, column, file_id, title)`: Creates word cloud for text columns

3. **Advanced Visualization**
   - `create_time_series_visualization(df, time_column, value_column, aggregation, file_id)`: Creates time series visualization with trend and seasonality detection

## insights.py (InsightGenerator)

The `InsightGenerator` class generates data insights using both ML and rule-based approaches:

1. **Core Methods**
   - `__init__(config_path)`: Initializes with Mistral AI model and configurations
   - `generate_insights(df, config, file_id, insight_types)`: Creates insights using ML-based approach
   - `generate_rule_based_insights(df, file_id, insight_types)`: Creates insights using rule-based approach

2. **ML-based Insight Methods**
   - `_create_summary_insight_with_mistral(df, file_id)`: Creates dataset overview using Mistral AI
   - `_create_distribution_insights_with_mistral(df, file_id)`: Analyzes distributions with Mistral AI
   - `_create_correlation_insights_with_mistral(df, correlation_threshold, file_id)`: Identifies correlations with Mistral AI
   - `_create_trend_insights_with_mistral(df, file_id)`: Detects trends with Mistral AI
   - `_create_outlier_insights_with_mistral(df, file_id)`: Finds outliers with Mistral AI
   - `_create_pattern_insights_with_mistral(df, file_id)`: Discovers patterns with Mistral AI
   - `_prepare_column_summary(df, column)`: Prepares data summaries for Mistral AI
   - `_generate_comprehensive_insights(df, insight_types, file_id)`: Creates integrated insights using Mistral AI

3. **Rule-based Insight Methods**
   - `_create_summary_insight(df, file_id)`: Creates dataset summary
   - `_create_distribution_insights(df, file_id)`: Analyzes distributions
   - `_create_correlation_insights(df, file_id)`: Identifies correlations
   - `_create_trend_insights(df, file_id)`: Detects trends
   - `_create_outlier_insights(df, file_id)`: Finds outliers
   - `_create_pattern_insights(df, file_id)`: Discovers patterns
   - `_detect_id_columns(df, threshold)`: Detects ID columns
   - `_detect_datetime_columns(df)`: Detects datetime columns
   - `_prepare_dataset_summary(df)`: Prepares comprehensive dataset summary

4. **Specialized Insight Methods**
   - `_create_binary_insights(df, binary_cols, file_id)`: Insights for binary columns
   - `_create_likert_insights(df, likert_cols, file_id)`: Insights for Likert scale columns
   - `_create_gender_insights(df, gender_cols, file_id)`: Insights for gender columns
   - `_get_country_name(country_code)`: Helper for country identification
   - `_create_range_insights(df, range_cols, file_id)`: Insights for range columns
   - `_create_text_insights(df, text_cols, file_id)`: Insights for text columns

## recommender.py (ChartRecommender)

The `ChartRecommender` class recommends and creates appropriate visualizations:

1. **Core Methods**
   - `__init__(config_path)`: Initializes with configuration and component references
   - `_load_config(config_path)`: Loads configuration settings
   - `recommend_charts(df, columns, file_id)`: Provides comprehensive chart recommendations
   - `get_best_charts(df, columns, top_k, file_id)`: Returns top chart recommendations with diversity
   - `create_custom_visualization(df, columns, chart_type, file_id, title, description)`: Creates custom visualizations
   - `create_recommended_chart(df, columns, chart_type, file_id)`: Creates charts based on recommendations
   - `generate_all_charts(df, file_id, top_k)`: Creates multiple recommended charts

2. **Data Analysis Methods**
   - `_validate_data_quality(df)`: Evaluates data quality for better recommendations
   - `_analyze_column_types(df)`: Analyzes column types using DataProcessor
   - `_analyze_feature_importance(df, numeric_cols)`: Assesses feature importance
   - `_generate_df_hash(df)`: Creates hash key for caching

3. **Single Column Recommendations**
   - `_recommend_numeric_column(df, column)`: Recommends charts for numeric columns
   - `_recommend_categorical_column(df, column)`: Recommends charts for categorical columns
   - `_recommend_datetime_column(df, column)`: Recommends charts for datetime columns
   - `_recommend_likert_column(df, column)`: Recommends charts for Likert scales
   - `_recommend_binary_column(df, column)`: Recommends charts for binary columns
   - `_recommend_text_column(df, column)`: Recommends charts for text columns
   - `_recommend_range_column(df, column)`: Recommends charts for range columns

4. **Two-Column Recommendations**
   - `_recommend_numeric_vs_numeric(df, col1, col2)`: Recommendations for numeric-numeric pairs
   - `_recommend_categorical_vs_numeric(df, cat_col, num_col)`: Recommendations for categorical-numeric pairs
   - `_recommend_datetime_vs_numeric(df, dt_col, num_col)`: Recommendations for datetime-numeric pairs
   - `_recommend_categorical_vs_categorical(df, col1, col2)`: Recommendations for categorical-categorical pairs
   - `_recommend_datetime_vs_datetime(df, col1, col2)`: Recommendations for datetime-datetime pairs
   - `_recommend_datetime_vs_categorical(df, dt_col, cat_col)`: Recommendations for datetime-categorical pairs
   - `_recommend_binary_vs_numeric(df, bin_col, num_col)`: Recommendations for binary-numeric pairs
   - `_recommend_likert_vs_likert(df, likert1, likert2)`: Recommendations for likert-likert pairs

5. **Multi-Column Recommendations**
   - `_recommend_numeric_datetime_categorical(df, num_col, dt_col, cat_col)`: Three-way recommendations
   - `_recommend_two_numeric_one_categorical(df, num_col1, num_col2, cat_col)`: Three-way recommendations
   - `_recommend_three_numeric(df, num_col1, num_col2, num_col3)`: Three-way recommendations
   - `_recommend_correlation_analysis(df, numeric_cols)`: Correlation analysis recommendations
   - `_recommend_time_series_analysis(df, dt_col, numeric_cols)`: Time series analysis recommendations

# DateTimeProcessor Class (datetime_utils.py)

## Core Methods
1. **__init__(self, country_code: str = 'VN', locale_setting: str = None)**
   - `country_code`: Country code for holiday detection (default: 'VN')
   - `locale_setting`: Optional locale configuration for date formatting
   - Initializes various date format patterns, holiday calendars, and caching

## Format Detection & Conversion
2. **detect_datetime_format(self, sample_values: List[str]) -> Optional[str]**
   - `sample_values`: List of datetime strings to analyze
   - Returns: Detected datetime format or None
   - Uses caching, pattern matching, and frequency analysis for efficient format detection

3. **convert_to_datetime(self, series: Union[pd.Series, np.ndarray, List], preferred_formats: Optional[List[str]] = None, errors: str = 'coerce') -> pd.Series**
   - `series`: Data to convert to datetime
   - `preferred_formats`: Optional list of datetime formats to try first
   - `errors`: How to handle errors ('raise', 'coerce', 'ignore')
   - Returns: Series of datetime values
   - Handles multiple formats including timestamps, Excel dates, and string dates

## Feature Extraction & Analysis
4. **extract_datetime_features(self, df: pd.DataFrame, datetime_column: str, cyclical_encoding: bool = True, drop_original: bool = False, add_holidays: bool = False, include_lags: bool = False, lag_periods: List[int] = [1, 7, 30]) -> Tuple[pd.DataFrame, List[str]]**
   - `df`: Input DataFrame
   - `datetime_column`: Name of datetime column
   - `cyclical_encoding`: Whether to use cyclical encoding for periodic features
   - `drop_original`: Whether to drop the original datetime column
   - `add_holidays`: Whether to add holiday-related features
   - `include_lags`: Whether to add lagged features
   - `lag_periods`: List of periods for lag features
   - Returns: DataFrame with extracted features and list of new feature names
   - Creates year, month, day, hour, weekday, and other temporal features

5. **analyze_datetime_distribution(self, series: pd.Series) -> Dict**
   - `series`: Datetime series to analyze
   - Returns: Dictionary with distribution analysis
   - Analyzes time gaps, seasonality, frequency, and distribution patterns

## Helper Methods
6. **_clean_datetime_string(self, value: str) -> str**
   - `value`: Datetime string to clean
   - Returns: Cleaned datetime string
   - Normalizes various date formats, handles month names in multiple languages

7. **_check_if_timestamp(self, samples: List[str]) -> bool**
   - `samples`: List of strings to check
   - Returns: True if samples appear to be Unix timestamps
   - Uses pattern matching and range validation

8. **_analyze_month_names(self, samples: List[str]) -> Optional[str]**
   - `samples`: List of datetime strings
   - Returns: Format string based on month name patterns, or None
   - Detects formats with month names (Jan, February, etc.)

9. **_analyze_datetime_pattern(self, samples: List[str]) -> Optional[str]**
   - `samples`: List of datetime strings
   - Returns: Detected pattern or None
   - Analyzes delimiters and component ordering

10. **_detect_timeseries_frequency(self, time_diffs_seconds: np.ndarray) -> str**
    - `time_diffs_seconds`: Array of time differences in seconds
    - Returns: String describing detected frequency (hourly, daily, weekly, etc.)
    - Analyzes typical time gaps between data points

11. **_detect_seasonality(self, datetime_series: pd.Series) -> Dict**
    - `datetime_series`: Series of datetime values
    - Returns: Dictionary with seasonality analysis
    - Detects patterns by day of week, month, quarter, and special days

## Global Functions (Wrappers & Utilities)
12. **convert_to_datetime(series, preferred_formats=None, errors='coerce')**
    - Wrapper for DateTimeProcessor.convert_to_datetime using a global instance

13. **extract_datetime_features(df, datetime_column, cyclical_encoding=True, drop_original=False, add_holidays=False, country_code=None)**
    - Wrapper for DateTimeProcessor.extract_datetime_features using a global instance

14. **analyze_datetime_distribution(series, country_code=None)**
    - Wrapper for DateTimeProcessor.analyze_datetime_distribution using a global instance

15. **is_datetime(series: Union[pd.Series, List, np.ndarray], threshold: float = 0.85, sample_size: int = 100, strict: bool = False) -> bool**
    - `series`: Data to check
    - `threshold`: Minimum success rate for conversion
    - `sample_size`: Number of samples to test
    - `strict`: Whether to require all values to convert successfully
    - Returns: True if data appears to be datetime
    - Optimized for performance with sampling and early termination

16. **is_datetime_column(df: pd.DataFrame, column_name: str, threshold: float = 0.85) -> bool**
    - `df`: DataFrame to check
    - `column_name`: Column name to check
    - `threshold`: Minimum success rate
    - Returns: True if column appears to contain datetime values
    - Convenience wrapper for checking DataFrame columns

17. **detect_datetime_columns(df: pd.DataFrame, threshold: float = 0.85, sample_size: int = 100) -> List[str]**
    - `df`: DataFrame to analyze
    - `threshold`: Minimum success rate
    - `sample_size`: Number of samples to test
    - Returns: List of column names containing datetime values
    - Identifies all datetime columns in a DataFrame

18. **identify_date_format(value_str: str) -> str**
    - `value_str`: String to analyze
    - Returns: Format description ('timestamp', 'iso', 'dmy', 'mdy', 'ymd', etc.)
    - Quick individual format detection for a single string

This module uses optimization techniques including:
- Numba JIT compilation for time difference calculations
- LRU caching for frequent operations
- Vectorized operations with NumPy
- Early termination in detection functions
- Pattern-based grouping to minimize format testing

## ModelManager (model_manager.py)

### ModelManager Class

1. **get_instance(cls, config: Optional[Dict[str, Any]] = None)**
   - `config`: Optional configuration dictionary
   - Returns: Singleton instance of ModelManager
   - Class method implementing the Singleton pattern to avoid loading multiple models

2. **__init__(self, config: Optional[Dict[str, Any]] = None)**
   - `config`: Optional configuration dictionary
   - Initializes ModelManager with optional configuration
   - Sets up tracking for model loading state

3. **load_model(self, force_reload: bool = False) -> Dict[str, Any]**
   - `force_reload`: Whether to reload the model if already loaded
   - Returns: Dictionary containing model, tokenizer, and configuration
   - Loads model from Hugging Face or local storage
   - Includes handling for quantization, LoRA adapters, and flash attention

4. **get_model_attributes(self)**
   - Returns: Dictionary with model attributes for KV cache calculations
   - Gets attributes including number of layers, heads, hidden size, and head dimensions

5. **unload_model(self)**
   - Frees memory by destroying the model
   - Performs garbage collection and CUDA cache clearing

6. **is_model_available(self) -> bool**
   - Returns: Boolean indicating if model is ready to use
   - Property that checks if model and tokenizer are loaded
   
This class implements a simplified model manager focused on Mistral models, with features:
- Singleton pattern to prevent multiple model loads
- Quantization support (4-bit and 8-bit)
- LoRA adapter integration
- Flash Attention 2 support
- Local model caching
- Memory management


## PostgreSQL Connector (postgres_connector.py)

### PostgreSQLConnector Class

1. **__init__(self, connection_string: Optional[str] = None)**
   - `connection_string`: PostgreSQL connection string (defaults to "postgresql://ecommerce:ecommerce@localhost:5432/datasense")
   - Initializes the PostgreSQL connector and tests the connection

2. **_test_connection(self)**
   - Tests the database connection by executing a simple SELECT query
   - Raises an exception if connection fails

3. **execute_query(self, query: str) -> Tuple[List[Dict[str, Any]], List[str]]**
   - `query`: SQL query to execute
   - Returns: Tuple with query results (list of dictionaries) and column names
   - Executes SQL query and returns results with column names

4. **get_tables(self) -> List[str]**
   - Returns: List of table names in the database
   - Retrieves all table names from the public schema

5. **get_table_schema(self, table_name: str) -> Dict[str, Any]**
   - `table_name`: Name of the table to describe
   - Returns: Dictionary with detailed table schema information
   - Retrieves columns, primary keys, foreign keys, and row count

6. **get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]**
   - `table_name`: Table name to sample
   - `limit`: Maximum number of rows to return
   - Returns: List of sample rows as dictionaries
   - Gets sample data from specified table

7. **query_to_dataframe(self, query: str) -> pd.DataFrame**
   - `query`: SQL query to execute
   - Returns: Query results as a pandas DataFrame
   - Executes SQL query and returns results as DataFrame

### PostgreSQL LangChain Tools

#### PostgreSQLQueryTool Class

1. **__init__(self, connector: Optional[PostgreSQLConnector] = None)**
   - `connector`: Optional PostgreSQLConnector instance
   - Initializes the tool with a connector

2. **_run(self, query: str) -> str**
   - `query`: SQL query to execute
   - Returns: JSON-formatted query results or error message
   - Executes SQL query and returns results in a readable format

#### PostgreSQLSchemaTool Class

1. **__init__(self, connector: Optional[PostgreSQLConnector] = None)**
   - `connector`: Optional PostgreSQLConnector instance
   - Initializes the tool with a connector

2. **_run(self, table_name: str = "") -> str**
   - `table_name`: Optional table name to describe
   - Returns: List of tables or detailed schema for specific table
   - Gets schema information for database or specific table

#### PostgreSQLSampleTool Class

1. **__init__(self, connector: Optional[PostgreSQLConnector] = None)**
   - `connector`: Optional PostgreSQLConnector instance
   - Initializes the tool with a connector

2. **_run(self, table_name: str) -> str**
   - `table_name`: Table name to sample
   - Returns: JSON-formatted sample data or error message
   - Gets sample data from specified table

## LangChain Agent Factory (langchain_agent_factory.py)

### ChainOfThoughtCallbackHandler Class

1. **__init__(self, streaming_callback: Callable[[str, bool], None])**
   - `streaming_callback`: Callback function for streaming output
   - Initializes handler for Chain-of-Thought reasoning

2. **on_llm_start(self, serialized, prompts, **kwargs)**
   - Called when LLM starts generating
   - Prepares for token streaming

3. **on_llm_new_token(self, token: str, **kwargs)**
   - `token`: New token from LLM
   - Processes tokens, handling thinking mode and regular text

4. **on_llm_end(self, response, **kwargs)**
   - Called when LLM generation ends
   - Completes streaming and signals completion

5. **on_llm_error(self, error, **kwargs)**
   - `error`: Error from LLM
   - Handles LLM generation errors

6. **on_tool_start(self, serialized, input_str, **kwargs)**
   - Called when tool execution starts
   - Displays tool usage information

7. **on_tool_end(self, output, **kwargs)**
   - `output`: Tool execution output
   - Formats and displays tool output

8. **on_tool_error(self, error, **kwargs)**
   - `error`: Error from tool execution
   - Handles tool execution errors

9. **on_agent_action(self, action, **kwargs)**
   - `action`: Agent action information
   - Shows agent's decision-making process

10. **on_agent_finish(self, finish, **kwargs)**
    - `finish`: Agent completion information
    - Displays agent's final output

### LangChainAgentFactory Class

1. **__init__(self, llm: Optional[Union[BaseChatModel, Any]] = None, db_connection_string: Optional[str] = None, agent_type: str = "chat-conversational-react-description")**
   - `llm`: LangChain compatible LLM
   - `db_connection_string`: PostgreSQL connection string
   - `agent_type`: Type of agent to create
   - Initializes agent factory with components and tools

2. **_parse_agent_type(self, agent_type: str) -> AgentType**
   - `agent_type`: Agent type string
   - Returns: LangChain AgentType
   - Converts string to LangChain AgentType

3. **_register_default_tools(self)**
   - Registers default tools for data analysis
   - Adds PostgreSQL and data analysis tools

4. **register_tool(self, tool: BaseTool)**
   - `tool`: LangChain BaseTool
   - Registers a custom tool

5. **create_agent(self, memory: Optional[ConversationBufferMemory] = None, system_message: Optional[str] = None, streaming_callback: Optional[Callable[[str, bool], None]] = None, verbose: bool = True) -> AgentExecutor**
   - `memory`: ConversationBufferMemory
   - `system_message`: System message for the agent
   - `streaming_callback`: Callback for streaming output
   - `verbose`: Whether to enable verbose output
   - Returns: LangChain agent executor
   - Creates a LangChain agent with tools and configuration

6. **get_tools(self) -> List[BaseTool]**
   - Returns: List of registered tools
   - Gets all registered tools

7. **create_chain_of_thought_prompt(self) -> PromptTemplate**
   - Returns: Prompt template for Chain-of-Thought reasoning
   - Creates a prompt template with thinking steps

8. **create_analysis_chain(self, prompt_template: Optional[PromptTemplate] = None, streaming_callback: Optional[Callable[[str, bool], None]] = None) -> LLMChain**
   - `prompt_template`: Custom prompt template
   - `streaming_callback`: Callback for streaming output
   - Returns: LLMChain for analysis
   - Creates a Chain-of-Thought analysis chain

## Data Analysis Tools (data_analysis_tools.py)

### DataAnalysisTools Class

1. **__init__(self, db_connection_string: Optional[str] = None)**
   - `db_connection_string`: PostgreSQL connection string
   - Initializes data analysis tools and components

2. **process_data(self, data: Union[str, pd.DataFrame]) -> pd.DataFrame**
   - `data`: Data to process (DataFrame or path to file)
   - Returns: Processed DataFrame
   - Processes data using DataProcessor

3. **validate_data(self, data: Union[str, pd.DataFrame]) -> Dict[str, Any]**
   - `data`: Data to validate (DataFrame or path to file)
   - Returns: Dictionary with validation results
   - Validates data using DataValidator

4. **analyze_data(self, data: Union[str, pd.DataFrame], analysis_type: str = "full") -> Dict[str, Any]**
   - `data`: Data to analyze (DataFrame or path to file)
   - `analysis_type`: Type of analysis to perform
   - Returns: Dictionary with analysis results
   - Analyzes data using DataAnalyzer

5. **generate_visualizations(self, data: Union[str, pd.DataFrame], columns: Optional[List[str]] = None, chart_type: Optional[str] = None) -> List[Dict[str, Any]]**
   - `data`: Data to visualize (DataFrame or path to file)
   - `columns`: Columns to visualize
   - `chart_type`: Type of chart to generate
   - Returns: List of visualization specifications
   - Generates visualizations using ChartGenerator

6. **generate_insights(self, data: Union[str, pd.DataFrame], insight_types: Optional[List[str]] = None) -> List[Dict[str, Any]]**
   - `data`: Data to analyze (DataFrame or path to file)
   - `insight_types`: Types of insights to generate
   - Returns: List of generated insights
   - Generates insights using InsightGenerator

7. **recommend_charts(self, data: Union[str, pd.DataFrame], columns: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]**
   - `data`: Data to analyze (DataFrame or path to file)
   - `columns`: Columns to consider
   - Returns: Dictionary with chart recommendations
   - Recommends charts based on data

8. **get_best_charts(self, data: Union[str, pd.DataFrame], columns: Optional[List[str]] = None, top_k: int = 5) -> List[Dict[str, Any]]**
   - `data`: Data to analyze (DataFrame or path to file)
   - `columns`: Columns to consider
   - `top_k`: Number of top charts to return
   - Returns: List of best chart recommendations
   - Gets top chart recommendations

9. **execute_sql(self, query: str) -> Union[List[Dict[str, Any]], str]**
   - `query`: SQL query to execute
   - Returns: Query results or error message
   - Executes SQL query on PostgreSQL database

10. **describe_tables(self) -> Dict[str, Dict[str, Any]]**
    - Returns: Dictionary with table descriptions
    - Gets description of tables in PostgreSQL database

11. **get_table_sample(self, table_name: str, limit: int = 10) -> Union[List[Dict[str, Any]], str]**
    - `table_name`: Table name to sample
    - `limit`: Maximum number of rows to return
    - Returns: Sample data or error message
    - Gets sample data from table

12. **_load_data(self, data: Union[str, pd.DataFrame]) -> pd.DataFrame**
    - `data`: Data source (DataFrame, path, or JSON string)
    - Returns: Loaded DataFrame
    - Loads data from various sources

## LangChain Integration (langchain_integration.py)

### MistralLLM Class

1. **__init__(self, mistral_inference, **kwargs)**
   - `mistral_inference`: MistralInference instance
   - `**kwargs`: Additional parameters like temperature, max_tokens
   - Initializes LangChain compatible LLM using MistralInference

2. **_llm_type(self) -> str**
   - Returns: Type of LLM ("mistral")
   - Property that returns the LLM type

3. **_call(self, prompt: str, stop: Optional[List[str]] = None, run_manager=None, **kwargs) -> str**
   - `prompt`: Text prompt for the model
   - `stop`: Optional stop sequences
   - `run_manager`: Optional callback manager
   - `**kwargs`: Additional parameters
   - Returns: Generated text
   - Calls the Mistral model to generate text

4. **_identifying_params(self) -> Dict[str, Any]**
   - Returns: Dictionary with model parameters
   - Property that returns identifying parameters

### ChainOfThoughtCallbackHandler Class

1. **__init__(self, streaming_callback: Callable[[str, bool], None])**
   - `streaming_callback`: Function to call with streaming output
   - Initializes callback handler for streaming Chain of Thought reasoning

2. **on_llm_start(self, serialized, prompts, **kwargs)**
   - Called when LLM starts generating
   - Prepares for streaming

3. **on_llm_new_token(self, token: str, **kwargs)**
   - `token`: New token from LLM
   - Processes token, handling thinking mode
   - Accumulates tokens in thinking buffer or streams directly

4. **on_llm_end(self, response, **kwargs)**
   - Called when LLM ends generating
   - Sends any remaining buffer and signals completion

5. **on_llm_error(self, error, **kwargs)**
   - `error`: Error from LLM
   - Handles LLM errors

6. **on_chain_start(self, serialized, inputs, **kwargs)**
   - Called when chain starts running
   - Prepares for chain execution

7. **on_chain_end(self, outputs, **kwargs)**
   - Called when chain ends running
   - Handles chain completion

8. **on_chain_error(self, error, **kwargs)**
   - `error`: Error from chain
   - Handles chain errors

9. **on_tool_start(self, serialized, input_str, **kwargs)**
   - Called when tool starts running
   - Displays tool usage information

10. **on_tool_end(self, output, **kwargs)**
    - `output`: Tool execution output
    - Formats and displays tool output

11. **on_tool_error(self, error, **kwargs)**
    - `error`: Error from tool
    - Handles tool errors

12. **on_text(self, text, **kwargs)**
    - `text`: Text to display
    - Handles text display while not in thinking mode

13. **on_agent_action(self, action, **kwargs)**
    - `action`: Agent action
    - Displays agent's decision process

14. **on_agent_finish(self, finish, **kwargs)**
    - `finish`: Agent completion
    - Handles agent completion

### PostgreSQLTool Class

1. **__init__(self, dsn=None)**
   - `dsn`: Database connection string
   - Initializes PostgreSQL tool with connection string

2. **execute_query(self, query: str) -> str**
   - `query`: SQL query to execute
   - Returns: String representation of query results
   - Executes SQL query and returns formatted results

3. **describe_tables(self) -> str**
   - Returns: String with table descriptions
   - Gets information about available tables

### Utility Functions

1. **create_cot_prompt_template() -> PromptTemplate**
   - Returns: PromptTemplate for Chain of Thought
   - Creates a prompt template with thinking steps

2. **create_analysis_tools(analyzer: DataAnalyzer = None, data_processor: DataProcessor = None) -> List[Tool]**
   - `analyzer`: Optional DataAnalyzer instance
   - `data_processor`: Optional DataProcessor instance
   - Returns: List of LangChain tools for data analysis
   - Creates tools for data analysis, including PostgreSQL and Python code execution

3. **create_mistral_agent(mistral_llm, tools: List[Tool], memory: Optional[ConversationBufferMemory] = None, streaming_callback: Optional[Callable] = None) -> Any**
   - `mistral_llm`: MistralLLM instance
   - `tools`: List of LangChain tools
   - `memory`: Optional conversation memory
   - `streaming_callback`: Optional callback for streaming
   - Returns: LangChain agent
   - Creates a LangChain agent using Mistral LLM

4. **format_sql_query(query: str) -> str**
   - `query`: SQL query to format
   - Returns: Formatted SQL query
   - Formats SQL query for better readability

## MistralInference (mistral_inference.py)

### MistralInference Class

1. **__init__(self, config_path: Optional[Union[str, Dict]] = None)**
   - `config_path`: Path to configuration file or dictionary
   - Initializes inference engine with config, model manager, cache, and function registry
   - Loads the config from file if provided as a path, or uses the dictionary directly

2. **load_model(self, force_reload: bool = False) -> Dict[str, Any]**
   - `force_reload`: Whether to force model reload
   - Returns: Dictionary with model container
   - Loads model if not already loaded using ModelManager

3. **count_tokens(self, text: str) -> int**
   - `text`: Text to count tokens for
   - Returns: Number of tokens in text
   - Counts number of tokens in text using the model tokenizer (useful for LangChain integration)

4. **format_prompt(self, messages: List[Dict[str, str]]) -> str**
   - `messages`: List of messages with 'role' and 'content'
   - Returns: Formatted prompt string
   - Formats LangChain messages into Mistral prompt format with system, user, and assistant tags
   - Handles conversion between LangChain message formats and Mistral-specific formatting

5. **generate(self, prompt: str, conversation_id: Optional[str] = None, use_history: bool = False, temperature: Optional[float] = None, top_p: Optional[float] = None, top_k: Optional[int] = None, max_tokens: Optional[int] = None, repetition_penalty: Optional[float] = None, do_sample: bool = True, stop_sequences: Optional[List[str]] = None, **kwargs) -> str**
   - `prompt`: Text prompt for generation
   - `conversation_id`: Optional conversation identifier (not used with LangChain)
   - `use_history`: Whether to use internal history (defaults to False for LangChain)
   - `temperature`: Controls randomness (higher = more random)
   - `top_p`: Nucleus sampling parameter
   - `top_k`: Top-k sampling parameter
   - `max_tokens`: Maximum number of tokens to generate
   - `repetition_penalty`: Penalty for token repetition
   - `do_sample`: Whether to use sampling vs greedy decoding
   - `stop_sequences`: List of strings that stop generation
   - Returns: Generated text
   - Generates text with proper error handling and fallback strategies

6. **generate_with_langchain_messages(self, messages: List[Dict[str, str]], **kwargs) -> str**
   - `messages`: List of messages in LangChain format
   - `**kwargs`: Additional generation parameters
   - Returns: Generated response
   - Converts LangChain messages to Mistral format and generates text

7. **async stream(self, prompt: str, conversation_id: Optional[str] = None, use_history: bool = False, temperature: Optional[float] = None, top_p: Optional[float] = None, top_k: Optional[int] = None, max_tokens: Optional[int] = None, repetition_penalty: Optional[float] = None, do_sample: bool = True, stop_sequences: Optional[List[str]] = None, **kwargs) -> AsyncGenerator[str, None]**
   - Parameters similar to generate method
   - Returns: AsyncGenerator yielding tokens as they're generated
   - Implements asynchronous token streaming with proper stop sequence handling

8. **async stream_with_langchain_messages(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]**
   - `messages`: List of messages in LangChain format
   - `**kwargs`: Additional streaming parameters
   - Returns: AsyncGenerator yielding tokens
   - Converts LangChain messages and streams text token by token

9. **_generate_with_streamer(self, **kwargs)**
   - Internal helper method for streaming generation
   - Runs model generation in a separate thread with streamer
   - Includes error handling for generation failures

10. **register_function(self, name: str, func: Callable, description: str, parameters: Dict = None) -> None**
    - `name`: Function name
    - `func`: Function to call
    - `description`: Function description
    - `parameters`: Function parameters schema
    - Registers a function that can be called by the model for function calling capabilities

11. **call_function(self, name: str, **kwargs) -> Any**
    - `name`: Function name
    - `**kwargs`: Function arguments
    - Returns: Function result
    - Calls a registered function with provided arguments

12. **parse_function_calls(self, text: str) -> List[Dict[str, Any]]**
    - `text`: Generated text
    - Returns: List of function calls with name and arguments
    - Parses function calls from generated text using regex patterns

13. **create_langchain_tools(self) -> List[Tool]**
    - Returns: List of LangChain tools
    - Creates LangChain tools from registered functions for agent integration

14. **get_token_estimator(self) -> Callable[[str], int]**
    - Returns: Token estimation function
    - Returns function to estimate tokens for LangChain's token trackers