// AI contribution: 50% or more AI-generated
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";

import { CURRENT_USER_QUERY_KEY, useCurrentUser } from "../features/accounts/currentUser";
import { checkHouseholdSearchAccess, HouseholdSearchError } from "../features/households/searchApi";
import { ErrorState, LoadingState } from "../shared/ui";
import { homePathFor } from "./navigation";

/** Redirect only after the API refuses access; avoid redirecting back to this screen. */
function RefusedSearch({
  status,
  home,
  onRetry,
}: {
  status: number;
  home: string;
  onRetry: () => void;
}) {
  const location = useLocation();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  useEffect(() => {
    if (status === 401) queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
  }, [queryClient, status]);
  // Drop a stale signed-in profile before redirecting, otherwise the sign-in
  // screen would immediately send the user back to this refused route.
  if (status === 401) return <LoadingState />;
  if (home !== location.pathname) return <Navigate to={home} replace />;
  return (
    <ErrorState
      title={t("household.search.denied")}
      description={t("household.search.deniedDescription")}
      onRetry={onRetry}
    />
  );
}

/** Let the backend authorize search access instead of duplicating its staff role policy. */
export function RequireHouseholdSearch() {
  const location = useLocation();
  const user = useCurrentUser();
  const access = useQuery({
    queryKey: ["household-search-access", user.data?.id],
    queryFn: ({ signal }) => checkHouseholdSearchAccess(signal),
    enabled: Boolean(user.data),
    gcTime: 0,
    staleTime: 0,
    retry: false,
    refetchOnWindowFocus: false,
  });
  if (user.isPending) return <LoadingState />;
  if (user.isError) return <ErrorState onRetry={() => void user.refetch()} />;
  if (!user.data) {
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }
  if (access.isPending) return <LoadingState />;
  if (access.isError) {
    if (access.error instanceof HouseholdSearchError && [401, 403].includes(access.error.status)) {
      return (
        <RefusedSearch
          status={access.error.status}
          home={homePathFor(user.data.role)}
          onRetry={() => void access.refetch()}
        />
      );
    }
    return <ErrorState onRetry={() => void access.refetch()} />;
  }
  return <Outlet />;
}
