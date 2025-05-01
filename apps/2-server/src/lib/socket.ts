// lib/socket.ts
import { MessageRole } from '@prisma/client';
import { EventSource } from 'eventsource';
import { Server as HttpServer } from 'http';
import { Server } from 'socket.io';
import prisma from '../lib/prisma';
import { verifyToken } from '../middlewares/auth';
import { jsonService } from '../services/jsonService';

let io: Server;

// Map để theo dõi active streams
const activeStreams = new Map();

export const initializeSocket = (server: HttpServer, corsOptions?: any) => {
    io = new Server(server, {
        cors: corsOptions || {
            origin: '*',
            methods: ['GET', 'POST'],
            credentials: true
        },
        transports: ['websocket', 'polling'],
        pingTimeout: 60000, // Tăng thời gian chờ ping
        pingInterval: 25000 // Giảm tần suất ping
    });

    // Middleware để xác thực người dùng qua token
    io.use(async (socket, next) => {
        try {
            const token = socket.handshake.auth.token ||
                socket.handshake.headers.authorization?.replace('Bearer ', '');

            if (!token) {
                return next(new Error('Authentication error: Token required'));
            }

            // Xác thực token và lấy thông tin user
            const user = await verifyToken(token);
            if (!user) {
                return next(new Error('Authentication error: Invalid token'));
            }

            // Lưu thông tin user vào socket để sử dụng sau này
            socket.data.user = user;
            next();
        } catch (error) {
            next(new Error('Authentication error'));
        }
    });

    io.on('connection', (socket) => {
        // Gửi event để xác nhận kết nối
        socket.emit('connection-status', {
            connected: true,
            socketId: socket.id,
            userId: socket.data?.user?.id
        });

        // Xử lý khi client join một chat room
        socket.on('join-chat', (chatId: string) => {
            socket.join(chatId);
            // Thông báo cho client biết đã join thành công
            socket.emit('joined-chat', { chatId, success: true });
        });

        // Xử lý gửi tin nhắn chat
        socket.on('send-message', (data: {
            chatId: string,
            message: string,
            fileId: string,
        }) => {
            // Xử lý tin nhắn chat với streaming
            processSocketMessage(socket, data).catch(err => {
                console.error('Error processing socket message:', err);
                socket.emit('chat-error', {
                    error: 'Lỗi khi xử lý tin nhắn',
                    chatId: data.chatId,
                });
            });
        });

        // Xử lý ping từ client
        socket.on('ping', () => {
            socket.emit('pong', { timestamp: Date.now() });
        });

        // Xử lý khi client yêu cầu cancel request
        socket.on('cancel-request', (data: { messageId: string, chatId: string }) => {
            const { messageId, chatId } = data;
            const streamKey = `${chatId}:${messageId}`;

            if (activeStreams.has(streamKey)) {
                const eventSource = activeStreams.get(streamKey);
                if (eventSource) {
                    // Đóng stream
                    eventSource.close();
                    activeStreams.delete(streamKey);

                    // Thông báo cho client
                    socket.emit('request-canceled', {
                        messageId,
                        chatId,
                        success: true
                    });
                }
            }
        });

        socket.on('disconnect', () => {
            // Clean up any active streams for this socket
            for (const [key, eventSource] of activeStreams.entries()) {
                if (key.includes(socket.id)) {
                    eventSource.close();
                    activeStreams.delete(key);
                }
            }
        });
    });

    return io;
};

export const getIO = () => {
    if (!io) {
        throw new Error('Socket.io not initialized');
    }
    return io;
};

/**
 * Xử lý tin nhắn chat gửi qua socket và chuyển tiếp đến AI service
 */
export const processSocketMessage = async (socket: any, data: {
    chatId: string,
    message: string,
    fileId: string
}) => {
    try {
        const { chatId, message, fileId } = data;
        const userId = socket.data?.user?.id;

        if (!userId) {
            socket.emit('chat-error', {
                error: 'Không có quyền truy cập'
            });
            return;
        }

        // Kiểm tra chat tồn tại và thuộc về user
        const chat = await prisma.chat.findUnique({
            where: {
                id: chatId,
                userId: userId
            },
            include: {
                file: true
            }
        });

        if (!chat) {
            socket.emit('chat-error', {
                error: 'Chat không tồn tại'
            });
            return;
        }

        // Lưu tin nhắn vào database
        const userMessage = await prisma.message.create({
            data: {
                chatId,
                role: MessageRole.USER,
                content: message,
                createdAt: (new Date()).toISOString(),
                updatedAt: (new Date()).toISOString()
            }
        });

        // Tạo tin nhắn trả lời trống để có ID cho streaming
        const assistantMessage = await prisma.message.create({
            data: {
                chatId,
                role: MessageRole.ASSISTANT,
                content: '',
                metadata: {
                    isStreaming: true
                },
                createdAt: (new Date()).toISOString(),
                updatedAt: (new Date()).toISOString()
            }
        });

        // Thông báo cho client về tin nhắn đã lưu
        socket.emit('message-sent', {
            messageId: userMessage.id,
            chatId,
            success: true
        });

        // Thông báo bắt đầu nhận phản hồi
        socket.emit('chat-response-start', {
            messageId: assistantMessage.id,
            chatId
        });

        try {
            // Khởi tạo stream từ AI service với đúng thứ tự tham số
            await setupChatStream(
                chatId,             // chat_id
                assistantMessage.id, // message_id
                userId,              // user_id
                message,             // query
                socket,              // socket
                fileId           // file_id (optional)
            );
        } catch (error) {
            console.error('Error setting up chat stream:', error);
            socket.emit('chat-error', {
                messageId: assistantMessage.id,
                chatId,
                error: 'Lỗi khi thiết lập streaming'
            });

            // Cập nhật tin nhắn assistant với lỗi
            await prisma.message.update({
                where: { id: assistantMessage.id },
                data: {
                    content: 'Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu của bạn.',
                    metadata: {
                        isStreaming: false,
                        error: error instanceof Error ? error.message : 'Unknown error'
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error in process socket message:', error);
        socket.emit('chat-error', {
            chatId: data.chatId,
            error: 'Lỗi server khi xử lý tin nhắn'
        });
    }
};

/**
 * Thiết lập streaming từ AI service và gửi cho client với timeout và retry
 * @param chatId ID của chat
 * @param messageId ID của message (cho assistant)
 * @param userId ID của user
 * @param query Nội dung câu hỏi/tin nhắn
 * @param socket Socket object để gửi kết quả về
 * @param fileId (optional) ID của file cần xử lý
 */
const setupChatStream = async (
    chatId: string,
    messageId: string,
    userId: string,
    query: string,
    socket: any,
    fileId?: string
) => {
    // Stream key để theo dõi và quản lý
    const streamKey = `${chatId}:${messageId}`;

    // Theo dõi thời gian bắt đầu và timeout
    const streamStartTime = Date.now();
    const STREAM_TIMEOUT = 120000; // 2 phút timeout
    let timeoutId: NodeJS.Timeout | null = null;

    try {
        // Xây dựng query params - phù hợp với chat_router.py
        const params = new URLSearchParams();
        params.append('query', query);
        params.append('user_id', userId);
        params.append('chat_id', chatId);
        params.append('message_id', messageId);
        if (fileId) params.append('file_id', fileId);

        // Import config để lấy ML service URL
        const config = await import('../config').then(m => m.default);
        const streamUrl = `${config.mlServiceUrl}/chat/stream?${params.toString()}`;

        // Tạo EventSource để kết nối đến stream
        const eventSource = new EventSource(streamUrl);

        // Lưu vào map để quản lý
        activeStreams.set(streamKey, eventSource);

        // Thiết lập timeout handler
        timeoutId = setTimeout(async () => {
            console.error(`Stream timeout for chat ${chatId}, message ${messageId}`);

            // Đóng stream
            eventSource.close();
            activeStreams.delete(streamKey);

            // Thông báo lỗi cho client
            socket.emit('chat-error', {
                messageId,
                chatId,
                error: 'Thời gian chờ phản hồi từ AI service đã hết'
            });

            // Cập nhật message trong database
            try {
                await prisma.message.update({
                    where: { id: messageId },
                    data: {
                        metadata: {
                            isStreaming: false,
                            error: 'Stream timeout',
                        }
                    }
                });
            } catch (dbError) {
                console.error('Error updating database after timeout:', dbError);
            }
        }, STREAM_TIMEOUT);

        // Theo dõi trạng thái connection
        let messageContent = '';
        let lastActivityTime = Date.now();

        // Xử lý message event từ AI service
        eventSource.addEventListener('message', async (event) => {
            try {
                lastActivityTime = Date.now();

                const data = JSON.parse(event.data);

                // Chuyển đổi từ snake_case về camelCase
                const transformedData = jsonService.transformResponse(data, {
                    convertToCamelCase: true
                });

                // Xử lý token streaming
                if ('token' in transformedData && transformedData.token !== undefined) {
                    messageContent += transformedData.token;

                    // Gửi token đến client
                    socket.emit('chat-response', {
                        messageId,
                        chatId,
                        content: transformedData.token,
                        done: 'done' in transformedData ? transformedData.done : false
                    });

                    // Nếu đã hoàn thành, cập nhật message trong DB
                    if ('done' in transformedData && transformedData.done) {
                        try {
                            await prisma.message.update({
                                where: { id: messageId },
                                data: {
                                    content: messageContent,
                                    metadata: {
                                        isStreaming: false,
                                        completedAt: new Date().toISOString()
                                    }
                                }
                            });
                        } catch (dbError) {
                            console.error('Error updating message after completion:', dbError);
                        }

                        // Xóa timeout và đóng stream
                        if (timeoutId) clearTimeout(timeoutId);
                        eventSource.close();
                        activeStreams.delete(streamKey);
                    }
                }
            } catch (error) {
                console.error('Error processing message event:', error);
            }
        });

        // Xử lý visualization event từ AI service
        eventSource.addEventListener('chat-visualizations', async (event) => {
            try {
                lastActivityTime = Date.now();

                const data = JSON.parse(event.data);

                // Chuyển đổi từ snake_case về camelCase
                const transformedData = jsonService.transformResponse(data, {
                    convertToCamelCase: true
                });

                // Gửi visualizations đến client
                socket.emit('chat-visualizations', {
                    messageId,
                    chatId,
                    visualizations: 'visualizations' in transformedData ? transformedData.visualizations : []
                });

                // Cập nhật metadata của message - sử dụng transaction để tránh race condition
                try {
                    // Lấy message hiện tại
                    const currentMessage = await prisma.message.findUnique({
                        where: { id: messageId },
                        select: { metadata: true }
                    });

                    // Kết hợp metadata hiện tại với metadata mới
                    const updatedMetadata = {
                        ...(typeof currentMessage?.metadata === 'object' && currentMessage?.metadata !== null ? currentMessage.metadata : {}),
                        visualizations: 'visualizations' in transformedData ? transformedData.visualizations : []
                    };

                    // Cập nhật message
                    await prisma.message.update({
                        where: { id: messageId },
                        data: {
                            metadata: {
                                ...updatedMetadata,
                                visualizations: 'visualizations' in transformedData && Array.isArray(transformedData.visualizations)
                                    ? transformedData.visualizations
                                    : []
                            }
                        }
                    });
                } catch (dbError) {
                    console.error('Error updating message metadata for visualizations:', dbError);
                }
            } catch (error) {
                console.error('Error processing visualizations:', error);
            }
        });

        // Xử lý insight event từ AI service
        eventSource.addEventListener('chat-insights', async (event) => {
            try {
                lastActivityTime = Date.now();

                const data = JSON.parse(event.data);

                // Chuyển đổi từ snake_case về camelCase
                const transformedData = jsonService.transformResponse(data, {
                    convertToCamelCase: true
                });

                // Gửi insights đến client
                socket.emit('chat-insights', {
                    messageId,
                    chatId,
                    insights: 'insights' in transformedData && Array.isArray(transformedData.insights)
                        ? transformedData.insights
                        : []
                });

                // Cập nhật metadata của message - tương tự như visualizations
                try {
                    // Lấy message hiện tại
                    const currentMessage = await prisma.message.findUnique({
                        where: { id: messageId },
                        select: { metadata: true }
                    });

                    // Kết hợp metadata hiện tại với metadata mới
                    const updatedMetadata = {
                        ...(typeof currentMessage?.metadata === 'object' && currentMessage?.metadata !== null ? currentMessage.metadata : {}),
                        insights: 'insights' in transformedData && Array.isArray(transformedData.insights)
                            ? transformedData.insights
                            : []
                    };

                    // Cập nhật message
                    await prisma.message.update({
                        where: { id: messageId },
                        data: {
                            metadata: updatedMetadata
                        }
                    });
                } catch (dbError) {
                    console.error('Error updating message metadata for insights:', dbError);
                }
            } catch (error) {
                console.error('Error processing insights:', error);
            }
        });

        // Xử lý error event từ AI service
        eventSource.addEventListener('error', async (event) => {
            try {
                let errorMessage = 'Lỗi từ AI service';
                try {
                    if ('data' in event && event.data) {
                        const data = typeof event.data === 'string' ? JSON.parse(event.data) : {};
                        errorMessage = data.error || errorMessage;
                    }
                } catch (e) {
                    // Nếu không parse được JSON, sử dụng message mặc định
                }

                socket.emit('chat-error', {
                    messageId,
                    chatId,
                    error: errorMessage
                });

                // Cập nhật tin nhắn với thông báo lỗi
                try {
                    await prisma.message.update({
                        where: { id: messageId },
                        data: {
                            content: messageContent || 'Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu của bạn.',
                            metadata: {
                                isStreaming: false,
                                error: errorMessage
                            }
                        }
                    });
                } catch (dbError) {
                    console.error('Error updating message after error event:', dbError);
                }

                // Xóa timeout và đóng stream
                if (timeoutId) clearTimeout(timeoutId);
                eventSource.close();
                activeStreams.delete(streamKey);
            } catch (error) {
                console.error('Error handling error event:', error);
            }
        });

        // Xử lý complete event từ AI service
        eventSource.addEventListener('complete', async () => {
            try {
                // Gửi sự kiện hoàn thành đến client
                socket.emit('complete', {
                    messageId,
                    chatId
                });

                // Cập nhật tin nhắn nếu cần
                if (messageContent) {
                    try {
                        await prisma.message.update({
                            where: { id: messageId },
                            data: {
                                content: messageContent,
                                metadata: {
                                    isStreaming: false,
                                    completedAt: new Date().toISOString()
                                }
                            }
                        });
                    } catch (dbError) {
                        console.error('Error updating message after completion event:', dbError);
                    }
                }

                // Xóa timeout và đóng stream
                if (timeoutId) clearTimeout(timeoutId);
                eventSource.close();
                activeStreams.delete(streamKey);
            } catch (error) {
                console.error('Error handling complete event:', error);
            }
        });

        // Xử lý khi kết nối bị đóng
        eventSource.onerror = async (error) => {
            console.error('EventSource error:', error);

            // Chỉ cập nhật message nếu chưa hoàn thành
            try {
                const message = await prisma.message.findUnique({
                    where: { id: messageId },
                    select: { metadata: true }
                }) as { metadata: { isStreaming?: boolean } | null };

                if (message?.metadata && message.metadata.isStreaming !== false) {
                    // Cập nhật tin nhắn nếu stream bị ngắt
                    await prisma.message.update({
                        where: { id: messageId },
                        data: {
                            content: messageContent || 'Tin nhắn bị ngắt kết nối.',
                            metadata: {
                                isStreaming: false,
                                error: 'Kết nối đến AI service bị ngắt'
                            }
                        }
                    });

                    socket.emit('chat-error', {
                        messageId,
                        chatId,
                        error: 'Kết nối đến AI service bị ngắt'
                    });
                }
            } catch (dbError) {
                console.error('Error updating message after connection close:', dbError);
            }

            // Xóa timeout và đóng stream
            if (timeoutId) clearTimeout(timeoutId);
            eventSource.close();
            activeStreams.delete(streamKey);
        };

        // Giám sát thời gian kết nối và hoạt động của stream
        const activityCheckInterval = setInterval(async () => {
            const currentTime = Date.now();
            const inactiveTime = currentTime - lastActivityTime;
            const totalTime = currentTime - streamStartTime;

            // Nếu không có hoạt động trong 30 giây hoặc đã quá 2 phút
            if (inactiveTime > 30000 || totalTime > STREAM_TIMEOUT) {
                console.warn(`Stream inactive for ${inactiveTime / 1000}s or total time ${totalTime / 1000}s exceeded`);

                clearInterval(activityCheckInterval);
                if (timeoutId) clearTimeout(timeoutId);

                // Đóng stream nếu còn mở
                if (activeStreams.has(streamKey)) {
                    eventSource.close();
                    activeStreams.delete(streamKey);

                    // Thông báo cho client
                    socket.emit('chat-error', {
                        messageId,
                        chatId,
                        error: 'Kết nối đến AI service bị ngắt do không hoạt động'
                    });

                    // Cập nhật message trong DB nếu đang streaming
                    try {
                        const message = await prisma.message.findUnique({
                            where: { id: messageId },
                            select: { metadata: true }
                        }) as { metadata: { isStreaming?: boolean } | null };

                        if (message?.metadata && message.metadata.isStreaming !== false) {
                            await prisma.message.update({
                                where: { id: messageId },
                                data: {
                                    content: messageContent || 'Tin nhắn bị ngắt kết nối do không hoạt động.',
                                    metadata: {
                                        isStreaming: false,
                                        error: 'Kết nối bị đóng do không hoạt động'
                                    }
                                }
                            });
                        }
                    } catch (dbError) {
                        console.error('Error updating message after inactivity:', dbError);
                    }
                }
            }
        }, 10000); // Kiểm tra mỗi 10 giây

        // Đảm bảo interval sẽ được xóa
        eventSource.addEventListener('open', () => {
            // Reset last activity time khi stream mở
            lastActivityTime = Date.now();
        });

        eventSource.addEventListener('end', () => {
            clearInterval(activityCheckInterval);
        });

    } catch (error) {
        console.error('Error setting up chat stream:', error);

        // Cleanup
        if (timeoutId) clearTimeout(timeoutId);
        activeStreams.delete(streamKey);

        throw error;
    }
};