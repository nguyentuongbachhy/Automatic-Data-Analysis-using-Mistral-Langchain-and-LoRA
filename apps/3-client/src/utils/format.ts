/**
 * Format a number with thousand separators
 */
export function formatNumber(value: number | undefined | null): string {
    if (value === undefined || value === null) return '';
    return value.toLocaleString('vi-VN');
}

/**
 * Format a number as a percentage
 */
export function formatPercent(
    value: number | undefined | null,
    decimals: number = 1
): string {
    if (value === undefined || value === null) return '';
    return `${value.toFixed(decimals)}%`;
}

/**
 * Format bytes to a human readable string (KB, MB, GB, etc.)
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * 
 * Format file size to human readable string
 */
export const formatFileSize = (size: number): string => {
    if (size < 1024) {
        return `${size} B`;
    } else if (size < 1024 * 1024) {
        return `${(size / 1024).toFixed(2)} KB`;
    } else {
        return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    }
};

/**
 * Truncate a string to a specified length
 */
export function truncateString(str: string, maxLength: number): string {
    if (!str) return '';
    if (str.length <= maxLength) return str;
    return str.slice(0, maxLength) + '...';
}