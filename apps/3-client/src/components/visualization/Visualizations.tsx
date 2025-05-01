// apps/client/src/components/visualization/Visualizations.tsx
import { useQuery } from "@tanstack/react-query";
import { BarChart2, Info, LineChart, Maximize2, PieChart, ScatterChart, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { getFileVisualizations } from "../../services/api";
import { ChartType, FileData, VisualizationData } from "../../types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle
} from "../ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Skeleton } from "../ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import ChartRenderer from "./ChartRenderer";

interface VisualizationsProps {
    fileData: FileData;
}

export default function Visualizations({ fileData }: VisualizationsProps) {
    const { user } = useAuth()
    if (!user || !user.id) {
        return <p>Please login first</p>
    }

    if (fileData.id === undefined || fileData.columns === undefined) {
        return <p>Please upload a file for visualization</p>
    }

    const [activeChart, setActiveChart] = useState<string | null>(null);
    const [expandedChart, setExpandedChart] = useState<number | null>(null);
    const [chartType, setChartType] = useState<Record<string, ChartType>>({});
    const [chartView, setChartView] = useState<"grid" | "list">("grid");

    // Using the getFileVisualizations API function from api.ts
    const { data: visualizationsData, isLoading, error } = useQuery<VisualizationData[]>({
        queryKey: ["visualizations", fileData.id],
        queryFn: async () => {
            // Option 1: Use getFileVisualizations to fetch existing visualizations
            return await getFileVisualizations(fileData.id, fileData.path);

            // Option 2: If you need to generate visualizations on-the-fly with the chat functionality
            // you could use processMessage
            /*
            const response = await processMessage({
                userId: user.id,
                query: `Create chart visualizations for ${fileData.columns!.join(', ')} columns`,
                fileId: fileData.id,
                filePath: fileData.id ? `files/${fileData.id}` : ''
            });
            return response.visualizations || [];
            */
        },
        enabled: !!fileData.id && !!fileData.path,
    });

    // Filter out null visualizations
    const visualizations = visualizationsData?.filter((viz) => viz !== null)

    // Initialize default chart type for each visualization
    useEffect(() => {
        if (visualizations && visualizations.length > 0) {
            const initialChartTypes: Record<string, ChartType> = {};
            visualizations.forEach((chart: VisualizationData, index: number) => {
                initialChartTypes[index.toString()] = chart.recommendedType as ChartType || chart.type as ChartType || ChartType.BAR;
            });
            setChartType(initialChartTypes);

            // Set the first chart as active if none is selected
            if (!activeChart) {
                setActiveChart("0");
            }
        }
    }, [visualizations, activeChart]);

    // Change chart type
    const handleChartTypeChange = (chartIndex: string, type: ChartType) => {
        setChartType((prev) => ({
            ...prev,
            [chartIndex]: type,
        }));
    };

    // Get the expanded chart data
    const getExpandedChart = (): VisualizationData | null => {
        if (expandedChart === null || !visualizations || expandedChart >= visualizations.length) {
            return null;
        }
        return visualizations[expandedChart];
    };

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <Skeleton className="h-10 w-48" />
                    <Skeleton className="h-10 w-24" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[...Array(4)].map((_, i) => (
                        <Card key={i} className="overflow-hidden">
                            <CardHeader className="pb-2">
                                <Skeleton className="h-4 w-3/4" />
                            </CardHeader>
                            <CardContent>
                                <Skeleton className="h-[200px] w-full" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <Card className="p-8 text-center">
                <CardContent>
                    <p className="text-muted-foreground mb-4">An error occurred while loading visualizations.</p>
                    <Button variant="outline" onClick={() => window.location.reload()}>
                        Try again
                    </Button>
                </CardContent>
            </Card>
        );
    }

    if (!visualizations || visualizations.length === 0) {
        return (
            <Card className="p-8 text-center">
                <CardContent>
                    <BarChart2 className="mx-auto h-12 w-12 text-muted-foreground" />
                    <p className="text-muted-foreground mb-4 mt-4">No charts have been created for this data yet.</p>
                    <p className="text-sm text-muted-foreground mb-6">
                        Try asking the chatbot to create charts or use the automatic analysis tools.
                    </p>
                    <Button>
                        Create Automatic Charts
                    </Button>
                </CardContent>
            </Card>
        );
    }

    const chartTypeIcons: Record<string, React.ReactNode> = {
        [ChartType.BAR]: <BarChart2 className="h-4 w-4" />,
        [ChartType.LINE]: <LineChart className="h-4 w-4" />,
        [ChartType.PIE]: <PieChart className="h-4 w-4" />,
        [ChartType.SCATTER]: <ScatterChart className="h-4 w-4" />,
        [ChartType.AREA]: <TrendingUp className="h-4 w-4" />,
    };

    const getChartTypeName = (type: string): string => {
        switch (type) {
            case ChartType.BAR: return "Bar";
            case ChartType.BAR_GROUPED: return "Bar Grouped"
            case ChartType.LINE: return "Line";
            case ChartType.PIE: return "Pie";
            case ChartType.SCATTER: return "Scatter";
            case ChartType.AREA: return "Area";
            case ChartType.HISTOGRAM: return "Histogram"
            case ChartType.GROUPED_HISTOGRAM: return "Grouped Histogram"
            case ChartType.HEATMAP: return "Heatmap";
            case ChartType.BOX: return "Box";
            case ChartType.BUBBLE: return "Bubble";
            case ChartType.RADAR: return "Radar";
            case ChartType.COMBO: return "Combo";
            case ChartType.DONUT: return "Donut";
            case ChartType.DIVERGING: return "Diverging";
            case ChartType.GANTT: return "Gantt";
            case ChartType.HEXBIN: return "Hexbin";
            case ChartType.NETWORK: return "Network";
            default: return "Other";
        }
    };

    // Create visualization object for ChartRenderer
    const createVisualizationObject = (chart: VisualizationData, index: number): VisualizationData => {
        return {
            ...chart,
            type: chartType[index.toString()] || chart.recommendedType as ChartType || chart.type as ChartType || ChartType.BAR
        };
    };

    return (
        <div className="space-y-4">
            {/* Controls */}
            <div className="flex flex-col sm:flex-row justify-between gap-4">
                <Tabs value={chartView} onValueChange={(v) => setChartView(v as "grid" | "list")}>
                    <TabsList className="grid w-full sm:w-auto grid-cols-2">
                        <TabsTrigger value="grid" className="flex items-center gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-layout-grid"><rect width="7" height="7" x="3" y="3" rx="1" /><rect width="7" height="7" x="14" y="3" rx="1" /><rect width="7" height="7" x="14" y="14" rx="1" /><rect width="7" height="7" x="3" y="14" rx="1" /></svg>
                            Grid
                        </TabsTrigger>
                        <TabsTrigger value="list" className="flex items-center gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-list"><line x1="8" x2="21" y1="6" y2="6" /><line x1="8" x2="21" y1="12" y2="12" /><line x1="8" x2="21" y1="18" y2="18" /><line x1="3" x2="3.01" y1="6" y2="6" /><line x1="3" x2="3.01" y1="12" y2="12" /><line x1="3" x2="3.01" y1="18" y2="18" /></svg>
                            List
                        </TabsTrigger>
                    </TabsList>
                </Tabs>

                {activeChart !== null && chartView === "list" && (
                    <div className="flex items-center gap-2">
                        <span className="text-sm">Chart Type:</span>
                        <Select
                            value={chartType[activeChart]}
                            onValueChange={(value) => handleChartTypeChange(activeChart, value as ChartType)}
                        >
                            <SelectTrigger className="w-[160px]">
                                <SelectValue placeholder="Select chart type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={ChartType.BAR} className="flex items-center gap-2">
                                    <BarChart2 className="h-4 w-4 mr-2" />Bar Chart
                                </SelectItem>
                                <SelectItem value={ChartType.LINE} className="flex items-center gap-2">
                                    <LineChart className="h-4 w-4 mr-2" />Line Chart
                                </SelectItem>
                                <SelectItem value={ChartType.PIE} className="flex items-center gap-2">
                                    <PieChart className="h-4 w-4 mr-2" />Pie Chart
                                </SelectItem>
                                <SelectItem value={ChartType.SCATTER} className="flex items-center gap-2">
                                    <ScatterChart className="h-4 w-4 mr-2" />Scatter Chart
                                </SelectItem>
                                <SelectItem value={ChartType.AREA} className="flex items-center gap-2">
                                    <TrendingUp className="h-4 w-4 mr-2" />Area Chart
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                )}
            </div>

            {/* Content based on view type */}
            <TabsContent value="grid" className="m-0 mt-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {visualizations.map((chart: VisualizationData, index: number) => (
                        <Card
                            key={index}
                            className="group overflow-hidden hover:shadow-md transition-shadow"
                        >
                            <CardHeader className="pb-2">
                                <div className="flex items-start justify-between">
                                    <CardTitle className="text-base">{chart.title}</CardTitle>
                                    <div className="flex items-center gap-1">
                                        <Badge variant="outline" className="hidden sm:flex items-center gap-1">
                                            {chartTypeIcons[chart.recommendedType as string || chart.type as string || ChartType.BAR] ||
                                                chartTypeIcons[ChartType.BAR]}
                                            <span className="text-xs">
                                                {getChartTypeName(chart.recommendedType as string || chart.type as string || ChartType.BAR)}
                                            </span>
                                        </Badge>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                                            onClick={() => setExpandedChart(index)}
                                        >
                                            <Maximize2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div
                                    className="h-full cursor-pointer"
                                    onClick={() => setExpandedChart(index)}
                                >
                                    <ChartRenderer
                                        visualization={createVisualizationObject(chart, index)}
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
            </TabsContent>

            <TabsContent value="list" className="m-0 mt-2">
                <div className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                        {visualizations.map((chart: VisualizationData, index: number) => (
                            <Button
                                key={index}
                                variant={activeChart === index.toString() ? "default" : "outline"}
                                className="flex items-center gap-2"
                                onClick={() => setActiveChart(index.toString())}
                            >
                                {chartTypeIcons[chart.recommendedType as string || chart.type as string || ChartType.BAR] ||
                                    chartTypeIcons[ChartType.BAR]}
                                <span className="hidden sm:inline">{chart.title}</span>
                                <span className="sm:hidden">Chart {index + 1}</span>
                            </Button>
                        ))}
                    </div>

                    {activeChart !== null && visualizations[parseInt(activeChart)] && (
                        <Card className="overflow-hidden">
                            <CardHeader>
                                <div className="flex items-start justify-between">
                                    <div>
                                        <CardTitle>{visualizations[parseInt(activeChart)].title}</CardTitle>
                                        {visualizations[parseInt(activeChart)].description && (
                                            <CardDescription>{visualizations[parseInt(activeChart)].description}</CardDescription>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Select
                                            value={chartType[activeChart]}
                                            onValueChange={(value) => handleChartTypeChange(activeChart, value as ChartType)}
                                        >
                                            <SelectTrigger className="w-[140px]">
                                                <SelectValue placeholder="Chart Type" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value={ChartType.BAR}>Bar Chart</SelectItem>
                                                <SelectItem value={ChartType.LINE}>Line Chart</SelectItem>
                                                <SelectItem value={ChartType.PIE}>Pie Chart</SelectItem>
                                                <SelectItem value={ChartType.SCATTER}>Scatter Chart</SelectItem>
                                                <SelectItem value={ChartType.AREA}>Area Chart</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            onClick={() => setExpandedChart(parseInt(activeChart))}
                                        >
                                            <Maximize2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="h-[400px]">
                                    <ChartRenderer
                                        visualization={createVisualizationObject(
                                            visualizations[parseInt(activeChart)],
                                            parseInt(activeChart)
                                        )}
                                    />
                                </div>
                            </CardContent>
                            {visualizations[parseInt(activeChart)].insight && (
                                <CardFooter className="border-t bg-muted/50">
                                    <div className="space-y-1 w-full">
                                        <div className="flex items-center gap-1 text-sm font-medium text-primary">
                                            <Info className="h-4 w-4" /> Analysis
                                        </div>
                                        <p className="text-sm text-muted-foreground">
                                            {visualizations[parseInt(activeChart)].insight}
                                        </p>
                                    </div>
                                </CardFooter>
                            )}
                        </Card>
                    )}
                </div>
            </TabsContent>

            {/* Expanded Chart Dialog */}
            <Dialog open={expandedChart !== null} onOpenChange={(open) => !open && setExpandedChart(null)}>
                <DialogContent className="max-w-4xl">
                    {getExpandedChart() && (
                        <>
                            <DialogHeader>
                                <DialogTitle>{getExpandedChart()?.title}</DialogTitle>
                                <DialogDescription>
                                    {getExpandedChart()?.description}
                                </DialogDescription>
                            </DialogHeader>

                            <div className="h-[500px] mt-2">
                                <ChartRenderer
                                    visualization={{
                                        ...getExpandedChart()!,
                                        type: chartType[expandedChart?.toString() || "0"] ||
                                            getExpandedChart()!.recommendedType as ChartType ||
                                            getExpandedChart()!.type as ChartType ||
                                            ChartType.BAR
                                    }}
                                />
                            </div>

                            {getExpandedChart()?.insight && (
                                <div className="border-t pt-4 mt-2">
                                    <div className="flex items-center gap-1 mb-1 text-sm font-medium text-primary">
                                        <Info className="h-4 w-4" /> INSIGHT
                                    </div>
                                    <p className="text-sm text-muted-foreground">{getExpandedChart()?.insight}</p>
                                </div>
                            )}
                        </>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}