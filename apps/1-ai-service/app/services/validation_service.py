import asyncio
import concurrent.futures
import logging
import os
import pandas as pd
from typing import Dict, List, Optional, Union, Any, BinaryIO, Tuple
import uuid
import aiofiles

from ml.utils.memory_utils import estimate_dataframe_size, optimize_dataframe_memory
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

class ValidationService(BaseService):
    """
    Service xác thực và đọc dữ liệu
    Tận dụng ml/data/data_validator.py và ml/data/data_processor.py
    """
    
    _instance = None

    @classmethod
    def get_instance(cls, config: Optional[Dict] = None):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = ValidationService(config=config)
        return cls._instance

    def __init__(self, config: Optional[Dict] = None):
        """Khởi tạo service với data validator và processor từ ml module"""
        super().__init__(config=config)
        # Cấu hình
        self.data_config = self.config.get("data_processing", {})
        self.max_file_size_mb = self.data_config.get("max_file_size_mb", 100)
        self.max_rows_preview = self.data_config.get("max_rows_preview", 100)
        self.max_rows_analysis = self.data_config.get("max_rows_analysis", 100000)
        
        logger.info("ValidationService initialized")
    
    async def validate_and_load_file(
        self, 
        file_path: str,
        chunk_size: Optional[int] = None,
        sample_rows: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Xác thực và tải tệp dữ liệu, hỗ trợ nhiều định dạng
        
        Args:
            file_path: Đường dẫn đến file
            chunk_size: Kích thước chunk nếu cần chunking
            sample_rows: Số lượng rows lấy mẫu
            
        Returns:
            pd.DataFrame: DataFrame đã tải
        """
        result = await self.load_and_validate_data(file_path, chunk_size, sample_rows)
        return result[0]
    
    async def load_and_validate_data(
        self, 
        file_path: str,
        chunk_size: Optional[int] = None,
        sample_rows: Optional[int] = None,
        sample: bool = False,
        max_rows: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Xác thực và tải tệp dữ liệu, trả về cả DataFrame và quality report
        
        Args:
            file_path: Đường dẫn đến file
            chunk_size: Kích thước chunk nếu cần chunking
            sample_rows: Số lượng rows lấy mẫu
            sample: Flag chỉ lấy mẫu nếu True
            max_rows: Số lượng dòng tối đa để đọc
            
        Returns:
            Tuple[pd.DataFrame, Dict[str, Any]]: DataFrame đã tải và quality report
        """
        try:
            # Kiểm tra xem file có tồn tại không
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Xác định sample_rows từ các tham số
            actual_sample_rows = None
            if sample and max_rows:
                actual_sample_rows = max_rows
            elif sample_rows:
                actual_sample_rows = sample_rows
            
            # Kiểm tra kích thước file
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb and not chunk_size:
                logger.warning(f"File size ({file_size_mb:.2f} MB) exceeds threshold. Using chunking.")
                chunk_size = chunk_size or 10000  # Default chunk size
            
            # Xác định định dạng file
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Đọc file dựa vào định dạng - chuyển sang executor để không block
            with concurrent.futures.ThreadPoolExecutor() as executor:
                if file_ext in ['.csv', '.txt']:
                    df = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        self._read_csv_file,
                        file_path,
                        chunk_size,
                        actual_sample_rows
                    )
                elif file_ext in ['.xlsx', '.xls']:
                    df = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        self._read_excel_file,
                        file_path,
                        actual_sample_rows
                    )
                elif file_ext == '.json':
                    df = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        self._read_json_file,
                        file_path,
                        actual_sample_rows
                    )
                elif file_ext == '.parquet':
                    df = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        self._read_parquet_file,
                        file_path,
                        actual_sample_rows
                    )
                else:
                    raise ValueError(f"Unsupported file format: {file_ext}")
            
            # Tối ưu memory sử dụng từ ml/utils/memory_utils.py
            if not isinstance(df, pd.io.parsers.TextFileReader):  # Nếu không phải chunked iterator
                df_size = estimate_dataframe_size(df)
                logger.info(f"Loaded DataFrame size: {df_size:.2f} MB")
                
                if df_size > 200:  # Optimize nếu >200MB
                    logger.info("Optimizing DataFrame memory usage")
                    df = optimize_dataframe_memory(df)
            
            # Tạo quality report
            quality_report = await self.validate_data_quality(df)
            
            return df, quality_report
        except Exception as e:
            logger.error(f"Error validating and loading file: {str(e)}", exc_info=True)
            raise
    
    def _read_csv_file(
        self, 
        file_path: str, 
        chunk_size: Optional[int] = None,
        sample_rows: Optional[int] = None
    ) -> Union[pd.DataFrame, pd.io.parsers.TextFileReader]:
        """Đọc file CSV với xử lý thông minh cho encoding và delimiter"""
        try:
            # Thử đọc với các encoding và delimiter khác nhau
            encodings = ['utf-8', 'latin-1', 'ISO-8859-1', 'cp1252']
            delimiters = [',', ';', '\t', '|']
            
            df = None
            error = None
            
            for encoding in encodings:
                if df is not None:
                    break
                    
                for delimiter in delimiters:
                    try:
                        # Nếu yêu cầu chunking
                        if chunk_size:
                            return pd.read_csv(
                                file_path,
                                delimiter=delimiter,
                                encoding=encoding,
                                chunksize=chunk_size,
                                low_memory=True,
                                on_bad_lines='skip'
                            )
                        
                        # Nếu chỉ lấy mẫu
                        if sample_rows:
                            df = pd.read_csv(
                                file_path,
                                delimiter=delimiter,
                                encoding=encoding,
                                nrows=sample_rows,
                                low_memory=True,
                                on_bad_lines='skip'
                            )
                        else:
                            df = pd.read_csv(
                                file_path,
                                delimiter=delimiter,
                                encoding=encoding,
                                low_memory=True,
                                on_bad_lines='skip'
                            )
                        break
                    except Exception as e:
                        error = e
                        continue
            
            if df is None:
                raise error or ValueError("Failed to read CSV file with all attempted encodings and delimiters")
                
            return df
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            raise
    
    def _read_excel_file(self, file_path: str, sample_rows: Optional[int] = None) -> pd.DataFrame:
        """Đọc file Excel với xử lý thông minh cho sheet"""
        try:
            # Đọc thông tin về worksheet trước
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            
            if not sheet_names:
                raise ValueError("No sheets found in Excel file")
            
            # Nếu có nhiều sheet, ưu tiên sheet đầu tiên
            sheet_name = sheet_names[0]
            
            # Nếu chỉ lấy mẫu
            if sample_rows:
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    nrows=sample_rows
                )
            else:
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name
                )
                
            return df
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            raise
    
    def _read_json_file(self, file_path: str, sample_rows: Optional[int] = None) -> pd.DataFrame:
        """Đọc file JSON với xử lý thông minh cho nhiều định dạng JSON"""
        try:
            # Đọc file trước để kiểm tra định dạng
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
            
            if first_line.startswith('['):
                # JSON array - mỗi phần tử là một row
                df = pd.read_json(file_path)
            else:
                # Nếu là JSON Lines (NDJSON) - mỗi dòng là một JSON object
                df = pd.read_json(file_path, lines=True)
            
            # Nếu chỉ lấy mẫu
            if sample_rows and len(df) > sample_rows:
                df = df.head(sample_rows)
                
            return df
        except Exception as e:
            logger.error(f"Error reading JSON file: {str(e)}")
            raise
    
    def _read_parquet_file(self, file_path: str, sample_rows: Optional[int] = None) -> pd.DataFrame:
        """Đọc file Parquet"""
        try:
            df = pd.read_parquet(file_path)
            
            # Nếu chỉ lấy mẫu
            if sample_rows and len(df) > sample_rows:
                df = df.head(sample_rows)
                
            return df
        except Exception as e:
            logger.error(f"Error reading Parquet file: {str(e)}")
            raise
    
    async def detect_column_types(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Phát hiện kiểu dữ liệu cho mỗi cột - sử dụng data_processor từ ml/
        
        Returns:
            Dict[str, List[str]]: Dictionary kiểu {kiểu_dữ_liệu: [tên_cột]}
        """
        try:
            # Sử dụng data_processor từ ml/ để phát hiện kiểu cột
            column_types = self.data_processor.get_column_types(df)
            return column_types
        except Exception as e:
            logger.error(f"Error detecting column types: {str(e)}", exc_info=True)
            # Fallback basic detection
            return self._basic_column_detection(df)
    
    async def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Xác thực chất lượng dữ liệu sử dụng DataValidator từ ml/
        
        Returns:
            Dict: Báo cáo chất lượng dữ liệu
        """
        try:
            # Sử dụng DataValidator từ ml/ để kiểm tra chất lượng
            with concurrent.futures.ThreadPoolExecutor() as executor:
                quality_report = await asyncio.get_event_loop().run_in_executor(
                    executor,
                    self.data_validator.validate_dataset,
                    df
                )
            
            return quality_report
        except Exception as e:
            logger.error(f"Error validating data quality: {str(e)}", exc_info=True)
            # Fallback basic validation
            return {
                "error": str(e),
                "basic_stats": self._get_basic_data_stats(df)
            }
    
    def _get_basic_data_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Tính toán thống kê cơ bản về DataFrame"""
        try:
            stats = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "missing_values": df.isna().sum().sum(),
                "missing_percent": df.isna().sum().sum() / (len(df) * len(df.columns)) * 100 if len(df) > 0 else 0,
                "column_types": {},
                "memory_usage_mb": estimate_dataframe_size(df)
            }
            
            # Thống kê cho mỗi cột
            for col in df.columns:
                col_stats = {
                    "type": str(df[col].dtype),
                    "missing": df[col].isna().sum(),
                    "unique_values": df[col].nunique()
                }
                
                # Thêm thống kê cho kiểu numeric
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_stats.update({
                        "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                        "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                        "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                        "median": float(df[col].median()) if not pd.isna(df[col].median()) else None
                    })
                
                stats["column_types"][col] = col_stats
            
            return stats
        except Exception as e:
            logger.error(f"Error calculating basic stats: {str(e)}")
            return {"error": str(e)}
        
    async def save_upload_file(
        self,
        file: BinaryIO,
        filename: str,
        upload_dir: Optional[str] = None
    ) -> str:
        """
        Lưu file được upload một cách an toàn
        
        Args:
            file: File object được upload
            filename: Tên gốc của file
            upload_dir: Thư mục lưu file (nếu không chỉ định sẽ dùng mặc định)
        
        Returns:
            str: Đường dẫn đầy đủ của file đã lưu
        """
        try:
            if not upload_dir:
                upload_dir = os.environ.get("UPLOAD_DIR", self.config.get("upload_dir", os.path.join(os.getcwd(), "uploads")))
            os.makedirs(upload_dir, exist_ok=True)

            file_ext = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)

            max_file_size_mb = self.max_file_size_mb or 100
        
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > max_file_size_mb * 1024 * 1024:
                raise ValueError(f"File size exceeds maximum limit of {max_file_size_mb} MB")
            
            async with aiofiles.open(file_path, 'wb') as out_file:
                while True:
                    chunk = await file.read(8192)
                    if not chunk:
                        break
                    await out_file.write(chunk)
            
            logger.info(f"Uploaded file saved: {file_path}")
            
            return file_path
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            raise