import { useMemo } from 'react';
import { ResponsiveContainer } from 'recharts';

// COLORS array for consistent styling
const COLORS = [
    '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
    '#4895ef', '#560bad', '#b5179e', '#f15bb5', '#00bbf9',
    '#fb8500', '#ffb703', '#023047', '#219ebc', '#8ecae6'
];

interface WordCloudWord {
    text: string;
    value: number;
}

interface WordCloudRendererProps {
    data: any[];
    title?: string;
    description?: string;
    config?: {
        maxWords?: number;
        fontSizeRange?: [number, number];
        colorScheme?: string[];
        width?: number;
        height?: number;
    };
}

export default function WordCloudRenderer({
    data,
    title,
    description,
    config = {}
}: WordCloudRendererProps) {
    // Process data into format required for word cloud
    const wordCloudData = useMemo(() => {
        if (!data || data.length === 0) return [];

        // Handle different data formats
        const wordData: WordCloudWord[] = data.map(item => {
            if ('text' in item && 'value' in item) {
                return { text: String(item.text), value: Number(item.value) };
            } else if ('word' in item && 'count' in item) {
                return { text: String(item.word), value: Number(item.count) };
            } else if ('name' in item && 'value' in item) {
                return { text: String(item.name), value: Number(item.value) };
            } else {
                // Try to extract appropriate properties
                const textKey = Object.keys(item).find(
                    key => typeof item[key] === 'string' &&
                        ['text', 'word', 'term', 'name'].includes(key.toLowerCase())
                );

                const valueKey = Object.keys(item).find(
                    key => typeof item[key] === 'number' &&
                        ['value', 'count', 'frequency', 'size'].includes(key.toLowerCase())
                );

                if (textKey && valueKey) {
                    return { text: String(item[textKey]), value: Number(item[valueKey]) };
                }

                return null;
            }
        }).filter(Boolean) as WordCloudWord[];

        // Sort by value (highest first) and limit to maxWords
        const maxWords = config?.maxWords || 100;
        return wordData
            .sort((a, b) => b.value - a.value)
            .slice(0, maxWords);
    }, [data, config?.maxWords]);

    // Calculate font sizes based on word frequencies
    const processedWords = useMemo(() => {
        if (wordCloudData.length === 0) return [];

        const minFontSize = config?.fontSizeRange?.[0] || 12;
        const maxFontSize = config?.fontSizeRange?.[1] || 60;

        // Find min and max values
        const values = wordCloudData.map(word => word.value);
        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);
        const valueRange = maxValue - minValue;

        // Calculate font size for each word
        return wordCloudData.map((word, index) => {
            let fontSize = minFontSize;

            if (valueRange > 0) {
                // Scale font size based on value
                const normalizedValue = (word.value - minValue) / valueRange;
                fontSize = minFontSize + normalizedValue * (maxFontSize - minFontSize);
            }

            // Assign color
            const colorScheme = config?.colorScheme || COLORS;
            const color = colorScheme[index % colorScheme.length];

            return {
                ...word,
                fontSize: Math.round(fontSize),
                color
            };
        });
    }, [wordCloudData, config?.fontSizeRange, config?.colorScheme]);

    // Render the word cloud using custom layout algorithm (simple version)
    // In a real implementation, you would use a more sophisticated layout algorithm
    const renderWordCloud = useMemo(() => {
        if (processedWords.length === 0) {
            return (
                <div className="flex items-center justify-center h-full">
                    <div className="text-gray-500">No data to display</div>
                </div>
            );
        }

        // Simple random layout (just for visualization)
        // In a real implementation, you would use a collision detection algorithm
        return (
            <div className="relative h-full w-full overflow-hidden bg-white p-4 text-center">
                {processedWords.map((word, index) => {
                    // Calculate random position
                    const leftPos = Math.random() * 70 + 10; // 10-80%
                    const topPos = Math.random() * 70 + 10; // 10-80%

                    return (
                        <div
                            key={index}
                            className="absolute inline-block transform -translate-x-1/2 -translate-y-1/2"
                            style={{
                                left: `${leftPos}%`,
                                top: `${topPos}%`,
                                fontSize: `${word.fontSize}px`,
                                color: word.color,
                                fontWeight: word.fontSize > 30 ? 'bold' : 'normal',
                                opacity: 0.85,
                                textShadow: word.fontSize > 40 ? '1px 1px 1px rgba(0,0,0,0.1)' : 'none',
                                transform: `rotate(${Math.random() * 30 - 15}deg)`,
                                zIndex: Math.round(word.fontSize)
                            }}
                        >
                            {word.text}
                        </div>
                    );
                })}

                {/* Render top words in a list for better accessibility */}
                <div className="sr-only">
                    <h2>Top Words</h2>
                    <ul>
                        {processedWords.slice(0, 10).map((word, index) => (
                            <li key={index}>
                                {word.text}: {word.value}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        );
    }, [processedWords]);

    return (
        <div className="h-full w-full">
            <div className="mb-2">
                {title && <div className="font-medium">{title}</div>}
                {description && <div className="text-sm text-gray-500 mt-1">{description}</div>}
                <div className="text-xs text-gray-500 mt-1">
                    {processedWords.length} words displayed
                </div>
            </div>

            <div className="h-full w-full">
                <ResponsiveContainer width="95%" height="90%">
                    {renderWordCloud}
                </ResponsiveContainer>
            </div>

            {/* Legend for top words */}
            <div className="mt-2 flex flex-wrap justify-center gap-2">
                {processedWords.slice(0, 5).map((word, index) => (
                    <div key={index} className="flex items-center text-xs">
                        <span
                            className="inline-block w-2 h-2 rounded-full mr-1"
                            style={{ backgroundColor: word.color }}
                        />
                        <span>{word.text} ({word.value})</span>
                    </div>
                ))}
            </div>
        </div>
    );
}