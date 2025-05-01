// apps/client/src/components/dashboard/StatsCards.tsx
import { Activity, BarChart2, Calendar, File } from 'lucide-react';
import { FileData } from '../../types';
import { cn } from '../../utils/cn';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';

interface StatsCardsProps {
    files: FileData[];
    isLoading?: boolean;
}

const StatsCards = ({ files, isLoading = false }: StatsCardsProps) => {
    // Calculate statistics
    const calculateStats = () => {
        // Make sure we have valid files array
        const safeFiles = Array.isArray(files) ? files : [];

        const totalFiles = safeFiles.length;

        const totalRows = safeFiles.reduce((sum, file) => sum + (file.analysis?.rowCount || 0), 0);

        // Filter out undefined/null quality scores and compute average
        const qualityScores = safeFiles
            .map(file => file.qualityScore)
            .filter((score): score is number =>
                score !== undefined && score !== null
            );

        const averageQuality = qualityScores.length > 0
            ? qualityScores.reduce((sum, score) => sum + score, 0) / qualityScores.length
            : 0;

        // Count files uploaded in the current month
        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();

        const filesThisMonth = safeFiles.filter(file => {
            const fileDate = new Date(file.createdAt);
            return fileDate.getMonth() === currentMonth && fileDate.getFullYear() === currentYear;
        }).length;

        return {
            totalFiles,
            totalRows,
            averageQuality,
            filesThisMonth,
        };
    };

    const stats = calculateStats();

    const items = [
        {
            title: 'Tổng số tệp',
            value: stats.totalFiles,
            description: 'Đã tải lên và phân tích',
            icon: File,
            color: 'text-blue-500',
        },
        {
            title: 'Tổng dòng dữ liệu',
            value: stats.totalRows.toLocaleString(),
            description: 'Tổng số dòng trong tất cả tệp',
            icon: Activity,
            color: 'text-green-500',
        },
        {
            title: 'Chất lượng trung bình',
            value: `${stats.averageQuality.toFixed(1)}%`,
            description: 'Điểm chất lượng dữ liệu',
            icon: BarChart2,
            color: 'text-yellow-500',
        },
        {
            title: 'Tệp trong tháng này',
            value: stats.filesThisMonth,
            description: 'Tải lên trong tháng hiện tại',
            icon: Calendar,
            color: 'text-purple-500',
        },
    ];

    if (isLoading) {
        return (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {Array(4).fill(0).map((_, index) => (
                    <Card key={index}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <Skeleton className="h-4 w-24" />
                            <Skeleton className="h-4 w-4 rounded-full" />
                        </CardHeader>
                        <CardContent>
                            <Skeleton className="h-7 w-20 mb-1" />
                            <Skeleton className="h-3 w-32" />
                        </CardContent>
                    </Card>
                ))}
            </div>
        );
    }

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {items.map((item, index) => (
                <Card key={index}>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            {item.title}
                        </CardTitle>
                        <item.icon className={cn("h-4 w-4", item.color)} />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{item.value}</div>
                        <p className="text-xs text-muted-foreground">
                            {item.description}
                        </p>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
};

export default StatsCards;