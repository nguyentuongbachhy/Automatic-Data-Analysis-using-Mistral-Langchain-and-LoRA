import { useQuery } from "@tanstack/react-query";
import {
    AlertTriangle,
    BarChart4,
    CheckCircle,
    Clock,
    FileSpreadsheet,
    Info,
    List,
    Table as TableIcon
} from "lucide-react";
import React from "react";
import { getFileSummary } from "../../services/api";
import {
    ApiResponse,
    ColumnStats,
    FileData,
    ResponseStatus,
    deepCamelCaseKeys
} from "../../types";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { ScrollArea } from "../ui/scroll-area";
import { Skeleton } from "../ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";

interface DataSummaryProps {
    fileData: FileData;
}

// Custom types to handle the data structure
interface DataSummaryType {
    id: string;
    fileId: string;
    stats: {
        rowCount: number;
        columnCount: number;
        missingValues: number;
        duplicateRows: number;
        outliers: number;
        qualityScore?: number;
    };
    columns: DataColumn[];
    insights: string[];
    issues: string[];
    rowCount: number;
    columnCount: number;
    createdAt: string;
    updatedAt: string;
}

// Combination of ColumnInfo and ColumnStats
interface DataColumn extends Partial<ColumnStats> {
    name: string;
    type: string;
    completeness?: number;
    count?: number;
    missing?: number;
    distribution?: Record<string, number>;
}

// Helper function to adapt API response to our DataSummary type
const adaptDataSummary = (response: ApiResponse): DataSummaryType => {
    // Check if we have a valid response with data
    if (!response || response.status !== ResponseStatus.SUCCESS || !response.data) {
        return {} as DataSummaryType;
    }

    // Convert snake_case to camelCase if necessary
    const data = deepCamelCaseKeys(response.data);

    return {
        id: data.id || '',
        fileId: data.fileId || data.file_id || '',
        stats: data.stats || {
            rowCount: data.rowCount || data.analysis?.rowCount || 0,
            columnCount: data.columnCount || data.analysis?.columnCount || 0,
            missingValues: data.missingValues || data.analysis?.missingValues || 0,
            duplicateRows: data.duplicateRows || data.analysis?.duplicateRows || 0,
            outliers: data.outliers || data.analysis?.outliers || 0,
            qualityScore: data.qualityScore || 0
        },
        columns: Array.isArray(data.columns) ? data.columns : [],
        insights: Array.isArray(data.insights) ? data.insights :
            (data.analysis?.summary?.insights || []),
        issues: Array.isArray(data.issues) ? data.issues :
            (data.analysis?.summary?.issues || []),
        rowCount: data.rowCount || data.analysis?.rowCount || 0,
        columnCount: data.columnCount || data.analysis?.columnCount || 0,
        createdAt: data.createdAt || '',
        updatedAt: data.updatedAt || ''
    };
};

// Type definition for column types with styling information
type ColumnTypeInfo = {
    color: string;
    icon: React.ReactNode;
};

// Column type styles mapping
const COLUMN_TYPE_STYLES: Record<string, ColumnTypeInfo> = {
    'numeric': {
        color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        icon: <BarChart4 className="h-3 w-3 mr-1" />
    },
    'number': {
        color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
        icon: <BarChart4 className="h-3 w-3 mr-1" />
    },
    'categorical': {
        color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
        icon: <List className="h-3 w-3 mr-1" />
    },
    'datetime': {
        color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300',
        icon: <Clock className="h-3 w-3 mr-1" />
    },
    'date': {
        color: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300',
        icon: <Clock className="h-3 w-3 mr-1" />
    },
    'text': {
        color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        icon: <TableIcon className="h-3 w-3 mr-1" />
    },
    'string': {
        color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
        icon: <TableIcon className="h-3 w-3 mr-1" />
    },
    'boolean': {
        color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
        icon: <TableIcon className="h-3 w-3 mr-1" />
    },
};

// Default for unknown types
const DEFAULT_TYPE_STYLE: ColumnTypeInfo = {
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    icon: <TableIcon className="h-3 w-3 mr-1" />
};

const DataSummary: React.FC<DataSummaryProps> = ({ fileData }) => {
    const { data: summaryResponse, isLoading, error } = useQuery<ApiResponse, Error>({
        queryKey: ["summary", fileData.id],
        queryFn: () => getFileSummary(fileData.id),
        enabled: !!fileData.id,
    });

    // Adapt the data from API to our format
    const summary: DataSummaryType = React.useMemo(() => {
        return summaryResponse ? adaptDataSummary(summaryResponse) : {} as DataSummaryType;
    }, [summaryResponse]);

    // Loading state
    if (isLoading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-[200px] w-full" />
                <Skeleton className="h-[300px] w-full" />
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <Alert variant="destructive" className="mb-4">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>
                    {error.message || "Không thể tải tổng hợp dữ liệu. Vui lòng thử lại sau."}
                </AlertDescription>
            </Alert>
        );
    }

    // Check if we have valid data
    const hasValidData = summary && summary.stats && summary.columns;
    if (!hasValidData) {
        return (
            <Card className="p-8 text-center">
                <p className="text-muted-foreground">Dữ liệu tổng hợp không đầy đủ</p>
            </Card>
        );
    }

    const { stats, columns, insights, issues } = summary;

    // Get badge for column type with appropriate styling
    const getColumnTypeBadge = (type: string): React.ReactNode => {
        const typeKey = type.toLowerCase();
        const typeInfo = COLUMN_TYPE_STYLES[typeKey] || DEFAULT_TYPE_STYLE;

        return (
            <Badge variant="outline" className={`${typeInfo.color} flex items-center text-xs font-medium`}>
                {typeInfo.icon} {type}
            </Badge>
        );
    };

    // Calculate data completeness for a column
    const getCompleteness = (column: DataColumn): number => {
        if (column.completeness !== undefined) return column.completeness;

        const total = column.count || 0;
        const missing = column.missing || 0;

        if (total === 0) return 0;
        return Math.round(((total - missing) / total) * 100);
    };

    // Render column statistics based on type
    const renderColumnStats = (column: DataColumn): React.ReactNode => {
        const columnType = column.type.toLowerCase();

        if (columnType === 'numeric' || columnType === 'number') {
            return (
                <>
                    <div>Min: {column.min !== undefined ? (typeof column.min === 'number' ? column.min.toLocaleString() : column.min instanceof Date ? column.min.toLocaleString() : column.min) : 'N/A'}</div>
                    <div>Max: {column.max !== undefined ? (typeof column.max === 'number' ? column.max.toLocaleString() : column.max instanceof Date ? column.max.toLocaleString() : column.max) : 'N/A'}</div>
                    <div>Unique: {column.unique || 'N/A'}</div>
                </>
            );
        }

        if (columnType === 'categorical' || columnType === 'string') {
            return (
                <>
                    <div>Unique: {column.unique || 'N/A'}</div>
                    {column.distribution && (
                        <div>
                            Top: {Object.entries(column.distribution)
                                .slice(0, 1)
                                .map(([key, value]) => `${key} (${value})`)
                                .join(', ')}
                        </div>
                    )}
                </>
            );
        }

        if (columnType === 'datetime' || columnType === 'date') {
            return (
                <>
                    <div>Min: {column.min ? (column.min instanceof Date ? column.min.toLocaleDateString() : new Date(column.min as string).toLocaleDateString()) : 'N/A'}</div>
                    <div>Max: {column.max ? (column.max instanceof Date ? column.max.toLocaleDateString() : new Date(column.max as string).toLocaleDateString()) : 'N/A'}</div>
                </>
            );
        }

        return <div>No stats available</div>;
    };

    return (
        <div className="space-y-6">
            {/* File information card */}
            <Card>
                <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                        <div>
                            <CardTitle className="text-xl">
                                <div className="flex items-center">
                                    <FileSpreadsheet className="mr-2 h-5 w-5" />
                                    {fileData.originalName}
                                </div>
                            </CardTitle>
                            <CardDescription>
                                Tải lên lúc {new Date(fileData.createdAt).toLocaleString()}
                            </CardDescription>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Badge variant="outline" className="bg-gray-100">
                                {fileData.type.toUpperCase()}
                            </Badge>
                            {stats &&
                                <>
                                    <Badge variant="outline" className="bg-blue-100 text-blue-800">
                                        {stats.rowCount.toLocaleString()} dòng
                                    </Badge>
                                    <Badge variant="outline" className="bg-green-100 text-green-800">
                                        {stats.columnCount} cột
                                    </Badge>
                                </>}
                        </div>
                    </div>
                </CardHeader>
            </Card>

            {/* Data quality issues card */}
            {issues && issues.length > 0 && (
                <Card className="border-amber-200 bg-amber-50 dark:bg-amber-950 dark:border-amber-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center">
                            <AlertTriangle className="h-5 w-5 mr-2 text-amber-500" />
                            Vấn đề cần chú ý
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-2">
                            {issues.map((issue, index) => (
                                <li key={index} className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span className="text-sm">{issue}</span>
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {/* Data insights card */}
            {insights && insights.length > 0 && (
                <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center">
                            <Info className="h-5 w-5 mr-2 text-blue-500" />
                            Insights từ dữ liệu
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-2">
                            {insights.map((insight, index) => (
                                <li key={index} className="flex items-start">
                                    <span className="mr-2">•</span>
                                    <span className="text-sm">{insight}</span>
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            )}

            {/* Column details table */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Chi tiết các cột</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <ScrollArea className="h-[400px]">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Tên cột</TableHead>
                                    <TableHead>Loại dữ liệu</TableHead>
                                    <TableHead>Đầy đủ</TableHead>
                                    <TableHead>Thống kê</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {columns && columns.map((column) => {
                                    const completeness = getCompleteness(column);
                                    return (
                                        <TableRow key={column.name}>
                                            <TableCell className="font-medium">{column.name}</TableCell>
                                            <TableCell>{getColumnTypeBadge(column.type)}</TableCell>
                                            <TableCell>
                                                <div className="flex items-center">
                                                    {completeness >= 95 ? (
                                                        <CheckCircle className="h-4 w-4 text-green-500 mr-1" />
                                                    ) : completeness < 80 ? (
                                                        <AlertTriangle className="h-4 w-4 text-amber-500 mr-1" />
                                                    ) : (
                                                        <Info className="h-4 w-4 text-blue-500 mr-1" />
                                                    )}
                                                    {completeness}%
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="text-xs">
                                                    {renderColumnStats(column)}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </ScrollArea>
                </CardContent>
            </Card>
        </div>
    );
};

export default DataSummary;