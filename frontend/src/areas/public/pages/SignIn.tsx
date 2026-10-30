// AI contribution: 50% or more AI-generated
import { Button, PasswordInput, Stack, TextInput, Title } from "@mantine/core";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate } from "react-router";

import { homePathFor } from "../../../app/navigation";
import { TextField } from "../../../shared/forms";
import { useFieldWrapper } from "../../../shared/forms/fieldProps";
import { Notice } from "../../../shared/ui";
import { AuthError } from "../../../shared/auth/api";
import { useAuth } from "../../../shared/auth/authContext";

type Step = "password" | "code";
type ErrorKey =
  "required" | "invalidEmail" | "invalidCode" | "invalidCredentials" | "locked" | "unavailable";

/** The code step appears only when allauth reports a pending MFA challenge. */
export function SignIn() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, signIn, verifyCode, retryProfile } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<Step>("password");
  const [error, setError] = useState<ErrorKey | null>(null);
  const [profileUnavailable, setProfileUnavailable] = useState(false);
  const [pending, setPending] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const passwordWrapper = useFieldWrapper({ label: t("auth.login.password") });
  const codeWrapper = useFieldWrapper({ label: t("auth.login.code") });

  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);

  if (user) return <Navigate to={homePathFor(user.role)} replace />;

  function showError(next: ErrorKey) {
    setError(next);
  }

  async function recoverProfile() {
    setPending(true);
    setError(null);
    try {
      const current = await retryProfile();
      setProfileUnavailable(false);
      navigate(homePathFor(current.role), { replace: true });
    } catch {
      showError("unavailable");
    } finally {
      setPending(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (step === "password" && (!email.trim() || !password)) {
      showError("required");
      return;
    }
    if (step === "password" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      showError("invalidEmail");
      return;
    }
    if (step === "code" && !/^\d{6}$/.test(code)) {
      showError("invalidCode");
      return;
    }
    setPending(true);
    try {
      if (step === "code") {
        const current = await verifyCode(code);
        navigate(homePathFor(current.role), { replace: true });
      } else {
        const result = await signIn(email.trim(), password);
        if (result === "mfa_required") {
          setPassword("");
          setStep("code");
        } else {
          navigate(homePathFor(result.role), { replace: true });
        }
      }
    } catch (caught) {
      if (caught instanceof AuthError) {
        if (caught.code === "profile_unavailable") setProfileUnavailable(true);
        showError(
          caught.code === "locked"
            ? "locked"
            : caught.code === "invalid_code"
              ? "invalidCode"
              : caught.code === "invalid_credentials"
                ? "invalidCredentials"
                : "unavailable",
        );
      } else {
        showError("unavailable");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Stack gap="lg">
      <Title order={1}>{t("auth.login.title")}</Title>
      {error && (
        <div ref={errorRef} tabIndex={-1}>
          <Notice type="error">{t(`auth.login.${error}`)}</Notice>
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
                value={email}
                onChange={setEmail}
                disabled={pending}
              />
              <PasswordInput
                {...passwordWrapper}
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
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
              value={code}
              onChange={(event) => setCode(event.currentTarget.value)}
              disabled={pending}
              description={t("auth.login.codeHelp")}
            />
          )}
          <Button type="submit" loading={pending} fullWidth>
            {t(step === "password" ? "auth.common.signIn" : "auth.login.verify")}
          </Button>
        </Stack>
      </form>
    </Stack>
  );
}
