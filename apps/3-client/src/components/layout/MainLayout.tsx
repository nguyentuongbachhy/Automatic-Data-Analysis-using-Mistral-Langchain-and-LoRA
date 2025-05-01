// apps/client/src/components/layout/MainLayout.tsx
import { Menu } from 'lucide-react';
import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { useSocket } from '../../contexts/SocketContext';
import { useAuth } from '../../hooks/use-auth';
import { Button } from '../ui/button';
import Header from './Header';
import { MobileMenu } from './MobileMenu';
import Sidebar from './Sidebar';

const MainLayout = () => {
    const { user, logout } = useAuth();
    const { isConnected } = useSocket();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen);
    };

    return (
        <div className="flex w-screen h-screen bg-background">
            {/* Sidebar - Ẩn trên thiết bị di động */}
            <div className={`hidden md:flex`}>
                <Sidebar />
            </div>

            {/* Sidebar di động */}
            <MobileMenu isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)}>
                <Sidebar mobile onClose={() => setIsSidebarOpen(false)} />
            </MobileMenu>

            {/* Main content */}
            <div className="flex flex-col flex-1 overflow-hidden">
                <Header
                    user={user}
                    onLogout={logout}
                    connectionStatus={isConnected ? 'connected' : 'disconnected'}
                >
                    <div className="md:hidden">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={toggleSidebar}
                            aria-label="Toggle menu"
                        >
                            <Menu className="h-6 w-6" />
                        </Button>
                    </div>
                </Header>

                <main className="flex-1 overflow-auto p-4 md:p-6">
                    <Outlet />
                </main>
            </div>
        </div>
    );
};

export default MainLayout;