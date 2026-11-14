// AI contribution: 50% or more AI-generated
import type { WalkInDecision } from "../../../../features/households/noticeApi";

export type ShownDecision = Pick<WalkInDecision, "status" | "status_reason" | "expires_at"> &
  Partial<Pick<WalkInDecision, "invitation_not_sent">>;

const DECIDED = new Set(["approved", "rejected", "review_required"]);

/**
 * The decision just made, or after a reload the saved outcome. A file in review stays
 * in review: approving it again could not change anything, so it shows its reasons.
 */
export function shownDecision(
  made: WalkInDecision | undefined,
  status: string,
  statusReason: string,
  expiresAt: string | null,
): ShownDecision | undefined {
  if (made) return made;
  if (!DECIDED.has(status)) return undefined;
  return { status, status_reason: statusReason, expires_at: expiresAt };
}
