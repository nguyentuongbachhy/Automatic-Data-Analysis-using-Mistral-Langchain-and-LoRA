import bcrypt from 'bcryptjs';
import { Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import config from '../config';
import prisma from '../lib/prisma';
import { AuthRequest } from '../middlewares/auth';

export const register = async (req: Request, res: Response) => {
    try {
        const { email, password, name } = req.body;

        // Kiểm tra email đã tồn tại
        const existingUser = await prisma.user.findUnique({
            where: { email },
        });

        if (existingUser) {
            res.status(400).json({ error: 'Email đã được sử dụng' });
            return;
        }

        // Hash mật khẩu
        const hashedPassword = await bcrypt.hash(password, 10);

        // Tạo user mới
        const user = await prisma.user.create({
            data: {
                email,
                password: hashedPassword,
                name,
                createdAt: (new Date()).toISOString(),
                updatedAt: (new Date()).toISOString()
            },
        });

        // Tạo JWT token
        const token = jwt.sign(
            { id: user.id, email: user.email, name: user.name },
            config.jwtSecret,
            { expiresIn: '1d' }
        );

        res.status(201).json({
            token,
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
            },
        });
    } catch (error) {
        console.error('Error registering user:', error);
        res.status(500).json({ error: 'Lỗi khi đăng ký' });
    }
};

export const login = async (req: Request, res: Response) => {
    try {
        const { email, password } = req.body;

        // Tìm user
        const user = await prisma.user.findUnique({
            where: { email },
        });

        if (!user) {
            res.status(401).json({ error: 'Email hoặc mật khẩu không đúng' });
            return;
        }

        // Kiểm tra mật khẩu
        const validPassword = await bcrypt.compare(password, user.password);

        if (!validPassword) {
            res.status(401).json({ error: 'Email hoặc mật khẩu không đúng' });
            return;
        }

        // Tạo JWT token
        const token = jwt.sign(
            { id: user.id, email: user.email, name: user.name },
            config.jwtSecret,
            { expiresIn: '7d' }
        );

        res.json({
            token,
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
            },
        });
    } catch (error) {
        console.error('Error logging in:', error);
        res.status(500).json({ error: 'Lỗi khi đăng nhập' });
    }
};

export const getCurrentUser = async (req: AuthRequest, res: Response) => {
    try {
        // req.user đã được thiết lập bởi middleware auth
        const user = await prisma.user.findUnique({
            where: { id: req.user!.id },
            select: {
                id: true,
                email: true,
                name: true,
            },
        });

        if (!user) {
            res.status(404).json({ error: 'Không tìm thấy người dùng' });
            return;
        }

        res.json(user);
    } catch (error) {
        console.error('Error fetching current user:', error);
        res.status(500).json({ error: 'Lỗi khi lấy thông tin người dùng' });
    }
}