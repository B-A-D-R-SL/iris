// AI contribution: 50% or more AI-generated
/** Household screens (screens.md, "Household"): beneficiaries only. */
import { Route } from "react-router";

import { ListingDetail } from "../../areas/household/pages/ListingDetail";
import { Listings } from "../../areas/household/pages/Listings";
import { AREA_ROLES } from "../../shared/auth/roles";
import { MobileAreaLayout } from "../layouts/MobileAreaLayout";
import { RequireRole } from "../RequireRole";

export const householdRoutes = (
  <Route element={<RequireRole roles={AREA_ROLES.household} />}>
    <Route element={<MobileAreaLayout area="household" />}>
      <Route path="listings" element={<Listings />} />
      <Route path="listings/:id" element={<ListingDetail />} />
    </Route>
  </Route>
);
