import { NextFunction, Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import config from '../config';
import prisma from '../lib/prisma';

export interface AuthRequest extends Request {
    user?: {
        id: string;
        email: string;
        name?: string
    };
}

export const auth = async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
        const token = req.headers.authorization?.split(' ')[1];

        if (!token) {
            res.status(401).json({ error: 'Chưa xác thực' });
            return;
        }

        const decoded = jwt.verify(token, config.jwtSecret) as { id: string; email: string, name: string };

        const user = await prisma.user.findUnique({
            where: { id: decoded.id },
        });

        if (!user) {
            res.status(401).json({ error: 'Người dùng không tồn tại' });
            return;
        }

        req.user = {
            id: user.id,
            email: user.email,
            name: user.name || undefined
        };

        next();
    } catch (error) {
        console.error('Auth middleware error:', error);
        res.status(401).json({ error: 'Xác thực thất bại' });
    }
};

export const verifyToken = async (token: string) => {
    try {
        const decoded = jwt.verify(token, config.jwtSecret) as { id: string };

        if (!decoded || !decoded.id) {
            return null;
        }

        const user = await prisma.user.findUnique({
            where: { id: decoded.id },
            select: {
                id: true,
                email: true,
                name: true
            }
        });

        return user;
    } catch (error) {
        console.error('Token verification error:', error);
        return null;
    }
};