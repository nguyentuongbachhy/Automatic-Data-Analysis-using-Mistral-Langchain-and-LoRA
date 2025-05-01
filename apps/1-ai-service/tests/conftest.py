import sys
import os
import pytest
from pathlib import Path

# Thêm thư mục gốc của project vào PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Fixtures dùng chung cho các tests
@pytest.fixture
def sample_dataframe():
    """Fixture tạo sample DataFrame cho tests"""
    import pandas as pd
    import numpy as np
    
    return pd.DataFrame({
        'numeric_col': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'category_col': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'B'],
        'date_col': pd.date_range(start='2023-01-01', periods=10),
        'value_col': [10, 25, 30, 15, 20, 35, 40, 45, 50, 55]
    })

@pytest.fixture
def sample_csv_path(sample_dataframe, tmp_path):
    """Fixture tạo sample CSV file trong thư mục tạm"""
    csv_path = tmp_path / "test_data.csv"
    sample_dataframe.to_csv(csv_path, index=False)
    return csv_path