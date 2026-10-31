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
import { useAuth, type AuthContextValue } from "../../../shared/auth/authContext";

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

function useSignInState() {
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
  return {
    step,
    setStep,
    form,
    error,
    setError,
    profileUnavailable,
    setProfileUnavailable,
    pending,
    setPending,
  };
}

type SignInState = ReturnType<typeof useSignInState>;
type SignInActions = {
  state: SignInState;
  auth: AuthContextValue;
  destination: (role: Role) => string;
  navigate: ReturnType<typeof useNavigate>;
};

function handleSignInError(caught: unknown, state: SignInState) {
  if (caught instanceof AuthError && caught.code === "profile_unavailable") {
    state.setProfileUnavailable(true);
  }
  const key = errorKeyFor(caught);
  if (key === "invalidCredentials") {
    state.form.setFieldError("email", validationMessage("auth.login.invalidCredentials"));
  } else if (key === "invalidCode") {
    state.form.setFieldError("code", validationMessage("auth.login.invalidCode"));
  }
  state.setError(key);
}

async function recoverProfile({ state, auth, destination, navigate }: SignInActions) {
  state.setPending(true);
  state.setError(null);
  try {
    const current = await auth.retryProfile();
    state.setProfileUnavailable(false);
    navigate(destination(current.role), { replace: true });
  } catch {
    state.setError("unavailable");
  } finally {
    state.setPending(false);
  }
}

async function submitCredentials(event: FormEvent<HTMLFormElement>, actions: SignInActions) {
  event.preventDefault();
  const { state, auth, destination, navigate } = actions;
  const { step, form } = state;
  state.setError(null);
  const invalid = validateStep(step, form.values.email, form.values.password, form.values.code);
  if ((await form.validate()).hasErrors && invalid) {
    state.setError(invalid);
    return;
  }
  state.setPending(true);
  try {
    if (step === "code") {
      const current = await auth.verifyCode(form.values.code);
      navigate(destination(current.role), { replace: true });
    } else {
      const result = await auth.signIn(form.values.email.trim(), form.values.password);
      if (result === "mfa_required") {
        form.setFieldValue("password", "");
        form.clearErrors();
        state.setStep("code");
      } else {
        navigate(destination(result.role), { replace: true });
      }
    }
  } catch (caught) {
    handleSignInError(caught, state);
  } finally {
    state.setPending(false);
  }
}

function useSignInFlow() {
  const state = useSignInState();
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  const destination = (role: Role) => from ?? homePathFor(role);
  const actions = { state, auth, destination, navigate };
  return {
    ...state,
    user: auth.user,
    destination,
    submit: (event: FormEvent<HTMLFormElement>) => submitCredentials(event, actions),
    recover: () => recoverProfile(actions),
    useAnotherAccount: () => {
      state.form.setFieldValue("code", "");
      state.form.clearErrors();
      state.setError(null);
      state.setStep("password");
    },
  };
}

type SignInFlow = ReturnType<typeof useSignInFlow>;

function PasswordStep({ flow }: { flow: SignInFlow }) {
  const { t } = useTranslation();
  const passwordWrapper = useFieldWrapper({ label: t("auth.login.password") });
  return (
    <>
      <TextField
        label={t("auth.login.email")}
        name="email"
        type="email"
        autoComplete="username"
        {...flow.form.getInputProps("email")}
        disabled={flow.pending}
      />
      <PasswordInput
        {...passwordWrapper}
        name="password"
        autoComplete="current-password"
        {...flow.form.getInputProps("password")}
        disabled={flow.pending}
      />
    </>
  );
}

function CodeStep({ flow }: { flow: SignInFlow }) {
  const { t } = useTranslation();
  const codeWrapper = useFieldWrapper({ label: t("auth.login.code") });
  return (
    <TextInput
      {...codeWrapper}
      name="code"
      inputMode="numeric"
      autoComplete="one-time-code"
      maxLength={6}
      {...flow.form.getInputProps("code")}
      disabled={flow.pending}
      description={t("auth.login.codeHelp")}
    />
  );
}

function SignInForm({ flow }: { flow: SignInFlow }) {
  const { t } = useTranslation();
  return (
    <form onSubmit={(event) => void flow.submit(event)} noValidate>
      <Stack gap="md">
        {flow.step === "password" ? <PasswordStep flow={flow} /> : <CodeStep flow={flow} />}
        <Button type="submit" loading={flow.pending} fullWidth>
          {t(flow.step === "password" ? "auth.common.signIn" : "auth.login.verify")}
        </Button>
        {flow.step === "code" && (
          <Button
            type="button"
            variant="subtle"
            disabled={flow.pending}
            onClick={flow.useAnotherAccount}
          >
            {t("auth.login.useAnotherAccount")}
          </Button>
        )}
      </Stack>
    </form>
  );
}

function SignInLinks() {
  const { t } = useTranslation();
  return (
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
  );
}

/** The code step appears only when allauth reports a pending MFA challenge. */
export function SignIn() {
  const { t } = useTranslation();
  const flow = useSignInFlow();
  const errorRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (flow.error) errorRef.current?.focus();
  }, [flow.error]);

  if (flow.user) return <Navigate to={flow.destination(flow.user.role)} replace />;

  return (
    <Stack gap="lg">
      <Title order={1}>{t("auth.login.title")}</Title>
      {flow.error && (
        <div ref={errorRef} tabIndex={-1}>
          <Notice
            type="error"
            title={
              Object.keys(flow.form.errors).length > 0
                ? t("shared.form.errorCount", { count: Object.keys(flow.form.errors).length })
                : undefined
            }
          >
            {t(`auth.login.${flow.error}`)}
          </Notice>
        </div>
      )}
      {flow.profileUnavailable && (
        <Button
          type="button"
          variant="light"
          loading={flow.pending}
          onClick={() => void flow.recover()}
        >
          {t("shared.states.retry")}
        </Button>
      )}
      <SignInForm flow={flow} />
      <SignInLinks />
    </Stack>
  );
}
