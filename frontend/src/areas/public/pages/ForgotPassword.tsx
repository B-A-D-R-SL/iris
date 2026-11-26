// AI contribution: 50% or more AI-generated
import { Button, Stack, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useTranslation } from "react-i18next";

import { requestPasswordReset } from "../../../features/accounts/passwordReset";
import { allOf, hasLength, isEmail, isRequired, TextField } from "../../../shared/forms";
import { Notice } from "../../../shared/ui";
import { ResetErrorNotice, ResetSignInLink } from "./passwordResetUi";
import { useResetSubmission } from "./useResetSubmission";

/** The same confirmation covers every syntactically valid address accepted by allauth. */
export function ForgotPassword() {
  const { t, i18n } = useTranslation();
  const submission = useResetSubmission();
  const form = useForm({
    initialValues: { email: "" },
    validateInputOnBlur: true,
    validate: { email: allOf(isRequired(), isEmail(), hasLength({ max: 254 })) },
  });
  const submit = form.onSubmit(({ email }) => {
    void submission.run(() => requestPasswordReset(email.trim(), i18n.resolvedLanguage ?? "fr"));
  }, submission.failValidation);
  return (
    <Stack gap="lg">
      <Title order={1}>{t("auth.common.forgotPassword")}</Title>
      {submission.complete ? (
        <Notice type="success">{t("auth.passwordReset.requestSuccess")}</Notice>
      ) : (
        <>
          <Text>{t("auth.passwordReset.requestHelp")}</Text>
          <ResetErrorNotice failure={submission.failure} />
          <form onSubmit={submit} noValidate>
            <Stack gap="md">
              <TextField
                {...form.getInputProps("email")}
                label={t("auth.login.email")}
                name="email"
                type="email"
                autoComplete="email"
                disabled={submission.pending}
              />
              <Button type="submit" loading={submission.pending} fullWidth>
                {t("auth.passwordReset.requestSubmit")}
              </Button>
            </Stack>
          </form>
        </>
      )}
      <ResetSignInLink />
    </Stack>
  );
}
