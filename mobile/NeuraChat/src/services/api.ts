import axios from 'axios';

const BASE_URL = 'http://10.0.2.2:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface TestAIResponse {
  success: boolean;
  model?: string;
  prompt?: string;
  response?: string;
  error?: string;
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  role: string;
  content: string;
}

export const checkHealth = async (): Promise<HealthResponse> => {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
};

export const sendTestAI = async (prompt: string): Promise<TestAIResponse> => {
  const response = await apiClient.post<TestAIResponse>('/test-ai', { prompt });
  return response.data;
};

export const sendChatMessage = async (
  message: string,
  history: ChatMessage[] = [],
): Promise<ChatResponse> => {
  const payload: ChatRequest = { message, history };
  const response = await apiClient.post<ChatResponse>('/chat/', payload);
  return response.data;
};

export const getErrorMessage = (err: unknown, fallback: string): string => {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;
    const message = typeof detail === 'string' ? detail : err.message;
    return status ? `${fallback} (${status}): ${message}` : `${fallback}: ${message}`;
  }

  return `${fallback}: ${err instanceof Error ? err.message : 'Unknown error'}`;
};
