// apps/client/src/pages/auth/RegisterPage.tsx
import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../hooks/use-auth';
import { useToast } from '../../hooks/use-toast';

const RegisterPage = () => {
    const navigate = useNavigate();
    const { register } = useAuth();
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        // Validate form
        if (!formData.name || !formData.email || !formData.password) {
            toast({
                title: 'Lỗi đăng ký',
                description: 'Vui lòng điền đầy đủ thông tin',
                variant: 'destructive',
            });
            return;
        }

        if (formData.password !== formData.confirmPassword) {
            toast({
                title: 'Lỗi đăng ký',
                description: 'Mật khẩu xác nhận không khớp',
                variant: 'destructive',
            });
            return;
        }

        if (formData.password.length < 6) {
            toast({
                title: 'Lỗi đăng ký',
                description: 'Mật khẩu phải có ít nhất 6 ký tự',
                variant: 'destructive',
            });
            return;
        }

        try {
            setIsLoading(true);
            await register(formData.name, formData.email, formData.password);
            toast({
                title: 'Đăng ký thành công',
                description: 'Tài khoản của bạn đã được tạo thành công!',
            });
            navigate('/');
        } catch (error: any) {
            toast({
                title: 'Lỗi đăng ký',
                description: error.message || 'Đã xảy ra lỗi khi đăng ký',
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
                    Tạo tài khoản mới
                </h1>
                <p className="text-sm text-muted-foreground">
                    Nhập thông tin của bạn để tạo tài khoản
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="name">Họ tên</Label>
                    <Input
                        id="name"
                        name="name"
                        placeholder="Nguyễn Văn A"
                        value={formData.name}
                        onChange={handleChange}
                        disabled={isLoading}
                        required
                    />
                </div>

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
                    <Label htmlFor="password">Mật khẩu</Label>
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

                <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Xác nhận mật khẩu</Label>
                    <Input
                        id="confirmPassword"
                        name="confirmPassword"
                        type="password"
                        placeholder="••••••••"
                        value={formData.confirmPassword}
                        onChange={handleChange}
                        disabled={isLoading}
                        required
                    />
                </div>

                <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Đang xử lý
                        </>
                    ) : (
                        'Đăng ký'
                    )}
                </Button>
            </form>

            <div className="text-center text-sm">
                Đã có tài khoản?{' '}
                <Link to="/login" className="text-primary hover:underline">
                    Đăng nhập
                </Link>
            </div>
        </div>
    );
};

export default RegisterPage;