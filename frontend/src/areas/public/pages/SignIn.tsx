// AI contribution: 50% or more AI-generated
import { Anchor, Button, PasswordInput, Stack, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useNavigate } from "react-router";

import { homePathFor } from "../../../app/navigation";
import type { Role } from "../../../features/accounts/currentUser";
import { isEmail, isRequired, TextField } from "../../../shared/forms";
import { useFieldWrapper } from "../../../shared/forms/fieldProps";
import { validationMessage } from "../../../shared/forms/validators";
import { logger } from "../../../shared/logger";
import { Notice } from "../../../shared/ui";
import { AuthError, type AuthErrorCode } from "../../../shared/auth/api";
import { useAuth } from "../../../shared/auth/authContext";

type Step = "password" | "code";
type ErrorKey =
  "required" | "invalidEmail" | "invalidCode" | "invalidCredentials" | "locked" | "unavailable";

const ERROR_KEYS: Partial<Record<AuthErrorCode, ErrorKey>> = {
  locked: "locked",
  invalid_code: "invalidCode",
  invalid_credentials: "invalidCredentials",
};

/** Check the visible step before sending credentials to the server. */
function validateStep(step: Step, email: string, password: string, code: string): ErrorKey | null {
  if (step === "code") return /^\d{6}$/.test(code) ? null : "invalidCode";
  if (!email.trim() || !password) return "required";
  return isEmail()(email) ? "invalidEmail" : null;
}

function errorKeyFor(caught: unknown): ErrorKey {
  const code = caught instanceof AuthError ? caught.code : null;
  if (code === null) logger.error("sign_in_failed_unexpectedly");
  return (code && ERROR_KEYS[code]) ?? "unavailable";
}

/** The code step appears only when allauth reports a pending MFA challenge. */
export function SignIn() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  const destination = (role: Role) => from ?? homePathFor(role);
  const { user, signIn, verifyCode, retryProfile } = useAuth();
  const [step, setStep] = useState<Step>("password");
  const form = useForm({
    initialValues: { email: "", password: "", code: "" },
    validateInputOnBlur: true,
    validate: {
      email: (value) => (step === "password" ? isRequired()(value) || isEmail()(value) : null),
      password: (value) => (step === "password" ? isRequired()(value) : null),
      code: (value) =>
        step === "code" && !/^\d{6}$/.test(value)
          ? validationMessage("auth.login.invalidCode")
          : null,
    },
  });
  const [error, setError] = useState<ErrorKey | null>(null);
  const [profileUnavailable, setProfileUnavailable] = useState(false);
  const [pending, setPending] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const passwordWrapper = useFieldWrapper({ label: t("auth.login.password") });
  const codeWrapper = useFieldWrapper({ label: t("auth.login.code") });

  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);

  if (user) return <Navigate to={destination(user.role)} replace />;

  function showError(next: ErrorKey) {
    setError(next);
  }

  async function recoverProfile() {
    setPending(true);
    setError(null);
    try {
      const current = await retryProfile();
      setProfileUnavailable(false);
      navigate(destination(current.role), { replace: true });
    } catch {
      showError("unavailable");
    } finally {
      setPending(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const invalid = validateStep(step, form.values.email, form.values.password, form.values.code);
    if ((await form.validate()).hasErrors && invalid) {
      showError(invalid);
      return;
    }
    setPending(true);
    try {
      if (step === "code") {
        const current = await verifyCode(form.values.code);
        navigate(destination(current.role), { replace: true });
      } else {
        const result = await signIn(form.values.email.trim(), form.values.password);
        if (result === "mfa_required") {
          form.setFieldValue("password", "");
          form.clearErrors();
          setStep("code");
        } else {
          navigate(destination(result.role), { replace: true });
        }
      }
    } catch (caught) {
      if (caught instanceof AuthError && caught.code === "profile_unavailable") {
        setProfileUnavailable(true);
      }
      const key = errorKeyFor(caught);
      if (key === "invalidCredentials") {
        form.setFieldError("email", validationMessage("auth.login.invalidCredentials"));
      } else if (key === "invalidCode") {
        form.setFieldError("code", validationMessage("auth.login.invalidCode"));
      }
      showError(key);
    } finally {
      setPending(false);
    }
  }

  return (
    <Stack gap="lg">
      <Title order={1}>{t("auth.login.title")}</Title>
      {error && (
        <div ref={errorRef} tabIndex={-1}>
          <Notice
            type="error"
            title={
              Object.keys(form.errors).length > 0
                ? t("shared.form.errorCount", { count: Object.keys(form.errors).length })
                : undefined
            }
          >
            {t(`auth.login.${error}`)}
          </Notice>
        </div>
      )}
      {profileUnavailable && (
        <Button
          type="button"
          variant="light"
          loading={pending}
          onClick={() => void recoverProfile()}
        >
          {t("shared.states.retry")}
        </Button>
      )}
      <form onSubmit={(event) => void submit(event)} noValidate>
        <Stack gap="md">
          {step === "password" ? (
            <>
              <TextField
                label={t("auth.login.email")}
                name="email"
                type="email"
                autoComplete="username"
                {...form.getInputProps("email")}
                disabled={pending}
              />
              <PasswordInput
                {...passwordWrapper}
                name="password"
                autoComplete="current-password"
                {...form.getInputProps("password")}
                disabled={pending}
              />
            </>
          ) : (
            <TextInput
              {...codeWrapper}
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              {...form.getInputProps("code")}
              disabled={pending}
              description={t("auth.login.codeHelp")}
            />
          )}
          <Button type="submit" loading={pending} fullWidth>
            {t(step === "password" ? "auth.common.signIn" : "auth.login.verify")}
          </Button>
          {step === "code" && (
            <Button
              type="button"
              variant="subtle"
              disabled={pending}
              onClick={() => {
                form.setFieldValue("code", "");
                form.clearErrors();
                setError(null);
                setStep("password");
              }}
            >
              {t("auth.login.useAnotherAccount")}
            </Button>
          )}
        </Stack>
      </form>
      <Stack gap="xs" align="center">
        <Anchor component={Link} to="/forgot-password" size="sm">
          {t("auth.common.forgotPassword")}
        </Anchor>
        <Anchor component={Link} to="/sign-up" size="sm">
          {t("auth.common.createAccount")}
        </Anchor>
        <Anchor component={Link} to="/partner/apply" size="sm">
          {t("store.partnerApplication.becomePartner")}
        </Anchor>
      </Stack>
    </Stack>
  );
}
