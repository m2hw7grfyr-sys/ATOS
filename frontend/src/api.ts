import axios, { AxiosError, type AxiosRequestConfig } from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type ApiResponse<T> = {
  success: boolean;
  code: string;
  message: string;
  data: T;
  trace_id: string;
};

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path);
}

type ApiRequestOptions = AxiosRequestConfig & {
  body?: BodyInit | null;
};

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { body, ...axiosOptions } = options;
  const data = axiosOptions.data ?? body;
  try {
    const response = await httpClient.request<ApiResponse<T>>({
      url: path,
      ...axiosOptions,
      data,
    });
    if (!response.data.success) {
      throw new Error(response.data.message);
    }
    return response.data.data;
  } catch (reason) {
    if (reason instanceof AxiosError) {
      const payload = reason.response?.data as ApiResponse<unknown> | undefined;
      throw new Error(payload?.message ?? reason.message);
    }
    throw reason;
  }
}

export const httpClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

httpClient.interceptors.request.use((config) => {
  const token = window.localStorage.getItem("atos.token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
