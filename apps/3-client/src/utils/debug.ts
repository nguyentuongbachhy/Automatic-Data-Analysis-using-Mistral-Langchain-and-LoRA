export function logApiResponse(label: string, response: any): void {
    if (process.env.NODE_ENV !== 'production') {
        console.group(`API Response: ${label}`);

        // Log basic response info
        console.log('Status:', response?.status);
        console.log('Has data:', !!response?.data);

        // Look for file IDs in various possible locations
        const fileId = response?.data?.fileId ||
            response?.data?.id ||
            response?.data?.data?.fileId ||
            response?.data?.data?.id;

        console.log('File ID found:', fileId || 'NOT FOUND');

        // Log the first level of data structure
        if (response?.data) {
            console.log('Top-level keys:', Object.keys(response.data));

            if (response.data.data) {
                console.log('Second-level keys:', Object.keys(response.data.data));
            }
        }

        // If this is a FileData object, log important properties
        if (response?.id !== undefined || response?.fileId !== undefined) {
            console.log('FileData properties:');
            console.log('- id:', response.id || 'undefined');
            console.log('- fileId:', response.fileId || 'undefined');
            console.log('- filename:', response.filename || response.fileName || 'undefined');
            console.log('- originalName:', response.originalName || 'undefined');
        }

        console.groupEnd();
    }
}

/**
 * Safely extracts a file ID from various possible data structures
 */
export function extractFileId(data: any): string | undefined {
    if (!data) return undefined;

    // Try all possible locations for a file ID
    return data.fileId ||
        data.id ||
        data.data?.fileId ||
        data.data?.id ||
        undefined;
}

/**
 * Add this to window for debugging from browser console
 */
if (process.env.NODE_ENV !== 'production') {
    // @ts-ignore
    window.debugUtils = {
        logApiResponse,
        extractFileId
    };
}