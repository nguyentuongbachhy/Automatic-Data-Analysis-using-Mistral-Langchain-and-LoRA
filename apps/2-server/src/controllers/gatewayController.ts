// controllers/gatewayController.ts
import axios from 'axios';
import { Request, Response } from 'express';
import { AuthRequest } from '../middlewares/auth';
import { ApiResponseSchema, ChatResponseSchema } from '../schemas';
import { checkHealth, forwardRequest } from '../services/gatewayService';
import { jsonService } from '../services/jsonService';
import { ResponseStatus } from '../types';

/**
 * Base proxy request handler with consistent error handling and authentication validation
 */
const proxyBaseRequest = async (req: AuthRequest, res: Response, aiEndpoint: string, validateSchema?: any) => {
    try {
        const user = req.user;

        if (!user || !user.id) {
            res.status(401).json({
                status: ResponseStatus.ERROR,
                error: 'User not authenticated'
            });
            return;
        }

        // Add user info to the request
        const payload = {
            ...req.body,
            userId: user.id
        };

        // Forward request to AI service
        const response = await forwardRequest(
            aiEndpoint,
            req.method,
            payload,
            req.query,
            {
                // Add options for validation and transformation
                validateSchema: validateSchema || ApiResponseSchema
            }
        );

        // Return transformed result
        res.json(response);
    } catch (error) {
        console.error(`Gateway error for ${aiEndpoint}:`, error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error processing request',
            meta: {
                timestamp: new Date().toISOString(),
                endpoint: aiEndpoint
            }
        });
    }
};

/**
 * Proxy chat requests to AI service
 */
export const proxyChatRequest = async (req: AuthRequest, res: Response) => {
    try {
        // Kiểm tra xác thực
        const user = req.user;
        if (!user || !user.id) {
            res.status(401).json({
                status: ResponseStatus.ERROR,
                error: 'User not authenticated'
            });
            return;
        }

        // Handle streaming requests or LangChain requests
        if (req.query.stream === 'true' || req.path.includes('/stream')) {
            return await handleStreamRequest(req, res);
        }

        // Extract endpoint
        let endpoint = req.path.replace(/^\/api\/chat|^\/chat/, '');
        if (!endpoint || endpoint === '/') {
            endpoint = '/message';
        }

        // Map client endpoints to AI service endpoints
        let aiEndpoint = `/chat${endpoint}`;

        // Special case mapping
        if (endpoint.match(/^\/[a-f0-9-]+\/messages$/)) {
            const chatId = endpoint.split('/')[1];
            req.body.chatId = chatId;
            aiEndpoint = '/chat/message';
        }

        console.log(`Forwarding chat request to: ${aiEndpoint}`);

        const payload = {
            userId: user.id,
            ...req.body
        };

        // Đảm bảo các trường bắt buộc
        if (!payload.query) {
            payload.query = payload.content || "";
        }

        if (!payload.messages && !payload.message) {
            payload.messages = [];
        }

        const handledPayload = jsonService.toSnakeCase(payload);

        console.log(`Request payload after transformation:`, handledPayload);

        // Forward request to AI service
        const response = await forwardRequest(
            aiEndpoint,
            req.method,
            handledPayload,
            req.query,
            {
                validateSchema: endpoint.includes('/message') ? ChatResponseSchema : ApiResponseSchema
            }
        );

        // Return result
        res.json(response);
    } catch (error) {
        console.error('Chat gateway error:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error processing chat request',
            meta: { timestamp: new Date().toISOString() }
        });
    }
};

/**
 * Proxy analysis requests to AI service
 */
export const proxyAnalyzeRequest = async (req: AuthRequest, res: Response) => {
    try {

        const user = req.user

        if (!user || !user.id) {
            res.status(401).json({
                status: ResponseStatus.ERROR,
                error: 'User not authenticated'
            });
            return;
        }
        // Handle streaming requests specially
        if (req.query.stream === 'true' || req.path.includes('/stream')) {
            await handleStreamRequest(req, res);
            return
        }

        // Extract the path after /analyze
        let endpoint = req.path.replace(/^\/api\/analyze|^\/analyze/, '');
        if (!endpoint || endpoint === '/') {
            // Default endpoint for analysis
            endpoint = '/full';
        }

        // Map client endpoints to AI service endpoints
        let aiEndpoint;

        // Special case mappings for analyze
        if (endpoint.includes('/visualizations')) {
            aiEndpoint = '/chat/generate-visualization';
        } else if (endpoint.includes('/insights')) {
            aiEndpoint = '/chat/generate-insights';
        } else if (endpoint.includes('/forecast')) {
            aiEndpoint = '/chat/time-series-forecast';
        } else {
            // Default structure
            aiEndpoint = `/analyze${endpoint}`;
        }

        console.log(`Forwarding analysis request to: ${aiEndpoint}`);

        await proxyBaseRequest(req, res, aiEndpoint, ApiResponseSchema);
    } catch (error) {
        console.error('Analysis gateway error:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error processing analysis request',
            meta: { timestamp: new Date().toISOString() }
        });
    }
};

/**
 * Handle streaming requests for both chat and analysis
 */
const handleStreamRequest = async (req: AuthRequest, res: Response) => {
    const user = req.user;

    if (!user || !user.id) {
        res.status(401).json({
            status: ResponseStatus.ERROR,
            error: 'User not authenticated'
        });
        return;
    }

    try {
        // Set SSE headers
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        // Keep track of connection
        let isConnected = true;

        // Handle client disconnect
        req.on('close', () => {
            isConnected = false;
        });

        // Determine type (chat or analysis)
        const isChat = req.path.includes('/chat');
        const isAnalysis = req.path.includes('/analyze');

        if (isChat) {
            // Extract parameters from body
            const { query, fileId, chatId } = req.body || {};

            // Validate required fields
            if (!query && !req.body.is_initialization && !req.path.includes('/create')) {
                throw new Error('Query is required for chat messages');
            }

            // Tạo URL cho request
            const mlServiceUrl = process.env.ML_SERVICE_URL || 'http://localhost:8000';
            const streamUrl = `${mlServiceUrl}/chat/stream`;

            // Tạo request body - chuyển sang snake_case
            const requestBody = {
                query: query,
                user_id: user.id,
                chat_id: chatId,
                file_id: fileId,
                use_cache: true,
            };

            try {
                // Sử dụng axios để gửi POST request
                const response = await axios({
                    method: 'GET',
                    url: streamUrl,
                    data: requestBody,
                    headers: {
                        'Authorization': `Bearer ${process.env.ML_SERVICE_KEY || ''}`,
                        'X-User-ID': user.id,
                        'Content-Type': 'application/json'
                    },
                    responseType: 'stream'
                });

                // Pipe stream trực tiếp đến response
                response.data.pipe(res);

                // Xử lý sự kiện kết thúc stream
                response.data.on('end', () => {
                    if (isConnected) {
                        res.end();
                    }
                });

                // Xử lý lỗi stream
                response.data.on('error', (err: Error) => {
                    console.error('Stream error:', err);
                    if (isConnected) {
                        res.write(`event: error\ndata: ${JSON.stringify({ error: err.message })}\n\n`);
                        res.end();
                    }
                });
            } catch (error: any) {
                console.error('Stream request error details:', {
                    status: error.response?.status,
                    statusText: error.response?.statusText,
                    data: error.response?.data?.toString(), // Try to get raw data
                    message: error.message,
                    config: error.config // Log request config
                });

                const errorMessage = error.response
                    ? `AI service responded with ${error.response.status}: ${error.response.statusText}`
                    : error.message || 'Unknown error';

                if (isConnected) {
                    res.write(`event: error\ndata: ${JSON.stringify({ error: errorMessage })}\n\n`);
                    res.end();
                }
            }
        } else if (isAnalysis) {
            // Code xử lý analysis - phần này giữ nguyên, nhưng tôi đã cập nhật để sử dụng axios
            // Extract the file ID from path
            const fileId = req.path.includes('/stream/') ? req.path.split('/stream/')[1] : undefined;

            if (!fileId) {
                throw new Error('File ID is required for analysis streaming');
            }

            const { analysisType } = req.body || req.query;


            // Tạo URL đầy đủ cho request
            const mlServiceUrl = process.env.ML_SERVICE_URL || 'http://localhost:8000';
            const requestUrl = `${mlServiceUrl}/chat/stream-analysis/${fileId}`;

            try {
                // Sử dụng axios để gửi request
                const response = await axios({
                    method: 'POST',
                    url: requestUrl,
                    data: {
                        file_id: fileId,
                        user_id: user.id,
                        ...(analysisType && { analysis_type: analysisType })
                    },
                    headers: {
                        'Authorization': `Bearer ${process.env.ML_SERVICE_KEY || ''}`,
                        'X-User-ID': user.id
                    },
                    responseType: 'stream'
                });

                // Pipe stream trực tiếp đến response
                response.data.pipe(res);

                // Xử lý sự kiện kết thúc stream
                response.data.on('end', () => {
                    if (isConnected) {
                        res.end();
                    }
                });

                // Xử lý lỗi stream
                response.data.on('error', (err: Error) => {
                    console.error('Stream error:', err);
                    if (isConnected) {
                        res.write(`event: error\ndata: ${JSON.stringify({ error: err.message })}\n\n`);
                        res.end();
                    }
                });
            } catch (error: any) {
                console.error('Error streaming analysis:', error.message);

                const errorMessage = error.response
                    ? `AI service responded with ${error.response.status}: ${error.response.statusText}`
                    : error.message || 'Unknown error';

                if (isConnected) {
                    res.write(`event: error\ndata: ${JSON.stringify({ error: errorMessage })}\n\n`);
                    res.end();
                }
            }
        } else {
            throw new Error('Unknown streaming request type');
        }
    } catch (error) {
        console.error('Stream gateway error:', error);
        res.write(`event: error\ndata: ${JSON.stringify({
            error: error instanceof Error ? error.message : 'Error processing stream request'
        })}\n\n`);
        res.end();
    }
};

/**
 * Health check endpoint
 */
export const proxyHealthCheckRequest = async (req: Request, res: Response) => {
    try {
        const aiHealth = await checkHealth();

        res.json({
            status: ResponseStatus.SUCCESS,
            data: {
                ai_service: aiHealth,
                gateway: {
                    status: 'healthy',
                    timestamp: new Date().toISOString()
                }
            }
        });
    } catch (error) {
        console.error('Health check error:', error);
        res.status(500).json({
            status: ResponseStatus.ERROR,
            error: error instanceof Error ? error.message : 'Error checking health',
            data: {
                ai_service: { status: 'unhealthy' },
                gateway: {
                    status: 'healthy',
                    timestamp: new Date().toISOString()
                }
            }
        });
    }
};