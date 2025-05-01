import { Loader2, SendHorizonal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

interface ChatInputProps {
    onSendMessage: (content: string) => void;
    disabled?: boolean;
    placeholder?: string;
}

const ChatInput = ({
    onSendMessage,
    disabled = false,
    placeholder = 'Type your message...'
}: ChatInputProps) => {
    const [message, setMessage] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const resizeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Cải thiện auto-resize textarea với debounce
    const adjustTextareaHeight = () => {
        if (!textareaRef.current) return;

        // Sử dụng scrollHeight để điều chỉnh chiều cao
        textareaRef.current.style.height = 'auto';
        const newHeight = Math.min(textareaRef.current.scrollHeight, 200);
        textareaRef.current.style.height = `${newHeight}px`;
    };

    // Thêm resize với debounce để tránh hiệu ứng giật
    useEffect(() => {
        // Dọn dẹp timeout cũ trước khi đặt cái mới
        if (resizeTimeoutRef.current) {
            clearTimeout(resizeTimeoutRef.current);
        }

        // Đặt timeout mới để tránh resize quá nhiều lần
        resizeTimeoutRef.current = setTimeout(() => {
            adjustTextareaHeight();
        }, 10);

        return () => {
            if (resizeTimeoutRef.current) {
                clearTimeout(resizeTimeoutRef.current);
            }
        };
    }, [message]);

    const handleSubmit = () => {
        const trimmedMessage = message.trim();
        if (trimmedMessage && !disabled) {
            onSendMessage(trimmedMessage);
            setMessage('');

            // Reset height sau khi gửi
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Gửi khi nhấn Enter (không giữ Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="flex items-end gap-2 border rounded-lg bg-background p-2">
            <Textarea
                ref={textareaRef}
                placeholder={placeholder}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 resize-none border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
                disabled={disabled}
                rows={1}
            />
            <Button
                type="submit"
                size="icon"
                className="h-9 w-9 shrink-0 rounded-full"
                onClick={handleSubmit}
                disabled={!message.trim() || disabled}
            >
                {disabled ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                    <SendHorizonal className="h-4 w-4" />
                )}
            </Button>
        </div>
    );
};

export default ChatInput;