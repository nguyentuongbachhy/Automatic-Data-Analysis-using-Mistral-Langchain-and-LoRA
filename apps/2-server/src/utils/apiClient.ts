import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

export class APIClient {
    private client: AxiosInstance;
    private baseUrl: string;

    constructor(baseUrl: string, config?: AxiosRequestConfig) {
        this.baseUrl = baseUrl;
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 60000, // 60 seconds default timeout
            headers: {
                'Content-Type': 'application/json',
            },
            ...config,
        });

        // Add request interceptor for logging
        this.client.interceptors.request.use(
            (config) => {
                console.log(`API Request to: ${config.url}`);
                return config;
            },
            (error) => {
                console.error('API Request Error:', error);
                return Promise.reject(error);
            }
        );

        // Add response interceptor for error handling
        this.client.interceptors.response.use(
            (response) => {
                return response;
            },
            (error) => {
                // Enhance error message with more details
                let errorMessage = 'Request failed';

                if (error.response) {
                    // The request was made and the server responded with a status code
                    // that falls out of the range of 2xx
                    errorMessage = `Error ${error.response.status}: ${error.response.statusText}`;
                    console.error('API Error Response:', error.response.data);
                } else if (error.request) {
                    // The request was made but no response was received
                    errorMessage = 'No response received from server';
                    console.error('API Error Request:', error.request);
                } else {
                    // Something happened in setting up the request that triggered an Error
                    errorMessage = error.message;
                    console.error('API Error Message:', error.message);
                }

                // Create a new error with enhanced message
                const enhancedError = new Error(errorMessage);
                enhancedError.stack = error.stack;

                return Promise.reject(enhancedError);
            }
        );
    }

    async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
        try {
            const response: AxiosResponse<T> = await this.client.get(url, config);
            return response.data;
        } catch (error) {
            throw this.handleError(error, `GET ${url}`);
        }
    }

    async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
        try {
            const response: AxiosResponse<T> = await this.client.post(url, data, config);
            return response.data;
        } catch (error) {
            throw this.handleError(error, `POST ${url}`);
        }
    }

    async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
        try {
            const response: AxiosResponse<T> = await this.client.put(url, data, config);
            return response.data;
        } catch (error) {
            throw this.handleError(error, `PUT ${url}`);
        }
    }

    async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
        try {
            const response: AxiosResponse<T> = await this.client.delete(url, config);
            return response.data;
        } catch (error) {
            throw this.handleError(error, `DELETE ${url}`);
        }
    }

    private handleError(error: any, request: string): Error {
        // Log detailed error
        console.error(`API Error in ${request}:`, error);

        // Return a more user-friendly error
        if (error.response) {
            return new Error(`Request failed with status ${error.response.status}`);
        }
        if (error.request) {
            return new Error('No response received from server');
        }
        return new Error(error.message || 'Unknown error occurred');
    }
}

export default APIClient;