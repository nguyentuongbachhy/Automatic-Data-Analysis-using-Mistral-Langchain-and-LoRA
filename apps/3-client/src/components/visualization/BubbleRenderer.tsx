import { useCallback, useMemo, useState } from 'react';
import {
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Scatter,
    ScatterChart,
    Tooltip,
    XAxis,
    YAxis,
    ZAxis
} from 'recharts';
import { formatNumber } from '../../utils/chart';

// Màu sắc cho đồ thị
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6'
];

// Hàm để lấy mẫu dữ liệu khi có quá nhiều điểm
function sampleData(data: any[], maxPoints: number = 1000, samplingRate?: number) {
    if (!data || data.length <= maxPoints) return data;

    // Nếu có samplingRate, ưu tiên sử dụng samplingRate
    if (samplingRate && samplingRate > 0 && samplingRate < 1) {
        return data.filter(() => Math.random() < samplingRate);
    }

    // Nếu không có samplingRate, sử dụng maxPoints
    const interval = Math.ceil(data.length / maxPoints);
    return data.filter((_, index) => index % interval === 0);
}

interface BubbleRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: {
        xAxis?: { name?: string; key?: string };
        yAxis?: { name?: string; key?: string };
        sizeAxis?: { name?: string; key?: string };
        colorBy?: string;
        maxPoints?: number;
        minBubbleSize?: number;
        maxBubbleSize?: number;
        categories?: string;
        alwaysShowTooltip?: boolean;
        samplingRate?: number;
    };
}

export default function BubbleRenderer({ data, title, description, config = {} }: BubbleRendererProps) {
    const alwaysShowTooltip = config?.alwaysShowTooltip || false;

    // Mặc định cho các cấu hình
    const {
        xAxis = { name: 'X', key: 'x' },
        yAxis = { name: 'Y', key: 'y' },
        sizeAxis = { name: 'Size', key: 'value' },
        minBubbleSize = 10,
        maxBubbleSize = 60,
        maxPoints = 1000,
        samplingRate = 0,
        colorBy
    } = config;

    // State để theo dõi điểm được hover
    const [hoveredData, setHoveredData] = useState<any>(null);

    // Chuẩn hóa và xử lý dữ liệu đầu vào
    const safeData = useMemo(() => {
        if (!data) return [];
        return Array.isArray(data) ? data : [];
    }, [data]);

    // Phát hiện các thuộc tính x, y, z trong dữ liệu
    const hasDefaultProps = useMemo(() => {
        if (xAxis.key === undefined || yAxis.key === undefined || sizeAxis.key === undefined) return null
        return safeData.length > 0 && safeData[0] &&
            ('x' in safeData[0] || xAxis.key in safeData[0]) &&
            ('y' in safeData[0] || yAxis.key in safeData[0]) &&
            ('value' in safeData[0] || 'size' in safeData[0] || 'z' in safeData[0] || (sizeAxis.key in safeData[0]));
    }, [safeData, xAxis, yAxis, sizeAxis]);

    // Xử lý dữ liệu cho bubble chart
    const processedData = useMemo(() => {
        if (safeData.length === 0) return [];

        let bubbleData;

        if (hasDefaultProps) {
            // Trường hợp dữ liệu đã có thuộc tính x, y, value
            bubbleData = safeData.map(item => {
                if (!item || xAxis.key === undefined || yAxis.key === undefined || sizeAxis.key === undefined) return null;

                const x = Number(item[xAxis.key] !== undefined ? item[xAxis.key] : item.x);
                const y = Number(item[yAxis.key] !== undefined ? item[yAxis.key] : item.y);
                const size = Number(
                    item[sizeAxis.key] !== undefined ? item[sizeAxis.key] :
                        item.value !== undefined ? item.value :
                            item.size !== undefined ? item.size :
                                item.z !== undefined ? item.z : 1
                );

                // Chỉ giữ các điểm có tọa độ x, y hợp lệ
                if (isNaN(x) || isNaN(y)) return null;

                return {
                    ...item,
                    x,
                    y,
                    z: Math.max(0.1, size), // Đảm bảo kích thước bubble luôn dương
                    name: item.name || item.category || `Point`,
                    category: item.category || item.group || ''
                };
            }).filter(Boolean);
        } else {
            // Trường hợp phải tự phát hiện thuộc tính
            const firstItem = safeData[0];
            if (!firstItem || typeof firstItem !== 'object') {
                return [];
            }

            // Tìm các thuộc tính số
            const numericKeys = Object.keys(firstItem).filter(
                key => typeof firstItem[key] === 'number'
            );

            if (numericKeys.length < 3) return [];

            // Sử dụng 3 thuộc tính số đầu tiên cho x, y, z
            const xKey = numericKeys[0];
            const yKey = numericKeys[1];
            const zKey = numericKeys[2];

            bubbleData = safeData.map(item => {
                if (!item) return null;

                const x = Number(item[xKey]);
                const y = Number(item[yKey]);
                const size = Number(item[zKey]);

                if (isNaN(x) || isNaN(y)) return null;

                return {
                    ...item,
                    x,
                    y,
                    z: Math.max(0.1, size),
                    name: item.name || item.category || `Point`,
                    category: item.category || item.group || ''
                };
            }).filter(Boolean);
        }

        // Xử lý phân nhóm theo category nếu có
        if (colorBy && bubbleData.some(item => item[colorBy])) {
            // Map các category với màu sắc
            const categories = [...new Set(bubbleData.map(item => item[colorBy]))];
            const colorMap = Object.fromEntries(
                categories.map((category, index) => [category, COLORS[index % COLORS.length]])
            );

            // Gán màu sắc dựa vào category
            bubbleData = bubbleData.map(item => ({
                ...item,
                fill: colorMap[item[colorBy]] || COLORS[0]
            }));
        }

        // Lấy mẫu nếu có quá nhiều điểm
        return sampleData(bubbleData, maxPoints, samplingRate);
    }, [safeData, hasDefaultProps, xAxis, yAxis, sizeAxis, colorBy, maxPoints, samplingRate]);

    // Tìm min, max cho z-axis để scale kích thước bong bóng
    const zAxisDomain = useMemo(() => {
        if (processedData.length === 0) return [0, 1];

        let minZ = Infinity;
        let maxZ = -Infinity;

        processedData.forEach(item => {
            minZ = Math.min(minZ, item.z);
            maxZ = Math.max(maxZ, item.z);
        });

        return [minZ === Infinity ? 0 : minZ, maxZ === -Infinity ? 1 : maxZ];
    }, [processedData]);

    // Tạo dữ liệu cho Legend
    const legendData = useMemo(() => {
        if (!colorBy || processedData.length === 0) return [];

        const categories = [...new Set(processedData.map(item => item[colorBy]))];

        return categories.map((category, index) => ({
            value: String(category),
            color: COLORS[index % COLORS.length]
        }));
    }, [processedData, colorBy]);

    // Custom tooltip component
    const CustomTooltip = useCallback(({ active, payload }: any) => {
        const display = active || alwaysShowTooltip;

        if (display && payload && payload.length && payload[0] && payload[0].payload) {
            const point = payload[0].payload;

            return (
                <div className="bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    <p className="font-medium">{xAxis.name || 'X'}: {formatNumber(point.x)}</p>
                    <p className="font-medium">{yAxis.name || 'Y'}: {formatNumber(point.y)}</p>
                    <p className="font-medium">{sizeAxis.name || 'Size'}: {formatNumber(point.z)}</p>

                    {/* Hiển thị tên nếu có */}
                    {point.name && <p className="font-medium">Name: {point.name}</p>}

                    {/* Hiển thị category nếu có */}
                    {colorBy && point[colorBy] && (
                        <p className="font-medium">{colorBy}: {point[colorBy]}</p>
                    )}

                    {/* Hiển thị các thuộc tính khác */}
                    {Object.entries(point).map(([key, value]) => {
                        if (
                            key !== 'x' && key !== 'y' && key !== 'z' &&
                            key !== 'name' && key !== colorBy && key !== 'fill' &&
                            typeof value !== 'object' && value !== undefined
                        ) {
                            return (
                                <p key={key} className="font-medium">
                                    {key}: {typeof value === 'number' ? formatNumber(value) : String(value)}
                                </p>
                            );
                        }
                        return null;
                    })}
                </div>
            );
        }

        return null;
    }, [alwaysShowTooltip, xAxis.name, yAxis.name, sizeAxis.name, colorBy]);

    // Xử lý sự kiện hover
    const handleMouseMove = useCallback((state: any) => {
        if (alwaysShowTooltip && state && state.activePayload && state.activePayload.length) {
            setHoveredData(state.activePayload[0].payload);
        }
    }, [alwaysShowTooltip]);

    // Custom Legend
    const CustomLegend = useCallback(() => {
        if (legendData.length === 0) return null;

        return (
            <div className="flex flex-wrap justify-center mt-2 gap-2">
                {legendData.map((item, index) => (
                    <div key={index} className="flex items-center">
                        <div
                            className="w-3 h-3 rounded-full mr-1"
                            style={{ backgroundColor: item.color }}
                        />
                        <span className="text-xs">{item.value}</span>
                    </div>
                ))}
            </div>
        );
    }, [legendData]);

    // Render bubble chart
    const renderChart = useMemo(() => {
        if (!processedData || processedData.length === 0) {
            return (
                <div className="flex items-center justify-center h-full">
                    <div className="text-gray-500">Không có dữ liệu để hiển thị</div>
                </div>
            );
        }

        return (
            <ScatterChart
                margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
                onMouseMove={handleMouseMove}
            >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />

                <XAxis
                    type="number"
                    dataKey="x"
                    name={xAxis.name || 'X'}
                    domain={['auto', 'auto']}
                    label={{
                        value: xAxis.name,
                        position: 'insideBottom',
                        offset: -5
                    }}
                />

                <YAxis
                    type="number"
                    dataKey="y"
                    name={yAxis.name || 'Y'}
                    domain={['auto', 'auto']}
                    label={{
                        value: yAxis.name,
                        angle: -90,
                        position: 'insideLeft'
                    }}
                />

                <ZAxis
                    type="number"
                    dataKey="z"
                    range={[minBubbleSize, maxBubbleSize]}
                    domain={zAxisDomain}
                />

                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />

                {colorBy && <Legend content={<CustomLegend />} />}

                <Scatter
                    name="Bubble Chart"
                    data={processedData}
                    fill={colorBy ? undefined : COLORS[0]}
                    isAnimationActive={true}
                />
            </ScatterChart>
        );
    }, [
        processedData,
        handleMouseMove,
        xAxis,
        yAxis,
        zAxisDomain,
        minBubbleSize,
        maxBubbleSize,
        CustomTooltip,
        colorBy,
        CustomLegend
    ]);

    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
                <div className="flex items-center justify-between mt-1">
                    <div className="text-xs text-gray-500">
                        {processedData.length} điểm
                        {safeData.length > maxPoints ?
                            ` (đã lấy mẫu từ ${safeData.length} điểm)` : ''}
                    </div>
                </div>
            </div>

            {/* Hiển thị thông tin tooltip khi hover */}
            {alwaysShowTooltip && hoveredData && (
                <div className="mt-2 bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    <p className="font-medium">{xAxis.name || 'X'}: {formatNumber(hoveredData.x)}</p>
                    <p className="font-medium">{yAxis.name || 'Y'}: {formatNumber(hoveredData.y)}</p>
                    <p className="font-medium">{sizeAxis.name || 'Size'}: {formatNumber(hoveredData.z)}</p>
                    {colorBy && hoveredData[colorBy] && (
                        <p className="font-medium">{colorBy}: {hoveredData[colorBy]}</p>
                    )}
                </div>
            )}

            <div className="h-full w-full">
                <ResponsiveContainer width="95%" height="90%">
                    {renderChart}
                </ResponsiveContainer>
            </div>
        </div>
    );
}