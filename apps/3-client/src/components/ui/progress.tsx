// apps/client/src/components/ui/progress.tsx
import * as ProgressPrimitive from "@radix-ui/react-progress";
import * as React from "react";

import { cn } from "../../utils/cn";

const Progress = React.forwardRef<
    React.ElementRef<typeof ProgressPrimitive.Root>,
    React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(({ className, value, ...props }, ref) => (
    <ProgressPrimitive.Root
        ref={ref}
        className={cn(
            "relative h-2 w-full overflow-hidden rounded-full bg-muted",
            className
        )}
        {...props}
    >
        <ProgressPrimitive.Indicator
            className="h-full w-full flex-1 bg-primary transition-all"
            style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
        />
    </ProgressPrimitive.Root>
));
Progress.displayName = ProgressPrimitive.Root.displayName;

export { Progress };

// Progress with label
interface ProgressWithLabelProps extends React.ComponentPropsWithoutRef<typeof Progress> {
    showPercentage?: boolean;
    label?: string;
}

export function ProgressWithLabel({
    value,
    showPercentage = true,
    label,
    className,
    ...props
}: ProgressWithLabelProps) {
    return (
        <div className="space-y-1">
            {label && (
                <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">{label}</span>
                    {showPercentage && <span className="font-medium">{Math.round(value || 0)}%</span>}
                </div>
            )}
            <Progress
                value={value}
                className={cn("h-2", className)}
                {...props}
            />
            {!label && showPercentage && (
                <div className="text-xs text-right text-muted-foreground">
                    {Math.round(value || 0)}%
                </div>
            )}
        </div>
    );
}

// Progress circle for compact display
interface ProgressCircleProps {
    value: number;
    size?: number;
    thickness?: number;
    showLabel?: boolean;
    className?: string;
}

export function ProgressCircle({
    value,
    size = 36,
    thickness = 3,
    showLabel = true,
    className
}: ProgressCircleProps) {
    const radius = (size - thickness) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (value / 100) * circumference;

    return (
        <div className={cn("relative inline-flex items-center justify-center", className)}>
            <svg
                width={size}
                height={size}
                viewBox={`0 0 ${size} ${size}`}
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="rotate-[-90deg]"
            >
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={thickness}
                    className="text-muted/30"
                />
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke="currentColor"
                    strokeWidth={thickness}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    className="text-primary"
                    strokeLinecap="round"
                />
            </svg>
            {showLabel && (
                <span
                    className="absolute text-xs font-medium"
                    style={{ fontSize: `${size / 4}px` }}
                >
                    {Math.round(value)}%
                </span>
            )}
        </div>
    );
}