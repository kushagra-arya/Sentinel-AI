export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost/api";

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") {
    return {};
  }
  const token = window.localStorage.getItem("sentinelai_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    cache: "no-store",
    headers: authHeaders()
  });
  if (!response.ok) {
    throw new Error(`GET ${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T, Body>(path: string, body: Body): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`POST ${path} failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}
