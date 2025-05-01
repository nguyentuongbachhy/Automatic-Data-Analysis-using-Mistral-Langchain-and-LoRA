import { ColumnStats } from '../types';

export const inferColumnType = (values: any[]): string => {
    if (values.length === 0) return 'string';

    const nonEmptyValues = values.filter(v => v !== null && v !== undefined && v !== '');
    if (nonEmptyValues.length === 0) return 'string';

    // Check if all values are numbers
    const allNumbers = nonEmptyValues.every(v => !isNaN(Number(v)));
    if (allNumbers) return 'number';

    // Check if all values are valid dates
    const allDates = nonEmptyValues.every(v => !isNaN(Date.parse(v)));
    if (allDates) return 'date';

    // Check if all values are booleans
    const boolValues = ['true', 'false', 'yes', 'no', '0', '1', 'y', 'n'];
    const allBools = nonEmptyValues.every(v =>
        boolValues.includes(String(v).toLowerCase())
    );
    if (allBools) return 'boolean';

    return 'string';
};

export const calculateColumnStats = (
    name: string,
    values: any[]
): ColumnStats => {
    const nonEmptyValues = values.filter(v => v !== null && v !== undefined && v !== '');
    const type = inferColumnType(values);

    const stats: ColumnStats = {
        name,
        type,
        count: values.length,
        missing: values.length - nonEmptyValues.length,
        unique: new Set(values).size,
    };

    if (type === 'number') {
        const numericValues = nonEmptyValues.map(v => Number(v));
        stats.min = Math.min(...numericValues);
        stats.max = Math.max(...numericValues);
        stats.mean = numericValues.reduce((sum, v) => sum + v, 0) / numericValues.length;

        // Calculate median
        numericValues.sort((a, b) => a - b);
        const mid = Math.floor(numericValues.length / 2);
        stats.median = numericValues.length % 2 !== 0
            ? numericValues[mid]
            : (numericValues[mid - 1] + numericValues[mid]) / 2;

        // Calculate standard deviation
        const variance = numericValues.reduce((sum, v) => sum + Math.pow(v - stats.mean!, 2), 0) / numericValues.length;
        stats.stdDev = Math.sqrt(variance);

        // Create distribution for numeric values
        const binCount = Math.min(10, stats.unique);
        if (binCount > 1) {
            const binSize = (stats.max as number - stats.min as number) / binCount;
            const distribution: Record<string, number> = {};

            for (let i = 0; i < binCount; i++) {
                const binStart: number = (stats.min as number) + i * binSize;
                const binEnd = binStart + binSize;
                const binKey = `${binStart.toFixed(2)}-${binEnd.toFixed(2)}`;
                distribution[binKey] = numericValues.filter(v => v >= binStart && v < binEnd).length;
            }

            stats.distribution = distribution;
        }
    } else if (type === 'date') {
        const dateValues = nonEmptyValues.map(v => new Date(v));
        stats.min = new Date(Math.min(...dateValues.map(d => d.getTime())));
        stats.max = new Date(Math.max(...dateValues.map(d => d.getTime())));
    } else {
        // For string and boolean, create distribution of top values
        const valueCount: Record<string, number> = {};
        nonEmptyValues.forEach(v => {
            const strVal = String(v);
            valueCount[strVal] = (valueCount[strVal] || 0) + 1;
        });

        // Get top 10 values
        const sortedValues = Object.entries(valueCount)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 10);

        stats.distribution = Object.fromEntries(sortedValues);
    }

    return stats;
};