// AI contribution: 50% or more AI-generated
/**
 * A stand-in for the Iris API, only for the US-33 time-to-post check. It
 * answers as a signed-in store worker (sign-in arrives with US-01), serves the
 * categories, accepts every listing without saving it, and times each run.
 * Synthetic data only; it listens on 127.0.0.1. Start it with preview.mjs.
 */
import { createServer } from "node:http";

import { createRunRecorder, participantFrom } from "./runs.mjs";

export const PREVIEW_USER = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "Participant",
  role: "store_staff",
  store: "00000000-0000-4000-8000-0000000000aa",
  language: "fr",
};

function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

/** The posted fields, from JSON or from multipart form data (a post with a photo). */
export function listingFrom(body, contentType) {
  if (contentType.startsWith("application/json")) {
    try {
      return JSON.parse(body);
    } catch {
      return {};
    }
  }
  const listing = {};
  for (const [, name, value] of body.matchAll(/name="([^"]+)"\r\n\r\n([^\r]*)\r\n/g)) {
    listing[name] = value;
  }
  return listing;
}

/**
 * The preview server. `clock` gives the time in milliseconds; `onRestart` hears
 * when a reload drops a running clock, `onOpen` when a participant's clock starts
 * and `onRun` receives each finished run (see runs.mjs).
 */
export function createPreviewApi({
  categories,
  previousRuns = [],
  clock = Date.now,
  onRestart = () => {},
  onOpen = () => {},
  onRun = () => {},
}) {
  const recorder = createRunRecorder(previousRuns);

  return createServer(async (request, response) => {
    const send = (status, body) => {
      response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
      response.end(JSON.stringify(body));
    };
    const participant = participantFrom(request.headers.referer);

    if (request.method === "GET" && request.url === "/api/me/") {
      if (recorder.pageLoaded(participant)) onRestart(participant);
      return send(200, PREVIEW_USER);
    }
    if (request.method === "GET" && request.url === "/api/categories/") {
      if (recorder.formOpened(participant, clock())) onOpen(participant);
      return send(200, categories);
    }
    if (request.method === "POST" && request.url === "/api/store/listings/") {
      const listing = listingFrom(await readBody(request), request.headers["content-type"] ?? "");
      const run = recorder.published(participant, clock(), listing);
      if (run) onRun(run);
      return send(201, { ...listing, id: `preview-${run?.run ?? 0}`, status: "published" });
    }
    return send(404, { code: "not_found", message: "Not part of the preview.", fields: {} });
  });
}
