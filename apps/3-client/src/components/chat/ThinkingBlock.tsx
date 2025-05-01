// Đầu tiên, tạo component ThinkingBlock.tsx mới
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';
import React from 'react';
import ReactMarkdown from 'react-markdown';

interface ThinkingBlockProps {
    content: string;
    isOpen: boolean;
    onToggle: () => void;
}

const ThinkingBlock: React.FC<ThinkingBlockProps> = ({ content, isOpen, onToggle }) => {
    return (
        <div className="mt-4 border-t pt-3">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                    <Brain className="h-4 w-4 mr-2 text-purple-500" />
                    <h3 className="text-sm font-medium">AI's Thinking Process</h3>
                </div>
                <button
                    onClick={onToggle}
                    className="flex items-center gap-1 text-xs px-2 py-1 rounded hover:bg-muted/30"
                >
                    {isOpen ? 'Hide' : 'Show'}
                    {isOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>
            </div>

            {isOpen && (
                <div className="p-3 bg-muted/30 rounded-md text-sm text-muted-foreground whitespace-pre-wrap">
                    <ReactMarkdown>{content}</ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export default ThinkingBlock;