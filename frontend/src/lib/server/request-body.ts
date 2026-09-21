export const MAX_REQUEST_BYTES = 16 * 1024;

export class RequestBodyTooLarge extends Error {}

export async function readRequestBody(
  request: Request,
): Promise<Uint8Array<ArrayBuffer> | undefined> {
  if (request.method === "GET" || !request.body) return undefined;
  const declared = request.headers.get("content-length");
  if (
    declared &&
    /^\d+$/.test(declared) &&
    Number(declared) > MAX_REQUEST_BYTES
  ) {
    await request.body.cancel();
    throw new RequestBodyTooLarge();
  }
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_REQUEST_BYTES) {
        await reader.cancel();
        throw new RequestBodyTooLarge();
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return body;
}
