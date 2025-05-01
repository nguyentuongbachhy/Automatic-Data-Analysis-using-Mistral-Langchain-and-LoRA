import { useCallback, useMemo, useState } from 'react';
import {
    CartesianGrid,
    Label,
    Legend,
    ReferenceArea,
    ReferenceLine,
    ResponsiveContainer,
    Scatter,
    ScatterChart,
    Tooltip,
    XAxis,
    YAxis,
    ZAxis
} from 'recharts';
import { formatNumber } from '../../utils/chart';

// Màu sắc cho biểu đồ phân tán
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6'
];

/**
 * Hàm lấy mẫu dữ liệu khi có quá nhiều điểm
 * @param data Dữ liệu gốc
 * @param maxPoints Số điểm tối đa muốn hiển thị
 * @param samplingRate Tỷ lệ lấy mẫu (0-1)
 * @returns Dữ liệu đã lấy mẫu
 */
function sampleData(data: any[], maxPoints: number = 5000, samplingRate?: number) {
    if (!data || data.length <= maxPoints) return data;

    // Nếu có samplingRate, ưu tiên sử dụng samplingRate
    if (samplingRate && samplingRate > 0 && samplingRate < 1) {
        return data.filter(() => Math.random() < samplingRate);
    }

    // Nếu không có samplingRate, sử dụng maxPoints
    const interval = Math.ceil(data.length / maxPoints);
    return data.filter((_, index) => index % interval === 0);
}

/**
 * Tính toán mật độ điểm trong biểu đồ phân tán
 * @param data Dữ liệu điểm
 * @param binCount Số lượng bin trên mỗi trục
 * @returns Dữ liệu mật độ đã tính toán
 */
function calculateDensity(data: any[], binCount: number = 50) {
    if (!data || data.length === 0) return [];

    // Tìm min, max cho các trục
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    data.forEach(point => {
        if (!point) return;
        const x = Number(point.x || 0);
        const y = Number(point.y || 0);
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
    });

    if (minX === Infinity) {
        minX = 0; maxX = 1;
        minY = 0; maxY = 1;
    }

    // Tính kích thước của mỗi bin
    const binWidth = (maxX - minX) / binCount || 1;
    const binHeight = (maxY - minY) / binCount || 1;

    // Tính mật độ với Map
    const bins = new Map();

    data.forEach(point => {
        if (!point) return;
        const x = Number(point.x || 0);
        const y = Number(point.y || 0);

        const binX = Math.floor((x - minX) / binWidth);
        const binY = Math.floor((y - minY) / binHeight);
        const key = `${binX}-${binY}`;

        const binCenterX = minX + (binX + 0.5) * binWidth;
        const binCenterY = minY + (binY + 0.5) * binHeight;

        if (bins.has(key)) {
            bins.get(key).count++;
        } else {
            bins.set(key, {
                x: binCenterX,
                y: binCenterY,
                count: 1,
                // Lưu thêm thông tin bin để hiển thị tooltip
                binMinX: minX + binX * binWidth,
                binMaxX: minX + (binX + 1) * binWidth,
                binMinY: minY + binY * binHeight,
                binMaxY: minY + (binY + 1) * binHeight
            });
        }
    });

    // Chuyển từ Map sang Array
    const result = Array.from(bins.values());

    // Tính toán kích thước điểm dựa trên số lượng
    const maxCount = Math.max(...result.map(bin => bin.count), 1);

    return result.map(bin => ({
        ...bin,
        z: Math.max(1, Math.ceil((bin.count / maxCount) * 10)),
        // Tính màu dựa trên mật độ
        fill: getColorFromDensity(bin.count / maxCount)
    }));
}

/**
 * Tạo màu dựa trên mật độ điểm
 * @param density Giá trị mật độ từ 0-1
 * @returns Mã màu hex
 */
function getColorFromDensity(density: number): string {
    // Từ xanh nhạt đến xanh đậm
    const baseColors = ['#EBF5FB', '#AED6F1', '#3498DB', '#2874A6', '#1A5276'];

    const index = Math.min(
        baseColors.length - 1,
        Math.floor(density * baseColors.length)
    );

    return baseColors[index];
}

interface ScatterRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: {
        xAxis?: { name?: string; key?: string; min?: number; max?: number };
        yAxis?: { name?: string; key?: string; min?: number; max?: number };
        maxPoints?: number;
        colorBy?: string;
        markerSize?: number;
        useDensity?: boolean;
        samplingRate?: number;
        alwaysShowTooltip?: boolean;
        showRegressionLine?: boolean;
        showQuadrants?: boolean;
        quadrantLabels?: string[];
        trendlines?: {
            show?: boolean;
            color?: string;
            type?: 'linear' | 'polynomial';
            degree?: number;
        };
        annotations?: Array<{
            type: 'point' | 'area';
            x1?: number;
            y1?: number;
            x2?: number;
            y2?: number;
            label?: string;
            color?: string;
        }>;
    };
}

export default function ScatterRenderer({ data, title, description, config = {} }: ScatterRendererProps) {
    // Thuộc tính config
    const alwaysShowTooltip = config?.alwaysShowTooltip || false;
    const showDensityDefault = config?.useDensity || false;

    // Các cấu hình mặc định
    const {
        xAxis = { name: 'X' },
        yAxis = { name: 'Y' },
        maxPoints = 5000,
        markerSize = 3,
        samplingRate = 0,
        showRegressionLine = false,
        showQuadrants = false,
        quadrantLabels = ['', '', '', ''],
        colorBy
    } = config;

    // State cho chế độ hiển thị mật độ
    const [showDensity, setShowDensity] = useState(showDensityDefault || false);
    const [hoveredData, setHoveredData] = useState<any>(null);

    // Kiểm tra dữ liệu có thuộc tính x, y sẵn không
    const hasXYProps = useMemo(() => {
        return data.length > 0 && data[0] && 'x' in data[0] && 'y' in data[0];
    }, [data]);

    // Xử lý dữ liệu scatterplot
    const processedData = useMemo(() => {
        if (data.length === 0) return [];

        let scatterData;

        // Chuẩn hóa dữ liệu tùy thuộc vào định dạng
        if (hasXYProps) {
            scatterData = data.map(item => ({
                ...item,
                x: Number(item.x),
                y: Number(item.y),
                category: item.category || item.group || ''
            }));
        } else {
            const firstItem = data[0];
            if (!firstItem || typeof firstItem !== 'object') {
                return [];
            }

            // Tìm các khóa có giá trị là số
            const numericKeys = Object.keys(firstItem).filter(
                key => typeof firstItem[key] === 'number'
            );

            if (numericKeys.length < 2) return [];

            // Sử dụng khóa từ config nếu có, ngược lại dùng 2 khóa số đầu tiên
            const xKey = xAxis.key || numericKeys[0];
            const yKey = yAxis.key || numericKeys[1];

            scatterData = data.map(item => {
                if (!item) return { x: 0, y: 0 };
                return {
                    ...item,
                    x: Number(item[xKey] || 0),
                    y: Number(item[yKey] || 0),
                    category: item.category || item.group || ''
                };
            });
        }

        // Lọc các điểm không hợp lệ
        scatterData = scatterData.filter(point =>
            point &&
            point.x !== undefined && point.y !== undefined &&
            point.x !== null && point.y !== null &&
            !isNaN(Number(point.x)) && !isNaN(Number(point.y))
        );

        // Kiểm tra nếu có colorBy, thêm màu vào các điểm
        if (colorBy && scatterData.some(item => item[colorBy])) {
            // Tạo danh sách các loại giá trị
            const categories = [...new Set(scatterData.map(item => item[colorBy]))];

            // Map màu cho từng loại
            const colorMap = Object.fromEntries(
                categories.map((category, index) => [category, COLORS[index % COLORS.length]])
            );

            // Gán màu cho từng điểm
            scatterData = scatterData.map(item => ({
                ...item,
                fill: colorMap[item[colorBy]] || COLORS[0]
            }));
        }

        // Lấy mẫu nếu số lượng điểm quá lớn
        return sampleData(scatterData, maxPoints, samplingRate);
    }, [data, hasXYProps, xAxis.key, yAxis.key, colorBy, maxPoints, samplingRate]);

    // Tính toán dữ liệu mật độ nếu showDensity = true
    const densityData = useMemo(() => {
        if (!showDensity || processedData.length === 0) return [];

        // Tính số bin dựa trên số lượng điểm
        const binCount = Math.min(50, Math.ceil(Math.sqrt(processedData.length / 5)));

        return calculateDensity(processedData, binCount);
    }, [processedData, showDensity]);

    // Dữ liệu hiển thị (điểm thường hoặc điểm mật độ)
    const displayData = useMemo(() => {
        return showDensity && densityData.length > 0 ? densityData : processedData;
    }, [showDensity, densityData, processedData]);

    // Tính toán đường hồi quy tuyến tính (nếu cần)
    const regressionLine = useMemo(() => {
        if (!showRegressionLine || processedData.length < 2) return null;

        // Tính các giá trị cần thiết cho hồi quy tuyến tính
        let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        let n = processedData.length;

        processedData.forEach(point => {
            const x = Number(point.x);
            const y = Number(point.y);
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumX2 += x * x;
        });

        // Tính hệ số của đường hồi quy y = a*x + b
        const a = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        const b = (sumY - a * sumX) / n;

        // Tìm giá trị min, max của x
        const xValues = processedData.map(point => point.x);
        const minX = Math.min(...xValues);
        const maxX = Math.max(...xValues);

        // Tạo 2 điểm để vẽ đường thẳng
        return [
            { x: minX, y: a * minX + b },
            { x: maxX, y: a * maxX + b }
        ];
    }, [showRegressionLine, processedData]);

    // Tạo dữ liệu legend
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
                    {/* Nếu là điểm mật độ */}
                    {showDensity ? (
                        <>
                            <p className="font-medium">{xAxis.name || 'X'}: {formatNumber(Number(point.x))}</p>
                            <p className="font-medium">{yAxis.name || 'Y'}: {formatNumber(Number(point.y))}</p>
                            <p className="font-medium">Số điểm: {point.count}</p>
                            {point.binMinX !== undefined && (
                                <p className="text-xs mt-1">
                                    Phạm vi X: {formatNumber(point.binMinX)} - {formatNumber(point.binMaxX)}
                                </p>
                            )}
                            {point.binMinY !== undefined && (
                                <p className="text-xs">
                                    Phạm vi Y: {formatNumber(point.binMinY)} - {formatNumber(point.binMaxY)}
                                </p>
                            )}
                        </>
                    ) : (
                        <>
                            <p className="font-medium">{xAxis.name || 'X'}: {formatNumber(Number(point.x))}</p>
                            <p className="font-medium">{yAxis.name || 'Y'}: {formatNumber(Number(point.y))}</p>

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
                        </>
                    )}
                </div>
            );
        }

        return null;
    }, [alwaysShowTooltip, showDensity, xAxis.name, yAxis.name, colorBy]);

    // Custom dot component
    const CustomDot = useCallback((props: any) => {
        const { cx, cy, payload } = props;

        // Sử dụng fill từ payload nếu có (đã được gán khi có colorBy)
        const fill = payload.fill || props.fill || COLORS[0];

        // Kích thước dot có thể được cấu hình
        const size = markerSize || 3;

        return (
            <circle
                cx={cx}
                cy={cy}
                r={size}
                fill={fill}
                stroke={fill}
                strokeWidth={0.5}
                fillOpacity={0.7}
            />
        );
    }, [markerSize]);

    // Xử lý sự kiện hover
    const handleMouseMove = useCallback((state: any) => {
        if (alwaysShowTooltip && state && state.activePayload && state.activePayload.length) {
            setHoveredData(state.activePayload[0].payload);
        }
    }, [alwaysShowTooltip]);

    // Custom legend
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

    // Tính toán domain cho các trục
    const axisDomains = useMemo(() => {
        if (processedData.length === 0) return { x: [0, 0], y: [0, 0] };

        // Tìm min, max cho trục x và y
        const xValues = processedData.map(d => d.x);
        const yValues = processedData.map(d => d.y);

        let xMin = config?.xAxis?.min !== undefined ? config.xAxis.min : Math.min(...xValues);
        let xMax = config?.xAxis?.max !== undefined ? config.xAxis.max : Math.max(...xValues);
        let yMin = config?.yAxis?.min !== undefined ? config.yAxis.min : Math.min(...yValues);
        let yMax = config?.yAxis?.max !== undefined ? config.yAxis.max : Math.max(...yValues);

        // Thêm khoảng cách để biểu đồ đẹp hơn
        const xRange = xMax - xMin;
        const yRange = yMax - yMin;

        xMin = xMin - xRange * 0.05;
        xMax = xMax + xRange * 0.05;
        yMin = yMin - yRange * 0.05;
        yMax = yMax + yRange * 0.05;

        return { x: [xMin, xMax], y: [yMin, yMax] };
    }, [processedData, config?.xAxis?.min, config?.xAxis?.max, config?.yAxis?.min, config?.yAxis?.max]);

    // Render biểu đồ
    const renderChart = useMemo(() => {
        if (!displayData || displayData.length === 0) {
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
                    domain={axisDomains.x}
                    label={{
                        value: xAxis.name || 'X',
                        position: 'insideBottom',
                        offset: -5,
                        fontSize: 12
                    }}
                />

                <YAxis
                    type="number"
                    dataKey="y"
                    name={yAxis.name || 'Y'}
                    domain={axisDomains.y}
                    label={{
                        value: yAxis.name || 'Y',
                        angle: -90,
                        position: 'insideLeft',
                        fontSize: 12
                    }}
                />

                {/* ZAxis cho kích thước mật độ */}
                {showDensity && (
                    <ZAxis
                        type="number"
                        dataKey="z"
                        range={[markerSize, markerSize * 5]}
                        domain={[0, 'auto']}
                    />
                )}

                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />

                {/* Hiển thị legend nếu colorBy được cấu hình */}
                {colorBy && <Legend content={<CustomLegend />} />}

                {/* Hiển thị quadrants nếu có cấu hình showQuadrants */}
                {showQuadrants && (
                    <>
                        <ReferenceLine
                            x={0}
                            stroke="#666"
                            strokeDasharray="3 3"
                            label=""
                        />
                        <ReferenceLine
                            y={0}
                            stroke="#666"
                            strokeDasharray="3 3"
                            label=""
                        />

                        {/* Quadrant labels */}
                        {quadrantLabels[0] && (
                            <ReferenceArea
                                x1={axisDomains.x[0]}
                                x2={0}
                                y1={0}
                                y2={axisDomains.y[1]}
                                fillOpacity={0.05}
                            >
                                <Label position="center" fontSize={10}>{quadrantLabels[0]}</Label>
                            </ReferenceArea>
                        )}
                        {quadrantLabels[1] && (
                            <ReferenceArea
                                x1={0}
                                x2={axisDomains.x[1]}
                                y1={0}
                                y2={axisDomains.y[1]}
                                fillOpacity={0.05}
                            >
                                <Label position="center" fontSize={10}>{quadrantLabels[1]}</Label>
                            </ReferenceArea>
                        )}
                        {quadrantLabels[2] && (
                            <ReferenceArea
                                x1={axisDomains.x[0]}
                                x2={0}
                                y1={axisDomains.y[0]}
                                y2={0}
                                fillOpacity={0.05}
                            >
                                <Label position="center" fontSize={10}>{quadrantLabels[2]}</Label>
                            </ReferenceArea>
                        )}
                        {quadrantLabels[3] && (
                            <ReferenceArea
                                x1={0}
                                x2={axisDomains.x[1]}
                                y1={axisDomains.y[0]}
                                y2={0}
                                fillOpacity={0.05}
                            >
                                <Label position="center" fontSize={10}>{quadrantLabels[3]}</Label>
                            </ReferenceArea>
                        )}
                    </>
                )}

                {/* Hiển thị đường hồi quy nếu có */}
                {showRegressionLine && regressionLine && (
                    <Scatter
                        name="Regression Line"
                        data={regressionLine}
                        line={{ stroke: '#ff7300', strokeWidth: 2 }}
                        legendType="none"
                    />
                )}

                {/* Hiển thị annotations nếu có */}
                {config?.annotations?.map((anno, index) => {
                    if (anno.type === 'area' && anno.x1 !== undefined && anno.y1 !== undefined &&
                        anno.x2 !== undefined && anno.y2 !== undefined) {
                        return (
                            <ReferenceArea
                                key={index}
                                x1={anno.x1}
                                y1={anno.y1}
                                x2={anno.x2}
                                y2={anno.y2}
                                stroke={anno.color || "#f00"}
                                strokeOpacity={0.3}
                                fill={anno.color || "#f00"}
                                fillOpacity={0.1}
                            >
                                {anno.label && <Label position="center">{anno.label}</Label>}
                            </ReferenceArea>
                        );
                    }
                    return null;
                })}

                {/* Hiển thị scatter points */}
                <Scatter
                    name={`${xAxis.name || 'X'} vs ${yAxis.name || 'Y'}`}
                    data={displayData}
                    fill={colorBy ? undefined : "#1f77b4"}
                    shape={showDensity ? undefined : CustomDot}
                    isAnimationActive={false}
                />
            </ScatterChart>
        );
    }, [
        displayData,
        axisDomains,
        xAxis.name,
        yAxis.name,
        showDensity,
        CustomTooltip,
        CustomDot,
        handleMouseMove,
        colorBy,
        CustomLegend,
        showQuadrants,
        quadrantLabels,
        showRegressionLine,
        regressionLine,
        config?.annotations,
        markerSize
    ]);

    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
                <div className="flex items-center justify-between mt-1">
                    <div className="text-xs text-gray-500">
                        {displayData.length} điểm
                        {showDensity ? ' (dạng mật độ)' : ''}
                        {data.length > maxPoints && !showDensity ?
                            ` (đã lấy mẫu từ ${data.length} điểm)` : ''}
                    </div>
                    {data.length > 500 && (
                        <button
                            className="text-xs px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded transition-colors"
                            onClick={() => setShowDensity(!showDensity)}
                        >
                            {showDensity ? 'Hiển thị điểm' : 'Hiển thị mật độ'}
                        </button>
                    )}
                </div>
            </div>

            {/* Hiển thị tooltip ở bên ngoài biểu đồ khi hover */}
            {alwaysShowTooltip && hoveredData && (
                <div className="mt-2 bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    <p className="font-medium">{xAxis.name || 'X'}: {formatNumber(Number(hoveredData.x))}</p>
                    <p className="font-medium">{yAxis.name || 'Y'}: {formatNumber(Number(hoveredData.y))}</p>
                    {hoveredData.count && <p className="font-medium">Số điểm: {hoveredData.count}</p>}
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