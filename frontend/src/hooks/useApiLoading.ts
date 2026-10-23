import { useState, useCallback } from 'react';

interface UseLoadingOptions {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export const useApiLoading = (options?: UseLoadingOptions) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const withLoading = useCallback(
    async <T,>(asyncFn: () => Promise<T>): Promise<T | null> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await asyncFn();
        options?.onSuccess?.();
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        options?.onError?.(error);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [options]
  );

  return { isLoading, error, withLoading };
};
