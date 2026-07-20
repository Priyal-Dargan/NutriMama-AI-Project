/**
 * api.js — thin fetch wrapper for the NutriMama AI backend.
 * Handles: base URL config, attaching the JWT bearer token, JSON parsing,
 * consistent error surfacing, and auto-redirect to login on 401.
 */

// Defaults to same-origin (relative requests) — correct when the FastAPI backend
// serves this frontend directly (see backend/app.py static mount), which is the
// primary supported setup. If you serve the frontend separately (e.g. a static
// file server on a different port), set window.NUTRIMAMA_API_BASE_URL to the
// backend's full URL (e.g. 'http://127.0.0.1:8000') in a <script> tag BEFORE
// this file loads, and add that origin to CORS_ORIGINS in the backend's .env.
const API_BASE_URL = window.NUTRIMAMA_API_BASE_URL !== undefined ? window.NUTRIMAMA_API_BASE_URL : '';

const TOKEN_KEY = 'nutrimama_access_token';
const REFRESH_KEY = 'nutrimama_refresh_token';

const Auth = {
  getToken() { return localStorage.getItem(TOKEN_KEY); },
  getRefreshToken() { return localStorage.getItem(REFRESH_KEY); },
  setTokens(access, refresh) {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  isLoggedIn() { return !!this.getToken(); },
  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = 'login.html';
    }
  },
};

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Core request helper. `path` is relative to API_BASE_URL (e.g. '/auth/login').
 * Set `auth: false` in opts to skip attaching the bearer token (only needed
 * for register/login/forgot-password, which don't have one yet).
 */
async function apiRequest(path, { method = 'GET', body, auth = true, isForm = false } = {}) {
  const headers = {};
  if (!isForm) headers['Content-Type'] = 'application/json';
  if (auth) {
    const token = Auth.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });

  if (response.status === 401 && auth) {
    Auth.clear();
    window.location.href = 'login.html?expired=1';
    throw new ApiError('Session expired', 401);
  }

  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const detail = data?.detail || data?.errors || response.statusText;
    throw new ApiError(
      typeof detail === 'string' ? detail : 'Something went wrong. Please try again.',
      response.status,
      detail
    );
  }

  return data;
}

const Api = {
  // --- Auth ---
  register: (payload) => apiRequest('/auth/register', { method: 'POST', body: payload, auth: false }),
  login: (payload) => apiRequest('/auth/login', { method: 'POST', body: payload, auth: false }),
  logout: () => apiRequest('/auth/logout', { method: 'POST' }),
  me: () => apiRequest('/auth/me'),
  forgotPassword: (payload) => apiRequest('/auth/forgot-password', { method: 'POST', body: payload, auth: false }),
  resetPassword: (payload) => apiRequest('/auth/reset-password', { method: 'POST', body: payload, auth: false }),

  // --- Profile ---
  getProfile: () => apiRequest('/profile'),
  updatePregnancyProfile: (payload) => apiRequest('/profile/pregnancy', { method: 'PUT', body: payload }),
  updateMedicalHistory: (payload) => apiRequest('/profile/medical', { method: 'PUT', body: payload }),
  updateDietPreferences: (payload) => apiRequest('/profile/diet', { method: 'PUT', body: payload }),

  // --- Dashboard ---
  getDashboard: () => apiRequest('/dashboard'),

  // --- Chat ---
  sendChatMessage: (message) => apiRequest('/chat', { method: 'POST', body: { message } }),
  getChatHistory: () => apiRequest('/chat/history'),

  // --- Meal Planner ---
  generateMealPlan: () => apiRequest('/mealplan/generate', { method: 'POST' }),
  getMealPlanHistory: () => apiRequest('/mealplan/history'),
  deleteMealPlan: (id) => apiRequest(`/mealplan/delete/${id}`, { method: 'DELETE' }),

  // --- Food Safety ---
  checkFoodSafety: (foodName) => apiRequest('/foodsafety/check', { method: 'POST', body: { food_name: foodName } }),

  // --- Nutrition Tracker ---
  logNutrition: (payload) => apiRequest('/nutrition/log', { method: 'POST', body: payload }),
  getNutritionHistory: () => apiRequest('/nutrition/history'),
  logWeight: (payload) => apiRequest('/nutrition/weight', { method: 'POST', body: payload }),
  getWeightHistory: () => apiRequest('/nutrition/weight/history'),

  // --- Reminders ---
  createReminder: (payload) => apiRequest('/reminder/create', { method: 'POST', body: payload }),
  listReminders: () => apiRequest('/reminder/list'),
  updateReminder: (id, payload) => apiRequest(`/reminder/update/${id}`, { method: 'PUT', body: payload }),
  deleteReminder: (id) => apiRequest(`/reminder/delete/${id}`, { method: 'DELETE' }),

  // --- Reports ---
  getWeeklyReport: () => apiRequest('/reports/weekly'),
  getMonthlyReport: () => apiRequest('/reports/monthly'),
  listBloodReports: () => apiRequest('/reports/blood'),
  getBloodReport: (id) => apiRequest(`/reports/blood/${id}`),
  updateBloodReport: (id, payload) => apiRequest(`/reports/blood/${id}`, { method: 'PUT', body: payload }),

  // --- Upload ---
  uploadBloodReport: (formData) => apiRequest('/upload/report', { method: 'POST', body: formData, isForm: true }),

  // --- Admin ---
  adminDashboard: () => apiRequest('/admin/dashboard'),
  adminFeedback: () => apiRequest('/admin/feedback'),
  adminRagStatus: () => apiRequest('/admin/rag/status'),
  adminRebuildIndex: () => apiRequest('/admin/rag/rebuild-index', { method: 'POST' }),
  adminUploadDocument: (formData) => apiRequest('/admin/rag/upload-document', { method: 'POST', body: formData, isForm: true }),
};
