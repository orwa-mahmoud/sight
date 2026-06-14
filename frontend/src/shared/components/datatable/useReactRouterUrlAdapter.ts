import type { UrlStateAdapter } from "@adapttable/mantine";
import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";

/** Keeps table URL state in sync with react-router `useSearchParams`. */
export function useReactRouterUrlAdapter(): UrlStateAdapter {
  const navigate = useNavigate();
  const location = useLocation();

  return useMemo(
    () => ({
      getSearch: () => location.search.replace(/^\?/, ""),
      setSearch: (search, opts) => navigate({ search }, { replace: !opts?.push }),
      subscribe: () => () => undefined,
    }),
    [location.search, navigate],
  );
}
