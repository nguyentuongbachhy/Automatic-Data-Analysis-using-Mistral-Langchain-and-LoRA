// apps/client/src/components/upload/FileUploader.tsx
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, Loader2, Upload } from "lucide-react";
import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { useToast } from "../../hooks/use-toast";
import { getFileById, uploadFile } from "../../services/api";
import { FileData, ResponseStatus, UploadResponse } from "../../types";
import { cn } from "../../utils/cn";
import { logApiResponse } from '../../utils/debug';
import { formatFileSize } from "../../utils/format";
import { Button } from "../ui/button";

interface FileUploaderProps {
    onUploadSuccess: (fileData: FileData) => void;
}

/**
 * FileUploader component allows users to upload CSV or Excel files for analysis
 */
export default function FileUploader({ onUploadSuccess }: FileUploaderProps) {
    const [file, setFile] = useState<File | null>(null);
    const [uploadState, setUploadState] = useState<{
        fileId: string | null;
        isAnalyzing: boolean;
        fileInfo: Partial<FileData> | null;
    }>({
        fileId: null,
        isAnalyzing: false,
        fileInfo: null,
    });
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Check file analysis status mutation using getFileById
    const { mutate: checkStatus, isPending: isChecking } = useMutation({
        mutationFn: getFileById, // Using getFileById to check file status
        onSuccess: (fileData: FileData) => {
            logApiResponse("File Analysis Response", fileData);

            // Check if the file is still pending analysis
            if (fileData.isPending) {
                // File is still being analyzed, check again later
                setTimeout(() => {
                    if (uploadState.fileId) {
                        checkStatus(uploadState.fileId);
                    }
                }, 2000);
                return;

            }
            // Analysis is complete, use the returned file data
            setUploadState({
                fileId: null,
                isAnalyzing: false,
                fileInfo: null,
            });

            setFile(null);

            toast({
                title: "Processing successful",
                description: `${file?.name || fileData.originalName} has been analyzed and is ready to use.`,
            });

            // Update files list
            queryClient.invalidateQueries({ queryKey: ["files"] });

            onUploadSuccess(fileData);
        },
        onError: (error: any) => {
            setUploadState({
                fileId: null,
                isAnalyzing: false,
                fileInfo: null,
            });
            toast({
                title: "Error checking file status",
                description: error.response?.data?.error || error.message || "An error occurred while checking file status.",
                variant: "destructive",
            });
        },
    });

    // Upload file mutation
    const { mutate, isPending: isUploading } = useMutation({
        mutationFn: uploadFile,
        onSuccess: (response: UploadResponse) => {
            logApiResponse("File Upload Response", response);

            if (response.status === ResponseStatus.SUCCESS && response.data) {
                const fileId = response.data.fileId;
                const fileInfo = {
                    id: fileId,
                    filename: fileId, // Using fileId as the filename initially
                    originalName: response.data.originalName || file?.name || '',
                    size: file?.size || 0,
                    type: file?.type || '',
                    path: '', // Not present in the response
                };

                // Update state once
                setUploadState({
                    fileId,
                    isAnalyzing: true,
                    fileInfo,
                });

                toast({
                    title: "Upload successful",
                    description: response.data.message || `${file?.name} is being analyzed. This process may take a moment.`,
                });

                // Trigger status check directly here instead of using useEffect
                checkStatus(fileId);
            } else {
                toast({
                    title: "Upload error",
                    description: response.error || "Unable to upload file.",
                    variant: "destructive",
                });
                setFile(null);
            }
        },
        onError: (error: any) => {
            toast({
                title: "Upload error",
                description: error.response?.data?.error || error.message || "An error occurred while uploading the file.",
                variant: "destructive",
            });
            setFile(null);
        },
    });

    // Initialize dropzone
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        accept: {
            'text/csv': ['.csv'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            'application/vnd.ms-excel': ['.xls']
        },
        maxFiles: 1,
        onDrop: (acceptedFiles) => {
            if (acceptedFiles.length > 0) {
                setFile(acceptedFiles[0]);
            }
        },
        disabled: isUploading || uploadState.isAnalyzing,
    });

    // Handle file upload
    const handleUpload = () => {
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);
        mutate(formData);
    };

    const isPending = isUploading || uploadState.isAnalyzing || isChecking;
    const statusText = isUploading ? "Uploading..." : (uploadState.isAnalyzing ? "Analyzing..." : "Analyze");

    return (
        <div className="w-full space-y-4">
            {/* Dropzone area */}
            <div
                {...getRootProps()}
                className={cn(
                    "border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors",
                    isDragActive ? "border-primary bg-muted" : "border-muted-foreground/25 hover:border-primary/50",
                    (isPending) && "opacity-50 cursor-not-allowed"
                )}
                data-testid="dropzone-area"
            >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center gap-2">
                    <Upload className="h-10 w-10 text-muted-foreground" />
                    {isDragActive ? (
                        <p>Drop the file here...</p>
                    ) : (
                        <>
                            <p className="text-sm font-medium">
                                Drag and drop your CSV or Excel file here
                            </p>
                            <p className="text-xs text-muted-foreground">
                                Supports CSV, XLSX, and XLS files
                            </p>
                        </>
                    )}
                </div>
            </div>

            {/* Selected file info */}
            {file && (
                <div className="flex items-center gap-2 p-2 rounded-md bg-muted" data-testid="selected-file">
                    <FileSpreadsheet className="h-5 w-5 text-blue-500" />
                    <span className="text-sm font-medium flex-1 truncate">{file.name}</span>
                    <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                    <Button
                        onClick={handleUpload}
                        disabled={isPending}
                        size="sm"
                        className="ml-auto"
                        data-testid="analyze-button"
                    >
                        {isPending ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> {statusText}
                            </>
                        ) : (
                            "Analyze"
                        )}
                    </Button>
                </div>
            )}

            {/* Analysis progress indicator */}
            {uploadState.isAnalyzing && !file && (
                <div className="flex items-center justify-center p-4 bg-muted rounded-md" data-testid="analysis-progress">
                    <Loader2 className="h-5 w-5 mr-2 animate-spin text-primary" />
                    <span className="text-sm font-medium">Analyzing your data, please wait...</span>
                </div>
            )}
        </div>
    );
}