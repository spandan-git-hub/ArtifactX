import axios from 'axios';

const API_BASE = '/api/auth';
const TOKEN_KEY = 'arx_auth_token';

// Install Axios request interceptor to attach JWT token to all outbound requests
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export interface ExaminerProfile {
  id: number;
  username: string;
  name: string;
  agency: string;
  designation: string;
}

export const GUEST_EXAMINER: ExaminerProfile = {
  id: 0,
  username: 'guest@artifactx.local',
  name: 'Guest Examiner (Demo)',
  agency: 'ArtifactX Evaluation Sandbox',
  designation: 'Guest Forensic Analyst',
};

export const GUEST_TOKEN = 'guest-demo-token';

export interface AuthResponse {
  access_token: string;
  token_type: string;
  examiner: ExaminerProfile;
}

export const authService = {
  login: async (username: string, password: string): Promise<AuthResponse> => {
    const response = await axios.post<AuthResponse>(`${API_BASE}/login`, {
      username,
      password,
    });
    if (response.data?.access_token) {
      localStorage.setItem(TOKEN_KEY, response.data.access_token);
    }
    return response.data;
  },

  /** Direct auth skip for guest sessions - immediately creates local session and alerts backend */
  loginAsGuest: (): AuthResponse => {
    localStorage.setItem(TOKEN_KEY, GUEST_TOKEN);
    // Asynchronously notify backend for audit logging without blocking frontend entry
    axios.post(`${API_BASE}/guest`).catch(() => {});
    return {
      access_token: GUEST_TOKEN,
      token_type: 'bearer',
      examiner: GUEST_EXAMINER,
    };
  },

  getCurrentUser: async (): Promise<ExaminerProfile> => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token === GUEST_TOKEN || token?.startsWith('guest')) {
      return GUEST_EXAMINER;
    }
    const response = await axios.get<{ examiner: ExaminerProfile }>(`${API_BASE}/me`);
    return response.data.examiner;
  },

  isGuest: (): boolean => {
    const token = localStorage.getItem(TOKEN_KEY);
    return token === GUEST_TOKEN || Boolean(token?.startsWith('guest'));
  },

  getGuestExaminer: (): ExaminerProfile => GUEST_EXAMINER,
  getGuestToken: (): string => GUEST_TOKEN,

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
  },

  getToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
  },

  isAuthenticated: (): boolean => {
    return Boolean(localStorage.getItem(TOKEN_KEY));
  },
};

export default authService;

