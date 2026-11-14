// AI contribution: 50% or more AI-generated
import { Anchor, Button, PasswordInput, Stack, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useNavigate } from "react-router";

import { homePathFor, type Role } from "../../../shared/auth/roles";
import { isEmail, isRequired, TextField } from "../../../shared/forms";
import { useFieldWrapper } from "../../../shared/forms/fieldProps";
import { validationMessage } from "../../../shared/forms/validators";
import { logger } from "../../../shared/logger";
import { Notice } from "../../../shared/ui";
import { AuthError, type AuthErrorCode } from "../../../shared/auth/api";
import { useAuth, type AuthContextValue } from "../../../shared/auth/authContext";

type ErrorKey = "required" | "invalidEmail" | "invalidCredentials" | "locked" | "unavailable";

const ERROR_KEYS: Partial<Record<AuthErrorCode, ErrorKey>> = {
  locked: "locked",
  invalid_credentials: "invalidCredentials",
};

/** Check the credentials before sending them to the server. */
function validateCredentials(email: string, password: string): ErrorKey | null {
  if (!email.trim() || !password.trim()) return "required";
  return isEmail()(email) ? "invalidEmail" : null;
}

function errorKeyFor(caught: unknown): ErrorKey {
  const code = caught instanceof AuthError ? caught.code : null;
  if (code === null) logger.error("sign_in_failed_unexpectedly");
  return (code && ERROR_KEYS[code]) ?? "unavailable";
}

function useSignInState() {
  const form = useForm({
    initialValues: { email: "", password: "" },
    validateInputOnBlur: true,
    validate: {
      email: (value) => isRequired()(value) || isEmail()(value),
      password: isRequired(),
    },
  });
  const [error, setError] = useState<ErrorKey | null>(null);
  const [profileUnavailable, setProfileUnavailable] = useState(false);
  const [pending, setPending] = useState(false);
  return {
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
  const { form } = state;
  state.setError(null);
  const { hasErrors } = await form.validate();
  const invalid = validateCredentials(form.values.email, form.values.password);
  if (hasErrors || invalid) {
    state.setError(invalid ?? "required");
    return;
  }
  state.setPending(true);
  try {
    const current = await auth.signIn(form.values.email.trim(), form.values.password);
    navigate(destination(current.role), { replace: true });
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
  };
}

type SignInFlow = ReturnType<typeof useSignInFlow>;

function CredentialFields({ flow }: { flow: SignInFlow }) {
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

function SignInForm({ flow }: { flow: SignInFlow }) {
  const { t } = useTranslation();
  return (
    <form onSubmit={(event) => void flow.submit(event)} noValidate>
      <Stack gap="md">
        <CredentialFields flow={flow} />
        <Button type="submit" loading={flow.pending} fullWidth>
          {t("auth.common.signIn")}
        </Button>
      </Stack>
    </form>
  );
}

function SignInLinks() {
  const { t } = useTranslation();
  // Password reset and online sign-up add their links with their screens.
  return (
    <Stack gap="xs" align="center">
      <Anchor component={Link} to="/partner/apply" size="sm">
        {t("store.partnerApplication.becomePartner")}
      </Anchor>
    </Stack>
  );
}

/** Password sign-in uses the current allauth browser session endpoints. */
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
                ? t(
                    Object.keys(flow.form.errors).length === 1
                      ? "shared.form.errorCountOne"
                      : "shared.form.errorCountOther",
                    { count: Object.keys(flow.form.errors).length },
                  )
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
