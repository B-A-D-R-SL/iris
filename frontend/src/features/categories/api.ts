/**
 * AI contribution: 50% or more AI-generated
 * Public API client for listing categories.
 */

export interface Category {
  code: string;
  name_fr: string;
  name_en: string;
  is_food: boolean;
  default_value_cents: number;
}

function isCategory(value: unknown): value is Category {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  if (
    !("code" in value) ||
    !("name_fr" in value) ||
    !("name_en" in value) ||
    !("is_food" in value) ||
    !("default_value_cents" in value)
  ) {
    return false;
  }

  return (
    typeof value.code === "string" &&
    typeof value.name_fr === "string" &&
    typeof value.name_en === "string" &&
    typeof value.is_food === "boolean" &&
    typeof value.default_value_cents === "number" &&
    Number.isSafeInteger(value.default_value_cents) &&
    value.default_value_cents >= 0
  );
}

/** Retrieve the active categories from the public backend endpoint. */
export async function getCategories(): Promise<Category[]> {
  const response = await fetch("/api/categories/");

  if (!response.ok) {
    throw new Error(`Failed to fetch categories: ${response.status}`);
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data) || !data.every(isCategory)) {
    throw new Error("Invalid categories API response");
  }

  return data;
}
