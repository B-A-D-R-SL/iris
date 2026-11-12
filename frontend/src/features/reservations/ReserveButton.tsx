// AI contribution: 50% or more AI-generated
/**
 * Reserve in one tap (US-41, #517), on the listing page (mockup H1 step 4).
 * The page shows the result: the confirmation (onReserved) or a notice at the
 * top (onRefused). This keeps the follow-up action under the button: "Voir
 * d'autres offres" when sold out (4a), "Voir mes réservations" at the limit (4b).
 */
import { Button, Stack } from "@mantine/core";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { reserve, type Reservation } from "./api";
import { quantityToSend } from "./quantity";
import { QuantityPicker } from "./QuantityPicker";
import { refusalCode, SOLD_OUT, TOO_MANY_ACTIVE } from "./refusalMessage";

export interface ReserveButtonProps {
  listingId: string;
  maxPerHousehold: number;
  unitsLeft: number;
  onReserved: (reservation: Reservation) => void;
  onRefused: (code: string) => void;
}

export function ReserveButton(props: ReserveButtonProps) {
  const { listingId, maxPerHousehold, unitsLeft, onReserved, onRefused } = props;
  const { t, i18n } = useTranslation();
  const language = i18n.language.startsWith("en") ? "en" : "fr";
  const cap = Math.max(1, Math.min(maxPerHousehold, unitsLeft));
  const [quantity, setQuantity] = useState<number | string>(1);
  const mutation = useMutation({
    // A value typed past the cap is only clamped on blur, so clamp it here too.
    mutationFn: () => reserve(listingId, quantityToSend(quantity, cap), language),
    onSuccess: (reservation) => onReserved(reservation),
    onError: (error) => onRefused(refusalCode(error)),
  });

  const refusal = mutation.isError ? refusalCode(mutation.error) : null;
  const soldOut = unitsLeft < 1 || refusal === SOLD_OUT;
  const atLimit = refusal === TOO_MANY_ACTIVE;
  return (
    <Stack gap="sm">
      {/* Mockup H1 4a and 4b: no quantity to choose once reserving is not possible. */}
      {maxPerHousehold > 1 && !soldOut && !atLimit && (
        <QuantityPicker
          value={quantity}
          maxPerHousehold={maxPerHousehold}
          cap={cap}
          onChange={setQuantity}
        />
      )}
      <Button
        size="lg"
        fullWidth
        disabled={soldOut || atLimit}
        loading={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {t(soldOut ? "reservation.reserve.soldOutButton" : "reservation.reserve.button")}
      </Button>
      <FollowUp soldOut={soldOut} atLimit={atLimit} />
    </Stack>
  );
}

/** The way out after a refusal, as in mockup H1 4a and 4b. */
function FollowUp({ soldOut, atLimit }: { soldOut: boolean; atLimit: boolean }) {
  const { t } = useTranslation();
  if (!soldOut && !atLimit) return null;
  return (
    <Button component={Link} to={soldOut ? "/listings" : "/reservations"} variant="outline">
      {t(soldOut ? "reservation.reserve.otherListings" : "reservation.reserve.myReservations")}
    </Button>
  );
}
