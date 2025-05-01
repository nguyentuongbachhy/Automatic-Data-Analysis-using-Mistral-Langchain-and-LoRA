// apps/client/src/components/dashboard/ActivityFeed.tsx
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
    ArrowUpRight,
    BarChart2,
    FileText,
    FileUp,
    RefreshCw,
    Search
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getFiles } from '../../services/api';
import { FileData } from '../../types';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Skeleton } from '../ui/skeleton';


// Define activity interface
interface Activity {
    id: string;
    type: 'upload' | 'analyze' | 'search' | 'view';
    fileId?: string;
    fileName?: string;
    query?: string;
    timestamp: Date;
}

// Generate activities based on real file data
const generateActivities = (files: FileData[]): Activity[] => {
    const activities: Activity[] = [];

    // Create activities based on most recent files
    if (files && files.length > 0) {
        // Sort files by creation date (newest first)
        const sortedFiles = [...files].sort(
            (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
        );

        // Take at most 3 most recent files
        const recentFiles = sortedFiles.slice(0, 3);

        // Create file upload activities
        recentFiles.forEach(file => {
            activities.push({
                id: `upload-${file.id}`,
                type: 'upload',
                fileId: file.id,
                fileName: file.originalName,
                timestamp: new Date(file.createdAt),
            });

            // Add file analysis activity (simulate 1 minute after upload)
            const analyzeTime = new Date(file.createdAt);
            analyzeTime.setMinutes(analyzeTime.getMinutes() + 1);

            activities.push({
                id: `analyze-${file.id}`,
                type: 'analyze',
                fileId: file.id,
                fileName: file.originalName,
                timestamp: analyzeTime,
            });
        });
    }

    // Sort activities by timestamp (newest first)
    return activities.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
};

const ActivityFeed = () => {
    const navigate = useNavigate();
    const { data: files, isLoading, error } = useQuery({
        queryKey: ['files'],
        queryFn: getFiles,
    });

    // Generate activities from files fetched via API
    const activities = files ? generateActivities(files) : [];

    const getActivityIcon = (type: string) => {
        switch (type) {
            case 'upload':
                return <FileUp className="h-4 w-4 text-green-500" />;
            case 'analyze':
                return <BarChart2 className="h-4 w-4 text-blue-500" />;
            case 'search':
                return <Search className="h-4 w-4 text-purple-500" />;
            case 'view':
                return <FileText className="h-4 w-4 text-amber-500" />;
            default:
                return <RefreshCw className="h-4 w-4 text-gray-500" />;
        }
    };

    const formatTime = (date: Date) => {
        return format(date, 'HH:mm');
    };

    const getActivityText = (activity: Activity) => {
        switch (activity.type) {
            case 'upload':
                return `Tải lên ${activity.fileName}`;
            case 'analyze':
                return `Phân tích ${activity.fileName}`;
            case 'search':
                return `Tìm kiếm "${activity.query}"`;
            case 'view':
                return `Xem chi tiết ${activity.fileName}`;
            default:
                return 'Hoạt động không xác định';
        }
    };

    const handleClickActivity = (activity: Activity) => {
        if (activity.fileId) {
            navigate(`/files/${activity.fileId}`);
        }
    };

    if (isLoading) {
        return (
            <div className="space-y-4">
                {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex items-center gap-2">
                        <Skeleton className="h-8 w-8 rounded-full" />
                        <div className="space-y-2">
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-3 w-24" />
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-center">
                <p className="text-sm text-red-500">Error loading activity data</p>
                <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => window.location.reload()}
                >
                    <RefreshCw className="mr-2 h-3 w-3" />
                    Try again
                </Button>
            </div>
        );
    }

    if (!activities.length) {
        return (
            <div className="p-4 text-center">
                <p className="text-sm text-muted-foreground">No recent activity</p>
            </div>
        );
    }

    return (
        <ScrollArea className="h-[300px] pr-4">
            <div className="space-y-4">
                {activities.map((activity) => (
                    <div
                        key={activity.id}
                        className="flex items-start gap-3"
                    >
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted">
                            {getActivityIcon(activity.type)}
                        </div>
                        <div className="flex-1 space-y-1">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium">
                                    {getActivityText(activity)}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    {formatTime(activity.timestamp)}
                                </p>
                            </div>
                            {activity.fileId && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-2 text-xs"
                                    onClick={() => handleClickActivity(activity)}
                                >
                                    <span>Xem chi tiết</span>
                                    <ArrowUpRight className="ml-1 h-3 w-3" />
                                </Button>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </ScrollArea>
    );
};

export default ActivityFeed;