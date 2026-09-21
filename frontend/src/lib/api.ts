export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(
  path: string,
  options?: { body: unknown; csrf?: string },
): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api" + path, {
      method: options ? "POST" : "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: options
        ? {
            "Content-Type": "application/json",
            ...(options.csrf ? { "X-CSRF-Token": options.csrf } : {}),
          }
        : undefined,
      body: options ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(50_000),
    });
  } catch {
    throw new ApiError(0, "Falha na conexão. Tente novamente.");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? payload.detail
        : null;
    throw new ApiError(
      response.status,
      typeof detail === "string"
        ? detail
        : "Falha na consulta. Tente novamente.",
    );
  }
  return payload as T;
}
