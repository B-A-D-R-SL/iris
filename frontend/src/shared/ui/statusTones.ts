// AI contribution: 50% or more AI-generated
import type { components } from "../api/generated";

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";
type Schemas = components["schemas"];

/** SET-33 (#651) status map. Generated enums make new API statuses a compile error. */
export const statusTones = {
  household: {
    draft: "neutral",
    submitted: "info",
    awaiting_visit: "info",
    review_required: "warning",
    renewal_needed: "warning",
    approved: "success",
    suspended: "danger",
    rejected: "danger",
  } satisfies Record<Schemas["WalkInDraftReadStatusEnum"], StatusTone>,
  listing: {
    published: "success",
    sold_out: "neutral",
    closed: "neutral",
    cancelled: "neutral",
  } satisfies Record<Schemas["PostedListingStatusEnum"] | "sold_out", StatusTone>,
  // These records have no generated status enum yet. Keep the backend values verbatim.
  reservation: {
    reserved: "info",
    picked_up: "success",
    cancelled: "neutral",
    cancelled_by_store: "warning",
    no_show: "danger",
  },
  partnerApplication: { submitted: "info", approved: "success", rejected: "danger" },
  store: { active: "success", deactivated: "neutral" },
  category: { active: "success", inactive: "neutral" },
} as const satisfies Record<string, Record<string, StatusTone>>;

export type StatusRecord = keyof typeof statusTones;
