// apps/client/src/pages/AnalysisPage.tsx
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';
import {
    Activity,
    BarChart2,
    BrainCircuit,
    Check,
    ChevronLeft,
    Download,
    FileSpreadsheet,
    FileText,
    Info,
    LineChart,
    Loader2, // Added Loader2 import
    Maximize2,
    MessageSquare,
    Network,
    PieChart,
    Plus,
    RefreshCw,
    ScatterChart,
    Settings,
    Share2,
    Table,
    X
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ChatInterface from '../components/chat/ChatInterface';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle
} from '../components/ui/card';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import ChartRenderer from '../components/visualization/ChartRenderer';
import { useAuth } from '../contexts/AuthContext';
import {
    analyzeTimeSeries,
    correlationAnalysis,
    createChat, // Added createChat import
    createVisualization,
    generateInsights,
    getChats, // Added getChats import
    getFileById,
    getFileVisualizations,
    getRecommendedCharts,
    performFullAnalysis
} from '../services/api';
import {
    ApiResponse,
    ChartRecommendation,
    CorrelationAnalysisRequest,
    CorrelationData,
    FileData,
    InsightData,
    RecommendedChartData,
    ResponseStatus,
    TimeSeriesAnalysisRequest,
    TimeSeriesData,
    VisualizationData
} from '../types';
import { ChartType } from '../types/common';

// Helper types for better type checking with API responses

// Helper function to standardize chart data for visualization
const standardizeChartData = (visualization: VisualizationData): VisualizationData => {
    // Make sure we have a valid object
    if (!visualization) return {
        id: '',
        type: ChartType.BAR,
        title: 'Không có dữ liệu',
        data: [],
        recommendedType: ChartType.BAR,
    };

    // Ensure data is in proper format
    let chartData = visualization.data;
    if (!chartData) {
        chartData = [];
    }

    return {
        ...visualization,
        type: visualization.type || ChartType.BAR,
        title: visualization.title || 'Biểu đồ không tiêu đề',
        description: visualization.description || '',
        data: chartData,
        recommendedType: visualization.recommendedType || visualization.type || ChartType.BAR,
    };
};

// Custom hook for handling analysis progress
// This would need to be replaced with actual implementation based on your API
const useAnalysisProgress = () => {
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('');
    const [isComplete, setIsComplete] = useState(false);

    const startAnalysis = async (fileId: string) => {
        setProgress(0);
        setStatus('Đang bắt đầu phân tích...');
        setIsComplete(false);

        try {
            // Call the actual API to start analysis
            await performFullAnalysis(fileId, 'full');

            // This would need to be updated with actual implementation
            // Just simulating progress for now
            let currentProgress = 0;
            const interval = setInterval(() => {
                currentProgress += 10;
                setProgress(currentProgress);
                setStatus(`Đang phân tích... ${currentProgress}%`);

                if (currentProgress >= 100) {
                    clearInterval(interval);
                    setIsComplete(true);
                    setStatus('Phân tích hoàn tất');
                }
            }, 1000);

            return () => clearInterval(interval);
        } catch (error) {
            console.error('Lỗi khi phân tích:', error);
            setStatus('Phân tích thất bại');
            setIsComplete(true);
            return () => { };
        }
    };

    return { progress, status, isComplete, startAnalysis };
};

const AnalysisPage = () => {
    const { user } = useAuth();
    if (!user || !user.id) {
        return (
            <p>
                Please login first
            </p>
        );
    }

    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('visualizations');
    const [expandedChart, setExpandedChart] = useState<number | null>(null);
    const [showDialog, setShowDialog] = useState(false);
    const [showCorrelation, setShowCorrelation] = useState(false);
    const [correlationThreshold, setCorrelationThreshold] = useState(0.3);
    const [showTimeSeriesAnalysis, setShowTimeSeriesAnalysis] = useState(false);
    const [showProgress, setShowProgress] = useState(false);
    const [analysisStatus, setAnalysisStatus] = useState('');
    const [newChartDialog, setNewChartDialog] = useState(false);
    const [newChartData, setNewChartData] = useState<VisualizationData | null>(null);

    // Chat related state variables
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [isCreatingChat, setIsCreatingChat] = useState(false);

    const analysisProgressHook = useAnalysisProgress();
    const { progress: analysisProgress, status, isComplete } = analysisProgressHook;

    const [timeSeriesConfig, setTimeSeriesConfig] = useState<TimeSeriesAnalysisRequest>({
        dateColumn: '',
        valueColumn: '',
        forecast: true,
        forecastPeriods: 10
    });

    const [chartConfig, setChartConfig] = useState({
        chartType: ChartType.BAR,
        columns: [] as string[],
        title: '',
        description: ''
    });

    const queryClient = useQueryClient();

    // Fetch file data
    const { data: file, isLoading: isFileLoading } = useQuery<FileData, Error>({
        queryKey: ['file', id],
        queryFn: () => getFileById(id as string),
        enabled: !!id,
    });

    // Fetch chat data
    const { data: chats } = useQuery({
        queryKey: ['file-chats', id],
        queryFn: () => getChats(id),
        enabled: !!id && activeTab === 'chat',
    });

    // Fetch visualizations
    const { data: visualizations = [], isLoading: isVisualizationsLoading } = useQuery<VisualizationData[], Error>({
        queryKey: ['visualizations', id],
        queryFn: () => getFileVisualizations(id as string),
        enabled: !!id,
    });

    // Fetch insights
    const { data: insightsResponse, isLoading: isInsightsLoading } = useQuery<InsightData[] | ApiResponse, Error>({
        queryKey: ['insights', id],
        queryFn: () => generateInsights(id as string),
        enabled: !!id,
    });

    // Extract insights data, handling both direct array and ApiResponse format
    const insights: InsightData[] = Array.isArray(insightsResponse)
        ? insightsResponse
        : ((insightsResponse as ApiResponse)?.status === ResponseStatus.SUCCESS
            ? ((insightsResponse as ApiResponse).data as InsightData[] || [])
            : []);

    // Fetch correlation data with proper ApiResponse type
    const { data: correlationResponse, isLoading: isCorrelationLoading } = useQuery<ApiResponse, Error>({
        queryKey: ['correlation', id, correlationThreshold],
        queryFn: () => correlationAnalysis(
            id as string,
            { threshold: correlationThreshold } as CorrelationAnalysisRequest
        ),
        enabled: !!id && showCorrelation,
    });

    // Extract correlation data from API response safely
    const correlationData: CorrelationData | undefined =
        correlationResponse?.status === ResponseStatus.SUCCESS
            ? (correlationResponse.data as CorrelationData)
            : undefined;

    // Fetch chart recommendations with proper type handling
    const { data: recommendedChartsResponse } = useQuery<ChartRecommendation | ApiResponse, Error>({
        queryKey: ['recommendedCharts', id],
        queryFn: () => getRecommendedCharts(id as string),
        enabled: !!id,
    });

    const processedRecommendedCharts = useMemo(() => {
        const recommendedCharts: RecommendedChartData[] | undefined =
            (recommendedChartsResponse as ApiResponse)?.status !== undefined
                ? ((recommendedChartsResponse as ApiResponse).status === ResponseStatus.SUCCESS
                    ? (recommendedChartsResponse as ApiResponse).data.bestCharts as RecommendedChartData[]
                    : undefined)
                : (recommendedChartsResponse as ChartRecommendation)?.bestCharts || [];
        return (recommendedCharts ?? []).sort((a, b) => b.score - a.score)
    }, [recommendedChartsResponse]);

    // Create chart mutation with improved type safety
    const createChartMutation = useMutation({
        mutationFn: ({ chartType, columns, title, description }: {
            chartType: string,
            columns: string[],
            title?: string,
            description?: string
        }) => {
            console.log("Creating chart with:", { chartType, columns, title, description });

            if (!id) {
                throw new Error("Missing fileId");
            }

            if (!columns.length) {
                throw new Error("No columns selected");
            }

            return createVisualization(
                id as string,
                {
                    type: chartType,
                    title: title || `${chartType} Chart`,
                    description: description || '',
                    data: [],
                    config: { columns },
                    parameters: { columns },
                    fileId: id
                }
            );
        },
        onSuccess: (data) => {
            if ('error' in data && data.error) {
                console.error("Chart created but has error:", data.error);
                return;
            }

            setNewChartData(data as VisualizationData);
            setNewChartDialog(true);

            console.log("Chart created successfully:", data);
            queryClient.invalidateQueries({ queryKey: ['visualizations', id] });
            setShowDialog(false);
        },
        onError: (error: any) => {
            console.error("Failed to create chart:", error);
        }
    });

    // Create chat mutation
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

    // Handle creating a new chat
    const handleCreateNewChat = () => {
        if (id && !isCreatingChat) {
            setIsCreatingChat(true);
            createChatMutation.mutate();
        }
    };

    // Fetch timeseries with proper ApiResponse type
    const { data: timeSeriesResponse, isLoading: isTimeSeriesLoading } = useQuery<ApiResponse, Error>({
        queryKey: ['timeSeries', id, timeSeriesConfig],
        queryFn: () => analyzeTimeSeries(
            id as string,
            timeSeriesConfig
        ),
        enabled: !!id && showTimeSeriesAnalysis && !!timeSeriesConfig.dateColumn && !!timeSeriesConfig.valueColumn,
    });

    // Extract time series data from API response safely
    const timeSeriesData: TimeSeriesData | undefined =
        timeSeriesResponse?.status === ResponseStatus.SUCCESS
            ? (timeSeriesResponse.data as TimeSeriesData)
            : undefined;

    // Start full analysis
    const startFullAnalysis = async () => {
        try {
            setShowProgress(true);
            setAnalysisStatus('Đang bắt đầu phân tích...');

            // Start the analysis and track progress
            const cleanup = await analysisProgressHook.startAnalysis(
                id as string,
            );

            return () => {
                if (cleanup) cleanup();
                setShowProgress(false);
            };
        } catch (error) {
            console.error('Lỗi khi bắt đầu phân tích:', error);
            setAnalysisStatus('Phân tích thất bại');
            setShowProgress(false);
        }
    };

    // Watch for analysis completion
    useEffect(() => {
        if (isComplete && showProgress) {
            setShowProgress(false);
            queryClient.invalidateQueries({ queryKey: ['visualizations', id] });
            queryClient.invalidateQueries({ queryKey: ['insights', id] });
        }
    }, [isComplete, showProgress, queryClient, id]);

    // Set current chat ID when switching to the chat tab or when chats are loaded
    useEffect(() => {
        if (activeTab === 'chat') {
            // Only set chatId from existing chats without automatically creating a new one
            if (chats && chats.length > 0 && !currentChatId) {
                setCurrentChatId(chats[0].id);
            }
        }
    }, [activeTab, chats, currentChatId]);

    // Standardize visualization data to ensure compatibility with ChartRenderer
    const standardizedVisualizations: VisualizationData[] = Array.isArray(visualizations)
        ? visualizations
            .filter((visualization): visualization is VisualizationData => visualization !== null)
            .map(standardizeChartData)
        : [];

    // Get file icon
    const getFileIcon = (fileType?: string) => {
        switch (fileType) {
            case 'csv':
                return <Table className="h-8 w-8 text-green-500" />;
            case 'xlsx':
            case 'xls':
                return <FileSpreadsheet className="h-8 w-8 text-blue-500" />;
            default:
                return <FileText className="h-8 w-8 text-gray-500" />;
        }
    };

    // Format date
    const formatDate = (dateString?: string | Date) => {
        if (!dateString) return '';
        try {
            return format(new Date(dateString), 'dd/MM/yyyy HH:mm', { locale: vi });
        } catch (e) {
            return 'Không hợp lệ';
        }
    };

    const getExpandedChart = () => {
        if (expandedChart === null || !standardizedVisualizations || expandedChart >= standardizedVisualizations.length) {
            return null;
        }
        return standardizedVisualizations[expandedChart];
    };

    // Get insight importance color
    const getInsightImportanceColor = (importance: number): string => {
        if (importance >= 8) return "bg-red-500";
        if (importance >= 6) return "bg-orange-500";
        if (importance >= 4) return "bg-yellow-500";
        if (importance >= 2) return "bg-blue-500";
        return "bg-gray-500";
    };

    useEffect(() => {
        if (!showDialog) {
            setChartConfig({
                chartType: ChartType.BAR,
                columns: [],
                title: '',
                description: ''
            });
        }
    }, [showDialog]);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate(`/files/${id}`)}
                        className="h-8 w-8"
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <h1 className="text-2xl font-bold tracking-tight">Phân tích dữ liệu</h1>
                </div>

                <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={() => navigate(`/files/${id}/chat`)}>
                        <MessageSquare className="mr-2 h-4 w-4" /> Chat với dữ liệu
                    </Button>
                    <Button variant="outline" onClick={() => setShowDialog(true)}>
                        <Plus className="mr-2 h-4 w-4" /> Tạo biểu đồ mới
                    </Button>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline">
                                <RefreshCw className="mr-2 h-4 w-4" /> Phân tích nâng cao
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => startFullAnalysis()}>
                                <Activity className="mr-2 h-4 w-4" />
                                <span>Phân tích toàn diện</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                                setActiveTab('correlation');
                                setShowCorrelation(true);
                            }}>
                                <Network className="mr-2 h-4 w-4" />
                                <span>Phân tích tương quan</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                                setActiveTab('timeSeries');
                                setShowTimeSeriesAnalysis(true);
                            }}>
                                <LineChart className="mr-2 h-4 w-4" />
                                <span>Phân tích chuỗi thời gian</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setActiveTab('chat')}>
                                <BrainCircuit className="mr-2 h-4 w-4" />
                                <span>Chat với dữ liệu</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>

            {/* File Info Card */}
            <Card>
                <CardContent className="p-4 sm:p-6">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                        {isFileLoading ? (
                            <>
                                <Skeleton className="h-12 w-12 rounded-md" />
                                <div className="space-y-2">
                                    <Skeleton className="h-5 w-40" />
                                    <Skeleton className="h-4 w-32" />
                                </div>
                            </>
                        ) : (
                            <>
                                <div className="h-12 w-12 shrink-0 flex items-center justify-center">
                                    {getFileIcon(file?.type)}
                                </div>
                                <div>
                                    <h2 className="text-lg font-medium">{file?.originalName}</h2>
                                    <p className="text-sm text-muted-foreground">
                                        {(file?.analysis?.rowCount || 0).toLocaleString()} dòng · {file?.analysis?.columnCount || 0} cột · Tải lên {formatDate(file?.createdAt)}
                                    </p>
                                </div>
                            </>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Main Content */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="visualizations" className="flex items-center gap-1">
                        <BarChart2 className="h-4 w-4" /> Trực quan hóa
                    </TabsTrigger>
                    <TabsTrigger value="insights" className="flex items-center gap-1">
                        <Info className="h-4 w-4" /> Insights
                    </TabsTrigger>
                    <TabsTrigger value="correlation" className="flex items-center gap-1">
                        <Network className="h-4 w-4" /> Tương quan
                    </TabsTrigger>
                    <TabsTrigger value="timeSeries" className="flex items-center gap-1">
                        <LineChart className="h-4 w-4" /> Chuỗi thời gian
                    </TabsTrigger>
                    <TabsTrigger value="chat" className="flex items-center gap-1">
                        <MessageSquare className="h-4 w-4" /> Chat
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="visualizations" className="space-y-6">
                    {isVisualizationsLoading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {[...Array(4)].map((_, index) => (
                                <Card key={index}>
                                    <CardHeader className="pb-2">
                                        <Skeleton className="h-5 w-2/3" />
                                    </CardHeader>
                                    <CardContent>
                                        <Skeleton className="h-[240px] w-full" />
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : !standardizedVisualizations || standardizedVisualizations.length === 0 ? (
                        <Card>
                            <CardContent className="p-6 text-center">
                                <BarChart2 className="mx-auto h-12 w-12 text-muted-foreground" />
                                <h3 className="mt-4 text-lg font-semibold">Chưa có biểu đồ nào</h3>
                                <p className="mt-2 text-sm text-muted-foreground">
                                    Tạo biểu đồ mới hoặc sử dụng chat để tạo biểu đồ tự động
                                </p>
                                <div className="mt-4 flex flex-col sm:flex-row gap-2 justify-center">
                                    <Button onClick={() => setShowDialog(true)}>
                                        <Plus className="mr-2 h-4 w-4" /> Tạo biểu đồ
                                    </Button>
                                    <Button variant="outline" onClick={() => setActiveTab('chat')}>
                                        <MessageSquare className="mr-2 h-4 w-4" /> Chat để tạo biểu đồ
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {processedRecommendedCharts && Array.isArray(processedRecommendedCharts) && (
                                <div className="mb-6">
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="text-lg font-medium">Biểu đồ đề xuất</h3>
                                        <Button variant="outline" size="sm">
                                            Xem tất cả
                                        </Button>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        {processedRecommendedCharts.slice(0, 6).map((chart, index) => (
                                            <Card
                                                key={`rec-${index}`}
                                                className="cursor-pointer hover:border-primary transition-all"
                                                onClick={() => {
                                                    if (!Array.isArray(chart.columns) || chart.columns.length === 0) {
                                                        console.error("Không có cột nào được chọn hoặc columns không phải là mảng!");
                                                        return;
                                                    }

                                                    console.log("Creating chart with data:", chart);

                                                    createChartMutation.mutate({
                                                        chartType: chart.chartType,
                                                        columns: chart.columns,
                                                        title: chart.title,
                                                        description: chart.description
                                                    });
                                                }}
                                            >
                                                <CardContent className="p-4">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <div className="flex items-center gap-2">
                                                            {chart.chartType === ChartType.BAR && <BarChart2 className="h-4 w-4" />}
                                                            {chart.chartType === ChartType.LINE && <LineChart className="h-4 w-4" />}
                                                            {chart.chartType === ChartType.PIE && <PieChart className="h-4 w-4" />}
                                                            {chart.chartType === ChartType.SCATTER && <ScatterChart className="h-4 w-4" />}
                                                            <span className="font-medium text-sm">{chart.chartType}</span>
                                                        </div>
                                                        <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-800 rounded font-medium">
                                                            {Math.round(chart.score * 100)}%
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-muted-foreground">{chart.description}</p>
                                                    <div className="mt-2 flex flex-wrap gap-1">
                                                        {chart.columns.map((col: string, idx: number) => (
                                                            <span
                                                                key={idx}
                                                                className="inline-flex text-xs bg-neutral-700 px-2 py-1 rounded"
                                                            >
                                                                {col}
                                                            </span>
                                                        ))}
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {standardizedVisualizations.map((chart: VisualizationData, index: number) => (
                                <Card key={chart.id || `chart-${index}`} className="group overflow-hidden">
                                    <CardHeader className="pb-2">
                                        <div className="flex items-start justify-between">
                                            <CardTitle className="text-base">{chart.title}</CardTitle>
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-4 w-4">
                                                            <path d="M3.625 7.5C3.625 8.12132 3.12132 8.625 2.5 8.625C1.87868 8.625 1.375 8.12132 1.375 7.5C1.375 6.87868 1.87868 6.375 2.5 6.375C3.12132 6.375 3.625 6.87868 3.625 7.5ZM8.625 7.5C8.625 8.12132 8.12132 8.625 7.5 8.625C6.87868 8.625 6.375 8.12132 6.375 7.5C6.375 6.87868 6.87868 6.375 7.5 6.375C8.12132 6.375 8.625 6.87868 8.625 7.5ZM12.5 8.625C13.1213 8.625 13.625 8.12132 13.625 7.5C13.625 6.87868 13.1213 6.375 12.5 6.375C11.8787 6.375 11.375 6.87868 11.375 7.5C11.375 8.12132 11.8787 8.625 12.5 8.625Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd"></path>
                                                        </svg>
                                                    </Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem onClick={() => setExpandedChart(index)}>
                                                        <Maximize2 className="mr-2 h-4 w-4" />
                                                        <span>Phóng to</span>
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem>
                                                        <Share2 className="mr-2 h-4 w-4" />
                                                        <span>Chia sẻ</span>
                                                    </DropdownMenuItem>
                                                    <DropdownMenuItem>
                                                        <Download className="mr-2 h-4 w-4" />
                                                        <span>Tải xuống</span>
                                                    </DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div
                                            className="h-[240px] cursor-pointer"
                                            onClick={() => setExpandedChart(index)}
                                        >
                                            <ChartRenderer
                                                visualization={{
                                                    data: chart.data,
                                                    type: chart.type,
                                                    title: chart.title,
                                                    description: chart.description,
                                                    config: chart.config
                                                }}
                                            />
                                        </div>
                                    </CardContent>
                                    {chart.insight && (
                                        <CardFooter className="pt-0 text-sm text-muted-foreground">
                                            <div className="border-t pt-3 w-full">
                                                <div className="flex items-center gap-1 mb-1 text-xs font-medium text-primary">
                                                    <Info className="h-3 w-3" /> INSIGHT
                                                </div>
                                                {chart.insight}
                                            </div>
                                        </CardFooter>
                                    )}
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                {/* Insights Tab */}
                <TabsContent value="insights">
                    <Card>
                        <CardHeader>
                            <CardTitle>Insights & Phân tích</CardTitle>
                            <CardDescription>
                                Phân tích chuyên sâu dữ liệu của bạn
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isInsightsLoading ? (
                                <div className="space-y-4">
                                    {[...Array(5)].map((_, i) => (
                                        <Skeleton key={i} className="h-16 w-full" />
                                    ))}
                                </div>
                            ) : !insights || insights.length === 0 ? (
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <h3 className="font-medium">Tổng quan</h3>
                                        <p className="text-sm text-muted-foreground">
                                            Đây là phân tích tổng quan về file "{file?.originalName}" của bạn.
                                            File này có {(file?.analysis?.rowCount || 0).toLocaleString()} dòng và {file?.analysis?.columnCount || 0} cột.
                                        </p>
                                    </div>

                                    <div className="space-y-4">
                                        <h3 className="font-medium">Phân tích chính</h3>
                                        <Card className="bg-muted/50">
                                            <CardContent className="p-4">
                                                <p className="text-center text-sm text-muted-foreground">
                                                    Để nhận phân tích sâu hơn, hãy hỏi chatbot:
                                                </p>
                                                <div className="mt-3 space-y-2">
                                                    <Button
                                                        variant="outline"
                                                        className="w-full justify-start text-left"
                                                        onClick={() => setActiveTab('chat')}
                                                    >
                                                        "Phân tích tương quan giữa các cột"
                                                    </Button>
                                                    <Button
                                                        variant="outline"
                                                        className="w-full justify-start text-left"
                                                        onClick={() => setActiveTab('chat')}
                                                    >
                                                        "Tìm các xu hướng trong dữ liệu"
                                                    </Button>
                                                    <Button
                                                        variant="outline"
                                                        className="w-full justify-start text-left"
                                                        onClick={() => setActiveTab('chat')}
                                                    >
                                                        "Tóm tắt insights chính từ dữ liệu"
                                                    </Button>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <h3 className="font-medium">Tổng quan</h3>
                                        <p className="text-sm text-muted-foreground">
                                            Đây là phân tích tổng quan về file "{file?.originalName}" của bạn.
                                            File này có {(file?.analysis?.rowCount || 0).toLocaleString()} dòng và {file?.analysis?.columnCount || 0} cột.
                                        </p>
                                    </div>

                                    <div className="space-y-4">
                                        <h3 className="font-medium">Insights phát hiện được</h3>
                                        {Array.isArray(insights) && insights.length > 0 && insights.filter((insight): insight is InsightData => insight !== null).map((insight: InsightData, index: number) => {
                                            const { id, title, content, columns, importance } = insight;

                                            return (
                                                <Card key={id || `insight-${index}`} className="overflow-hidden">
                                                    <CardHeader className="pb-3">
                                                        <div className="flex items-center gap-2">
                                                            <div className={`w-2 h-2 rounded-full ${getInsightImportanceColor(importance || 0)}`}></div>
                                                            <CardTitle className="text-base">
                                                                {title?.trim() || 'Insight không có tiêu đề'}
                                                            </CardTitle>
                                                        </div>
                                                    </CardHeader>

                                                    <CardContent className="pt-0">
                                                        <p className="text-sm">
                                                            {content?.trim() || ''}
                                                        </p>

                                                        {Array.isArray(columns) && columns.length > 0 && (
                                                            <div className="mt-2 flex flex-wrap gap-1">
                                                                {columns.map((column, idx) => (
                                                                    <span
                                                                        key={idx}
                                                                        className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700"
                                                                    >
                                                                        {column}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </CardContent>
                                                </Card>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Correlation Tab */}
                <TabsContent value="correlation">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center justify-between">
                                <span>Phân tích tương quan</span>
                                <div className="flex items-center gap-2">
                                    <label className="text-sm font-normal">Ngưỡng tương quan:</label>
                                    <select
                                        className="text-sm rounded border p-1"
                                        value={correlationThreshold}
                                        onChange={e => setCorrelationThreshold(parseFloat(e.target.value))}
                                    >
                                        <option value="0.1">0.1</option>
                                        <option value="0.3">0.3</option>
                                        <option value="0.5">0.5</option>
                                        <option value="0.7">0.7</option>
                                        <option value="0.9">0.9</option>
                                    </select>
                                    <Button size="sm" onClick={() => setShowCorrelation(true)} disabled={showCorrelation && isCorrelationLoading}>
                                        {isCorrelationLoading ? (
                                            <RefreshCw className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <RefreshCw className="h-4 w-4" />
                                        )}
                                        Phân tích
                                    </Button>
                                </div>
                            </CardTitle>
                            <CardDescription>
                                Phân tích mối quan hệ giữa các biến trong dữ liệu
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isCorrelationLoading ? (
                                <div className="space-y-4">
                                    <Skeleton className="h-[400px] w-full" />
                                </div>
                            ) : !correlationData ? (
                                <div className="flex flex-col items-center justify-center h-[400px] text-center">
                                    <Network className="h-12 w-12 text-muted-foreground mb-4" />
                                    <h3 className="text-lg font-medium">Chưa có dữ liệu tương quan</h3>
                                    <p className="text-sm text-muted-foreground max-w-md mt-2">
                                        Nhấn nút "Phân tích" để bắt đầu phân tích tương quan giữa các biến trong dữ liệu.
                                    </p>
                                    <Button className="mt-4" onClick={() => setShowCorrelation(true)}>
                                        <RefreshCw className="mr-2 h-4 w-4" /> Phân tích tương quan
                                    </Button>
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {/* Correlation Heatmap */}
                                    <div className="h-[400px]">
                                        {correlationData.visualization && (
                                            <ChartRenderer
                                                visualization={{
                                                    data: correlationData.visualization.data,
                                                    type: ChartType.HEATMAP,
                                                    title: "Heatmap tương quan",
                                                    description: correlationData.visualization.description,
                                                    config: correlationData.visualization.config
                                                }}
                                            />
                                            // <ChartRenderer
                                            //     data={correlationData.visualization}
                                            //     type={ChartType.HEATMAP}
                                            //     title="Heatmap tương quan"
                                            // />
                                        )}
                                    </div>

                                    {/* Strong Correlations */}
                                    {correlationData.strongCorrelations && correlationData.strongCorrelations.length > 0 && (
                                        <div className="mt-6 border-t pt-4">
                                            <h3 className="text-lg font-medium mb-3">Các tương quan mạnh</h3>
                                            <div className="grid gap-2">
                                                {correlationData.strongCorrelations.map((corr, index) => (
                                                    <div
                                                        key={index}
                                                        className={`p-3 rounded-md border flex items-center justify-between ${Math.abs(corr.correlation) > 0.7 ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                                                            }`}
                                                    >
                                                        <div className="flex flex-col">
                                                            <span className="font-medium">{corr.column1} ↔ {corr.column2}</span>
                                                            <span className="text-sm text-muted-foreground">
                                                                {corr.correlation > 0 ? 'Tương quan thuận' : 'Tương quan nghịch'}
                                                            </span>
                                                        </div>
                                                        <div className={`px-2 py-1 rounded text-white font-medium ${Math.abs(corr.correlation) > 0.7 ? 'bg-blue-500' : 'bg-gray-500'
                                                            }`}>
                                                            {corr.correlation.toFixed(2)}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Correlation Insights */}
                                    {correlationData.insights && correlationData.insights.length > 0 && (
                                        <div className="mt-6 border-t pt-4">
                                            <h3 className="text-lg font-medium mb-3">Insights từ phân tích tương quan</h3>
                                            <div className="space-y-3">
                                                {correlationData.insights.map((insight, index) => (
                                                    <Card key={index}>
                                                        <CardHeader className="pb-2">
                                                            <CardTitle className="text-base">{insight.title}</CardTitle>
                                                        </CardHeader>
                                                        <CardContent className="pt-0">
                                                            <p className="text-sm">{insight.content}</p>
                                                        </CardContent>
                                                    </Card>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Time Series Tab */}
                <TabsContent value="timeSeries">
                    <Card>
                        <CardHeader>
                            <CardTitle>Phân tích chuỗi thời gian</CardTitle>
                            <CardDescription>
                                Phân tích và dự báo chuỗi thời gian từ dữ liệu của bạn
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {!file?.columns ? (
                                <div className="h-[400px] flex items-center justify-center">
                                    <Skeleton className="h-[400px] w-full" />
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="space-y-4">
                                            <div className="space-y-2">
                                                <label className="text-sm font-medium">Cột ngày/thời gian:</label>
                                                <select
                                                    className="w-full p-2 border rounded-md"
                                                    value={timeSeriesConfig.dateColumn}
                                                    onChange={(e) => setTimeSeriesConfig({
                                                        ...timeSeriesConfig,
                                                        dateColumn: e.target.value
                                                    })}
                                                >
                                                    <option value="">-- Chọn cột ngày/thời gian --</option>
                                                    {file.columns
                                                        .filter(col => col.type === 'date' || col.type === 'datetime' || col.name.toLowerCase().includes('date') || col.name.toLowerCase().includes('time'))
                                                        .map(col => (
                                                            <option key={col.name} value={col.name}>{col.name}</option>
                                                        ))
                                                    }
                                                </select>
                                            </div>
                                            <div className="space-y-2">
                                                <label className="text-sm font-medium">Cột giá trị:</label>
                                                <select
                                                    className="w-full p-2 border rounded-md"
                                                    value={timeSeriesConfig.valueColumn}
                                                    onChange={(e) => setTimeSeriesConfig({
                                                        ...timeSeriesConfig,
                                                        valueColumn: e.target.value
                                                    })}
                                                >
                                                    <option value="">-- Chọn cột giá trị --</option>
                                                    {file.columns
                                                        .filter(col => col.type === 'number' || col.type === 'integer' || col.type === 'float')
                                                        .map(col => (
                                                            <option key={col.name} value={col.name}>{col.name}</option>
                                                        ))
                                                    }
                                                </select>
                                            </div>
                                            <div className="space-y-2">
                                                <label className="text-sm font-medium">Số kỳ dự báo:</label>
                                                <input
                                                    type="number"
                                                    className="w-full p-2 border rounded-md"
                                                    min="1"
                                                    max="50"
                                                    value={timeSeriesConfig.forecastPeriods}
                                                    onChange={(e) => setTimeSeriesConfig({
                                                        ...timeSeriesConfig,
                                                        forecastPeriods: parseInt(e.target.value)
                                                    })}
                                                />
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    id="forecast-checkbox"
                                                    checked={timeSeriesConfig.forecast}
                                                    onChange={(e) => setTimeSeriesConfig({
                                                        ...timeSeriesConfig,
                                                        forecast: e.target.checked
                                                    })}
                                                />
                                                <label htmlFor="forecast-checkbox" className="text-sm font-medium">
                                                    Tạo dự báo
                                                </label>
                                            </div>
                                            <Button
                                                className="w-full"
                                                disabled={!timeSeriesConfig.dateColumn || !timeSeriesConfig.valueColumn || showTimeSeriesAnalysis}
                                                onClick={() => setShowTimeSeriesAnalysis(true)}
                                            >
                                                Phân tích chuỗi thời gian
                                            </Button>
                                        </div>
                                        <div className="border rounded-md p-4 bg-gray-50">
                                            <h3 className="text-sm font-medium mb-2">Hướng dẫn phân tích chuỗi thời gian</h3>
                                            <ul className="text-sm space-y-2 text-muted-foreground">
                                                <li>• Chọn một cột ngày/thời gian (ví dụ: ngày, tháng, quý...)</li>
                                                <li>• Chọn một cột giá trị số (ví dụ: doanh thu, số lượng...)</li>
                                                <li>• Điều chỉnh số kỳ dự báo nếu cần</li>
                                                <li>• Nhấn "Phân tích chuỗi thời gian" để thực hiện phân tích</li>
                                            </ul>
                                        </div>
                                    </div>

                                    {/* Time Series Results */}
                                    {showTimeSeriesAnalysis && (
                                        <div className="mt-8 pt-4 border-t">
                                            <h3 className="text-lg font-medium mb-4">Kết quả phân tích</h3>

                                            {/* Loading state */}
                                            {!timeSeriesConfig.dateColumn || !timeSeriesConfig.valueColumn ? (
                                                <Card className="bg-gray-50">
                                                    <CardContent className="p-6 text-center">
                                                        <p className="text-muted-foreground">Vui lòng chọn cột ngày/thời gian và cột giá trị để tiếp tục.</p>
                                                    </CardContent>
                                                </Card>
                                            ) : isTimeSeriesLoading ? (
                                                <div className="space-y-4">
                                                    <Skeleton className="h-[300px] w-full" />
                                                    <div className="grid grid-cols-2 gap-4">
                                                        <Skeleton className="h-24 w-full" />
                                                        <Skeleton className="h-24 w-full" />
                                                    </div>
                                                </div>
                                            ) : !timeSeriesData ? (
                                                <Card>
                                                    <CardContent className="p-6 text-center">
                                                        <LineChart className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                                                        <p>Chưa có dữ liệu phân tích</p>
                                                        <Button className="mt-4" onClick={() => setShowTimeSeriesAnalysis(true)}>
                                                            Bắt đầu phân tích
                                                        </Button>
                                                    </CardContent>
                                                </Card>
                                            ) : (
                                                <div className="space-y-4">
                                                    <Card>
                                                        <CardContent className="pt-6">
                                                            <div className="h-[300px]">
                                                                {/* Use actual data from timeSeriesData */}
                                                                {timeSeriesData.visualization && (
                                                                    <ChartRenderer
                                                                        visualization={{
                                                                            data: timeSeriesData.visualization.data || [],
                                                                            type: ChartType.LINE,
                                                                            title: `Phân tích chuỗi thời gian: ${timeSeriesConfig.valueColumn} theo ${timeSeriesConfig.dateColumn}`,
                                                                            description: timeSeriesData.visualization.description || ''
                                                                        }}
                                                                    />
                                                                )}
                                                            </div>
                                                        </CardContent>
                                                    </Card>

                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                        <Card>
                                                            <CardHeader className="pb-2">
                                                                <CardTitle className="text-base">Thông tin chuỗi thời gian</CardTitle>
                                                            </CardHeader>
                                                            <CardContent>
                                                                <ul className="space-y-1 text-sm">
                                                                    <li className="flex justify-between">
                                                                        <span className="text-muted-foreground">Cột thời gian:</span>
                                                                        <span className="font-medium">{timeSeriesConfig.dateColumn}</span>
                                                                    </li>
                                                                    <li className="flex justify-between">
                                                                        <span className="text-muted-foreground">Cột giá trị:</span>
                                                                        <span className="font-medium">{timeSeriesConfig.valueColumn}</span>
                                                                    </li>
                                                                    {timeSeriesData.timeSeriesInfo && (
                                                                        <>
                                                                            <li className="flex justify-between">
                                                                                <span className="text-muted-foreground">Số điểm dữ liệu:</span>
                                                                                <span className="font-medium">{timeSeriesData.timeSeriesInfo.dataPoints || 'N/A'}</span>
                                                                            </li>
                                                                            <li className="flex justify-between">
                                                                                <span className="text-muted-foreground">Từ:</span>
                                                                                <span className="font-medium">{timeSeriesData.timeSeriesInfo.startDate || 'N/A'}</span>
                                                                            </li>
                                                                            <li className="flex justify-between">
                                                                                <span className="text-muted-foreground">Đến:</span>
                                                                                <span className="font-medium">{timeSeriesData.timeSeriesInfo.endDate || 'N/A'}</span>
                                                                            </li>
                                                                            <li className="flex justify-between">
                                                                                <span className="text-muted-foreground">Tần suất:</span>
                                                                                <span className="font-medium">{timeSeriesData.timeSeriesInfo.frequency || 'N/A'}</span>
                                                                            </li>
                                                                            <li className="flex justify-between">
                                                                                <span className="text-muted-foreground">Có xu hướng:</span>
                                                                                <span className="font-medium">{timeSeriesData.timeSeriesInfo.hasTrend ? 'Có' : 'Không'}</span>
                                                                            </li>
                                                                            <li className="flex justify-between">
                                                                                <span className="text-muted-foreground">Có tính mùa vụ:</span>
                                                                                <span className="font-medium">{timeSeriesData.timeSeriesInfo.hasSeasonality ? 'Có' : 'Không'}</span>
                                                                            </li>
                                                                        </>
                                                                    )}
                                                                </ul>
                                                            </CardContent>
                                                        </Card>

                                                        <Card>
                                                            <CardHeader className="pb-2">
                                                                <CardTitle className="text-base">
                                                                    {timeSeriesData.forecast ? 'Kết quả dự báo' : 'Phân tích thống kê'}
                                                                </CardTitle>
                                                            </CardHeader>
                                                            <CardContent>
                                                                {timeSeriesData.forecast ? (
                                                                    <ul className="space-y-1 text-sm">
                                                                        <li className="flex justify-between">
                                                                            <span className="text-muted-foreground">Kỳ dự báo:</span>
                                                                            <span className="font-medium">{timeSeriesData.forecast.horizon || timeSeriesConfig.forecastPeriods}</span>
                                                                        </li>
                                                                        {timeSeriesData.metrics && Object.entries(timeSeriesData.metrics).map(([key, value], idx) => (
                                                                            <li key={idx} className="flex justify-between">
                                                                                <span className="text-muted-foreground">{key.toUpperCase()}:</span>
                                                                                <span className="font-medium">{typeof value === 'number' ? value.toFixed(4) : value}</span>
                                                                            </li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <p className="text-center text-muted-foreground text-sm mt-4">
                                                                        Không có dữ liệu dự báo
                                                                    </p>
                                                                )}
                                                            </CardContent>
                                                        </Card>
                                                    </div>

                                                    {/* Display insights from time series if available */}
                                                    {timeSeriesData.insights && timeSeriesData.insights.length > 0 && (
                                                        <Card>
                                                            <CardHeader className="pb-2">
                                                                <CardTitle className="text-base">Insights từ chuỗi thời gian</CardTitle>
                                                            </CardHeader>
                                                            <CardContent>
                                                                <ul className="space-y-2">
                                                                    {timeSeriesData.insights.map((insight, idx) => (
                                                                        <li key={idx} className="text-sm">
                                                                            • {insight}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </CardContent>
                                                        </Card>
                                                    )}

                                                    {/* Display forecast data if forecast is available */}
                                                    {timeSeriesData.forecast && timeSeriesData.forecast.forecastData && (
                                                        <Card>
                                                            <CardHeader className="pb-2">
                                                                <CardTitle className="text-base">Dữ liệu dự báo</CardTitle>
                                                            </CardHeader>
                                                            <CardContent>
                                                                <div className="max-h-[200px] overflow-y-auto">
                                                                    <table className="min-w-full divide-y divide-gray-200">
                                                                        <thead className="bg-gray-50">
                                                                            <tr>
                                                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                                    Thời gian
                                                                                </th>
                                                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                                    Dự báo
                                                                                </th>
                                                                                {timeSeriesData.forecast.predictionIntervals && (
                                                                                    <>
                                                                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                                            Giới hạn dưới
                                                                                        </th>
                                                                                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                                            Giới hạn trên
                                                                                        </th>
                                                                                    </>
                                                                                )}
                                                                            </tr>
                                                                        </thead>
                                                                        <tbody className="bg-white divide-y divide-gray-200">
                                                                            {timeSeriesData.forecast.forecastData.map((point, idx) => (
                                                                                <tr key={idx} className="hover:bg-gray-50">
                                                                                    <td className="px-3 py-2 whitespace-nowrap text-xs">
                                                                                        {point.date}
                                                                                    </td>
                                                                                    <td className="px-3 py-2 whitespace-nowrap text-xs font-medium">
                                                                                        {point.value.toFixed(2)}
                                                                                    </td>
                                                                                    {timeSeriesData.forecast?.predictionIntervals && (
                                                                                        <>
                                                                                            <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-500">
                                                                                                {point.lower?.toFixed(2) || 'N/A'}
                                                                                            </td>
                                                                                            <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-500">
                                                                                                {point.upper?.toFixed(2) || 'N/A'}
                                                                                            </td>
                                                                                        </>
                                                                                    )}
                                                                                </tr>
                                                                            ))}
                                                                        </tbody>
                                                                    </table>
                                                                </div>
                                                            </CardContent>
                                                        </Card>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="chat" className="h-[calc(100vh-16rem)]">
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

            {/* Expanded Chart Dialog */}
            <Dialog open={expandedChart !== null} onOpenChange={() => setExpandedChart(null)}>
                <DialogContent className="max-w-4xl">
                    <DialogHeader>
                        <DialogTitle>{getExpandedChart()?.title}</DialogTitle>
                        <DialogDescription>
                            {getExpandedChart()?.description}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="h-[500px] mt-2">
                        {getExpandedChart() && (
                            <ChartRenderer
                                visualization={getExpandedChart() as VisualizationData}
                            />
                        )}
                    </div>

                    {getExpandedChart()?.insight && (
                        <div className="border-t pt-4 mt-2">
                            <div className="flex items-center gap-1 mb-1 text-sm font-medium text-primary">
                                <Info className="h-4 w-4" /> INSIGHT
                            </div>
                            <p className="text-sm text-muted-foreground">{getExpandedChart()?.insight}</p>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* Create Chart Dialog */}
            <Dialog open={showDialog} onOpenChange={setShowDialog}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Tạo biểu đồ mới</DialogTitle>
                        <DialogDescription>
                            Tạo và tùy chỉnh biểu đồ từ dữ liệu của bạn
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Loại biểu đồ</label>
                                <select
                                    className="w-full p-2 border rounded-md"
                                    value={chartConfig.chartType}
                                    onChange={(e) => setChartConfig({
                                        ...chartConfig,
                                        chartType: e.target.value as ChartType
                                    })}
                                >
                                    <option value={ChartType.BAR}>Biểu đồ cột</option>
                                    <option value={ChartType.LINE}>Biểu đồ đường</option>
                                    <option value={ChartType.PIE}>Biểu đồ tròn</option>
                                    <option value={ChartType.SCATTER}>Biểu đồ phân tán</option>
                                    <option value={ChartType.AREA}>Biểu đồ vùng</option>
                                    <option value={ChartType.HEATMAP}>Bản đồ nhiệt</option>
                                    <option value={ChartType.HISTOGRAM}>Biểu đồ histogram</option>
                                </select>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium">Chọn các cột</label>
                                <div className="border rounded-md p-2 max-h-[200px] overflow-y-auto">
                                    {file?.columns && file.columns.map((col, index) => (
                                        <label key={index} className="flex items-center gap-2 py-1 px-2 hover:bg-gray-50 rounded">
                                            <input
                                                type="checkbox"
                                                value={col.name}
                                                onChange={(e) => {
                                                    const isChecked = e.target.checked;
                                                    setChartConfig(prev => {
                                                        if (isChecked) {
                                                            return {
                                                                ...prev,
                                                                columns: [...prev.columns, col.name]
                                                            };
                                                        } else {
                                                            return {
                                                                ...prev,
                                                                columns: prev.columns.filter(c => c !== col.name)
                                                            };
                                                        }
                                                    });
                                                }}
                                            />
                                            <span className="text-sm">
                                                {col.name}
                                                <span className="text-xs text-muted-foreground ml-1">
                                                    ({col.type})
                                                </span>
                                            </span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium">Tiêu đề biểu đồ</label>
                                <input
                                    type="text"
                                    className="w-full p-2 border rounded-md"
                                    placeholder="Nhập tiêu đề biểu đồ"
                                    value={chartConfig.title}
                                    onChange={(e) => setChartConfig({
                                        ...chartConfig,
                                        title: e.target.value
                                    })}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium">Mô tả (tùy chọn)</label>
                                <textarea
                                    className="w-full p-2 border rounded-md resize-none"
                                    rows={2}
                                    placeholder="Mô tả ngắn về biểu đồ này"
                                    value={chartConfig.description}
                                    onChange={(e) => setChartConfig({
                                        ...chartConfig,
                                        description: e.target.value
                                    })}
                                />
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="border rounded-md p-4 bg-gray-50 h-full">
                                <h3 className="text-sm font-medium mb-2">Xem trước cấu hình</h3>
                                <div className="space-y-2 text-sm">
                                    <div className="bg-white p-3 rounded border">
                                        <p className="font-medium">Loại biểu đồ:</p>
                                        <p className="text-muted-foreground">{chartConfig.chartType}</p>
                                    </div>

                                    <div className="bg-white p-3 rounded border">
                                        <p className="font-medium">Cột dữ liệu ({chartConfig.columns.length}):</p>
                                        <div className="flex flex-wrap gap-1 mt-1">
                                            {chartConfig.columns.length === 0 ? (
                                                <p className="text-muted-foreground text-xs">Chưa chọn cột nào</p>
                                            ) : (
                                                chartConfig.columns.map((col, idx) => (
                                                    <span
                                                        key={idx}
                                                        className="inline-flex text-xs bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded"
                                                    >
                                                        {col}
                                                    </span>
                                                ))
                                            )}
                                        </div>
                                    </div>

                                    <div className="bg-white p-3 rounded border">
                                        <p className="font-medium">Tiêu đề:</p>
                                        <p className="text-muted-foreground">
                                            {chartConfig.title || "(Chưa đặt tiêu đề)"}
                                        </p>
                                    </div>
                                </div>

                                <div className="mt-4 pt-3 border-t">
                                    <p className="text-sm text-muted-foreground mb-2">
                                        Nếu không chắc chắn loại biểu đồ nào phù hợp, hãy dùng tính năng Chat với dữ liệu:
                                    </p>
                                    <Button
                                        variant="outline"
                                        className="w-full"
                                        onClick={() => {
                                            setShowDialog(false);
                                            setActiveTab('chat');
                                        }}
                                    >
                                        <MessageSquare className="mr-2 h-4 w-4" /> Chat với dữ liệu
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <DialogFooter className="flex items-center justify-between">
                        <div className="flex items-center">
                            <Button
                                variant="ghost"
                                onClick={() => {
                                    // Reset chart config
                                    setChartConfig({
                                        chartType: ChartType.BAR,
                                        columns: [],
                                        title: '',
                                        description: ''
                                    });
                                }}
                            >
                                Đặt lại
                            </Button>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" onClick={() => setShowDialog(false)}>
                                Hủy
                            </Button>
                        </div>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Progress Dialog */}
            <Dialog open={showProgress} onOpenChange={(open) => open ? null : setShowProgress(false)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Đang phân tích dữ liệu</DialogTitle>
                    </DialogHeader>
                    <div className="py-4 space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-sm">{status || analysisStatus}</span>
                            <span className="text-sm font-medium">{Math.round(analysisProgress)}%</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary rounded-full transition-all"
                                style={{ width: `${analysisProgress}%` }}
                            ></div>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Quá trình này có thể mất vài phút tùy thuộc vào kích thước và độ phức tạp của dữ liệu.
                        </p>
                    </div>
                </DialogContent>
            </Dialog>

            {/* New Chart Preview Dialog */}
            <Dialog open={newChartDialog} onOpenChange={setNewChartDialog}>
                <DialogContent className="max-w-4xl">
                    <DialogHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <DialogTitle className="text-xl font-bold">
                                    {newChartData?.title || "Biểu đồ mới"}
                                </DialogTitle>
                                <DialogDescription className="mt-1">
                                    {newChartData?.description || "Biểu đồ được tạo từ dữ liệu của bạn"}
                                </DialogDescription>
                            </div>
                            {newChartData?.type && (
                                <div className="flex items-center gap-2">
                                    <Badge
                                        variant="outline"
                                        className="flex items-center gap-1.5 px-2.5 py-1"
                                    >
                                        {newChartData.type === ChartType.BAR && <BarChart2 className="h-4 w-4" />}
                                        {newChartData.type === ChartType.LINE && <LineChart className="h-4 w-4" />}
                                        {newChartData.type === ChartType.PIE && <PieChart className="h-4 w-4" />}
                                        {newChartData.type === ChartType.SCATTER && <ScatterChart className="h-4 w-4" />}
                                        <span>
                                            {newChartData.type === ChartType.BAR && "Biểu đồ cột"}
                                            {newChartData.type === ChartType.LINE && "Biểu đồ đường"}
                                            {newChartData.type === ChartType.PIE && "Biểu đồ tròn"}
                                            {newChartData.type === ChartType.SCATTER && "Biểu đồ phân tán"}
                                            {newChartData.type === ChartType.AREA && "Biểu đồ vùng"}
                                            {newChartData.type === ChartType.HEATMAP && "Bản đồ nhiệt"}
                                            {newChartData.type === ChartType.BOX && "Biểu đồ hộp"}
                                            {!["BAR", "LINE", "PIE", "SCATTER", "AREA", "HEATMAP", "BOX"].includes(newChartData.type as string) &&
                                                `${newChartData.type}`}
                                        </span>
                                    </Badge>
                                </div>
                            )}
                        </div>
                    </DialogHeader>

                    <div className="h-[400px] mt-4 border rounded-md p-4 bg-gray-50/50">
                        {newChartData && (
                            <ChartRenderer visualization={newChartData} />
                        )}
                    </div>

                    {/* Thông tin chi tiết về biểu đồ */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                        {/* Cột bên trái */}
                        <div className="space-y-4">
                            {/* Insight */}
                            {newChartData?.insight && (
                                <div className="border rounded-md p-3 bg-muted/30">
                                    <div className="flex items-center gap-1.5 mb-2 text-sm font-medium text-primary">
                                        <Info className="h-4 w-4" /> Phân tích
                                    </div>
                                    <p className="text-sm text-muted-foreground">{newChartData.insight}</p>
                                </div>
                            )}

                            {/* Thông tin về dữ liệu */}
                            <div className="border rounded-md p-3">
                                <h3 className="text-sm font-medium mb-2 flex items-center gap-1.5">
                                    <Activity className="h-4 w-4" /> Thông tin dữ liệu
                                </h3>
                                <div className="grid grid-cols-2 gap-y-2 text-sm">
                                    <div className="flex flex-col">
                                        <span className="text-muted-foreground">Số điểm dữ liệu:</span>
                                        <span className="font-medium">{Array.isArray(newChartData?.data) ? newChartData?.data.length : 0}</span>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-muted-foreground">Thời gian tạo:</span>
                                        <span className="font-medium">{newChartData?.createdAt ? formatDate(new Date(newChartData.createdAt)) : 'Bây giờ'}</span>
                                    </div>
                                    {newChartData?.fileId && (
                                        <div className="flex flex-col col-span-2">
                                            <span className="text-muted-foreground">File ID:</span>
                                            <span className="font-medium truncate">{newChartData.fileId}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Cột bên phải */}
                        <div className="space-y-4">
                            {/* Cấu hình biểu đồ */}
                            <div className="border rounded-md p-3">
                                <h3 className="text-sm font-medium mb-2 flex items-center gap-1.5">
                                    <Settings className="h-4 w-4" /> Cấu hình biểu đồ
                                </h3>
                                <div className="grid grid-cols-1 gap-2 text-sm">
                                    {newChartData?.recommendedType && newChartData.recommendedType !== newChartData.type && (
                                        <div className="flex justify-between items-center">
                                            <span className="text-muted-foreground">Loại đề xuất:</span>
                                            <Badge variant="outline">
                                                {newChartData.recommendedType === ChartType.BAR && "Biểu đồ cột"}
                                                {newChartData.recommendedType === ChartType.LINE && "Biểu đồ đường"}
                                                {newChartData.recommendedType === ChartType.PIE && "Biểu đồ tròn"}
                                                {newChartData.recommendedType === ChartType.SCATTER && "Biểu đồ phân tán"}
                                                {newChartData.recommendedType === ChartType.AREA && "Biểu đồ vùng"}
                                                {!["BAR", "LINE", "PIE", "SCATTER", "AREA"].includes(newChartData.recommendedType as string) &&
                                                    `${newChartData.recommendedType}`}
                                            </Badge>
                                        </div>
                                    )}
                                    <div className="flex justify-between items-center">
                                        <span className="text-muted-foreground">Loại biểu đồ:</span>
                                        <Badge>
                                            {newChartData?.type === ChartType.BAR && "Biểu đồ cột"}
                                            {newChartData?.type === ChartType.LINE && "Biểu đồ đường"}
                                            {newChartData?.type === ChartType.PIE && "Biểu đồ tròn"}
                                            {newChartData?.type === ChartType.SCATTER && "Biểu đồ phân tán"}
                                            {newChartData?.type === ChartType.AREA && "Biểu đồ vùng"}
                                            {newChartData?.type === ChartType.HEATMAP && "Bản đồ nhiệt"}
                                            {newChartData?.type === ChartType.BOX && "Biểu đồ hộp"}
                                            {newChartData?.type && !["BAR", "LINE", "PIE", "SCATTER", "AREA", "HEATMAP", "BOX"].includes(newChartData.type as string) &&
                                                `${newChartData.type}`}
                                        </Badge>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-muted-foreground">Tùy chỉnh:</span>
                                        <Badge variant={newChartData?.isCustom ? "default" : "outline"}>
                                            {newChartData?.isCustom ? "Có" : "Mặc định"}
                                        </Badge>
                                    </div>
                                    {newChartData?.chartLibrary && (
                                        <div className="flex justify-between items-center">
                                            <span className="text-muted-foreground">Thư viện:</span>
                                            <Badge variant="outline">{newChartData.chartLibrary}</Badge>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Cột được sử dụng */}
                            {newChartData?.parameters?.columns && (
                                <div className="border rounded-md p-3">
                                    <h3 className="text-sm font-medium mb-2 flex items-center gap-1.5">
                                        <Table className="h-4 w-4" /> Cột được sử dụng
                                    </h3>
                                    <div className="flex flex-wrap gap-1 mt-1">
                                        {Array.isArray(newChartData.parameters.columns) && newChartData.parameters.columns.map((column: string, idx: number) => (
                                            <Badge
                                                key={idx}
                                                variant="secondary"
                                                className="px-2 py-1"
                                            >
                                                {column}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    <DialogFooter className="flex items-center justify-between mt-4 pt-4 border-t">
                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm" onClick={() => setNewChartDialog(false)}>
                                <X className="h-4 w-4 mr-1.5" /> Đóng
                            </Button>
                            <Button variant="outline" size="sm">
                                <Download className="h-4 w-4 mr-1.5" /> Tải xuống
                            </Button>
                            <Button variant="outline" size="sm">
                                <Share2 className="h-4 w-4 mr-1.5" /> Chia sẻ
                            </Button>
                        </div>
                        <div>
                            <Button onClick={() => {
                                setNewChartDialog(false);
                                // Scroll đến biểu đồ mới trong danh sách
                                setTimeout(() => {
                                    const chartElements = document.querySelectorAll('.chart-card');
                                    const lastChart = chartElements[chartElements.length - 1];
                                    if (lastChart) {
                                        lastChart.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    }
                                }, 100);
                            }}>
                                <Check className="h-4 w-4 mr-1.5" /> Xác nhận
                            </Button>
                        </div>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default AnalysisPage;