// AI contribution: 50% or more AI-generated
import { Anchor, Button, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { resetPassword } from "../../../features/accounts/passwordReset";
import { useAuth } from "../../../shared/auth/authContext";
import { isRequired, validationMessage } from "../../../shared/forms";
import { useFieldWrapper } from "../../../shared/forms/fieldProps";
import { Notice } from "../../../shared/ui";
import { ResetErrorNotice, ResetSignInLink } from "./passwordResetUi";
import { useResetSubmission } from "./useResetSubmission";

function usePasswordForm() {
  return useForm({
    initialValues: { password: "", confirmation: "" },
    validateInputOnBlur: true,
    validate: {
      password: (value) =>
        isRequired()(value) ||
        (value.length < 10 ? validationMessage("auth.invitation.passwordTooShort") : null),
      confirmation: (value, values) =>
        isRequired()(value) ||
        (value === values.password ? null : validationMessage("auth.invitation.passwordMismatch")),
    },
  });
}

function PasswordFields({
  form,
  pending,
}: {
  form: ReturnType<typeof usePasswordForm>;
  pending: boolean;
}) {
  const { t } = useTranslation();
  const password = useFieldWrapper({
    label: t("auth.passwordReset.newPassword"),
    description: t("auth.invitation.passwordHelp"),
    error: form.errors.password,
  });
  const confirmation = useFieldWrapper({
    label: t("auth.signup.passwordConfirm"),
    error: form.errors.confirmation,
  });
  const visibility = { "aria-label": t("auth.passwordReset.togglePasswordVisibility") };
  return (
    <>
      <PasswordInput
        {...form.getInputProps("password")}
        {...password}
        aria-invalid={Boolean(password.error)}
        name="password"
        autoComplete="new-password"
        visibilityToggleButtonProps={visibility}
        disabled={pending}
      />
      <PasswordInput
        {...form.getInputProps("confirmation")}
        {...confirmation}
        aria-invalid={Boolean(confirmation.error)}
        name="password_confirm"
        autoComplete="new-password"
        visibilityToggleButtonProps={visibility}
        disabled={pending}
      />
    </>
  );
}

function ResetPasswordSuccess() {
  const { t } = useTranslation();
  const { user } = useAuth();
  return (
    <>
      <Notice type="success">{t("auth.passwordReset.resetSuccess")}</Notice>
      {user ? <Text>{t("auth.passwordReset.signedInGuidance")}</Text> : <ResetSignInLink />}
    </>
  );
}

function ResetPasswordForm({ resetKey }: { resetKey: string }) {
  const { t, i18n } = useTranslation();
  const { refreshAfterPasswordReset } = useAuth();
  const form = usePasswordForm();
  const submission = useResetSubmission();
  const submit = form.onSubmit(({ password }) => {
    void submission.run(async () => {
      await resetPassword(resetKey, password, i18n.resolvedLanguage ?? "fr");
      form.reset();
      // A reset of the current account invalidates its existing password-derived session.
      await refreshAfterPasswordReset();
    });
  }, submission.failValidation);
  return (
    <Stack gap="lg">
      <Title order={1}>{t("auth.passwordReset.resetTitle")}</Title>
      {submission.complete ? (
        <ResetPasswordSuccess />
      ) : (
        <>
          <ResetErrorNotice failure={submission.failure} />
          <form onSubmit={submit} noValidate>
            <Stack gap="md">
              <PasswordFields form={form} pending={submission.pending} />
              <Button type="submit" loading={submission.pending} fullWidth>
                {t("auth.passwordReset.resetSubmit")}
              </Button>
            </Stack>
          </form>
          <Anchor component={Link} to="/forgot-password" replace>
            {t("auth.passwordReset.newLink")}
          </Anchor>
        </>
      )}
    </Stack>
  );
}

export function ResetPassword() {
  const { key } = useParams();
  return <ResetPasswordForm key={key} resetKey={key ?? ""} />;
}
