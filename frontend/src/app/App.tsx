// AI contribution: 50% or more AI-generated
/**
 * Every route of Release 1 (screens.md). Screens not built yet show a
 * placeholder: replace the element with your screen in your story's PR.
 * Who may open each area comes from navigation.ts.
 */
import { Navigate, Route, Routes } from "react-router";

import { WelcomePage } from "../areas/public/WelcomePage";
import { MobileAreaLayout } from "./layouts/MobileAreaLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { StaffLayout } from "./layouts/StaffLayout";
import { AREA_ROLES } from "./navigation";
import { NotFoundPage } from "./NotFoundPage";
import { PlaceholderScreen } from "./PlaceholderScreen";
import { RequireRole } from "./RequireRole";
import { CategoriesPage } from "../features/categories/CategoriesPage";

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<WelcomePage />} />
        <Route path="sign-in" element={<PlaceholderScreen titleKey="auth.login.title" />} />
        <Route
          path="sign-up"
          element={<PlaceholderScreen titleKey="auth.common.createAccount" />}
        />
        <Route
          path="partner/apply"
          element={<PlaceholderScreen titleKey="store.partnerApplication.becomePartner" />}
        />
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
          <Route
            path="listings"
            element={<PlaceholderScreen titleKey="app.householdNav.listings" appBar />}
          />
          <Route
            path="listings/:id"
            element={
              <PlaceholderScreen titleKey="listing.common.listing" appBar backTo="/listings" />
            }
          />
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
          <Route
            path="store/confirm"
            element={<PlaceholderScreen titleKey="reservation.common.confirmPickup" appBar />}
          />
          <Route
            path="store/listings/new"
            element={<PlaceholderScreen titleKey="listing.common.postListing" appBar />}
          />
          <Route
            path="store/listings"
            element={<PlaceholderScreen titleKey="app.storeNav.myListings" appBar />}
          />
        </Route>
      </Route>

      <Route element={<RequireRole roles={AREA_ROLES.staff} />}>
        <Route element={<StaffLayout />}>
          <Route path="staff" element={<Navigate to="/staff/households" replace />} />
          <Route
            path="staff/households"
            element={<PlaceholderScreen titleKey="app.staffNav.households" />}
          />
          <Route
            path="staff/walk-in"
            element={<PlaceholderScreen titleKey="app.staffNav.walkIn" />}
          />
          <Route element={<RequireRole roles={["admin"]} />}>
            <Route
              path="staff/review"
              element={<PlaceholderScreen titleKey="app.staffNav.reviews" />}
            />
            <Route
              path="staff/partners"
              element={<PlaceholderScreen titleKey="app.staffNav.partners" />}
            />
            <Route
              path="staff/stores"
              element={<PlaceholderScreen titleKey="app.staffNav.stores" />}
            />
            <Route path="staff/categories" element={<CategoriesPage />} />
            <Route
              path="staff/audit"
              element={<PlaceholderScreen titleKey="app.staffNav.auditLog" />}
            />
          </Route>
        </Route>
      </Route>
    </Routes>
  );
}
