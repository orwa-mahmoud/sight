import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DataTable,
  SelectFilter,
  TextFilter,
  useBackendData,
  useFrontendData,
  type ColumnDef,
  type PaginatedResponse,
  type RowAction,
  type TableQueryParams,
  type TableSource,
} from "@shared/components/datatable";
import { ActiveFilterChips } from "@shared/components/datatable/ActiveFilterChips";
import { TestWrapper } from "@test/wrapper";

interface Row {
  id: string;
  name: string;
  status?: string;
}

const COLUMNS: ColumnDef<Row>[] = [{ key: "name", header: "Name", accessor: (r) => r.name }];

// Columns exercising the default cell (no accessor) + mobileLabel fallback.
const MOBILE_COLUMNS: ColumnDef<Row>[] = [
  { key: "name", header: "Name", accessor: (r) => r.name },
  { key: "status", header: "Status", mobileLabel: "State" },
];

function setMatchMedia(matches: boolean) {
  Object.defineProperty(globalThis, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => setMatchMedia(false));

/* ── useBackendData ─────────────────────────────────────────────── */

function fakeQuery(
  overrides: Partial<UseInfiniteQueryResult<InfiniteData<PaginatedResponse<Row>>, Error>> = {},
): UseInfiniteQueryResult<InfiniteData<PaginatedResponse<Row>>, Error> {
  return {
    data: {
      pages: [{ items: [{ id: "1", name: "Alpha" }], total: 1, page: 1, limit: 20, hasNext: false }],
      pageParams: [],
    },
    isLoading: false,
    isFetching: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    refetch: vi.fn().mockResolvedValue(undefined),
    error: null,
    ...overrides,
  } as unknown as UseInfiniteQueryResult<InfiniteData<PaginatedResponse<Row>>, Error>;
}

function BackendHarness({
  query,
}: Readonly<{ query: UseInfiniteQueryResult<InfiniteData<PaginatedResponse<Row>>, Error> }>) {
  const source = useBackendData<Row, TableQueryParams, PaginatedResponse<Row>>({
    usePaginatedQuery: () => query,
  });
  return <DataTable source={source} columns={COLUMNS} rowKey={(r) => r.id} tableLabel="Rows" />;
}

describe("useBackendData", () => {
  it("renders rows + range from a paged infinite query", () => {
    render(
      <TestWrapper>
        <BackendHarness query={fakeQuery()} />
      </TestWrapper>,
    );
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("1–1 of 1")).toBeInTheDocument();
  });

  it("shows a loading skeleton while the query loads", () => {
    render(
      <TestWrapper>
        <BackendHarness query={fakeQuery({ isLoading: true, data: undefined })} />
      </TestWrapper>,
    );
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
  });

  it("shows an error with a working retry", () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    render(
      <TestWrapper>
        <BackendHarness query={fakeQuery({ error: new Error("boom"), data: undefined, refetch })} />
      </TestWrapper>,
    );
    expect(screen.getByText("Could not load data")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalled();
  });
});

/* ── Mobile cards + infinite "load more" ────────────────────────── */

const MANY: Row[] = Array.from({ length: 25 }, (_, i) => ({
  id: String(i + 1),
  name: `Item ${i + 1}`,
  status: "ready",
}));

function MobileHarness({ onAction }: Readonly<{ onAction?: (row: Row) => void }>) {
  const source = useFrontendData<Row>({ data: MANY, columns: MOBILE_COLUMNS });
  const rowActions: RowAction<Row>[] | undefined = onAction
    ? [{ key: "view", label: "View", onClick: onAction }]
    : undefined;
  return <DataTable source={source} columns={MOBILE_COLUMNS} rowKey={(r) => r.id} rowActions={rowActions} />;
}

describe("DataTable mobile + infinite", () => {
  it("renders mobile cards, default-cell values, and loads more", async () => {
    setMatchMedia(true); // mobile → cards + infinite pagination
    render(
      <TestWrapper>
        <MobileHarness />
      </TestWrapper>,
    );
    expect(screen.getByText("Item 1")).toBeInTheDocument();
    expect(screen.getAllByText("State").length).toBeGreaterThan(0); // mobileLabel
    expect(screen.getAllByText("ready").length).toBeGreaterThan(0); // default cell value
    expect(screen.queryByText("Item 21")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    await waitFor(() => expect(screen.getByText("Item 21")).toBeInTheDocument());
  });

  it("runs a mobile row action", () => {
    setMatchMedia(true);
    const onAction = vi.fn();
    render(
      <TestWrapper>
        <MobileHarness onAction={onAction} />
      </TestWrapper>,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "View" })[0]!);
    expect(onAction).toHaveBeenCalledWith(MANY[0]);
  });
});

/* ── DataTable filter chips + clear ─────────────────────────────── */

describe("DataTable filter chips", () => {
  it("shows a chip for an active filter and clears all", async () => {
    const source = { ...makeSource({ status: "ready" }), clearAll: vi.fn(), setExtra: vi.fn() };
    render(
      <TestWrapper>
        <DataTable
          source={source}
          columns={COLUMNS}
          rowKey={(r) => r.id}
          filters={<div data-testid="filter-widgets" />}
          filterLabels={{ status: (v) => `Status: ${String(v)}` }}
        />
      </TestWrapper>,
    );
    // chip derived from source.extra + filterLabels
    expect(screen.getByText("Status: ready")).toBeInTheDocument();

    // opening the drawer exposes the "Clear all" action
    fireEvent.click(screen.getByRole("button", { name: "Filters" }));
    fireEvent.click(await screen.findByText("Clear all"));
    expect(source.clearAll).toHaveBeenCalled();
  });
});

/* ── SelectFilter ───────────────────────────────────────────────── */

describe("SelectFilter", () => {
  it("renders the current value as the selected option", () => {
    const source = makeSource({ status: "ready" });
    render(
      <TestWrapper>
        <SelectFilter
          source={source}
          filterKey="status"
          label="Status"
          data={[
            { value: "ready", label: "Ready" },
            { value: "failed", label: "Failed" },
          ]}
        />
      </TestWrapper>,
    );
    expect(screen.getByDisplayValue("Ready")).toBeInTheDocument();
  });
});

/* ── TextFilter + ActiveFilterChips ─────────────────────────────── */

function makeSource(extra: Record<string, string> = {}): TableSource<Row> {
  return {
    rows: [],
    total: 0,
    isLoading: false,
    isFetching: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    error: null,
    paginationMode: "paged",
    page: 1,
    limit: 20,
    search: "",
    sortBy: undefined,
    sortDir: undefined,
    extra,
    setPage: vi.fn(),
    setLimit: vi.fn(),
    setSort: vi.fn(),
    setSearch: vi.fn(),
    setExtra: vi.fn(),
    clearAll: vi.fn(),
  };
}

describe("TextFilter", () => {
  it("writes typed input to source.extra", () => {
    const source = makeSource();
    render(
      <TestWrapper>
        <TextFilter source={source} filterKey="q" label="Name" />
      </TestWrapper>,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "abc" } });
    expect(source.setExtra).toHaveBeenCalledWith("q", "abc");
  });

  it("clears the filter when emptied", () => {
    const source = makeSource({ q: "abc" });
    render(
      <TestWrapper>
        <TextFilter source={source} filterKey="q" label="Name" />
      </TestWrapper>,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "" } });
    expect(source.setExtra).toHaveBeenCalledWith("q", undefined);
  });
});

describe("ActiveFilterChips", () => {
  it("renders nothing when empty", () => {
    const { container } = render(
      <TestWrapper>
        <ActiveFilterChips chips={[]} onRemove={vi.fn()} />
      </TestWrapper>,
    );
    expect(container.querySelector(".mantine-Pill-root")).toBeNull();
  });

  it("renders chips and removes them", () => {
    const onRemove = vi.fn();
    const { container } = render(
      <TestWrapper>
        <ActiveFilterChips chips={[{ key: "status", label: "Status: ready" }]} onRemove={onRemove} />
      </TestWrapper>,
    );
    expect(screen.getByText("Status: ready")).toBeInTheDocument();
    const removeBtn = container.querySelector(".mantine-Pill-remove");
    expect(removeBtn).not.toBeNull();
    fireEvent.click(removeBtn!);
    expect(onRemove).toHaveBeenCalledWith("status");
  });
});
