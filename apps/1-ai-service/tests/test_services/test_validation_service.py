import pytest
import pandas as pd
import numpy as np
from app.services.validation_service import ValidationService

class TestValidationService:
    """Test service validation dữ liệu"""
    
    def setup_method(self):
        """Setup trước mỗi test"""
        self.service = ValidationService()
    
    def test_validate_and_load_file_csv(self, sample_csv_path):
        """Test tải và validate file CSV"""
        df = self.service.validate_and_load_file(sample_csv_path)
        
        # Kiểm tra kết quả
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert 'date' in df.columns
        assert 'value' in df.columns
    
    def test_validate_and_load_file_nonexistent(self):
        """Test tải file không tồn tại"""
        non_existent_path = "non_existent_file.csv"
        
        with pytest.raises(FileNotFoundError):
            self.service.validate_and_load_file(non_existent_path)
    
    def test_validate_and_load_file_unsupported(self, tmp_path):
        """Test tải file không được hỗ trợ"""
        # Tạo file với định dạng không được hỗ trợ
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.write_text("This is a test file")
        
        with pytest.raises(ValueError):
            self.service.validate_and_load_file(str(unsupported_file))
    
    def test_validate_columns(self):
        """Test validate các cột"""
        # Tạo DataFrame test
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        
        # Test với tất cả cột tồn tại
        valid, message = self.service.validate_columns(df, ['col1', 'col2'])
        assert valid is True
        assert "All required columns exist" in message
        
        # Test với cột không tồn tại
        valid, message = self.service.validate_columns(df, ['col1', 'col3'])
        assert valid is False
        assert "Missing required columns" in message
    
    def test_validate_data_types(self):
        """Test validate kiểu dữ liệu"""
        # Tạo DataFrame test
        df = pd.DataFrame({
            'numeric_col': [1, 2, 3],
            'categoric_col': ['a', 'b', 'c'],
            'date_col': pd.date_range(start='2023-01-01', periods=3),
            'bool_col': [True, False, True]
        })
        
        # Test với các kiểu dữ liệu đúng
        valid, message = self.service.validate_data_types(df, {
            'numeric_col': 'numeric',
            'categoric_col': 'categorical',
            'date_col': 'datetime',
            'bool_col': 'boolean'
        })
        assert valid is True
        assert "All data types are valid" in message
        
        # Test với kiểu dữ liệu không đúng
        valid, message = self.service.validate_data_types(df, {
            'numeric_col': 'datetime',  # Sai kiểu
            'categoric_col': 'categorical'
        })
        assert valid is False
        assert "Invalid data types for columns" in message
    
    def test_check_missing_values(self):
        """Test kiểm tra các giá trị thiếu"""
        # Tạo DataFrame test với missing values
        df = pd.DataFrame({
            'col1': [1, 2, np.nan],
            'col2': ['a', np.nan, 'c']
        })
        
        missing_info = self.service.check_missing_values(df)
        
        # Kiểm tra kết quả
        assert 'col1' in missing_info
        assert 'col2' in missing_info
        assert missing_info['col1']['count'] == 1
        assert missing_info['col2']['count'] == 1
    
    def test_check_duplicates(self):
        """Test kiểm tra các dòng trùng lặp"""
        # Tạo DataFrame test với các dòng trùng lặp
        df = pd.DataFrame({
            'col1': [1, 2, 1],
            'col2': ['a', 'b', 'a']
        })
        
        duplicate_info = self.service.check_duplicates(df)
        
        # Kiểm tra kết quả
        assert duplicate_info['count'] == 1  # 1 dòng trùng lặp
        assert duplicate_info['percentage'] == pytest.approx(33.33, 0.01)  # 33.33%