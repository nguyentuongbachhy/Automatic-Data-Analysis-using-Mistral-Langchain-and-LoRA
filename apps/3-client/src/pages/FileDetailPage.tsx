// apps/client/src/pages/FileDetailPage.tsx
import { useMutation, useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';
import {
    AlertTriangle,
    AlignLeft,
    AtSign,
    BarChart,
    BarChart2,
    CheckCircle2,
    ChevronLeft,
    Eye,
    EyeOff,
    FileSpreadsheet,
    FileText,
    Globe,
    Hash,
    Info,
    LayoutGrid,
    Loader2,
    MapPin,
    MessageSquare,
    Phone,
    Plus,
    Table,
    UserCircle,
    Users,
    XCircle
} from 'lucide-react';
import { JSX, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ChatInterface from '../components/chat/ChatInterface';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle
} from '../components/ui/card';
import { ScrollArea } from '../components/ui/scroll-area';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { createChat, getChats, getFileById } from '../services/api';
import {
    ColumnInfo,
    FileData
} from '../types';
import { cn } from '../utils/cn';
import { formatFileSize } from '../utils/format';

// Define base DataColumn interface
interface DataColumn extends Partial<ColumnInfo> {
    name: string;
    displayName?: string;
    type: string;
    completeness?: number;
    quality?: number;
    nullable?: boolean;
    stats?: Record<string, any>;
    count?: number;
    unique?: number;
    missing?: number;
    distribution?: Record<string, any>;
    min?: any;
    max?: any;
}

// Define enhanced column interface that combines file.columns with statistical data
interface EnhancedColumn extends DataColumn {
    stats: Record<string, any>;
    distributionData?: string;
    min?: any;
    max?: any;
    mean?: number | string;
    median?: number | string;
    stdDev?: number | string;
    unique?: number;
    mostCommon?: string;
    dateRange?: number;
    topValues?: Record<string, any>;
    // New fields for specialized column types
    averageLength?: number;
    averageWords?: number;
    scalePoints?: number[];
    valueDistribution?: Record<string, number>;
    truePercentage?: number;
    falsePercentage?: number;
    genderDistribution?: Record<string, any>;
    rangeStats?: Record<string, any>;
    textStats?: Record<string, any>;
}

const snakeToCamel = (str: String) =>
    str.replace(/([-_][a-z])/g, (group) =>
        group.toUpperCase()
            .replace('-', '')
            .replace('_', '')
    );

const FileDetailPage = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('overview');
    const [showFullColumns, setShowFullColumns] = useState(false);
    const [enhancedColumns, setEnhancedColumns] = useState<EnhancedColumn[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [isCreatingChat, setIsCreatingChat] = useState(false);

    // Query file data
    const { data: file, isLoading: isFileLoading } = useQuery<FileData, Error>({
        queryKey: ['file', id],
        queryFn: () => getFileById(id as string),
        enabled: !!id,
    });

    const { data: chats } = useQuery({
        queryKey: ['file-chats', id],
        queryFn: () => getChats(id),
        enabled: !!id && activeTab === 'chat',
    });

    const createChatMutation = useMutation({
        mutationFn: () => createChat(id, file?.originalName ? `Chat về ${file.originalName}` : undefined),
        onSuccess: (data) => {
            setCurrentChatId(data.chatId);
            setIsCreatingChat(false);
        },
        onError: (error) => {
            console.error("Error creating chat:", error);
            setIsCreatingChat(false);
        }
    });

    // Tạo chat mới thủ công
    const handleCreateNewChat = () => {
        if (id && !isCreatingChat) {
            setIsCreatingChat(true);
            createChatMutation.mutate();
        }
    };

    // Process columns and combine with statistical analysis
    useEffect(() => {
        if (file && file.columns) {
            // Process and enhance columns with statistical data
            const processedColumns = file.columns.map(column => {
                const camelCaseName = snakeToCamel(column.name);
                console.log(`Looking for ${column.type} column: ${column.name} as ${camelCaseName}`);

                const enhancedColumn: EnhancedColumn = {
                    ...column,
                    name: camelCaseName,
                    completeness: column.completeness !== undefined ? column.completeness : 1,
                    quality: column.quality !== undefined ? column.quality * 100 : undefined,
                    stats: column.stats || {},
                };

                // Extract stats from the appropriate section based on column type
                if (file.analysis?.statisticalAnalysis) {
                    // Handle numeric columns
                    if (column.type === 'numeric' && file.analysis.statisticalAnalysis.numericSummary) {
                        const stats = file.analysis.statisticalAnalysis.numericSummary[camelCaseName];

                        if (stats) {
                            enhancedColumn.min = stats.min;
                            enhancedColumn.max = stats.max;
                            enhancedColumn.mean = stats.mean;
                            enhancedColumn.median = stats.median !== undefined ? stats.median : stats["50%"];
                            enhancedColumn.stdDev = stats.std;
                            enhancedColumn.stats = stats;
                        }
                    }
                    // Handle datetime columns
                    else if (column.type === 'datetime' && file.analysis.statisticalAnalysis.datetimeSummary) {
                        const stats = file.analysis.statisticalAnalysis.datetimeSummary[column.name];

                        if (stats) {
                            enhancedColumn.min = stats.min;
                            enhancedColumn.max = stats.max;
                            enhancedColumn.dateRange = stats.rangeDays;
                            enhancedColumn.stats = stats;
                        }
                    }
                    // Handle categorical columns
                    else if ((column.type === 'categorical' || column.type === 'string') &&
                        file.analysis.statisticalAnalysis.categoricalSummary) {
                        let stats = file.analysis.statisticalAnalysis.categoricalSummary[camelCaseName];

                        if (stats) {
                            enhancedColumn.mostCommon = stats.mode;
                            enhancedColumn.unique = stats.uniqueValues;
                            enhancedColumn.topValues = stats.topValues;
                            enhancedColumn.stats = stats;

                            // Create distribution data string
                            if (stats.topValues && Object.keys(stats.topValues).length > 0) {
                                const entries = Object.entries(stats.topValues);
                                enhancedColumn.distributionData = entries.slice(0, 3).map(([key, value]) =>
                                    `${key}: ${String(value)}`
                                ).join(', ');

                                if (entries.length > 3) {
                                    enhancedColumn.distributionData += ` (và ${entries.length - 3} khác)`;
                                }
                            }
                        }
                    }
                    // Handle binary columns
                    else if (column.type === 'binary' && file.analysis.statisticalAnalysis.binarySummary) {
                        const stats = file.analysis.statisticalAnalysis.binarySummary[camelCaseName];

                        if (stats) {
                            enhancedColumn.stats = stats;
                            if (stats.percentDistribution) {
                                enhancedColumn.truePercentage = stats.percentDistribution['1'] ||
                                    stats.percentDistribution['true'] ||
                                    stats.percentDistribution['True'] || 0;
                                enhancedColumn.falsePercentage = stats.percentDistribution['0'] ||
                                    stats.percentDistribution['false'] ||
                                    stats.percentDistribution['False'] || 0;
                            }
                        }
                    }
                    // Handle likert columns
                    else if (column.type === 'likert' && file.analysis.statisticalAnalysis.likertSummary) {
                        const stats = file.analysis.statisticalAnalysis.likertSummary[camelCaseName];

                        if (stats) {
                            enhancedColumn.stats = stats;
                            enhancedColumn.mean = stats.mean;
                            enhancedColumn.median = stats.median;
                            enhancedColumn.scalePoints = stats.scalePoints;
                            enhancedColumn.valueDistribution = stats.percentDistribution;
                        }
                    }
                    // Handle gender columns
                    else if (column.type === 'gender' && file.analysis.statisticalAnalysis.genderSummary) {
                        const stats = file.analysis.statisticalAnalysis.genderSummary[camelCaseName];

                        if (stats) {
                            enhancedColumn.stats = stats;
                            enhancedColumn.genderDistribution = stats.distribution;
                        }
                    }
                    // Handle range columns
                    else if (column.type === 'range' && file.analysis.statisticalAnalysis.rangeSummary) {
                        const stats = file.analysis.statisticalAnalysis.rangeSummary[camelCaseName];

                        if (stats) {
                            enhancedColumn.stats = stats;
                            enhancedColumn.rangeStats = stats;
                        }
                    }
                    // Handle text columns
                    else if (column.type === 'text' && file.analysis.statisticalAnalysis.textSummary) {
                        const stats = file.analysis.statisticalAnalysis.textSummary[camelCaseName];

                        if (stats) {
                            enhancedColumn.stats = stats;
                            enhancedColumn.textStats = stats;
                            enhancedColumn.averageLength = stats.averageLength;
                            enhancedColumn.averageWords = stats.averageWords;
                            enhancedColumn.unique = stats.uniqueCount;
                        }
                    }
                }

                // Additional special case handling for advanced analysis
                if (file.analysis?.advancedAnalysis) {
                    // Add text analysis data
                    if (column.type === 'text' && file.analysis.advancedAnalysis.textAnalysis?.[camelCaseName]) {
                        enhancedColumn.stats = {
                            ...enhancedColumn.stats,
                            textAnalysis: file.analysis.advancedAnalysis.textAnalysis[camelCaseName]
                        };
                    }
                    // Add likert analysis data
                    else if (column.type === 'likert' &&
                        file.analysis.advancedAnalysis.likertAnalysis?.responsePatterns?.[camelCaseName]) {
                        enhancedColumn.stats = {
                            ...enhancedColumn.stats,
                            likertAnalysis: file.analysis.advancedAnalysis.likertAnalysis.responsePatterns[camelCaseName]
                        };
                    }
                }

                return enhancedColumn;
            });

            setEnhancedColumns(processedColumns);
        }
    }, [file]);

    // Khi chuyển tab hoặc có dữ liệu chats mới, tự động xác định chatId
    useEffect(() => {
        if (activeTab === 'chat') {
            // Chỉ thiết lập chatId từ chats hiện có mà không tự động tạo mới
            if (chats && chats.length > 0 && !currentChatId) {
                setCurrentChatId(chats[0].id);
            }
        }
    }, [activeTab, chats, currentChatId]);

    const isLoading = isFileLoading;

    // Get file icon
    const getFileIcon = (fileType?: string): JSX.Element => {
        if (!fileType) return <FileText className="h-10 w-10 text-gray-500" />;

        switch (fileType.toLowerCase()) {
            case 'text/csv':
            case 'csv':
                return <Table className="h-10 w-10 text-green-500" />;
            case 'xlsx':
            case 'xls':
                return <FileSpreadsheet className="h-10 w-10 text-blue-500" />;
            default:
                return <FileText className="h-10 w-10 text-gray-500" />;
        }
    };

    // Format date
    const formatDate = (dateString?: string | Date): string => {
        if (!dateString) return '';
        try {
            return format(new Date(dateString), 'dd/MM/yyyy HH:mm', { locale: vi });
        } catch (e) {
            return 'Không hợp lệ';
        }
    };

    // Get quality badge
    const getQualityBadge = (score?: number): JSX.Element | null => {
        if (score === undefined) return null;

        let color = '';
        let label = '';

        if (score >= 90) {
            color = 'bg-green-100 text-green-800';
            label = 'Xuất sắc';
        } else if (score >= 80) {
            color = 'bg-green-100 text-green-800';
            label = 'Tốt';
        } else if (score >= 70) {
            color = 'bg-yellow-100 text-yellow-800';
            label = 'Khá';
        } else if (score >= 60) {
            color = 'bg-yellow-100 text-yellow-800';
            label = 'Trung bình';
        } else if (score >= 50) {
            color = 'bg-orange-100 text-orange-800';
            label = 'Yếu';
        } else {
            color = 'bg-red-100 text-red-800';
            label = 'Kém';
        }

        return (
            <Badge className={color}>
                {score.toFixed(1)}% - {label}
            </Badge>
        );
    };

    // Get column type badge
    const getColumnTypeBadge = (type?: string): JSX.Element => {
        if (!type) return <Badge variant="outline">Không xác định</Badge>;

        switch (type.toLowerCase()) {
            case 'numeric':
            case 'number':
                return <Badge variant="outline" className="bg-blue-100 text-blue-800">
                    <Hash className="h-3 w-3 mr-1" />Số
                </Badge>;
            case 'categorical':
            case 'string':
                return <Badge variant="outline" className="bg-purple-100 text-purple-800">
                    <LayoutGrid className="h-3 w-3 mr-1" />Phân loại
                </Badge>;
            case 'datetime':
            case 'date':
                return <Badge variant="outline" className="bg-amber-100 text-amber-800">
                    <BarChart className="h-3 w-3 mr-1" />Ngày giờ
                </Badge>;
            case 'text':
                return <Badge variant="outline" className="bg-green-100 text-green-800">
                    <AlignLeft className="h-3 w-3 mr-1" />Văn bản
                </Badge>;
            case 'boolean':
                return <Badge variant="outline" className="bg-pink-100 text-pink-800">
                    <CheckCircle2 className="h-3 w-3 mr-1" />Logic
                </Badge>;
            // New badge types
            case 'likert':
                return <Badge variant="outline" className="bg-indigo-100 text-indigo-800">
                    <BarChart className="h-3 w-3 mr-1" />Thang đo
                </Badge>;
            case 'binary':
                return <Badge variant="outline" className="bg-pink-100 text-pink-800">
                    <CheckCircle2 className="h-3 w-3 mr-1" />Nhị phân
                </Badge>;
            case 'gender':
                return <Badge variant="outline" className="bg-purple-100 text-purple-800">
                    <Users className="h-3 w-3 mr-1" />Giới tính
                </Badge>;
            case 'range':
                return <Badge variant="outline" className="bg-sky-100 text-sky-800">
                    <BarChart2 className="h-3 w-3 mr-1" />Phạm vi
                </Badge>;
            case 'email':
                return <Badge variant="outline" className="bg-blue-100 text-blue-800">
                    <AtSign className="h-3 w-3 mr-1" />Email
                </Badge>;
            case 'phone':
                return <Badge variant="outline" className="bg-green-100 text-green-800">
                    <Phone className="h-3 w-3 mr-1" />Điện thoại
                </Badge>;
            case 'address':
                return <Badge variant="outline" className="bg-amber-100 text-amber-800">
                    <MapPin className="h-3 w-3 mr-1" />Địa chỉ
                </Badge>;
            case 'name':
                return <Badge variant="outline" className="bg-violet-100 text-violet-800">
                    <UserCircle className="h-3 w-3 mr-1" />Tên
                </Badge>;
            case 'url':
                return <Badge variant="outline" className="bg-cyan-100 text-cyan-800">
                    <Globe className="h-3 w-3 mr-1" />URL
                </Badge>;
            case 'id':
                return <Badge variant="outline" className="bg-slate-100 text-slate-800">
                    <Hash className="h-3 w-3 mr-1" />ID
                </Badge>;
            default:
                return <Badge variant="outline">Khác</Badge>;
        }
    };

    // Calculate completion percentage
    const getColumnCompleteness = (column: EnhancedColumn) => {
        if (column.completeness !== undefined) return column.completeness * 100;

        const total = column.count || 0;
        const missing = column.missing || 0;

        if (total === 0) return 0;
        return Math.round(((total - missing) / total) * 100);
    };

    const getColumnsToDisplay = () => {
        if (showFullColumns) {
            return enhancedColumns;
        }

        // Show only top 10 columns
        return enhancedColumns.slice(0, 10);
    };

    const getColumnDisplayData = (column: EnhancedColumn) => {
        // Tính toán completeness nếu chưa có
        const completeness = getColumnCompleteness(column);

        // Lấy distribution để hiển thị
        let distributionData = column.distributionData;
        if (!distributionData && column.distribution && Object.keys(column.distribution).length > 0) {
            const entries = Object.entries(column.distribution);
            distributionData = entries.slice(0, 3).map(([key, value]) =>
                `${key}: ${typeof value === 'number' ? value.toFixed(2) : value}`
            ).join(', ');

            if (entries.length > 3) {
                distributionData += ` (và ${entries.length - 3} khác)`;
            }
        }

        if (file?.isPending) {
            return (
                <div className="flex items-center justify-center p-4 bg-muted rounded-md">
                    <Loader2 className="h-5 w-5 mr-2 animate-spin text-primary" />
                    <span className="text-sm font-medium">{file.message || "Đang phân tích dữ liệu..."}</span>
                </div>
            )
        }

        return (
            <div>
                <div className="flex items-center gap-2">
                    <h3 className="font-medium">{column.displayName || column.name}</h3>
                    {getColumnTypeBadge(column.type)}
                    <Badge
                        variant="outline"
                        className={cn(
                            completeness >= 95
                                ? "bg-green-100 text-green-800"
                                : completeness < 80
                                    ? "bg-red-100 text-red-800"
                                    : "bg-amber-100 text-amber-800"
                        )}
                    >
                        {completeness}% đầy đủ
                    </Badge>
                    {column.quality !== undefined && (
                        <Badge variant="outline" className={
                            column.quality >= 80 ? "bg-green-100 text-green-800" :
                                column.quality >= 60 ? "bg-amber-100 text-amber-800" :
                                    "bg-red-100 text-red-800"
                        }>
                            CL: {Math.round(column.quality)}%
                        </Badge>
                    )}
                </div>

                <div className="mt-2 text-sm">
                    {/* NUMERIC COLUMN */}
                    {(column.type === 'numeric' || column.type === 'number') && (
                        <div className="grid grid-cols-3 md:grid-cols-6 gap-x-4 gap-y-1">
                            <div>
                                <span className="text-muted-foreground">Min:</span>{" "}
                                <span className="font-medium">
                                    {column && typeof column.min === 'number' ? column.min.toLocaleString() : 'N/A'}
                                </span>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Max:</span>{" "}
                                <span className="font-medium">
                                    {column && typeof column.max === 'number' ? column.max.toLocaleString() : 'N/A'}
                                </span>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Mean:</span>{" "}
                                <span className="font-medium">
                                    {column && typeof column.mean === 'number' ? column.mean.toLocaleString() : 'N/A'}
                                </span>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Median:</span>{" "}
                                <span className="font-medium">
                                    {column && typeof column.median === 'number' ? column.median.toLocaleString() : 'N/A'}
                                </span>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Std:</span>{" "}
                                <span className="font-medium">
                                    {column && typeof column.stdDev === 'number' ? column.stdDev.toLocaleString() : 'N/A'}
                                </span>
                            </div>
                        </div>
                    )}

                    {/* CATEGORICAL COLUMN */}
                    {(column.type === 'categorical' || column.type === 'string') && (
                        <>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                                <div>
                                    <span className="text-muted-foreground">Unique:</span>{" "}
                                    <span className="font-medium">
                                        {column && typeof column.unique === 'number' ? column.unique.toLocaleString() : 'N/A'}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-muted-foreground">Most common:</span>{" "}
                                    <span className="font-medium">
                                        {column && typeof column.mostCommon ? column.mostCommon : 'N/A'}
                                    </span>
                                </div>
                            </div>
                            {column &&
                                column.topValues &&
                                typeof column.topValues === 'object' &&
                                column.topValues !== null && (
                                    <div className="mt-1">
                                        <span className="text-muted-foreground">Top values:</span>{" "}
                                        <span className="font-medium">
                                            {Object.entries(column.topValues as Record<string, unknown>)
                                                .slice(0, 3)
                                                .map(([key, value]) => `${key}: ${String(value)}`)
                                                .join(', ')}
                                            {Object.keys(column.topValues as Record<string, unknown>).length > 3
                                                ? ` (và ${Object.keys(column.topValues as Record<string, unknown>).length - 3} khác)`
                                                : ''}
                                        </span>
                                    </div>
                                )}
                        </>
                    )}

                    {/* DATETIME COLUMN */}
                    {(column.type === 'datetime' || column.type === 'date') && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            <div>
                                <span className="text-muted-foreground">Min:</span>{" "}
                                <span className="font-medium">
                                    {column && column.min
                                        ? formatDate(String(column.min))
                                        : 'N/A'}
                                </span>
                            </div>
                            <div>
                                <span className="text-muted-foreground">Max:</span>{" "}
                                <span className="font-medium">
                                    {column && column.max
                                        ? formatDate(String(column.max))
                                        : 'N/A'}
                                </span>
                            </div>
                            {column && column.dateRange && (
                                <div>
                                    <span className="text-muted-foreground">Range:</span>{" "}
                                    <span className="font-medium">
                                        {typeof column.dateRange === 'number' ? `${column.dateRange} ngày` : 'N/A'}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* TEXT COLUMN */}
                    {column.type === 'text' && (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1">
                            {column.averageLength !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Độ dài trung bình:</span>{" "}
                                    <span className="font-medium">
                                        {column.averageLength.toLocaleString()} ký tự
                                    </span>
                                </div>
                            )}
                            {column.averageWords !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Từ trung bình:</span>{" "}
                                    <span className="font-medium">
                                        {column.averageWords.toLocaleString()} từ
                                    </span>
                                </div>
                            )}
                            {column.unique !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Số giá trị khác nhau:</span>{" "}
                                    <span className="font-medium">
                                        {column.unique.toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {column.textStats?.topWords && (
                                <div className="col-span-3">
                                    <span className="text-muted-foreground">Từ phổ biến:</span>{" "}
                                    <span className="font-medium">
                                        {Object.entries(column.textStats.topWords)
                                            .slice(0, 5)
                                            .map(([word, count]) => `${word}: ${count}`)
                                            .join(', ')}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* BINARY COLUMN */}
                    {column.type === 'binary' && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {column.truePercentage !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">True/Yes:</span>{" "}
                                    <span className="font-medium">
                                        {column.truePercentage.toFixed(1)}%
                                    </span>
                                </div>
                            )}
                            {column.falsePercentage !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">False/No:</span>{" "}
                                    <span className="font-medium">
                                        {column.falsePercentage.toFixed(1)}%
                                    </span>
                                </div>
                            )}
                            {column.stats?.mode && (
                                <div>
                                    <span className="text-muted-foreground">Giá trị phổ biến:</span>{" "}
                                    <span className="font-medium">
                                        {column.stats.mode}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* LIKERT COLUMN */}
                    {column.type === 'likert' && (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1">
                            {column.mean !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Trung bình:</span>{" "}
                                    <span className="font-medium">
                                        {typeof column.mean === 'number' ? column.mean.toFixed(2) : column.mean}
                                    </span>
                                </div>
                            )}
                            {column.median !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Trung vị:</span>{" "}
                                    <span className="font-medium">
                                        {typeof column.median === 'number' ? column.median.toFixed(1) : column.median}
                                    </span>
                                </div>
                            )}
                            {column.scalePoints && column.scalePoints.length > 0 && (
                                <div>
                                    <span className="text-muted-foreground">Thang điểm:</span>{" "}
                                    <span className="font-medium">
                                        {column.scalePoints.join(', ')}
                                    </span>
                                </div>
                            )}
                            {column.valueDistribution && Object.keys(column.valueDistribution).length > 0 && (
                                <div className="col-span-3">
                                    <span className="text-muted-foreground">Phân bố:</span>{" "}
                                    <span className="font-medium">
                                        {Object.entries(column.valueDistribution)
                                            .slice(0, 5)
                                            .map(([value, percent]) => `${value}: ${typeof percent === 'number' ? percent.toFixed(1) : percent}%`)
                                            .join(', ')}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* GENDER COLUMN */}
                    {column.type === 'gender' && column.genderDistribution && (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1">
                            {column.genderDistribution.male && (
                                <div>
                                    <span className="text-muted-foreground">Nam:</span>{" "}
                                    <span className="font-medium">
                                        {column.genderDistribution.male.percentage?.toFixed(1)}% ({column.genderDistribution.male.count})
                                    </span>
                                </div>
                            )}
                            {column.genderDistribution.female && (
                                <div>
                                    <span className="text-muted-foreground">Nữ:</span>{" "}
                                    <span className="font-medium">
                                        {column.genderDistribution.female.percentage?.toFixed(1)}% ({column.genderDistribution.female.count})
                                    </span>
                                </div>
                            )}
                            {column.genderDistribution.other_or_unknown && (
                                <div>
                                    <span className="text-muted-foreground">Khác/Không rõ:</span>{" "}
                                    <span className="font-medium">
                                        {column.genderDistribution.other_or_unknown.percentage?.toFixed(1)}% ({column.genderDistribution.other_or_unknown.count})
                                    </span>
                                </div>
                            )}
                            {column.genderDistribution.ratio !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Tỷ lệ Nam/Nữ:</span>{" "}
                                    <span className="font-medium">
                                        {column.genderDistribution.ratio.toFixed(2)}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* RANGE COLUMN */}
                    {column.type === 'range' && column.rangeStats && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {column.rangeStats.average_min !== undefined && column.rangeStats.average_max !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Khoảng trung bình:</span>{" "}
                                    <span className="font-medium">
                                        {column.rangeStats.average_min.toFixed(1)} - {column.rangeStats.average_max.toFixed(1)}
                                    </span>
                                </div>
                            )}
                            {column.rangeStats.average_range !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Độ rộng trung bình:</span>{" "}
                                    <span className="font-medium">
                                        {column.rangeStats.average_range.toFixed(1)}
                                    </span>
                                </div>
                            )}
                            {column.rangeStats.unique_count !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Số khoảng khác nhau:</span>{" "}
                                    <span className="font-medium">
                                        {column.rangeStats.unique_count}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* EMAIL COLUMN */}
                    {column.type === 'email' && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {column.unique !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Địa chỉ duy nhất:</span>{" "}
                                    <span className="font-medium">
                                        {column.unique.toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {column.stats?.topDomains && (
                                <div>
                                    <span className="text-muted-foreground">Tên miền phổ biến:</span>{" "}
                                    <span className="font-medium">
                                        {Object.entries(column.stats.topDomains)
                                            .slice(0, 3)
                                            .map(([domain, count]) => `${domain}: ${count}`)
                                            .join(', ')}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* PHONE COLUMN */}
                    {column.type === 'phone' && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {column.unique !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Số điện thoại duy nhất:</span>{" "}
                                    <span className="font-medium">
                                        {column.unique.toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {column.stats?.countryCodeDistribution && (
                                <div>
                                    <span className="text-muted-foreground">Mã vùng phổ biến:</span>{" "}
                                    <span className="font-medium">
                                        {Object.entries(column.stats.countryCodeDistribution)
                                            .slice(0, 3)
                                            .map(([code, count]) => `${code}: ${count}`)
                                            .join(', ')}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ADDRESS COLUMN */}
                    {column.type === 'address' && (
                        <div className="grid grid-cols-1 gap-x-4 gap-y-1">
                            {column.unique !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Địa chỉ duy nhất:</span>{" "}
                                    <span className="font-medium">
                                        {column.unique.toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {column.stats?.averageLength && (
                                <div>
                                    <span className="text-muted-foreground">Độ dài trung bình:</span>{" "}
                                    <span className="font-medium">
                                        {column.stats.averageLength.toFixed(1)} ký tự
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* NAME COLUMN */}
                    {column.type === 'name' && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {column.unique !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Tên duy nhất:</span>{" "}
                                    <span className="font-medium">
                                        {column.unique.toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {column.stats?.wordCount && (
                                <div>
                                    <span className="text-muted-foreground">Từ trung bình:</span>{" "}
                                    <span className="font-medium">
                                        {column.stats.wordCount.toFixed(1)}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* URL COLUMN */}
                    {column.type === 'url' && (
                        <div className="grid grid-cols-1 gap-x-4 gap-y-1">
                            {column.unique !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">URL duy nhất:</span>{" "}
                                    <span className="font-medium">
                                        {column.unique.toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {column.stats?.topDomains && (
                                <div>
                                    <span className="text-muted-foreground">Tên miền phổ biến:</span>{" "}
                                    <span className="font-medium">
                                        {Object.entries(column.stats.topDomains)
                                            .slice(0, 3)
                                            .map(([domain, count]) => `${domain}: ${count}`)
                                            .join(', ')}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ID COLUMN */}
                    {column.type === 'id' && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {column.unique !== undefined && (
                                <div>
                                    <span className="text-muted-foreground">Giá trị duy nhất:</span>{" "}
                                    <span className="font-medium">
                                        {column.unique.toLocaleString()}
                                    </span>
                                </div>
                            )}
                            {column.stats?.pattern && (
                                <div>
                                    <span className="text-muted-foreground">Kiểu mẫu:</span>{" "}
                                    <span className="font-medium">
                                        {column.stats.pattern}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Hiển thị outliers nếu có */}
                    {file?.analysis?.outliers && file?.analysis?.outliers > 0 && column.type === 'numeric' && (
                        <div className="mt-1">
                            <Badge variant="outline" className="bg-amber-100 text-amber-800">
                                {file.analysis.outliers} outliers
                            </Badge>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    // Navigate to analysis page
    const goToAnalysis = () => {
        if (id) {
            navigate(`/analysis/${id}`);
        }
    };

    // Get data metrics from file
    const hasNullValues = file?.analysis?.dataQuality?.completeness?.missingCells > 0 || false;
    const hasDuplicates = file?.analysis?.dataQuality?.uniqueness?.duplicateRows > 0 || false;
    const dataQualityScore = file?.qualityScore || file?.analysis?.dataQuality?.overallScore;
    const insights = file?.insights?.map(insight => insight.content) || [];
    const recommendations = file?.analysis?.recommendations || [];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate('/files')}
                        className="h-8 w-8"
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <h1 className="text-2xl font-bold tracking-tight">Chi tiết tệp</h1>
                </div>

                <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={() => navigate(`/files/${id}/chat`)}>
                        <MessageSquare className="mr-2 h-4 w-4" /> Chat với dữ liệu
                    </Button>
                    <Button onClick={goToAnalysis}>
                        <BarChart2 className="mr-2 h-4 w-4" /> Phân tích
                    </Button>
                </div>
            </div>

            {/* File Info */}
            <Card>
                <CardHeader className="pb-2">
                    {isLoading ? (
                        <Skeleton className="h-8 w-3/4" />
                    ) : (
                        <div className="flex items-center">
                            {getFileIcon(file?.type)}
                            <div className="ml-3">
                                <CardTitle className="text-xl">{file?.originalName}</CardTitle>
                                <CardDescription>
                                    Tải lên lúc {formatDate(file?.createdAt)}
                                </CardDescription>
                            </div>
                        </div>
                    )}
                </CardHeader>

                <CardContent>
                    {isLoading ? (
                        <div className="flex flex-wrap gap-4">
                            {[...Array(4)].map((_, i) => (
                                <Skeleton key={i} className="h-6 w-24" />
                            ))}
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-4">
                            <Badge variant="outline">
                                {(file?.type || '').toUpperCase()}
                            </Badge>
                            <Badge variant="outline">
                                {(file?.analysis?.rowCount || 0).toLocaleString()} dòng
                            </Badge>
                            <Badge variant="outline">
                                {file?.analysis?.columnCount || 0} cột
                            </Badge>
                            <Badge variant="outline">
                                {formatFileSize(file?.size || 0)}
                            </Badge>
                            {getQualityBadge(dataQualityScore)}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Main Content */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="overview">Tổng quan</TabsTrigger>
                    <TabsTrigger value="columns">Cấu trúc dữ liệu</TabsTrigger>
                    <TabsTrigger value="preview">Xem trước</TabsTrigger>
                    <TabsTrigger value="chat">Chat</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                    {isLoading ? (
                        <>
                            <Skeleton className="h-[200px] w-full" />
                            <Skeleton className="h-[200px] w-full" />
                        </>
                    ) : (
                        <>
                            {/* Issues */}
                            {file?.analysis?.dataQuality?.issues && Array.isArray(file.analysis.dataQuality.issues) && file.analysis.dataQuality.issues.length > 0 && (
                                <Card className="border-amber-200 bg-amber-50 dark:bg-amber-950/20">
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base flex items-center">
                                            <AlertTriangle className="h-5 w-5 mr-2 text-amber-500" />
                                            Vấn đề cần lưu ý
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <ul className="space-y-2">
                                            {file.analysis.dataQuality.issues.map((issue: string, index: number) => (
                                                <li key={index} className="flex items-start">
                                                    <XCircle className="h-5 w-5 mr-2 text-amber-500 shrink-0 mt-0.5" />
                                                    <span>{issue}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Insights */}
                            {insights && insights.length > 0 && (
                                <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950/20">
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base flex items-center">
                                            <Info className="h-5 w-5 mr-2 text-blue-500" />
                                            Thông tin nổi bật
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <ul className="space-y-2">
                                            {insights.map((insight: string, index: number) => (
                                                <li key={index} className="flex items-start">
                                                    <CheckCircle2 className="h-5 w-5 mr-2 text-blue-500 shrink-0 mt-0.5" />
                                                    <span>{insight}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Recommendations */}
                            {recommendations && recommendations.length > 0 && (
                                <Card className="border-green-200 bg-green-50 dark:bg-green-950/20">
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base flex items-center">
                                            <Info className="h-5 w-5 mr-2 text-green-500" />
                                            Gợi ý phân tích
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <ul className="space-y-2">
                                            {recommendations.map((recommendation: any, index: number) => (
                                                <li key={index} className="flex items-start">
                                                    <CheckCircle2 className="h-5 w-5 mr-2 text-green-500 shrink-0 mt-0.5" />
                                                    <span>{typeof recommendation === 'string' ? recommendation :
                                                        recommendation.description || recommendation.text || JSON.stringify(recommendation)}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </CardContent>
                                </Card>
                            )}

                            {/* Data Stats */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-base">Thông tin dữ liệu</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                                        <div className="space-y-1">
                                            <p className="text-sm font-medium text-muted-foreground">Tổng số dòng</p>
                                            <p className="text-2xl font-bold">{(file?.analysis?.rowCount || 0).toLocaleString()}</p>
                                        </div>

                                        <div className="space-y-1">
                                            <p className="text-sm font-medium text-muted-foreground">Tổng số cột</p>
                                            <p className="text-2xl font-bold">{file?.analysis?.columnCount || 0}</p>
                                        </div>

                                        <div className="space-y-1">
                                            <p className="text-sm font-medium text-muted-foreground">Chất lượng dữ liệu</p>
                                            <p className="text-2xl font-bold">{(dataQualityScore || 0).toFixed(1)}%</p>
                                        </div>

                                        <div className="space-y-1">
                                            <p className="text-sm font-medium text-muted-foreground">Có giá trị trống</p>
                                            <p className="text-2xl font-bold flex items-center">
                                                {hasNullValues ? (
                                                    <>
                                                        <CheckCircle2 className="h-6 w-6 mr-2 text-amber-500" />
                                                        Có
                                                    </>
                                                ) : (
                                                    <>
                                                        <XCircle className="h-6 w-6 mr-2 text-green-500" />
                                                        Không
                                                    </>
                                                )}
                                            </p>
                                        </div>

                                        <div className="space-y-1">
                                            <p className="text-sm font-medium text-muted-foreground">Có dòng trùng lặp</p>
                                            <p className="text-2xl font-bold flex items-center">
                                                {hasDuplicates ? (
                                                    <>
                                                        <CheckCircle2 className="h-6 w-6 mr-2 text-amber-500" />
                                                        Có
                                                    </>
                                                ) : (
                                                    <>
                                                        <XCircle className="h-6 w-6 mr-2 text-green-500" />
                                                        Không
                                                    </>
                                                )}
                                            </p>
                                        </div>

                                        {file?.analysis?.outliers && file?.analysis?.outliers > 0 && (
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium text-muted-foreground">Outliers</p>
                                                <p className="text-2xl font-bold flex items-center">
                                                    <AlertTriangle className="h-6 w-6 mr-2 text-amber-500" />
                                                    {file.analysis.outliers}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Column Type Distribution */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-base">Phân bố loại dữ liệu</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                                        {Object.entries(
                                            enhancedColumns.reduce((acc, col) => {
                                                acc[col.type] = (acc[col.type] || 0) + 1;
                                                return acc;
                                            }, {} as Record<string, number>)
                                        ).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                                            <div key={type} className="flex items-center space-x-2">
                                                {getColumnTypeBadge(type)}
                                                <span className="text-sm font-medium">{count}</span>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Visualizations Summary */}
                            {file?.visualizations && file.visualizations.length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="text-base">Biểu đồ</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-2">
                                            {file.visualizations.slice(0, 3).map((viz, index) => (
                                                <div key={index} className="flex items-center p-2 border rounded hover:bg-muted transition-colors">
                                                    <BarChart2 className="h-5 w-5 mr-3 text-primary" />
                                                    <div>
                                                        <p className="font-medium">{viz.title}</p>
                                                        <p className="text-sm text-muted-foreground">{viz.description}</p>
                                                    </div>
                                                </div>
                                            ))}

                                            {file.visualizations.length > 3 && (
                                                <Button variant="outline" onClick={goToAnalysis} className="w-full mt-2">
                                                    Xem tất cả {file.visualizations.length} biểu đồ
                                                </Button>
                                            )}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </>
                    )}
                </TabsContent>

                <TabsContent value="columns" className="space-y-4">
                    {isLoading ? (
                        <Skeleton className="h-[500px] w-full" />
                    ) : (
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-base">Cấu trúc dữ liệu</CardTitle>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setShowFullColumns(!showFullColumns)}
                                        className="text-xs h-8"
                                    >
                                        {showFullColumns ? (
                                            <>
                                                <EyeOff className="h-3.5 w-3.5 mr-1" /> Thu gọn
                                            </>
                                        ) : (
                                            <>
                                                <Eye className="h-3.5 w-3.5 mr-1" /> Xem tất cả {enhancedColumns.length} cột
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                <ScrollArea className="h-[500px]">
                                    <div className="grid grid-cols-1 divide-y">
                                        {getColumnsToDisplay().map((column: EnhancedColumn, index: number) => (
                                            <div
                                                key={column.name}
                                                className={cn(
                                                    "p-4 hover:bg-muted/50 transition-colors",
                                                    !showFullColumns && index >= 5 && "animate-in fade-in slide-in-from-top-3"
                                                )}
                                            >
                                                <div className="flex items-start justify-between">
                                                    {getColumnDisplayData(column)}
                                                </div>
                                            </div>
                                        ))}

                                        {!showFullColumns && enhancedColumns.length > 10 && (
                                            <div className="p-4 text-center">
                                                <Button
                                                    variant="outline"
                                                    onClick={() => setShowFullColumns(true)}
                                                >
                                                    <Eye className="h-4 w-4 mr-2" />
                                                    Xem thêm {enhancedColumns.length - 10} cột
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                </ScrollArea>
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                <TabsContent value="preview" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Xem trước dữ liệu</CardTitle>
                            <CardDescription>
                                Hiển thị 100 dòng đầu tiên của dữ liệu
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <Skeleton className="h-[400px] w-full" />
                            ) : (
                                <div className="border rounded-md overflow-auto">
                                    <div className="h-[400px] flex items-center justify-center text-center p-4">
                                        <div>
                                            <FileSpreadsheet className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                                            <p className="mb-4">Để xem chi tiết dữ liệu, hãy sử dụng chức năng phân tích hoặc chat.</p>
                                            <Button onClick={goToAnalysis}>
                                                <BarChart2 className="mr-2 h-4 w-4" /> Phân tích dữ liệu
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="chat" className="h-[calc(100vh-14rem)]">
                    {isCreatingChat ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                                <p className="text-muted-foreground">Đang tạo cuộc trò chuyện mới...</p>
                            </div>
                        </div>
                    ) : currentChatId ? (
                        <div className="h-full flex flex-col">
                            <div className="flex justify-between items-center mb-3">
                                <div className="flex items-center">
                                    <MessageSquare className="w-5 h-5 mr-2 text-primary" />
                                    <h3 className="font-medium">
                                        {chats && chats.length > 0
                                            ? `Chat ${chats.findIndex(c => c.id === currentChatId) + 1}/${chats.length}`
                                            : 'Chat với dữ liệu'}
                                    </h3>
                                </div>

                                <Button onClick={handleCreateNewChat} disabled={isCreatingChat}>
                                    <Plus className="mr-2 h-4 w-4" />
                                    {isCreatingChat ? "Đang tạo..." : "Tạo cuộc trò chuyện mới"}
                                </Button>
                            </div>

                            {id && currentChatId && <ChatInterface
                                chatId={currentChatId}
                                fileId={id}
                            />}
                        </div>
                    ) : (
                        <div className="flex items-center justify-center h-full">
                            <Button onClick={handleCreateNewChat}>
                                <Plus className="mr-2 h-4 w-4" />
                                Tạo cuộc trò chuyện mới
                            </Button>
                        </div>
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default FileDetailPage;