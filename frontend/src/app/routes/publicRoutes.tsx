// AI contribution: 50% or more AI-generated
/** Pages without sign-in (screens.md, "Public"), and the page for unknown addresses. */
import { Route } from "react-router";

import { AcceptInvitation } from "../../areas/public/pages/AcceptInvitation";
import { PartnerApply } from "../../areas/public/pages/PartnerApply";
import { SignIn } from "../../areas/public/pages/SignIn";
import { WelcomePage } from "../../areas/public/WelcomePage";
import { PublicLayout } from "../layouts/PublicLayout";
import { NotFoundPage } from "../NotFoundPage";
import { PlaceholderScreen } from "../PlaceholderScreen";

export const publicRoutes = (
  <Route element={<PublicLayout />}>
    <Route index element={<WelcomePage />} />
    <Route path="sign-in" element={<SignIn />} />
    <Route path="invitation/:token" element={<AcceptInvitation />} />
    <Route path="partner/apply" element={<PartnerApply />} />
    {/* Linked from the partner form's consent text; see PlaceholderScreen. */}
    <Route path="privacy" element={<PlaceholderScreen titleKey="privacy.common.privacyPolicy" />} />
    <Route path="*" element={<NotFoundPage />} />
  </Route>
);
