// apps/client/src/components/dashboard/RecentFiles.tsx
import { format } from 'date-fns';
import {
    ArrowUpRight,
    BarChart2,
    FileSpreadsheet,
    FileText,
    Table
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { FileData } from '../../types';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
    Card,
    CardContent
} from '../ui/card';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '../ui/dropdown-menu';

interface RecentFilesProps {
    files: FileData[];
    showAll?: boolean;
    isLoading?: boolean;
}

const RecentFiles = ({ files, showAll = false, isLoading = false }: RecentFilesProps) => {
    const navigate = useNavigate();

    // Ensure we have a valid array of files
    const safeFiles = Array.isArray(files) ? files : [];

    // Sort files by creation date (newest first)
    const sortedFiles = [...safeFiles].sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );

    // Get the number of files to display (all if showAll, otherwise max 5)
    const displayFiles = showAll ? sortedFiles : sortedFiles.slice(0, 5);

    if (isLoading) {
        return (
            <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                    <Card key={i} className="animate-pulse">
                        <CardContent className="p-4">
                            <div className="flex items-start space-x-4">
                                <div className="h-10 w-10 rounded bg-muted"></div>
                                <div className="space-y-2 flex-1">
                                    <div className="h-4 bg-muted rounded w-3/4"></div>
                                    <div className="h-3 bg-muted rounded w-1/2"></div>
                                    <div className="h-3 bg-muted rounded w-1/4"></div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        );
    }

    if (displayFiles.length === 0) {
        return (
            <div className="text-center py-8">
                <FileSpreadsheet className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">Không có file nào</h3>
                <p className="text-sm text-muted-foreground mt-2">
                    Tải lên file CSV hoặc Excel để bắt đầu phân tích
                </p>
            </div>
        );
    }

    const formatDate = (dateString: string | Date) => {
        return format(new Date(dateString), 'dd/MM/yyyy HH:mm');
    };

    const getFileIcon = (fileType: string) => {
        const type = fileType.toLowerCase();
        switch (type) {
            case 'csv':
                return <Table className="h-10 w-10 text-green-500" />;
            case 'xlsx':
            case 'xls':
                return <FileSpreadsheet className="h-10 w-10 text-blue-500" />;
            default:
                return <FileText className="h-10 w-10 text-gray-500" />;
        }
    };

    const getQualityColor = (score?: number) => {
        if (!score) return 'bg-gray-200 text-gray-700';
        if (score >= 80) return 'bg-green-100 text-green-800';
        if (score >= 60) return 'bg-yellow-100 text-yellow-800';
        return 'bg-red-100 text-red-800';
    };

    return (
        <div className="space-y-4">
            {displayFiles.map((file) => (
                <Card
                    key={file.id}
                    className="hover:bg-muted/50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/files/${file.id}`)}
                >
                    <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                            <div className="flex items-start space-x-4">
                                {getFileIcon(file.type)}
                                <div>
                                    <div className="font-medium line-clamp-1">{file.originalName}</div>
                                    <div className="flex items-center gap-2 mt-1">
                                        <Badge variant="outline" className="text-xs">
                                            {file.type ? file.type.toUpperCase() : "UNKNOWN"}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">
                                            {file.analysis ? file.analysis?.rowCount.toLocaleString() : 0} dòng
                                        </span>
                                        <span className="text-xs text-muted-foreground">
                                            {file.analysis ? file.analysis?.columnCount : 0} cột
                                        </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                        {formatDate(file.createdAt)}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                {file.qualityScore !== undefined && (
                                    <Badge className={getQualityColor(file.qualityScore)}>
                                        {file.qualityScore?.toFixed(0) || 0}%
                                    </Badge>
                                )}

                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8"
                                            onClick={(e) => e.stopPropagation()} // Prevent card click
                                        >
                                            <ArrowUpRight className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent className='bg-neutral-800' align="end">
                                        <DropdownMenuItem
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                navigate(`/files/${file.id}`);
                                            }}
                                        >
                                            <FileText className="mr-2 h-4 w-4" />
                                            <span>Xem chi tiết</span>
                                        </DropdownMenuItem>
                                        <DropdownMenuItem
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                navigate(`/analysis/${file.id}`);
                                            }}
                                        >
                                            <BarChart2 className="mr-2 h-4 w-4" />
                                            <span>Phân tích</span>
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
};

export default RecentFiles;