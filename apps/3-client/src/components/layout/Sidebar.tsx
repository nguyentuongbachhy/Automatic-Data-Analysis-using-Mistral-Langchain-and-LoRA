import {
    BarChart2,
    Cpu,
    Database,
    FileText,
    HelpCircle,
    Home,
    Settings,
    Upload,
    X,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../utils/cn';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';

interface SidebarProps {
    mobile?: boolean;
    onClose?: () => void;
}

const Sidebar = ({ mobile = false, onClose }: SidebarProps) => {
    const { pathname } = useLocation();

    const isActive = (path: string) => {
        if (path === '/' && pathname === '/') return true;
        if (path !== '/' && pathname.startsWith(path)) return true;
        return false;
    };

    const navigation = [
        {
            name: 'Trang chủ',
            href: '/',
            icon: Home,
        },
        {
            name: 'Tệp dữ liệu',
            href: '/files',
            icon: FileText,
        },
        {
            name: 'Phân tích',
            href: '/analysis',
            icon: BarChart2,
        },
        {
            name: 'Tải lên',
            href: '/upload',
            icon: Upload,
        },
        {
            name: 'Cài đặt',
            href: '/settings',
            icon: Settings,
        },
    ];

    return (
        <div
            className={cn(
                'flex h-full w-64 flex-col border-r bg-neutral-800',
                mobile && 'w-full'
            )}
        >
            {mobile && (
                <div className="flex items-center justify-between border-b px-4 py-2">
                    <div className="flex items-center">
                        <Database className="h-6 w-6 text-primary" />
                        <span className="ml-2 text-lg font-bold">DataSenseAI</span>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="h-8 w-8"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            )}

            <div className="flex items-center h-16 px-4 border-b">
                {!mobile && (
                    <>
                        <Database className="h-6 w-6 text-primary" />
                        <span className="ml-2 text-lg font-bold">DataSenseAI</span>
                    </>
                )}
            </div>

            <ScrollArea className="flex-1 pt-3">
                <nav className="flex flex-col px-2 space-y-1">
                    {navigation.map((item) => (
                        <Link
                            key={item.name}
                            to={item.href}
                            className={cn(
                                'flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                                isActive(item.href)
                                    ? 'bg-muted text-primary'
                                    : 'text-muted-foreground hover:bg-muted hover:text-primary'
                            )}
                            onClick={mobile ? onClose : undefined}
                        >
                            <item.icon className="mr-2 h-4 w-4" />
                            {item.name}
                        </Link>
                    ))}
                </nav>
            </ScrollArea>

            <div className="border-t p-4 space-y-4">
                <div className="rounded-lg bg-muted p-4">
                    <div className="flex items-center">
                        <Cpu className="h-8 w-8 text-primary" />
                        <div className="ml-4">
                            <h3 className="text-sm font-medium">AI trợ giúp</h3>
                            <p className="text-xs text-muted-foreground">
                                Nhận trợ giúp từ AI của chúng tôi
                            </p>
                        </div>
                    </div>
                    <Button className="mt-3 w-full text-xs" size="sm">
                        <HelpCircle className="mr-2 h-3 w-3" /> Trợ giúp
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;