import { useContext } from 'react';
import AuthContext from '../contexts/AuthContext';

export const useAuth = () => useContext(AuthContext);

// apps/client/src/hooks/use-toast.tsx
import { ToastActionElement, ToastProps } from '../components/ui/toast';
import {
    useToast as useToastOriginal
} from './use-toast';

type ToastOptions = Omit<ToastProps, 'id'> & {
    action?: ToastActionElement;
    description?: string; // Added description property
};

export function useToast() {
    const { toast, ...rest } = useToastOriginal();

    return {
        toast: (options: ToastOptions) => {
            const { title, description, variant, action, ...restOptions } = options;

            return toast({
                title,
                description,
                variant: variant || 'default',
                action,
                ...restOptions,
            });
        },
        ...rest,
    };
}