import { format } from 'date-fns';
import {
    BarChart2, Bot,
    Brain,
    Check,
    ChevronDown, ChevronUp,
    Copy, ExpandIcon,
    LineChartIcon, PieChartIcon, ScatterChart,
    UserIcon
} from 'lucide-react';
import { memo, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { InsightData, Message, VisualizationData } from '../../types';
import { cn } from '../../utils/cn';
import { Avatar, AvatarFallback } from '../ui/avatar';
import { Button } from '../ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle
} from '../ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import ChartRenderer from '../visualization/ChartRenderer';

interface ChatMessageProps {
    message: Message;
}

const ChatMessage = memo(({ message }: ChatMessageProps) => {
    const [copied, setCopied] = useState(false);
    const isUser = message.role === 'user';
    const hasVisualizations = message.metadata?.visualizations && message.metadata.visualizations.length > 0;
    const hasInsights = message.metadata?.insights && message.metadata.insights.length > 0;
    const [expandedVisualization, setExpandedVisualization] = useState<VisualizationData | null>(null);
    const [isArtifactCollapsed, setIsArtifactCollapsed] = useState(false);
    const [expandedStates, setExpandedStates] = useState<Record<string, boolean>>({});
    const [imageLinks, setImageLinks] = useState<string[]>([]);
    const [showReasoning, setShowReasoning] = useState(false);

    const [thinkingContent, setThinkingContent] = useState<string>("");
    const [hasThinking, setHasThinking] = useState(false);
    const [cleanedContent, setCleanedContent] = useState(message.content);

    useEffect(() => {
        if (!message.content) return;

        // Extract thinking tags from content
        const extractThinking = (content: string) => {
            const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/g;
            const matches = content.match(thinkingRegex);

            if (matches && matches.length > 0) {
                let extractedThinking = "";
                let cleanContent = content;

                for (const match of matches) {
                    // Extract content inside thinking tags
                    const thinkingContent = match.replace(/<thinking>|<\/thinking>/g, '');
                    extractedThinking += thinkingContent + "\n\n";

                    // Remove thinking tag from original content
                    cleanContent = cleanContent.replace(match, '');
                }

                setThinkingContent(extractedThinking.trim());
                setHasThinking(true);

                // Clean up the content
                cleanContent = cleanContent.trim();
                setCleanedContent(cleanContent);
            }
        };

        // Clean up role prefixes (Assistant:, User:) from content
        const cleanRolePrefixes = (content: string) => {
            // Remove role prefixes that might be generated
            let cleaned = content;

            // Common patterns
            const patterns = [
                /^Assistant:\s*/i,
                /^User:\s*/i,
                /^AI:\s*/i,
                /^Human:\s*/i,
                /\n\s*Assistant:\s*/gi,
                /\n\s*User:\s*/gi,
                /\n\s*AI:\s*/gi,
                /\n\s*Human:\s*/gi,
            ];

            patterns.forEach(pattern => {
                cleaned = cleaned.replace(pattern, isUser ? '' : '\n');
            });

            return cleaned;
        };

        // Process the message content
        extractThinking(message.content);

        // Also update the cleaned content with role prefixes removed
        setCleanedContent(prev => cleanRolePrefixes(prev));

    }, [message.content, isUser]);

    useEffect(() => {
        if (copied) {
            const timer = setTimeout(() => setCopied(false), 2000);
            return () => clearTimeout(timer);
        }
    }, [copied]);

    // Detect image links
    useEffect(() => {
        if (!cleanedContent) {
            setImageLinks([]);
            return;
        }

        const imgRegex = /<img.*?src=["'](.*?)["'].*?>/g;
        const matches = [...cleanedContent.matchAll(imgRegex)];
        const links = matches.map(match => match[1]);
        setImageLinks(links);
    }, [cleanedContent]);

    // Initialize expanded states for visualizations
    useEffect(() => {
        if (!hasVisualizations || !message.metadata?.visualizations) return;

        const states: Record<string, boolean> = {};
        message.metadata.visualizations.forEach((viz: VisualizationData, idx: number) => {
            const vizId = `viz-${viz.id || idx}`;
            if (!(vizId in expandedStates)) {
                states[vizId] = true;
            }
        });

        if (Object.keys(states).length > 0) {
            setExpandedStates(prev => ({
                ...prev,
                ...states
            }));
        }
    }, [hasVisualizations, message.metadata?.visualizations, expandedStates]);

    const handleCopy = () => {
        navigator.clipboard.writeText(cleanedContent);
        setCopied(true);
    };

    const formatDate = (dateString: string) => {
        return format(new Date(dateString), 'HH:mm, dd/MM/yyyy');
    };

    const toggleVizExpanded = (vizId: string) => {
        setExpandedStates(prev => ({
            ...prev,
            [vizId]: !prev[vizId]
        }));
    };

    const toggleAllArtifacts = () => {
        setIsArtifactCollapsed(!isArtifactCollapsed);

        if (isArtifactCollapsed && hasVisualizations) {
            const states: Record<string, boolean> = {};
            message.metadata!.visualizations!.forEach((viz: VisualizationData, idx: number) => {
                states[`viz-${viz.id || idx}`] = true;
            });
            setExpandedStates(states);
        }
    };

    // Existing helper for chart icons
    const getChartIcon = (type: string) => {
        const chartType = type.toLowerCase();
        if (chartType.includes('bar') || chartType.includes('column')) {
            return <BarChart2 className="h-4 w-4" />;
        } else if (chartType.includes('line') || chartType.includes('trend')) {
            return <LineChartIcon className="h-4 w-4" />;
        } else if (chartType.includes('pie') || chartType.includes('donut')) {
            return <PieChartIcon className="h-4 w-4" />;
        } else if (chartType.includes('scatter') || chartType.includes('bubble')) {
            return <ScatterChart className="h-4 w-4" />;
        }
        return <BarChart2 className="h-4 w-4" />;
    };


    const renderThinking = () => {
        if (!hasThinking) return null;

        return (
            <div className="mt-4 border-t pt-3">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center">
                        <Brain className="h-4 w-4 mr-2 text-purple-500" />
                        <h3 className="text-sm font-medium">AI's Thinking Process</h3>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowReasoning(!showReasoning)}
                        className="h-7 px-2 text-xs"
                    >
                        {showReasoning ? 'Hide' : 'Show'}
                        {showReasoning ? (
                            <ChevronUp className="ml-1 h-3 w-3" />
                        ) : (
                            <ChevronDown className="ml-1 h-3 w-3" />
                        )}
                    </Button>
                </div>

                {showReasoning && (
                    <div className="p-3 bg-muted/30 rounded-md text-sm text-muted-foreground">
                        <ReactMarkdown>{thinkingContent}</ReactMarkdown>
                    </div>
                )}
            </div>
        );
    };

    const renderVisualizations = () => {
        if (!hasVisualizations) return null;

        return (
            <div className="mt-4 space-y-4">
                {message.metadata!.visualizations!.map((visualization: VisualizationData, index: number) => {
                    const vizId = `viz-${visualization.id || index}`;
                    const isExpanded = expandedStates[vizId];

                    return (
                        <div
                            key={vizId}
                            className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden mb-3"
                        >
                            <div
                                className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/20"
                                onClick={() => toggleVizExpanded(vizId)}
                            >
                                <div className="flex items-center gap-2">
                                    {getChartIcon(visualization.type)}
                                    <span className="font-medium">{visualization.title || 'Chart'}</span>
                                </div>
                                <div className="flex items-center">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0 mr-1"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setExpandedVisualization(visualization);
                                        }}
                                    >
                                        <ExpandIcon className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleVizExpanded(vizId);
                                        }}
                                    >
                                        {isExpanded ? (
                                            <ChevronUp className="h-4 w-4" />
                                        ) : (
                                            <ChevronDown className="h-4 w-4" />
                                        )}
                                    </Button>
                                </div>
                            </div>

                            {isExpanded && (
                                <div className="p-3 pt-0 transition-all">
                                    <div className="h-64 w-full rounded-md bg-muted/40">
                                        <ChartRenderer
                                            visualization={visualization}
                                        />
                                    </div>
                                    {visualization.insight && (
                                        <div className="mt-3 text-sm text-muted-foreground p-2 bg-muted/20 rounded-md">
                                            <p className="font-medium mb-1">Insight:</p>
                                            <p>{visualization.insight}</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    const renderInsights = () => {
        if (!hasInsights) return null;

        return (
            <div className="mt-4 space-y-2">
                <h3 className="text-sm font-medium">Insights</h3>
                {message.metadata!.insights!.map((insight: InsightData, index: number) => (
                    <InsightCard
                        key={`insight-${index}`}
                        insight={insight}
                    />
                ))}
            </div>
        );
    };

    // Render detected images from text
    const renderImageLinks = () => {
        if (imageLinks.length === 0) return null;

        return (
            <div className="mt-4 space-y-2">
                <h3 className="text-sm font-medium">Images</h3>
                <div className="grid grid-cols-1 gap-4">
                    {imageLinks.map((link, index) => (
                        <Card key={`img-${index}`} className="overflow-hidden">
                            <CardContent className="p-2">
                                <div className="relative aspect-video bg-muted/40 rounded-md flex items-center justify-center">
                                    {/* Display "Image not available" since this is a reference */}
                                    <div className="text-muted-foreground text-sm text-center p-4">
                                        <p>Image not available:</p>
                                        <p className="text-xs break-all mt-2">{link}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        );
    };


    // Check if message has any artifacts (visualizations, insights, images)
    const hasArtifacts = hasVisualizations || hasInsights || imageLinks.length > 0;

    return (
        <div
            className={cn(
                'group flex w-full items-start gap-3 py-4',
                isUser && 'justify-end'
            )}
        >
            {!isUser && (
                <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground">
                        <Bot className="h-4 w-4" />
                    </AvatarFallback>
                </Avatar>
            )}

            <div className={cn('flex max-w-[80%] flex-col gap-2', isUser && 'items-end')}>
                <Card
                    className={cn(
                        'w-full shadow-sm',
                        isUser && 'bg-primary text-primary-foreground'
                    )}
                >
                    <CardHeader className="p-3 pb-0">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-medium">
                                {isUser ? 'You' : 'AI Assistant'}
                            </CardTitle>
                            <CardDescription
                                className={cn(
                                    'text-xs',
                                    isUser && 'text-primary-foreground/70'
                                )}
                            >
                                {formatDate(message.createdAt)}
                            </CardDescription>
                        </div>
                    </CardHeader>
                    <CardContent className="p-3 pt-2">
                        <div className={cn('prose prose-sm max-w-none', isUser && 'prose-invert')}>
                            <ReactMarkdown>{cleanedContent}</ReactMarkdown>
                        </div>

                        {/* NEW: Add thinking block if present */}
                        {hasThinking && renderThinking()}

                        {/* Existing artifacts container */}
                        {hasArtifacts && (
                            <div className={cn('mt-4 border-t pt-3', isUser && 'border-primary-foreground/20')}>
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-medium">
                                        {hasVisualizations ? 'Charts & Analysis' : 'Analysis Details'}
                                    </h3>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={toggleAllArtifacts}
                                        className="h-7 px-2 text-xs"
                                    >
                                        {isArtifactCollapsed ? 'Show' : 'Hide'}
                                        {isArtifactCollapsed ? (
                                            <ChevronDown className="ml-1 h-3 w-3" />
                                        ) : (
                                            <ChevronUp className="ml-1 h-3 w-3" />
                                        )}
                                    </Button>
                                </div>

                                {!isArtifactCollapsed && (
                                    <div className="space-y-4 transition-all">
                                        {hasVisualizations && renderVisualizations()}
                                        {hasInsights && renderInsights()}
                                        {imageLinks.length > 0 && renderImageLinks()}
                                    </div>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {!isUser && (
                    <div className="flex items-center opacity-0 transition-opacity group-hover:opacity-100">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={handleCopy}
                        >
                            {copied ? (
                                <Check className="h-4 w-4 text-green-500" />
                            ) : (
                                <Copy className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                )}
            </div>

            {isUser && (
                <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-muted">
                        <UserIcon className="h-4 w-4" />
                    </AvatarFallback>
                </Avatar>
            )}

            {/* Dialog for expanded visualization */}
            <Dialog
                open={expandedVisualization !== null}
                onOpenChange={() => setExpandedVisualization(null)}
            >
                <DialogContent className="max-w-4xl">
                    <DialogHeader>
                        <DialogTitle>{expandedVisualization?.title || 'Visualization'}</DialogTitle>
                    </DialogHeader>
                    <div className="h-[500px] my-6">
                        {expandedVisualization && (
                            <ChartRenderer
                                visualization={expandedVisualization}
                            />
                        )}
                    </div>
                    {expandedVisualization?.insight && (
                        <div className="mt-4 p-3 bg-muted/20 rounded-md">
                            <h4 className="text-sm font-semibold mb-1">Insight:</h4>
                            <p className="text-sm">{expandedVisualization.insight}</p>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
});

interface InsightCardProps {
    insight: InsightData;
}

const InsightCard = memo(({ insight }: InsightCardProps) => {
    return (
        <Card className="border-blue-100 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/20">
            <CardHeader className="p-3 pb-0">
                <CardTitle className="text-sm font-medium">{insight.title}</CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-2">
                <p className="text-sm">{insight.content}</p>
                {insight.columns && insight.columns.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                        {insight.columns.map((column, idx) => (
                            <span
                                key={idx}
                                className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                            >
                                {column}
                            </span>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
});

export default ChatMessage;