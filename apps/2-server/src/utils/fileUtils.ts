import fs from 'fs';
import path from 'path';
import xlsx from 'xlsx';

export const readFileData = (filePath: string): { headers: string[], data: any[] } => {
    const extension = path.extname(filePath).toLowerCase();

    if (extension === '.csv') {
        return readCSV(filePath);
    } else if (extension === '.xlsx' || extension === '.xls') {
        return readExcel(filePath);
    } else {
        throw new Error(`Unsupported file format: ${extension}`);
    }
};

const readCSV = (filePath: string): { headers: string[], data: any[] } => {
    // Đọc nội dung file
    const content = fs.readFileSync(filePath, 'utf8');

    // Đọc các dòng
    const rows = content.split('\n');

    // Đọc headers từ dòng đầu tiên
    const headers = rows[0].split(',').map(header => header.trim());

    // Đọc data từ các dòng tiếp theo
    const data = [];
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        if (row.trim() === '') continue; // Bỏ qua dòng trống

        const values = row.split(',');
        const rowData: any = {};

        for (let j = 0; j < headers.length; j++) {
            rowData[headers[j]] = values[j] ? values[j].trim() : '';
        }

        data.push(rowData);
    }

    return { headers, data };
};

const readExcel = (filePath: string): { headers: string[], data: any[] } => {
    // Đọc file Excel
    const workbook = xlsx.readFile(filePath);

    // Lấy sheet đầu tiên
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];

    // Chuyển đổi sheet thành JSON
    const jsonData = xlsx.utils.sheet_to_json(sheet);

    // Lấy headers
    const headers = Object.keys(jsonData[0] || {});

    return { headers, data: jsonData };
};