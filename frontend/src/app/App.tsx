// AI contribution: 50% or more AI-generated
/**
 * Every route of Release 1 (screens.md). Screens not built yet show a
 * placeholder: replace the element with your screen in your story's PR.
 * Who may open each area comes from navigation.ts.
 */
import { Navigate, Route, Routes } from "react-router";

import { WelcomePage } from "../areas/public/WelcomePage";
import { SignIn } from "../areas/public/pages/SignIn";
import { AcceptInvitation } from "../areas/public/pages/AcceptInvitation";
import { PartnerApply } from "../areas/public/pages/PartnerApply";
import { PartnerApplications } from "../areas/staff/pages/PartnerApplications";
import { Audit } from "../areas/staff/pages/Audit";
import { Search } from "../areas/staff/pages/Search";
import { Household } from "../areas/staff/pages/Household";
import { WalkIn } from "../areas/staff/pages/WalkIn/WalkIn";
import { Confirm } from "../areas/store/pages/Confirm";
import { NewListing } from "../areas/store/pages/NewListing";
import { ListingDetail } from "../areas/household/pages/ListingDetail";
import { Listings } from "../areas/household/pages/Listings";
import { MobileAreaLayout } from "./layouts/MobileAreaLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { StaffLayout } from "./layouts/StaffLayout";
import { AREA_ROLES } from "./navigation";
import { NotFoundPage } from "./NotFoundPage";
import { PlaceholderScreen } from "./PlaceholderScreen";
import { RequireRole } from "./RequireRole";
import { RequireHouseholdSearch } from "./RequireHouseholdSearch";
import { CategoriesPage } from "../features/categories/CategoriesPage";

// Size exception: React Router inspects Route children directly. Keep this
// declarative route tree together so layout and role-guard nesting stays explicit.
export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<WelcomePage />} />
        <Route path="sign-in" element={<SignIn />} />
        <Route path="invitation/:token" element={<AcceptInvitation />} />
        <Route
          path="forgot-password"
          element={<PlaceholderScreen titleKey="auth.common.forgotPassword" />}
        />
        <Route
          path="sign-up"
          element={<PlaceholderScreen titleKey="auth.common.createAccount" />}
        />
        <Route path="partner/apply" element={<PartnerApply />} />
        <Route
          path="privacy"
          element={<PlaceholderScreen titleKey="privacy.common.privacyPolicy" />}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route element={<RequireRole roles={AREA_ROLES.household} />}>
        <Route element={<MobileAreaLayout area="household" />}>
          <Route
            path="home"
            element={<PlaceholderScreen titleKey="app.householdNav.home" appBar />}
          />
          <Route path="listings" element={<Listings />} />
          <Route path="listings/:id" element={<ListingDetail />} />
          <Route
            path="reservations"
            element={<PlaceholderScreen titleKey="app.householdNav.reservations" appBar />}
          />
          <Route
            path="profile"
            element={<PlaceholderScreen titleKey="app.householdNav.profile" appBar />}
          />
        </Route>
      </Route>

      <Route element={<RequireRole roles={AREA_ROLES.store} />}>
        <Route element={<MobileAreaLayout area="store" />}>
          <Route
            path="store"
            element={<PlaceholderScreen titleKey="app.storeNav.today" appBar />}
          />
          <Route path="store/confirm" element={<Confirm />} />
          <Route path="store/listings/new" element={<NewListing />} />
          <Route
            path="store/listings"
            element={<PlaceholderScreen titleKey="app.storeNav.myListings" appBar />}
          />
        </Route>
      </Route>

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
          <Route element={<RequireRole roles={["admin"]} />}>
            <Route
              path="staff/review"
              element={<PlaceholderScreen titleKey="app.staffNav.reviews" />}
            />
            <Route path="staff/partners" element={<PartnerApplications />} />
            <Route
              path="staff/stores"
              element={<PlaceholderScreen titleKey="app.staffNav.stores" />}
            />
            <Route path="staff/categories" element={<CategoriesPage />} />
            <Route path="staff/audit" element={<Audit />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  );
}
