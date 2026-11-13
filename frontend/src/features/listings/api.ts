// AI contribution: 50% or more AI-generated
/**
 * POST /api/store/listings/ (T-05.33.3). The server checks the role, the store
 * and every rule again; the form only helps the worker get it right first time.
 * GET /api/store/listings/categories/ (US-34) lists the categories a store may
 * post in: the server leaves out the prohibited ones.
 */
import { csrfToken } from "../../shared/api/csrf";
import type { components } from "../../shared/api/generated";
import { isCategory, type Category } from "../categories/api";

/** What the form sends; the photo travels separately as a file. */
export type NewListing = Omit<components["schemas"]["NewListing"], "photo" | "store">;
export type PostedListing = components["schemas"]["PostedListing"];
type PostingError = components["schemas"]["PostingError"];

/** A refused post: 400 has messages per API field; 403 and 503 only a message. */
export class PostingFailed extends Error {
  readonly status: number;
  readonly fields: Record<string, string[]>;

  constructor(status: number, message: string, fields: Record<string, string[]> = {}) {
    super(message);
    this.name = "PostingFailed";
    this.status = status;
    this.fields = fields;
  }
}

function isPostingError(value: unknown): value is PostingError {
  if (typeof value !== "object" || value === null) return false;
  const { message, fields } = value as Record<string, unknown>;
  return typeof message === "string" && typeof fields === "object" && fields !== null;
}

/** A photo needs multipart form data; everything else goes as JSON. */
function requestBody(listing: NewListing, photo: File | null): FormData | string {
  if (!photo) return JSON.stringify(listing);
  const form = new FormData();
  for (const [key, value] of Object.entries(listing)) {
    if (value !== null && value !== undefined) form.append(key, String(value));
  }
  form.append("photo", photo);
  return form;
}

/** The active categories the signed-in store may post in (prohibited ones left out). */
export async function getPostingCategories(): Promise<Category[]> {
  const response = await fetch("/api/store/listings/categories/", {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch posting categories: ${response.status}`);
  }
  const data: unknown = await response.json();
  if (!Array.isArray(data) || !data.every(isCategory)) {
    throw new Error("Invalid posting categories API response");
  }
  return data;
}

/**
 * Publishes a listing for the signed-in worker's store. `language` asks the
 * server for its error messages in French or English.
 */
export async function postListing(
  listing: NewListing,
  photo: File | null,
  language: "fr" | "en",
): Promise<PostedListing> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": language,
  };
  // The browser sets the multipart boundary itself.
  if (!photo) headers["Content-Type"] = "application/json";
  const token = csrfToken();
  if (token) headers["X-CSRFToken"] = token;

  const response = await fetch("/api/store/listings/", {
    method: "POST",
    headers,
    body: requestBody(listing, photo),
    credentials: "same-origin",
  });
  if (response.status === 201) {
    // An unreadable answer keeps its status, so it is not taken for a lost connection.
    const posted: unknown = await response.json().catch(() => undefined);
    if (posted !== undefined) return posted as PostedListing;
    throw new PostingFailed(response.status, "");
  }

  const error: unknown = await response.json().catch(() => null);
  if (isPostingError(error)) {
    throw new PostingFailed(response.status, error.message, error.fields);
  }
  throw new PostingFailed(response.status, "");
}
