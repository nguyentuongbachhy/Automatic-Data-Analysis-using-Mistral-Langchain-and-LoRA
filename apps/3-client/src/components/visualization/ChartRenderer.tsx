import { useCallback, useMemo, useState } from 'react';
import {
    Area,
    AreaChart,
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    ComposedChart,
    Legend,
    Line,
    LineChart,
    Pie,
    PieChart,
    PolarAngleAxis,
    PolarGrid,
    PolarRadiusAxis,
    Radar,
    RadarChart,
    Rectangle,
    ReferenceLine,
    ResponsiveContainer,
    Scatter,
    ScatterChart,
    Tooltip,
    Treemap,
    XAxis,
    YAxis
} from 'recharts';
import { VisualizationData } from '../../types';
import { ChartType } from '../../types/common';
import { formatNumber, getDisplayName } from '../../utils/chart';
import BoxPlotRenderer from './BoxPlotRenderer';
import BubbleRenderer from './BubbleRenderer';
import DivergingChartRenderer from './DivergingChartRenderer';
import DonutChartRenderer from './DonutChartRenderer';
import GanttChartRenderer from './GanttChartRenderer';
import HexbinChartRenderer from './HexbinChartRenderer';
import NetworkChartRenderer from './NetworkChartRenderer';
import SankeyRenderer from './SandkeyRenderer';
import ScatterRenderer from './ScatterChartRenderer';
import WordCloudRenderer from './WordCloudRenderer';


// Array of colors with high contrast suitable for various chart types
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6',
    '#ff595e', '#ffca3a', '#8ac926', '#1982c4', '#6a4c93'
];


// Default configuration for extended chart components
const DEFAULT_CHART_CONFIG = {
    margin: { top: 10, right: 20, left: 10, bottom: 20 },
    gridStroke: '#e0e0e0',
    gridStrokeDasharray: '3 3',
    animationDuration: 500,
    fontSize: {
        axis: 12,
        legend: 12,
        tooltip: 12
    },
    treemap: {
        aspectRatio: 4 / 3,
        colorScale: ['#4cc9f0', '#4361ee']
    },
    waterfall: {
        positiveColor: '#4cc9f0',
        negativeColor: '#f72585',
        totalColor: '#3a0ca3'
    },
    radar: {
        fillOpacity: 0.6,
        strokeWidth: 2
    },
    box: {
        fill: '#8ecae6',
        stroke: '#4361ee',
        whiskerStroke: '#023047',
        medianStroke: '#f72585'
    }
};


/**
 * Color interpolation function between two hex colors
 */
function interpolateColor(color1: string, color2: string, factor: number): string {
    const c1 = hexToRgb(color1);
    const c2 = hexToRgb(color2);
    if (!c1 || !c2) return color1;
    const result = {
        r: Math.round(c1.r + factor * (c2.r - c1.r)),
        g: Math.round(c1.g + factor * (c2.g - c1.g)),
        b: Math.round(c1.b + factor * (c2.b - c1.b))
    };
    return rgbToHex(result.r, result.g, result.b);
}

function hexToRgb(hex: string) {
    let cleanedHex = hex.replace('#', '');
    if (cleanedHex.length === 3) {
        cleanedHex = cleanedHex.split('').map(c => c + c).join('');
    }
    const bigint = parseInt(cleanedHex, 16);
    return {
        r: (bigint >> 16) & 255,
        g: (bigint >> 8) & 255,
        b: bigint & 255
    };
}

function rgbToHex(r: number, g: number, b: number): string {
    return '#' + [r, g, b]
        .map(x => {
            const hex = x.toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        })
        .join('');
}

/**
 * Function to generate color gradient for treemap and heatmap
 */
export function getColorScale(
    value: number,
    min: number,
    max: number,
    colorScale: string[] = ['#2166ac', '#f7fbff']
): string {
    // Ensure we don't divide by zero
    const range = max - min;
    const ratio = range === 0 ? 0.5 : (value - min) / range;

    // For two colors
    if (colorScale.length === 2) {
        return interpolateColor(colorScale[0], colorScale[1], ratio);
    }

    // For multiple colors
    if (colorScale.length > 2) {
        const segmentCount = colorScale.length - 1;
        const segmentSize = 1 / segmentCount;
        const segmentIndex = Math.min(Math.floor(ratio / segmentSize), segmentCount - 1);
        const segmentRatio = (ratio - segmentIndex * segmentSize) / segmentSize;
        return interpolateColor(colorScale[segmentIndex], colorScale[segmentIndex + 1], segmentRatio);
    }

    return colorScale[0] || '#4361ee';
}

/**
 * Function to return heatmap color based on value
 */
export function getHeatmapColor(
    value: number,
    min: number,
    max: number,
    colorScale?: string[]
): string {
    const colors = colorScale && colorScale.length >= 2
        ? colorScale
        : ['#2166ac', '#f7fbff'];
    return getColorScale(value, min, max, colors);
}

/**
 * Function to prepare waterfall data
 */
function prepareWaterfallData(data: any[], config: any = {}) {
    const sortedItems = [...data].sort((a, b) => {
        // Ensure "Total" is always at the end
        const aName = String(a.name || a.category || '').toLowerCase();
        const bName = String(b.name || b.category || '').toLowerCase();

        if (aName === 'total') return 1;
        if (bName === 'total') return -1;
        return 0;
    });

    let cumulativeSum = 0;
    const waterfallData = sortedItems.map((item, index) => {
        const name = item.name || item.category || `Item ${index}`;
        let value = Number(item.value || 0);
        const isTotal = name.toLowerCase() === 'total';

        // Determine the start and end points of the bar
        const start = isTotal ? 0 : cumulativeSum;
        const end = isTotal ? value : cumulativeSum + value;

        // Update cumulative sum (except for "Total")
        if (!isTotal) {
            cumulativeSum = end;
        }

        // Determine color based on value (increase/decrease)
        const fillColor = isTotal
            ? config.totalColor || DEFAULT_CHART_CONFIG.waterfall.totalColor
            : value >= 0
                ? config.positiveColor || DEFAULT_CHART_CONFIG.waterfall.positiveColor
                : config.negativeColor || DEFAULT_CHART_CONFIG.waterfall.negativeColor;

        return {
            name,
            value,
            start,
            end,
            fill: fillColor,
            isTotal
        };
    });

    return waterfallData;
}

/**
 * Function to process data for Grouped Histogram
 */
function prepareGroupedHistogramData(data: any[], dimension: string, measures: string[]) {
    // Create map to group data by dimension value
    const groupedData: Map<string, Record<string, number>> = new Map();

    // Iterate through each item in data
    data.forEach(item => {
        const key = String(item[dimension] || 'Unknown');
        if (!groupedData.has(key)) {
            groupedData.set(key, {});
        }

        // Add each measure value to corresponding group
        measures.forEach(measure => {
            const currentValue = groupedData.get(key)![measure] || 0;
            const newValue = Number(item[measure] || 0);
            groupedData.get(key)![measure] = currentValue + newValue;
        });
    });

    // Convert Map to Array
    return Array.from(groupedData).map(([key, values]) => ({
        name: key,
        ...values
    }));
}

/**
 * Type guard to check if the data follows ChartData format
 */
function isChartDataFormat(data: any): data is { values: any[], dimensions: string[], measures: string[] } {
    return data &&
        typeof data === 'object' &&
        Array.isArray(data.values) &&
        (Array.isArray(data.dimensions) || Array.isArray(data.measures));
}

interface ChartRendererProps {
    visualization: VisualizationData;
    alwaysShowTooltip?: boolean;
}

export default function ChartRenderer({
    visualization,
    alwaysShowTooltip = false
}: ChartRendererProps) {
    const { data, type, title, description, config = {} } = visualization;

    // Normalize chart type
    const normalizedType = useMemo(() => {
        const chartType = String(type).toLowerCase();

        // Map to ChartType enum values
        if (chartType.includes('bar') || chartType.includes('column')) {
            return ChartType.BAR;
        } else if (chartType.includes('line') || chartType.includes('trend')) {
            return ChartType.LINE;
        } else if (chartType.includes('pie') || chartType.includes('donut')) {
            return ChartType.PIE;
        } else if (chartType.includes('scatter')) {
            return ChartType.SCATTER;
        } else if (chartType.includes('bubble')) {
            return ChartType.BUBBLE;
        } else if (chartType.includes('area')) {
            return ChartType.AREA;
        } else if (chartType.includes('radar')) {
            return ChartType.RADAR;
        } else if (chartType.includes('heat')) {
            return ChartType.HEATMAP;
        } else if (chartType.includes('tree')) {
            return ChartType.TREEMAP;
        } else if (chartType.includes('water')) {
            return ChartType.WATERFALL;
        } else if (chartType.includes('box')) {
            return ChartType.BOX;
        } else if (chartType.includes('histogram') && !chartType.includes('grouped')) {
            return ChartType.HISTOGRAM;
        } else if (chartType.includes('grouped') && (chartType.includes('hist') || chartType.includes('bar'))) {
            return ChartType.GROUPED_HISTOGRAM;
        } else if (chartType.includes('combo') || chartType.includes('mixed')) {
            return ChartType.COMBO;
        } else if (chartType.includes('likert') && chartType.includes('correlation')) {
            return ChartType.LIKERT_CORRELATION;
        } else if (chartType.includes('likert')) {
            return ChartType.LIKERT;
        } else if (chartType.includes('word') && chartType.includes('cloud')) {
            return ChartType.WORD_CLOUD;
        } else if (chartType.includes('range')) {
            return ChartType.RANGE;
        } else if (chartType.includes('text')) {
            return ChartType.TEXT;
        } else if (chartType.includes('sankey')) {
            return ChartType.SANKEY;
        } else if (chartType.includes('donut')) {
            return ChartType.DONUT;
        }

        else if (chartType.includes('hexbin')) {
            return ChartType.HEXBIN;
        }

        else if (chartType.includes('diverging')) {
            return ChartType.DIVERGING;
        }
        else if (chartType.includes('gantt')) {
            return ChartType.GANTT;
        }
        else if (chartType.includes('network')) {
            return ChartType.NETWORK;
        }

        try {
            // Try to use as enum value
            return chartType as ChartType;
        } catch {
            // Default to bar if type is not recognized
            return ChartType.BAR;
        }
    }, [type]);

    // Handle specialized charts
    if (normalizedType === ChartType.SCATTER) {
        return (
            <ScatterRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.BUBBLE) {
        return (
            <BubbleRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.WORD_CLOUD) {
        return (
            <WordCloudRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.SANKEY) {
        return (
            <SankeyRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.DONUT) {
        return (
            <DonutChartRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.DIVERGING) {
        return (
            <DivergingChartRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.GANTT) {
        return (
            <GanttChartRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.HEXBIN) {
        return (
            <HexbinChartRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.NETWORK) {
        return (
            <NetworkChartRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    if (normalizedType === ChartType.BOX) {
        return (
            <BoxPlotRenderer
                data={Array.isArray(data) ? data : (data || [])}
                title={title}
                description={description}
                config={config}
            />
        );
    }

    // Process data and determine dimensions, measures
    const { formattedData, dimensions, measures } = useMemo(() => {
        if (!data || (Array.isArray(data) && data.length === 0)) {
            return { formattedData: [], dimensions: [], measures: [] };
        }

        // If data has ChartData format
        if (isChartDataFormat(data)) {
            return {
                formattedData: data.values || [],
                dimensions: data.dimensions || [],
                measures: data.measures || []
            };
        }

        const dataArray = Array.isArray(data) ? data : [];
        if (dataArray.length === 0) {
            return { formattedData: [], dimensions: [], measures: [] };
        }

        let dims: string[] = [];
        let meas: string[] = [];

        // Determine dimensions and measures from config
        if (config?.dimensions || config?.measures) {
            dims = Array.isArray(config.dimensions) ? config.dimensions :
                config.dimensions ? [config.dimensions] : [];
            meas = Array.isArray(config.measures) ? config.measures :
                config.measures ? [config.measures] : [];
        } else if (config?.xAxis?.key && config?.yAxis?.key) {
            dims = [config.xAxis.key];
            meas = [config.yAxis.key];
        }
        // Case for heatmap with x, y, value structure
        else if (normalizedType === ChartType.HEATMAP && 'x' in dataArray[0] && 'y' in dataArray[0] && 'value' in dataArray[0]) {
            dims = [];
            meas = ['x', 'y', 'value'];
        }
        // Auto-detect dimensions and measures
        else {
            const firstItem = dataArray[0];
            if (!firstItem || typeof firstItem !== 'object') {
                return { formattedData: [], dimensions: [], measures: [] };
            }

            const allKeys = Object.keys(firstItem);

            // Detect dimensions based on data type and field name
            dims = allKeys.filter(key => {
                const value = firstItem[key];
                return typeof value === 'string' ||
                    key.toLowerCase().includes('date') ||
                    key.toLowerCase().includes('category') ||
                    key.toLowerCase().includes('name') ||
                    key.toLowerCase() === 'id';
            });

            // Detect measures based on data type and field name
            meas = allKeys.filter(key => {
                const value = firstItem[key];
                return typeof value === 'number' ||
                    key.toLowerCase().includes('value') ||
                    key.toLowerCase().includes('count') ||
                    key.toLowerCase().includes('amount') ||
                    key.toLowerCase().includes('total');
            });

            // Ensure at least 1 dimension and 1 measure
            if (dims.length === 0 && allKeys.length > 0) dims = [allKeys[0]];
            if (meas.length === 0 && allKeys.length > 1) meas = [allKeys.filter(k => k !== dims[0])[0]];
        }

        let processedData = dataArray;

        // Process data based on chart type
        switch (normalizedType) {
            case ChartType.HEATMAP: {
                let minValue = Infinity;
                let maxValue = -Infinity;

                // Process heatmap data
                processedData = dataArray.map(item => {
                    if (!item) return { x: '', y: '', value: 0 };
                    let x, y, value;

                    if ('x' in item && 'y' in item && 'value' in item) {
                        x = item.x;
                        y = item.y;
                        value = item.value !== null ? Number(item.value) : 0;
                    } else if (dims.length >= 2 && meas.length >= 1) {
                        x = item[dims[0]];
                        y = item[dims[1]];
                        value = item[meas[0]] !== null ? Number(item[meas[0]]) : 0;
                    } else if (meas.length >= 3) {
                        x = Number(item[meas[0]]) || 0;
                        y = Number(item[meas[1]]) || 0;
                        value = item[meas[2]] !== null ? Number(item[meas[2]]) : 0;
                    } else {
                        return item;
                    }

                    // Update min/max
                    minValue = Math.min(minValue, value);
                    maxValue = Math.max(maxValue, value);
                    return { x, y, value };
                });

                // Handle correlation data
                if (config?.isCorrelation) {
                    minValue = -1;
                    maxValue = 1;
                } else if (minValue === Infinity || maxValue === -Infinity) {
                    minValue = -1;
                    maxValue = 1;
                }

                // Apply colors to heatmap
                processedData = processedData.map(item => ({
                    ...item,
                    fill: getHeatmapColor(item.value, minValue, maxValue, config?.colorScale)
                }));
                break;
            }

            case ChartType.TREEMAP: {
                // Process treemap data
                let minValue = Infinity;
                let maxValue = -Infinity;

                processedData = dataArray.map(item => {
                    const name = item.name || item[dims[0]] || '';
                    const value = Number(item.value || item[meas[0]]) || 0;
                    minValue = Math.min(minValue, value);
                    maxValue = Math.max(maxValue, value);

                    return { name, value };
                });

                // Add color property
                processedData = processedData.map(item => ({
                    ...item,
                    fill: getColorScale(
                        item.value,
                        minValue,
                        maxValue,
                        config?.colorScale || DEFAULT_CHART_CONFIG.treemap.colorScale
                    )
                }));
                break;
            }

            case ChartType.WATERFALL: {
                // Process waterfall data
                processedData = prepareWaterfallData(dataArray, {
                    positiveColor: config?.positiveColor || DEFAULT_CHART_CONFIG.waterfall.positiveColor,
                    negativeColor: config?.negativeColor || DEFAULT_CHART_CONFIG.waterfall.negativeColor,
                    totalColor: config?.totalColor || DEFAULT_CHART_CONFIG.waterfall.totalColor
                });
                break;
            }

            case ChartType.GROUPED_HISTOGRAM: {
                // Process grouped histogram data
                const dimensionToUse = dims.length > 0 ? dims[0] : Object.keys(dataArray[0])[0];
                processedData = prepareGroupedHistogramData(dataArray, dimensionToUse, meas);
                break;
            }

            case ChartType.PIE: {
                // Process pie chart data
                processedData = dataArray.map((item, index) => {
                    if (!item) return { name: `Item ${index}`, value: 0 };
                    const name = item.name || item[dims[0]] || `Item ${index}`;
                    const value = Number(item.value || item[meas[0]]) || 0;
                    return {
                        name,
                        value,
                        color: item.color || COLORS[index % COLORS.length]
                    };
                });
                break;
            }

            default: {
                // General processing for other chart types
                processedData = dataArray.map(item => {
                    if (!item) return {};
                    const result: any = { ...item };

                    // Ensure measures are numbers
                    meas.forEach(measure => {
                        if (measure in item) {
                            result[measure] = Number(item[measure]) || 0;
                        }
                    });
                    return result;
                });
                break;
            }
        }

        return { formattedData: processedData, dimensions: dims, measures: meas };
    }, [data, config, normalizedType]);

    // Transform data for each chart type
    const chartData = useMemo(() => {
        if (!formattedData || formattedData.length === 0) return [];

        switch (normalizedType) {
            case ChartType.PIE:
                return formattedData.map((item, index) => {
                    const name = item.name || item[dimensions[0]] || `Item ${index}`;
                    const value = Number(item.value || item[measures[0]]) || 0;
                    return {
                        name,
                        value,
                        color: item.color || COLORS[index % COLORS.length]
                    };
                });

            case ChartType.TREEMAP:
                return formattedData;

            case ChartType.WATERFALL:
                return formattedData;

            case ChartType.RADAR:
                return formattedData.map(item => {
                    const result = { ...item };
                    measures.forEach(measure => {
                        result[measure] = Number(item[measure]) || 0;
                    });
                    return result;
                });

            case ChartType.HISTOGRAM:
            case ChartType.GROUPED_HISTOGRAM:
            case ChartType.BAR:
            case ChartType.LINE:
            case ChartType.AREA:
            case ChartType.COMBO:
                return formattedData.map(item => {
                    const result = { ...item };

                    if (item.midpoint !== undefined) {
                        const midpointValue = Number(item.midpoint) || 0;
                        result.midpoint_display = formatNumber(midpointValue);
                        result.midpoint = midpointValue;
                    }

                    measures.forEach(measure => {
                        result[measure] = Number(item[measure]) || 0;
                    });

                    return result;
                });

            default:
                return formattedData.map(item => {
                    const result = { ...item };
                    measures.forEach(measure => {
                        result[measure] = Number(item[measure]) || 0;
                    });
                    return result;
                });
        }
    }, [formattedData, normalizedType, dimensions, measures]);

    // State for storing hover point (used for alwaysShowTooltip)
    const [hoveredData, setHoveredData] = useState<any>(null);

    // Configuration for Cartesian charts
    const cartesianConfig = {
        margin: config?.margin || DEFAULT_CHART_CONFIG.margin,
        xAxisConfig: {
            dataKey: dimensions[0] || undefined,
            fontSize: DEFAULT_CHART_CONFIG.fontSize.axis,
            tickMargin: 5,
            axisLine: true,
            tickLine: true,
            angle: config?.xAxisRotation || 0,
            interval: config?.xAxisInterval || 0
        },
        yAxisConfig: {
            fontSize: DEFAULT_CHART_CONFIG.fontSize.axis,
            tickMargin: 10,
            axisLine: true,
            tickLine: true,
            tickFormatter: config?.yAxisFormat ? (value: any) => config.yAxisFormat(value) : undefined
        },
        grid: {
            vertical: true,
            horizontal: true,
            strokeDasharray: DEFAULT_CHART_CONFIG.gridStrokeDasharray,
            stroke: DEFAULT_CHART_CONFIG.gridStroke
        }
    };

    // Custom tooltip
    const CustomTooltip = useCallback(({ active, payload, label }: any) => {
        const display = active || alwaysShowTooltip;

        if (display && payload && payload.length) {
            return (
                <div className="bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    {normalizedType === ChartType.HEATMAP ? (
                        <>
                            <p className="font-medium">X: {payload[0]?.payload?.x}</p>
                            <p className="font-medium">Y: {payload[0]?.payload?.y}</p>
                            <p className="font-medium">
                                Value: {formatNumber(payload[0]?.payload?.value)}
                            </p>
                        </>
                    ) : normalizedType === ChartType.TREEMAP ? (
                        <>
                            <p className="text-gray-200 font-medium mb-1">
                                {payload[0]?.payload?.name}
                            </p>
                            <p className="font-medium">
                                Value: {formatNumber(payload[0]?.payload?.value)}
                            </p>
                        </>
                    ) : normalizedType === ChartType.WATERFALL ? (
                        <>
                            <p className="text-gray-200 font-medium mb-1">
                                {payload[0]?.payload?.name}
                            </p>
                            <p className="font-medium">
                                Value: {formatNumber(payload[0]?.payload?.value)}
                            </p>
                            <p className="font-medium">
                                Start: {formatNumber(payload[0]?.payload?.start)}
                            </p>
                            <p className="font-medium">
                                End: {formatNumber(payload[0]?.payload?.end)}
                            </p>
                        </>
                    ) : (
                        <>
                            {dimensions.length > 0 && label !== undefined && (
                                <p className="text-gray-200 font-medium mb-1">
                                    {getDisplayName(dimensions[0])}: {label}
                                </p>
                            )}
                            {payload.map((item: any, index: number) => {
                                if (!item || !item.name) return null;

                                let displayValue = item.value;
                                if (typeof item.value === 'number') {
                                    const name = item.name.toLowerCase();
                                    if (
                                        name.includes('midpoint') ||
                                        name.includes('average') ||
                                        name.includes('mean') ||
                                        name.includes('median')
                                    ) {
                                        displayValue = formatNumber(item.value);
                                    } else if (
                                        name.includes('percent') ||
                                        name.includes('rate')
                                    ) {
                                        displayValue = `${formatNumber(item.value)}%`;
                                    } else {
                                        displayValue = formatNumber(item.value);
                                    }
                                }

                                return (
                                    <p key={index} className="flex items-center gap-2">
                                        <span
                                            className="inline-block w-3 h-3 rounded-full"
                                            style={{ backgroundColor: item.color }}
                                        />
                                        <span className="font-medium">{item.name}:</span>
                                        <span>{displayValue}</span>
                                    </p>
                                );
                            })}
                        </>
                    )}
                </div>
            );
        }
        return null;
    }, [dimensions, alwaysShowTooltip, normalizedType]);

    // Custom cell for heatmap
    const HeatmapCell = useCallback((props: any) => {
        const { x, y, width, height, fill } = props;
        return <Rectangle x={x} y={y} width={width} height={height} fill={fill} />;
    }, []);

    // Handle mouse move event
    const handleMouseMove = useCallback((state: any) => {
        if (alwaysShowTooltip && state && state.activePayload && state.activePayload.length) {
            setHoveredData(state.activePayload[0].payload);
        }
    }, [alwaysShowTooltip]);

    // Custom content for treemap
    const TreemapCustomContent = useCallback((props: any) => {
        const { depth, x, y, width, height, payload, colors, name, value } = props;

        return (
            <g>
                <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    style={{
                        fill: depth < 2 ? payload.fill || colors[Math.floor(Math.random() * 6)] : 'none',
                        stroke: '#fff',
                        strokeWidth: 2 / (depth + 1e-10),
                        strokeOpacity: 1 / (depth + 1e-10),
                    }}
                />
                {width > 50 && height > 30 && (
                    <text
                        x={x + width / 2}
                        y={y + height / 2}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fontSize={Math.min(14, width / 10)}
                        fill="#fff"
                    >
                        {name}
                    </text>
                )}
                {width > 80 && height > 50 && (
                    <text
                        x={x + width / 2}
                        y={y + height / 2 + 14}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fontSize={Math.min(12, width / 12)}
                        fill="#fff"
                    >
                        {formatNumber(value)}
                    </text>
                )}
            </g>
        );
    }, []);

    // Renderer for chart elements (bar, line, area, etc.)
    const renderElements = useMemo(() => {
        if (!chartData || chartData.length === 0) return null;

        switch (normalizedType) {
            case ChartType.HISTOGRAM:
            case ChartType.GROUPED_HISTOGRAM:
            case ChartType.BAR:
                return measures.map((measure, index) => (
                    <Bar
                        key={measure}
                        dataKey={measure}
                        fill={COLORS[index % COLORS.length]}
                        name={getDisplayName(measure)}
                        animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                        isAnimationActive={true}
                    />
                ));

            case ChartType.LINE:
                return measures.map((measure, index) => (
                    <Line
                        key={measure}
                        type="monotone"
                        dataKey={measure}
                        stroke={COLORS[index % COLORS.length]}
                        name={getDisplayName(measure)}
                        dot={{ r: 3, strokeWidth: 1 }}
                        activeDot={{ r: 5, strokeWidth: 1 }}
                        strokeWidth={2}
                        animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                        isAnimationActive={true}
                    />
                ));

            case ChartType.AREA:
                return measures.map((measure, index) => (
                    <Area
                        key={measure}
                        type="monotone"
                        dataKey={measure}
                        fill={COLORS[index % COLORS.length]}
                        stroke={COLORS[index % COLORS.length]}
                        name={getDisplayName(measure)}
                        fillOpacity={0.4}
                        strokeWidth={2}
                        animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                        isAnimationActive={true}
                    />
                ));

            case ChartType.COMBO:
                return measures.map((measure, index) => {
                    // Divide measures into bar, line, and area based on config or order
                    const chartStyle = config?.seriesConfig?.[measure]?.style ||
                        ((index === 0 && measures.length > 1) ? 'bar' :
                            (index === 1 && measures.length > 2) ? 'line' : 'area');

                    switch (chartStyle) {
                        case 'bar':
                            return (
                                <Bar
                                    key={measure}
                                    dataKey={measure}
                                    fill={COLORS[index % COLORS.length]}
                                    name={getDisplayName(measure)}
                                    animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                                    isAnimationActive={true}
                                />
                            );
                        case 'line':
                            return (
                                <Line
                                    key={measure}
                                    type="monotone"
                                    dataKey={measure}
                                    stroke={COLORS[index % COLORS.length]}
                                    name={getDisplayName(measure)}
                                    dot={{ r: 3, strokeWidth: 1 }}
                                    activeDot={{ r: 5, strokeWidth: 1 }}
                                    strokeWidth={2}
                                    animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                                    isAnimationActive={true}
                                />
                            );
                        case 'area':
                        default:
                            return (
                                <Area
                                    key={measure}
                                    type="monotone"
                                    dataKey={measure}
                                    fill={COLORS[index % COLORS.length]}
                                    stroke={COLORS[index % COLORS.length]}
                                    name={getDisplayName(measure)}
                                    fillOpacity={0.4}
                                    strokeWidth={2}
                                    animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                                    isAnimationActive={true}
                                />
                            );
                    }
                });

            case ChartType.HEATMAP:
                return <Scatter data={formattedData} shape={<HeatmapCell />} />;

            case ChartType.RADAR:
                return measures.map((measure, index) => (
                    <Radar
                        key={measure}
                        dataKey={measure}
                        name={getDisplayName(measure)}
                        stroke={COLORS[index % COLORS.length]}
                        fill={COLORS[index % COLORS.length]}
                        fillOpacity={DEFAULT_CHART_CONFIG.radar.fillOpacity}
                        isAnimationActive={true}
                        animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                    />
                ));

            case ChartType.WATERFALL:
                return (
                    <Bar
                        dataKey="value"
                        fill="url(#pattern)"
                        shape={(props: any) => {
                            const { x, y, width, height, fill } = props;
                            return <Rectangle x={x} y={y} width={width} height={height} fill={fill} />;
                        }}
                    />
                );

            case ChartType.PIE:
                return (
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        outerRadius="70%"
                        innerRadius={config?.innerRadius || (normalizedType === ChartType.PIE ? 0 : '40%')}
                        dataKey="value"
                        nameKey="name"
                        label={({ name, percent }) =>
                            `${name}: ${(percent * 100).toFixed(1)}%`
                        }
                        labelLine={true}
                        animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                        isAnimationActive={true}
                    >
                        {chartData.map((entry, index) => (
                            <Cell
                                key={`cell-${index}`}
                                fill={entry.color || COLORS[index % COLORS.length]}
                            />
                        ))}
                    </Pie>
                );

            default:
                return null;
        }
    }, [chartData, normalizedType, measures, formattedData, HeatmapCell, config]);

    // Format tooltip value
    const formatTooltipValue = useCallback((value: any, name: string) => {
        if (typeof value === 'number') {
            if (
                name.toLowerCase().includes('midpoint') ||
                name.toLowerCase().includes('average') ||
                name.toLowerCase().includes('mean') ||
                name.toLowerCase().includes('median')
            ) {
                return [formatNumber(value), getDisplayName(name)];
            }
            if (
                name.toLowerCase().includes('percent') ||
                name.toLowerCase().includes('rate')
            ) {
                return [`${formatNumber(value)}%`, getDisplayName(name)];
            }
            if (
                name.toLowerCase().includes('price') ||
                name.toLowerCase().includes('cost') ||
                name.toLowerCase().includes('revenue') ||
                name.toLowerCase().includes('sales')
            ) {
                return [formatNumber(value), getDisplayName(name)];
            }
            return [formatNumber(value), getDisplayName(name)];
        }
        return [value, getDisplayName(name)];
    }, []);

    // Render appropriate chart based on type
    const renderChart = useMemo(() => {
        if (!chartData || chartData.length === 0) {
            return (
                <div className="h-full flex items-center justify-center flex-col text-muted-foreground">
                    <div className="text-xl mb-2">No Data</div>
                    <div className="text-sm">{description || "No data available for this chart"}</div>
                </div>
            );
        }

        switch (normalizedType) {
            case ChartType.BAR:
            case ChartType.GROUPED_HISTOGRAM:
                return (
                    <BarChart data={chartData} margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            dataKey={cartesianConfig.xAxisConfig.dataKey}
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={cartesianConfig.xAxisConfig.interval}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            labelFormatter={(label) => `${getDisplayName(dimensions[0])}: ${label}`}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'rgba(0,0,0,0.1)' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            iconType="circle"
                            align="center"
                        />
                        {renderElements}
                    </BarChart>
                );

            case ChartType.LINE:
                return (
                    <LineChart data={chartData} margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            dataKey={cartesianConfig.xAxisConfig.dataKey}
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={cartesianConfig.xAxisConfig.interval}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            content={<CustomTooltip />}
                            cursor={{ stroke: 'rgba(0,0,0,0.2)', strokeWidth: 1, strokeDasharray: '3 3' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            iconType="line"
                            align="center"
                        />
                        {renderElements}
                    </LineChart>
                );

            case ChartType.AREA:
                return (
                    <AreaChart data={chartData} margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            dataKey={cartesianConfig.xAxisConfig.dataKey}
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={cartesianConfig.xAxisConfig.interval}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            content={<CustomTooltip />}
                            cursor={{ stroke: 'rgba(0,0,0,0.2)', strokeWidth: 1, strokeDasharray: '3 3' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            iconType="square"
                            align="center"
                        />
                        {renderElements}
                    </AreaChart>
                );

            case ChartType.COMBO:
                return (
                    <ComposedChart data={chartData} margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            dataKey={cartesianConfig.xAxisConfig.dataKey}
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={cartesianConfig.xAxisConfig.interval}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'rgba(0,0,0,0.1)' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            align="center"
                        />
                        {renderElements}
                    </ComposedChart>
                );

            case ChartType.HEATMAP:
                return (
                    <ScatterChart margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} horizontal={false} />
                        <XAxis
                            type="category"
                            dataKey="x"
                            name={config?.xAxis?.name || "Variables"}
                            allowDuplicatedCategory={false}
                            tick={{ fontSize: cartesianConfig.xAxisConfig.fontSize }}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            type="category"
                            dataKey="y"
                            name={config?.yAxis?.name || "Variables"}
                            allowDuplicatedCategory={false}
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'transparent' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            iconType="square"
                            align="center"
                        />
                        {renderElements}
                    </ScatterChart>
                );

            case ChartType.HISTOGRAM:
                return (
                    <BarChart data={chartData} margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            dataKey="bin"
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={0}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'rgba(0,0,0,0.1)' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            iconType="circle"
                            align="center"
                        />
                        {config?.showMean && config?.meanValue && (
                            <ReferenceLine
                                y={config.meanValue}
                                stroke="#ff7300"
                                strokeDasharray="3 3"
                                label={{
                                    value: `Mean: ${formatNumber(config.meanValue)}`,
                                    position: 'insideBottomRight',
                                    fontSize: 12
                                }}
                            />
                        )}
                        {config?.showMedian && config?.medianValue && (
                            <ReferenceLine
                                y={config.medianValue}
                                stroke="#4caf50"
                                strokeDasharray="3 3"
                                label={{
                                    value: `Median: ${formatNumber(config.medianValue)}`,
                                    position: 'insideTopRight',
                                    fontSize: 12
                                }}
                            />
                        )}
                        <Bar
                            dataKey="frequency"
                            fill={COLORS[0]}
                            name="Frequency"
                            isAnimationActive={true}
                        />
                    </BarChart>
                );

            case ChartType.LIKERT:
                return (
                    <BarChart
                        data={chartData}
                        layout="horizontal"
                        margin={cartesianConfig.margin}
                        onMouseMove={handleMouseMove}
                    >
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            type="number"
                            tick={{ fontSize: cartesianConfig.xAxisConfig.fontSize }}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                            tickFormatter={value => `${value}%`}
                        />
                        <YAxis
                            type="category"
                            dataKey="value"
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            width={120}
                        />
                        <Tooltip
                            formatter={(value, name) => [`${value}%`, name]}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'rgba(0,0,0,0.1)' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            iconType="circle"
                            align="center"
                        />
                        <Bar
                            dataKey="percentage"
                            fill={COLORS[0]}
                            name="Percentage"
                            isAnimationActive={true}
                            label={{
                                position: 'right',
                                formatter: (value: number) => `${value}%`,
                                fontSize: 12
                            }}
                        >
                            {chartData.map((_, index: number) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={COLORS[index % COLORS.length]}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                );

            case ChartType.TEXT:
                return (
                    <BarChart data={chartData} margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            dataKey="bin"
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={0}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                            label={{ value: "Text Length", position: "insideBottom", offset: -5 }}
                        />
                        <YAxis
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                            label={{ value: "Frequency", angle: -90, position: "insideLeft" }}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'rgba(0,0,0,0.1)' }}
                        />
                        <Bar
                            dataKey="frequency"
                            fill="#8884d8"
                            name="Frequency"
                            isAnimationActive={true}
                        />
                        {config?.meanValue && (
                            <ReferenceLine
                                x={config.meanValue}
                                stroke="#ff7300"
                                strokeDasharray="3 3"
                                label={{ value: `Avg Length: ${formatNumber(config.meanValue)}`, position: 'top' }}
                            />
                        )}
                    </BarChart>
                );

            case ChartType.RANGE:
                return (
                    <BarChart data={chartData} margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            dataKey="category"
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={0}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                        />
                        <Tooltip
                            formatter={formatTooltipValue}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'rgba(0,0,0,0.1)' }}
                        />
                        <Bar
                            dataKey="value"
                            fill="#8884d8"
                            name="Count"
                            isAnimationActive={true}
                        >
                            {chartData.map((_, index: number) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={COLORS[index % COLORS.length]}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                );

            case ChartType.LIKERT_CORRELATION:
                return (
                    <ScatterChart margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} horizontal={false} />
                        <XAxis
                            type="category"
                            dataKey="x"
                            name={config?.xAxis?.name || "Likert Scales"}
                            allowDuplicatedCategory={false}
                            tick={{ fontSize: cartesianConfig.xAxisConfig.fontSize }}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            type="category"
                            dataKey="y"
                            name={config?.yAxis?.name || "Likert Scales"}
                            allowDuplicatedCategory={false}
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                        />
                        <Tooltip
                            formatter={(value: number | string, name: string) => {
                                if (typeof value === 'number') {
                                    return [
                                        value > 0
                                            ? `+${value.toFixed(2)} (Positive correlation)`
                                            : `${value.toFixed(2)} (Negative correlation)`,
                                        name
                                    ];
                                }
                                return [value, name];
                            }}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'transparent' }}
                        />
                        <Scatter
                            data={chartData}
                            shape={<Rectangle />}
                            fill="#8884d8"
                            name="Correlation"
                        />
                    </ScatterChart>
                );

            case ChartType.PIE:
                return (
                    <PieChart margin={cartesianConfig.margin} onMouseMove={handleMouseMove}>
                        <Tooltip
                            formatter={(value, name) => [formatNumber(Number(value)), name]}
                            content={<CustomTooltip />}
                            cursor={{ fill: 'transparent' }}
                        />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            layout="horizontal"
                            align="center"
                            verticalAlign="bottom"
                        />
                        {renderElements}
                    </PieChart>
                );

            case ChartType.RADAR:
                return (
                    <RadarChart
                        cx="50%"
                        cy="50%"
                        outerRadius="80%"
                        data={chartData}
                        margin={cartesianConfig.margin}
                        onMouseMove={handleMouseMove}
                    >
                        <PolarGrid gridType={config?.gridType || "circle"} />
                        <PolarAngleAxis
                            dataKey={dimensions[0] || "name"}
                            tick={{
                                fontSize: DEFAULT_CHART_CONFIG.fontSize.axis,
                                fill: "#666"
                            }}
                        />
                        <PolarRadiusAxis
                            angle={config?.angleOffset || 90}
                            domain={config?.domain || ['auto', 'auto']}
                            tickCount={config?.tickCount || 5}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            align="center"
                        />
                        {renderElements}
                    </RadarChart>
                );

            case ChartType.TREEMAP:
                return (
                    <Treemap
                        data={chartData}
                        dataKey="value"
                        nameKey="name"
                        aspectRatio={config?.aspectRatio || DEFAULT_CHART_CONFIG.treemap.aspectRatio}
                        stroke="#fff"
                        fill="#8884d8"
                        content={<TreemapCustomContent />}
                        animationDuration={DEFAULT_CHART_CONFIG.animationDuration}
                        isAnimationActive={true}
                    >
                        <Tooltip content={<CustomTooltip />} />
                    </Treemap>
                );

            case ChartType.WATERFALL:
                return (
                    <BarChart
                        data={chartData}
                        margin={cartesianConfig.margin}
                        onMouseMove={handleMouseMove}
                        layout={config?.layout || "vertical"}
                    >
                        <CartesianGrid
                            strokeDasharray={cartesianConfig.grid.strokeDasharray}
                            stroke={cartesianConfig.grid.stroke}
                            vertical={cartesianConfig.grid.vertical}
                            horizontal={cartesianConfig.grid.horizontal}
                        />
                        <XAxis
                            type="category"
                            dataKey="name"
                            tick={{
                                fontSize: cartesianConfig.xAxisConfig.fontSize,
                                transform: `rotate(${cartesianConfig.xAxisConfig.angle})`
                            }}
                            interval={cartesianConfig.xAxisConfig.interval}
                            axisLine={cartesianConfig.xAxisConfig.axisLine}
                            tickLine={cartesianConfig.xAxisConfig.tickLine}
                            tickMargin={cartesianConfig.xAxisConfig.tickMargin}
                        />
                        <YAxis
                            type="number"
                            domain={[
                                (dataMin: number) => Math.min(0, dataMin),
                                (dataMax: number) => Math.max(dataMax * 1.1, 0)
                            ]}
                            tick={{ fontSize: cartesianConfig.yAxisConfig.fontSize }}
                            axisLine={cartesianConfig.yAxisConfig.axisLine}
                            tickLine={cartesianConfig.yAxisConfig.tickLine}
                            tickMargin={cartesianConfig.yAxisConfig.tickMargin}
                            tickFormatter={cartesianConfig.yAxisConfig.tickFormatter}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend
                            wrapperStyle={{ fontSize: DEFAULT_CHART_CONFIG.fontSize.legend, paddingTop: 10 }}
                            align="center"
                        />
                        <ReferenceLine y={0} stroke="#000" strokeDasharray="3 3" />
                        {renderElements}
                    </BarChart>
                );
            default:
                return (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                        Unsupported chart type: {normalizedType}
                    </div>
                );
        }
    }, [
        chartData, normalizedType, dimensions, measures, renderElements,
        formatTooltipValue, CustomTooltip, description, handleMouseMove,
        cartesianConfig, config, TreemapCustomContent
    ]);

    return (
        <div className="h-full w-full" role="figure" aria-label={title || "Chart"}>
            {title && (
                <div className="font-medium text-center mb-2" aria-hidden="true">{title}</div>
            )}
            <div className="h-full w-full overflow-visible" aria-hidden="true">
                <ResponsiveContainer width="99%" height={title ? "92%" : "99%"} debounce={50}>
                    {renderChart}
                </ResponsiveContainer>
            </div>
            {/* If alwaysShowTooltip = true and there's hoveredData, display tooltip outside the chart */}
            {alwaysShowTooltip && hoveredData && (
                <div className="mt-2 bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    {dimensions[0] && hoveredData[dimensions[0]] && (
                        <p className="font-medium">
                            {getDisplayName(dimensions[0])}: {hoveredData[dimensions[0]]}
                        </p>
                    )}
                    {measures.map((m, i) => (
                        hoveredData[m] !== undefined && (
                            <p key={i}>
                                {getDisplayName(m)}: {formatNumber(hoveredData[m])}
                            </p>
                        )
                    ))}
                </div>
            )}
            {/* Information for screen readers */}
            <div className="sr-only">
                {title && <h2>{title}</h2>}
                {description && <p>{description}</p>}
                <p>Chart type: {normalizedType} with {chartData.length} data points</p>
                {dimensions.length > 0 && (
                    <p>Dimensions: {dimensions.map(getDisplayName).join(', ')}</p>
                )}
                {measures.length > 0 && (
                    <p>Measures: {measures.map(getDisplayName).join(', ')}</p>
                )}
            </div>
        </div>
    );
}