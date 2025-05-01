// apps/client/src/components/layout/Header.tsx
import {
    HelpCircle,
    LogOut,
    Moon,
    Settings,
    Sun,
    Upload,
    User,
    Wifi,
    WifiOff,
} from 'lucide-react';
import { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';
import { User as UserType } from '../../types';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '../ui/dropdown-menu';

interface HeaderProps {
    user: UserType | null;
    onLogout: () => Promise<void>;
    connectionStatus?: 'connected' | 'disconnected';
    children?: ReactNode;
}

const Header = ({ user, onLogout, connectionStatus = 'disconnected', children }: HeaderProps) => {
    const navigate = useNavigate();
    const { theme, setTheme } = useTheme();

    const toggleTheme = () => {
        setTheme(theme === 'dark' ? 'light' : 'dark');
    };

    const handleLogout = async () => {
        try {
            await onLogout();
            navigate('/login');
        } catch (error) {
            console.error('Error logging out:', error);
        }
    };

    const getInitials = (name: string) => {
        return name
            .split(' ')
            .map((n) => n[0])
            .join('')
            .toUpperCase();
    };

    return (
        <header className="sticky top-0 z-10 flex h-16 items-center border-b bg-background px-4 md:px-6">
            <div className="flex flex-1 items-center justify-between">
                <div className="flex items-center">
                    {children}
                </div>

                <div className="flex items-center gap-4">
                    {connectionStatus && (
                        <Badge variant={connectionStatus === 'connected' ? 'default' : 'outline'} className="gap-1">
                            {connectionStatus === 'connected' ? (
                                <>
                                    <Wifi className="h-3 w-3" />
                                    <span className="text-xs">Kết nối</span>
                                </>
                            ) : (
                                <>
                                    <WifiOff className="h-3 w-3" />
                                    <span className="text-xs">Đang kết nối lại</span>
                                </>
                            )}
                        </Badge>
                    )}

                    {/* Nút Theme - với inline styles và kích thước rõ ràng */}
                    <div
                        onClick={toggleTheme}
                        className="flex h-10 w-10 items-center justify-center rounded-full border border-input bg-background hover:bg-accent cursor-pointer"
                    >
                        {theme === 'dark' ? (
                            <Sun
                                size={20}
                                color="#F59E0B"
                                style={{ minWidth: '20px', minHeight: '20px' }}
                            />
                        ) : (
                            <Moon
                                size={20}
                                color="#4F46E5"
                                style={{ minWidth: '20px', minHeight: '20px' }}
                            />
                        )}
                    </div>

                    <Button
                        variant="outline"
                        className="hidden md:flex items-center gap-2"
                        onClick={() => navigate('/upload')}
                    >
                        <Upload className="h-4 w-4" />
                        <span>Tải lên</span>
                    </Button>

                    {/* Nút Help - với inline styles và kích thước rõ ràng */}
                    <div
                        className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-accent cursor-pointer"
                    >
                        <HelpCircle
                            size={20}
                            color={theme === 'dark' ? '#E5E7EB' : '#DDD'}
                            style={{ minWidth: '20px', minHeight: '20px' }}
                        />
                    </div>

                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="bg-black relative h-9 w-9 rounded-full">
                                <Avatar className="h-9 w-9">
                                    <AvatarImage src={user?.avatar || ''} alt={user?.name || 'User'} />
                                    <AvatarFallback>{user?.name ? getInitials(user.name) : 'U'}</AvatarFallback>
                                </Avatar>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className='bg-neutral-800' align="end">
                            <DropdownMenuLabel>Tài khoản của tôi</DropdownMenuLabel>
                            {user && (
                                <div className="px-2 py-1.5">
                                    <div className="text-sm font-medium">{user.name}</div>
                                    <div className="text-xs text-muted-foreground">{user.email}</div>
                                </div>
                            )}
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => navigate('/profile')}>
                                <User className="mr-2 h-4 w-4" />
                                <span>Hồ sơ</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => navigate('/settings')}>
                                <Settings className="mr-2 h-4 w-4" />
                                <span>Cài đặt</span>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={handleLogout}>
                                <LogOut className="mr-2 h-4 w-4" />
                                <span>Đăng xuất</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
        </header>
    );
};

export default Header;