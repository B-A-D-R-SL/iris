// AI contribution: 50% or more AI-generated
/** Pages without sign-in (screens.md, "Public"), and the page for unknown addresses. */
import { Route } from "react-router";

import { AcceptInvitation } from "../../areas/public/pages/AcceptInvitation";
import { ForgotPassword } from "../../areas/public/pages/ForgotPassword";
import { PartnerApply } from "../../areas/public/pages/PartnerApply";
import { ResetPassword } from "../../areas/public/pages/ResetPassword";
import { SignIn } from "../../areas/public/pages/SignIn";
import { WelcomePage } from "../../areas/public/WelcomePage";
import { PublicLayout } from "../layouts/PublicLayout";
import { NotFoundPage } from "../NotFoundPage";
import { PlaceholderScreen } from "../PlaceholderScreen";

export const publicRoutes = (
  <Route element={<PublicLayout />}>
    <Route index element={<WelcomePage />} />
    <Route path="sign-in" element={<SignIn />} />
    <Route path="forgot-password" element={<ForgotPassword />} />
    <Route path="reset-password/:key" element={<ResetPassword />} />
    <Route path="invitation/:token" element={<AcceptInvitation />} />
    <Route path="partner/apply" element={<PartnerApply />} />
    {/* Linked from the partner form's consent text; see PlaceholderScreen. */}
    <Route path="privacy" element={<PlaceholderScreen titleKey="privacy.common.privacyPolicy" />} />
    <Route path="*" element={<NotFoundPage />} />
  </Route>
);
