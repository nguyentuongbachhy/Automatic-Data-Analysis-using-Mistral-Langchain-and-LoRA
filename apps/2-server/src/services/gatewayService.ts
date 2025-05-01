// services/apiGateway.ts
import axios, { AxiosRequestConfig } from 'axios';
import config from '../config';
import { ApiResponse, ErrorResponse, ResponseStatus } from '../types';
import { jsonService } from './jsonService';

// Extend InternalAxiosRequestConfig to include metadata
declare module 'axios' {
    export interface InternalAxiosRequestConfig {
        metadata?: { startTime: number };
    }
}

// Create an axios instance with optimized configuration
const apiClient = axios.create({
    baseURL: config.mlServiceUrl,
    timeout: 600000, // 10 minutes
    headers: {
        'Content-Type': 'application/json',
    },
    validateStatus: (status) => status < 500, // Only reject if status >= 500
});

// Add request interceptor for logging and metrics
apiClient.interceptors.request.use(
    (config) => {
        // Add request timestamp for performance monitoring
        config.metadata = { startTime: new Date().getTime() };

        // Add request ID for tracing
        config.headers['X-Request-ID'] = `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;

        // Log request (in development)
        if (process.env.NODE_ENV === 'development') {
            console.log(`🔄 Request: ${config.method?.toUpperCase()} ${config.url}`);
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor for logging and metrics
apiClient.interceptors.response.use(
    (response) => {
        const requestTime = new Date().getTime() - (response.config.metadata?.startTime || 0);

        // Log slow requests
        if (requestTime > 5000) { // Log slow requests (>5s)
            console.warn(`⚠️ Slow request to ${response.config.url}: ${requestTime}ms`);
        }

        // Log response (in development)
        if (process.env.NODE_ENV === 'development') {
            console.log(`✅ Response: ${response.status} from ${response.config.url} (${requestTime}ms)`);
        }

        return response;
    },
    (error) => {
        // Log error
        console.error(`❌ Error in request to ${error.config?.url || 'unknown endpoint'}:`,
            error.response?.status || error.code || 'unknown error');
        return Promise.reject(error);
    }
);

interface ForwardRequestOptions {
    headers?: Record<string, string>;
    additionalFields?: Record<string, any>;
    validateSchema?: any;
    retries?: number;
    retryDelay?: number;
    timeout?: number;
}

/**
 * Enhanced forward request function with better error handling and retry capability
 */
export const forwardRequest = async <T = any>(
    endpoint: string,
    method: string,
    data: any = null,
    queryParams: any = null,
    options: ForwardRequestOptions = {}
): Promise<ApiResponse<T>> => {
    const {
        headers = {},
        additionalFields,
        validateSchema,
        retries = 1,
        retryDelay = 1000,
        timeout
    } = options;

    let attempts = 0;

    const executeRequest = async (): Promise<ApiResponse<T>> => {
        try {
            attempts++;

            // Transform data from camelCase to snake_case for AI service
            const transformedData = data ? jsonService.transformRequest(data, {
                convertToSnakeCase: true,
                addFields: additionalFields
            }) : undefined;

            const requestConfig: AxiosRequestConfig = {
                method,
                url: endpoint,
                headers: {
                    ...headers,
                    'X-Request-ID': `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`
                },
                params: queryParams,
                data: method !== 'GET' ? transformedData : undefined,
            };

            // Set custom timeout if provided
            if (timeout) {
                requestConfig.timeout = timeout;
            }

            const response = await apiClient(requestConfig);

            // Transform response from snake_case to camelCase
            return jsonService.transformResponse<T>(response.data, {
                convertToCamelCase: true,
                validateWithSchema: validateSchema
            });
        } catch (error) {
            // Handle retry logic
            if (attempts < retries && axios.isAxiosError(error) &&
                (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT' ||
                    (error.response && error.response.status >= 500))) {

                console.log(`Request to ${endpoint} failed, retrying (${attempts}/${retries})...`);

                // Wait before retry using exponential backoff
                await new Promise(resolve => setTimeout(resolve, retryDelay * attempts));
                return executeRequest();
            }

            console.error(`API Gateway error for ${endpoint}:`, error);

            if (axios.isAxiosError(error) && error.response) {
                // Transform error response
                return jsonService.transformResponse(error.response.data, {
                    convertToCamelCase: true
                });
            }

            // Create a standard error format
            const errorResponse: ErrorResponse = {
                status: ResponseStatus.ERROR,
                error: error instanceof Error ? error.message : 'Unknown error',
                meta: {
                    endpoint,
                    timestamp: new Date().toISOString(),
                    attempts
                }
            };

            return errorResponse;
        }
    };

    return executeRequest();
};

/**
 * Upload file with progress tracking
 */
export const uploadFile = async (
    file: File,
    url: string,
    onProgress?: (progress: number) => void
): Promise<ApiResponse<any>> => {
    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await apiClient.post(url, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            onUploadProgress: (progressEvent) => {
                if (onProgress && progressEvent.total) {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(progress);
                }
            }
        });

        return jsonService.transformResponse(response.data, {
            convertToCamelCase: true
        });
    } catch (error) {
        console.error('File upload error:', error);

        const errorResponse: ErrorResponse = {
            status: ResponseStatus.ERROR,
            error: axios.isAxiosError(error) && error.response?.data?.error
                ? error.response.data.error
                : 'File upload failed',
            meta: {
                fileName: file.name,
                fileSize: file.size,
                timestamp: new Date().toISOString()
            }
        };

        return errorResponse;
    }
};

/**
 * Check ML service health
 */
export const checkHealth = async (): Promise<boolean> => {
    try {
        const response = await apiClient.get('/health', { timeout: 5000 });
        return response.data?.status === 'ok';
    } catch (error) {
        console.error('Health check failed:', error);
        return false;
    }
};

/**
 * Stream chat response
 */
export const streamChatResponse = async (
    query: string,
    fileId?: string,
    filePath?: string,
    userId?: string,
    chatId?: string,
    messageId?: string,
    onMessage?: (token: string) => void,
    onError?: (error: string) => void,
    onComplete?: () => void
): Promise<void> => {
    try {
        // Prepare URL with query parameters
        const params = new URLSearchParams({
            query,
            ...(fileId && { file_id: fileId }),
            ...(filePath && { file_path: filePath }),
            ...(userId && { user_id: userId }),
            ...(chatId && { chat_id: chatId }),
            ...(messageId && { message_id: messageId })
        });

        const url = `${config.mlServiceUrl}/chat/stream?${params}`;

        // Create event source
        const EventSource = require('eventsource');
        const eventSource = new EventSource(url, {
            headers: {
                'Authorization': `Bearer ${process.env.ML_SERVICE_KEY || ''}`,
                'X-User-ID': userId || ''
            }
        });

        // Handle events
        eventSource.onmessage = (event: any) => {
            try {
                const data = JSON.parse(event.data);
                if (onMessage && data.token) {
                    onMessage(data.token);
                }
            } catch (e) {
                console.error('Error parsing stream message:', e);
                if (onMessage) {
                    onMessage(event.data);
                }
            }
        };

        eventSource.onerror = (error: any) => {
            console.error('Stream error:', error);
            if (onError) {
                onError(error.message || 'Stream connection error');
            }
            eventSource.close();
        };

        // Handle different event types
        eventSource.addEventListener('complete', () => {
            if (onComplete) {
                onComplete();
            }
            eventSource.close();
        });

        eventSource.addEventListener('error', (event: any) => {
            try {
                const data = JSON.parse(event.data);
                if (onError) {
                    onError(data.error || 'Unknown stream error');
                }
            } catch (e) {
                if (onError) {
                    onError('Stream error occurred');
                }
            }
            eventSource.close();
        });

        // Close event source after 10 minutes to prevent hanging connections
        setTimeout(() => {
            if (eventSource.readyState !== 2) { // 2 = closed
                console.warn('Closing stream after timeout');
                eventSource.close();
            }
        }, 600000);

        return eventSource;
    } catch (error) {
        console.error('Error setting up stream:', error);
        if (onError) {
            onError(error instanceof Error ? error.message : 'Error setting up stream');
        }
    }
};