// AI contribution: 50% or more AI-generated
import { Anchor, Button, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useParams } from "react-router";

import { acceptInvitation, InvitationError } from "../../../features/accounts/invitations";
import { useAuth } from "../../../shared/auth/authContext";
import { isRequired, validationMessage } from "../../../shared/forms";
import { useFieldWrapper } from "../../../shared/forms/fieldProps";
import { logger } from "../../../shared/logger";
import { Notice } from "../../../shared/ui";

type ErrorKey =
  "checkPassword" | "expired" | "used" | "invalid" | "emailRegistered" | "unavailable";
type Failure = { error: InvitationError; language: string };
const ERROR_KEYS: Record<InvitationError["code"], ErrorKey> = {
  validation_error: "checkPassword",
  invitation_expired: "expired",
  invitation_used: "used",
  invitation_invalid: "invalid",
  email_already_registered: "emailRegistered",
  unavailable: "unavailable",
};

/** Preserve password whitespace while checking the shared sign-up minimum. */
function useInvitationForm() {
  return useForm({
    initialValues: { password: "", passwordConfirm: "" },
    validateInputOnBlur: true,
    validate: {
      password: (value) =>
        isRequired()(value) ||
        (value.length < 10 ? validationMessage("auth.invitation.passwordTooShort") : null),
      passwordConfirm: (value, values) =>
        isRequired()(value) ||
        (value !== values.password ? validationMessage("auth.invitation.passwordMismatch") : null),
    },
  });
}

/** Keep credentials in the form and serialize only the accepted request fields. */
function useInvitationFlow() {
  const form = useInvitationForm();
  const { token } = useParams();
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const [complete, setComplete] = useState(false);
  const [pending, setPending] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [failedSubmissions, setFailedSubmissions] = useState(0);
  const locked = useRef(false);
  const language = i18n.resolvedLanguage ?? "fr";
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current) return;
    locked.current = true;
    setFailure(null);
    const { hasErrors } = await form.validate();
    setInvalid(hasErrors);
    if (hasErrors) {
      setFailedSubmissions((count) => count + 1);
      locked.current = false;
      return;
    }
    setPending(true);
    try {
      await acceptInvitation({ token: token ?? "", password: form.values.password }, language);
      form.reset();
      setComplete(true);
    } catch (caught) {
      if (!(caught instanceof InvitationError))
        logger.error("invitation_accept_failed_unexpectedly");
      setFailure({
        error: caught instanceof InvitationError ? caught : new InvitationError("unavailable"),
        language,
      });
      setFailedSubmissions((count) => count + 1);
    } finally {
      locked.current = false;
      setPending(false);
    }
  }
  return { form, user, complete, pending, invalid, failure, language, submit, failedSubmissions };
}

type InvitationFlow = ReturnType<typeof useInvitationFlow>;

/** Backend field text belongs to its request language; local errors translate live. */
function passwordError(flow: InvitationFlow) {
  const server =
    flow.failure?.language === flow.language ? flow.failure.error.fields.password?.join(" ") : null;
  return server || flow.form.errors.password;
}

function PasswordFields({ flow }: { flow: InvitationFlow }) {
  const { t } = useTranslation();
  const password = useFieldWrapper({
    label: t("auth.signup.password"),
    description: t("auth.invitation.passwordHelp"),
    error: passwordError(flow),
  });
  const confirmation = useFieldWrapper({
    label: t("auth.signup.passwordConfirm"),
    error: flow.form.errors.passwordConfirm,
  });
  return (
    <>
      <PasswordInput
        {...flow.form.getInputProps("password")}
        {...password}
        aria-invalid={Boolean(password.error)}
        name="password"
        autoComplete="new-password"
        disabled={flow.pending}
      />
      <PasswordInput
        {...flow.form.getInputProps("passwordConfirm")}
        {...confirmation}
        aria-invalid={Boolean(confirmation.error)}
        name="password_confirm"
        autoComplete="new-password"
        disabled={flow.pending}
      />
    </>
  );
}

/** Focus new failed submissions while letting visitors edit fields uninterrupted. */
function InvitationErrorNotice({ flow }: { flow: InvitationFlow }) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const { failedSubmissions } = flow;
  const key = flow.invalid
    ? "checkPassword"
    : flow.failure
      ? ERROR_KEYS[flow.failure.error.code]
      : null;
  const count =
    Object.keys(flow.form.errors).length +
    (passwordError(flow) && !flow.form.errors.password ? 1 : 0);
  useEffect(() => {
    if (failedSubmissions > 0) ref.current?.focus();
  }, [failedSubmissions]);
  if (!key) return null;
  return (
    <div ref={ref} tabIndex={-1}>
      <Notice
        type="error"
        title={
          count > 0
            ? t(count === 1 ? "shared.form.errorCountOne" : "shared.form.errorCountOther", {
                count,
              })
            : undefined
        }
      >
        {t(`auth.invitation.${key}`)}
        {["expired", "invalid"].includes(key) && (
          <Text size="sm">{t("auth.invitation.newLinkHelp")}</Text>
        )}
      </Notice>
    </div>
  );
}

/** An existing session stays active until its owner explicitly uses header sign-out. */
function InvitationComplete({ signedIn }: { signedIn: boolean }) {
  const { t } = useTranslation();
  return (
    <Stack gap="md">
      <Title order={1}>{t("auth.invitation.title")}</Title>
      <Notice type="success">{t("auth.invitation.success")}</Notice>
      {signedIn ? (
        <Text>{t("auth.invitation.signedInGuidance")}</Text>
      ) : (
        <Anchor component={Link} to="/sign-in">
          {t("auth.common.signIn")}
        </Anchor>
      )}
    </Stack>
  );
}

/** The server authorizes the token and determines expiry, reuse and account creation. */
export function AcceptInvitation() {
  const { t } = useTranslation();
  const flow = useInvitationFlow();
  if (flow.complete && flow.user === null) return <Navigate to="/sign-in" replace />;
  if (flow.complete) return <InvitationComplete signedIn={Boolean(flow.user)} />;
  return (
    <Stack gap="lg">
      <Title order={1}>{t("auth.invitation.title")}</Title>
      <Text size="sm">{t("shared.form.requiredNotice")}</Text>
      <InvitationErrorNotice flow={flow} />
      <form noValidate onSubmit={(event) => void flow.submit(event)}>
        <Stack gap="md">
          <PasswordFields flow={flow} />
          <Button type="submit" loading={flow.pending} fullWidth>
            {t("auth.invitation.submit")}
          </Button>
        </Stack>
      </form>
      <Anchor component={Link} to="/sign-in">
        {t("auth.common.signIn")}
      </Anchor>
    </Stack>
  );
}
