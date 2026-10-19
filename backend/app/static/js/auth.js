// ============================================================
// AUTH - Authentication helper
// ============================================================

// Auth helper - injects token into all socket emits
export function withAuth(data) {
    return { ...data, token: window.AUTH_TOKEN || "" };
}