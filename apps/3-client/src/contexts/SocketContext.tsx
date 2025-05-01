// apps/client/src/contexts/SocketContext.tsx
import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '../hooks/use-auth';

interface SocketContextType {
    socket: Socket | null;
    isConnected: boolean;
    reconnect: () => void;
    lastError: string | null;
    connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
}

const SocketContext = createContext<SocketContextType>({
    socket: null,
    isConnected: false,
    reconnect: () => { },
    lastError: null,
    connectionStatus: 'disconnected'
});

export const SocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const [lastError, setLastError] = useState<string | null>(null);
    const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
    const { isAuthenticated, user } = useAuth();

    const socketRef = useRef<Socket | null>(null);
    const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const isInitializedRef = useRef<boolean>(false);

    // Tạo function để khởi tạo socket connection
    const initializeSocket = () => {
        // Nếu đã khởi tạo socket trước đó và vẫn còn kết nối, không khởi tạo lại
        if (isInitializedRef.current && socketRef.current?.connected) {
            return () => { }; // Return empty cleanup function
        }

        const SOCKET_URL = import.meta.env.VITE_WS_URL || window.location.origin;
        const token = localStorage.getItem('auth-token');

        if (isAuthenticated && user && token) {
            // Cleanup previous socket if exists
            if (socketRef.current) {
                socketRef.current.disconnect();
            }

            // Cleanup previous ping interval
            if (pingIntervalRef.current) {
                clearInterval(pingIntervalRef.current);
                pingIntervalRef.current = null;
            }

            // Cập nhật trạng thái
            setConnectionStatus('connecting');
            setLastError(null);

            // Khởi tạo socket với retry và ping options
            const socketIo = io(SOCKET_URL, {
                autoConnect: true,
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: 5,
                reconnectionDelayMax: 5000,
                randomizationFactor: 0.5,
                timeout: 60000, // Tăng timeout lên 60s
                auth: {
                    token, // Truyền token vào socket để xác thực
                },
                extraHeaders: {
                    Authorization: `Bearer ${token}`, // Truyền token qua header
                }
            });

            // Các event listeners
            socketIo.on('connect', () => {
                // Cập nhật trạng thái kết nối
                setIsConnected(true);
                setConnectionStatus('connected');
                setLastError(null);
                console.log('Socket connected successfully with ID:', socketIo.id);
            });

            socketIo.on('disconnect', (reason) => {
                setIsConnected(false);
                setConnectionStatus('disconnected');
                console.log('Socket disconnected, reason:', reason);

                // Nếu disconnect vì lỗi kết nối, cố gắng reconnect
                if (reason === 'io server disconnect' || reason === 'transport close') {
                    socketIo.connect();
                }
            });

            socketIo.on('connect_error', (err) => {
                setIsConnected(false);
                setConnectionStatus('error');
                setLastError(err.message);
                console.error('Socket connect error:', err.message);
            });

            socketIo.on('error', (error) => {
                setLastError(typeof error === 'string' ? error : 'Unknown socket error');
                setConnectionStatus('error');
                console.error('Socket error:', error);
            });

            // Lắng nghe trạng thái kết nối
            socketIo.on('connection-status', (data) => {
                // Không cần console.log ở đây để giảm spam
                if (data.connected) {
                    // Cập nhật trạng thái kết nối
                }
            });

            // Lưu socket instance vào cả state và ref
            setSocket(socketIo);
            socketRef.current = socketIo;
            isInitializedRef.current = true;

            // Bắt đầu ping service để giữ kết nối - giảm tần suất ping
            pingIntervalRef.current = setInterval(() => {
                if (socketIo.connected) {
                    socketIo.emit('ping');
                }
            }, 50000); // Tăng lên 50 giây để giảm traffic

            // Cleanup khi component unmount
            return () => {
                if (pingIntervalRef.current) {
                    clearInterval(pingIntervalRef.current);
                    pingIntervalRef.current = null;
                }

                // Disconnect socket chỉ khi cần thiết
                if (socketIo) {
                    socketIo.disconnect();
                }
            };
        } else {
            setConnectionStatus('disconnected');
        }

        return () => { };
    };

    // Function để reconnect socket
    const reconnect = () => {
        // Chỉ reconnect khi cần thiết
        if (socketRef.current && !socketRef.current.connected) {
            // Set trạng thái
            setConnectionStatus('connecting');
            console.log('Attempting to reconnect socket...');

            // Thử kết nối lại
            socketRef.current.connect();
        } else if (!socketRef.current) {
            // Nếu chưa có socket, khởi tạo mới
            console.log('Socket not initialized, creating new connection...');
            initializeSocket();
        }
    };

    // Chỉ chạy một lần sau khi component mount và khi auth thay đổi
    useEffect(() => {
        console.log('SocketContext: Auth state changed, authenticated:', isAuthenticated);

        // Chỉ khởi tạo socket khi user đã được xác thực
        if (isAuthenticated && user) {
            console.log('Initializing socket connection for user:', user.id);
            const cleanup = initializeSocket();

            // Thêm event handling để giám sát connection issues
            const handleOnline = () => {
                console.log('Network is online, checking socket connection');
                if (socketRef.current && !socketRef.current.connected) {
                    reconnect();
                }
            };

            window.addEventListener('online', handleOnline);

            // Cleanup everything
            return () => {
                cleanup();
                window.removeEventListener('online', handleOnline);
            };
        } else {
            // Nếu user chưa xác thực, cleanup socket hiện tại
            if (socketRef.current) {
                console.log('User not authenticated, disconnecting socket');
                socketRef.current.disconnect();
                socketRef.current = null;
            }

            if (pingIntervalRef.current) {
                clearInterval(pingIntervalRef.current);
                pingIntervalRef.current = null;
            }

            isInitializedRef.current = false;
            setSocket(null);
            setIsConnected(false);
            setConnectionStatus('disconnected');
        }
    }, [isAuthenticated, user?.id]);

    return (
        <SocketContext.Provider value={{ socket, isConnected, reconnect, lastError, connectionStatus }}>
            {children}
        </SocketContext.Provider>
    );
};

export const useSocket = () => useContext(SocketContext);