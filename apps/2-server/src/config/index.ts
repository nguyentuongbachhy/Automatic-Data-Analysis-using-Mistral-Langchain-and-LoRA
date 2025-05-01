import dotenv from 'dotenv';
import path from 'path';
dotenv.config()

const projectRoot = path.resolve(__dirname);

// Cập nhật trong file config/index.ts
export default {
    port: parseInt(process.env.PORT || '3000'),
    jwtSecret: process.env.JWT_SECRET || 'NtbhPtkt0803200427012004@<3',
    jwtExpiresIn: process.env.JWT_EXPIRES_IN || '1d',
    mlServiceUrl: process.env.ML_SERVICE_URL || 'http://localhost:5000',
    uploadDir: process.env.UPLOAD_DIR || path.join(projectRoot, 'storage/uploads'),
    database: {
        url: process.env.DATABASE_URL,
    },
    environment: process.env.NODE_ENV || 'development',
    json: {
        useCamelCase: process.env.USE_CAMEL_CASE === 'true' || true,
        validateResponses: process.env.VALIDATE_RESPONSES === 'true' || true
    }
};