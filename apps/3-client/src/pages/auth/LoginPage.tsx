import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../hooks/use-auth';
import { useToast } from '../../hooks/use-toast';

const LoginPage = () => {
    const navigate = useNavigate();
    const { login } = useAuth();
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        if (!formData.email || !formData.password) {
            toast({
                title: 'Lỗi đăng nhập',
                description: 'Vui lòng nhập email và mật khẩu',
                variant: 'destructive',
            });
            return;
        }

        try {
            setIsLoading(true);
            await login(formData.email, formData.password);
            toast({
                title: 'Đăng nhập thành công',
                description: 'Chào mừng bạn đã quay trở lại!',
            });
            navigate('/');
        } catch (error: any) {
            toast({
                title: 'Lỗi đăng nhập',
                description: error.message || 'Đã xảy ra lỗi khi đăng nhập',
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="space-y-2 text-center">
                <h1 className="text-xl font-semibold tracking-tight">
                    Đăng nhập vào tài khoản
                </h1>
                <p className="text-sm text-muted-foreground">
                    Nhập thông tin đăng nhập của bạn bên dưới
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                        id="email"
                        name="email"
                        type="email"
                        placeholder="name@example.com"
                        value={formData.email}
                        onChange={handleChange}
                        disabled={isLoading}
                        required
                    />
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="password">Mật khẩu</Label>
                        <Link
                            to="/forgot-password"
                            className="text-xs text-primary hover:underline"
                        >
                            Quên mật khẩu?
                        </Link>
                    </div>
                    <Input
                        id="password"
                        name="password"
                        type="password"
                        placeholder="••••••••"
                        value={formData.password}
                        onChange={handleChange}
                        disabled={isLoading}
                        required
                    />
                </div>

                <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Đang đăng nhập
                        </>
                    ) : (
                        'Đăng nhập'
                    )}
                </Button>
            </form>

            <div className="text-center text-sm">
                Chưa có tài khoản?{' '}
                <Link to="/register" className="text-primary hover:underline">
                    Đăng ký ngay
                </Link>
            </div>
        </div>
    );
};

export default LoginPage;