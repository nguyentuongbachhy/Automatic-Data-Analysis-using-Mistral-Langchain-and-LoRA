import os
import logging
import concurrent.futures
import asyncio
from typing import List, Optional, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Body

from app.api.dependencies import (
    ValidationServiceDep, ModelServiceDep,
    get_analyze_service, timed_endpoint, get_performance_monitor
)

from app.services.analyze_service import AnalyzeService

from app.core.monitoring import PerformanceMonitor
from app.models.analysis import (
    ChartType, PredictionConfig
    )
from app.models.common import (
    ApiResponse, ResponseStatus, MLServiceRequest
)

logger = logging.getLogger(__name__)

router = APIRouter()

def validate_file_request(request: MLServiceRequest) -> MLServiceRequest:
    """Validate file request với thông báo lỗi chi tiết"""
    logger.info(f"Request: {request}")
    errors = []
    if not request.file_id:
        errors.append("file_id là bắt buộc")
    
    if not request.user_id:
        errors.append("user_id là bắt buộc")

    if errors:
        raise HTTPException(
            status_code=400, detail=", ".join(errors)
        )
    return request


@router.post("/insights", response_model=ApiResponse, 
             summary="Tạo insights từ dữ liệu",
             description="Phân tích dữ liệu và tạo insights sử dụng kỹ thuật ML nâng cao")
@timed_endpoint
async def get_insights(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request),
    insight_types: Optional[List[str]] = Query(None, description="Loại insights cần tạo (VD: DISTRIBUTION, CORRELATION, TREND)"),
    target_columns: Optional[List[str]] = Query(None, description="Cột cụ thể để tập trung phân tích"),
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
    background_tasks: BackgroundTasks = None
) -> ApiResponse:
    """Phân tích file và tạo insights với các tùy chọn chi tiết"""
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)
        insight_types = insight_types or request.data.get("insightTypes") if request.data else None
        target_columns = target_columns or request.data.get("targetColumns") if request.data else None

        # Validate và load dữ liệu
        df = await validation_service.validate_and_load_file(file_path)
        
        # Tạo query hint nếu có target columns
        query_hint = None
        if target_columns:
            query_hint = f"Analyze columns: {', '.join(target_columns)}"
        
        # Tạo insights với bộ lọc loại
        insights = await analyze_service.generate_insights(df, insight_types, query_hint)
        
        # Chuyển đổi NumPy types sang Python native types
        insights_data = analyze_service._convert_numpy_types([
            insight.model_dump(by_alias=True) if hasattr(insight, "model_dump") else insight 
            for insight in insights
        ])
        
        # Ghi nhận hiệu suất
        monitor.record_insight_generation(len(insights_data) if insights_data else 0)

        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "insights": insights_data,
                "insight_types": insight_types,
                "target_columns": target_columns
            },
            meta={
                "insight_count": len(insights_data) if insights_data else 0,
                "analyzed_columns": len(df.columns),
                "analyzed_rows": len(df)
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi tạo insights: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            meta={"error_type": type(e).__name__}
        )
    

@router.post("/generate-insights", response_model=ApiResponse)
@timed_endpoint
async def generate_insights(
    request: MLServiceRequest,
    model_service: ModelServiceDep,
    validation_service: ValidationServiceDep,
    insight_types: Optional[List[str]] = Query(None, description="Types of insights to generate"),
) -> ApiResponse:
    """Generate insights from data using advanced ML"""
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)
        if not file_path:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="file_path is required for insight generation"
            )
        
        # Validate file existence
        if not os.path.exists(file_path):
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"File not found: {file_path}"
            )
        
        df = await validation_service.validate_and_load_file(file_path)

        # Generate insights
        if hasattr(analyze_service, "generate_insights"):
            insights = await analyze_service.generate_insights(
                df=df,
                insight_types=insight_types,
                query=""
            )
        else:
            # Fallback to direct approach
            # Read file
            df = await validation_service.validate_and_load_file(
                file_path, sample_rows=10000  # Limit rows for insights
            )
            
            # Generate insights
            insights = await analyze_service.generate_insights(
                df=df,
                insight_types=insight_types,
                query=""
            )
        
        # Convert insights to dict
        insight_data = []
        for insight in insights:
            if hasattr(insight, "model_dump"):
                insight_data.append(insight.model_dump())
            elif hasattr(insight, "dict"):
                insight_data.append(insight.dict())
            else:
                insight_data.append(insight)
        
        # Convert NumPy types to Python native types
        if hasattr(analyze_service, "_convert_numpy_types"):
            insight_data = analyze_service._convert_numpy_types(insight_data)
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"insights": insight_data}
        )
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e)
        )


@router.post("/visualize", response_model=ApiResponse,
             summary="Tạo biểu đồ từ dữ liệu",
             description="Tạo biểu đồ phù hợp dựa trên thuộc tính dữ liệu")
@timed_endpoint
async def get_visualizations(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request),
    chart_types: Optional[List[str]] = Query(None, description="Loại biểu đồ cần tạo (VD: BAR, LINE, SCATTER)"),
    target_columns: Optional[List[str]] = Query(None, description="Cột cụ thể để tạo biểu đồ"),
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
    query: Optional[str] = Query(None, description="Mô tả ngôn ngữ tự nhiên về biểu đồ cần tạo")
) -> ApiResponse:
    """Tạo các biểu đồ trực quan hóa cho file với các tùy chọn nâng cao"""
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)
        # Validate và load dữ liệu
        df = await validation_service.validate_and_load_file(file_path)
        
        # Lọc DataFrame nếu có target_columns
        if target_columns:
            valid_columns = [col for col in target_columns if col in df.columns]
            if valid_columns:
                df = df[valid_columns]
        
        # Khởi tạo analyze service
        analyze_service = get_analyze_service(request.file_id, file_path)
        
        # Tạo biểu đồ với lọc loại và hướng dẫn từ query
        visualizations = await analyze_service.generate_visualizations(df, chart_types, query)
        
        # Chuyển đổi NumPy types sang Python native types
        viz_data = analyze_service._convert_numpy_types([
            viz.model_dump() if hasattr(viz, "model_dump") else viz 
            for viz in visualizations
        ])

        # Ghi nhận hiệu suất
        monitor.record_visualization_generation(len(viz_data) if viz_data else 0)

        # Trả về kết quả với metadata
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "visualizations": viz_data,
                "chart_types": chart_types,
                "target_columns": target_columns
            },
            meta={
                "visualization_count": len(visualizations) if visualizations else 0,
                "analyzed_columns": len(df.columns),
                "analyzed_rows": len(df)
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            meta={"error_type": type(e).__name__}
        )


@router.post("/predict", response_model=ApiResponse,
             summary="Tạo dự đoán từ mô hình ML",
             description="Tạo dự đoán dựa trên dữ liệu sử dụng các mô hình ML")
@timed_endpoint
async def get_predictions(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request)
) -> ApiResponse:
    """Tạo dự đoán dựa trên dữ liệu với các mô hình ML tiên tiến"""
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)
        if not request.file_id or not file_path or not request.data:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="fileId, file_path và data là bắt buộc"
            )
            
        # Validate và load dữ liệu
        df = await validation_service.validate_and_load_file(file_path)
        
        # Parse prediction config
        prediction_config = PredictionConfig(**request.data)
        
        # Tạo dự đoán với preprocessing tự động
        prediction_result = await analyze_service.make_prediction(
            df, 
            prediction_config,
            preprocess=True  # Kích hoạt tiền xử lý tự động
        )
        
        # Format kết quả
        if hasattr(prediction_result, "model_dump"):
            result_data = prediction_result.model_dump()
        else:
            result_data = prediction_result

        # Chuyển đổi NumPy types sang Python native types
        result_data = analyze_service._convert_numpy_types(result_data)
            
        # Trả về kết quả với metadata
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data=result_data,
            meta={
                "model_type": prediction_config.modelType,
                "target_column": prediction_config.targetColumn,
                "feature_columns": prediction_config.featureColumns,
                "rows_analyzed": len(df)
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi dự đoán: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            meta={"error_type": type(e).__name__}
        )


@router.post("/full", response_model=ApiResponse,
             summary="Phân tích dữ liệu toàn diện",
             description="Thực hiện phân tích toàn diện về dữ liệu bao gồm thống kê, insights và biểu đồ")
@timed_endpoint
async def get_full_analysis(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request),
    analysis_type: Optional[str] = Query("full", description="Loại phân tích (full, quality, statistics, insights, visualizations, advanced)"),
    query: Optional[str] = Query(None, description="Câu hỏi ngôn ngữ tự nhiên để định hướng phân tích"),
    use_ml: bool = Query(False, description="Whether to use ML for insights (slower but more contextual)")
) -> ApiResponse:
    """Phân tích toàn diện file dữ liệu với tùy chọn phân tích theo hướng dẫn"""
    try:
        analyze_service = get_analyze_service(request.file_id,request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)

        # Validate and load data
        df = await validation_service.validate_and_load_file(file_path)

        # Run comprehensive analysis with query guidance and ML option
        analysis_results = await analyze_service.run_analysis(df, analysis_type="full", query=query, use_ml=use_ml)
        
        # Ensure results don't contain NumPy types
        analysis_results = analyze_service._convert_numpy_types(analysis_results)
        
        # Get insight and visualization counts for metadata
        insight_count = len(analysis_results.get("insights", []))
        visualization_count = len(analysis_results.get("visualizations", []))
        
        # Return result with metadata
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data=analysis_results,
            meta={
                "analysis_type": analysis_type,
                "rows_analyzed": len(df),
                "columns_analyzed": len(df.columns),
                "insight_count": insight_count,
                "visualization_count": visualization_count,
                "used_ml": use_ml
            }
        )
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            meta={"error_type": type(e).__name__}
        )

@router.post("/time-series", response_model=ApiResponse,
             summary="Phân tích dữ liệu chuỗi thời gian",
             description="Thực hiện phân tích và dự báo chuỗi thời gian chuyên biệt")
@timed_endpoint
async def analyze_time_series(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request),
) -> ApiResponse:
    """Phân tích và dự báo chuỗi thời gian nâng cao"""
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)

        if not request.file_id or not file_path or not request.data:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="fileId, file_path và data là bắt buộc"
            )
            
        # Validate và load dữ liệu
        df = await validation_service.validate_and_load_file(file_path)
        
        # Lấy thông tin cột thời gian và giá trị
        data = request.data
        date_col = data.get("date_column")
        value_col = data.get("value_column")
        
        if not date_col or not value_col:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="date_column và value_column là bắt buộc"
            )
            
        # Khởi tạo analyze service
        analyze_service = get_analyze_service(request.file_id, file_path)
        
        # Truy cập time_series_analyzer từ BaseService
        time_series_analyzer = analyze_service.time_series_analyzer
        
        # Phân tích time series - chuyển sang execution bất đồng bộ
        with concurrent.futures.ThreadPoolExecutor() as executor:
            analysis_result = await asyncio.get_event_loop().run_in_executor(
                executor,
                time_series_analyzer.analyze_time_series,
                df, date_col, value_col
            )
        
        # Tạo dự báo nếu yêu cầu
        if data.get("forecast", False):
            forecast_periods = data.get("forecast_periods", 10)
            exogenous_vars = data.get("exogenous_variables")
            return_confidence = data.get("return_confidence", True)
            
            # Thực hiện dự báo bất đồng bộ
            with concurrent.futures.ThreadPoolExecutor() as executor:
                forecast_result = await asyncio.get_event_loop().run_in_executor(
                    executor,
                    time_series_analyzer.forecast_time_series,
                    df, date_col, value_col, forecast_periods, return_confidence, exogenous_vars
                )
                
            analysis_result["forecast"] = forecast_result
            
            # Tạo biểu đồ cho dự báo
            if "forecast_data" in forecast_result:
                visualization = await analyze_service._create_time_series_forecast_visualization(
                    forecast_result["forecast_data"], date_col, value_col
                )
                analysis_result["visualization"] = visualization.model_dump() if hasattr(visualization, "model_dump") else visualization
        
        analysis_result = analyze_service._convert_numpy_types(analysis_result)

        # Trả về kết quả với metadata
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data=analysis_result,
            meta={
                "date_column": date_col,
                "value_column": value_col,
                "time_range_days": analysis_result.get("time_series_info", {}).get("date_range_days"),
                "has_forecast": data.get("forecast", False)
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi phân tích chuỗi thời gian: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            meta={"error_type": type(e).__name__}
        )


@router.post("/correlation", response_model=ApiResponse,
             summary="Phân tích tương quan giữa biến",
             description="Phân tích tương quan giữa các cột được chỉ định hoặc tất cả cột số")
@timed_endpoint
async def analyze_correlations(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request),
    columns: Optional[List[str]] = Query(None),
    threshold: float = Query(0.3)
) -> ApiResponse:
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)

        df = await validation_service.validate_and_load_file(file_path)
        
        if columns:
            valid_columns = [col for col in columns if col in df.columns]
            if valid_columns:
                df = df[valid_columns]
                
        analyze_service = get_analyze_service(request.file_id, file_path)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            analysis_result = await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: analyze_service.data_analyzer._run_statistical_analysis(df)
            )
            
        correlation_data = analysis_result.get("correlation_matrix", {})
        
        if correlation_data and isinstance(correlation_data, list):
            correlation_data = [
                corr for corr in correlation_data 
                if abs(corr.get("correlation", 0)) >= threshold
            ]
        
        visualization = None
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(numeric_cols) >= 2:
            visualization = analyze_service.chart_generator._create_correlation_chart(
                df, numeric_cols[:10]
            )
        
        # Chuyển đổi NumPy types sang Python native types
        correlation_data = analyze_service._convert_numpy_types(correlation_data)
        
        if visualization and hasattr(visualization, "model_dump"):
            viz_data = visualization.model_dump()
        else:
            viz_data = visualization
            
        viz_data = analyze_service._convert_numpy_types(viz_data) if viz_data else None
        
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "correlations": correlation_data,
                "visualization": viz_data
            },
            meta={
                "threshold": threshold,
                "numeric_columns_analyzed": len(numeric_cols),
                "total_correlations": len(correlation_data) if correlation_data else 0
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi phân tích tương quan: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            meta={"error_type": type(e).__name__}
        )


@router.post("/recommend-charts", response_model=ApiResponse,
             summary="Gợi ý loại biểu đồ",
             description="Đề xuất loại biểu đồ phù hợp nhất cho dữ liệu")
@timed_endpoint
async def recommend_charts(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request),
    columns: Optional[List[str]] = Query(None, description="Cột cụ thể để xem xét"),
    top_k: int = Query(5, description="Số lượng đề xuất hàng đầu để trả về")
) -> ApiResponse:
    """Khuyến nghị các loại biểu đồ phù hợp nhất với dữ liệu"""
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)

        # Validate và load dữ liệu
        df = await validation_service.validate_and_load_file(file_path)
        
        # Khởi tạo analyze service
        analyze_service = get_analyze_service(request.file_id, file_path)
        
        # Sử dụng chart_recommender từ BaseService
        # rec_charts = analyze_service.chart_recommender.recommend_charts(df, columns, file_id=request.file_id)
        best_charts = analyze_service.chart_recommender.get_best_charts(df, columns, top_k, file_id=request.file_id)
        
        # Chuyển đổi NumPy types sang Python native types
        # rec_charts = analyze_service._convert_numpy_types(rec_charts)
        best_charts = analyze_service._convert_numpy_types(best_charts)

        # Trả về kết quả
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                # "recommendation_charts": rec_charts,
                "best_charts": best_charts

            },
            meta={
                "columns_analyzed": len(columns) if columns else len(df.columns),
                "top_k": top_k
            }
        )
    except Exception as e:
        logger.error(f"Lỗi khi đề xuất biểu đồ: {str(e)}", exc_info=e)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=str(e),
            meta={"error_type": type(e).__name__}
        )


@router.post("/create-chart", response_model=ApiResponse,
             summary="Tạo biểu đồ cụ thể",
             description="Tạo biểu đồ cụ thể dựa trên tham số đã cung cấp")
@timed_endpoint
async def create_chart(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: MLServiceRequest = Depends(validate_file_request),
    chart_type: str = Query(..., description="Loại biểu đồ (BAR, LINE, SCATTER, v.v.)"),
    columns: List[str] = Query(..., description="Cột sử dụng trong biểu đồ")
) -> ApiResponse:
    """Tạo biểu đồ cụ thể theo yêu cầu"""
    try:
        analyze_service = get_analyze_service(request.file_id, request.user_id, model_service)

        file_path = analyze_service.get_file_path(request.file_id, request.user_id)

        if not request.data:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Thiếu thông tin cấu hình biểu đồ"
            )

        chart_type = request.data.get("chartType") or request.data.get("chart_type")
        columns = request.data.get("columns", [])
        
        logger.info(f"Creating chart with type: {chart_type}, columns: {columns}")
        
        if not chart_type:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Thiếu loại biểu đồ (chartType/chart_type)"
            )
        
        if not columns:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Thiếu danh sách cột (columns)"
            )
            
        # Validate và load dữ liệu
        df = await validation_service.validate_and_load_file(file_path)
        
        # Validate columns
        valid_columns = [col for col in columns if col in df.columns]
        if not valid_columns:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Không có cột nào trong số các cột được chỉ định tồn tại trong dữ liệu"
            )
        
        # Khởi tạo analyze service
        analyze_service = get_analyze_service(request.file_id, file_path)
        
        # Chuyển đổi chuỗi chart_type thành enum ChartType
        try:
            # Chuyển đổi camelCase thành UPPER_SNAKE_CASE nếu cần
            chart_type_upper = chart_type.upper()
            # Kiểm tra trực tiếp nếu có trong enum
            if hasattr(ChartType, chart_type_upper):
                chart_type_enum = getattr(ChartType, chart_type_upper)
            else:
                # Thử các biến thể khác nếu cần
                possible_values = [t.name for t in ChartType]
                closest_match = next((t for t in possible_values if t.upper() == chart_type_upper), None)
                
                if closest_match:
                    chart_type_enum = getattr(ChartType, closest_match)
                else:
                    # Nếu không tìm thấy, gửi danh sách hợp lệ
                    return ApiResponse(
                        status=ResponseStatus.ERROR,
                        error=f"Loại biểu đồ không được hỗ trợ: {chart_type}. Các loại được hỗ trợ: {', '.join([t.name for t in ChartType])}"
                    )
        except (AttributeError, Exception) as e:
            logger.error(f"Error parsing chart type: {str(e)}")
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"Lỗi khi xử lý loại biểu đồ: {chart_type}. Chi tiết: {str(e)}"
            )
        
        try:
            # Tạo biểu đồ sử dụng chart_recommender
            chart = analyze_service.chart_recommender.create_recommended_chart(
                df[valid_columns], valid_columns, chart_type_enum
            )
            
            if not chart:
                return ApiResponse(
                    status=ResponseStatus.ERROR,
                    error=f"Không thể tạo biểu đồ {chart_type} với các cột đã chỉ định"
                )
                
            # Chuyển đổi dữ liệu sang định dạng JSON
            try:
                if hasattr(chart, "model_dump"):
                    chart_data = chart.model_dump()
                else:
                    chart_data = chart
                    
                chart_data = analyze_service._convert_numpy_types(chart_data)
            except Exception as e:
                logger.error(f"Error converting chart data: {str(e)}")
                return ApiResponse(
                    status=ResponseStatus.ERROR,
                    error=f"Lỗi khi chuyển đổi dữ liệu biểu đồ: {str(e)}"
                )

            # Trả về kết quả
            return ApiResponse(
                status=ResponseStatus.SUCCESS,
                data={
                    "chart": chart_data
                },
                meta={
                    "chart_type": chart_type,
                    "columns_used": valid_columns
                }
            )
        except Exception as e:
            logger.error(f"Error creating chart: {str(e)}", exc_info=True)
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"Lỗi khi tạo biểu đồ: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in create_chart: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=f"Lỗi không mong đợi: {str(e)}",
            meta={"error_type": type(e).__name__}
        )


@router.post("/create-custom-chart", response_model=ApiResponse,
             summary="Tạo biểu đồ tùy chỉnh đầy đủ",
             description="Tạo biểu đồ với đầy đủ dữ liệu để render dựa trên các tham số đã cung cấp")
@timed_endpoint
async def create_custom_chart(
    validation_service: ValidationServiceDep,
    model_service: ModelServiceDep,
    request: Dict = Body(...),
) -> ApiResponse:
    """Tạo biểu đồ tùy chỉnh với đầy đủ dữ liệu để render"""
    try:
        # Lấy các tham số trực tiếp từ request body ở mức cao nhất
        file_id = request.get("file_id")
        user_id = request.get("user_id")
        chart_type = request.get("chart_type")
        columns = request.get("columns", [])
        title = request.get("title")
        description = request.get("description")
        
        logger.info(f"Creating custom chart with type: {chart_type}, columns: {columns}, title: {title}")
        
        # Kiểm tra tham số bắt buộc
        if not file_id:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Thiếu fileId"
            )
            
        
        if not chart_type:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Thiếu loại biểu đồ (chartType)"
            )
        
        if not columns:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Thiếu danh sách cột (columns)"
            )
            

        analyze_service = get_analyze_service(file_id, user_id, model_service)
        file_path = analyze_service.get_file_path(file_id, user_id)
        # Validate và load dữ liệu
        df = await validation_service.validate_and_load_file(file_path)
        
        # Validate columns
        valid_columns = [col for col in columns if col in df.columns]
        if not valid_columns:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error="Không có cột nào trong số các cột được chỉ định tồn tại trong dữ liệu"
            )
        
        # Khởi tạo analyze service
        analyze_service = get_analyze_service(file_id, file_path)
        
        # Sử dụng phương thức create_custom_visualization từ chart_recommender
        chart = analyze_service.chart_recommender.create_custom_visualization(
            df, valid_columns, chart_type, file_id, title, description
        )
        
        if not chart:
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"Không thể tạo biểu đồ {chart_type} với các cột đã chỉ định"
            )
            
        # Chuyển đổi dữ liệu sang định dạng JSON
        try:
            if hasattr(chart, "model_dump"):
                chart_data = chart.model_dump()
            else:
                chart_data = chart
                
            chart_data = analyze_service._convert_numpy_types(chart_data)
            
            # In ra để debug
            logger.debug(f"Chart data structure: {chart_data.keys() if isinstance(chart_data, dict) else 'not a dict'}")
            if isinstance(chart_data, dict) and 'data' in chart_data:
                logger.debug(f"Chart data length: {len(chart_data['data'])}")
        except Exception as e:
            logger.error(f"Error converting chart data: {str(e)}")
            return ApiResponse(
                status=ResponseStatus.ERROR,
                error=f"Lỗi khi chuyển đổi dữ liệu biểu đồ: {str(e)}"
            )

        # Trả về kết quả
        return ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={
                "chart": chart_data
            },
            meta={
                "chart_type": chart_type,
                "columns_used": valid_columns,
                "data_points": len(chart_data['data']) if isinstance(chart_data, dict) and 'data' in chart_data else 0
            }
        )
    except Exception as e:
        logger.error(f"Error creating chart: {str(e)}", exc_info=True)
        return ApiResponse(
            status=ResponseStatus.ERROR,
            error=f"Lỗi khi tạo biểu đồ: {str(e)}"
        )
