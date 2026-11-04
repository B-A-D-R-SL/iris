// AI contribution: 50% or more AI-generated
/**
 * "See the list of prohibited items" (forms-and-fields.md, Listing form; SET-11
 * "Store - Post a listing", steps 3 and 4).
 *
 * Placeholder for US-34: the list of prohibited items is not built yet, so the
 * link is announced as unavailable and does nothing when activated.
 * TODO: open the prohibited-items list once a story builds it.
 */
import { Anchor } from "@mantine/core";
import { useTranslation } from "react-i18next";

export interface ProhibitedItemsLinkProps {
  /**
   * "See the list" in the category sheet (WF/Caption); the full sentence under
   * the checkbox otherwise (WF/Caption strong). Both are always underlined.
   */
  short?: boolean;
}

export function ProhibitedItemsLink({ short = false }: ProhibitedItemsLinkProps) {
  const { t } = useTranslation();
  return (
    <Anchor
      component="button"
      type="button"
      size="xs"
      underline="always"
      fw={short ? 400 : 600}
      aria-disabled="true"
      onClick={(event) => event.preventDefault()}
    >
      {t(short ? "store.newListing.prohibitedListShort" : "store.newListing.prohibitedList")}
    </Anchor>
  );
}
