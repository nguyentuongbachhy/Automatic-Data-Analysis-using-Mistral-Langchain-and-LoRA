import numeral from 'numeral';

const HEATMAP_COLORS = [
    '#313695', '#74add1', '#ffffbf', '#fdae61', '#a50026'
];

export const formatNumber = (value: number): string => {
    return numeral(value).format("0.000")
};

// Ánh xạ màu cho heatmap
export const getHeatmapColor = (value: number, min: number, max: number) => {
    if (min === max) return HEATMAP_COLORS[2];
    const normalized = (value - min) / (max - min);
    const colorIndex = Math.min(
        Math.floor(normalized * HEATMAP_COLORS.length),
        HEATMAP_COLORS.length - 1
    );
    return HEATMAP_COLORS[colorIndex];
};

// Hàm helper để tạo tên hiển thị
export const getDisplayName = (key: string): string => {
    return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/_/g, ' ')
        .replace(/^\w/, c => c.toUpperCase());
};

// Kiểm tra định dạng dữ liệu chart
export const isChartDataFormat = (data: any): boolean => {
    return data && typeof data === 'object' &&
        (Array.isArray(data.values) || Array.isArray(data.dimensions) || Array.isArray(data.measures));
};

// Lấy mẫu thông minh, giữ lại hình dạng phân phối
export const sampleData = (data: any[], maxPoints: number = 1000, samplingRate = 0): any[] => {
    if (!Array.isArray(data) || data.length <= maxPoints) return data || [];

    // Nếu có samplingRate được chỉ định
    if (samplingRate > 1) {
        return data.filter((_, index) => index % samplingRate === 0);
    }

    // Chia dữ liệu thành grid và giữ điểm đại diện
    const sampledData: any[] = [];
    const gridMap = new Map();

    // Xác định giới hạn x và y
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    data.forEach(point => {
        if (!point) return;
        const x = point.x !== undefined ? Number(point.x) : 0;
        const y = point.y !== undefined ? Number(point.y) : 0;
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
    });

    // Số lượng ô grid mỗi chiều
    const gridSize = Math.ceil(Math.sqrt(maxPoints));

    // Kích thước một ô
    const cellWidth = (maxX - minX) / gridSize || 1;
    const cellHeight = (maxY - minY) / gridSize || 1;

    // Đưa điểm vào grid
    data.forEach(point => {
        if (!point) return;
        const x = point.x !== undefined ? Number(point.x) : 0;
        const y = point.y !== undefined ? Number(point.y) : 0;

        // Tính vị trí grid
        const gridX = Math.floor((x - minX) / cellWidth);
        const gridY = Math.floor((y - minY) / cellHeight);
        const key = `${gridX}-${gridY}`;

        if (!gridMap.has(key)) {
            gridMap.set(key, point);
        }
    });

    // Lấy điểm đại diện từ mỗi grid
    gridMap.forEach(point => {
        sampledData.push(point);
    });

    return sampledData;
};