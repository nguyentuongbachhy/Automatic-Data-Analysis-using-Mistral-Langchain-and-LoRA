import { useCallback, useMemo, useState } from 'react';
import {
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Scatter,
    ScatterChart,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';
import { formatNumber } from '../../utils/chart';

// Màu sắc cho biểu đồ
const COLOR_RANGE = [
    '#f7fbff', // Lightest blue - lower density
    '#deebf7',
    '#c6dbef',
    '#9ecae1',
    '#6baed6',
    '#4292c6',
    '#2171b5',
    '#08519c',
    '#08306b'  // Darkest blue - higher density
];

interface HexbinDataPoint {
    x: number;
    y: number;
    count: number;
    color: string;
    points: any[];
    hexPointsPath: string;
}

interface HexbinChartRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: {
        xAxis?: { name?: string; key?: string };
        yAxis?: { name?: string; key?: string };
        radius?: number;
        colorRange?: string[];
        showLabels?: boolean;
        showOriginalPoints?: boolean;
        showTooltip?: boolean;
        binCount?: number;
        margin?: { top: number; right: number; bottom: number; left: number };
    };
}

export default function HexbinChartRenderer({
    data,
    title,
    description,
    config = {}
}: HexbinChartRendererProps) {
    // State cho việc hover vào hexbin
    const [hoveredBin, setHoveredBin] = useState<HexbinDataPoint | null>(null);

    // Cấu hình mặc định
    const {
        xAxis = { name: 'X', key: 'x' },
        yAxis = { name: 'Y', key: 'y' },
        radius = 15,
        colorRange = COLOR_RANGE,
        showLabels = true,
        showOriginalPoints = false,
        showTooltip = true,
        binCount = 20,
        margin = { top: 20, right: 20, bottom: 40, left: 40 }
    } = config;

    // Xử lý và chuẩn bị dữ liệu
    const { processedData, hexbinData } = useMemo(() => {
        if (!data || data.length === 0) {
            return { processedData: [], hexbinData: [], dimensions: { xMin: 0, xMax: 1, yMin: 0, yMax: 1 } };
        }

        // Chuẩn hóa dữ liệu với tọa độ x, y
        const processedPoints = data.map(item => {
            const x = Number(xAxis.key ? item[xAxis.key] ?? 0 : (item.x || 0));
            const y = Number(yAxis.key ? item[yAxis.key] ?? 0 : (item.x || 0));

            return {
                ...item,
                x,
                y
            };
        }).filter(point => !isNaN(point.x) && !isNaN(point.y));

        // Tìm phạm vi dữ liệu
        const xValues = processedPoints.map(p => p.x);
        const yValues = processedPoints.map(p => p.y);

        const xMin = Math.min(...xValues);
        const xMax = Math.max(...xValues);
        const yMin = Math.min(...yValues);
        const yMax = Math.max(...yValues);

        // Tính toán khoảng cách giữa các bin
        const xRange = xMax - xMin;
        const yRange = yMax - yMin;

        const xStep = xRange / binCount;
        const yStep = yRange / binCount;

        // Tạo hexbin bins
        const hexbins: Map<string, { x: number; y: number; points: any[] }> = new Map();

        // Helper function tạo hex coordinates
        const hexPoints = (centerX: number, centerY: number, size: number) => {
            const points = [];
            for (let i = 0; i < 6; i++) {
                const angle = (Math.PI / 3) * i;
                const x = centerX + size * Math.cos(angle);
                const y = centerY + size * Math.sin(angle);
                points.push([x, y]);
            }
            return points;
        };

        // Helper function tạo path cho hexagon
        const hexPath = (points: number[][]) => {
            return `M${points.map(p => p.join(',')).join('L')}Z`;
        };

        // Thực hiện hexbin binning
        processedPoints.forEach(point => {
            // Xác định bin center gần nhất
            const xBin = Math.floor((point.x - xMin) / xStep);
            const yBin = Math.floor((point.y - yMin) / yStep);

            // Hexagonal grid offset cho hàng chẵn/lẻ
            const offset = yBin % 2 === 0 ? 0 : 0.5;

            // Bin center
            const centerX = xMin + (xBin + offset) * xStep + xStep / 2;
            const centerY = yMin + yBin * yStep + yStep / 2;

            // Bin key
            const key = `${xBin}-${yBin}`;

            // Thêm point vào bin tương ứng
            if (!hexbins.has(key)) {
                hexbins.set(key, {
                    x: centerX,
                    y: centerY,
                    points: []
                });
            }

            hexbins.get(key)!.points.push(point);
        });

        // Chuyển từ Map sang Array và chuẩn bị dữ liệu cho rendering
        const hexArray = Array.from(hexbins.values());

        // Tìm bin với nhiều điểm nhất để scale màu sắc
        const maxCount = Math.max(...hexArray.map(bin => bin.points.length));

        // Tạo dữ liệu hexbin hoàn chỉnh với màu sắc và đường path
        const hexbinPoints = hexArray.map(bin => {
            const count = bin.points.length;
            const normalizedCount = count / maxCount;

            // Chọn màu dựa trên mật độ điểm
            const colorIndex = Math.min(
                Math.floor(normalizedCount * colorRange.length),
                colorRange.length - 1
            );

            // Tạo polygon path cho hexagon
            const hexPointsArray = hexPoints(bin.x, bin.y, radius);
            const hexPointsPath = hexPath(hexPointsArray);

            return {
                x: bin.x,
                y: bin.y,
                count,
                color: colorRange[colorIndex],
                points: bin.points,
                hexPointsPath
            };
        });

        return {
            processedData: processedPoints,
            hexbinData: hexbinPoints,
            dimensions: { xMin, xMax, yMin, yMax }
        };
    }, [data, xAxis, yAxis, radius, colorRange, binCount]);

    // Custom shape component cho hexagon
    const HexShape = useCallback((props: any) => {
        const { cx, cy, payload } = props;

        return (
            <g
                transform={`translate(${cx - payload.x}, ${cy - payload.y})`}
                onMouseEnter={() => setHoveredBin(payload)}
                onMouseLeave={() => setHoveredBin(null)}
            >
                <path
                    d={payload.hexPointsPath}
                    fill={payload.color}
                    stroke="#fff"
                    strokeWidth={1}
                    fillOpacity={0.8}
                />
                {showLabels && payload.count > 0 && (
                    <text
                        x={payload.x}
                        y={payload.y}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="#000"
                        fontSize={10}
                        fontWeight="bold"
                    >
                        {payload.count}
                    </text>
                )}
            </g>
        );
    }, [showLabels]);

    // Custom component cho original data points (optional)
    const OriginalPoints = useCallback(() => {
        if (!showOriginalPoints || processedData.length === 0) return null;

        return (
            <Scatter
                data={processedData}
                fill="#000"
                fillOpacity={0.3}
                shape="circle"
                legendType="none"
            />
        );
    }, [showOriginalPoints, processedData]);

    // Custom tooltip
    const CustomTooltip = useCallback(({ active, payload }: any) => {
        if (active && payload && payload.length && payload[0].payload) {
            const data = payload[0].payload;

            return (
                <div className="bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    <p className="font-medium">Bin Center</p>
                    <p>X: {formatNumber(data.x)}</p>
                    <p>Y: {formatNumber(data.y)}</p>
                    <p className="font-medium mt-1">Points: {data.count}</p>
                </div>
            );
        }

        return null;
    }, []);

    // Legend showing density scale
    const CustomLegend = useCallback(() => {
        return (
            <div className="flex items-center justify-center mt-2">
                <div className="flex items-center text-xs">
                    <div className="h-3 w-20 mr-2 rounded" style={{
                        background: `linear-gradient(to right, ${colorRange.join(', ')})`
                    }} />
                    <span>Density</span>
                </div>
            </div>
        );
    }, [colorRange]);

    // Render hexbin chart
    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
                <div className="text-xs text-gray-500 mt-1">
                    {processedData.length} points in {hexbinData.length} hexbins
                </div>
            </div>

            <div className="h-full w-full">
                <ResponsiveContainer width="99%" height={title ? "92%" : "99%"}>
                    <ScatterChart margin={margin}>
                        <CartesianGrid strokeDasharray="3 3" />

                        <XAxis
                            type="number"
                            dataKey="x"
                            name={xAxis.name}
                            domain={['auto', 'auto']}
                            label={{
                                value: xAxis.name,
                                position: 'insideBottom',
                                offset: -10
                            }}
                        />

                        <YAxis
                            type="number"
                            dataKey="y"
                            name={yAxis.name}
                            domain={['auto', 'auto']}
                            label={{
                                value: yAxis.name,
                                angle: -90,
                                position: 'insideLeft'
                            }}
                        />

                        {showTooltip && (
                            <Tooltip
                                content={<CustomTooltip />}
                                cursor={{ fill: 'transparent' }}
                            />
                        )}

                        <Legend content={<CustomLegend />} />

                        {/* Original points (optional) */}
                        {showOriginalPoints && <OriginalPoints />}

                        {/* Hexbin points */}
                        <Scatter
                            name="Hexbin"
                            data={hexbinData}
                            shape={<HexShape />}
                        />
                    </ScatterChart>
                </ResponsiveContainer>
            </div>

            {/* Extra information for hovered bin */}
            {hoveredBin && showTooltip && (
                <div className="mt-2 text-xs">
                    <p>Selected bin: {hoveredBin.count} points</p>
                    <p>Center: ({formatNumber(hoveredBin.x)}, {formatNumber(hoveredBin.y)})</p>
                </div>
            )}
        </div>
    );
}