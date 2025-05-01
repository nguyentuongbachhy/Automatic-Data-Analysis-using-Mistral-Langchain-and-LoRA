import { Database, Moon, Sun } from 'lucide-react';
import { Navigate, Outlet } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../hooks/use-auth';
import { cn } from '../../utils/cn';
import { Button } from '../ui/button';
import LoadingScreen from '../ui/loading-screen';

const AuthLayout = () => {
    const { isAuthenticated, loading } = useAuth();
    const { theme, setTheme } = useTheme();

    const toggleTheme = () => {
        setTheme(theme === 'dark' ? 'light' : 'dark');
    };

    if (loading) {
        return <LoadingScreen />;
    }

    if (isAuthenticated) {
        return <Navigate to="/" replace />;
    }

    return (
        <div className="flex w-screen h-screen flex-col bg-muted/40 overflow-x-hidden">
            <header className="flex h-14 items-center px-4 lg:px-6 border-b bg-background">
                <div className="flex items-center gap-2 font-semibold">
                    <Database className="h-6 w-6 text-primary" />
                    <span>DataSenseAI</span>
                </div>
                <div className="ml-auto flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleTheme}
                        className="rounded-full"
                    >
                        {theme === 'dark' ? (
                            <Sun className="h-5 w-5" />
                        ) : (
                            <Moon className="h-5 w-5" />
                        )}
                    </Button>
                </div>
            </header>
            <main className="flex-1 grid place-items-center p-4 md:px-6">
                <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
                    <div className="flex flex-col space-y-2 text-center">
                        <h1 className="text-2xl font-semibold tracking-tight">
                            DataSenseAI
                        </h1>
                        <p className="text-sm text-muted-foreground">
                            Phân tích dữ liệu thông minh với AI
                        </p>
                    </div>
                    <div
                        className={cn(
                            "grid gap-6",
                            "border rounded-lg bg-card text-card-foreground shadow p-6"
                        )}
                    >
                        <Outlet />
                    </div>
                </div>
            </main>
            <footer className="flex items-center justify-center py-4 border-t">
                <p className="text-xs text-muted-foreground">
                    &copy; {new Date().getFullYear()} DataSenseAI. All rights reserved.
                </p>
            </footer>
        </div>
    );
};

export default AuthLayout;