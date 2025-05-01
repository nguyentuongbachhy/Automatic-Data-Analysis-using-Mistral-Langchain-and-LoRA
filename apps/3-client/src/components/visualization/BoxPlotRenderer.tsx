import { useCallback, useMemo } from 'react';
import {
    CartesianGrid,
    ComposedChart,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';
import { formatNumber } from '../../utils/chart';

interface BoxPlotRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: Record<string, any>;
}

export default function BoxPlotRenderer({
    data,
    title,
    config = {}
}: BoxPlotRendererProps) {
    // Màu sắc mặc định
    const boxFill = config?.boxFill || '#8ecae6';
    const boxStroke = config?.boxStroke || '#4361ee';
    const medianStroke = config?.medianStroke || '#f72585';
    const whiskerStroke = config?.whiskerStroke || '#023047';

    // Format dữ liệu
    const chartData = useMemo(() => {
        if (!data || data.length === 0) return [];
        return data;
    }, [data]);

    // Tính toán domain cho trục Y
    const yDomain = useMemo(() => {
        if (!chartData || chartData.length === 0) return [0, 10];

        let minValue = Number.MAX_SAFE_INTEGER;
        let maxValue = Number.MIN_SAFE_INTEGER;

        chartData.forEach(item => {
            if (item.min < minValue) minValue = item.min;
            if (item.max > maxValue) maxValue = item.max;
        });

        // Thêm khoảng trống để biểu đồ đẹp hơn
        const padding = (maxValue - minValue) * 0.1;
        return [minValue - padding, maxValue + padding];
    }, [chartData]);

    // Custom tooltip
    const CustomTooltip = useCallback(({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="bg-white p-3 border border-gray-200 shadow-md rounded-md text-sm max-w-xs">
                    <p className="font-medium text-gray-900 mb-1">{data.name}</p>
                    <div className="space-y-1 text-gray-700">
                        <p className="flex justify-between">
                            <span>Tối thiểu:</span>
                            <span className="font-medium ml-2">{formatNumber(data.min)}</span>
                        </p>
                        <p className="flex justify-between">
                            <span>Phân vị 25%:</span>
                            <span className="font-medium ml-2">{formatNumber(data.q1)}</span>
                        </p>
                        <p className="flex justify-between bg-blue-50 px-1 rounded">
                            <span>Trung vị:</span>
                            <span className="font-medium ml-2">{formatNumber(data.median)}</span>
                        </p>
                        <p className="flex justify-between">
                            <span>Phân vị 75%:</span>
                            <span className="font-medium ml-2">{formatNumber(data.q3)}</span>
                        </p>
                        <p className="flex justify-between">
                            <span>Tối đa:</span>
                            <span className="font-medium ml-2">{formatNumber(data.max)}</span>
                        </p>
                    </div>
                </div>
            );
        }
        return null;
    }, []);

    // Vẽ BoxPlot
    const CustomBoxPlot = useCallback((props: any) => {
        const { x, y, width, height, payload } = props;

        if (!payload) return null;

        // Chiều rộng của box
        const boxWidth = Math.min(width * 0.5, 40);
        const boxX = x + (width - boxWidth) / 2;

        // Tính toán tỷ lệ dựa vào domain
        const range = yDomain[1] - yDomain[0];
        const getY = (value: number) => {
            const ratio = (value - yDomain[0]) / range;
            return y + height - (ratio * height);
        };

        const minY = getY(payload.min);
        const q1Y = getY(payload.q1);
        const medianY = getY(payload.median);
        const q3Y = getY(payload.q3);
        const maxY = getY(payload.max);

        return (
            <g className="boxplot-box">
                {/* Hộp từ Q1 đến Q3 */}
                <rect
                    x={boxX}
                    y={q3Y}
                    width={boxWidth}
                    height={Math.max(1, q1Y - q3Y)}
                    fill={boxFill}
                    stroke={boxStroke}
                    strokeWidth={1.5}
                    rx={3}
                    ry={3}
                    className="boxplot-rect"
                />

                {/* Đường trung vị */}
                <line
                    x1={boxX}
                    y1={medianY}
                    x2={boxX + boxWidth}
                    y2={medianY}
                    stroke={medianStroke}
                    strokeWidth={2}
                    className="boxplot-median"
                />

                {/* Đường râu trên */}
                <line
                    x1={boxX + boxWidth / 2}
                    y1={q3Y}
                    x2={boxX + boxWidth / 2}
                    y2={maxY}
                    stroke={whiskerStroke}
                    strokeWidth={1.5}
                    className="boxplot-whisker"
                />

                {/* Đường râu dưới */}
                <line
                    x1={boxX + boxWidth / 2}
                    y1={q1Y}
                    x2={boxX + boxWidth / 2}
                    y2={minY}
                    stroke={whiskerStroke}
                    strokeWidth={1.5}
                    className="boxplot-whisker"
                />

                {/* Đầu râu trên */}
                <line
                    x1={boxX + boxWidth / 2 - 10}
                    y1={maxY}
                    x2={boxX + boxWidth / 2 + 10}
                    y2={maxY}
                    stroke={whiskerStroke}
                    strokeWidth={1.5}
                    className="boxplot-whisker-cap"
                />

                {/* Đầu râu dưới */}
                <line
                    x1={boxX + boxWidth / 2 - 10}
                    y1={minY}
                    x2={boxX + boxWidth / 2 + 10}
                    y2={minY}
                    stroke={whiskerStroke}
                    strokeWidth={1.5}
                    className="boxplot-whisker-cap"
                />

                {/* Vùng trong suốt để hover tốt hơn */}
                <rect
                    x={boxX - 10}
                    y={Math.min(minY, maxY, q1Y, q3Y) - 5}
                    width={boxWidth + 20}
                    height={Math.abs(maxY - minY) + 10}
                    fill="transparent"
                    className="boxplot-hover-area"
                />
            </g>
        );
    }, [yDomain, boxFill, boxStroke, medianStroke, whiskerStroke]);

    return (
        <div className="h-full w-full" role="figure" aria-label={title || "Box Plot"}>
            {title && (
                <div className="font-medium text-center mb-2" aria-hidden="true">{title}</div>
            )}

            <div className="h-full w-full overflow-visible">
                <ResponsiveContainer width="99%" height={title ? "92%" : "99%"} debounce={50}>
                    <ComposedChart
                        data={chartData}
                        margin={{ top: 10, right: 30, left: 20, bottom: 20 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" vertical={true} horizontal={true} />

                        <XAxis
                            dataKey="name"
                            tick={{ fontSize: 12 }}
                            axisLine={true}
                            tickLine={true}
                        />

                        <YAxis
                            domain={yDomain}
                            tick={{ fontSize: 12 }}
                            axisLine={true}
                            tickLine={true}
                        />

                        <Tooltip content={<CustomTooltip />} cursor={false} />

                        <Legend
                            wrapperStyle={{ fontSize: 12, paddingTop: 10 }}
                            payload={[
                                {
                                    value: 'Box Plot',
                                    type: 'square',
                                    color: boxFill
                                }
                            ]}
                        />

                        {/* BoxPlot custom renderer */}
                        {chartData.map((entry, index) => (
                            <CustomBoxPlot
                                key={`boxplot-${index}`}
                                x={(index * 100) / chartData.length} // Assuming 100 as a default width
                                width={100 / chartData.length} // Assuming 100 as a default width
                                height={200} // Assuming 200 as a default height
                                index={index}
                                payload={entry}
                            />
                        ))}
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}