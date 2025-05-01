/**
 * Detect the type of a value (number, string, date, etc.)
 */
export function detectValueType(value: any): string {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'number') return 'numeric';
    if (typeof value === 'boolean') return 'boolean';

    if (typeof value === 'string') {
        // Try to convert to date
        const dateValue = new Date(value);
        if (!isNaN(dateValue.getTime())) {
            // Check if the string actually contains date-like patterns
            const datePattern = /^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}($|\s|\T)/;
            if (datePattern.test(value)) {
                return 'datetime';
            }
        }

        // Try to convert to number
        const numValue = Number(value);
        if (!isNaN(numValue)) {
            return 'numeric';
        }

        return 'text';
    }

    return 'unknown';
}

/**
 * Extract columns and their types from a data array
 */
export function detectColumnTypes(data: any[]): Record<string, string> {
    if (!data || data.length === 0) return {};

    const result: Record<string, string> = {};
    const firstRow = data[0];

    // Get all column names from the first row
    const columns = Object.keys(firstRow);

    columns.forEach(column => {
        // Get all values for this column
        const values = data
            .map(row => row[column])
            .filter(val => val !== null && val !== undefined);

        if (values.length === 0) {
            result[column] = 'text';
            return;
        }

        // Detect type for each value
        const types = values.map(detectValueType);

        // Find the most common type
        const typeCounts: Record<string, number> = {};
        types.forEach(type => {
            typeCounts[type] = (typeCounts[type] || 0) + 1;
        });

        let maxCount = 0;
        let dominantType = 'text';

        Object.entries(typeCounts).forEach(([type, count]) => {
            if (count > maxCount) {
                maxCount = count;
                dominantType = type;
            }
        });

        result[column] = dominantType;
    });

    return result;
}

/**
 * Deep clone an object
 */
export function deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj));
}