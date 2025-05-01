import { useCallback, useMemo, useState } from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';

// Màu sắc cho biểu đồ Gantt
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6'
];

// Status colors
const STATUS_COLORS = {
    'notStarted': '#cccccc',
    'inProgress': '#4cc9f0',
    'completed': '#4caf50',
    'delayed': '#f72585',
    'onHold': '#ffb703'
};

interface GanttTask {
    id: string | number;
    name: string;
    start: Date | string | number;
    end: Date | string | number;
    progress?: number;
    status?: string;
    dependencies?: string[];
    group?: string;
    color?: string;
    milestone?: boolean;
    duration?: number; // Added duration property
}

interface GanttChartRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: {
        timeFormat?: string;
        barHeight?: number;
        barPadding?: number;
        showProgress?: boolean;
        showDependencies?: boolean;
        showMilestones?: boolean;
        groupTasks?: boolean;
        today?: Date | string | number;
        startDate?: Date | string | number;
        endDate?: Date | string | number;
        dateTickFormat?: string;
        taskColors?: Record<string, string>;
        statusColors?: Record<string, string>;
        highlightCriticalPath?: boolean;
    };
}

export default function GanttChartRenderer({
    data,
    title,
    description,
    config = {}
}: GanttChartRendererProps) {
    // State for handling hover interaction
    const [_, setHoveredTask] = useState<string | number | null>(null);

    // Cấu hình mặc định
    const {
        barHeight = 20,
        barPadding = 5,
        showProgress = true,
        showDependencies = false,
        showMilestones = true,
        groupTasks = true,
        statusColors = STATUS_COLORS,
        taskColors = {},
    } = config;

    // Xử lý và chuẩn bị dữ liệu
    const {
        chartData,
        timeRange,
        taskGroups,
        dependencies
    } = useMemo(() => {
        if (!data || data.length === 0) {
            return { chartData: [], timeRange: [0, 100], taskGroups: [], dependencies: [] };
        }

        // Normalize dates
        const normalizeTasks = data.map((task) => {
            // Parse start and end dates if they are strings
            let startDate = task.start instanceof Date ? task.start : new Date(task.start);
            let endDate = task.end instanceof Date ? task.end : new Date(task.end);

            // Convert to timestamps
            const start = startDate.getTime();
            const end = endDate.getTime();

            return {
                ...task,
                id: task.id || `task-${Math.random().toString(36).substr(2, 9)}`,
                name: task.name || 'Unnamed Task',
                start,
                end,
                duration: end - start,
                progress: task.progress !== undefined ? task.progress : 0,
                status: task.status || 'notStarted',
                dependencies: task.dependencies || [],
                group: task.group || 'Default',
                color: task.color || null,
                milestone: !!task.milestone
            };
        });

        // Find min and max dates
        let minDate = Math.min(...normalizeTasks.map(t => t.start));
        let maxDate = Math.max(...normalizeTasks.map(t => t.end));

        // Add padding to the range
        const rangePadding = (maxDate - minDate) * 0.05;
        minDate -= rangePadding;
        maxDate += rangePadding;

        // Extract unique groups
        const groups = [...new Set(normalizeTasks.map(t => t.group))];

        // Collect dependencies
        const deps = [];
        for (const task of normalizeTasks) {
            if (task.dependencies && task.dependencies.length > 0) {
                for (const depId of task.dependencies) {
                    deps.push({
                        source: depId,
                        target: task.id
                    });
                }
            }
        }

        return {
            chartData: normalizeTasks,
            timeRange: [minDate, maxDate],
            taskGroups: groups,
            dependencies: deps
        };
    }, [data]);

    // Format date for display
    const formatDate = useCallback((timestamp: number) => {
        const date = new Date(timestamp);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }, []);

    // Xử lý khi hover vào một task
    const handleTaskHover = useCallback((taskId: string | number | null) => {
        setHoveredTask(taskId);
    }, []);

    // Color function based on task status and custom colors
    const getTaskColor = useCallback((task: GanttTask) => {
        // First check for explicit task color
        if (task.color) return task.color;

        // Check for color based on task ID in config
        if (taskColors[task.id]) return taskColors[task.id];

        // Color based on status
        if (task.status && statusColors[task.status as keyof typeof statusColors]) {
            return statusColors[task.status as keyof typeof statusColors];
        }

        // Color based on group
        if (task.group) {
            const groupIndex = taskGroups.indexOf(task.group);
            if (groupIndex >= 0) return COLORS[groupIndex % COLORS.length];
        }

        // Default color
        return COLORS[0];
    }, [taskColors, statusColors, taskGroups]);

    // Custom tooltip component
    const CustomTooltip = useCallback(({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const task = payload[0].payload;

            return (
                <div className="bg-neutral-700 p-2 border border-gray-500 shadow-md rounded-md text-sm text-white">
                    <p className="font-medium">{task.name}</p>
                    <p>Bắt đầu: {formatDate(task.start)}</p>
                    <p>Kết thúc: {formatDate(task.end)}</p>
                    {showProgress && (
                        <p>Tiến độ: {task.progress || 0}%</p>
                    )}
                    {task.status && (
                        <p>Trạng thái: {task.status}</p>
                    )}
                    {task.milestone && (
                        <p className="text-yellow-300">Cột mốc quan trọng</p>
                    )}
                    {task.group && (
                        <p>Nhóm: {task.group}</p>
                    )}
                </div>
            );
        }
        return null;
    }, [showProgress, formatDate]);

    // Custom task label
    const renderTaskLabel = useCallback(({ x, y, width, height, index }: any) => {
        const task = chartData[index];
        if (!task) return <g />;

        // For milestones, render a diamond shape instead of a bar
        if (task.milestone) {
            const centerX = x + width / 2;
            const centerY = y + height / 2;
            const size = Math.min(height, 20);

            return (
                <polygon
                    points={`${centerX},${centerY - size / 2} ${centerX + size / 2},${centerY} ${centerX},${centerY + size / 2} ${centerX - size / 2},${centerY}`}
                    fill={getTaskColor(task)}
                    stroke="#000"
                    strokeWidth="1"
                />
            );
        }

        // For regular tasks
        return (
            <g>
                {/* Main task bar */}
                <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={getTaskColor(task)}
                    stroke="#000"
                    strokeWidth="1"
                    rx={2}
                    ry={2}
                    onMouseEnter={() => handleTaskHover(task.id)}
                    onMouseLeave={() => handleTaskHover(null)}
                />

                {/* Progress overlay if enabled */}
                {showProgress && task.progress > 0 && (
                    <rect
                        x={x}
                        y={y}
                        width={width * (task.progress / 100)}
                        height={height}
                        fill="rgba(0,0,0,0.2)"
                        rx={2}
                        ry={2}
                    />
                )}

                {/* Task name */}
                <text
                    x={x + 5}
                    y={y + height / 2 + 4}
                    fill="#fff"
                    fontSize={10}
                    fontWeight="bold"
                    textAnchor="start"
                >
                    {width > 50 ? task.name : ''}
                </text>
            </g>
        );
    }, [chartData, getTaskColor, showProgress, handleTaskHover]);

    // Custom legend for task status
    const CustomLegend = useCallback(() => {
        // Get unique statuses
        const statuses = [...new Set(chartData.map(task => task.status))];

        return (
            <div className="flex flex-wrap justify-center gap-4 mt-2 text-sm">
                {statuses.map((status, index) => (
                    status && (
                        <div key={index} className="flex items-center">
                            <div
                                className="w-3 h-3 rounded-full mr-1"
                                style={{ backgroundColor: status && status in statusColors ? statusColors[status as keyof typeof statusColors] : COLORS[index % COLORS.length] }}
                            />
                            <span>{status}</span>
                        </div>
                    )
                ))}

                {showMilestones && chartData.some(task => task.milestone) && (
                    <div className="flex items-center">
                        <div className="mr-1">◆</div>
                        <span>Milestone</span>
                    </div>
                )}
            </div>
        );
    }, [chartData, statusColors, showMilestones]);

    // Prepare Gantt chart data for rendering
    const ganttChartData = useMemo(() => {
        if (groupTasks) {
            // When grouping by task group
            const grouped = chartData.reduce((acc: Record<string, GanttTask[]>, task) => {
                if (!acc[task.group]) {
                    acc[task.group] = [];
                }
                acc[task.group].push(task);
                return acc;
            }, {} as Record<string, GanttTask[]>);

            // Flatten and prepare for rendering
            const result: any[] = [];
            Object.entries(grouped).forEach(([group, tasks]) => {
                // Add a group header
                result.push({
                    id: `group-${group}`,
                    name: group,
                    isGroup: true,
                });

                // Add tasks in this group
                tasks.forEach((task: GanttTask) => {
                    result.push({
                        ...task,
                        // For bar chart rendering
                        startPos: task.start,
                        duration: task.duration,
                    });
                });
            });

            return result;
        }

        // No grouping, just prepare the data
        return chartData.map(task => ({
            ...task,
            startPos: task.start,
            duration: task.duration,
        }));
    }, [chartData, groupTasks]);

    // Custom formatter for x-axis (time)
    const formatTimeAxis = useCallback((value: number) => {
        return formatDate(value);
    }, [formatDate]);

    // Generate dependencies as SVG lines
    const renderDependencies = useCallback(() => {
        if (!showDependencies || dependencies.length === 0) return null;

        // Find task positions
        const taskPositions: Record<string | number, { id: string | number; start: number; end: number }> = {};
        chartData.forEach(task => {
            taskPositions[task.id] = {
                id: task.id,
                start: task.start,
                end: task.end
            };
        });

        return dependencies.map((dep, index) => {
            const sourceTask = taskPositions[dep.source];
            const targetTask = taskPositions[dep.target];

            if (!sourceTask || !targetTask) return null;

            // Very simplified - in a real implementation, you'd calculate this based on
            // actual rendered positions and use a path-finding algorithm
            return (
                <line
                    key={`dep-${index}`}
                    x1={sourceTask.end}
                    y1={index * 30 + 15}
                    x2={targetTask.start}
                    y2={(index + 1) * 30 + 15}
                    stroke="#999"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                    markerEnd="url(#arrowhead)"
                />
            );
        });
    }, [showDependencies, dependencies, chartData]);

    if (!chartData || chartData.length === 0) {
        return (
            <div className="h-full w-full flex items-center justify-center">
                <div className="text-gray-500">Không có dữ liệu cho biểu đồ Gantt</div>
            </div>
        );
    }

    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
            </div>

            <div className="h-full w-full">
                <ResponsiveContainer width="99%" height={title ? "92%" : "99%"}>
                    <BarChart
                        data={ganttChartData}
                        layout="vertical"
                        margin={{ top: 20, right: 30, left: 150, bottom: 20 }}
                        barSize={barHeight}
                        barGap={barPadding}
                    >
                        <defs>
                            <marker
                                id="arrowhead"
                                markerWidth="10"
                                markerHeight="7"
                                refX="0"
                                refY="3.5"
                                orient="auto"
                            >
                                <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
                            </marker>
                        </defs>

                        <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />

                        <XAxis
                            type="number"
                            domain={timeRange}
                            tickFormatter={formatTimeAxis}
                            tick={{ fontSize: 12 }}
                        />

                        <YAxis
                            type="category"
                            dataKey="name"
                            tick={{ fontSize: 12 }}
                            width={150}
                        />

                        <Tooltip content={<CustomTooltip />} />
                        <Legend content={<CustomLegend />} />

                        <Bar
                            dataKey="duration"
                            minPointSize={2}
                            shape={renderTaskLabel || <g />}
                        >
                            {ganttChartData.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={entry.isGroup ? '#999' : getTaskColor(entry)}
                                />
                            ))}
                        </Bar>

                        {/* Render dependencies if enabled */}
                        {renderDependencies()}
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}