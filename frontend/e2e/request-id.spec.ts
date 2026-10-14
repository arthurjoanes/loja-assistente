import { expect, test } from "@playwright/test";
import { createClientRequestId } from "../src/lib/request-id";

const uuidV4 =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

for (const protocol of ["http", "https"]) {
  test(`query intent UUID uses browser cryptography on ${protocol}`, async ({
    page,
  }) => {
    // Synthetic origin fulfilled in-process: no server, API or external network.
    await page.route("**/*", (route) =>
      route.fulfill({
        contentType: "text/html",
        body: "<!doctype html><title>UUID origin contract</title>",
      }),
    );
    await page.goto(`${protocol}://uuid-demo.example.invalid`);
    const secure = protocol === "https";
    expect(await page.evaluate(() => isSecureContext)).toBe(secure);
    expect(await page.evaluate(() => typeof crypto.randomUUID)).toBe(
      secure ? "function" : "undefined",
    );
    await page.evaluate(() => {
      const randomValues = crypto.getRandomValues.bind(crypto);
      const randomUUID = crypto.randomUUID?.bind(crypto);
      document.documentElement.dataset.entropyCalls = "0";
      const countCall = () => {
        document.documentElement.dataset.entropyCalls = String(
          Number(document.documentElement.dataset.entropyCalls) + 1,
        );
      };
      if (randomUUID)
        Object.defineProperty(crypto, "randomUUID", {
          value: () => {
            countCall();
            return randomUUID();
          },
        });
      else
        Object.defineProperty(crypto, "getRandomValues", {
          value: (bytes: Uint8Array) => {
            countCall();
            return randomValues(bytes);
          },
        });
      Math.random = () => {
        throw new Error("A query intent must use browser cryptography");
      };
    });
    const first = await page.evaluate(createClientRequestId);
    const second = await page.evaluate(createClientRequestId);
    expect(first).toMatch(uuidV4);
    expect(second).toMatch(uuidV4);
    expect(second).not.toBe(first);
    await expect(page.locator("html")).toHaveAttribute(
      "data-entropy-calls",
      "2",
    );
  });
}

test("query intent refuses a key when browser cryptography fails", async ({
  page,
}) => {
  await page.route("**/*", (route) =>
    route.fulfill({ contentType: "text/html", body: "<!doctype html>" }),
  );
  await page.goto("http://uuid-demo.example.invalid");
  await page.evaluate(() => {
    Object.defineProperty(crypto, "getRandomValues", {
      value: () => {
        throw new Error("Synthetic entropy failure");
      },
    });
  });
  await expect(page.evaluate(createClientRequestId)).rejects.toThrow(
    "Synthetic entropy failure",
  );
});
