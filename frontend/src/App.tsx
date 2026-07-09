import {
  Activity,
  Bot,
  BrainCircuit,
  CalendarClock,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Database,
  Gauge,
  HeartPulse,
  Menu,
  Play,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Users,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "./api";

type PageKey =
  | "dashboard"
  | "data-center"
  | "post-pool"
  | "ai-workspace"
  | "scheduler"
  | "account-center"
  | "execution"
  | "engagement"
  | "statistics"
  | "settings";

type RecordItem = Record<string, unknown>;

type DashboardData = {
  overview: {
    posts: number;
    ai_pending: number;
    scheduler_queue: number;
    active_accounts: number;
    data_sources: number;
  };
  platform_health: Array<{
    name: string;
    slug: string;
    status: string;
    enabled: boolean;
  }>;
  system_health: Array<{ service: string; status: string }>;
};

const navigation = [
  { key: "dashboard", label: "Dashboard", icon: Gauge },
  { key: "data-center", label: "Data Center", icon: Database },
  { key: "post-pool", label: "Post Pool", icon: Search },
  { key: "ai-workspace", label: "AI Workspace", icon: BrainCircuit },
  { key: "scheduler", label: "Scheduler", icon: CalendarClock },
  { key: "account-center", label: "Account Center", icon: Users },
  { key: "execution", label: "Execution", icon: Play },
  { key: "engagement", label: "Engagement", icon: Activity },
  { key: "statistics", label: "Statistics", icon: ChartNoAxesCombined },
  { key: "settings", label: "System Settings", icon: Settings },
] as const;

const pageMeta: Record<PageKey, { title: string; subtitle: string }> = {
  dashboard: { title: "运行总览", subtitle: "系统状态、队列与关键运营指标" },
  "data-center": { title: "Data Center", subtitle: "管理可插拔数据源与采集配置" },
  "post-pool": { title: "Post Pool", subtitle: "所有平台内容进入系统后的统一池" },
  "ai-workspace": { title: "AI Workspace", subtitle: "分析、评分、策略与人工审核" },
  scheduler: { title: "Scheduler", subtitle: "进入 Execution 前的唯一任务队列" },
  "account-center": { title: "Account Center", subtitle: "平台账号、健康度与运行限制" },
  execution: { title: "Execution Center", subtitle: "执行运行时占位与环境状态" },
  engagement: { title: "Engagement", subtitle: "策略组合与互动任务占位" },
  statistics: { title: "Statistics", subtitle: "事件驱动统计与转化漏斗占位" },
  settings: { title: "System Settings", subtitle: "模型、平台、调度与执行配置" },
};

function useApiData<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await apiGet<T>(path));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, error, loading, reload: load };
}

function StatusBadge({ value }: { value: unknown }) {
  const label = String(value ?? "UNKNOWN");
  const good = ["ACTIVE", "READY", "HEALTHY", "APPROVED", "QUALIFIED", "LOW"].includes(
    label,
  );
  const warning = ["QUEUED", "REVIEWING", "NEW", "PLANNED", "PLACEHOLDER"].includes(label);
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded px-2 py-1 text-xs font-semibold ${
        good
          ? "bg-emerald-50 text-emerald-700"
          : warning
            ? "bg-amber-50 text-amber-700"
            : "bg-red-50 text-red-700"
      }`}
    >
      <span
        className={`status-dot ${
          good ? "bg-emerald-500" : warning ? "bg-amber-500" : "bg-red-500"
        }`}
      />
      {label}
    </span>
  );
}

function StateView({
  loading,
  error,
  reload,
  children,
}: {
  loading: boolean;
  error: string;
  reload: () => void;
  children: React.ReactNode;
}) {
  if (loading) {
    return (
      <div className="grid gap-3 md:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="panel h-28 animate-pulse bg-gray-100" />
        ))}
      </div>
    );
  }
  if (error) {
    return (
      <div className="panel flex min-h-52 flex-col items-center justify-center gap-3 p-6 text-center">
        <CircleAlert className="h-7 w-7 text-red-600" />
        <div>
          <p className="font-semibold">API 暂时不可用</p>
          <p className="mt-1 text-sm text-gray-500">{error}</p>
        </div>
        <button className="button-secondary" onClick={reload}>
          <RefreshCw className="h-4 w-4" />
          重试
        </button>
      </div>
    );
  }
  return children;
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="panel flex min-h-48 flex-col items-center justify-center p-6 text-center">
      <Workflow className="h-8 w-8 text-gray-400" />
      <p className="mt-3 font-semibold">{title}</p>
      <p className="mt-1 max-w-md text-sm text-gray-500">{detail}</p>
    </div>
  );
}

function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-bold uppercase text-gray-500">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function DataTable({
  columns,
  rows,
}: {
  columns: Array<{ key: string; label: string }>;
  rows: RecordItem[];
}) {
  return (
    <div className="panel overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
            {columns.map((column) => (
              <th key={column.key} className="px-4 py-3 font-semibold">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.uuid ?? index)} className="border-b border-line last:border-0">
              {columns.map((column) => {
                const value = row[column.key];
                return (
                  <td key={column.key} className="max-w-xs px-4 py-3 align-top">
                    {column.key === "status" || column.key === "risk_level" ? (
                      <StatusBadge value={value} />
                    ) : column.key === "title" ? (
                      <span className="font-medium text-ink">{String(value ?? "—")}</span>
                    ) : typeof value === "object" && value !== null ? (
                      <span className="text-xs text-gray-500">{JSON.stringify(value)}</span>
                    ) : (
                      <span className="text-gray-600">{String(value ?? "—")}</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DashboardPage() {
  const { data, error, loading, reload } =
    useApiData<DashboardData>("/dashboard/summary");
  const cards = data
    ? [
        { label: "Posts", value: data.overview.posts, icon: Search, tone: "text-cyan" },
        { label: "AI Pending", value: data.overview.ai_pending, icon: Sparkles, tone: "text-teal" },
        {
          label: "Scheduler Queue",
          value: data.overview.scheduler_queue,
          icon: CalendarClock,
          tone: "text-amber",
        },
        {
          label: "Active Accounts",
          value: data.overview.active_accounts,
          icon: Users,
          tone: "text-emerald-700",
        },
        {
          label: "Data Sources",
          value: data.overview.data_sources,
          icon: Database,
          tone: "text-blue-700",
        },
      ]
    : [];

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-7">
        <Section
          title="Overview"
          action={
            <button className="icon-button" title="刷新" onClick={reload}>
              <RefreshCw className="h-4 w-4" />
            </button>
          }
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {cards.map((card) => (
              <div key={card.label} className="panel min-h-28 p-4">
                <div className="flex items-start justify-between">
                  <span className="text-xs font-semibold uppercase text-gray-500">
                    {card.label}
                  </span>
                  <card.icon className={`h-5 w-5 ${card.tone}`} />
                </div>
                <p className="mt-5 text-3xl font-bold">{card.value}</p>
              </div>
            ))}
          </div>
        </Section>
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Section title="Platform Health">
            <div className="panel divide-y divide-line">
              {data?.platform_health.map((platform) => (
                <div
                  key={platform.slug}
                  className="flex items-center justify-between gap-3 px-4 py-3"
                >
                  <div>
                    <p className="font-medium">{platform.name}</p>
                    <p className="text-xs text-gray-500">{platform.slug}</p>
                  </div>
                  <StatusBadge value={platform.status} />
                </div>
              ))}
            </div>
          </Section>
          <Section title="System Health">
            <div className="panel divide-y divide-line">
              {data?.system_health.map((service) => (
                <div
                  key={service.service}
                  className="flex items-center justify-between gap-3 px-4 py-3"
                >
                  <span className="font-medium">{service.service}</span>
                  <StatusBadge value={service.status} />
                </div>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </StateView>
  );
}

function DataCenterPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/data-sources");
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <Section
        title="Configured Sources"
        action={
          <button className="button">
            <Database className="h-4 w-4" />
            新建数据源
          </button>
        }
      >
        <DataTable
          columns={[
            { key: "name", label: "Name" },
            { key: "source_type", label: "Type" },
            { key: "adapter_key", label: "Adapter" },
            { key: "status", label: "Status" },
            { key: "last_run_at", label: "Last Run" },
          ]}
          rows={data ?? []}
        />
      </Section>
    </StateView>
  );
}

function PostPoolPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/posts");
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <Section
        title="Unified Post Pool"
        action={
          <div className="flex gap-2">
            <button className="button-secondary">
              <SlidersHorizontal className="h-4 w-4" />
              筛选
            </button>
            <button className="icon-button" title="刷新" onClick={reload}>
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        }
      >
        <DataTable
          columns={[
            { key: "title", label: "Post" },
            { key: "community", label: "Community" },
            { key: "author", label: "Author" },
            { key: "language", label: "Language" },
            { key: "status", label: "Status" },
          ]}
          rows={data ?? []}
        />
      </Section>
    </StateView>
  );
}

function AIWorkspacePage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/ai/tasks");
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <Section title="Review Queue">
        <DataTable
          columns={[
            { key: "strategy", label: "Strategy" },
            { key: "provider", label: "Provider" },
            { key: "model", label: "Model" },
            { key: "commercial_score", label: "Commercial" },
            { key: "risk_score", label: "Risk" },
            { key: "status", label: "Status" },
          ]}
          rows={data ?? []}
        />
      </Section>
    </StateView>
  );
}

function SchedulerPage() {
  const { data, error, loading, reload } =
    useApiData<RecordItem[]>("/scheduler/tasks");
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <Section
        title="Database Queue"
        action={
          <span className="rounded bg-cyan/10 px-2 py-1 text-xs font-semibold text-cyan">
            Execution 唯一入口
          </span>
        }
      >
        <DataTable
          columns={[
            { key: "task_type", label: "Task" },
            { key: "priority", label: "Priority" },
            { key: "account_id", label: "Account" },
            { key: "scheduled_at", label: "Scheduled" },
            { key: "status", label: "Status" },
          ]}
          rows={data ?? []}
        />
      </Section>
    </StateView>
  );
}

function AccountCenterPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/accounts");
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <Section title="Account Assets">
        <DataTable
          columns={[
            { key: "username", label: "Username" },
            { key: "display_name", label: "Display Name" },
            { key: "health_score", label: "Health" },
            { key: "risk_level", label: "Risk" },
            { key: "daily_limits", label: "Daily Limits" },
            { key: "status", label: "Status" },
          ]}
          rows={data ?? []}
        />
      </Section>
    </StateView>
  );
}

function SettingsPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/settings");
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <Section title="Configuration Service">
        <div className="grid gap-3 lg:grid-cols-2">
          {(data ?? []).map((item, index) => (
            <div key={String(item.uuid ?? index)} className="panel p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{String(item.key)}</p>
                  <p className="mt-1 text-xs uppercase text-gray-500">
                    {String(item.category)}
                  </p>
                </div>
                <StatusBadge value={item.status} />
              </div>
              <pre className="mt-4 overflow-x-auto border-t border-line pt-3 text-xs text-gray-600">
                {JSON.stringify(item.value, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </Section>
    </StateView>
  );
}

function PlaceholderPage({
  icon: Icon,
  title,
  detail,
  states,
}: {
  icon: typeof Zap;
  title: string;
  detail: string;
  states: string[];
}) {
  return (
    <div className="space-y-6">
      <div className="panel flex items-start gap-4 p-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-gray-100">
          <Icon className="h-5 w-5 text-gray-600" />
        </div>
        <div>
          <h2 className="font-bold">{title}</h2>
          <p className="mt-1 text-sm text-gray-500">{detail}</p>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {states.map((state) => (
          <div key={state} className="panel p-4">
            <p className="text-xs font-semibold uppercase text-gray-500">{state}</p>
            <p className="mt-4 text-2xl font-bold">0</p>
            <p className="mt-1 text-xs text-gray-400">等待后续 Runtime 接入</p>
          </div>
        ))}
      </div>
      <EmptyState title="MVP 占位已就绪" detail="页面边界、导航和状态区域已建立，后续能力通过独立 Service 与 API 接入。" />
    </div>
  );
}

function PageContent({ page }: { page: PageKey }) {
  switch (page) {
    case "dashboard":
      return <DashboardPage />;
    case "data-center":
      return <DataCenterPage />;
    case "post-pool":
      return <PostPoolPage />;
    case "ai-workspace":
      return <AIWorkspacePage />;
    case "scheduler":
      return <SchedulerPage />;
    case "account-center":
      return <AccountCenterPage />;
    case "settings":
      return <SettingsPage />;
    case "execution":
      return (
        <PlaceholderPage
          icon={Play}
          title="Execution Runtime"
          detail="Execution 只消费 Scheduler 分发的任务；当前版本不执行浏览器动作。"
          states={["Waiting", "Running", "Error"]}
        />
      );
    case "engagement":
      return (
        <PlaceholderPage
          icon={Activity}
          title="Engagement Strategies"
          detail="策略、配置和任务边界已预留，v0.1 不自动执行平台互动。"
          states={["Strategies", "Queued", "Cooling"]}
        />
      );
    case "statistics":
      return (
        <PlaceholderPage
          icon={ChartNoAxesCombined}
          title="Event Analytics"
          detail="统计中心将通过事件消费构建指标，不直接修改业务数据。"
          states={["Events", "Aggregations", "Alerts"]}
        />
      );
  }
}

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const current = pageMeta[page];
  const currentNav = useMemo(() => navigation.find((item) => item.key === page), [page]);

  function navigate(next: PageKey) {
    setPage(next);
    setMobileNavOpen(false);
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center border-b border-line bg-white">
        <div className="flex h-full w-64 shrink-0 items-center gap-3 border-r border-line px-4">
          <button className="icon-button lg:hidden" onClick={() => setMobileNavOpen(true)}>
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded bg-ink text-white">
            <Workflow className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-black">ATOS</p>
            <p className="text-[10px] uppercase text-gray-500">Local Console v0.1</p>
          </div>
        </div>
        <div className="flex min-w-0 flex-1 items-center justify-between gap-3 px-4">
          <button
            className="hidden h-9 w-full max-w-md items-center gap-2 border border-line bg-gray-50 px-3 text-left text-sm text-gray-500 md:flex"
            style={{ borderRadius: 5 }}
            onClick={() => setSearchOpen(!searchOpen)}
          >
            <Search className="h-4 w-4" />
            搜索模块与任务
          </button>
          <div className="ml-auto flex items-center gap-2">
            <div className="hidden items-center gap-2 text-xs text-emerald-700 sm:flex">
              <span className="status-dot bg-emerald-500" />
              Local
            </div>
            <button className="icon-button" title="系统健康">
              <HeartPulse className="h-4 w-4" />
            </button>
            <div className="flex h-9 w-9 items-center justify-center rounded bg-teal text-sm font-bold text-white">
              A
            </div>
          </div>
        </div>
      </header>

      <aside
        className={`fixed bottom-0 left-0 top-16 z-30 w-64 border-r border-line bg-white transition-transform lg:translate-x-0 ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-line px-4 py-3 lg:hidden">
          <span className="text-sm font-semibold">导航</span>
          <button className="icon-button" onClick={() => setMobileNavOpen(false)}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="space-y-1 p-3">
          {navigation.map((item) => (
            <button
              key={item.key}
              onClick={() => navigate(item.key)}
              className={`flex h-10 w-full items-center gap-3 px-3 text-left text-sm font-medium transition ${
                page === item.key
                  ? "bg-gray-100 text-ink"
                  : "text-gray-600 hover:bg-gray-50 hover:text-ink"
              }`}
              style={{ borderRadius: 5 }}
            >
              <item.icon className={`h-4 w-4 ${page === item.key ? "text-teal" : ""}`} />
              <span className="min-w-0 flex-1 truncate">{item.label}</span>
              {page === item.key && <ChevronRight className="h-4 w-4 text-gray-400" />}
            </button>
          ))}
        </nav>
        <div className="absolute bottom-0 inset-x-0 border-t border-line p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            Human-in-the-loop mode
          </div>
        </div>
      </aside>

      {mobileNavOpen && (
        <button
          className="fixed inset-0 z-20 bg-black/20 lg:hidden"
          aria-label="关闭导航"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <main className="pt-16 lg:pl-64">
        <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase text-gray-500">
                {currentNav && <currentNav.icon className="h-3.5 w-3.5" />}
                {currentNav?.label}
              </div>
              <h1 className="mt-2 text-2xl font-bold">{current.title}</h1>
              <p className="mt-1 text-sm text-gray-500">{current.subtitle}</p>
            </div>
            <div className="flex gap-2">
              <button className="button-secondary">
                <Bot className="h-4 w-4" />
                Worker 状态
              </button>
              <button className="button">
                <Zap className="h-4 w-4" />
                Quick Action
              </button>
            </div>
          </div>
          <PageContent page={page} />
        </div>
      </main>
    </div>
  );
}
