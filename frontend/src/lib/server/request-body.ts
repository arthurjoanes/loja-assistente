import { createProxyLifetime } from "./proxy-lifetime";

export const MAX_REQUEST_BYTES = 16 * 1024;

export class RequestBodyTooLarge extends Error {}
export class RequestBodyTimedOut extends Error {}

function readChunk(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  signal: AbortSignal,
): Promise<ReadableStreamReadResult<Uint8Array>> {
  return new Promise((resolve, reject) => {
    const onAbort = () => {
      signal.removeEventListener("abort", onAbort);
      reject(signal.reason);
    };
    signal.addEventListener("abort", onAbort, { once: true });
    if (signal.aborted) {
      onAbort();
      return;
    }
    reader.read().then(
      (chunk) => {
        signal.removeEventListener("abort", onAbort);
        resolve(chunk);
      },
      (error) => {
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
}

export async function readRequestBody(
  request: Request,
  options: { signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<Uint8Array<ArrayBuffer> | undefined> {
  if (request.method === "GET" || !request.body) return undefined;
  const declared = request.headers.get("content-length");
  if (
    declared &&
    /^\d+$/.test(declared) &&
    Number(declared) > MAX_REQUEST_BYTES
  ) {
    void request.body.cancel().catch(() => undefined);
    throw new RequestBodyTooLarge();
  }
  const reader = request.body.getReader();
  const lifetime = createProxyLifetime(
    options.signal ?? request.signal,
    options.timeoutMs,
  );
  const { signal } = lifetime;
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await readChunk(reader, signal);
      if (done) break;
      size += value.byteLength;
      if (size > MAX_REQUEST_BYTES) {
        throw new RequestBodyTooLarge();
      }
      chunks.push(value);
    }
  } catch (error) {
    void reader.cancel(error).catch(() => undefined);
    if (signal.aborted && signal.reason?.name === "TimeoutError") {
      throw new RequestBodyTimedOut();
    }
    throw error;
  } finally {
    reader.releaseLock();
    lifetime.dispose();
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return body;
}
