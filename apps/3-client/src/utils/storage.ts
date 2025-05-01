/**
 * Save an object to localStorage with expiration
 */
export function setWithExpiry(
    key: string,
    value: any,
    ttl: number
): void {
    const item = {
        value,
        expiry: new Date().getTime() + ttl,
    };
    localStorage.setItem(key, JSON.stringify(item));
}

/**
 * Get an object from localStorage with expiration check
 */
export function getWithExpiry(key: string): any {
    const itemStr = localStorage.getItem(key);
    if (!itemStr) return null;

    const item = JSON.parse(itemStr);
    const now = new Date().getTime();

    if (now > item.expiry) {
        localStorage.removeItem(key);
        return null;
    }
    return item.value;
}
