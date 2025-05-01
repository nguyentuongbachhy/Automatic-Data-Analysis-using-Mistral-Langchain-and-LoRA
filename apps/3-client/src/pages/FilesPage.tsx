// apps/client/src/pages/FilesPage.tsx
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';
import {
    BarChart2,
    Eye,
    FileSpreadsheet,
    FileText,
    Filter,
    Loader2,
    Plus,
    Search,
    SortAsc,
    SortDesc,
    Table,
    Trash2
} from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../components/ui/dialog';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Input } from '../components/ui/input';
import { Skeleton } from '../components/ui/skeleton';
import FileUploader from '../components/upload/FileUploader';
import { useDebounce } from '../hooks/use-debounce';
import { useToast } from '../hooks/use-toast';
import { deleteFile, getFiles } from '../services/api';
import { ApiResponse, FileData, ResponseStatus } from '../types';
import { formatFileSize } from '../utils/format';

const FilesPage = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { toast } = useToast();

    // States
    const [searchQuery, setSearchQuery] = useState('');
    const [showUploadDialog, setShowUploadDialog] = useState(false);
    const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
    const [sortBy, setSortBy] = useState<string>('createdAt');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    // Debounce search query
    const debouncedSearchQuery = useDebounce(searchQuery, 300);

    // Fetch files data with proper typing
    const { data: files = [], isLoading } = useQuery<FileData[], Error>({
        queryKey: ['files'],
        queryFn: getFiles,
    });

    // Delete file mutation
    const { mutate: deleteMutate, isPending: isDeleting } = useMutation({
        mutationFn: (fileId: string) => deleteFile(fileId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['files'] });
            toast({
                title: 'Xóa thành công',
                description: 'File đã được xóa',
            });
            setDeleteConfirmId(null);
        },
        onError: (error: any) => {
            toast({
                title: 'Lỗi xóa file',
                description: `Đã xảy ra lỗi khi xóa file: ${error.message || 'Không xác định'}`,
                variant: 'destructive',
            });
            setDeleteConfirmId(null);
        },
    });

    // Handle sorting
    const handleSort = (column: string) => {
        if (sortBy === column) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(column);
            setSortOrder('desc');
        }
    };

    // Process files for display with filtering and sorting
    const getProcessedFiles = () => {
        if (!Array.isArray(files) || files.length === 0) return [];

        let processed = [...files];

        // Apply search filter
        if (debouncedSearchQuery) {
            processed = processed.filter(file =>
                file.originalName?.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
                file.filename?.toLowerCase().includes(debouncedSearchQuery.toLowerCase())
            );
        }

        // Apply sorting
        processed.sort((a, b) => {
            if (sortBy === 'createdAt') {
                const dateA = a.createdAt ? new Date(a.createdAt).getTime() : 0;
                const dateB = b.createdAt ? new Date(b.createdAt).getTime() : 0;
                return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
            }

            if (sortBy === 'name') {
                const nameA = a.originalName || a.filename || '';
                const nameB = b.originalName || b.filename || '';
                return sortOrder === 'asc'
                    ? nameA.localeCompare(nameB)
                    : nameB.localeCompare(nameA);
            }

            if (sortBy === 'rows') {
                return sortOrder === 'asc'
                    ? (a.analysis?.rowCount || 0) - (b.analysis?.rowCount || 0)
                    : (b.analysis?.rowCount || 0) - (a.analysis?.rowCount || 0);
            }

            if (sortBy === 'size') {
                return sortOrder === 'asc'
                    ? (a.size || 0) - (b.size || 0)
                    : (b.size || 0) - (a.size || 0);
            }

            if (sortBy === 'quality') {
                const qualityA = a.qualityScore || 0;
                const qualityB = b.qualityScore || 0;
                return sortOrder === 'asc'
                    ? qualityA - qualityB
                    : qualityB - qualityA;
            }

            return 0;
        });

        return processed;
    };

    // Get file icon based on type
    const getFileIcon = (fileType: string | undefined) => {
        if (!fileType) return <FileText className="h-10 w-10 text-gray-500" />;

        switch (fileType.toLowerCase()) {
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
    const formatDate = (dateString: string | Date | undefined) => {
        if (!dateString) return '';
        try {
            return format(new Date(dateString), 'dd/MM/yyyy HH:mm', { locale: vi });
        } catch (e) {
            return 'Không hợp lệ';
        }
    };

    // Get quality color
    const getQualityColor = (score?: number) => {
        if (score === undefined || score === null) return 'bg-gray-200 text-gray-700';
        if (score >= 90) return 'bg-green-100 text-green-800';
        if (score >= 80) return 'bg-green-100 text-green-800';
        if (score >= 70) return 'bg-yellow-100 text-yellow-800';
        if (score >= 60) return 'bg-yellow-100 text-yellow-800';
        if (score >= 50) return 'bg-orange-100 text-orange-800';
        return 'bg-red-100 text-red-800';
    };

    const processedFiles = getProcessedFiles();

    console.log(files);
    console.log(processedFiles);

    // Handles file upload success with proper typing
    const handleFileUploadSuccess = (fileData: FileData | ApiResponse) => {
        setShowUploadDialog(false);

        // Handle the case where the API returns an ApiResponse
        if ((fileData as ApiResponse)?.status === ResponseStatus.SUCCESS) {
            const apiResponse = fileData as ApiResponse;
            const data = apiResponse.data as FileData;

            if (!data?.id) {
                toast({
                    title: 'Lỗi xử lý',
                    description: 'Không thể xác định ID tệp. Vui lòng thử lại hoặc liên hệ hỗ trợ.',
                    variant: 'destructive',
                });
                console.error('Missing file ID in API response:', apiResponse);
                return;
            }

            toast({
                title: 'Tải lên thành công',
                description: `${data.originalName} đã được tải lên và phân tích`,
            });

            queryClient.invalidateQueries({ queryKey: ['files'] });
            navigate(`/files/${data.id}`);
            return;
        }

        // Direct FileData object
        const data = fileData as FileData;
        if (!data.id) {
            toast({
                title: 'Lỗi xử lý',
                description: 'Không thể xác định ID tệp. Vui lòng thử lại hoặc liên hệ hỗ trợ.',
                variant: 'destructive',
            });
            console.error('Missing file ID in upload success handler:', data);
            return;
        }

        toast({
            title: 'Tải lên thành công',
            description: `${data.originalName} đã được tải lên và phân tích`,
        });

        queryClient.invalidateQueries({ queryKey: ['files'] });
        navigate(`/files/${data.id}`);
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Tệp dữ liệu</h1>
                    <p className="text-muted-foreground">
                        Quản lý các tệp dữ liệu đã tải lên
                    </p>
                </div>

                <Button onClick={() => setShowUploadDialog(true)}>
                    <Plus className="mr-2 h-4 w-4" /> Tải lên tệp
                </Button>
            </div>

            {/* Search and Filter */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        placeholder="Tìm kiếm theo tên tệp..."
                        className="pl-9"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" className="w-full sm:w-auto">
                            <Filter className="mr-2 h-4 w-4" /> Sắp xếp
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="bg-neutral-800 w-40">
                        <DropdownMenuItem onClick={() => handleSort('size')} className="flex justify-between">
                            <span>Kích thước</span>
                            {sortBy === 'size' && (sortOrder === 'desc' ? <SortDesc className="h-4 w-4" /> : <SortAsc className="h-4 w-4" />)}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => handleSort('createdAt')}
                            className="flex justify-between"
                        >
                            <span>Thời gian</span>
                            {sortBy === 'createdAt' && (
                                sortOrder === 'desc' ? <SortDesc className="h-4 w-4" /> : <SortAsc className="h-4 w-4" />
                            )}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => handleSort('name')}
                            className="flex justify-between"
                        >
                            <span>Tên</span>
                            {sortBy === 'name' && (
                                sortOrder === 'desc' ? <SortDesc className="h-4 w-4" /> : <SortAsc className="h-4 w-4" />
                            )}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => handleSort('rows')}
                            className="flex justify-between"
                        >
                            <span>Số dòng</span>
                            {sortBy === 'rows' && (
                                sortOrder === 'desc' ? <SortDesc className="h-4 w-4" /> : <SortAsc className="h-4 w-4" />
                            )}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => handleSort('quality')}
                            className="flex justify-between"
                        >
                            <span>Chất lượng</span>
                            {sortBy === 'quality' && (
                                sortOrder === 'desc' ? <SortDesc className="h-4 w-4" /> : <SortAsc className="h-4 w-4" />
                            )}
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            {/* Files List */}
            <div className="space-y-4">
                {isLoading ? (
                    // Loading skeleton
                    Array.from({ length: 5 }).map((_, index) => (
                        <Card key={index}>
                            <CardContent className="p-6">
                                <div className="flex items-start space-x-4">
                                    <Skeleton className="h-12 w-12 rounded-md" />
                                    <div className="space-y-2 flex-1">
                                        <Skeleton className="h-5 w-full max-w-[300px]" />
                                        <div className="flex items-center gap-2">
                                            <Skeleton className="h-4 w-20" />
                                            <Skeleton className="h-4 w-20" />
                                            <Skeleton className="h-4 w-20" />
                                        </div>
                                        <Skeleton className="h-4 w-32" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))
                ) : processedFiles.length === 0 ? (
                    // Empty state
                    <Card>
                        <CardContent className="p-6 text-center">
                            <FileSpreadsheet className="mx-auto h-12 w-12 text-muted-foreground" />
                            <h3 className="mt-4 text-lg font-semibold">Chưa có tệp nào</h3>
                            <p className="mt-2 text-sm text-muted-foreground">
                                Tải lên tệp CSV hoặc Excel để bắt đầu phân tích dữ liệu
                            </p>
                            <Button className="mt-4" onClick={() => setShowUploadDialog(true)}>
                                <Plus className="mr-2 h-4 w-4" /> Tải lên tệp
                            </Button>
                        </CardContent>
                    </Card>
                ) : (
                    // Files list
                    processedFiles.map((file) => (
                        <Card key={file.id} className="hover:bg-muted/50 transition-colors">
                            <CardContent className="p-6">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start space-x-4">
                                        {getFileIcon(file.type)}
                                        <div>
                                            <h3 className="font-medium line-clamp-1">{file.originalName}</h3>
                                            <div className="flex flex-wrap gap-2 mt-1">
                                                <Badge variant="outline" className="text-xs">
                                                    {(file.type || '').toUpperCase()}
                                                </Badge>
                                                <span className="text-xs text-muted-foreground">
                                                    {(file.analysis?.rowCount || 0).toLocaleString()} dòng
                                                </span>
                                                <span className="text-xs text-muted-foreground">
                                                    {file.analysis?.columnCount || 0} cột
                                                </span>
                                                <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                                                {file.qualityScore && file.qualityScore !== undefined && (
                                                    <Badge className={getQualityColor(file.qualityScore)}>
                                                        {file.qualityScore.toFixed(0)}%
                                                    </Badge>
                                                )}
                                            </div>
                                            <div className="text-xs text-muted-foreground mt-1">
                                                Tải lên: {formatDate(file.createdAt)}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                                    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg" className="h-4 w-4">
                                                        <path d="M3.625 7.5C3.625 8.12132 3.12132 8.625 2.5 8.625C1.87868 8.625 1.375 8.12132 1.375 7.5C1.375 6.87868 1.87868 6.375 2.5 6.375C3.12132 6.375 3.625 6.87868 3.625 7.5ZM8.625 7.5C8.625 8.12132 8.12132 8.625 7.5 8.625C6.87868 8.625 6.375 8.12132 6.375 7.5C6.375 6.87868 6.87868 6.375 7.5 6.375C8.12132 6.375 8.625 6.87868 8.625 7.5ZM12.5 8.625C13.1213 8.625 13.625 8.12132 13.625 7.5C13.625 6.87868 13.1213 6.375 12.5 6.375C11.8787 6.375 11.375 6.87868 11.375 7.5C11.375 8.12132 11.8787 8.625 12.5 8.625Z" fill="currentColor" fillRule="evenodd" clipRule="evenodd"></path>
                                                    </svg>
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent className='bg-neutral-800' align="end">
                                                <DropdownMenuItem onClick={() => navigate(`/files/${file.id}`)}>
                                                    <Eye className="mr-2 h-4 w-4" />
                                                    <span>Xem chi tiết</span>
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={() => navigate(`/analysis/${file.id}`)}>
                                                    <BarChart2 className="mr-2 h-4 w-4" />
                                                    <span>Phân tích</span>
                                                </DropdownMenuItem>
                                                <DropdownMenuSeparator />
                                                <DropdownMenuItem onClick={() => setDeleteConfirmId(file.id)}>
                                                    <Trash2 className="mr-2 h-4 w-4 text-destructive" />
                                                    <span className="text-destructive">Xóa</span>
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))
                )}
            </div>

            {/* Upload Dialog */}
            <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Tải lên tệp dữ liệu</DialogTitle>
                        <DialogDescription>
                            Tải lên tệp CSV hoặc Excel để phân tích dữ liệu
                        </DialogDescription>
                    </DialogHeader>
                    <FileUploader onUploadSuccess={handleFileUploadSuccess} />
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={!!deleteConfirmId} onOpenChange={() => setDeleteConfirmId(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Xác nhận xóa</DialogTitle>
                        <DialogDescription>
                            Bạn có chắc chắn muốn xóa tệp này? Hành động này không thể hoàn tác.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
                            Hủy bỏ
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={() => deleteConfirmId && deleteMutate(deleteConfirmId)}
                            disabled={isDeleting}
                        >
                            {isDeleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Xóa
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default FilesPage;