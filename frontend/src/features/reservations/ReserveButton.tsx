// AI contribution: 50% or more AI-generated
/**
 * Reserve in one tap (US-41, #517). Mounted on the listing detail page by US-36
 * (#507). A quantity picker appears only when a household may take more than
 * one; its cap is a convenience, the server checks every limit again.
 */
import { Button, NumberInput, Stack } from "@mantine/core";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Notice } from "../../shared/ui";
import { reserve, ReserveFailed, type Reservation } from "./api";
import { ReservationConfirmation } from "./ReservationConfirmation";

/** Server refusal codes with their own message; anything else is generic. */
const REFUSAL_KEYS: Record<string, string> = {
  sold_out: "reservation.reserve.soldOut",
  not_enough_units: "reservation.reserve.notEnough",
  quantity_over_listing_limit: "reservation.reserve.overListingLimit",
  too_many_active_reservations: "reservation.reserve.tooManyActive",
  listing_not_available: "reservation.reserve.notAvailable",
  household_not_approved: "reservation.reserve.notApproved",
  reservations_unavailable: "reservation.reserve.tryAgain",
  pickup_code_unavailable: "reservation.reserve.tryAgain",
};

export interface ReserveButtonProps {
  listingId: string;
  title: string;
  maxPerHousehold: number;
  unitsLeft: number;
  /** Called after a reservation is made, for example to refresh the listing. */
  onReserved?: (reservation: Reservation) => void;
}

export function ReserveButton({
  listingId,
  title,
  maxPerHousehold,
  unitsLeft,
  onReserved,
}: ReserveButtonProps) {
  const { t, i18n } = useTranslation();
  const language = i18n.language.startsWith("en") ? "en" : "fr";
  const cap = Math.max(1, Math.min(maxPerHousehold, unitsLeft));
  const [quantity, setQuantity] = useState(1);

  const mutation = useMutation({
    mutationFn: () => reserve(listingId, quantity, language),
    onSuccess: (reservation) => onReserved?.(reservation),
  });

  if (mutation.isSuccess) {
    return <ReservationConfirmation reservation={mutation.data} title={title} />;
  }

  const refusal = mutation.error instanceof ReserveFailed ? mutation.error.code : null;
  const soldOut = unitsLeft < 1 || refusal === "sold_out";
  const errorKey = mutation.isError
    ? (REFUSAL_KEYS[refusal ?? ""] ?? "reservation.reserve.failed")
    : null;

  return (
    <Stack gap="sm">
      {soldOut ? (
        <Notice type="warning" title={t("reservation.reserve.soldOutTitle")}>
          {t("reservation.reserve.soldOut")}
        </Notice>
      ) : (
        errorKey && <Notice type="error">{t(errorKey)}</Notice>
      )}
      {maxPerHousehold > 1 && !soldOut && (
        <NumberInput
          label={t("reservation.reserve.quantity")}
          description={t("reservation.reserve.quantityHelp", { max: cap })}
          min={1}
          max={cap}
          clampBehavior="strict"
          allowDecimal={false}
          allowNegative={false}
          value={quantity}
          onChange={(value) => setQuantity(typeof value === "number" ? value : 1)}
        />
      )}
      <Button
        size="lg"
        fullWidth
        disabled={soldOut}
        loading={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {soldOut ? t("reservation.reserve.soldOutTitle") : t("reservation.reserve.button")}
      </Button>
    </Stack>
  );
}
