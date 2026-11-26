// AI contribution: 50% or more AI-generated
import { Anchor } from "@mantine/core";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Notice } from "../../../shared/ui";
import type { ResetFailure } from "./useResetSubmission";

/** Focus on each failed submission while leaving ordinary field edits alone. */
export function ResetErrorNotice({ failure }: { failure: ResetFailure | null }) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (failure) ref.current?.focus();
  }, [failure]);
  if (!failure) return null;
  return (
    <div ref={ref} tabIndex={-1}>
      <Notice type="error">{t(`auth.passwordReset.${failure.code}`)}</Notice>
    </div>
  );
}

export function ResetSignInLink() {
  const { t } = useTranslation();
  return (
    <Anchor component={Link} to="/sign-in" replace>
      {t("auth.common.signIn")}
    </Anchor>
  );
}
