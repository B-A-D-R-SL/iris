// AI contribution: 50% or more AI-generated
import { request as httpRequest } from "node:http";
import { afterEach, describe, expect, it } from "vitest";

import { createPreviewApi, listingFrom, PREVIEW_USER } from "./preview-api.mjs";

const CATEGORIES = [
  {
    code: "bakery",
    name_fr: "Boulangerie",
    name_en: "Bakery",
    is_food: true,
    default_value_cents: 400,
  },
];
const FORM = "http://127.0.0.1:5173/store/listings/new";
const OPENED = new Date(2026, 10, 12, 9, 0).getTime();

let server;

afterEach(() => new Promise((resolve) => (server ? server.close(resolve) : resolve())));

/** Starts the preview on a free port with a clock the test controls. */
async function start(previousRuns = []) {
  const clock = { now: OPENED };
  const runs = [];
  const opened = [];
  server = createPreviewApi({
    categories: CATEGORIES,
    previousRuns,
    clock: () => clock.now,
    onOpen: (participant) => opened.push(participant),
    onRun: (run) => runs.push(run),
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return { clock, runs, opened, port: server.address().port };
}

/** An HTTP call with the Referer a browser would send from the form page. */
function call(port, method, path, { referer, body, contentType } = {}) {
  return new Promise((resolve, reject) => {
    const headers = {};
    if (referer) headers.Referer = referer;
    if (contentType) headers["Content-Type"] = contentType;
    const req = httpRequest({ host: "127.0.0.1", port, method, path, headers }, (res) => {
      let text = "";
      res.on("data", (chunk) => (text += chunk));
      res.on("end", () => resolve({ status: res.statusCode, body: JSON.parse(text) }));
    });
    req.on("error", reject);
    req.end(body);
  });
}

describe("preview API", () => {
  it("answers as a signed-in store worker and serves the categories", async () => {
    const { port } = await start();
    expect(await call(port, "GET", "/api/me/")).toEqual({ status: 200, body: PREVIEW_USER });
    expect(PREVIEW_USER.role).toBe("store_staff");
    expect(await call(port, "GET", "/api/categories/")).toEqual({ status: 200, body: CATEGORIES });
    expect((await call(port, "GET", "/api/listings/")).status).toBe(404);
  });

  it("times a participant from the form's load to the accepted post", async () => {
    const { clock, runs, opened, port } = await start();
    const referer = `${FORM}?participant=P1`;
    await call(port, "GET", "/api/me/", { referer });
    await call(port, "GET", "/api/categories/", { referer });
    await call(port, "GET", "/api/categories/", { referer });
    expect(opened).toEqual(["P1"]);
    clock.now += 41_200;
    const posted = await call(port, "POST", "/api/store/listings/", {
      referer,
      contentType: "application/json",
      body: JSON.stringify({
        title: "Pains de la veille",
        category: "bakery",
        quantity: 5,
        best_before: "2026-11-13",
      }),
    });

    expect(posted.status).toBe(201);
    expect(posted.body).toMatchObject({ title: "Pains de la veille", status: "published" });
    expect(runs).toEqual([
      expect.objectContaining({ run: 1, participant: "P1", seconds: 41.2, differences: [] }),
    ]);
  });

  it("continues saved attempts after the preview server restarts", async () => {
    const { runs, port } = await start([{ run: 3, participant: "P1", attempt: 2 }]);
    const referer = `${FORM}?participant=P1`;
    await call(port, "GET", "/api/me/", { referer });
    await call(port, "GET", "/api/categories/", { referer });
    await call(port, "POST", "/api/store/listings/", {
      referer,
      contentType: "application/json",
      body: "{}",
    });
    expect(runs).toEqual([expect.objectContaining({ run: 4, participant: "P1", attempt: 3 })]);
  });

  it("drops the idle time before a reload", async () => {
    const { clock, runs, port } = await start();
    const referer = `${FORM}?participant=P1`;
    await call(port, "GET", "/api/me/", { referer });
    await call(port, "GET", "/api/categories/", { referer });
    clock.now += 120_000; // The facilitator opened the page too early, then reloads.
    await call(port, "GET", "/api/me/", { referer });
    await call(port, "GET", "/api/categories/", { referer });
    clock.now += 30_000;
    await call(port, "POST", "/api/store/listings/", {
      referer,
      contentType: "application/json",
      body: "{}",
    });
    expect(runs).toEqual([expect.objectContaining({ participant: "P1", seconds: 30 })]);
  });

  it("does not time a post from a page that never loaded", async () => {
    const { runs, port } = await start();
    const posted = await call(port, "POST", "/api/store/listings/", {
      referer: `${FORM}?participant=P2`,
      contentType: "application/json",
      body: "{}",
    });
    expect(posted.status).toBe(201);
    expect(runs).toEqual([]);
  });
});

describe("listingFrom", () => {
  it("reads JSON and the fields of a multipart post with a photo", () => {
    expect(listingFrom('{"quantity":5}', "application/json")).toEqual({ quantity: 5 });
    expect(listingFrom("not json", "application/json")).toEqual({});
    const multipart = [
      "--b",
      'Content-Disposition: form-data; name="category"',
      "",
      "bakery",
      "--b",
      'Content-Disposition: form-data; name="quantity"',
      "",
      "5",
      "--b--",
      "",
    ].join("\r\n");
    expect(listingFrom(multipart, "multipart/form-data; boundary=b")).toEqual({
      category: "bakery",
      quantity: "5",
    });
  });
});
