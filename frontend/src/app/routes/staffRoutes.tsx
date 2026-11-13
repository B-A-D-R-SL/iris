// AI contribution: 50% or more AI-generated
/**
 * B.A.D.R. staff screens (screens.md, "Staff"). Household search asks the API
 * who may search; the other screens are for intake workers and admins, and some
 * for admins only.
 */
import { Navigate, Route } from "react-router";

import { Audit } from "../../areas/staff/pages/Audit";
import { Household } from "../../areas/staff/pages/Household";
import { PartnerApplications } from "../../areas/staff/pages/PartnerApplications";
import { Search } from "../../areas/staff/pages/Search";
import { Notices } from "../../areas/staff/pages/WalkIn/Notices";
import { WalkIn } from "../../areas/staff/pages/WalkIn/WalkIn";
import { CategoriesPage } from "../../features/categories/CategoriesPage";
import { AREA_ROLES } from "../../shared/auth/roles";
import { StaffLayout } from "../layouts/StaffLayout";
import { RequireHouseholdSearch } from "../RequireHouseholdSearch";
import { RequireRole } from "../RequireRole";

export const staffRoutes = (
  <>
    <Route element={<RequireHouseholdSearch />}>
      <Route element={<StaffLayout />}>
        <Route path="staff/households" element={<Search />} />
        <Route path="staff/households/:id" element={<Household />} />
      </Route>
    </Route>

    <Route element={<RequireRole roles={AREA_ROLES.staff} />}>
      <Route element={<StaffLayout />}>
        <Route path="staff" element={<Navigate to="/staff/households" replace />} />
        <Route path="staff/walk-in" element={<WalkIn />} />
        <Route path="staff/walk-in/:id" element={<WalkIn />} />
        <Route path="staff/walk-in/:id/notices" element={<Notices />} />
        <Route element={<RequireRole roles={["admin"]} />}>
          <Route path="staff/partners" element={<PartnerApplications />} />
          <Route path="staff/categories" element={<CategoriesPage />} />
          <Route path="staff/audit" element={<Audit />} />
        </Route>
      </Route>
    </Route>
  </>
);
