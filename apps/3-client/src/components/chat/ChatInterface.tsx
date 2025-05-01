import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ScrollArea } from "../../components/ui/scroll-area";
import { useSocket } from "../../contexts/SocketContext";
import { useAuth } from "../../hooks/use-auth"; // Thêm import Auth hook
import {
    getChatMessages,
    sendChatMessage,
    streamChatMessage // Thêm import này
} from "../../services/api";
import {
    ChatResponse, // Thêm ChatResponse interface 
    InsightData,
    Message,
    MessageRole,
    VisualizationData
} from "../../types";


import { Button } from "../ui/button";
import ChatInput from "./ChatInput";
import ChatMessage from "./ChatMessage";

interface ChatInterfaceProps {
    chatId?: string;
    fileId?: string;
    filePath?: string;
}

// Constants
const WELCOME_MESSAGE_ID = "welcome";
const RESPONSE_TIMEOUT = 45000; // 45 seconds
const FORCE_CLEAR_TIMEOUT = 5000; // 5 seconds

// Helper function to create a message object
const createMessage = (
    role: MessageRole,
    content: string,
    chatId: string,
    id: string = crypto.randomUUID()
): Message => ({
    id,
    chatId,
    role,
    content,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    metadata: {}
});

const ChatInterface = ({ chatId, fileId }: ChatInterfaceProps) => {
    // Lấy thông tin authentication
    const { user } = useAuth();

    if (!chatId) {
        return (<p>Error: Missing ChatId</p>)
    }

    // -------- STATE --------
    // Lưu trữ các tin nhắn hiển thị trong chat
    const [messages, setMessages] = useState<Message[]>([
        createMessage(
            MessageRole.ASSISTANT,
            fileId
                ? "Hello! I have analyzed your data file. You can ask any questions about the data, create charts, or ask for insights."
                : "Hello! I am an AI data analysis assistant. Please upload the data file to get started.",
            WELCOME_MESSAGE_ID
        ),
    ]);
    // Theo dõi trạng thái đang xử lý của AI
    const [isThinking, setIsThinking] = useState(false);
    // ID của tin nhắn hiện tại đang được xử lý
    const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);
    // Thêm state để lưu trữ EventSource instance
    const [eventSource, setEventSource] = useState<EventSource | null>(null);

    // -------- REFS --------
    // Ref để scroll đến tin nhắn cuối cùng
    const messagesEndRef = useRef<HTMLDivElement>(null);
    // Quản lý timeout cho các hoạt động không đồng bộ
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);
    // Lưu thời điểm hoạt động cuối cùng để kiểm tra timeout
    const lastActivityRef = useRef<number>(Date.now());

    // -------- SOCKET CONNECTION --------
    // Sử dụng context để lấy socket connection
    const { socket, isConnected } = useSocket();

    // -------- REACT QUERY: MUTATIONS & QUERIES --------

    // Lấy tin nhắn của chat
    const { data: messagesData, isLoading: isLoadingMessages } = useQuery({
        queryKey: ["chat-messages", chatId],
        queryFn: () => getChatMessages(chatId, true),
        enabled: !!chatId,
        staleTime: 10000, // Only refetch after 10 seconds
    });

    // Gửi tin nhắn qua HTTP API
    const sendMessageMutation = useMutation({
        mutationFn: (content: string) => sendChatMessage(chatId, content, fileId),
        onSuccess: (response) => {
            console.log(response);
            // Lấy ID của tin nhắn đã được lưu trong database
            setCurrentMessageId(response.id);

            // Nếu đã lưu trên server mà không thấy tin nhắn trong UI, thêm vào
            if (response?.response && !messages.some(msg => msg.id === response.id)) {
                // Tạo tin nhắn đầy đủ từ phản hồi
                const assistantMessage: Message = {
                    id: response.id,
                    chatId: chatId,
                    role: MessageRole.ASSISTANT,
                    content: response.response,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                    metadata: {
                        visualizations: response.visualizations || [],
                        insights: response.insights || []
                    }
                };

                addMessage(assistantMessage);
            }

            // Signal completion
            setIsThinking(false);
        },
        onError: (error) => {
            console.error("Error sending message:", error);

            const errorMessageId = `error-${Date.now()}`;
            addMessage(
                createMessage(
                    MessageRole.ASSISTANT,
                    "Sorry, there was an error processing your request. Please try again later.",
                    errorMessageId
                )
            );

            handleError({
                error: "Sorry, there was an error processing your request. Please try again later.",
                clientMessageId: errorMessageId
            });
        }
    });

    // -------- HELPER FUNCTIONS --------

    // Scroll to bottom khi có tin nhắn mới
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, []);

    // Thêm tin nhắn mới vào state
    const addMessage = useCallback((message: Message) => {
        setMessages(prev => [...prev, message]);
    }, []);

    // Cập nhật tin nhắn đã có
    const updateMessage = useCallback((messageId: string, updater: (message: Message) => Message) => {
        setMessages((prevMessages) => {
            const index = prevMessages.findIndex(msg => msg.id === messageId);
            if (index === -1) return prevMessages;

            const newMessages = [...prevMessages];
            newMessages[index] = updater(newMessages[index]);
            return newMessages;
        });
    }, []);

    // Clear timeout hiện tại
    const clearTimeout = useCallback(() => {
        if (timeoutRef.current) {
            window.clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
    }, []);

    // Reset timeout và đặt timeout mới
    const resetTimeout = useCallback(() => {
        // Cập nhật timestamp hoạt động gần nhất
        lastActivityRef.current = Date.now();

        // Xóa timeout hiện tại
        clearTimeout();

        // Đặt timeout mới để kiểm tra không hoạt động
        timeoutRef.current = setTimeout(() => {
            const timeSinceLastActivity = Date.now() - lastActivityRef.current;

            if (timeSinceLastActivity > 10000) {
                setIsThinking(false);
                setCurrentMessageId(null);
                addMessage(
                    createMessage(
                        MessageRole.ASSISTANT,
                        "Sorry, I didn't get a response from the server. Please try again later.",
                        chatId
                    )
                );
            }
        }, RESPONSE_TIMEOUT);
    }, [addMessage, clearTimeout]);

    // -------- EVENT HANDLERS --------

    // Xử lý khi người dùng gửi tin nhắn - Cập nhật sử dụng streamChatMessage
    const handleSendMessage = useCallback(async (content: string) => {
        // Đóng EventSource hiện tại nếu có
        if (eventSource) {
            eventSource.close();
            setEventSource(null);
        }

        // Thêm tin nhắn người dùng vào danh sách
        const userMessage = createMessage(MessageRole.USER, content, chatId);
        addMessage(userMessage);
        setIsThinking(true);
        resetTimeout();
        setCurrentMessageId(userMessage.id);

        // Tạo một tin nhắn trống của assistant để cập nhật dần dần
        const tempAssistantMessageId = `assistant-${Date.now()}`;
        const assistantMessage = createMessage(
            MessageRole.ASSISTANT,
            "",
            chatId,
            tempAssistantMessageId
        );
        addMessage(assistantMessage);

        // Sử dụng socket nếu đã kết nối, ngược lại sử dụng streamChatMessage
        if (socket && isConnected) {
            socket.emit('send-message', {
                chatId: chatId,
                message: content,
                fileId,
                clientMessageId: userMessage.id,
                use_langchain: true,
                show_thinking: true
            });
        } else {
            try {
                // Tạo các handlers
                const onToken = (token: string) => {
                    updateMessage(tempAssistantMessageId, (msg) => ({
                        ...msg,
                        content: msg.content + token
                    }));
                    resetTimeout();
                };

                const onComplete = (response: ChatResponse) => {
                    // Cập nhật tin nhắn với nội dung cuối cùng và các visualizations/insights
                    updateMessage(tempAssistantMessageId, (msg) => ({
                        ...msg,
                        id: response.id || tempAssistantMessageId, // Cập nhật ID nếu có
                        content: response.response || msg.content,
                        metadata: {
                            ...msg.metadata,
                            visualizations: response.visualizations,
                            insights: response.insights
                        }
                    }));

                    // Cập nhật trạng thái khi hoàn tất
                    setIsThinking(false);
                    setCurrentMessageId(null);
                    clearTimeout();

                    // Đóng và xóa EventSource
                    if (eventSource) {
                        eventSource.close();
                        setEventSource(null);
                    }
                };

                const onError = (error: string) => {
                    updateMessage(tempAssistantMessageId, (msg) => ({
                        ...msg,
                        content: error || "An error occurred while processing your request."
                    }));

                    // Cập nhật trạng thái khi có lỗi
                    setIsThinking(false);
                    setCurrentMessageId(null);
                    clearTimeout();

                    // Đóng và xóa EventSource
                    if (eventSource) {
                        eventSource.close();
                        setEventSource(null);
                    }
                };

                // Sử dụng streamChatMessage API dựa theo signature thực tế
                const source = await streamChatMessage(
                    chatId,
                    content,
                    fileId,
                    user?.id, // Truyền userId từ auth context
                    userMessage.id, // messageId
                    onToken,
                    onComplete,
                    onError
                );

                // Lưu EventSource instance
                setEventSource(source);
            } catch (error) {
                console.error("Error setting up stream:", error);

                // Cập nhật tin nhắn với thông báo lỗi
                updateMessage(tempAssistantMessageId, (msg) => ({
                    ...msg,
                    content: "Sorry, there was an error setting up the conversation stream."
                }));

                // Cập nhật trạng thái
                setIsThinking(false);
                setCurrentMessageId(null);
                clearTimeout();
            }
        }
    }, [
        addMessage,
        resetTimeout,
        socket,
        isConnected,
        chatId,
        fileId,
        updateMessage,
        clearTimeout,
        eventSource
    ]);

    // Hủy trạng thái đang suy nghĩ
    const handleCancelThinking = useCallback(() => {
        clearTimeout();
        setIsThinking(false);
        setCurrentMessageId(null);

        // Đóng EventSource nếu đang streaming
        if (eventSource) {
            eventSource.close();
            setEventSource(null);
        }
    }, [clearTimeout, eventSource]);

    // Xử lý khi stream hoàn tất
    const handleCompletion = useCallback(() => {
        console.log("Chat completion received");
        setIsThinking(false);
        setCurrentMessageId(null);
        clearTimeout();

        // Đóng EventSource khi hoàn tất
        if (eventSource) {
            eventSource.close();
            setEventSource(null);
        }
    }, [clearTimeout, eventSource]);

    // Xử lý lỗi từ stream
    const handleError = useCallback((data: {
        messageId?: string;
        clientMessageId?: string;
        error?: string
    }) => {
        console.error("Chat error:", data);

        const targetMessageId = data.clientMessageId || currentMessageId || data.messageId;

        if (targetMessageId) {
            updateMessage(targetMessageId, (msg) => ({
                ...msg,
                content: data.error || "There was an error processing the request."
            }));
        } else {
            const errorMessage = createMessage(
                MessageRole.ASSISTANT,
                data.error || "There was an error processing the request.",
                chatId
            );
            addMessage(errorMessage);
        }

        handleCompletion();
    }, [currentMessageId, handleCompletion, updateMessage, addMessage]);

    // Xử lý phản hồi chat từ stream
    const handleChatResponse = useCallback((data: {
        messageId?: string;
        content?: string;
        token?: string;
        done?: boolean;
        error?: string;
        clientMessageId?: string;
    }) => {
        console.log("Received chat response:", data);
        resetTimeout();

        // Xác định message ID mục tiêu
        const targetMessageId = data.clientMessageId || currentMessageId || data.messageId;
        const token = data.token || data.content || "";

        if (targetMessageId) {
            setMessages(prevMessages => {
                const existingMessageIndex = prevMessages.findIndex(msg => msg.id === targetMessageId);

                if (existingMessageIndex >= 0) {
                    // Cập nhật tin nhắn hiện có
                    const updatedMessages = [...prevMessages];
                    const existingMessage = updatedMessages[existingMessageIndex];
                    updatedMessages[existingMessageIndex] = {
                        ...existingMessage,
                        content: data.error || ((existingMessage.content || "") + token)
                    };
                    return updatedMessages;
                } else if (token || data.error) {
                    // Tạo tin nhắn mới nếu không tìm thấy ID
                    return [...prevMessages, createMessage(
                        MessageRole.ASSISTANT,
                        token || data.error || "",
                        targetMessageId
                    )];
                }
                return prevMessages;
            });

            if (data.done) {
                handleCompletion();
            }
        } else if (token || data.error) {
            // Nếu không có ID để xử lý, tạo tin nhắn mới
            addMessage(
                createMessage(
                    MessageRole.ASSISTANT,
                    token || data.error || "",
                    chatId
                )
            );

            if (data.done) {
                handleCompletion();
            }
        }
    }, [currentMessageId, handleCompletion, resetTimeout, addMessage]);

    // Xử lý khi nhận được visualizations từ stream
    const handleVisualizations = useCallback((data: {
        messageId?: string;
        clientMessageId?: string;
        visualizations?: VisualizationData[];
    }) => {
        console.log("Received visualizations:", data);
        resetTimeout();

        // Xác định ID tin nhắn cần cập nhật
        const targetMessageId = data.clientMessageId || currentMessageId || data.messageId;

        if (targetMessageId && data.visualizations && data.visualizations.length > 0) {
            updateMessage(targetMessageId, (msg) => ({
                ...msg,
                metadata: {
                    ...msg.metadata,
                    visualizations: data.visualizations
                }
            }));
        }
    }, [currentMessageId, resetTimeout, updateMessage]);

    // Xử lý khi nhận được insights từ stream
    const handleInsights = useCallback((data: {
        messageId?: string;
        clientMessageId?: string;
        insights?: InsightData[];
    }) => {
        console.log("Received insights:", data);
        resetTimeout();

        // Xác định ID tin nhắn cần cập nhật
        const targetMessageId = data.clientMessageId || currentMessageId || data.messageId;

        if (targetMessageId && data.insights && data.insights.length > 0) {
            updateMessage(targetMessageId, (msg) => ({
                ...msg,
                metadata: {
                    ...msg.metadata,
                    insights: data.insights
                }
            }));
        }
    }, [currentMessageId, resetTimeout, updateMessage]);

    // -------- EFFECTS --------

    // Cập nhật tin nhắn từ lịch sử chat
    useEffect(() => {
        if (messagesData && Array.isArray(messagesData) && messagesData.length > 0) {
            setMessages(prev => {
                // Nếu chỉ có tin nhắn welcome, thay thế bằng lịch sử từ server
                if (prev.length === 1 && prev[0].id === WELCOME_MESSAGE_ID) {
                    // Xử lý các tin nhắn từ server
                    const processedMessages = messagesData.map(msg => {
                        // Chuẩn hóa role từ CSDL
                        let normalizedMessage = { ...msg };

                        // Xử lý role từ chuỗi thành enum MessageRole
                        if (typeof normalizedMessage.role === 'string') {
                            const roleStr = normalizedMessage.role.toUpperCase();

                            // Chuyển đổi role string thành MessageRole enum
                            if (roleStr === 'USER') {
                                normalizedMessage.role = MessageRole.USER;
                            } else if (roleStr === 'ASSISTANT') {
                                normalizedMessage.role = MessageRole.ASSISTANT;
                            } else if (roleStr === 'SYSTEM') {
                                normalizedMessage.role = MessageRole.SYSTEM;
                            } else {
                                // Mặc định USER nếu không xác định được
                                normalizedMessage.role = MessageRole.USER;
                            }
                        }

                        return normalizedMessage;
                    });

                    return processedMessages;
                }

                // Tìm và thêm tin nhắn mới
                const existingIds = new Set(prev.map(msg => msg.id));
                const newMessages = messagesData
                    .filter(msg => !existingIds.has(msg.id))
                    .map(msg => {
                        // Chuẩn hóa role cho tin nhắn mới
                        let normalizedMessage = { ...msg };

                        if (typeof normalizedMessage.role === 'string') {
                            const roleStr = normalizedMessage.role.toUpperCase();

                            if (roleStr === 'USER') {
                                normalizedMessage.role = MessageRole.USER;
                            } else if (roleStr === 'ASSISTANT') {
                                normalizedMessage.role = MessageRole.ASSISTANT;
                            } else if (roleStr === 'SYSTEM') {
                                normalizedMessage.role = MessageRole.SYSTEM;
                            } else {
                                normalizedMessage.role = MessageRole.USER;
                            }
                        }

                        return normalizedMessage;
                    });

                if (newMessages.length > 0) {
                    return [...prev, ...newMessages];
                }

                return prev;
            });
        }
    }, [messagesData]);


    // Thiết lập socket event listeners
    useEffect(() => {
        if (!socket || !isConnected) return;

        // Cache lại các handler hiện tại để tránh re-attach
        const currentHandlers = {
            chatResponse: handleChatResponse,
            chatVisualizations: handleVisualizations,
            chatInsights: handleInsights,
            chatError: handleError,
            completion: handleCompletion
        };

        // Tạo các event handler từ handlers hiện tại
        const onChatResponse = (data: any) => currentHandlers.chatResponse(data);
        const onVisualizations = (data: any) => currentHandlers.chatVisualizations(data);
        const onInsights = (data: any) => currentHandlers.chatInsights(data);
        const onError = (data: any) => currentHandlers.chatError(data);
        const onComplete = () => currentHandlers.completion();

        // Thêm listener cho các event DB
        const onDbSaved = (data: any) => {
            console.log("Message saved to database:", data);
            // Nếu muốn, có thể cập nhật UI hoặc thực hiện hành động bổ sung ở đây
        };

        // Listener cho connection-status và joined-chat
        socket.on('connection-status', (data) => {
            console.log('Socket connection status:', data);
        });

        socket.on('joined-chat', (data) => {
            console.log('Joined chat room:', data);
        });

        // Attach stable listeners
        socket.on("chat-response", onChatResponse);
        socket.on("chat-visualizations", onVisualizations);
        socket.on("chat-insights", onInsights);
        socket.on("chat-error", onError);
        socket.on("complete", onComplete);
        socket.on("db_saved", onDbSaved);

        return () => {
            // Remove listeners khi component unmount
            socket.off("chat-response", onChatResponse);
            socket.off("chat-visualizations", onVisualizations);
            socket.off("chat-insights", onInsights);
            socket.off("chat-error", onError);
            socket.off("complete", onComplete);
            socket.off("db_saved", onDbSaved);
            socket.off("connection-status");
            socket.off("joined-chat");

            clearTimeout();
        };
    }, [socket, isConnected, clearTimeout, handleChatResponse, handleVisualizations, handleInsights, handleError, handleCompletion]);

    // Tham gia chat room khi có chatId
    useEffect(() => {
        if (socket && isConnected && chatId) {
            socket.emit('join-chat', chatId);
        }
    }, [socket, isConnected, chatId]);

    // Force clear message ID sau khi hoàn tất
    useEffect(() => {
        if (currentMessageId && !isThinking) {
            const forceClearTimer = window.setTimeout(() => {
                setCurrentMessageId(null);
            }, FORCE_CLEAR_TIMEOUT);

            return () => window.clearTimeout(forceClearTimer);
        }
    }, [currentMessageId, isThinking]);

    // Scroll to bottom khi tin nhắn thay đổi
    useEffect(() => {
        const scrollTimer = setTimeout(() => {
            scrollToBottom();
        }, 100);

        return () => window.clearTimeout(scrollTimer);
    }, [messages, scrollToBottom]);

    // Cleanup EventSource khi component unmount
    useEffect(() => {
        return () => {
            if (eventSource) {
                eventSource.close();
            }
        };
    }, [eventSource]);

    // Render
    return (
        <div className="flex flex-col h-full">
            <ScrollArea className="flex-1 pr-4">
                <div className="space-y-4 pb-4">
                    {isLoadingMessages ? (
                        <div className="flex items-center justify-center p-4">
                            <Loader2 className="h-5 w-5 animate-spin mr-2" />
                            <span className="text-sm text-muted-foreground">Loading...</span>
                        </div>
                    ) : (
                        messages.map((message) => (
                            <ChatMessage key={message.id} message={message} />
                        ))
                    )}

                    {isThinking && (
                        <div className="flex items-center justify-between text-sm text-muted-foreground p-4 bg-muted/30 rounded-lg">
                            <div className="flex items-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                <span>AI is thinking...</span>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleCancelThinking}
                                className="h-7 px-2"
                            >
                                <X className="h-3.5 w-3.5 mr-1" />
                                Cancel
                            </Button>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </ScrollArea>

            <div className="pt-4">
                <ChatInput
                    onSendMessage={handleSendMessage}
                    disabled={
                        sendMessageMutation.isPending ||
                        isThinking ||
                        isLoadingMessages
                    }
                    placeholder="Ask about your data..."
                />
            </div>
        </div>
    );
};

export default ChatInterface;