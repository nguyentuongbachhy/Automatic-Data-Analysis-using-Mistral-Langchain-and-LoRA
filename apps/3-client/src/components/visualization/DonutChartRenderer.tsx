import { useCallback, useMemo } from 'react';
import {
    Cell,
    Label,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip
} from 'recharts';
import { formatNumber } from '../../utils/chart';

// Màu sắc cho biểu đồ
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6'
];

interface DonutChartRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: {
        innerRadius?: number;
        outerRadius?: number;
        dataKey?: string;
        nameKey?: string;
        paddingAngle?: number;
        showTotal?: boolean;
        showPercentage?: boolean;
        labelOffset?: number;
        colorScheme?: string[];
        totalLabel?: string;
        legendPosition?: 'top' | 'bottom' | 'left' | 'right';
    };
}

export default function DonutChartRenderer({
    data,
    title,
    description,
    config = {}
}: DonutChartRendererProps) {
    // Xử lý dữ liệu cho biểu đồ hình tròn
    const chartData = useMemo(() => {
        if (!data || data.length === 0) return [];

        return data.map((item, index) => {
            const name = item.name || item.category || `Item ${index}`;
            const value = Number(item.value || 0);

            return {
                name,
                value,
                color: item.color || COLORS[index % COLORS.length]
            };
        });
    }, [data]);

    // Tính tổng giá trị
    const totalValue = useMemo(() => {
        return chartData.reduce((sum, item) => sum + item.value, 0);
    }, [chartData]);

    // Cấu hình mặc định
    const {
        innerRadius = 60,
        outerRadius = 90,
        dataKey = 'value',
        nameKey = 'name',
        paddingAngle = 2,
        showTotal = true,
        showPercentage = true,
        labelOffset = 20,
        colorScheme = COLORS,
        totalLabel = 'Tổng cộng',
        legendPosition = 'bottom'
    } = config;

    // Custom label hiển thị phần trăm
    const renderCustomizedLabel = useCallback(({ cx, cy, midAngle, outerRadius, percent }: any) => {
        if (!showPercentage) return null;

        const RADIAN = Math.PI / 180;
        const radius = outerRadius + labelOffset;
        const x = cx + radius * Math.cos(-midAngle * RADIAN);
        const y = cy + radius * Math.sin(-midAngle * RADIAN);

        return (
            <text
                x={x}
                y={y}
                fill="#000"
                textAnchor={x > cx ? 'start' : 'end'}
                dominantBaseline="central"
                fontSize={12}
            >
                {`${(percent * 100).toFixed(1)}%`}
            </text>
        );
    }, [showPercentage, labelOffset]);

    // Custom tooltip
    const CustomTooltip = useCallback(({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;

            return (
                <div className="bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    <p className="font-medium">{data.name}</p>
                    <p className="font-medium">Giá trị: {formatNumber(data.value)}</p>
                    <p className="font-medium">Tỷ lệ: {((data.value / totalValue) * 100).toFixed(1)}%</p>
                </div>
            );
        }

        return null;
    }, [totalValue]);

    // Legend tùy chỉnh
    const CustomLegend = useCallback(({ payload }: any) => {
        if (!payload || payload.length === 0) return null;

        return (
            <div className="flex flex-wrap justify-center gap-2 mt-2">
                {payload.map((entry: any, index: number) => (
                    <div key={index} className="flex items-center text-xs">
                        <div
                            className="w-3 h-3 rounded-full mr-1"
                            style={{ backgroundColor: entry.color }}
                        />
                        <span className="mr-1">{entry.value}</span>
                    </div>
                ))}
            </div>
        );
    }, []);

    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
            </div>

            <div className="h-full w-full">
                <ResponsiveContainer width="99%" height={title ? "92%" : "99%"}>
                    <PieChart>
                        <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={innerRadius}
                            outerRadius={outerRadius}
                            paddingAngle={paddingAngle}
                            dataKey={dataKey}
                            nameKey={nameKey}
                            label={renderCustomizedLabel}
                            labelLine={showPercentage}
                            isAnimationActive={true}
                        >
                            {chartData.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={entry.color || colorScheme[index % colorScheme.length]}
                                />
                            ))}
                            {showTotal && (
                                <Label
                                    content={({ viewBox }) => {
                                        const { cx, cy } = viewBox as any;
                                        return (
                                            <text
                                                x={cx}
                                                y={cy}
                                                textAnchor="middle"
                                                dominantBaseline="central"
                                                className="recharts-text recharts-label"
                                                fontSize="16"
                                                fontWeight="bold"
                                            >
                                                <tspan x={cx} dy="-0.5em">{totalLabel}</tspan>
                                                <tspan x={cx} dy="1.5em" fontSize="14">{formatNumber(totalValue)}</tspan>
                                            </text>
                                        );
                                    }}
                                    position="center"
                                />
                            )}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend
                            content={<CustomLegend />}
                            layout={legendPosition === 'left' || legendPosition === 'right' ? 'vertical' : 'horizontal'}
                            align="center"
                            verticalAlign={legendPosition === 'top' ? 'top' : 'bottom'}
                        />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}