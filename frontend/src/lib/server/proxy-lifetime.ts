export const PROXY_TIMEOUT_MS = 45_000;

export function createProxyLifetime(
  parent: AbortSignal,
  timeoutMs = PROXY_TIMEOUT_MS,
) {
  const controller = new AbortController();
  const onAbort = () => controller.abort(parent.reason);
  const timer = setTimeout(
    () => controller.abort(new DOMException("Proxy timeout", "TimeoutError")),
    timeoutMs,
  );
  parent.addEventListener("abort", onAbort, { once: true });
  if (parent.aborted) onAbort();
  return {
    signal: controller.signal,
    abort(reason?: unknown) {
      controller.abort(reason);
    },
    dispose() {
      clearTimeout(timer);
      parent.removeEventListener("abort", onAbort);
    },
  };
}

export type ProxyLifetime = ReturnType<typeof createProxyLifetime>;

// Keep backpressure and chunks; the deadline owns the body until EOF/cancel,
// including periods when the downstream consumer is not calling pull().
export function forwardResponseBody(
  body: ReadableStream<Uint8Array> | null,
  lifetime: ProxyLifetime,
): ReadableStream<Uint8Array> | null {
  if (!body) {
    lifetime.dispose();
    return null;
  }
  const reader = body.getReader();
  let finished = false;
  let onAbort: () => void;
  function finish(cancel: boolean, reason?: unknown) {
    if (finished) return;
    finished = true;
    lifetime.signal.removeEventListener("abort", onAbort);
    if (cancel) {
      lifetime.abort(reason);
      // An underlying cancel hook may never resolve; cleanup cannot wait for it.
      void reader.cancel(reason).catch(() => undefined);
    }
    reader.releaseLock();
    lifetime.dispose();
  }
  return new ReadableStream<Uint8Array>({
    start(controller) {
      onAbort = () => {
        controller.error(lifetime.signal.reason);
        finish(true, lifetime.signal.reason);
      };
      lifetime.signal.addEventListener("abort", onAbort, { once: true });
      if (lifetime.signal.aborted) onAbort();
    },
    async pull(controller) {
      try {
        const { value, done } = await reader.read();
        if (finished) return;
        if (done) {
          controller.close();
          finish(false);
        } else {
          controller.enqueue(value);
        }
      } catch (error) {
        if (finished) return;
        controller.error(error);
        finish(true, error);
      }
    },
    cancel(reason) {
      finish(true, reason);
    },
  });
}
