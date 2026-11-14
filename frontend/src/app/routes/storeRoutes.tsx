// AI contribution: 50% or more AI-generated
/** Partner store screens (screens.md, "Store"): store staff and managers. */
import { Route } from "react-router";

import { Confirm } from "../../areas/store/pages/Confirm";
import { NewListing } from "../../areas/store/pages/NewListing";
import { AREA_ROLES } from "../../shared/auth/roles";
import { MobileAreaLayout } from "../layouts/MobileAreaLayout";
import { RequireRole } from "../RequireRole";

export const storeRoutes = (
  <Route element={<RequireRole roles={AREA_ROLES.store} />}>
    <Route element={<MobileAreaLayout area="store" />}>
      <Route path="store/confirm" element={<Confirm />} />
      <Route path="store/listings/new" element={<NewListing />} />
    </Route>
  </Route>
);
