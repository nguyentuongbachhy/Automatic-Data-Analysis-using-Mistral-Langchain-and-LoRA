import cors from 'cors';
import express from 'express';
import http from 'http';
import morgan from 'morgan';
import path from 'path';
import config from './config';
import { initializeSocket } from './lib/socket';
import apiRoutes from './routes';

const app = express();
const server = http.createServer(app);

const corsOptions = {
    origin: ['http://localhost:3001'], // Hoặc chỉ định domain cụ thể ['http://localhost:5173', 'https://yourdomain.com']
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    credentials: true
};

// Initialize socket.io
initializeSocket(server, corsOptions);

// Middleware
app.use(cors(corsOptions));
app.use(express.json());
app.use(morgan('dev'));

// Serve uploaded files
app.use('/uploads', express.static(path.join(process.cwd(), config.uploadDir)));

// API routes
app.use('/api', apiRoutes);

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
    console.log(`Server đang chạy tại http://localhost:${PORT}`);
});
