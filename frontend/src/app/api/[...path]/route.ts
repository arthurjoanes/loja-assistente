import type { NextRequest } from "next/server";
import {
  readRequestBody,
  RequestBodyTooLarge,
} from "@/lib/server/request-body";

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
  try {
    const upstream = await fetch(url, {
      method: request.method,
      headers,
      body: await readRequestBody(request),
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(45_000),
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
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    const requestId = crypto.randomUUID();
    const tooLarge = error instanceof RequestBodyTooLarge;
    return Response.json(
      {
        detail: tooLarge
          ? "Requisição maior que 16 KiB."
          : "Serviço de análise indisponível. Tente novamente.",
        request_id: requestId,
      },
      {
        status: tooLarge ? 413 : 503,
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
