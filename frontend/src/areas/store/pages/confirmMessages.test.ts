// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { isRefusalCode, refusalBodyKey, refusalTitleKey } from "./confirmMessages";

describe("confirmMessages", () => {
  it("maps known refusal codes to Confirm i18n stems", () => {
    expect(isRefusalCode("wrong_store")).toBe(true);
    expect(refusalTitleKey("wrong_store")).toBe("reservation.confirm.wrongStoreTitle");
    expect(refusalBodyKey("already_picked_up")).toBe("reservation.confirm.alreadyPickedUpBody");
  });

  it("falls back to unavailable for unknown API codes", () => {
    expect(isRefusalCode("not_a_real_code")).toBe(false);
    expect(refusalTitleKey("not_a_real_code")).toBe("reservation.confirm.unavailableTitle");
    expect(refusalBodyKey("not_a_real_code")).toBe("reservation.confirm.unavailableBody");
  });
});
