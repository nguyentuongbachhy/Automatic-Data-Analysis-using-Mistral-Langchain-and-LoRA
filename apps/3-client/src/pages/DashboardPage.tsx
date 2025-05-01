// apps/client/src/pages/DashboardPage.tsx
import { useQuery } from '@tanstack/react-query';
import { BarChart2, Clock, FileSpreadsheet, Plus, Upload } from 'lucide-react';
import { useState } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { useNavigate } from 'react-router-dom';
import ActivityFeed from '../components/dashboard/ActivityFeed';
import RecentFiles from '../components/dashboard/RecentFiles';
import StatsCards from '../components/dashboard/StatsCards';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import FileUploader from '../components/upload/FileUploader';
import { toast } from '../hooks/use-toast';
import { getFiles } from '../services/api';
import { FileData } from '../types';

const DashboardPage = () => {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('overview');

    // Fetch files with proper typing
    const { data: files, isLoading } = useQuery<FileData[], Error>({
        queryKey: ['files'],
        queryFn: getFiles,
    });

    console.log(files);

    const handleFileUploadSuccess = (fileData: FileData) => {
        // Validate that we have a valid file ID before navigation
        if (!fileData.id) {
            console.error('Missing file ID in upload success handler:', fileData);
            toast({
                title: 'Lỗi xử lý',
                description: 'Không thể xác định ID tệp. Vui lòng thử lại.',
                variant: 'destructive',
            });
            return;
        }

        console.log('Navigating to file with ID:', fileData.id);

        navigate(`/files/${fileData.id}`);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
                <Button className="hidden md:flex" onClick={() => setActiveTab('upload')}>
                    <Plus className="mr-2 h-4 w-4" /> Tải lên File
                </Button>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                <TabsList>
                    <TabsTrigger value="overview" className="flex items-center">
                        <BarChart2 className="mr-2 h-4 w-4" />
                        Tổng quan
                    </TabsTrigger>
                    <TabsTrigger value="recent" className="flex items-center">
                        <Clock className="mr-2 h-4 w-4" />
                        Gần đây
                    </TabsTrigger>
                    <TabsTrigger value="upload" className="flex items-center md:hidden">
                        <Upload className="mr-2 h-4 w-4" />
                        Tải lên
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                    <StatsCards files={files || []} />

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <Card className="md:col-span-2">
                            <CardHeader>
                                <CardTitle>Tệp gần đây</CardTitle>
                                <CardDescription>Các file đã phân tích gần đây</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {isLoading ? (
                                    <div className="space-y-2">
                                        {[...Array(3)].map((_, i) => (
                                            <div key={i} className="flex items-center space-x-4">
                                                <Skeleton className="h-12 w-12 rounded-md" />
                                                <div className="space-y-2">
                                                    <Skeleton className="h-4 w-[250px]" />
                                                    <Skeleton className="h-4 w-[200px]" />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <ErrorBoundary fallback={<div>Đã xảy ra lỗi khi tải dữ liệu</div>}>
                                        <RecentFiles files={files || []} />
                                    </ErrorBoundary>
                                )}
                            </CardContent>
                            <CardFooter>
                                <Button variant="outline" className="w-full" onClick={() => navigate('/files')}>
                                    Xem tất cả
                                </Button>
                            </CardFooter>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Hoạt động</CardTitle>
                                <CardDescription>Hoạt động gần đây</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ActivityFeed />
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="recent">
                    <Card>
                        <CardHeader>
                            <CardTitle>Tệp tin của bạn</CardTitle>
                            <CardDescription>
                                Danh sách các file CSV và Excel đã phân tích
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <div className="space-y-2">
                                    {[...Array(5)].map((_, i) => (
                                        <div key={i} className="flex items-center space-x-4">
                                            <Skeleton className="h-12 w-12 rounded-md" />
                                            <div className="space-y-2">
                                                <Skeleton className="h-4 w-[250px]" />
                                                <Skeleton className="h-4 w-[200px]" />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : !Array.isArray(files) || files.length === 0 ? (
                                <div className="text-center py-8">
                                    <FileSpreadsheet className="mx-auto h-12 w-12 text-muted-foreground" />
                                    <h3 className="mt-4 text-lg font-semibold">Không có file nào</h3>
                                    <p className="text-sm text-muted-foreground mt-2">
                                        Tải lên file CSV hoặc Excel để bắt đầu phân tích
                                    </p>
                                    <Button className="mt-4" onClick={() => setActiveTab('upload')}>
                                        <Upload className="mr-2 h-4 w-4" /> Tải lên file
                                    </Button>
                                </div>
                            ) : (
                                <RecentFiles files={files} showAll />
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="upload">
                    <Card>
                        <CardHeader>
                            <CardTitle>Tải lên file</CardTitle>
                            <CardDescription>
                                Tải lên file CSV hoặc Excel để phân tích
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <FileUploader onUploadSuccess={handleFileUploadSuccess} />
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default DashboardPage;