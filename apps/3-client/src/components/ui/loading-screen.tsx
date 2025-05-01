// apps/client/src/components/ui/loading-screen.tsx
import { Database, Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

interface LoadingScreenProps {
    fullscreen?: boolean;
    className?: string;
    text?: string;
}

const LoadingScreen = ({
    fullscreen = true,
    className,
    text = 'Đang tải...'
}: LoadingScreenProps) => {
    return (
        <div
            className={cn(
                'flex flex-col items-center justify-center p-8',
                fullscreen && 'fixed inset-0 bg-background z-50',
                className
            )}
        >
            <div className="flex items-center justify-center mb-6">
                <Database className="h-10 w-10 text-primary animate-pulse" />
            </div>
            <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm font-medium text-muted-foreground">{text}</p>
            </div>
        </div>
    );
};

export default LoadingScreen;