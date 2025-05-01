import numba

import re
from datetime import datetime
from typing import List, Optional, Union, Tuple, Dict
import locale
import holidays
from functools import lru_cache

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype
from dateutil import parser

@numba.jit(nopython=True)
def _numba_calculate_time_diff(timestamps_array):
    """
    Tính toán khoảng cách thời gian giữa các timestamp liên tiếp
    
    Args:
        timestamps_array: Mảng numpy các timestamp (nanoseconds)
        
    Returns:
        Mảng numpy các khoảng cách (seconds)
    """
    diffs = np.zeros(len(timestamps_array) - 1)
    for i in range(len(timestamps_array) - 1):
        diffs[i] = (timestamps_array[i+1] - timestamps_array[i]) / 1e9  # Convert to seconds
    return diffs

class DateTimeProcessor:
    """Bộ xử lý thời gian nâng cao với phát hiện format tự động và xử lý nhiều loại định dạng"""

    def __init__(self, country_code: str = 'VN', locale_setting: str = None):
        """
        Khởi tạo processor
        
        Args:
            country_code: Mã quốc gia để nhận dạng ngày lễ (VN, US, etc.)
            locale_setting: Cài đặt locale cho định dạng ngày tháng đặc biệt
        """
        # Các định dạng chuẩn thường gặp - sắp xếp theo thứ tự phổ biến để tối ưu kiểm tra
        self.standard_formats = [
            # Các định dạng phổ biến nhất đặt lên đầu để kiểm tra trước
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
            
            # ISO formats
            '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S',
            
            # Common regional formats
            '%d.%m.%Y', '%m.%d.%Y', '%d %b %Y', '%b %d %Y',
            
            # With time
            '%d-%m-%Y %H:%M:%S', '%m-%d-%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S',
            
            # Year first with abbreviated months
            '%Y-%b-%d', '%Y %b %d',
            
            # Only date parts
            '%Y', '%Y-%m', '%m-%Y',
            
            # Thêm các định dạng 2-digit year
            '%d-%m-%y', '%m-%d-%y', '%d/%m/%y', '%m/%d/%y',
            '%d.%m.%y', '%m.%d.%y', '%d %b %y', '%b %d %y',
            
            # Thêm định dạng tháng viết đầy đủ
            '%d %B %Y', '%B %d %Y', '%Y %B %d',
            
            # Định dạng kiểu dd-mmm-yy
            '%d-%b-%y', '%d-%b-%Y'
        ]
        
        # Map định dạng ngày theo nhóm để duyệt hiệu quả hơn
        self.format_groups = {
            'iso': ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'],
            'dmy': ['%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', '%d %b %Y', '%d %B %Y'],
            'mdy': ['%m-%d-%Y', '%m/%d/%Y', '%m.%d.%Y', '%b %d %Y', '%B %d %Y'],
            'ymd': ['%Y-%b-%d', '%Y %b %d', '%Y %B %d'],
            'short_year': ['%d-%m-%y', '%m-%d-%y', '%d/%m/%y', '%m/%d/%y', 
                          '%d.%m.%y', '%m.%d.%y', '%d %b %y', '%b %d %y', 
                          '%d-%b-%y', '%d-%b-%Y'],
            'with_time': ['%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%m-%d-%Y %H:%M:%S',
                        '%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S']
        }
        
        # Thêm các định dạng Excel và số serial
        self.excel_origin_date = datetime(1900, 1, 1)
        
        # Thêm các định dạng Unix timestamp
        self.unix_format = 'unix'
        
        # Thêm các địa phương hóa
        self.country_code = country_code
        if locale_setting:
            try:
                locale.setlocale(locale.LC_TIME, locale_setting)
            except:
                print(f"Không thể cài đặt locale: {locale_setting}")
        
        # Cài đặt holidays nếu có country_code
        self.holiday_calendar = None
        if country_code:
            try:
                self.holiday_calendar = getattr(holidays, country_code)(years=range(1900, 2100))
            except:
                print(f"Không thể tải calendar cho mã quốc gia: {country_code}")
        
        # Cache của các formats đã phát hiện
        self.detected_formats_cache = {}
        
        # Danh sách tên tháng theo nhiều ngôn ngữ - chuyển thành dạng set cho tìm kiếm nhanh hơn
        self.month_names = {
            'en': {
                'full': set(["january", "february", "march", "april", "may", "june", "july", 
                        "august", "september", "october", "november", "december"]),
                'abbr': set(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])
            },
            'vi': {
                'full': set(["tháng một", "tháng hai", "tháng ba", "tháng tư", "tháng năm", "tháng sáu", 
                        "tháng bảy", "tháng tám", "tháng chín", "tháng mười", "tháng mười một", "tháng mười hai"]),
                'abbr': set(["th1", "th2", "th3", "th4", "th5", "th6", "th7", "th8", "th9", "th10", "th11", "th12"])
            },
            'fr': {
                'full': set(["janvier", "février", "mars", "avril", "mai", "juin", "juillet", 
                        "août", "septembre", "octobre", "novembre", "décembre"]),
                'abbr': set(["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"])
            }
            # Thêm các ngôn ngữ khác nếu cần
        }
        
        # Các regex pattern để nhận diện - biên dịch trước để tối ưu hiệu suất
        self.date_patterns = {
            'dmy': re.compile(r'(\d{1,2})[\/\s.\-](\d{1,2}|[a-zA-Z]{3,})[\/\s.\-](\d{2,4})'),
            'mdy': re.compile(r'(\d{1,2}|[a-zA-Z]{3,})[\/\s.\-](\d{1,2})[\/\s.\-](\d{2,4})'),
            'ymd': re.compile(r'(\d{4})[\/\s.\-](\d{1,2}|[a-zA-Z]{3,})[\/\s.\-](\d{1,2})'),
            'timestamp': re.compile(r'^\d{9,13}$'),
            'iso8601': re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
            'time_suffix': re.compile(r'(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([AaPp][Mm]))?$')
        }
        
        # Tạo lookup set cho tên tháng - tối ưu tìm kiếm
        self.all_month_names = set()
        for lang_data in self.month_names.values():
            self.all_month_names.update(lang_data['full'])
            self.all_month_names.update(lang_data['abbr'])

    @lru_cache(maxsize=128)
    def _clean_datetime_string(self, value: str) -> str:
        """
        Làm sạch chuỗi datetime, chuẩn hóa định dạng
        
        Args:
            value: Chuỗi cần làm sạch
            
        Returns:
            str: Chuỗi đã làm sạch
        """
        if not isinstance(value, str):
            return str(value)
            
        # Loại bỏ các ký tự đặc biệt không cần thiết
        value = value.strip()
        
        # Thay thế nhiều ký tự trắng thành một
        value = re.sub(r'\s+', ' ', value)
        
        # Xử lý các trường hợp tháng không chuẩn
        value_lower = value.lower()
        
        # Xử lý tên tháng - sử dụng cách tiếp cận hiệu quả hơn
        for month_name in self.all_month_names:
            if month_name in value_lower:
                # Tìm tháng trong các ngôn ngữ 
                for lang, months in self.month_names.items():
                    idx = -1
                    if month_name in months['full']:
                        idx = list(months['full']).index(month_name)
                    elif month_name in months['abbr']:
                        idx = list(months['abbr']).index(month_name)
                    
                    if idx != -1:
                        # +1 vì idx bắt đầu từ 0 nhưng tháng bắt đầu từ 1
                        month_num = idx + 1
                        # Thay thế tên tháng thành số
                        value = re.sub(rf'\b{month_name}\b', f'{month_num}', value, flags=re.IGNORECASE)
                        break
        
        # Xử lý các định dạng đặc biệt của Việt Nam - thực hiện 1 lần thay vì lặp lại
        value = re.sub(r'ngày\s+(\d+)', r'\1', value, flags=re.IGNORECASE)
        value = re.sub(r'tháng\s+(\d+)', r'\1', value, flags=re.IGNORECASE)
        value = re.sub(r'năm\s+(\d+)', r'\1', value, flags=re.IGNORECASE)
        
        # Chuẩn hóa dấu phân cách
        value = re.sub(r'(\d+)[/\.-](\d+)[/\.-](\d+)', r'\1-\2-\3', value)
        
        return value
    
    def _check_if_timestamp(self, samples: List[str]) -> bool:
        """
        Kiểm tra xem mẫu có phải là timestamp Unix không
        
        Args:
            samples: Danh sách các mẫu
            
        Returns:
            bool: True nếu là timestamp Unix
        """
        # Sử dụng vectorized operations thay vì for loop
        pattern = self.date_patterns['timestamp']
        
        # Lọc các mẫu phù hợp pattern timestamp
        valid_samples = [s for s in samples if pattern.match(str(s).strip())]
        if not valid_samples:
            return False
            
        # Chuyển đổi thành số để kiểm tra range
        try:
            ts_values = np.array([int(s) for s in valid_samples])
            valid_range = (0 < ts_values) & (ts_values < 9999999999999)
            timestamp_count = np.sum(valid_range)
            
            # Nếu hầu hết là timestamp
            return timestamp_count > len(samples) * 0.7
        except:
            return False
    
    def detect_datetime_format(self, sample_values: List[str]) -> Optional[str]:
        """
        Phát hiện định dạng datetime phổ biến nhất từ một tập mẫu
        
        Args:
            sample_values: Danh sách các giá trị thời gian dạng chuỗi
            
        Returns:
            Optional[str]: Định dạng phát hiện được hoặc None nếu không thể xác định
        """
        # Nếu không có giá trị, không thể phát hiện
        if not sample_values:
            return None
            
        # Cache key dựa trên mẫu dữ liệu
        cache_key = hash(tuple(str(v) for v in sample_values[:5]))
        if cache_key in self.detected_formats_cache:
            return self.detected_formats_cache[cache_key]
        
        # Tiền xử lý mẫu - sử dụng list comprehension thay vì for loop
        clean_samples = [self._clean_datetime_string(str(v)) for v in sample_values 
                        if v is not None and pd.notna(v)]
        if not clean_samples:
            return None
            
        # Kiểm tra các định dạng đặc biệt trước
        if self._check_if_timestamp(clean_samples):
            self.detected_formats_cache[cache_key] = self.unix_format
            return self.unix_format
        
        # Tối ưu kiểm tra format: Sử dụng chiến lược phân nhóm
        # Lấy 1 mẫu đầu tiên để dự đoán nhóm định dạng
        first_sample = clean_samples[0]
        
        # Tìm nhóm định dạng có khả năng cao nhất dựa trên pattern
        likely_groups = []
        
        # Kiểm tra các pattern cơ bản
        if self.date_patterns['iso8601'].match(first_sample):
            likely_groups.append('iso')
        elif self.date_patterns['dmy'].match(first_sample):
            likely_groups.append('dmy')
        elif self.date_patterns['mdy'].match(first_sample):
            likely_groups.append('mdy')
        elif self.date_patterns['ymd'].match(first_sample):
            likely_groups.append('ymd')
        
        # Kiểm tra nếu có dấu hai chấm - có thể có thời gian
        if ':' in first_sample:
            likely_groups.append('with_time')
        
        # Lựa chọn định dạng từ các nhóm có khả năng cao
        format_matches = {}
        
        # Nếu có nhóm có khả năng cao, chỉ kiểm tra các định dạng trong các nhóm đó
        formats_to_check = []
        if likely_groups:
            for group in likely_groups:
                formats_to_check.extend(self.format_groups.get(group, []))
        
        # Nếu không xác định được nhóm, kiểm tra tất cả định dạng 
        if not formats_to_check:
            formats_to_check = self.standard_formats
        
        # Đếm số lần match cho mỗi format - tối ưu vòng lặp
        for fmt in formats_to_check:
            match_count = 0
            for value in clean_samples:
                try:
                    datetime.strptime(value, fmt)
                    match_count += 1
                except ValueError:
                    continue
            
            if match_count > 0:
                format_matches[fmt] = match_count
        
        # Tìm format có nhiều match nhất
        if format_matches:
            best_format = max(format_matches.items(), key=lambda x: x[1])
            
            # Chỉ trả về nếu có ít nhất 3 match hoặc >50% mẫu match
            if best_format[1] >= 3 or best_format[1] / len(clean_samples) > 0.5:
                # Lưu vào cache
                self.detected_formats_cache[cache_key] = best_format[0]
                return best_format[0]
        
        # Phân tích ngôn ngữ và tìm tên tháng
        language_format = self._analyze_month_names(clean_samples)
        if language_format:
            self.detected_formats_cache[cache_key] = language_format
            return language_format
        
        # Thử phân tích chuỗi để tìm pattern
        pattern = self._analyze_datetime_pattern(clean_samples)
        if pattern:
            self.detected_formats_cache[cache_key] = pattern
            return pattern
            
        # Không tìm được format phù hợp
        self.detected_formats_cache[cache_key] = None
        return None
    
    def _analyze_month_names(self, samples: List[str]) -> Optional[str]:
        """
        Phân tích mẫu để tìm định dạng dựa trên tên tháng
        
        Args:
            samples: Danh sách các mẫu
            
        Returns:
            Optional[str]: Định dạng phát hiện được hoặc None
        """
        # Kiểm tra mẫu đầu tiên
        for sample in samples[:5]:  # Chỉ kiểm tra 5 mẫu đầu tiên
            sample_lower = sample.lower()
            
            # Tìm tên tháng trong mẫu - sử dụng set để tìm kiếm O(1)
            found_month = None
            for month in self.all_month_names:
                if month in sample_lower:
                    found_month = month
                    break
            
            if found_month:
                # Tìm pattern phổ biến với tên tháng - sử dụng biểu thức chính quy đã biên dịch
                if re.search(r'\d{1,2}\s+\w+\s+\d{4}', sample):  # dd mmm yyyy
                    return '%d %b %Y'
                elif re.search(r'\w+\s+\d{1,2}\s*,?\s+\d{4}', sample):  # mmm dd, yyyy
                    return '%b %d %Y'
                elif re.search(r'\d{4}\s+\w+\s+\d{1,2}', sample):  # yyyy mmm dd
                    return '%Y %b %d'
        
        return None
    
    def _analyze_datetime_pattern(self, samples: List[str]) -> Optional[str]:
        """
        Phân tích pattern từ các mẫu để xác định định dạng
        
        Args:
            samples: Danh sách các giá trị mẫu
            
        Returns:
            Optional[str]: Pattern phát hiện được hoặc None
        """
        # Phân tích pattern cho các mẫu có giá trị
        valid_samples = [s for s in samples if isinstance(s, str) and not pd.isna(s)]
        if not valid_samples:
            return None
            
        # Kiểm tra xem các mẫu có chứa ký tự phân cách không - sử dụng Counter để đếm hiệu quả
        from collections import Counter
        
        # Đếm các dấu phân cách trong tất cả mẫu
        delimiter_counts = Counter()
        for s in valid_samples:
            for delimiter in ['-', '/', '.', ' ']:
                delimiter_counts[delimiter] += s.count(delimiter)
        
        # Lấy delimiter phổ biến nhất
        if delimiter_counts:
            main_delimiter, freq = delimiter_counts.most_common(1)[0]
            
            # Nếu chủ yếu mẫu đều chứa delimiter này (trung bình >0.7 delimiter mỗi mẫu)
            if freq >= len(valid_samples) * 0.7:
                # Đếm số lượng mẫu khớp với mỗi pattern một cách hiệu quả
                pattern_matches = {
                    'dmy': sum(1 for s in valid_samples if self.date_patterns['dmy'].search(s)),
                    'mdy': sum(1 for s in valid_samples if self.date_patterns['mdy'].search(s)),
                    'ymd': sum(1 for s in valid_samples if self.date_patterns['ymd'].search(s))
                }
                
                # Xác định pattern phổ biến nhất
                best_pattern = max(pattern_matches.items(), key=lambda x: x[1])
                
                if best_pattern[1] > 0:
                    sample = valid_samples[0]
                    parts = sample.split(main_delimiter)
                    
                    # Kiểm tra phần cuối có phải là năm không - sử dụng any với generator expression
                    has_year = any(len(part) >= 4 and part.isdigit() for part in parts)
                    
                    if best_pattern[0] == 'dmy':
                        return f'%d{main_delimiter}%m{main_delimiter}%Y' if has_year else f'%d{main_delimiter}%m{main_delimiter}%y'
                    elif best_pattern[0] == 'mdy':
                        return f'%m{main_delimiter}%d{main_delimiter}%Y' if has_year else f'%m{main_delimiter}%d{main_delimiter}%y'
                    elif best_pattern[0] == 'ymd':
                        return f'%Y{main_delimiter}%m{main_delimiter}%d'
        
        # Kiểm tra các mẫu có chứa thời gian không - sử dụng any với generator expression
        has_time = any(':' in s for s in valid_samples)
        if has_time:
            time_pattern = self.date_patterns['time_suffix'].search(valid_samples[0])
            if time_pattern:
                # Đã có giờ phút giây
                _, _, _, am_pm = time_pattern.groups()
                if am_pm:
                    return '%d-%m-%Y %I:%M:%S %p'  # 12-hour clock with AM/PM
                else:
                    return '%d-%m-%Y %H:%M:%S'  # 24-hour clock
        
        # Thử phân tích với dateutil.parser cho mẫu đầu tiên
        try:
            # Parse mẫu đầu tiên
            parsed_date = parser.parse(valid_samples[0])
            # Tạo định dạng từ các phần đã phân tích
            fmt = parsed_date.strftime('%Y-%m-%d')
            
            # Kiểm tra xem có giờ phút giây không
            if any(':' in s for s in valid_samples):
                fmt += ' %H:%M:%S'
                
            return fmt
        except:
            pass
            
        return None
    
    def convert_to_datetime(
        self, 
        series: Union[pd.Series, np.ndarray, List], 
        preferred_formats: Optional[List[str]] = None,
        errors: str = 'coerce'
    ) -> pd.Series:
        """
        Chuyển đổi một series thành datetime với xử lý thông minh
        
        Args:
            series: Series cần chuyển đổi
            preferred_formats: Các định dạng ưu tiên
            errors: Cách xử lý lỗi ('raise', 'coerce', 'ignore')
            
        Returns:
            pd.Series: Series đã chuyển đổi sang datetime
        """
        # Đảm bảo input là pandas Series
        if not isinstance(series, pd.Series):
            series = pd.Series(series)
        
        # Nếu Series đã là datetime, trả về nguyên dạng
        if is_datetime64_any_dtype(series):
            return series
        
        # Chuyển đổi tất cả giá trị thành chuỗi để xử lý
        series_str = series.astype(str)
        
        # Làm sạch chuỗi - sử dụng phương thức apply thay vì vòng lặp
        series_clean = series_str.apply(self._clean_datetime_string)
        
        # Tạo một Series mới để chứa kết quả
        result = pd.Series(index=series.index, dtype='datetime64[ns]')
        
        # Lấy mẫu để phát hiện định dạng - sử dụng pandas operations
        sample_size = min(100, len(series_clean.dropna()))
        sample = series_clean.dropna().sample(sample_size).tolist() if sample_size > 0 else []
        
        # Phát hiện định dạng nếu không có định dạng ưu tiên
        detected_format = None
        if not preferred_formats and sample:
            detected_format = self.detect_datetime_format(sample)
        
        # Kiểm tra xem có phải là Unix timestamp không
        is_timestamp = detected_format == self.unix_format
        
        # Kiểm tra xem có phải là Excel date không
        is_excel_date = False
        if not is_timestamp and not detected_format:
            # Excel dates thường là số thập phân từ 0 đến khoảng 60000
            if series.dtype.kind in 'if':  # integer or float
                num_values = series.dropna()
                if len(num_values) > 0:
                    min_val, max_val = num_values.min(), num_values.max()
                    if 0 <= min_val <= max_val <= 60000:
                        # Có khả năng là Excel date
                        is_excel_date = True
        
        # Xử lý các định dạng đặc biệt một cách hiệu quả
        if is_timestamp:
            # Unix timestamp - sử dụng pd.to_datetime một lần duy nhất
            try:
                # Xác định độ chính xác của timestamp (giây, mili, micro, nano)
                precision = 's'  # Default: seconds
                if series.dtype.kind in 'if':  # Numeric
                    sample_value = float(series.dropna().iloc[0])
                    if sample_value > 1e12:  # milliseconds (13 digits)
                        precision = 'ms'
                    elif sample_value > 1e15:  # microseconds (16 digits)
                        precision = 'us'
                    elif sample_value > 1e18:  # nanoseconds (19 digits)
                        precision = 'ns'
                
                # Chuyển đổi timestamp thành datetime
                result = pd.to_datetime(series, unit=precision, errors=errors)
                return result
            except Exception as e:
                if errors == 'raise':
                    raise e
                # Nếu lỗi, thử cách khác
        
        if is_excel_date:
            # Excel date - sử dụng vectorized operations thay vì list comprehension
            try:
                result = pd.Series([
                    self.excel_origin_date + pd.Timedelta(days=float(x)) if pd.notna(x) else pd.NaT
                    for x in series
                ], index=series.index)
                
                return result
            except Exception as e:
                if errors == 'raise':
                    raise e
                # Nếu lỗi, thử cách khác
        
        # Danh sách các định dạng cần thử - tránh nối list không cần thiết
        formats_to_try = preferred_formats or []
        if detected_format:
            formats_to_try = [detected_format] + formats_to_try
        formats_to_try.extend(self.standard_formats)

        # Thêm danh sách định dạng chuẩn vào cuối
        formats_to_try.extend([fmt for fmt in self.standard_formats if fmt not in formats_to_try])
        
        # Cố gắng chuyển đổi với từng định dạng
        for fmt in formats_to_try:
            try:
                result = pd.to_datetime(series_clean, format=fmt, errors='coerce')
                # Kiểm tra xem có bao nhiêu giá trị đã chuyển đổi thành công
                success_rate = result.notna().mean()
                if success_rate > 0.7:  # Nếu >70% chuyển đổi thành công
                    return result
            except:
                continue
        
        # Nếu không tìm được định dạng phù hợp, sử dụng parser tổng quát
        try:
            return pd.to_datetime(series_clean, format="%d-%m-%Y", errors=errors)
        except Exception as e:
            if errors == 'raise':
                raise e
            # Trả về Series với tất cả NaT nếu không thể chuyển đổi
            return pd.Series(np.full(len(series), np.datetime64('NaT')), index=series.index)

    # Các hàm còn lại của DateTimeProcessor giữ nguyên...
    # (không thay đổi các phương thức khác của class)
    
    def extract_datetime_features(
        self, 
        df: pd.DataFrame, 
        datetime_column: str,
        cyclical_encoding: bool = True,
        drop_original: bool = False,
        add_holidays: bool = False,
        include_lags: bool = False,
        lag_periods: List[int] = [1, 7, 30]
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Trích xuất đặc trưng từ cột datetime
        
        Args:
            df: DataFrame đầu vào
            datetime_column: Tên cột datetime
            cyclical_encoding: Có sử dụng encoding cyclical không
            drop_original: Có loại bỏ cột gốc không
            add_holidays: Có thêm đặc trưng ngày lễ không
            include_lags: Có thêm các đặc trưng lag không
            lag_periods: Danh sách các khoảng lag cần tạo
            
        Returns:
            Tuple[pd.DataFrame, List[str]]: DataFrame với đặc trưng mới và danh sách tên đặc trưng
        """
        df_result = df.copy()
        
        # Đảm bảo cột là kiểu datetime
        if not is_datetime64_any_dtype(df_result[datetime_column]):
            df_result[datetime_column] = self.convert_to_datetime(df_result[datetime_column])
        
        # Tạo danh sách đặc trưng mới
        new_features = []
        
        # 1. Trích xuất đặc trưng cơ bản
        # Tạo tất cả đặc trưng datetime cơ bản cùng một lúc - tối ưu hóa bằng cách nhóm các phép tính
        basic_features = {
            f"{datetime_column}_year": df_result[datetime_column].dt.year,
            f"{datetime_column}_month": df_result[datetime_column].dt.month,
            f"{datetime_column}_day": df_result[datetime_column].dt.day,
            f"{datetime_column}_dayofweek": df_result[datetime_column].dt.dayofweek,
            f"{datetime_column}_quarter": df_result[datetime_column].dt.quarter,
            f"{datetime_column}_weekofyear": df_result[datetime_column].dt.isocalendar().week,
            f"{datetime_column}_dayofyear": df_result[datetime_column].dt.dayofyear,
            f"{datetime_column}_is_weekend": (df_result[datetime_column].dt.dayofweek >= 5).astype(int),
            f"{datetime_column}_is_month_end": (df_result[datetime_column].dt.is_month_end).astype(int),
            f"{datetime_column}_is_month_start": (df_result[datetime_column].dt.day <= 7).astype(int)
        }
        
        # Thêm vào DataFrame và cập nhật danh sách đặc trưng mới
        for feature_name, feature_values in basic_features.items():
            df_result[feature_name] = feature_values
            new_features.append(feature_name)
        
        # Thêm cuối quý
        last_month_of_quarter = df_result[datetime_column].dt.month.isin([3, 6, 9, 12])
        last_days_of_month = df_result[datetime_column].dt.is_month_end
        df_result[f"{datetime_column}_is_quarter_end"] = (last_month_of_quarter & last_days_of_month).astype(int)
        new_features.append(f"{datetime_column}_is_quarter_end")
        
        # Kiểm tra có thông tin giờ không
        has_time = (df_result[datetime_column].dt.hour != 0).any()
        
        if has_time:
            # Tạo tất cả đặc trưng giờ cùng một lúc
            time_features = {
                f"{datetime_column}_hour": df_result[datetime_column].dt.hour,
                f"{datetime_column}_minute": df_result[datetime_column].dt.minute,
                f"{datetime_column}_business_hour": ((df_result[datetime_column].dt.hour >= 8) & 
                                                    (df_result[datetime_column].dt.hour < 18)).astype(int)
            }
            
            # Thêm vào DataFrame và cập nhật danh sách đặc trưng mới
            for feature_name, feature_values in time_features.items():
                df_result[feature_name] = feature_values
                new_features.append(feature_name)
                
            # Buổi trong ngày (sáng, chiều, tối, đêm) - sử dụng numpy.select thay vì nhiều điều kiện
            conditions = [
                (df_result[datetime_column].dt.hour >= 5) & (df_result[datetime_column].dt.hour < 12),
                (df_result[datetime_column].dt.hour >= 12) & (df_result[datetime_column].dt.hour < 17),
                (df_result[datetime_column].dt.hour >= 17) & (df_result[datetime_column].dt.hour < 22),
                (df_result[datetime_column].dt.hour >= 22) | (df_result[datetime_column].dt.hour < 5)
            ]
            choices = ['morning', 'afternoon', 'evening', 'night']
            df_result[f"{datetime_column}_time_of_day"] = np.select(conditions, choices, default='unknown')
            new_features.append(f"{datetime_column}_time_of_day")
        
        # Là ngày lễ hay không (cần thư viện holidays)
        if add_holidays and self.holiday_calendar:
            # Sử dụng vectorized operations thay vì map với lambda
            dates = df_result[datetime_column].dt.date
            
            # Tạo set các ngày lễ để tìm kiếm nhanh O(1)
            holiday_dates = set(self.holiday_calendar.keys())
            
            # Tạo đặc trưng ngày lễ với list comprehension nhanh hơn
            df_result[f"{datetime_column}_is_holiday"] = pd.Series(
                [1 if date in holiday_dates else 0 for date in dates],
                index=df_result.index
            )
            new_features.append(f"{datetime_column}_is_holiday")
            
            # Thêm thông tin trước/sau ngày lễ
            plus_one_day = pd.Series(
                [(date + pd.Timedelta(days=1)) in holiday_dates for date in dates],
                index=df_result.index
            ).astype(int)
            
            minus_one_day = pd.Series(
                [(date - pd.Timedelta(days=1)) in holiday_dates for date in dates],
                index=df_result.index
            ).astype(int)
            
            df_result[f"{datetime_column}_is_before_holiday"] = plus_one_day
            df_result[f"{datetime_column}_is_after_holiday"] = minus_one_day
            
            new_features.extend([
                f"{datetime_column}_is_before_holiday",
                f"{datetime_column}_is_after_holiday"
            ])
        
        # 2. Đặc trưng cyclical (sin/cos) cho biến tuần hoàn như giờ, ngày, tháng
        if cyclical_encoding:
            # Tạo tất cả đặc trưng cyclical cùng một lúc
            cyclical_features = {}
            
            # Tháng
            cyclical_features[f"{datetime_column}_month_sin"] = np.sin(2 * np.pi * df_result[datetime_column].dt.month / 12)
            cyclical_features[f"{datetime_column}_month_cos"] = np.cos(2 * np.pi * df_result[datetime_column].dt.month / 12)
            
            # Ngày trong tuần
            cyclical_features[f"{datetime_column}_dow_sin"] = np.sin(2 * np.pi * df_result[datetime_column].dt.dayofweek / 7)
            cyclical_features[f"{datetime_column}_dow_cos"] = np.cos(2 * np.pi * df_result[datetime_column].dt.dayofweek / 7)
            
            # Ngày trong tháng
            days_in_month = df_result[datetime_column].dt.days_in_month
            day_in_month_norm = df_result[datetime_column].dt.day / days_in_month
            cyclical_features[f"{datetime_column}_dom_sin"] = np.sin(2 * np.pi * day_in_month_norm)
            cyclical_features[f"{datetime_column}_dom_cos"] = np.cos(2 * np.pi * day_in_month_norm)
            
            # Ngày trong năm
            cyclical_features[f"{datetime_column}_doy_sin"] = np.sin(2 * np.pi * df_result[datetime_column].dt.dayofyear / 365)
            cyclical_features[f"{datetime_column}_doy_cos"] = np.cos(2 * np.pi * df_result[datetime_column].dt.dayofyear / 365)
            
            if has_time:
                # Giờ
                cyclical_features[f"{datetime_column}_hour_sin"] = np.sin(2 * np.pi * df_result[datetime_column].dt.hour / 24)
                cyclical_features[f"{datetime_column}_hour_cos"] = np.cos(2 * np.pi * df_result[datetime_column].dt.hour / 24)
            
            # Thêm vào DataFrame và cập nhật danh sách đặc trưng mới
            for feature_name, feature_values in cyclical_features.items():
                df_result[feature_name] = feature_values
                new_features.append(feature_name)
        
        # 3. Thêm các đặc trưng lag nếu cần
        if include_lags:
            # Sắp xếp dữ liệu theo thời gian
            df_sorted = df_result.sort_values(by=datetime_column)
            
            # Tạo lag cho các cột số - dùng dict comprehension để tối ưu
            numeric_columns = df.select_dtypes(include=np.number).columns
            for col in numeric_columns:
                for lag in lag_periods:
                    lag_col_name = f"{col}_lag_{lag}"
                    df_sorted[lag_col_name] = df_sorted[col].shift(lag)
                    new_features.append(lag_col_name)
            
            # Cập nhật df_result với các lag features
            df_result = df_sorted.reset_index(drop=True)
        
        # Loại bỏ cột gốc nếu cần
        if drop_original:
            df_result = df_result.drop(columns=[datetime_column])
            
        return df_result, new_features

    def analyze_datetime_distribution(self, series: pd.Series) -> Dict:
        """
        Phân tích phân phối datetime
        
        Args:
            series: Series chứa datetime
            
        Returns:
            Dict: Kết quả phân tích
        """
        if not is_datetime64_any_dtype(series):
            series = convert_to_datetime(series)
        
        non_null = series.dropna()
        if len(non_null) < 2:
            return {"error": "Not enough data points"}
        
        try:
            # Chuẩn bị kết quả
            result = {
                "count": len(non_null),
                "min_date": non_null.min().isoformat(),
                "max_date": non_null.max().isoformat(),
                "range_days": (non_null.max() - non_null.min()).total_seconds() / (24 * 3600),
                "distributions": {},
                "time_gaps": {},
                "seasonality": {}
            }
            
            # Phân tích phân phối theo năm, tháng, ngày trong tuần
            result["distributions"]["year"] = non_null.dt.year.value_counts().sort_index().to_dict()
            result["distributions"]["month"] = non_null.dt.month.value_counts().sort_index().to_dict()
            result["distributions"]["day_of_week"] = non_null.dt.dayofweek.value_counts().sort_index().to_dict()
            result["distributions"]["hour"] = non_null.dt.hour.value_counts().sort_index().to_dict() if (non_null.dt.hour != 0).any() else {}
            
            # Sử dụng numba để tính toán khoảng cách thời gian nhanh hơn
            timestamps = non_null.astype(np.int64).values  # Convert to nanoseconds
            sorted_timestamps = np.sort(timestamps)
            time_diffs_seconds = _numba_calculate_time_diff(sorted_timestamps)
            
            # Phân tích khoảng cách thời gian
            if len(time_diffs_seconds) > 0:
                # Tính thống kê cơ bản
                result["time_gaps"]["min_gap_seconds"] = float(np.min(time_diffs_seconds))
                result["time_gaps"]["max_gap_seconds"] = float(np.max(time_diffs_seconds))
                result["time_gaps"]["mean_gap_seconds"] = float(np.mean(time_diffs_seconds))
                result["time_gaps"]["median_gap_seconds"] = float(np.median(time_diffs_seconds))
                
                # Tính độ lệch chuẩn và biến thiên
                result["time_gaps"]["std_gap_seconds"] = float(np.std(time_diffs_seconds))
                if result["time_gaps"]["mean_gap_seconds"] > 0:
                    result["time_gaps"]["coefficient_of_variation"] = result["time_gaps"]["std_gap_seconds"] / result["time_gaps"]["mean_gap_seconds"]
                    # Độ đều đặn (regularity): 1 = rất đều đặn, 0 = không đều đặn
                    result["time_gaps"]["regularity"] = max(0, min(1, 1 - min(1, result["time_gaps"]["coefficient_of_variation"] / 3)))
                
                # Tìm khoảng thời gian phổ biến nhất
                gap_counts = {}
                rounded_gaps = np.round(time_diffs_seconds)
                for gap in rounded_gaps:
                    if gap not in gap_counts:
                        gap_counts[gap] = 0
                    gap_counts[gap] += 1
                
                # Sắp xếp theo tần suất và lấy top 3
                sorted_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)
                result["time_gaps"]["most_common_gaps"] = {
                    f"{int(gap)}s": count for gap, count in sorted_gaps[:3]
                }
                
                # Dự đoán tần suất dữ liệu
                result["suggested_frequency"] = self._detect_timeseries_frequency(time_diffs_seconds)
            
            # Phát hiện seasonality
            result["seasonality"] = self._detect_seasonality(non_null)
            
            return result
        except Exception as e:
            return {"error": str(e)}

    def _detect_timeseries_frequency(self, time_diffs_seconds: np.ndarray) -> str:
        """
        Phát hiện tần suất dữ liệu chuỗi thời gian
        
        Args:
            time_diffs_seconds: Mảng khoảng cách thời gian (giây)
            
        Returns:
            str: Tần suất phát hiện được
        """
        if len(time_diffs_seconds) == 0:
            return "unknown"
        
        # Tìm khoảng cách phổ biến nhất
        median_diff = np.median(time_diffs_seconds)
        
        # Chuyển đổi giây sang đơn vị lớn hơn để phát hiện tần suất
        minutes = median_diff / 60
        hours = minutes / 60
        days = hours / 24
        weeks = days / 7
        months = days / 30.44  # Số ngày trung bình trong tháng
        quarters = months / 3
        years = days / 365.25
        
        # Phát hiện tần suất dựa trên khoảng cách trung bình
        if median_diff <= 1:
            return "secondly"
        elif median_diff <= 60:
            return "minutely"
        elif hours <= 1:
            return "hourly"
        elif hours <= 24:
            # Phát hiện tần suất trong ngày (every 4 hours, etc.)
            if 3.5 <= hours <= 4.5:
                return "4-hourly"
            elif 5.5 <= hours <= 6.5:
                return "6-hourly"
            elif 11.5 <= hours <= 12.5:
                return "12-hourly"
            else:
                return "hourly"
        elif days <= 1.5:
            return "daily"
        elif days <= 7.5:
            if 6.5 <= days <= 7.5:
                return "weekly"
            else:
                return f"{int(round(days))}-daily"
        elif days <= 31:
            if 13 <= days <= 16:
                return "bi-weekly"
            elif 29 <= days <= 31:
                return "monthly"
            else:
                return f"{int(round(days))}-daily"
        elif months <= 1.5:
            return "monthly"
        elif months <= 3.5:
            return f"{int(round(months))}-monthly"
        elif months <= 12:
            if 2.5 <= months <= 3.5:
                return "quarterly"
            elif 5.5 <= months <= 6.5:
                return "semi-annually"
            else:
                return f"{int(round(months))}-monthly"
        else:
            if 11.5 <= months <= 12.5:
                return "yearly"
            elif years > 1:
                return f"{int(round(years))}-yearly"
            else:
                return f"{int(round(months))}-monthly"

    def _detect_seasonality(self, datetime_series: pd.Series) -> Dict:
        """
        Phát hiện tính mùa vụ trong dữ liệu thời gian
        
        Args:
            datetime_series: Series chứa datetime
            
        Returns:
            Dict: Kết quả phân tích seasonality
        """
        result = {"detected": False}
        
        # Kiểm tra có đủ dữ liệu không
        if len(datetime_series) < 30:
            result["message"] = "Not enough data for seasonality detection"
            return result
        
        try:
            # 1. Kiểm tra mẫu theo ngày trong tuần
            dow_counts = datetime_series.dt.dayofweek.value_counts().sort_index()
            
            # Tính chỉ số biến thiên
            if len(dow_counts) > 1:
                dow_cv = dow_counts.std() / dow_counts.mean()
                result["day_of_week"] = {
                    "counts": dow_counts.to_dict(),
                    "variation": float(dow_cv)
                }
                
                # Nếu biến thiên lớn, có thể có mẫu theo ngày trong tuần
                if dow_cv > 0.5:
                    result["detected"] = True
                    result["day_of_week"]["has_pattern"] = True
                    
                    # Tìm ngày cao điểm
                    peak_days = dow_counts.nlargest(2).index.tolist()
                    result["day_of_week"]["peak_days"] = [int(day) for day in peak_days]
            
            # 2. Kiểm tra mẫu theo tháng
            month_counts = datetime_series.dt.month.value_counts().sort_index()
            
            if len(month_counts) > 1:
                month_cv = month_counts.std() / month_counts.mean()
                result["month"] = {
                    "counts": month_counts.to_dict(),
                    "variation": float(month_cv)
                }
                
                # Nếu biến thiên lớn, có thể có mẫu theo tháng
                if month_cv > 0.3:
                    result["detected"] = True
                    result["month"]["has_pattern"] = True
                    
                    # Tìm tháng cao điểm
                    peak_months = month_counts.nlargest(3).index.tolist()
                    result["month"]["peak_months"] = [int(month) for month in peak_months]
            
            # 3. Kiểm tra mẫu theo quý
            datetime_quarters = datetime_series.dt.quarter
            quarter_counts = datetime_quarters.value_counts().sort_index()
            
            if len(quarter_counts) > 1:
                quarter_cv = quarter_counts.std() / quarter_counts.mean()
                result["quarter"] = {
                    "counts": quarter_counts.to_dict(),
                    "variation": float(quarter_cv)
                }
                
                # Nếu biến thiên lớn, có thể có mẫu theo quý
                if quarter_cv > 0.2:
                    result["detected"] = True
                    result["quarter"]["has_pattern"] = True
                    
                    # Tìm quý cao điểm
                    peak_quarters = quarter_counts.nlargest(2).index.tolist()
                    result["quarter"]["peak_quarters"] = [int(quarter) for quarter in peak_quarters]
            
            # 4. Phát hiện các ngày đặc biệt (tháng bắt đầu/kết thúc, quý kết thúc)
            month_start = (datetime_series.dt.day == 1).mean()
            month_end = datetime_series.dt.is_month_end.mean()
            
            if month_start > 0.4 or month_end > 0.4:
                result["detected"] = True
                result["special_days"] = {
                    "month_start_ratio": float(month_start),
                    "month_end_ratio": float(month_end)
                }
                
                # Kiểm tra ngày cuối quý
                is_quarter_end = (datetime_series.dt.month.isin([3, 6, 9, 12]) & 
                                datetime_series.dt.is_month_end)
                quarter_end_ratio = is_quarter_end.mean()
                
                if quarter_end_ratio > 0.2:
                    result["special_days"]["quarter_end_ratio"] = float(quarter_end_ratio)
            
            return result
        except Exception as e:
            return {"detected": False, "error": str(e)}
        
    def detect_datetime_format(self, sample_values: List[str]) -> Optional[str]:
        """
        Phát hiện định dạng datetime phổ biến nhất từ một tập mẫu
        
        Args:
            sample_values: Danh sách các giá trị thời gian dạng chuỗi
            
        Returns:
            Optional[str]: Định dạng phát hiện được hoặc None nếu không thể xác định
        """
        # Nếu không có giá trị, không thể phát hiện
        if not sample_values:
            return None
            
        # Cache key dựa trên mẫu dữ liệu
        cache_key = hash(tuple(str(v) for v in sample_values[:5]))
        if cache_key in self.detected_formats_cache:
            return self.detected_formats_cache[cache_key]
        
        # Tiền xử lý mẫu - sử dụng list comprehension thay vì for loop
        clean_samples = [self._clean_datetime_string(str(v)) for v in sample_values 
                        if v is not None and pd.notna(v)]
        if not clean_samples:
            return None
            
        # Kiểm tra các định dạng đặc biệt trước
        if self._check_if_timestamp(clean_samples):
            self.detected_formats_cache[cache_key] = self.unix_format
            return self.unix_format
        
        # Tối ưu kiểm tra format: Sử dụng chiến lược phân nhóm
        # Lấy 1 mẫu đầu tiên để dự đoán nhóm định dạng
        first_sample = clean_samples[0]
        
        # Tìm nhóm định dạng có khả năng cao nhất dựa trên pattern
        likely_groups = []
        
        # Kiểm tra các pattern cơ bản
        if self.date_patterns['iso8601'].match(first_sample):
            likely_groups.append('iso')
        elif self.date_patterns['dmy'].match(first_sample):
            likely_groups.append('dmy')
        elif self.date_patterns['mdy'].match(first_sample):
            likely_groups.append('mdy')
        elif self.date_patterns['ymd'].match(first_sample):
            likely_groups.append('ymd')
        
        # Kiểm tra nếu có dấu hai chấm - có thể có thời gian
        if ':' in first_sample:
            likely_groups.append('with_time')
        
        # Lựa chọn định dạng từ các nhóm có khả năng cao
        format_matches = {}
        
        # Nếu có nhóm có khả năng cao, chỉ kiểm tra các định dạng trong các nhóm đó
        formats_to_check = []
        if likely_groups:
            for group in likely_groups:
                formats_to_check.extend(self.format_groups.get(group, []))
        
        # Nếu không xác định được nhóm, kiểm tra tất cả định dạng 
        if not formats_to_check:
            formats_to_check = self.standard_formats
        
        # Đếm số lần match cho mỗi format - tối ưu vòng lặp
        for fmt in formats_to_check:
            match_count = 0
            for value in clean_samples:
                try:
                    datetime.strptime(value, fmt)
                    match_count += 1
                except ValueError:
                    continue
            
            if match_count > 0:
                format_matches[fmt] = match_count
        
        # Tìm format có nhiều match nhất
        if format_matches:
            best_format = max(format_matches.items(), key=lambda x: x[1])
            
            # Chỉ trả về nếu có ít nhất 3 match hoặc >50% mẫu match
            if best_format[1] >= 3 or best_format[1] / len(clean_samples) > 0.5:
                # Lưu vào cache
                self.detected_formats_cache[cache_key] = best_format[0]
                return best_format[0]
        
        # Phân tích ngôn ngữ và tìm tên tháng
        language_format = self._analyze_month_names(clean_samples)
        if language_format:
            self.detected_formats_cache[cache_key] = language_format
            return language_format
        
        # Thử phân tích chuỗi để tìm pattern
        pattern = self._analyze_datetime_pattern(clean_samples)
        if pattern:
            self.detected_formats_cache[cache_key] = pattern
            return pattern
            
        # Không tìm được format phù hợp
        self.detected_formats_cache[cache_key] = None
        return None

# Tạo một instance global cho lớp DateTimeProcessor
_datetime_processor = DateTimeProcessor()

# Tối ưu hoá các hàm helper bằng cách sử dụng instance đã tạo
def convert_to_datetime(series, preferred_formats=None, errors='coerce'):
    """Wrapper function cho convert_to_datetime - sử dụng instance duy nhất"""
    return _datetime_processor.convert_to_datetime(series, preferred_formats, errors)

def extract_datetime_features(df, datetime_column, cyclical_encoding=True, drop_original=False, 
                             add_holidays=False, country_code=None):
    """Wrapper function cho extract_datetime_features - sử dụng instance duy nhất"""
    # Nếu country_code khác với processor hiện tại, tạo mới instance với country_code đúng
    if country_code and country_code != _datetime_processor.country_code:
        temp_processor = DateTimeProcessor(country_code=country_code)
        return temp_processor.extract_datetime_features(df, datetime_column, cyclical_encoding, drop_original, add_holidays)
    
    return _datetime_processor.extract_datetime_features(df, datetime_column, cyclical_encoding, drop_original, add_holidays)

def analyze_datetime_distribution(series, country_code=None):
    """Wrapper function cho analyze_datetime_distribution - sử dụng instance duy nhất"""
    # Nếu country_code khác với processor hiện tại, tạo mới instance với country_code đúng
    if country_code and country_code != _datetime_processor.country_code:
        temp_processor = DateTimeProcessor(country_code=country_code)
        return temp_processor.analyze_datetime_distribution(series)
    
    return _datetime_processor.analyze_datetime_distribution(series)

# Tối ưu các hàm kiểm tra datetime
def is_datetime(
    series: Union[pd.Series, List, np.ndarray],
    threshold: float = 0.85,
    sample_size: int = 100,
    strict: bool = False
) -> bool:
    """
    Xác định xem một chuỗi giá trị có phải dạng datetime hay không
    
    Args:
        series: Chuỗi giá trị cần kiểm tra
        threshold: Tỉ lệ tối thiểu giá trị chuyển đổi thành công
        sample_size: Số lượng mẫu tối đa để kiểm tra
        strict: Nếu True, chỉ return True khi tất cả giá trị chuyển đổi thành công
        
    Returns:
        bool: True nếu là datetime, False nếu không phải
    """
    # Chuyển sang pandas Series nếu cần
    if not isinstance(series, pd.Series):
        series = pd.Series(series)
    
    # Nếu đã là datetime, trả về True
    if is_datetime64_any_dtype(series):
        return True
    
    # Lọc bỏ null values nhanh chóng
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
        
    try:
        # Lấy mẫu dữ liệu để kiểm tra nhanh - sử dụng pandas sampling thay vì vòng lặp
        sample = non_null.sample(min(sample_size, len(non_null))).astype(str).tolist()
        
        # Phát hiện định dạng
        detected_format = _datetime_processor.detect_datetime_format(sample)
        if not detected_format:
            return False
            
        # Kiểm tra chất lượng chuyển đổi
        test_sample = non_null.head(min(sample_size, len(non_null))).astype(str)
        converted = _datetime_processor.convert_to_datetime(test_sample, errors='coerce')
        
        # Tính tỉ lệ thành công
        success_rate = converted.notna().mean()
        
        if strict:
            # Chế độ nghiêm ngặt: yêu cầu tất cả giá trị đều chuyển đổi được
            return success_rate > 0.99
        else:
            # Chế độ thông thường: chỉ cần đạt threshold
            return success_rate >= threshold
    except Exception:
        # Bất kỳ lỗi gì đều trả về False
        return False

def is_datetime_column(df: pd.DataFrame, column_name: str, threshold: float = 0.85) -> bool:
    """
    Kiểm tra nhanh xem một cột trong DataFrame có phải là datetime hay không
    
    Args:
        df: DataFrame chứa cột cần kiểm tra
        column_name: Tên cột cần kiểm tra
        threshold: Tỉ lệ tối thiểu giá trị chuyển đổi thành công
        
    Returns:
        bool: True nếu là datetime, False nếu không phải
    """
    if column_name not in df.columns:
        return False
        
    return is_datetime(df[column_name], threshold=threshold)

def detect_datetime_columns(
    df: pd.DataFrame, 
    threshold: float = 0.85, 
    sample_size: int = 100
) -> List[str]:
    """
    Phát hiện tất cả cột datetime trong DataFrame
    
    Args:
        df: DataFrame cần kiểm tra
        threshold: Tỉ lệ tối thiểu giá trị chuyển đổi thành công
        sample_size: Số lượng mẫu tối đa cho mỗi cột
        
    Returns:
        List[str]: Danh sách tên cột là datetime
    """
    # Cải thiện bằng cách sử dụng list comprehension thay vì vòng lặp for
    
    # Lọc các cột đã là datetime
    datetime_cols = [col for col in df.columns if is_datetime64_any_dtype(df[col])]
    
    # Tên cột có khả năng là datetime
    potential_datetime_cols = [col for col in df.columns 
                              if col not in datetime_cols 
                              and any(term in col.lower() for term in 
                                     ['date', 'time', 'day', 'month', 'year', 'createdAt', 'updatedAt', 'ngày', 'tháng', 'năm'])]
    
    # Kiểm tra các cột tiềm năng song song
    results = []
    for col in potential_datetime_cols:
        if is_datetime(df[col], threshold=threshold, sample_size=sample_size):
            results.append(col)
    
    # Kết hợp kết quả
    datetime_cols.extend(results)
            
    return datetime_cols

def identify_date_format(value_str: str) -> str:
    """
    Phát hiện định dạng ngày tháng của một chuỗi
    
    Args:
        value_str: Chuỗi cần phân tích
        
    Returns:
        str: Định dạng phát hiện được hoặc 'unknown'
    """
    if not isinstance(value_str, str):
        return 'unknown'
    
    value_str = value_str.strip()
    
    # Kiểm tra timestamp
    if re.match(r'^\d{9,13}$', value_str):
        return 'timestamp'
    
    # Kiểm tra ISO
    try:
        datetime.fromisoformat(value_str.replace('Z', '+00:00'))
        return 'iso'
    except:
        pass
    
    # Kiểm tra các định dạng cơ bản
    dmy_pattern = re.compile(r'(\d{1,2})[\/\s.\-](\d{1,2}|[a-zA-Z]{3,})[\/\s.\-](\d{2,4})')
    mdy_pattern = re.compile(r'(\d{1,2}|[a-zA-Z]{3,})[\/\s.\-](\d{1,2})[\/\s.\-](\d{2,4})')
    ymd_pattern = re.compile(r'(\d{4})[\/\s.\-](\d{1,2}|[a-zA-Z]{3,})[\/\s.\-](\d{1,2})')
    
    if dmy_pattern.match(value_str):
        return 'dmy'
    if mdy_pattern.match(value_str):
        return 'mdy'
    if ymd_pattern.match(value_str):
        return 'ymd'
    
    # Kiểm tra các định dạng datetime tiêu chuẩn
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S']:
        try:
            datetime.strptime(value_str, fmt)
            return fmt
        except ValueError:
            continue
    
    # Kiểm tra định dạng với thời gian
    if ':' in value_str:
        for fmt in ['%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S']:
            try:
                datetime.strptime(value_str, fmt)
                return fmt
            except ValueError:
                continue
    
    # Thử sử dụng parser tổng quát từ dateutil
    try:
        from dateutil import parser
        parser.parse(value_str)
        return 'dateutil_auto'
    except:
        pass
    
    return 'unknown'

def detect_datetime_format(sample_values: List[str]) -> Optional[str]:
    """
    Phát hiện định dạng datetime phổ biến nhất từ danh sách mẫu
    
    Args:
        sample_values: Danh sách các giá trị thời gian
        
    Returns:
        Optional[str]: Định dạng phổ biến nhất hoặc None
    """
    if not sample_values or len(sample_values) == 0:
        return None
    
    # Lọc giá trị hợp lệ
    valid_samples = [str(v).strip() for v in sample_values if v is not None and pd.notna(v)]
    if not valid_samples:
        return None
    
    # Kiểm tra từng giá trị và đếm số lần xuất hiện của mỗi định dạng
    format_counts = {}
    
    for value in valid_samples:
        fmt = identify_date_format(value)
        if fmt != 'unknown':
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
    
    if not format_counts:
        return None
    
    # Tìm định dạng phổ biến nhất
    most_common_format = max(format_counts.items(), key=lambda x: x[1])
    
    # Nếu định dạng phổ biến nhất chiếm đa số (>50%)
    if most_common_format[1] / len(valid_samples) > 0.5:
        return most_common_format[0]
    
    # Cố gắng phát hiện định dạng chung
    if 'dateutil_auto' in format_counts:
        # Thử convert tất cả với dateutil
        try:
            from dateutil import parser
            success = sum(1 for v in valid_samples if _try_parse_with_dateutil(v))
            if success / len(valid_samples) > 0.8:
                return 'dateutil_auto'
        except:
            pass
    
    return None

def _try_parse_with_dateutil(value: str) -> bool:
    """Thử phân tích chuỗi với dateutil"""
    try:
        from dateutil import parser
        parser.parse(value)
        return True
    except:
        return False
    
if __name__ == "__main__":
    datetime_str = "04-Jan-22"
    print(is_datetime([datetime_str]))