import { getEventListeners } from "node:events";
import { expect, test } from "@playwright/test";
import { NextRequest } from "next/server";
import { POST } from "../src/app/api/[...path]/route";
import { api } from "../src/lib/api";
import {
  MAX_REQUEST_BYTES,
  readRequestBody,
  RequestBodyTimedOut,
  RequestBodyTooLarge,
} from "../src/lib/server/request-body";
import {
  createProxyLifetime,
  forwardResponseBody,
} from "../src/lib/server/proxy-lifetime";

test.setTimeout(3_000);

function requestWithBody(body: ReadableStream<Uint8Array>, declared?: string) {
  return new Request("http://local.test/api/analytics/query", {
    method: "POST",
    body,
    headers: declared ? { "Content-Length": declared } : {},
    ...{ duplex: "half" },
  });
}

test("leitura sem primeiro chunk expira e não espera cancel hook pendente", async () => {
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    cancel() {
      cancelled = true;
      return new Promise<void>(() => undefined);
    },
  });
  const parent = new AbortController();
  await expect(
    readRequestBody(requestWithBody(body), {
      signal: parent.signal,
      timeoutMs: 15,
    }),
  ).rejects.toBeInstanceOf(RequestBodyTimedOut);
  expect(cancelled).toBe(true);
  expect(body.locked).toBe(false);
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
});

test("chunks intermediários não renovam o prazo total de leitura", async () => {
  let sent = 0;
  let timer: ReturnType<typeof setInterval>;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array([1]));
      sent++;
      timer = setInterval(() => {
        sent++;
        controller.enqueue(new Uint8Array([1]));
      }, 2);
    },
    cancel() {
      clearInterval(timer);
    },
  });
  try {
    await expect(
      readRequestBody(requestWithBody(body), { timeoutMs: 20 }),
    ).rejects.toBeInstanceOf(RequestBodyTimedOut);
    expect(sent).toBeGreaterThan(1);
    expect(sent).toBeLessThan(MAX_REQUEST_BYTES);
  } finally {
    clearInterval(timer!);
  }
});

for (const declared of [undefined, String(MAX_REQUEST_BYTES + 1)]) {
  test(`excesso de bytes cancela sem esperar hook, declarado=${declared}`, async () => {
    let cancelled = false;
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new Uint8Array(MAX_REQUEST_BYTES + 1));
      },
      cancel() {
        cancelled = true;
        return new Promise<void>(() => undefined);
      },
    });
    await expect(
      readRequestBody(requestWithBody(body, declared)),
    ).rejects.toBeInstanceOf(RequestBodyTooLarge);
    expect(cancelled).toBe(true);
    expect(body.locked).toBe(false);
  });
}

test("aborto do chamador cancela leitura e remove listener", async () => {
  const parent = new AbortController();
  let cancelled: unknown;
  const body = new ReadableStream<Uint8Array>({
    cancel(reason) {
      cancelled = reason;
    },
  });
  const pending = readRequestBody(requestWithBody(body), {
    signal: parent.signal,
  });
  const reason = new Error("synthetic disconnect");
  parent.abort(reason);
  await expect(pending).rejects.toBe(reason);
  expect(cancelled).toBe(reason);
  expect(body.locked).toBe(false);
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
});

test("aborto anterior não é ignorado por chunks já disponíveis", async () => {
  const parent = new AbortController();
  const reason = new Error("already disconnected");
  parent.abort(reason);
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array([1]));
      controller.close();
    },
  });
  await expect(
    readRequestBody(requestWithBody(body), { signal: parent.signal }),
  ).rejects.toBe(reason);
  expect(body.locked).toBe(false);
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
});

test("sucesso libera listener e dispose remove o timer", async () => {
  const parent = new AbortController();
  const request = new Request("http://local.test/api/analytics/query", {
    method: "POST",
    body: "ok",
  });
  expect(
    new TextDecoder().decode(
      await readRequestBody(request, { signal: parent.signal, timeoutMs: 15 }),
    ),
  ).toBe("ok");
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
  const lifetime = createProxyLifetime(parent.signal, 15);
  lifetime.dispose();
  await new Promise((resolve) => setTimeout(resolve, 25));
  expect(lifetime.signal.aborted).toBe(false);
});

test("resposta entrega primeiro chunk antes de EOF e libera prazo ao concluir", async () => {
  const parent = new AbortController();
  const lifetime = createProxyLifetime(parent.signal, 1_000);
  let source: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      source = controller;
      controller.enqueue(new Uint8Array([1, 2]));
    },
  });
  const reader = forwardResponseBody(body, lifetime)!.getReader();
  expect(await reader.read()).toEqual({
    done: false,
    value: new Uint8Array([1, 2]),
  });
  source!.enqueue(new Uint8Array([3]));
  source!.close();
  expect((await reader.read()).value).toEqual(new Uint8Array([3]));
  expect((await reader.read()).done).toBe(true);
  expect(body.locked).toBe(false);
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
  parent.abort();
  expect(lifetime.signal.aborted).toBe(false);
});

test("resposta incompleta expira após o primeiro chunk e cancela upstream", async () => {
  const parent = new AbortController();
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array([1]));
    },
    cancel() {
      cancelled = true;
      return new Promise<void>(() => undefined);
    },
  });
  const lifetime = createProxyLifetime(parent.signal, 15);
  const reader = forwardResponseBody(body, lifetime)!.getReader();
  expect((await reader.read()).value).toEqual(new Uint8Array([1]));
  await expect(reader.read()).rejects.toHaveProperty("name", "TimeoutError");
  expect(cancelled).toBe(true);
  expect(body.locked).toBe(false);
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
});

test("prazo da resposta vale mesmo sem consumo do downstream", async () => {
  const parent = new AbortController();
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new Uint8Array([1]));
    },
    cancel() {
      cancelled = true;
    },
  });
  const lifetime = createProxyLifetime(parent.signal, 15);
  const forwarded = forwardResponseBody(body, lifetime)!;
  await new Promise((resolve) => setTimeout(resolve, 25));
  await expect(forwarded.getReader().read()).rejects.toHaveProperty(
    "name",
    "TimeoutError",
  );
  expect(cancelled).toBe(true);
  expect(body.locked).toBe(false);
});

test("cancelamento downstream interrompe fetch e não aguarda cancel hook", async () => {
  const parent = new AbortController();
  const lifetime = createProxyLifetime(parent.signal);
  let cancelled: unknown;
  const body = new ReadableStream<Uint8Array>({
    cancel(reason) {
      cancelled = reason;
      return new Promise<void>(() => undefined);
    },
  });
  const forwarded = forwardResponseBody(body, lifetime)!;
  const reason = new Error("downstream closed");
  await forwarded.cancel(reason);
  expect(lifetime.signal.reason).toBe(reason);
  expect(cancelled).toBe(reason);
  expect(body.locked).toBe(false);
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
});

test("erro upstream é propagado e resposta sem corpo não mantém deadline", async () => {
  const parent = new AbortController();
  const reason = new Error("synthetic upstream error");
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.error(reason);
    },
  });
  const lifetime = createProxyLifetime(parent.signal);
  await expect(
    forwardResponseBody(body, lifetime)!.getReader().read(),
  ).rejects.toBe(reason);
  expect(body.locked).toBe(false);
  expect(getEventListeners(parent.signal, "abort")).toHaveLength(0);
  const empty = createProxyLifetime(parent.signal, 15);
  expect(forwardResponseBody(null, empty)).toBeNull();
  await new Promise((resolve) => setTimeout(resolve, 25));
  expect(empty.signal.aborted).toBe(false);
});

test("rota responde 408 com identificador e sem cache quando leitura expira", async () => {
  const parent = new AbortController();
  const request = new NextRequest("http://local.test/api/analytics/query", {
    method: "POST",
    body: new ReadableStream<Uint8Array>(),
    signal: parent.signal,
    ...{ duplex: "half" },
  });
  const pending = POST(request, {
    params: Promise.resolve({ path: ["analytics", "query"] }),
  });
  parent.abort(new DOMException("synthetic deadline", "TimeoutError"));
  const response = await pending;
  expect(response.status).toBe(408);
  expect(response.headers.get("cache-control")).toBe("no-store");
  expect(response.headers.get("x-content-type-options")).toBe("nosniff");
  const payload = await response.json();
  expect(payload.request_id).toBe(response.headers.get("x-request-id"));
  expect(payload.detail).toContain("Tempo limite");
  expect(request.body!.locked).toBe(false);
});

test("rota preserva 413 e cabeçalhos ao recusar corpo excessivo", async () => {
  const response = await POST(
    new NextRequest("http://local.test/api/analytics/query", {
      method: "POST",
      body: "x".repeat(MAX_REQUEST_BYTES + 1),
    }),
    { params: Promise.resolve({ path: ["analytics", "query"] }) },
  );
  expect(response.status).toBe(413);
  expect(response.headers.get("cache-control")).toBe("no-store");
  expect(response.headers.get("x-content-type-options")).toBe("nosniff");
});

test("rota mantém streaming e cabeçalhos; aborto fecha resposta já iniciada", async () => {
  const originalFetch = globalThis.fetch;
  const parent = new AbortController();
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode('{"partial":'));
    },
    cancel() {
      cancelled = true;
    },
  });
  globalThis.fetch = async () =>
    new Response(body, {
      status: 202,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": "synthetic-request",
        "X-Content-Type-Options": "nosniff",
      },
    });
  try {
    const response = await POST(
      new NextRequest("http://local.test/api/analytics/query", {
        method: "POST",
        body: "{}",
        signal: parent.signal,
      }),
      { params: Promise.resolve({ path: ["analytics", "query"] }) },
    );
    expect(response.status).toBe(202);
    expect(response.headers.get("content-type")).toBe("application/json");
    expect(response.headers.get("x-request-id")).toBe("synthetic-request");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("cache-control")).toBe("no-store");
    const reader = response.body!.getReader();
    expect(new TextDecoder().decode((await reader.read()).value)).toBe(
      '{"partial":',
    );
    parent.abort(new DOMException("synthetic deadline", "TimeoutError"));
    await expect(reader.read()).rejects.toHaveProperty("name", "TimeoutError");
    expect(cancelled).toBe(true);
  } finally {
    parent.abort();
    globalThis.fetch = originalFetch;
  }
});

test("cliente não trata JSON interrompido como resultado bem-sucedido", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.error(new Error("synthetic interrupted response"));
        },
      }),
    );
  try {
    await expect(api("/health")).rejects.toMatchObject({
      status: 0,
      message: "Resposta incompleta do serviço. Tente novamente.",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
