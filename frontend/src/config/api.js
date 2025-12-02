/**
 * API Configuration
 * 
 * Central configuration for API endpoints.
 * Change API_VERSION to switch between API versions.
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 */

// API Version - change this to switch API versions
export const API_VERSION = 'v1';

// Base API URL - includes version
export const API_BASE = `/api/${API_VERSION}`;

// Legacy API URL (for backwards compatibility during migration)
export const API_BASE_LEGACY = '/api';

// WebSocket base URL (uses legacy path - v1 redirect doesn't support WebSocket)
export const WS_BASE = `ws://${window.location.host}/api`;

// Helper to build API URLs
export function apiUrl(path) {
  // Ensure path starts with /
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${cleanPath}`;
}

// Helper to build WebSocket URLs
export function wsUrl(path) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${WS_BASE}${cleanPath}`;
}

export default {
  API_VERSION,
  API_BASE,
  API_BASE_LEGACY,
  WS_BASE,
  apiUrl,
  wsUrl,
};
