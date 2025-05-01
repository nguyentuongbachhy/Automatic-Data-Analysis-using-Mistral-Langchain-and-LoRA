import { ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * A utility function that combines clsx and tailwind-merge
 * It allows for conditional and multiple class names while
 * merging tailwind classes properly
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}
