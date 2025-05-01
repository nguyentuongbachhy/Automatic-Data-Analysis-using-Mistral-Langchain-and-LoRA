import axios, { AxiosError, AxiosResponse } from 'axios';
import {
    ApiResponse,
    AuthResponse,
    ChartRecommendation,
    ChartRecommendationRequest,
    ChartType,
    ChatData,
    ChatRequest,
    ChatResponse,
    ColumnInfo,
    CorrelationAnalysisRequest,
    CreateChartRequest,
    deepCamelCaseKeys,
    deepSnakeCaseKeys,
    FileAnalysisResult,
    FileData,
    InsightData,
    LoginCredentials,
    Message,
    PredictionData,
    PredictionRequest,
    PredictionResult,
    RegisterData,
    ResponseStatus,
    TimeSeriesAnalysis,
    TimeSeriesAnalysisRequest,
    UploadResponse,
    User,
    VisualizationData
} from '../types';

// Create axios instance
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 600000,
});

// Request interceptor
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('auth-token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
        const { response } = error;

        // Handle token expiration
        if (response?.status === 401) {
            localStorage.removeItem('auth-token');
            window.location.href = '/login';
        }

        return Promise.reject(error);
    }
);

// Helper function to handle API responses
function handleApiResponse<T>(response: AxiosResponse): T {
    if (response.data && response.data.status === ResponseStatus.SUCCESS) {
        // Convert snake_case to camelCase
        return deepCamelCaseKeys(response.data.data) as T;
    }
    throw new Error(response.data?.error || 'Unknown error occurred');
}

// =====================================================
// Authentication API
// =====================================================

export const loginUser = async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', credentials);

    // Direct response format (not wrapped in ApiResponse)
    if (response.data && response.data.token && response.data.user) {
        return response.data as AuthResponse;
    }

    // Wrapped response format
    return handleApiResponse<AuthResponse>(response);
};

export const registerUser = async (userData: RegisterData): Promise<AuthResponse> => {
    const response = await api.post('/auth/register', userData);

    // Direct response format
    if (response.data && response.data.token && response.data.user) {
        return response.data as AuthResponse;
    }

    // Wrapped response format
    return handleApiResponse<AuthResponse>(response);
};

export const logoutUser = (): void => {
    localStorage.removeItem('auth-token');
};

export const getCurrentUser = async (): Promise<User> => {
    const response = await api.get('/auth/me');

    // Direct response format
    if (response.data && !response.data.status && response.data.id) {
        return response.data as User;
    }

    // Wrapped response format
    return handleApiResponse<User>(response);
};

// =====================================================
// File Management API
// =====================================================

export const getFiles = async (): Promise<FileData[]> => {
    const response = await api.get('/files');
    const result = handleApiResponse<{ files: any[] }>(response);
    return result.files.map(file => deepCamelCaseKeys(file) as FileData);
};

export const getFileById = async (fileId: string): Promise<FileData> => {
    try {
        const response = await api.get(`/files/${fileId}`);

        // Handle pending analysis (202 status)
        if (response.status === 202 ||
            (response.data && response.data.status === ResponseStatus.PENDING)) {
            return {
                ...(response.data?.data?.file ? deepCamelCaseKeys(response.data.data.file) : {}),
                id: fileId,
                isPending: true,
                message: response.data?.data?.message || 'Analysis in progress'
            } as FileData;
        }

        // Handle successful response
        if (response.data && response.data.status === ResponseStatus.SUCCESS) {
            return deepCamelCaseKeys(response.data.data) as FileData;
        }

        throw new Error('Failed to retrieve file data');
    } catch (error) {
        console.error("Error fetching file:", error);
        throw error;
    }
};

export const uploadFile = async (formData: FormData): Promise<UploadResponse> => {
    try {
        const response = await api.post('/files/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return response.data as UploadResponse;
    } catch (error: any) {
        return {
            status: ResponseStatus.ERROR,
            error: error?.response?.data?.error || error?.message || 'Upload failed',
            data: { fileId: '', originalName: '', message: 'No data available' }
        } as UploadResponse;
    }
};

export const deleteFile = async (fileId: string): Promise<boolean> => {
    const response = await api.delete(`/files/${fileId}`);
    return response.data?.status === ResponseStatus.SUCCESS;
};

export const getFileAnalysis = async (fileId: string): Promise<FileAnalysisResult> => {
    const response = await api.get(`/files/${fileId}`);

    if (response.data?.status === ResponseStatus.PENDING) {
        throw new Error('Analysis in progress');
    }

    return deepCamelCaseKeys(response.data.data) as FileAnalysisResult;
};

export const getFileSummary = async (fileId: string): Promise<ApiResponse> => {
    try {
        const response = await api.get(`/files/${fileId}?type=summary`);
        return response.data as ApiResponse;
    } catch (error: any) {
        return {
            status: ResponseStatus.ERROR,
            error: error?.response?.data?.error || error?.message || 'Failed to get file summary',
            data: null
        } as ApiResponse;
    }
};

// =====================================================
// Chat & Conversation API
// =====================================================

export const processMessage = async (request: ChatRequest): Promise<ChatResponse> => {
    // Convert to snake_case for the API
    const enhancedRequest = {
        ...request,
        show_thinking: true
    };
    const snakeCaseRequest = deepSnakeCaseKeys(enhancedRequest);
    const response = await api.post('/chat', snakeCaseRequest);
    return deepCamelCaseKeys(handleApiResponse<ChatResponse>(response));
};

export const createChat = async (fileId?: string, title?: string): Promise<{ chatId: string }> => {
    try {
        // Sử dụng endpoint mới
        const response = await api.post('/chat/create', {
            file_id: fileId,
            title: title || (fileId ? 'File Analysis' : 'New Chat')
        });

        if (response.data && response.data.status === ResponseStatus.SUCCESS) {
            // Lấy chat_id từ data
            return {
                chatId: response.data.data.chat_id
            };
        }

        // Các phần xử lý lỗi giữ nguyên
        throw new Error(response.data?.error || 'Failed to create chat');
    } catch (error: any) {
        console.error('Error creating chat:', error);
        throw error;
    }
};

/**
 * Lấy chats của người dùng có hoặc không có file cụ thể
 * @param fileId Optional, ID của file cần lọc
 * @returns Danh sách chat
 */
export const getChats = async (fileId?: string): Promise<ChatData[]> => {
    try {
        // Lấy ID người dùng từ localStorage hoặc auth context
        const userData = localStorage.getItem('auth-user');
        const user = userData ? JSON.parse(userData) : null;
        const userId = user?.value?.id;

        if (!userId) {
            console.error('User ID not found, please login again');
            return [];
        }

        // Tạo params với user_id bắt buộc
        const params = new URLSearchParams();
        params.append('user_id', userId);

        // Thêm file_id nếu có
        if (fileId) {
            params.append('file_id', fileId);
        }

        // Gọi đúng endpoint với đầy đủ tham số
        const response = await api.get(`/chat/get-chats?${params.toString()}`);

        if (response.data && response.data.status === ResponseStatus.SUCCESS) {
            return (response.data.data.chats || []).map((chat: any) =>
                deepCamelCaseKeys(chat) as ChatData
            );
        }

        return [];
    } catch (error) {
        console.error('Error fetching chats:', error);
        return [];
    }
};

export const sendChatMessage = async (
    chatId: string,
    content: string,
    fileId?: string,
): Promise<ChatResponse> => {
    try {
        const payload = deepSnakeCaseKeys({
            query: content,
            chatId: chatId,
            fileId,
            useLangchain: true,
            showThinking: true
        });

        const response = await api.post(`/chat/message`, payload);
        return deepCamelCaseKeys(handleApiResponse<ChatResponse>(response));
    } catch (error) {
        console.error(`Error sending message to chat ${chatId}:`, error);
        throw error;
    }
};

export const streamChatMessage = async (
    chatId: string,
    content: string,
    fileId?: string,
    userId?: string,
    messageId?: string,
    onToken?: (token: string) => void,
    onComplete?: (response: ChatResponse) => void,
    onError?: (error: string) => void
): Promise<EventSource> => {
    // Prepare URL with query parameters
    const params = new URLSearchParams({
        query: content,
        chat_id: chatId,
        ...(messageId && { message_id: messageId }),
        ...(fileId && { file_id: fileId }),
        ...(userId && { user_id: userId }), // Thêm user_id vào query params
        show_thinking: "true",
    });

    // Thêm token xác thực nếu có sẵn
    const token = localStorage.getItem('auth-token');
    if (token) {
        params.append('token', token);
    }

    // Sửa lại đường dẫn đúng là /chats/stream thay vì /chat/stream
    const url = `${api.defaults.baseURL}/chats/stream?${params}`;

    // Create EventSource
    const eventSource = new EventSource(url);
    let fullResponse = '';

    // Handle message events (tokens)
    eventSource.addEventListener('message', (event) => {
        try {
            const data = JSON.parse(event.data);
            fullResponse += data.token || '';

            if (onToken && data.token) {
                onToken(data.token);
            }

            // If done is true, we've received all tokens
            if (data.done) {
                // Continue listening for other events (visualizations, insights)
            }
        } catch (e) {
            console.error('Error parsing stream message:', e);
        }
    });

    // Handle visualization events
    eventSource.addEventListener('chat-visualizations', (event) => {
        try {
            const data = JSON.parse(event.data);
            if (onComplete && data.visualizations) {
                onComplete({
                    id: data.id,
                    response: fullResponse,
                    visualizations: deepCamelCaseKeys(data.visualizations)
                });
            }
        } catch (e) {
            console.error('Error parsing visualizations:', e);
        }
    });

    // Handle insight events
    eventSource.addEventListener('chat-insights', (event) => {
        try {
            const data = JSON.parse(event.data);
            if (onComplete && data.insights) {
                onComplete({
                    id: data.id,
                    response: fullResponse,
                    insights: deepCamelCaseKeys(data.insights)
                });
            }
        } catch (e) {
            console.error('Error parsing insights:', e);
        }
    });

    // Handle completion event
    eventSource.addEventListener('complete', () => {
        if (onComplete) {
            onComplete({ id: '', response: fullResponse });
        }
        eventSource.close();
    });

    // Handle error events
    eventSource.addEventListener('error', (event: any) => {
        try {
            // Khi EventSource gặp lỗi, thường `event.data` không tồn tại
            // Thay vì lỗi khi parse không thành công, kiểm tra trước
            if (event.data) {
                const data = JSON.parse(event.data);
                if (onError) {
                    onError(data.error || 'Unknown stream error');
                }
            } else {
                // Xử lý lỗi kết nối chung
                if (onError) {
                    onError('Connection error or unauthorized access');
                }
            }
        } catch (e) {
            if (onError) {
                onError('Stream error occurred');
            }
        }
        eventSource.close();
    });

    return eventSource;
};

export const getChatMessages = async (chatId: string, loadToMemory: boolean = true): Promise<Message[]> => {
    try {
        const response = await api.get(`/chat/messages/${chatId}?load_to_memory=${loadToMemory}`);
        if (response.data?.status === ResponseStatus.SUCCESS) {
            return (response.data.data.messages || []).map((msg: any) =>
                deepCamelCaseKeys(msg) as Message
            );
        }
        return [];
    } catch (error) {
        console.error(`Error fetching messages for chat ${chatId}:`, error);
        return [];
    }
};

// =====================================================
// Data Analysis API
// =====================================================

export const performFullAnalysis = async (
    fileId: string,
    analysisType: string = 'full'
): Promise<ApiResponse> => {
    const payload = deepSnakeCaseKeys({
        fileId,
        analysisType
    });

    try {
        const response = await api.post('/analyze/full', payload);
        return response.data as ApiResponse;
    } catch (error: any) {
        return {
            status: ResponseStatus.ERROR,
            error: error?.response?.data?.error || error?.message || 'Analysis failed',
            data: null
        } as ApiResponse;
    }
};

export const generateInsights = async (
    fileId: string,
    options: { insightTypes?: string[], columns?: string[] } = {}
): Promise<InsightData[]> => {
    try {
        const response = await proxyAnalyzeRequest(
            fileId,
            'insights',
            'POST',
            options
        );

        if (response.status === ResponseStatus.SUCCESS && response.data?.insights) {
            return response.data.insights.map((insight: any) =>
                deepCamelCaseKeys(insight) as InsightData
            );
        }

        return [];
    } catch (error) {
        console.error('Error generating insights:', error);
        return [];
    }
};

export const getRecommendedCharts = async (
    fileId: string,
    options: ChartRecommendationRequest = {}
): Promise<ChartRecommendation> => {
    const payload = {
        fileId,
        ...options
    };

    const response = await api.post('/analyze/recommend-charts', payload);
    return deepCamelCaseKeys(handleApiResponse<ChartRecommendation>(response));
};

export const createChart = async (
    fileId: string,
    chartType: string,
    columns: string[]
): Promise<VisualizationData> => {
    const payload = deepSnakeCaseKeys({
        fileId,
        chartType,
        columns
    } as CreateChartRequest);

    console.log(payload);

    const response = await api.post('/analyze/create-chart', payload);
    return deepCamelCaseKeys(handleApiResponse<VisualizationData>(response));
};

export const correlationAnalysis = async (
    fileId: string,
    options: CorrelationAnalysisRequest = {}
): Promise<ApiResponse> => {
    const payload = deepSnakeCaseKeys({
        fileId,
        ...options
    });

    const response = await api.post('/analyze/correlation', payload);
    return response.data as ApiResponse;
};

// =====================================================
// Prediction API
// =====================================================

export const predictData = async (request: PredictionRequest): Promise<PredictionResult> => {
    const payload = deepSnakeCaseKeys(request);
    const response = await api.post('/analyze/predict', payload);
    return deepCamelCaseKeys(handleApiResponse<PredictionResult>(response));
};

export const getPredictionById = async (predictionId: string): Promise<PredictionData> => {
    const response = await api.get(`/predictions/${predictionId}`);
    return deepCamelCaseKeys(handleApiResponse<PredictionData>(response));
};

export const getFilePredictions = async (fileId: string): Promise<PredictionData[]> => {
    const response = await api.get(`/files/${fileId}/predictions`);
    const predictions = handleApiResponse<any[]>(response);
    return predictions.map(prediction => deepCamelCaseKeys(prediction) as PredictionData);
};

// =====================================================
// Time Series Analysis API
// =====================================================

export const analyzeTimeSeries = async (
    fileId: string,
    config: TimeSeriesAnalysisRequest
): Promise<ApiResponse> => {
    const payload = deepSnakeCaseKeys({
        fileId,
        ...config
    });

    const response = await api.post('/analyze/time-series', payload);
    return response.data as ApiResponse;
};

export const getTimeSeriesAnalysis = async (
    fileId: string,
    dateColumn: string,
    valueColumn: string
): Promise<TimeSeriesAnalysis> => {
    const response = await api.get(
        `/files/${fileId}/time-series?date_column=${dateColumn}&value_column=${valueColumn}`
    );
    return deepCamelCaseKeys(handleApiResponse<TimeSeriesAnalysis>(response));
};

export const getFileTimeSeriesAnalyses = async (fileId: string): Promise<TimeSeriesAnalysis[]> => {
    const response = await api.get(`/files/${fileId}/time-series`);
    const analyses = handleApiResponse<any[]>(response);
    return analyses.map(analysis => deepCamelCaseKeys(analysis) as TimeSeriesAnalysis);
};

// =====================================================
// Visualization API
// =====================================================

export const getFileVisualizations = async (
    fileId: string,
    options: { insightTypes?: string[], columns?: string[] } = {}
): Promise<VisualizationData[]> => {
    try {
        const response = await proxyAnalyzeRequest(
            fileId,
            'visualize',
            'POST',
            options
        );

        if (response.status === ResponseStatus.SUCCESS && response.data?.visualizations) {
            return response.data.visualizations.map((visualization: any) =>
                deepCamelCaseKeys(visualization) as VisualizationData
            );
        }

        return [];
    } catch (error) {
        console.error('Error generating insights:', error);
        return [];
    }
};

export const getVisualizationById = async (vizId: string): Promise<VisualizationData> => {
    const response = await api.get(`/visualizations/${vizId}`);
    return deepCamelCaseKeys(handleApiResponse<VisualizationData>(response));
};

export const createVisualization = async (
    fileId: string,
    visualization: Partial<VisualizationData>
): Promise<VisualizationData> => {
    try {
        // 1. Chuẩn bị payload với đầy đủ thông tin
        const chartType = visualization.type || ChartType.BAR;
        const columns = visualization.config?.columns ||
            visualization.parameters?.columns ||
            [];

        // Kiểm tra dữ liệu bắt buộc
        if (!fileId) throw new Error("Thiếu fileId");
        if (columns.length === 0) throw new Error("Không có cột nào được chọn");

        console.log(`Chart type: ${chartType}, Columns:`, columns);

        // 2. Tạo payload đầy đủ
        const payload = {
            fileId: fileId,
            chartType: chartType,
            columns: columns,
            title: visualization.title || `Biểu đồ ${chartType}`,
            description: visualization.description || ''
        };

        console.log("Sending payload to server:", payload);

        // 3. Gọi API với payload đầy đủ
        const response = await api.post('/analyze/create-custom-chart', payload);
        console.log("Server response:", response.data);

        // 4. Xử lý kết quả
        if (response.data?.status === ResponseStatus.SUCCESS && response.data.data?.chart) {
            // Trả về chart từ server
            return deepCamelCaseKeys(response.data.data.chart) as VisualizationData;
        }

        if (response.data?.status === ResponseStatus.SUCCESS) {
            // Tạo visualization từ dữ liệu đã có nếu server không trả về chart
            return {
                id: `viz-${Date.now()}`,
                fileId,
                type: visualization.type || ChartType.BAR,
                title: visualization.title || `Biểu đồ ${chartType}`,
                description: visualization.description || '',
                data: visualization.data || [],
                config: {
                    ...visualization.config,
                    columns
                }
            } as VisualizationData;
        }

        // 5. Xử lý lỗi từ server
        if (response.data?.status === ResponseStatus.ERROR) {
            throw new Error(response.data.error || 'Server error');
        }

        throw new Error('Failed to create visualization');
    } catch (error: any) {
        // 6. Ghi log lỗi chi tiết
        console.error('Error creating visualization:', error);
        console.error('Error details:', {
            message: error.message,
            response: error.response?.data,
            status: error.response?.status
        });

        // Ném lỗi để mutation có thể bắt
        throw error;
    }
};

// =====================================================
// Insight API
// =====================================================

export const getFileInsights = async (fileId: string): Promise<InsightData[]> => {
    const response = await api.get(`/files/${fileId}/insights`);
    const insights = handleApiResponse<any[]>(response);
    return insights.map(insight => deepCamelCaseKeys(insight) as InsightData);
};

// =====================================================
// Column API
// =====================================================

export const getFileColumns = async (fileId: string): Promise<ColumnInfo[]> => {
    const response = await api.get(`/files/${fileId}/columns`);
    const columns = handleApiResponse<any[]>(response);
    return columns.map(column => deepCamelCaseKeys(column) as ColumnInfo);
};

// =====================================================
// Gateway API Proxy
// =====================================================

export const proxyAnalyzeRequest = async (
    fileId: string,
    endpoint: string,
    method: string = 'POST',
    data: any = null
): Promise<ApiResponse> => {
    try {

        const token = localStorage.getItem('auth-token');
        if (!token) {
            console.error('No authentication token found');
            return {
                status: ResponseStatus.ERROR,
                error: 'Chưa xác thực. Vui lòng đăng nhập lại.',
                data: null
            };
        }

        const requestData = {
            fileId,
            ...(data || {})
        };

        console.log(`Debug - Sending request to /analyze/${endpoint}:`, {
            url: `/analyze/${endpoint}`,
            method,
            headers: { Authorization: `Bearer ${token.substring(0, 10)}...` },
            data: requestData
        });

        const requestConfig = {
            method,
            url: `/analyze/${endpoint}`,
            headers: {
                Authorization: `Bearer ${token}`
            },
            data: requestData
        };

        const response = await api(requestConfig);;
        return response.data as ApiResponse;
    } catch (error: any) {
        console.error(`Error in analyze/${endpoint}:`, {
            status: error.response?.status,
            statusText: error.response?.statusText,
            data: error.response?.data,
            message: error.message
        });

        if (error.response && error.response.status === 401) {
            console.error('Authentication failed for analyze request');
            return {
                status: ResponseStatus.ERROR,
                error: 'Authentication failed. Please login again.',
                data: null
            } as ApiResponse;
        }
        return {
            status: ResponseStatus.ERROR,
            error: error?.response?.data?.error || error?.message || 'Request failed',
            data: null
        } as ApiResponse;
    }
};