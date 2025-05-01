import fs from 'fs';
import multer from 'multer';
import path from 'path';
import config from '../config';

// Sử dụng đường dẫn từ config
const uploadDir = config.uploadDir;
const tmpDir = path.join(uploadDir, 'tmp');
const processedDir = path.join(uploadDir, 'processed');

// Tạo thư mục nếu chưa tồn tại
[uploadDir, tmpDir, processedDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
});

// Cấu hình multer để lưu file upload
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        // Lưu trước vào thư mục tmp
        cb(null, tmpDir);
    },
    filename: function (req, file, cb) {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
    }
});

export const upload = multer({ storage: storage });

// Hàm di chuyển file từ tmp sang processed
export const moveToProcessed = (filename: string, newFilename: string): string => {
    const sourcePath = path.join(tmpDir, filename);
    const targetPath = path.join(processedDir, newFilename);

    // Di chuyển file
    fs.renameSync(sourcePath, targetPath);

    // Trả về đường dẫn của file đã xử lý
    return targetPath;
};