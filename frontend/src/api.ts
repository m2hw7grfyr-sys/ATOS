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

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const requestOptions: RequestInit = {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  };
  const configuredResponse = await fetch(`${API_BASE_URL}${path}`, requestOptions);
  if (!configuredResponse.ok) {
    const errorPayload = (await configuredResponse.json().catch(() => null)) as
      | ApiResponse<unknown>
      | null;
    throw new Error(
      errorPayload?.message ??
        `API ${configuredResponse.status}: ${configuredResponse.statusText}`,
    );
  }
  const payload = (await configuredResponse.json()) as ApiResponse<T>;
  if (!payload.success) {
    throw new Error(payload.message);
  }
  return payload.data;
}
