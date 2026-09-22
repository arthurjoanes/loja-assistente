import type { NextRequest } from "next/server";
import {
  readRequestBody,
  RequestBodyTimedOut,
  RequestBodyTooLarge,
} from "@/lib/server/request-body";
import {
  createProxyLifetime,
  forwardResponseBody,
} from "@/lib/server/proxy-lifetime";

export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const base = process.env.BACKEND_URL ?? "http://backend:8102";
  const url = new URL("/api/" + path.map(encodeURIComponent).join("/"), base);
  url.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ["content-type", "origin", "x-csrf-token"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  // Localhost cookies are shared across ports; forward only this application's session.
  const session = request.cookies.get("la_session");
  if (session) headers.set("cookie", "la_session=" + session.value);
  const lifetime = createProxyLifetime(request.signal);
  try {
    const upstream = await fetch(url, {
      method: request.method,
      headers,
      body: await readRequestBody(request, { signal: lifetime.signal }),
      cache: "no-store",
      redirect: "manual",
      signal: lifetime.signal,
    });
    const responseHeaders = new Headers({ "Cache-Control": "no-store" });
    for (const name of ["x-request-id", "x-content-type-options"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    responseHeaders.set(
      "Content-Type",
      upstream.headers.get("content-type") ?? "application/json",
    );
    for (const cookie of upstream.headers.getSetCookie())
      responseHeaders.append("Set-Cookie", cookie);
    return new Response(forwardResponseBody(upstream.body, lifetime), {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    lifetime.abort(error);
    lifetime.dispose();
    const requestId = crypto.randomUUID();
    const tooLarge = error instanceof RequestBodyTooLarge;
    const timedOut = error instanceof RequestBodyTimedOut;
    return Response.json(
      {
        detail: tooLarge
          ? "Requisição maior que 16 KiB."
          : timedOut
            ? "Tempo limite para receber a requisição. Tente novamente."
            : "Serviço de análise indisponível. Tente novamente.",
        request_id: requestId,
      },
      {
        status: tooLarge ? 413 : timedOut ? 408 : 503,
        headers: {
          "Cache-Control": "no-store",
          "X-Content-Type-Options": "nosniff",
          "X-Request-ID": requestId,
        },
      },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
