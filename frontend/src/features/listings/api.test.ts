// AI contribution: 50% or more AI-generated
import { afterEach, describe, expect, it, vi } from "vitest";

import { postListing, PostingFailed, type NewListing } from "./api";

const listing: NewListing = {
  category: "bakery",
  title: "Pains de la veille",
  description: null,
  quantity: 5,
  unit: "item",
  max_per_household: 1,
  pickup_start: "2026-10-29T16:00:00-04:00",
  pickup_end: "2026-10-29T18:00:00-04:00",
  best_before: "2026-10-30",
  estimated_value_cents: null,
  safe_and_allowed: true,
};

function stubFetch(response: Response) {
  const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(
    async () => response,
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("postListing", () => {
  it("posts JSON with the CSRF token and the language of the messages", async () => {
    document.cookie = "csrftoken=token123";
    const fetchMock = stubFetch(Response.json({ id: "1", title: "Pains" }, { status: 201 }));

    await expect(postListing(listing, null, "en")).resolves.toMatchObject({ title: "Pains" });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/store/listings/");
    expect(init).toMatchObject({
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Accept-Language": "en",
        "X-CSRFToken": "token123",
      },
    });
    expect(JSON.parse(init?.body as string)).toEqual(listing);
  });

  it("sends a photo as multipart form data without the empty fields", async () => {
    const fetchMock = stubFetch(Response.json({ id: "1" }, { status: 201 }));
    const photo = new File(["photo"], "pains.jpg", { type: "image/jpeg" });

    await postListing(listing, photo, "fr");

    const init = fetchMock.mock.calls[0][1];
    const body = init?.body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("photo")).toBe(photo);
    expect(body.get("quantity")).toBe("5");
    expect(body.get("safe_and_allowed")).toBe("true");
    expect(body.has("description")).toBe(false);
    // The browser adds the multipart boundary itself.
    expect(init?.headers).not.toHaveProperty("Content-Type");
    expect(init?.headers).not.toHaveProperty("X-CSRFToken");
  });

  it("reports field errors from a 400 response", async () => {
    stubFetch(
      Response.json(
        {
          code: "validation_error",
          message: "Vérifiez les champs indiqués.",
          fields: { quantity: ["Entrez une quantité de 1 à 999."] },
        },
        { status: 400 },
      ),
    );

    const error = await postListing(listing, null, "fr").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(PostingFailed);
    expect(error).toMatchObject({
      status: 400,
      message: "Vérifiez les champs indiqués.",
      fields: { quantity: ["Entrez une quantité de 1 à 999."] },
    });
  });

  it("reports a refusal without fields, and a response that is not JSON", async () => {
    stubFetch(
      Response.json(
        { code: "posting_unavailable", message: "Pas encore disponible.", fields: {} },
        { status: 503 },
      ),
    );
    await expect(postListing(listing, null, "fr")).rejects.toMatchObject({
      status: 503,
      message: "Pas encore disponible.",
    });

    stubFetch(new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(postListing(listing, null, "fr")).rejects.toMatchObject({
      status: 502,
      message: "",
      fields: {},
    });
  });
});
