// AI contribution: 50% or more AI-generated
/** Partner store screens (screens.md, "Store"): store staff and managers. */
import { Route } from "react-router";

import { NewListing } from "../../areas/store/pages/NewListing";
import { AREA_ROLES } from "../../shared/auth/roles";
import { MobileAreaLayout } from "../layouts/MobileAreaLayout";
import { RequireRole } from "../RequireRole";

export const storeRoutes = (
  <Route element={<RequireRole roles={AREA_ROLES.store} />}>
    <Route element={<MobileAreaLayout area="store" />}>
      <Route path="store/listings/new" element={<NewListing />} />
    </Route>
  </Route>
);
