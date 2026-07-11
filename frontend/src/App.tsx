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
  ExternalLink,
  FileClock,
  Gauge,
  HeartPulse,
  Menu,
  Play,
  Pencil,
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
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { apiGet, apiRequest } from "./api";

type PageKey =
  | "dashboard"
  | "data-center"
  | "post-pool"
  | "ai-workspace"
  | "scheduler"
  | "platform-center"
  | "worker-center"
  | "intelligence"
  | "account-center"
  | "execution"
  | "submission"
  | "engagement"
  | "statistics"
  | "settings";

type RecordItem = Record<string, unknown>;

type SourceConfig = {
  actor_id?: string;
  actor_name?: string;
  remark?: string;
  input_json?: Record<string, unknown>;
  max_items?: number;
  token_configured?: boolean;
  token_masked?: string;
  last_error?: string;
};

type DataSourceItem = RecordItem & {
  id: number;
  name: string;
  platform_id?: number;
  platform?: string;
  enabled: boolean;
  status: string;
  config: SourceConfig;
  latest_log?: RecordItem | null;
};

type PlatformOption = {
  id: number;
  name: string;
  slug: string;
  enabled: boolean;
};

type LLMProviderItem = RecordItem & {
  id: number;
  provider_name: string;
  provider_type: string;
  api_base_url?: string | null;
  model_name: string;
  enabled: boolean;
  priority: number;
  use_for_analysis: boolean;
  use_for_reply: boolean;
  use_for_embedding: boolean;
  is_mock: boolean;
  timeout_seconds: number;
  max_retries: number;
  remark?: string | null;
  api_key_configured?: boolean;
  api_key_masked?: string | null;
};

type DashboardData = {
  overview: {
    posts: number;
    version?: string;
    environment?: string;
    emergency_stop_active?: boolean;
    ai_pending: number;
    scheduler_queue: number;
    scheduler_pending?: number;
    scheduler_ready?: number;
    scheduler_delayed?: number;
    scheduler_failed?: number;
    no_available_account?: number;
    active_accounts: number;
    cooling_accounts?: number;
    high_risk_accounts?: number;
    tge_profiles_active?: number;
    accounts_without_tge?: number;
    execution_received?: number;
    execution_environment_ready?: number;
    execution_failed?: number;
    execution_queue?: number;
    execution_workers?: number;
    execution_running?: number;
    execution_success?: number;
    browser_running?: number;
    browser_tabs_open?: number;
    browser_dead_sessions?: number;
    tge_connection_failed?: number;
    tge_running?: number;
    tge_unknown?: number;
    data_sources: number;
    today_browse?: number;
    today_like?: number;
    today_profile_visit?: number;
    warmup_tasks?: number;
    engagement_success_rate?: number;
    llm_provider_health?: string;
    fallback_rate?: number;
    average_latency_ms?: number;
    ai_cost_today?: number;
    pipeline_today_imported?: number;
    pipeline_today_ai?: number;
    pipeline_approved?: number;
    pipeline_scheduled?: number;
    pipeline_success_rate?: number;
    active_platforms?: number;
    healthy_platforms?: number;
    failed_adapters?: number;
    worker_online?: number;
    worker_offline?: number;
    worker_running_tasks?: number;
    worker_capacity?: number;
    automation_retry_pending?: number;
    automation_worker_lost?: number;
    automation_alerts?: number;
    automation_queue_length?: number;
    intelligence_recommendations?: number;
    reply_average_score?: number;
    content_average_score?: number;
    best_time_windows?: number;
    submission_ready?: number;
    submission_waiting_manual?: number;
    submission_submitting?: number;
    submission_verified?: number;
    submission_failed?: number;
    submission_manual_required?: number;
    auto_assisted_submitting?: number;
    auto_assisted_completed?: number;
    auto_assisted_manual_review?: number;
    reddit_waiting_manual?: number;
    x_waiting_manual?: number;
    reddit_failed?: number;
    x_failed?: number;
    manual_confirmed_today?: number;
    retry_pending?: number;
    template_generated_today?: number;
    template_verified_today?: number;
    template_success_rate?: number;
    high_risk_template_usage?: number;
    template_platforms?: number;
  };
  platform_health: Array<{
    name: string;
    slug: string;
    status: string;
    enabled: boolean;
    adapter?: string;
    version?: string;
    capabilities?: string[];
  }>;
  system_health: Array<{ service: string; status: string }>;
};

type PagedRecords = {
  items: RecordItem[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
};

function listFromResponse(value: RecordItem[] | PagedRecords | null): RecordItem[] {
  if (!value) return [];
  return Array.isArray(value) ? value : value.items ?? [];
}

const navigation = [
  { key: "dashboard", label: "Dashboard", icon: Gauge },
  { key: "data-center", label: "Data Center", icon: Database },
  { key: "post-pool", label: "Post Pool", icon: Search },
  { key: "ai-workspace", label: "AI Workspace", icon: BrainCircuit },
  { key: "scheduler", label: "Scheduler", icon: CalendarClock },
  { key: "platform-center", label: "Platform Center", icon: SlidersHorizontal },
  { key: "worker-center", label: "Worker Center", icon: Bot },
  { key: "intelligence", label: "Intelligence", icon: Sparkles },
  { key: "account-center", label: "Account Center", icon: Users },
  { key: "execution", label: "Execution", icon: Play },
  { key: "submission", label: "Submission", icon: CheckCircle2 },
  { key: "engagement", label: "Engagement", icon: Activity },
  { key: "statistics", label: "Statistics", icon: ChartNoAxesCombined },
  { key: "settings", label: "System Settings", icon: Settings },
] as const;

const pageRoutes: Record<PageKey, string> = {
  dashboard: "/",
  "data-center": "/data-center",
  "post-pool": "/post-pool",
  "ai-workspace": "/ai-workspace",
  scheduler: "/scheduler",
  "platform-center": "/platform-center",
  "worker-center": "/worker-center",
  intelligence: "/intelligence",
  "account-center": "/account-center",
  execution: "/execution",
  submission: "/submission",
  engagement: "/engagement",
  statistics: "/statistics",
  settings: "/settings",
};

const routePages = Object.fromEntries(
  Object.entries(pageRoutes).map(([key, value]) => [value, key as PageKey]),
) as Record<string, PageKey>;

const pageMeta: Record<PageKey, { title: string; subtitle: string }> = {
  dashboard: { title: "运行总览", subtitle: "系统状态、队列与关键运营指标" },
  "data-center": { title: "Data Center", subtitle: "管理可插拔数据源与采集配置" },
  "post-pool": { title: "Post Pool", subtitle: "所有平台内容进入系统后的统一池" },
  "ai-workspace": { title: "AI Workspace", subtitle: "分析、评分、策略与人工审核" },
  scheduler: { title: "Scheduler", subtitle: "进入 Execution 前的唯一任务队列" },
  "platform-center": { title: "Platform Center", subtitle: "平台 Adapter、能力与健康状态" },
  "worker-center": { title: "Worker Center", subtitle: "Automation Runtime、Worker Pool 与任务 Claim" },
  intelligence: { title: "Intelligence Runtime", subtitle: "表现分析、评分、推荐与策略优化" },
  "account-center": { title: "Account Center", subtitle: "平台账号、健康度与运行限制" },
  execution: { title: "Execution Center", subtitle: "执行运行时占位与环境状态" },
  submission: { title: "Submission Runtime", subtitle: "半自动提交记录、策略闸门与结果验证" },
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
        { label: "Version", value: data.overview.version ?? "—", icon: Settings, tone: "text-blue-700" },
        { label: "Environment", value: data.overview.environment ?? "—", icon: ShieldCheck, tone: "text-teal" },
        {
          label: "Emergency Stop",
          value: data.overview.emergency_stop_active ? "ACTIVE" : "Clear",
          icon: ShieldCheck,
          tone: data.overview.emergency_stop_active ? "text-red-700" : "text-emerald-700",
        },
        { label: "AI Pending", value: data.overview.ai_pending, icon: Sparkles, tone: "text-teal" },
        {
          label: "Scheduler Queue",
          value: data.overview.scheduler_queue,
          icon: CalendarClock,
          tone: "text-amber",
        },
        {
          label: "Scheduler Ready",
          value: data.overview.scheduler_ready ?? 0,
          icon: CheckCircle2,
          tone: "text-emerald-700",
        },
        {
          label: "Scheduler Delayed",
          value: data.overview.scheduler_delayed ?? 0,
          icon: RefreshCw,
          tone: "text-blue-700",
        },
        {
          label: "No Account",
          value: data.overview.no_available_account ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Active Accounts",
          value: data.overview.active_accounts,
          icon: Users,
          tone: "text-emerald-700",
        },
        {
          label: "Cooling Accounts",
          value: data.overview.cooling_accounts ?? 0,
          icon: HeartPulse,
          tone: "text-amber",
        },
        {
          label: "High Risk",
          value: data.overview.high_risk_accounts ?? 0,
          icon: ShieldCheck,
          tone: "text-red-700",
        },
        {
          label: "Active TGE",
          value: data.overview.tge_profiles_active ?? 0,
          icon: Workflow,
          tone: "text-blue-700",
        },
        {
          label: "No TGE Binding",
          value: data.overview.accounts_without_tge ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Execution Received",
          value: data.overview.execution_received ?? 0,
          icon: Play,
          tone: "text-cyan",
        },
        {
          label: "Execution Queue",
          value: data.overview.execution_queue ?? 0,
          icon: FileClock,
          tone: "text-amber",
        },
        {
          label: "Workers Online",
          value: data.overview.execution_workers ?? 0,
          icon: Bot,
          tone: "text-teal",
        },
        {
          label: "Execution Running",
          value: data.overview.execution_running ?? 0,
          icon: Activity,
          tone: "text-blue-700",
        },
        {
          label: "Execution Success",
          value: data.overview.execution_success ?? 0,
          icon: CheckCircle2,
          tone: "text-emerald-700",
        },
        {
          label: "Running Browser",
          value: data.overview.browser_running ?? 0,
          icon: Workflow,
          tone: "text-blue-700",
        },
        {
          label: "Running Tabs",
          value: data.overview.browser_tabs_open ?? 0,
          icon: FileClock,
          tone: "text-cyan",
        },
        {
          label: "Dead Sessions",
          value: data.overview.browser_dead_sessions ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Env Ready",
          value: data.overview.execution_environment_ready ?? 0,
          icon: CheckCircle2,
          tone: "text-emerald-700",
        },
        {
          label: "TGE Running",
          value: data.overview.tge_running ?? 0,
          icon: Workflow,
          tone: "text-blue-700",
        },
        {
          label: "Data Sources",
          value: data.overview.data_sources,
          icon: Database,
          tone: "text-blue-700",
        },
        {
          label: "Today's Browse",
          value: data.overview.today_browse ?? 0,
          icon: Activity,
          tone: "text-cyan",
        },
        {
          label: "Today's Like",
          value: data.overview.today_like ?? 0,
          icon: HeartPulse,
          tone: "text-red-700",
        },
        {
          label: "Profile Visit",
          value: data.overview.today_profile_visit ?? 0,
          icon: Users,
          tone: "text-teal",
        },
        {
          label: "Warm-up Tasks",
          value: data.overview.warmup_tasks ?? 0,
          icon: Workflow,
          tone: "text-amber",
        },
        {
          label: "Engage Success",
          value: data.overview.engagement_success_rate ?? 0,
          icon: CheckCircle2,
          tone: "text-emerald-700",
        },
        {
          label: "LLM Health",
          value: data.overview.llm_provider_health ?? "—",
          icon: BrainCircuit,
          tone: "text-teal",
        },
        {
          label: "Fallback Rate",
          value: `${data.overview.fallback_rate ?? 0}%`,
          icon: RefreshCw,
          tone: "text-amber",
        },
        {
          label: "AI Latency",
          value: `${data.overview.average_latency_ms ?? 0}ms`,
          icon: Activity,
          tone: "text-cyan",
        },
        {
          label: "AI Cost",
          value: `$${data.overview.ai_cost_today ?? 0}`,
          icon: Database,
          tone: "text-blue-700",
        },
        {
          label: "Pipeline Imported",
          value: data.overview.pipeline_today_imported ?? 0,
          icon: Database,
          tone: "text-cyan",
        },
        {
          label: "Pipeline AI",
          value: data.overview.pipeline_today_ai ?? 0,
          icon: BrainCircuit,
          tone: "text-teal",
        },
        {
          label: "Pipeline Approved",
          value: data.overview.pipeline_approved ?? 0,
          icon: CheckCircle2,
          tone: "text-emerald-700",
        },
        {
          label: "Pipeline Scheduled",
          value: data.overview.pipeline_scheduled ?? 0,
          icon: CalendarClock,
          tone: "text-amber",
        },
        {
          label: "Pipeline Success",
          value: `${data.overview.pipeline_success_rate ?? 0}%`,
          icon: Activity,
          tone: "text-blue-700",
        },
        {
          label: "Active Platforms",
          value: data.overview.active_platforms ?? 0,
          icon: SlidersHorizontal,
          tone: "text-teal",
        },
        {
          label: "Healthy Platforms",
          value: data.overview.healthy_platforms ?? 0,
          icon: CheckCircle2,
          tone: "text-emerald-700",
        },
        {
          label: "Failed Adapters",
          value: data.overview.failed_adapters ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Worker Capacity",
          value: `${data.overview.worker_running_tasks ?? 0}/${data.overview.worker_capacity ?? 0}`,
          icon: Bot,
          tone: "text-teal",
        },
        {
          label: "Automation Queue",
          value: data.overview.automation_queue_length ?? 0,
          icon: FileClock,
          tone: "text-amber",
        },
        {
          label: "Retry Pending",
          value: data.overview.automation_retry_pending ?? 0,
          icon: RefreshCw,
          tone: "text-blue-700",
        },
        {
          label: "Open Alerts",
          value: data.overview.automation_alerts ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Recommendations",
          value: data.overview.intelligence_recommendations ?? 0,
          icon: Sparkles,
          tone: "text-teal",
        },
        {
          label: "Reply Score",
          value: data.overview.reply_average_score ?? 0,
          icon: BrainCircuit,
          tone: "text-blue-700",
        },
        {
          label: "Content Score",
          value: data.overview.content_average_score ?? 0,
          icon: ChartNoAxesCombined,
          tone: "text-emerald-700",
        },
        {
          label: "Best Time Windows",
          value: data.overview.best_time_windows ?? 0,
          icon: CalendarClock,
          tone: "text-amber",
        },
        {
          label: "Submission Ready",
          value: data.overview.submission_ready ?? 0,
          icon: CheckCircle2,
          tone: "text-emerald-700",
        },
        {
          label: "Waiting Manual",
          value: data.overview.submission_waiting_manual ?? 0,
          icon: FileClock,
          tone: "text-amber",
        },
        {
          label: "Submitting",
          value: data.overview.submission_submitting ?? 0,
          icon: Play,
          tone: "text-blue-700",
        },
        {
          label: "Verified Submit",
          value: data.overview.submission_verified ?? 0,
          icon: ShieldCheck,
          tone: "text-emerald-700",
        },
        {
          label: "Submit Failed",
          value: data.overview.submission_failed ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Manual Required",
          value: data.overview.submission_manual_required ?? 0,
          icon: Users,
          tone: "text-amber",
        },
        {
          label: "Auto Completed",
          value: data.overview.auto_assisted_completed ?? 0,
          icon: ShieldCheck,
          tone: "text-emerald-700",
        },
        {
          label: "Manual Review",
          value: data.overview.auto_assisted_manual_review ?? 0,
          icon: CircleAlert,
          tone: "text-amber",
        },
        {
          label: "Reddit Waiting",
          value: data.overview.reddit_waiting_manual ?? 0,
          icon: FileClock,
          tone: "text-amber",
        },
        {
          label: "X Waiting",
          value: data.overview.x_waiting_manual ?? 0,
          icon: FileClock,
          tone: "text-blue-700",
        },
        {
          label: "Reddit Failed",
          value: data.overview.reddit_failed ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "X Failed",
          value: data.overview.x_failed ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Manual Confirmed",
          value: data.overview.manual_confirmed_today ?? 0,
          icon: ShieldCheck,
          tone: "text-emerald-700",
        },
        {
          label: "Retry Pending",
          value: data.overview.retry_pending ?? 0,
          icon: RefreshCw,
          tone: "text-blue-700",
        },
        {
          label: "Template Generated",
          value: data.overview.template_generated_today ?? 0,
          icon: Sparkles,
          tone: "text-teal",
        },
        {
          label: "Template Verified",
          value: data.overview.template_verified_today ?? 0,
          icon: ShieldCheck,
          tone: "text-emerald-700",
        },
        {
          label: "Template Success",
          value: `${data.overview.template_success_rate ?? 0}%`,
          icon: ChartNoAxesCombined,
          tone: "text-blue-700",
        },
        {
          label: "High Risk Templates",
          value: data.overview.high_risk_template_usage ?? 0,
          icon: CircleAlert,
          tone: "text-red-700",
        },
        {
          label: "Template Platforms",
          value: data.overview.template_platforms ?? 0,
          icon: SlidersHorizontal,
          tone: "text-cyan",
        },
      ]
    : [];

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-7">
        {data?.overview.emergency_stop_active && (
          <div className="panel border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
            Emergency Stop is active. AUTO_ASSISTED tasks have been moved back to manual review.
          </div>
        )}
        <Section
          title="Overview"
          action={
            <button className="icon-button" title="刷新" onClick={reload}>
              <RefreshCw className="h-4 w-4" />
            </button>
          }
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
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
                    <p className="text-xs text-gray-500">
                      {platform.adapter ?? platform.slug}
                      {platform.version ? ` · ${platform.version}` : ""}
                    </p>
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
  const { data, error, loading, reload } = useApiData<DataSourceItem[]>("/data-sources");
  const platforms = useApiData<PlatformOption[]>("/data-sources/platforms");
  const mappings = useApiData<RecordItem[]>("/actor-mappings");
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("Apify Source");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [actorId, setActorId] = useState("");
  const [actorName, setActorName] = useState("");
  const [platformId, setPlatformId] = useState("1");
  const [remark, setRemark] = useState("");
  const [inputJson, setInputJson] = useState("{}");
  const [maxItems, setMaxItems] = useState("100");
  const [enabled, setEnabled] = useState(true);
  const [token, setToken] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [logs, setLogs] = useState<RecordItem[]>([]);
  const [logSource, setLogSource] = useState("");
  const [mappingForm, setMappingForm] = useState<Record<string, unknown>>({
    data_source_id: "",
    actor_id: "demo/reddit-discovery",
    platform: "reddit",
    mapping_name: "Default Reddit Mapping",
    title_path: "title",
    content_path: "selftext",
    url_path: "url",
    author_path: "author",
    author_id_path: "author_id",
    community_path: "subreddit",
    source_post_id_path: "id",
    published_at_path: "created_utc",
    score_path: "score",
    comment_count_path: "num_comments",
    media_path: "media",
    language_path: "language",
    enabled: true,
    remark: "",
  });
  const [mappingRawJson, setMappingRawJson] = useState("{\n  \"id\": \"abc123\",\n  \"title\": \"Example post\",\n  \"selftext\": \"Post body\",\n  \"url\": \"https://example.com/post\",\n  \"author\": \"demo_user\",\n  \"subreddit\": \"SaaS\"\n}");
  const [mappingPreview, setMappingPreview] = useState<RecordItem | null>(null);

  function resetForm() {
    setEditingId(null);
    setName("Apify Source");
    setActorId("");
    setActorName("");
    setPlatformId(String(platforms.data?.[0]?.id ?? 1));
    setRemark("");
    setInputJson("{}");
    setMaxItems("100");
    setEnabled(true);
    setToken("");
  }

  function startCreate() {
    resetForm();
    setFeedback("");
    setShowForm(true);
  }

  function startEdit(source: DataSourceItem) {
    setEditingId(source.id);
    setName(source.name);
    setActorId(source.config.actor_id ?? "");
    setActorName(source.config.actor_name ?? "");
    setPlatformId(String(source.platform_id ?? platforms.data?.[0]?.id ?? 1));
    setRemark(source.config.remark ?? "");
    setInputJson(JSON.stringify(source.config.input_json ?? {}, null, 2));
    setMaxItems(String(source.config.max_items ?? 100));
    setEnabled(source.enabled);
    setToken("");
    setFeedback("");
    setShowForm(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFeedback("");
    try {
      const parsedInput = JSON.parse(inputJson) as unknown;
      if (!parsedInput || Array.isArray(parsedInput) || typeof parsedInput !== "object") {
        throw new Error("Input JSON 必须是 JSON Object。");
      }
      await apiRequest(
        editingId ? `/data-sources/${editingId}` : "/data-sources",
        {
        method: editingId ? "PUT" : "POST",
        body: JSON.stringify({
          name,
          source_type: "APIFY",
          platform_id: Number(platformId),
          adapter_key: "apify",
          apify_token: token || undefined,
          enabled,
          config: {
            actor_id: actorId,
            actor_name: actorName,
            remark,
            input_json: parsedInput,
            max_items: Number(maxItems),
          },
        }),
      });
      setFeedback(editingId ? "数据源已更新。" : "Apify 数据源已创建。");
      setShowForm(false);
      resetForm();
      await reload();
    } catch (reason) {
      setFeedback(
        reason instanceof SyntaxError
          ? "Input JSON 格式不正确。"
          : reason instanceof Error
            ? reason.message
            : "保存失败",
      );
    }
  }

  async function sourceAction(
    source: DataSourceItem,
    action: "test" | "run" | "toggle" | "logs",
  ) {
    setBusyId(source.id);
    setFeedback("");
    try {
      if (action === "logs") {
        setLogs(await apiGet<RecordItem[]>(`/data-sources/${source.id}/logs`));
        setLogSource(source.name);
      } else if (action === "toggle") {
        await apiRequest(`/data-sources/${source.id}`, {
          method: "PUT",
          body: JSON.stringify({ enabled: !source.enabled }),
        });
        setFeedback(source.enabled ? "数据源已停用。" : "数据源已启用。");
        await reload();
      } else {
        const result = await apiRequest<RecordItem>(
          `/data-sources/${source.id}/${action}`,
          { method: "POST" },
        );
        if (action === "test") {
          setFeedback(`连接成功：${String(result.actor_name ?? result.actor_id ?? "")}`);
        } else {
          const runStatus = String(result.status ?? "UNKNOWN");
          setFeedback(
            runStatus === "SUCCEEDED"
              ? `采集完成：新增 ${String(result.inserted_count ?? 0)}，重复 ${String(result.duplicate_count ?? 0)}。`
              : `采集失败：${String(result.error_message ?? "请查看运行日志")}`,
          );
        }
        await reload();
      }
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "操作失败");
      await reload();
    } finally {
      setBusyId(null);
    }
  }

  function updateMappingField(key: string, value: unknown) {
    setMappingForm((current) => ({ ...current, [key]: value }));
  }

  async function createMapping() {
    try {
      await apiRequest("/actor-mappings", {
        method: "POST",
        body: JSON.stringify({
          ...mappingForm,
          data_source_id: mappingForm.data_source_id ? Number(mappingForm.data_source_id) : null,
        }),
      });
      setFeedback("Actor Mapping 已创建。");
      await mappings.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "创建 Mapping 失败");
    }
  }

  async function testMapping() {
    try {
      const raw = JSON.parse(mappingRawJson) as Record<string, unknown>;
      const result = await apiRequest<RecordItem>("/actor-mappings/test", {
        method: "POST",
        body: JSON.stringify({ mapping: mappingForm, raw_item_json: raw }),
      });
      setMappingPreview(result);
      setFeedback("Mapping Preview 已生成。");
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "测试 Mapping 失败");
    }
  }

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        {showForm && (
          <form className="panel grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-4" onSubmit={submit}>
            <label className="text-xs font-semibold text-gray-600">
              配置名称
              <input className="field mt-2" value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Actor ID
              <input className="field mt-2" value={actorId} onChange={(e) => setActorId(e.target.value)} placeholder="owner/actor-name" required />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Actor Name
              <input className="field mt-2" value={actorName} onChange={(e) => setActorName(e.target.value)} placeholder="便于识别的名称" />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Platform
              <select className="field mt-2" value={platformId} onChange={(e) => setPlatformId(e.target.value)}>
                {(platforms.data ?? []).map((platform) => (
                  <option key={platform.id} value={platform.id}>{platform.name}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold text-gray-600">
              APIFY_TOKEN
              <input className="field mt-2" type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={editingId ? "留空则保持现有 Token" : "可留空并使用 .env"} autoComplete="new-password" />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Max Items
              <input className="field mt-2" type="number" min="1" max="1000" value={maxItems} onChange={(e) => setMaxItems(e.target.value)} required />
            </label>
            <label className="text-xs font-semibold text-gray-600 md:col-span-2">
              Remark
              <input className="field mt-2" value={remark} onChange={(e) => setRemark(e.target.value)} placeholder="用途、Owner 或注意事项" />
            </label>
            <label className="text-xs font-semibold text-gray-600 md:col-span-2 xl:col-span-4">
              Actor Input JSON
              <textarea className="field mt-2 min-h-36 font-mono text-xs" value={inputJson} onChange={(e) => setInputJson(e.target.value)} spellCheck={false} />
            </label>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700 md:col-span-2 xl:col-span-4">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              Enabled
            </label>
            <div className="flex gap-2 md:col-span-2 xl:col-span-4">
              <button className="button" type="submit"><CheckCircle2 className="h-4 w-4" />{editingId ? "保存修改" : "创建数据源"}</button>
              <button className="button-secondary" type="button" onClick={() => setShowForm(false)}>取消</button>
            </div>
          </form>
        )}
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section
          title="Configured Sources"
          action={
            <button className="button" onClick={startCreate}>
              <Database className="h-4 w-4" />
              新建数据源
            </button>
          }
        >
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1120px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Source", "Platform", "Actor", "Token", "Status", "Last Run", "Result", "Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>
                {(data ?? []).map((source) => {
                  const latest = source.latest_log ?? {};
                  return (
                    <tr key={source.id} className="border-b border-line last:border-0">
                      <td className="px-4 py-3"><p className="font-semibold">{source.name}</p><p className="mt-1 max-w-52 truncate text-xs text-gray-500">{source.config.remark || "—"}</p></td>
                      <td className="px-4 py-3 text-gray-600">{source.platform || "—"}</td>
                      <td className="px-4 py-3"><p className="font-medium">{source.config.actor_name || "—"}</p><p className="text-xs text-gray-500">{source.config.actor_id || "—"}</p></td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">{source.config.token_masked || (source.config.token_configured ? "********" : "Not set")}</td>
                      <td className="px-4 py-3"><StatusBadge value={source.enabled ? source.status : "DISABLED"} /></td>
                      <td className="px-4 py-3 text-xs text-gray-500">{source.last_run_at ? new Date(String(source.last_run_at)).toLocaleString() : "Never"}</td>
                      <td className="px-4 py-3 text-xs text-gray-600">{latest.status ? `${String(latest.status)} · +${String(latest.inserted_count ?? 0)} / dup ${String(latest.duplicate_count ?? 0)}` : "—"}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <button className="icon-button" title="编辑" onClick={() => startEdit(source)}><Pencil className="h-4 w-4" /></button>
                          <button className="button-secondary" disabled={busyId === source.id} onClick={() => void sourceAction(source, "test")}>测试</button>
                          <button className="button" disabled={busyId === source.id || !source.enabled} onClick={() => void sourceAction(source, "run")}><Play className="h-4 w-4" />运行</button>
                          <button className="button-secondary" disabled={busyId === source.id} onClick={() => void sourceAction(source, "toggle")}>{source.enabled ? "停用" : "启用"}</button>
                          <button className="icon-button" title="运行日志" onClick={() => void sourceAction(source, "logs")}><FileClock className="h-4 w-4" /></button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Section>
        {logSource && (
          <Section title={`${logSource} · Recent Runs`} action={<button className="button-secondary" onClick={() => setLogSource("")}>关闭</button>}>
            <DataTable columns={[
              { key: "status", label: "Status" },
              { key: "started_at", label: "Started" },
              { key: "total_items", label: "Total" },
              { key: "inserted_count", label: "Inserted" },
              { key: "duplicate_count", label: "Duplicate" },
              { key: "error_count", label: "Errors" },
              { key: "error_message", label: "Message" },
            ]} rows={logs} />
          </Section>
        )}
        <Section title="Actor Mapping" action={<div className="flex gap-2"><button className="button-secondary" onClick={testMapping}>测试 Mapping</button><button className="button" onClick={createMapping}>保存 Mapping</button></div>}>
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="panel grid gap-3 p-4 md:grid-cols-2">
              <select className="field" value={String(mappingForm.data_source_id ?? "")} onChange={(e) => updateMappingField("data_source_id", e.target.value)}>
                <option value="">不绑定数据源</option>
                {(data ?? []).map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
              </select>
              <input className="field" value={String(mappingForm.actor_id ?? "")} onChange={(e) => updateMappingField("actor_id", e.target.value)} placeholder="actor_id" />
              <input className="field" value={String(mappingForm.platform ?? "")} onChange={(e) => updateMappingField("platform", e.target.value)} placeholder="platform" />
              <input className="field" value={String(mappingForm.mapping_name ?? "")} onChange={(e) => updateMappingField("mapping_name", e.target.value)} placeholder="mapping name" />
              {["title_path", "content_path", "url_path", "author_path", "community_path", "source_post_id_path", "published_at_path", "score_path", "comment_count_path"].map((key) => (
                <input key={key} className="field" value={String(mappingForm[key] ?? "")} onChange={(e) => updateMappingField(key, e.target.value)} placeholder={key} />
              ))}
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={Boolean(mappingForm.enabled)} onChange={(e) => updateMappingField("enabled", e.target.checked)} />Enabled</label>
            </div>
            <div className="panel p-4">
              <p className="text-xs font-semibold uppercase text-gray-500">Raw Item JSON</p>
              <textarea className="field mt-2 min-h-40 font-mono text-xs" value={mappingRawJson} onChange={(e) => setMappingRawJson(e.target.value)} />
              <pre className="mt-3 max-h-56 overflow-auto rounded bg-gray-50 p-3 text-xs text-gray-600">{JSON.stringify(mappingPreview ?? {}, null, 2)}</pre>
            </div>
          </div>
          <div className="panel mt-4 overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["name", "platform", "actor", "title", "url", "enabled"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(mappings.data ?? []).map((mapping) => (
                <tr key={String(mapping.id)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">{String(mapping.mapping_name)}</td>
                  <td className="px-4 py-3 uppercase text-teal">{String(mapping.platform)}</td>
                  <td className="px-4 py-3 font-mono text-xs">{String(mapping.actor_id)}</td>
                  <td className="px-4 py-3 font-mono text-xs">{String(mapping.title_path ?? "")}</td>
                  <td className="px-4 py-3 font-mono text-xs">{String(mapping.url_path ?? "")}</td>
                  <td className="px-4 py-3">{String(mapping.enabled)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
      </div>
    </StateView>
  );
}

function PostPoolPage() {
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [keyword, setKeyword] = useState("");
  const [community, setCommunity] = useState("");
  const [page, setPage] = useState(1);
  const [selectedPostIds, setSelectedPostIds] = useState<number[]>([]);
  const [feedback, setFeedback] = useState("");
  const [busyPostId, setBusyPostId] = useState<number | null>(null);
  const [rawPost, setRawPost] = useState<RecordItem | null>(null);
  const [timeline, setTimeline] = useState<RecordItem[] | null>(null);
  const sources = useApiData<DataSourceItem[]>("/data-sources");
  const query = new URLSearchParams();
  if (platform) query.set("platform", platform);
  if (status) query.set("status", status);
  if (sourceId) query.set("source_id", sourceId);
  if (keyword) query.set("keyword", keyword);
  if (community) query.set("community", community);
  query.set("page", String(page));
  query.set("page_size", "20");
  const { data, error, loading, reload } = useApiData<PagedRecords>(
    `/posts${query.size ? `?${query.toString()}` : ""}`,
  );
  const posts = listFromResponse(data);
  const pagination = data?.pagination;

  async function runPostAction(post: RecordItem, action: "analyze" | "reply" | "workspace") {
    const postId = Number(post.id);
    setBusyPostId(postId);
    setFeedback("");
    try {
      if (action === "reply" || action === "workspace") {
        await apiRequest(`/pipeline/post/${postId}`, {
          method: "POST",
          body: JSON.stringify({
            action: "RUN",
            auto_approve: false,
            send_to_scheduler: false,
          }),
        });
        setFeedback("回复草稿已生成，可到 AI Workspace 审核。");
      } else {
        await apiRequest(`/pipeline/post/${postId}`, {
          method: "POST",
          body: JSON.stringify({ action: "ANALYZE" }),
        });
        setFeedback("帖子已完成 AI 分析。");
      }
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "AI 操作失败");
    } finally {
      setBusyPostId(null);
    }
  }

  async function bulkAddToScheduler() {
    setFeedback("");
    try {
      const result = await runBatch("SEND_TO_SCHEDULER");
      setFeedback(`批量加入 Scheduler 完成：${String(result.scheduled ?? 0)} 条。`);
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "批量加入失败");
    }
  }

  async function runBatch(action: string) {
    const postIds = selectedPostIds.length ? selectedPostIds : posts.map((post) => Number(post.id)).filter(Boolean);
    const result = await apiRequest<RecordItem>("/pipeline/batch", {
      method: "POST",
      body: JSON.stringify({ post_ids: postIds, action, priority: "MEDIUM" }),
    });
    await reload();
    setSelectedPostIds([]);
    return result;
  }

  async function handleBatch(action: string) {
    setFeedback("");
    try {
      const result = await runBatch(action);
      setFeedback(`${action} 完成：处理 ${String(result.processed ?? 0)} 条，错误 ${String((result.errors as unknown[])?.length ?? 0)} 条。`);
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "批量操作失败");
    }
  }

  async function showTimeline(post: RecordItem) {
    try {
      const rows = await apiRequest<RecordItem[]>(`/posts/${String(post.id)}/timeline`);
      setTimeline(rows);
      setFeedback(`已加载 Timeline：${String(post.title ?? "")}`);
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Timeline 加载失败");
    }
  }

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-4">
        <div className="panel flex flex-wrap items-end gap-3 p-4">
          <SlidersHorizontal className="mb-2 h-5 w-5 text-gray-500" />
          <label className="text-xs font-semibold text-gray-600">Platform<select className="field mt-2 min-w-36" value={platform} onChange={(e) => setPlatform(e.target.value)}><option value="">All</option>{Array.from(new Set((sources.data ?? []).map((item) => item.platform).filter(Boolean))).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label className="text-xs font-semibold text-gray-600">Source<select className="field mt-2 min-w-48" value={sourceId} onChange={(e) => setSourceId(e.target.value)}><option value="">All</option>{(sources.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className="text-xs font-semibold text-gray-600">Keyword<input className="field mt-2 min-w-44" value={keyword} onChange={(e) => { setKeyword(e.target.value); setPage(1); }} placeholder="title / author" /></label>
          <label className="text-xs font-semibold text-gray-600">Community<input className="field mt-2 min-w-40" value={community} onChange={(e) => { setCommunity(e.target.value); setPage(1); }} placeholder="ADHD" /></label>
	          <label className="text-xs font-semibold text-gray-600">Status<select className="field mt-2 min-w-44" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">All</option><option value="NEW">NEW</option><option value="NORMALIZED">NORMALIZED</option><option value="READY_FOR_AI">READY_FOR_AI</option><option value="ANALYZING">ANALYZING</option><option value="AI_COMPLETED">AI_COMPLETED</option><option value="WAITING_REVIEW">WAITING_REVIEW</option><option value="APPROVED">APPROVED</option><option value="SCHEDULED">SCHEDULED</option><option value="ARCHIVED">ARCHIVED</option><option value="INCOMPLETE">INCOMPLETE</option></select></label>
          <button className="icon-button mb-0.5" title="刷新" onClick={reload}><RefreshCw className="h-4 w-4" /></button>
          <button className="button-secondary mb-0.5" onClick={() => void handleBatch("ANALYZE")}><BrainCircuit className="h-4 w-4" />Analyze</button>
          <button className="button-secondary mb-0.5" onClick={() => void handleBatch("APPROVE")}><CheckCircle2 className="h-4 w-4" />Approve</button>
          <button className="button-secondary mb-0.5" onClick={() => void handleBatch("REJECT")}>Reject</button>
          <button className="button-secondary mb-0.5" onClick={() => void handleBatch("ARCHIVE")}>Archive</button>
          <button className="button mb-0.5" onClick={bulkAddToScheduler}><CalendarClock className="h-4 w-4" />批量加入 Scheduler</button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section title={`Unified Post Pool · ${pagination?.total ?? posts.length}`}>
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1480px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
	                {["Select", "Platform", "Status", "Title", "Author", "Community", "Score", "Comments", "Source", "Actor", "Mapping", "URL", "Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{posts.map((post, index) => (
                <tr key={String(post.uuid ?? index)} className="border-b border-line last:border-0">
                    <td className="px-4 py-3"><input type="checkbox" checked={selectedPostIds.includes(Number(post.id))} onChange={(event) => setSelectedPostIds((current) => event.target.checked ? [...current, Number(post.id)] : current.filter((id) => id !== Number(post.id)))} /></td>
	                  <td className="px-4 py-3 font-semibold uppercase text-teal">{String(post.platform ?? "—")}</td>
	                  <td className="px-4 py-3"><StatusBadge value={post.status ?? "—"} /></td>
	                  <td className="max-w-sm px-4 py-3"><p className="line-clamp-2 font-medium">{String(post.title || "(Untitled)")}</p></td>
	                  <td className="px-4 py-3 text-gray-600">{String(post.author ?? "—")}</td>
	                  <td className="px-4 py-3 text-gray-600">{String(post.community ?? "—")}</td>
	                  <td className="px-4 py-3 text-gray-600">{String(post.score ?? 0)}</td>
	                  <td className="px-4 py-3 text-gray-600">{String(post.comment_count ?? 0)}</td>
	                  <td className="px-4 py-3 text-gray-600">{String(post.source_name ?? post.source ?? "Seed / Manual")}</td>
	                  <td className="px-4 py-3 text-gray-600">{String(post.actor_name ?? "—")}</td>
	                  <td className="px-4 py-3 text-gray-600">{String(post.mapping_name ?? "fallback")}</td>
	                  <td className="px-4 py-3">{post.url ? <a className="inline-flex items-center gap-1 text-cyan hover:underline" href={String(post.url)} target="_blank" rel="noreferrer">Open<ExternalLink className="h-3.5 w-3.5" /></a> : "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button className="button-secondary" disabled={busyPostId === post.id} onClick={() => void runPostAction(post, "analyze")}>Analyze</button>
	                      <button className="button-secondary" disabled={busyPostId === post.id} onClick={() => void runPostAction(post, "reply")}>Generate Reply</button>
	                      <button className="button" disabled={busyPostId === post.id} onClick={() => void runPostAction(post, "workspace")}><BrainCircuit className="h-4 w-4" />Send</button>
                        <button className="button-secondary" onClick={() => void showTimeline(post)}>Timeline</button>
	                      <button className="button-secondary" onClick={() => setRawPost(post)}>Raw JSON</button>
	                    </div>
	                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
	        </Section>
        {pagination && (
          <div className="panel flex items-center justify-between p-3 text-sm text-gray-600">
            <span>Page {pagination.page} / {pagination.pages || 1} · {pagination.total} records</span>
            <div className="flex gap-2">
              <button className="button-secondary" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button>
              <button className="button-secondary" disabled={page >= (pagination.pages || 1)} onClick={() => setPage((current) => current + 1)}>Next</button>
            </div>
          </div>
        )}
	        {rawPost && (
	          <Section title="Raw JSON Viewer" action={<button className="button-secondary" onClick={() => setRawPost(null)}>关闭</button>}>
	            <pre className="panel max-h-[520px] overflow-auto p-4 text-xs text-gray-600">{JSON.stringify(rawPost.raw_json ?? {}, null, 2)}</pre>
	          </Section>
	        )}
        {timeline && (
          <Section title="Post Timeline" action={<button className="button-secondary" onClick={() => setTimeline(null)}>关闭</button>}>
            <div className="panel overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">{["Time", "Event", "Old", "New", "Actor"].map((label) => <th key={label} className="px-4 py-3">{label}</th>)}</tr></thead>
                <tbody>{timeline.map((item) => (
                  <tr key={String(item.uuid)} className="border-b border-line last:border-0">
                    <td className="px-4 py-3">{String(item.created_at ?? "—")}</td>
                    <td className="px-4 py-3 font-semibold">{String(item.event_name ?? "—")}</td>
                    <td className="px-4 py-3">{String(item.old_status ?? "—")}</td>
                    <td className="px-4 py-3"><StatusBadge value={item.new_status} /></td>
                    <td className="px-4 py-3">{String(item.actor ?? "—")}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </Section>
        )}
	      </div>
    </StateView>
  );
}

function AIWorkspacePage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/ai/tasks");
  const posts = useApiData<PagedRecords>("/posts?page_size=100");
  const replyTemplates = useApiData<RecordItem[]>("/reply-templates");
  const [postId, setPostId] = useState("1");
  const [strategy, setStrategy] = useState("PURE_HELP");
  const [tone, setTone] = useState("supportive");
  const [templateId, setTemplateId] = useState("");
  const [feedback, setFeedback] = useState("");
  const [draftEdits, setDraftEdits] = useState<Record<string, string>>({});
  const [promptPreview, setPromptPreview] = useState<RecordItem | null>(null);
  const [selectedTaskIds, setSelectedTaskIds] = useState<number[]>([]);
  const postOptions = listFromResponse(posts.data);

  async function analyzeSelected() {
    try {
      await apiRequest(`/ai/tasks/${Number(postId)}/analyze`, { method: "POST" });
      setFeedback("AI 分析已完成。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "分析失败");
    }
  }

  async function generateSelected() {
    try {
      await apiRequest(`/ai/tasks/${Number(postId)}/generate-reply`, {
        method: "POST",
        body: JSON.stringify({
          strategy,
          tone,
          variables: {},
          reply_template_id: templateId ? Number(templateId) : undefined,
        }),
      });
      setFeedback("回复草稿已生成，等待人工审核。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "生成失败");
    }
  }

  async function regenerate(task: RecordItem) {
    try {
      await apiRequest(`/ai/tasks/${String(task.id)}/regenerate`, {
        method: "POST",
        body: JSON.stringify({
          strategy: String(task.strategy ?? strategy),
          tone,
          variables: {},
          reply_template_id: templateId ? Number(templateId) : (task.reply_task as RecordItem | undefined)?.reply_template_id,
        }),
      });
      setFeedback("已重新生成回复草稿。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "重新生成失败");
    }
  }

  async function saveReply(reply: RecordItem) {
    try {
      const replyId = String(reply.id);
      await apiRequest(`/ai/replies/${replyId}`, {
        method: "PUT",
        body: JSON.stringify({ content: draftEdits[replyId] ?? String(reply.content ?? "") }),
      });
      setFeedback("回复内容已保存为人工编辑版本。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  async function approve(taskId: unknown) {
    try {
      await apiRequest(`/ai/tasks/${String(taskId)}/approve`, {
        method: "POST",
        body: JSON.stringify({ reply_template_id: templateId ? Number(templateId) : undefined }),
      });
      setFeedback("任务已批准，可进入 Scheduler。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "批准失败");
    }
  }

  async function reject(taskId: unknown) {
    try {
      await apiRequest(`/ai/tasks/${String(taskId)}/reject`, { method: "POST" });
      setFeedback("任务已拒绝。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "拒绝失败");
    }
  }

  async function addToScheduler(taskId: unknown) {
    try {
      await apiRequest("/scheduler/tasks/from-approved", {
        method: "POST",
        body: JSON.stringify({ ai_task_id: Number(taskId), priority: "MEDIUM" }),
      });
      setFeedback("已加入 Scheduler 队列。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "加入 Scheduler 失败");
    }
  }

  async function previewPromptForTask(task: RecordItem) {
    try {
      const result = await apiRequest<RecordItem>(`/ai/tasks/${String(task.id)}/preview-prompt`, {
        method: "POST",
        body: JSON.stringify({
          strategy: String(task.strategy ?? strategy),
          tone,
          variables: {},
          reply_template_id: templateId ? Number(templateId) : (task.reply_task as RecordItem | undefined)?.reply_template_id,
        }),
      });
      setPromptPreview(result);
      setFeedback("Prompt Preview 已生成。");
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Prompt Preview 失败");
    }
  }

  async function batchAI(action: string) {
    setFeedback("");
    try {
      const result = await apiRequest<RecordItem>("/ai/tasks/batch", {
        method: "POST",
        body: JSON.stringify({
          task_ids: selectedTaskIds,
          action,
          strategy,
          tone,
        }),
      });
      setFeedback(`${action} 批量完成：处理 ${String(result.processed ?? 0)} 条。`);
      setSelectedTaskIds([]);
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "AI 批量操作失败");
    }
  }

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        <div className="panel grid gap-3 p-4 lg:grid-cols-[1fr_170px_170px_220px_auto_auto]">
          <label className="min-w-64 flex-1 text-xs font-semibold text-gray-600">
            选择帖子
            <select className="field mt-2" value={postId} onChange={(e) => setPostId(e.target.value)}>
              {postOptions.map((post) => (
                <option key={String(post.id)} value={String(post.id)}>{String(post.title)}</option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            Strategy
            <select className="field mt-2" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              <option value="PURE_HELP">Pure Help</option>
              <option value="EXPERIENCE_SHARE">Experience</option>
              <option value="EDUCATION">Education</option>
              <option value="WARM_UP">Warm-up</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            Tone
            <select className="field mt-2" value={tone} onChange={(e) => setTone(e.target.value)}>
              <option value="supportive">Supportive</option>
              <option value="concise">Concise</option>
              <option value="professional">Professional</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            回复模板
            <select className="field mt-2" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
              <option value="">系统推荐模板</option>
              {(replyTemplates.data ?? []).map((template) => (
                <option key={String(template.id)} value={String(template.id)}>
                  {String(template.name_cn)} · {String(template.risk_level)}
                </option>
              ))}
            </select>
          </label>
          <button className="button-secondary self-end" onClick={analyzeSelected}><BrainCircuit className="h-4 w-4" />Analyze</button>
          <button className="button self-end" onClick={generateSelected}><Sparkles className="h-4 w-4" />Generate</button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <div className="panel flex flex-wrap items-center gap-2 p-3">
          <span className="text-xs font-semibold uppercase text-gray-500">Batch Review</span>
          <button className="button-secondary" onClick={() => void batchAI("GENERATE")}><Sparkles className="h-4 w-4" />批量生成</button>
          <button className="button-secondary" onClick={() => void batchAI("APPROVE")}><CheckCircle2 className="h-4 w-4" />批量批准</button>
          <button className="button-secondary" onClick={() => void batchAI("REJECT")}>批量拒绝</button>
          <span className="text-xs text-gray-500">已选 {selectedTaskIds.length} 条</span>
        </div>
        <Section title="Review Queue">
          <div className="space-y-3">
            {(data ?? []).map((task) => (
              <div key={String(task.uuid)} className="panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <input className="mt-1" type="checkbox" checked={selectedTaskIds.includes(Number(task.id))} onChange={(event) => setSelectedTaskIds((current) => event.target.checked ? [...current, Number(task.id)] : current.filter((id) => id !== Number(task.id)))} />
                    <div>
                    <p className="font-semibold">{String(task.strategy)} · {String(task.model)}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {String(task.provider)} · Commercial {String(task.commercial_score)} · Risk {String(task.risk_score)}
                    </p>
                    {Boolean(task.reply_task || task.reply_template) && (
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        <span className="rounded bg-gray-100 px-2 py-1 text-gray-700">
                          模板：{String((task.reply_template as RecordItem | undefined)?.name_cn ?? (task.reply_task as RecordItem | undefined)?.funnel_intent ?? "系统推荐")}
                        </span>
                        <span className="rounded bg-gray-100 px-2 py-1 text-gray-700">
                          意图：{String((task.reply_task as RecordItem | undefined)?.funnel_intent ?? "—")}
                        </span>
                        <span className="rounded bg-gray-100 px-2 py-1 text-gray-700">
                          CTA：{String((task.reply_task as RecordItem | undefined)?.cta_strength ?? (task.reply_template as RecordItem | undefined)?.cta_strength ?? "—")}
                        </span>
                        <span className="rounded bg-gray-100 px-2 py-1 text-gray-700">
                          风险：{String((task.reply_template as RecordItem | undefined)?.risk_level ?? "—")}
                        </span>
                      </div>
                    )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={task.status} />
                    {task.status === "APPROVED" && (
                      <button className="button-secondary" onClick={() => addToScheduler(task.id)}>Add to Scheduler</button>
                    )}
                    {task.status !== "APPROVED" && (
                      <>
                        <button className="button-secondary" onClick={() => void regenerate(task)}>重新生成</button>
                        <button className="button-secondary" onClick={() => void previewPromptForTask(task)}>Preview Prompt</button>
                        <button className="button-secondary" onClick={() => reject(task.id)}>拒绝</button>
                        <button className="button" onClick={() => approve(task.id)}>批准</button>
                      </>
                    )}
                  </div>
                </div>
                {Boolean(task.post) && (
                  <div className="mt-4 border-t border-line pt-3">
                    <p className="text-sm font-semibold">{String((task.post as RecordItem).title)}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-gray-500">{String((task.post as RecordItem).content ?? "")}</p>
                  </div>
                )}
                {Boolean(task.analysis) && (
                  <div className="mt-4 grid gap-3 border-t border-line pt-3 md:grid-cols-3">
                    {[
                      ["Intent", (task.analysis as RecordItem).intent],
                      ["Pain Point", (task.analysis as RecordItem).pain_point],
                      ["Strategy", (task.analysis as RecordItem).recommended_strategy],
                      ["Source", (task.analysis as RecordItem).generation_source],
                      ["Provider", (task.analysis as RecordItem).provider_used],
                      ["Model", (task.analysis as RecordItem).model_used],
                    ].map(([label, value]) => (
                      <div key={String(label)} className="rounded border border-line p-3">
                        <p className="text-xs font-semibold uppercase text-gray-500">{String(label)}</p>
                        <p className="mt-1 text-sm text-gray-700">{String(value ?? "—")}</p>
                      </div>
                    ))}
                    <div className="rounded border border-line p-3 md:col-span-3">
                      <p className="text-xs font-semibold uppercase text-gray-500">Summary</p>
                      <p className="mt-1 text-sm text-gray-700">{String((task.analysis as RecordItem).summary ?? "—")}</p>
                    </div>
                  </div>
                )}
                {Boolean(task.reply_task) && (
                  <div className="mt-4 grid gap-3 border-t border-line pt-3 md:grid-cols-4">
                    {[
                      ["Profile Allowed", (task.reply_task as RecordItem).profile_redirect_allowed],
                      ["Main Account Allowed", (task.reply_task as RecordItem).main_account_redirect_allowed],
                      ["Direct Link Allowed", (task.reply_task as RecordItem).direct_link_allowed],
                      ["Reason", (task.reply_task as RecordItem).template_selection_reason],
                    ].map(([label, value]) => (
                      <div key={String(label)} className="rounded border border-line p-3">
                        <p className="text-xs font-semibold uppercase text-gray-500">{String(label)}</p>
                        <p className="mt-1 text-sm text-gray-700">{String(value ?? "—")}</p>
                      </div>
                    ))}
                  </div>
                )}
                {Boolean(task.reply) && (
                  <div className="mt-4 border-t border-line pt-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-xs font-semibold uppercase text-gray-500">
                        Draft · {String((task.reply as RecordItem).source ?? "UNKNOWN")}
                      </p>
                      <button className="button-secondary" onClick={() => void saveReply(task.reply as RecordItem)}>保存编辑</button>
                    </div>
                    <textarea
                      className="field min-h-32 text-sm"
                      value={
                        draftEdits[String((task.reply as RecordItem).id)] ??
                        String((task.reply as RecordItem).content ?? "")
                      }
                      onChange={(event) =>
                        setDraftEdits((current) => ({
                          ...current,
                          [String((task.reply as RecordItem).id)]: event.target.value,
                        }))
                      }
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
        {promptPreview && (
          <Section title="Prompt Preview" action={<button className="button-secondary" onClick={() => setPromptPreview(null)}>关闭</button>}>
            <div className="panel grid gap-4 p-4 lg:grid-cols-2">
              {["system_prompt", "platform_prompt", "strategy_prompt", "variables"].map((key) => (
                <div key={key}>
                  <p className="text-xs font-semibold uppercase text-gray-500">{key}</p>
                  <pre className="mt-2 overflow-x-auto rounded border border-line bg-gray-50 p-3 text-xs text-gray-600">{typeof promptPreview[key] === "object" ? JSON.stringify(promptPreview[key], null, 2) : String(promptPreview[key] ?? "—")}</pre>
                </div>
              ))}
              <div className="lg:col-span-2">
                <p className="text-xs font-semibold uppercase text-gray-500">Final Prompt · {String(promptPreview.prompt_version ?? "fallback")}</p>
                <pre className="mt-2 max-h-[420px] overflow-auto rounded border border-line bg-gray-50 p-3 text-xs text-gray-600">{String(promptPreview.final_prompt ?? "")}</pre>
              </div>
            </div>
          </Section>
        )}
      </div>
    </StateView>
  );
}

function SchedulerPage() {
  const { data, error, loading, reload } =
    useApiData<RecordItem[]>("/scheduler/tasks");
  const aiTasks = useApiData<RecordItem[]>("/ai/tasks");
  const accounts = useApiData<RecordItem[]>("/accounts");
  const logs = useApiData<RecordItem[]>("/scheduler/logs");
  const approved = (aiTasks.data ?? []).filter((task) => task.status === "APPROVED");
  const [aiTaskId, setAiTaskId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (!aiTaskId && approved[0]) setAiTaskId(String(approved[0].id));
    if (!accountId && accounts.data?.[0]) setAccountId(String(accounts.data[0].id));
  }, [approved, aiTaskId, accounts.data, accountId]);

  async function queueTask() {
    try {
      await apiRequest("/scheduler/tasks/from-approved", {
        method: "POST",
        body: JSON.stringify({
          ai_task_id: Number(aiTaskId),
          account_id: accountId ? Number(accountId) : null,
          priority: "HIGH",
        }),
      });
      setFeedback("已批准任务已加入数据库队列。Execution 不会自动运行。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "入队失败");
    }
  }

  async function runOnce() {
    try {
      const result = await apiRequest<RecordItem>("/scheduler/run-once", { method: "POST" });
      setFeedback(`Scheduler Run Once: ${String(result.status)} · processed ${String(result.processed ?? 0)}`);
      await reload();
      await logs.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "运行失败");
    }
  }

  async function taskAction(taskId: unknown, action: "cancel" | "retry") {
    try {
      await apiRequest(`/scheduler/tasks/${String(taskId)}/${action}`, { method: "POST" });
      setFeedback(action === "cancel" ? "任务已取消。" : "任务已重试入队。");
      await reload();
      await logs.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "操作失败");
    }
  }

  const taskGroups = [
    ["待调度任务", ["NEW", "WAITING_ACCOUNT", "WAITING_TIME"]],
    ["已排队任务", ["QUEUED"]],
    ["延迟中任务", ["DELAYED"]],
    ["已派发任务", ["DISPATCHED", "READY"]],
    ["失败任务", ["FAILED", "CANCELLED"]],
    ["冷却中任务", ["COOLDOWN"]],
  ] as const;

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        <div className="panel grid gap-3 p-4 md:grid-cols-[1fr_1fr_auto_auto]">
          <select className="field" value={aiTaskId} onChange={(e) => setAiTaskId(e.target.value)}>
            <option value="">选择已批准 AI Task</option>
            {approved.map((task) => <option key={String(task.id)} value={String(task.id)}>Task #{String(task.id)} · {String(task.strategy)}</option>)}
          </select>
          <select className="field" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">不指定账号</option>
            {(accounts.data ?? []).map((account) => <option key={String(account.id)} value={String(account.id)}>{String(account.username)}</option>)}
          </select>
          <button className="button" disabled={!aiTaskId} onClick={queueTask}><CalendarClock className="h-4 w-4" />加入队列</button>
          <button className="button-secondary" onClick={runOnce}><Play className="h-4 w-4" />Run Once</button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        {taskGroups.map(([title, statuses]) => {
          const rows = (data ?? []).filter((task) => (statuses as readonly string[]).includes(String(task.status)));
          return (
            <Section key={title} title={`${title} · ${rows.length}`}>
              <div className="panel overflow-x-auto">
                <table className="w-full min-w-[1320px] border-collapse text-left text-sm">
                  <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                    {["task_id", "platform", "post_title", "account", "strategy", "priority", "status", "scheduled_at", "earliest_execute_at", "delay_seconds", "created_at", "error_message", "actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
                  </tr></thead>
                  <tbody>
                    {rows.map((task) => (
                      <tr key={String(task.uuid)} className="border-b border-line last:border-0">
                        <td className="px-4 py-3 font-mono text-xs">{String(task.task_id ?? task.id)}</td>
                        <td className="px-4 py-3 uppercase text-teal">{String(task.platform ?? "—")}</td>
                        <td className="max-w-xs px-4 py-3 font-medium">{String(task.post_title ?? "—")}</td>
                        <td className="px-4 py-3">{String(task.account ?? "—")}</td>
                        <td className="px-4 py-3">{String(task.strategy ?? "—")}</td>
                        <td className="px-4 py-3">{String(task.priority ?? "—")}</td>
                        <td className="px-4 py-3"><StatusBadge value={task.status} /></td>
                        <td className="px-4 py-3 text-xs text-gray-500">{task.scheduled_at ? new Date(String(task.scheduled_at)).toLocaleString() : "—"}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">{task.earliest_execute_at ? new Date(String(task.earliest_execute_at)).toLocaleString() : "—"}</td>
                        <td className="px-4 py-3">{String(task.delay_seconds ?? 0)}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">{task.created_at ? new Date(String(task.created_at)).toLocaleString() : "—"}</td>
                        <td className="max-w-xs px-4 py-3 text-xs text-red-600">{String(task.error_message ?? "—")}</td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <button className="button-secondary" onClick={() => void taskAction(task.id, "retry")}>重试</button>
                            <button className="button-secondary" onClick={() => void taskAction(task.id, "cancel")}>取消</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          );
        })}
        <Section title="Scheduler Logs">
          <DataTable
            columns={[
              { key: "action", label: "Action" },
              { key: "old_status", label: "Old" },
              { key: "new_status", label: "New" },
              { key: "reason", label: "Reason" },
              { key: "selected_account_id", label: "Account" },
              { key: "delay_seconds", label: "Delay" },
              { key: "created_at", label: "Created" },
            ]}
            rows={logs.data ?? []}
          />
        </Section>
      </div>
    </StateView>
  );
}

function AccountCenterPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/accounts");
  const platforms = useApiData<PlatformOption[]>("/data-sources/platforms");
  const profiles = useApiData<RecordItem[]>("/tge-profiles");
  const [showForm, setShowForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState<RecordItem | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<RecordItem | null>(null);
  const [platformId, setPlatformId] = useState("1");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [profileUrl, setProfileUrl] = useState("");
  const [riskStatus, setRiskStatus] = useState("LOW");
  const [allowAutoAssisted, setAllowAutoAssisted] = useState(false);
  const [remark, setRemark] = useState("");
  const [replyLimit, setReplyLimit] = useState("5");
  const [currentReply, setCurrentReply] = useState("0");
  const [windowDay, setWindowDay] = useState("MON");
  const [windowStart, setWindowStart] = useState("09:00");
  const [windowEnd, setWindowEnd] = useState("18:00");
  const [bindProfileId, setBindProfileId] = useState("");
  const [feedback, setFeedback] = useState("");

  function startCreateAccount() {
    setEditingAccount(null);
    setPlatformId(String(platforms.data?.[0]?.id ?? 1));
    setUsername("");
    setDisplayName("");
    setProfileUrl("");
    setRiskStatus("LOW");
    setAllowAutoAssisted(false);
    setRemark("");
    setReplyLimit("5");
    setCurrentReply("0");
    setWindowDay("MON");
    setWindowStart("09:00");
    setWindowEnd("18:00");
    setShowForm(true);
  }

  function startEditAccount(account: RecordItem) {
    const limits = (account.limits ?? {}) as RecordItem;
    const windows = ((account.working_windows ?? []) as RecordItem[])[0] ?? {};
    setEditingAccount(account);
    setPlatformId(String(account.platform_id ?? platforms.data?.[0]?.id ?? 1));
    setUsername(String(account.username ?? ""));
    setDisplayName(String(account.display_name ?? ""));
    setProfileUrl(String(account.profile_url ?? ""));
    setRiskStatus(String(account.risk_status ?? "LOW"));
    setAllowAutoAssisted(Boolean(account.allow_auto_assisted));
    setRemark(String(account.remark ?? ""));
    setReplyLimit(String(limits.reply_daily_limit ?? 5));
    setCurrentReply(String(limits.current_reply_count ?? 0));
    setWindowDay(String(windows.day_of_week ?? "MON"));
    setWindowStart(String(windows.start_time ?? "09:00"));
    setWindowEnd(String(windows.end_time ?? "18:00"));
    setShowForm(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      const account = await apiRequest<RecordItem>(editingAccount ? `/accounts/${String(editingAccount.id)}` : "/accounts", {
        method: editingAccount ? "PUT" : "POST",
        body: JSON.stringify({
          platform_id: Number(platformId),
          username,
          display_name: displayName,
          profile_url: profileUrl,
          risk_status: riskStatus,
          allow_auto_assisted: allowAutoAssisted,
          remark,
          daily_limits: { browse: 20, like: 8, reply: 5 },
          working_time: { timezone: "Asia/Shanghai", ranges: ["09:00-12:00"] },
        }),
      });
      const accountId = Number(account.id);
      await apiRequest(`/accounts/${accountId}/limits`, {
        method: "PUT",
        body: JSON.stringify({
          browse_daily_limit: 20,
          like_daily_limit: 8,
          bookmark_daily_limit: 5,
          visit_profile_daily_limit: 5,
          reply_daily_limit: Number(replyLimit),
          dm_daily_limit: 0,
          follow_daily_limit: 0,
          current_browse_count: 0,
          current_like_count: 0,
          current_bookmark_count: 0,
          current_visit_profile_count: 0,
          current_reply_count: Number(currentReply),
          current_dm_count: 0,
          current_follow_count: 0,
        }),
      });
      await apiRequest(`/accounts/${accountId}/working-windows`, {
        method: "PUT",
        body: JSON.stringify({
          windows: [
            {
              day_of_week: windowDay,
              start_time: windowStart,
              end_time: windowEnd,
              timezone: "Asia/Shanghai",
              enabled: true,
            },
          ],
        }),
      });
      setFeedback(editingAccount ? "账号配置已更新。" : "账号已创建。");
      setShowForm(false);
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  async function accountAction(account: RecordItem, action: "pause" | "resume" | "recalculate-health") {
    try {
      await apiRequest(`/accounts/${String(account.id)}/${action}`, { method: "POST" });
      setFeedback(action === "pause" ? "账号已暂停。" : action === "resume" ? "账号已恢复。" : "Health Score 已重算。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "操作失败");
    }
  }

  async function bindProfile() {
    if (!selectedAccount || !bindProfileId) return;
    try {
      await apiRequest(`/accounts/${String(selectedAccount.id)}/bind-tge-profile`, {
        method: "POST",
        body: JSON.stringify({ profile_id: Number(bindProfileId) }),
      });
      setFeedback("TGE Profile 已绑定。");
      await reload();
      await profiles.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "绑定失败");
    }
  }

  async function unbindProfile(account: RecordItem) {
    try {
      await apiRequest(`/accounts/${String(account.id)}/unbind-tge-profile`, { method: "DELETE" });
      setFeedback("TGE Profile 已解绑。");
      await reload();
      await profiles.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "解绑失败");
    }
  }

  async function tgeProfileAction(profileId: unknown, action: "test-connection" | "sync-status" | "status") {
    if (!profileId) return;
    try {
      const method = action === "status" ? "GET" : "POST";
      await apiRequest(`/tge-profiles/${String(profileId)}/${action}`, { method });
      setFeedback(
        action === "test-connection"
          ? "TGE Profile 测试连接完成。"
          : action === "sync-status"
            ? "TGE Profile 状态已同步。"
            : "TGE Profile 状态已读取。",
      );
      await reload();
      await profiles.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "TGE 操作失败");
    }
  }

  const rows: RecordItem[] = (data ?? []).map((item) => {
    const limits = (item.limits ?? {}) as RecordItem;
    return {
      ...item,
      tge_environment_id: item.tge_environment_id ?? "—",
      reply_daily_limit: limits.reply_daily_limit ?? "—",
      current_reply_count: limits.current_reply_count ?? "—",
      allow_auto_assisted: item.allow_auto_assisted ?? false,
      last_seen_at: item.tge_profile ? (item.tge_profile as RecordItem).last_seen_at ?? "—" : "—",
    };
  });
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        {showForm && (
          <form className="panel grid gap-4 p-4 md:grid-cols-3 xl:grid-cols-4" onSubmit={submit}>
            <select className="field" value={platformId} onChange={(e) => setPlatformId(e.target.value)}>{(platforms.data ?? []).map((platform) => <option key={platform.id} value={platform.id}>{platform.name}</option>)}</select>
            <input className="field" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <input className="field" placeholder="Display Name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            <input className="field" placeholder="Profile URL" value={profileUrl} onChange={(e) => setProfileUrl(e.target.value)} />
            <select className="field" value={riskStatus} onChange={(e) => setRiskStatus(e.target.value)}>{["LOW", "MEDIUM", "HIGH", "CRITICAL", "COOLING_DOWN"].map((item) => <option key={item} value={item}>{item}</option>)}</select>
            <input className="field" type="number" placeholder="Reply Daily Limit" value={replyLimit} onChange={(e) => setReplyLimit(e.target.value)} />
            <input className="field" type="number" placeholder="Current Reply Count" value={currentReply} onChange={(e) => setCurrentReply(e.target.value)} />
            <input className="field" placeholder="Remark" value={remark} onChange={(e) => setRemark(e.target.value)} />
            <select className="field" value={windowDay} onChange={(e) => setWindowDay(e.target.value)}>{["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"].map((item) => <option key={item} value={item}>{item}</option>)}</select>
            <input className="field" value={windowStart} onChange={(e) => setWindowStart(e.target.value)} />
            <input className="field" value={windowEnd} onChange={(e) => setWindowEnd(e.target.value)} />
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input type="checkbox" checked={allowAutoAssisted} onChange={(e) => setAllowAutoAssisted(e.target.checked)} />
              Allow AUTO_ASSISTED
            </label>
            <div className="flex gap-2 md:col-span-3 xl:col-span-4">
              <button className="button" type="submit">{editingAccount ? "更新账号" : "保存账号"}</button>
              <button className="button-secondary" type="button" onClick={() => setShowForm(false)}>取消</button>
            </div>
          </form>
        )}
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section title="Account Assets" action={<button className="button" onClick={startCreateAccount}><Users className="h-4 w-4" />添加账号</button>}>
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1180px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Platform", "Username", "Health", "Risk", "Status", "AUTO", "TGE", "Reply Limit", "Used", "Last Seen", "Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{rows.map((account) => (
                <tr key={String(account.uuid)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 uppercase text-teal">{String(account.platform ?? "—")}</td>
                  <td className="px-4 py-3"><p className="font-semibold">{String(account.username)}</p><p className="text-xs text-gray-500">{String(account.display_name ?? "")}</p></td>
                  <td className="px-4 py-3">{String(account.health_score)}</td>
                  <td className="px-4 py-3"><StatusBadge value={account.risk_status} /></td>
                  <td className="px-4 py-3"><StatusBadge value={account.status} /></td>
                  <td className="px-4 py-3"><StatusBadge value={account.allow_auto_assisted ? "ALLOW" : "OFF"} /></td>
                  <td className="px-4 py-3 font-mono text-xs">{String(account.tge_environment_id ?? "—")}</td>
                  <td className="px-4 py-3">{String(account.reply_daily_limit)}</td>
                  <td className="px-4 py-3">{String(account.current_reply_count)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{String(account.last_seen_at ?? "—")}</td>
                  <td className="px-4 py-3"><div className="flex flex-wrap gap-2">
                    <button className="button-secondary" onClick={() => setSelectedAccount(account)}>详情</button>
                    <button className="button-secondary" onClick={() => startEditAccount(account)}>编辑</button>
                    <button className="button-secondary" onClick={() => void accountAction(account, account.status === "ACTIVE" ? "pause" : "resume")}>{account.status === "ACTIVE" ? "暂停" : "启用"}</button>
                    <button className="button-secondary" onClick={() => void accountAction(account, "recalculate-health")}>Health</button>
                  </div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
        {selectedAccount && (
          <Section title={`Account Detail · ${String(selectedAccount.username)}`} action={<button className="button-secondary" onClick={() => setSelectedAccount(null)}>关闭</button>}>
            <div className="grid gap-4 xl:grid-cols-2">
              <div className="panel p-4">
                <p className="font-semibold">基础信息</p>
                <pre className="mt-3 overflow-x-auto text-xs text-gray-600">{JSON.stringify({
                  profile_url: selectedAccount.profile_url,
                  account_level: selectedAccount.account_level,
                  karma_score: selectedAccount.karma_score,
                  followers_count: selectedAccount.followers_count,
                  following_count: selectedAccount.following_count,
                  account_age_days: selectedAccount.account_age_days,
                  cooling_down_until: selectedAccount.cooling_down_until,
                  failure_count_24h: selectedAccount.failure_count_24h,
                  restriction_count_7d: selectedAccount.restriction_count_7d,
                  allow_auto_assisted: selectedAccount.allow_auto_assisted,
                }, null, 2)}</pre>
              </div>
              <div className="panel p-4">
                <p className="font-semibold">TGE Profile</p>
                <pre className="mt-3 overflow-x-auto text-xs text-gray-600">{JSON.stringify(selectedAccount.tge_profile ?? {}, null, 2)}</pre>
                <div className="mt-3 flex gap-2">
                  <select className="field" value={bindProfileId} onChange={(e) => setBindProfileId(e.target.value)}>
                    <option value="">选择未绑定 Profile</option>
                    {(profiles.data ?? []).filter((profile) => !profile.bound_account_id || profile.bound_account_id === selectedAccount.id).map((profile) => <option key={String(profile.id)} value={String(profile.id)}>{String(profile.profile_name ?? profile.name)} · {String(profile.tge_environment_id ?? profile.environment_id)}</option>)}
                  </select>
                  <button className="button-secondary" onClick={bindProfile}>绑定</button>
                  <button className="button-secondary" onClick={() => void unbindProfile(selectedAccount)}>解绑</button>
                </div>
                {Boolean(selectedAccount.tge_profile) && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button className="button-secondary" onClick={() => void tgeProfileAction((selectedAccount.tge_profile as RecordItem).id, "test-connection")}>Test Connection</button>
                    <button className="button-secondary" onClick={() => void tgeProfileAction((selectedAccount.tge_profile as RecordItem).id, "status")}>Check Status</button>
                    <button className="button-secondary" onClick={() => void tgeProfileAction((selectedAccount.tge_profile as RecordItem).id, "sync-status")}>Sync Status</button>
                  </div>
                )}
              </div>
              <div className="panel p-4">
                <p className="font-semibold">Daily Limits / Usage Today</p>
                <pre className="mt-3 overflow-x-auto text-xs text-gray-600">{JSON.stringify(selectedAccount.limits ?? {}, null, 2)}</pre>
              </div>
              <div className="panel p-4">
                <p className="font-semibold">Working Windows</p>
                <pre className="mt-3 overflow-x-auto text-xs text-gray-600">{JSON.stringify(selectedAccount.working_windows ?? [], null, 2)}</pre>
              </div>
            </div>
          </Section>
        )}
      </div>
    </StateView>
  );
}

function SettingsPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/settings");
  const providers = useApiData<LLMProviderItem[]>("/settings/llm-providers");
  const providerRoutes = useApiData<RecordItem[]>("/settings/provider-routing");
  const replyTemplates = useApiData<RecordItem[]>("/reply-templates");
  const platformTemplateRules = useApiData<RecordItem[]>("/platform-template-rules");
  const templatePerformance = useApiData<RecordItem[]>("/template-performance");
  const promptTemplates = useApiData<RecordItem[]>("/prompt-templates");
  const promptVersions = useApiData<RecordItem[]>("/prompt-versions");
  const schedulerSettings = useApiData<RecordItem>("/settings/scheduler");
  const platformWeights = useApiData<RecordItem[]>("/settings/platform-weights");
  const tgeSettings = useApiData<RecordItem>("/settings/tge");
  const playwrightSettings = useApiData<RecordItem>("/settings/playwright");
  const submissionSettings = useApiData<RecordItem>("/settings/submission");
  const autoAssistedPlatforms = useApiData<RecordItem[]>("/settings/auto-assisted-platforms");
  const platformSelectors = useApiData<RecordItem[]>("/platform-selectors");
  const [showProviderForm, setShowProviderForm] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<number | null>(null);
  const [providerName, setProviderName] = useState("Mock Provider");
  const [providerType, setProviderType] = useState("mock");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("mock-v0.3");
  const [providerEnabled, setProviderEnabled] = useState(true);
  const [priority, setPriority] = useState("100");
  const [useAnalysis, setUseAnalysis] = useState(true);
  const [useReply, setUseReply] = useState(true);
  const [useEmbedding, setUseEmbedding] = useState(false);
  const [isMock, setIsMock] = useState(true);
  const [timeoutSeconds, setTimeoutSeconds] = useState("30");
  const [maxRetries, setMaxRetries] = useState("1");
  const [remark, setRemark] = useState("");
  const [schedulerForm, setSchedulerForm] = useState<Record<string, unknown>>({});
  const [tgeForm, setTgeForm] = useState<Record<string, unknown>>({});
  const [playwrightForm, setPlaywrightForm] = useState<Record<string, unknown>>({});
  const [submissionForm, setSubmissionForm] = useState<Record<string, unknown>>({});
  const [autoAssistedEdits, setAutoAssistedEdits] = useState<Record<string, Record<string, unknown>>>({});
  const [replyTemplateEdits, setReplyTemplateEdits] = useState<Record<string, Record<string, unknown>>>({});
  const [platformTemplateRuleEdits, setPlatformTemplateRuleEdits] = useState<Record<string, Record<string, unknown>>>({});
  const [selectorForm, setSelectorForm] = useState<Record<string, unknown>>({
    platform: "reddit",
    selector_key: "reply_box",
    selector_value: "",
    selector_type: "css",
    enabled: true,
    remark: "",
  });
  const [routeForm, setRouteForm] = useState<Record<string, unknown>>({
    name: "Default Reply Route",
    platform: "",
    task_type: "REPLY",
    strategy: "",
    min_commercial_score: 0,
    max_risk_score: 100,
    preferred_provider_id: "",
    fallback_provider_id: "",
    enabled: true,
    priority: 100,
    remark: "",
  });
  const [templateForm, setTemplateForm] = useState<Record<string, unknown>>({
    name: "Custom Reply Prompt",
    template_type: "reply_prompt",
    platform: "",
    strategy: "",
    tone: "supportive",
    content: "Write a helpful reply.\n\nTitle: {{title}}\nContent: {{content}}",
    version: "v1",
    enabled: true,
  });
  const [versionForm, setVersionForm] = useState<Record<string, unknown>>({
    prompt_template_id: "",
    version: "v1",
    content: "",
    platform: "",
    strategy: "",
    tone: "",
    enabled: true,
    is_default: false,
  });
  const [weightEdits, setWeightEdits] = useState<Record<string, Record<string, unknown>>>({});
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (schedulerSettings.data && Object.keys(schedulerForm).length === 0) {
      setSchedulerForm(schedulerSettings.data);
    }
  }, [schedulerSettings.data, schedulerForm]);

  useEffect(() => {
    if (tgeSettings.data && Object.keys(tgeForm).length === 0) {
      setTgeForm(tgeSettings.data);
    }
  }, [tgeSettings.data, tgeForm]);

  useEffect(() => {
    if (playwrightSettings.data && Object.keys(playwrightForm).length === 0) {
      setPlaywrightForm(playwrightSettings.data);
    }
  }, [playwrightSettings.data, playwrightForm]);

  useEffect(() => {
    if (submissionSettings.data && Object.keys(submissionForm).length === 0) {
      setSubmissionForm(submissionSettings.data);
    }
  }, [submissionSettings.data, submissionForm]);

  useEffect(() => {
    if ((autoAssistedPlatforms.data ?? []).length && Object.keys(autoAssistedEdits).length === 0) {
      const edits: Record<string, Record<string, unknown>> = {};
      for (const item of autoAssistedPlatforms.data ?? []) {
        const windowConfig = (item.allowed_time_window ?? {}) as Record<string, unknown>;
        edits[String(item.platform)] = {
          ...item,
          allowed_accounts_text: Array.isArray(item.allowed_accounts) ? item.allowed_accounts.join(", ") : "",
          allowed_start_time: windowConfig.allowed_start_time ?? windowConfig.start ?? "09:00",
          allowed_end_time: windowConfig.allowed_end_time ?? windowConfig.end ?? "22:00",
          timezone: windowConfig.timezone ?? "Asia/Shanghai",
        };
      }
      setAutoAssistedEdits(edits);
    }
  }, [autoAssistedPlatforms.data, autoAssistedEdits]);

  useEffect(() => {
    if ((platformWeights.data ?? []).length && Object.keys(weightEdits).length === 0) {
      const edits: Record<string, Record<string, unknown>> = {};
      for (const item of platformWeights.data ?? []) {
        edits[String(item.platform)] = {
          platform: item.platform,
          weight: item.weight,
          enabled: item.enabled,
          remark: item.remark,
        };
      }
      setWeightEdits(edits);
    }
  }, [platformWeights.data, weightEdits]);

  function resetProviderForm() {
    setEditingProviderId(null);
    setProviderName("Mock Provider");
    setProviderType("mock");
    setApiBaseUrl("");
    setApiKey("");
    setModelName("mock-v0.3");
    setProviderEnabled(true);
    setPriority("100");
    setUseAnalysis(true);
    setUseReply(true);
    setUseEmbedding(false);
    setIsMock(true);
    setTimeoutSeconds("30");
    setMaxRetries("1");
    setRemark("");
  }

  function startProviderCreate(type = "mock") {
    resetProviderForm();
    setProviderType(type);
    setIsMock(type === "mock");
    setProviderName(type === "openai" ? "OpenAI Provider" : "Mock Provider");
    setModelName(type === "openai" ? "gpt-4.1-mini" : "mock-v0.3");
    setApiBaseUrl(type === "openai" ? "https://api.openai.com/v1" : "");
    setShowProviderForm(true);
    setFeedback("");
  }

  function startProviderEdit(provider: LLMProviderItem) {
    setEditingProviderId(provider.id);
    setProviderName(provider.provider_name);
    setProviderType(provider.provider_type);
    setApiBaseUrl(String(provider.api_base_url ?? ""));
    setApiKey("");
    setModelName(provider.model_name);
    setProviderEnabled(provider.enabled);
    setPriority(String(provider.priority));
    setUseAnalysis(provider.use_for_analysis);
    setUseReply(provider.use_for_reply);
    setUseEmbedding(provider.use_for_embedding);
    setIsMock(provider.is_mock);
    setTimeoutSeconds(String(provider.timeout_seconds));
    setMaxRetries(String(provider.max_retries));
    setRemark(String(provider.remark ?? ""));
    setShowProviderForm(true);
    setFeedback("");
  }

  async function saveLLMProvider(event: React.FormEvent) {
    event.preventDefault();
    try {
      await apiRequest(
        editingProviderId
          ? `/settings/llm-providers/${editingProviderId}`
          : "/settings/llm-providers",
        {
          method: editingProviderId ? "PUT" : "POST",
          body: JSON.stringify({
            provider_name: providerName,
            provider_type: providerType,
            api_base_url: apiBaseUrl || null,
            api_key: apiKey || undefined,
            model_name: modelName,
            enabled: providerEnabled,
            priority: Number(priority),
            use_for_analysis: useAnalysis,
            use_for_reply: useReply,
            use_for_embedding: useEmbedding,
            is_mock: isMock || providerType === "mock",
            timeout_seconds: Number(timeoutSeconds),
            max_retries: Number(maxRetries),
            remark,
          }),
        },
      );
      setFeedback(editingProviderId ? "LLM Provider 已更新。" : "LLM Provider 已创建。");
      setShowProviderForm(false);
      resetProviderForm();
      await providers.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  async function toggleProvider(provider: LLMProviderItem) {
    try {
      await apiRequest(`/settings/llm-providers/${provider.id}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: !provider.enabled }),
      });
      setFeedback(provider.enabled ? "Provider 已停用。" : "Provider 已启用。");
      await providers.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  async function testProvider(provider: LLMProviderItem) {
    try {
      const result = await apiRequest<RecordItem>(`/settings/llm-providers/${provider.id}/test`, { method: "POST" });
      setFeedback(`Provider 测试完成：${String(result.health_status)} · ${String(result.message ?? "")}`);
      await providers.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Provider 测试失败");
    }
  }

  function updateRouteField(key: string, value: unknown) {
    setRouteForm((current) => ({ ...current, [key]: value }));
  }

  async function createProviderRoute() {
    try {
      await apiRequest("/settings/provider-routing", {
        method: "POST",
        body: JSON.stringify({
          ...routeForm,
          platform: routeForm.platform || null,
          strategy: routeForm.strategy || null,
          preferred_provider_id: routeForm.preferred_provider_id ? Number(routeForm.preferred_provider_id) : null,
          fallback_provider_id: routeForm.fallback_provider_id ? Number(routeForm.fallback_provider_id) : null,
          min_commercial_score: Number(routeForm.min_commercial_score ?? 0),
          max_risk_score: Number(routeForm.max_risk_score ?? 100),
          priority: Number(routeForm.priority ?? 100),
        }),
      });
      setFeedback("Provider Routing 已创建。");
      await providerRoutes.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "创建 Routing 失败");
    }
  }

  function updateTemplateField(key: string, value: unknown) {
    setTemplateForm((current) => ({ ...current, [key]: value }));
  }

  async function createPromptTemplate() {
    try {
      await apiRequest("/prompt-templates", {
        method: "POST",
        body: JSON.stringify({
          ...templateForm,
          platform: templateForm.platform || null,
          strategy: templateForm.strategy || null,
          tone: templateForm.tone || null,
        }),
      });
      setFeedback("Prompt Template 已创建。");
      await promptTemplates.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "创建 Prompt Template 失败");
    }
  }

  function updateVersionField(key: string, value: unknown) {
    setVersionForm((current) => ({ ...current, [key]: value }));
  }

  async function createPromptVersion() {
    try {
      await apiRequest("/prompt-versions", {
        method: "POST",
        body: JSON.stringify({
          ...versionForm,
          prompt_template_id: Number(versionForm.prompt_template_id),
          platform: versionForm.platform || null,
          strategy: versionForm.strategy || null,
          tone: versionForm.tone || null,
          variables_schema: {},
        }),
      });
      setFeedback("Prompt Version 已创建。");
      await promptVersions.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "创建 Prompt Version 失败");
    }
  }

  function updateSchedulerField(key: string, value: unknown) {
    setSchedulerForm((current) => ({ ...current, [key]: value }));
  }

  async function saveSchedulerSettings() {
    try {
      await apiRequest("/settings/scheduler", {
        method: "PUT",
        body: JSON.stringify({
          scheduler_enabled: Boolean(schedulerForm.scheduler_enabled),
          auto_queue_on_approval: Boolean(schedulerForm.auto_queue_on_approval),
          default_strategy: String(schedulerForm.default_strategy ?? "ROUND_ROBIN"),
          enable_random_delay: Boolean(schedulerForm.enable_random_delay),
          min_delay_seconds: Number(schedulerForm.min_delay_seconds ?? 120),
          max_delay_seconds: Number(schedulerForm.max_delay_seconds ?? 480),
          enable_platform_round_robin: Boolean(schedulerForm.enable_platform_round_robin),
          enable_weighted_round_robin: Boolean(schedulerForm.enable_weighted_round_robin),
          max_tasks_per_account_per_day: Number(schedulerForm.max_tasks_per_account_per_day ?? 5),
          max_tasks_per_platform_per_day: Number(schedulerForm.max_tasks_per_platform_per_day ?? 20),
        }),
      });
      setFeedback("Scheduler 默认配置已保存。");
      await schedulerSettings.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存 Scheduler 配置失败");
    }
  }

  async function savePlatformWeights() {
    try {
      await apiRequest("/settings/platform-weights", {
        method: "PUT",
        body: JSON.stringify({ weights: Object.values(weightEdits) }),
      });
      setFeedback("平台权重已保存。");
      await platformWeights.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存平台权重失败");
    }
  }

  function updateTgeField(key: string, value: unknown) {
    setTgeForm((current) => ({ ...current, [key]: value }));
  }

  async function saveTgeSettings() {
    try {
      await apiRequest("/settings/tge", {
        method: "PUT",
        body: JSON.stringify({
          tge_api_base_url: String(tgeForm.tge_api_base_url ?? ""),
          tge_api_key: String(tgeForm.tge_api_key ?? ""),
          default_timeout_seconds: Number(tgeForm.default_timeout_seconds ?? 10),
          enable_tge_connection_test: Boolean(tgeForm.enable_tge_connection_test),
          enable_auto_start_environment: Boolean(tgeForm.enable_auto_start_environment),
          enable_auto_attach_environment: Boolean(tgeForm.enable_auto_attach_environment),
          enable_auto_close_tab: Boolean(tgeForm.enable_auto_close_tab),
          remark: String(tgeForm.remark ?? ""),
        }),
      });
      setFeedback("TGE 配置已保存。");
      await tgeSettings.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存 TGE 配置失败");
    }
  }

  function updatePlaywrightField(key: string, value: unknown) {
    setPlaywrightForm((current) => ({ ...current, [key]: value }));
  }

  function updateSubmissionField(key: string, value: unknown) {
    setSubmissionForm((current) => ({ ...current, [key]: value }));
  }

  function updateAutoAssistedPlatform(platform: string, key: string, value: unknown) {
    setAutoAssistedEdits((current) => ({
      ...current,
      [platform]: {
        ...(current[platform] ?? {}),
        platform,
        [key]: value,
      },
    }));
  }

  function updateReplyTemplateEdit(template: RecordItem, key: string, value: unknown) {
    const id = String(template.id);
    setReplyTemplateEdits((current) => ({
      ...current,
      [id]: {
        ...(current[id] ?? template),
        [key]: value,
      },
    }));
  }

  function updatePlatformTemplateRuleEdit(rule: RecordItem, key: string, value: unknown) {
    const id = String(rule.id);
    setPlatformTemplateRuleEdits((current) => ({
      ...current,
      [id]: {
        ...(current[id] ?? rule),
        [key]: value,
      },
    }));
  }

  function updateSelectorField(key: string, value: unknown) {
    setSelectorForm((current) => ({ ...current, [key]: value }));
  }

  async function savePlaywrightSettings() {
    try {
      await apiRequest("/settings/playwright", {
        method: "PUT",
        body: JSON.stringify({
          playwright_enabled: Boolean(playwrightForm.playwright_enabled),
          playwright_mock_mode: Boolean(playwrightForm.playwright_mock_mode),
          playwright_timeout_seconds: Number(playwrightForm.playwright_timeout_seconds ?? 30),
          playwright_headless: Boolean(playwrightForm.playwright_headless),
          playwright_default_wait_ms: Number(playwrightForm.playwright_default_wait_ms ?? 1000),
          enable_screenshot: Boolean(playwrightForm.enable_screenshot),
          enable_html_snapshot: Boolean(playwrightForm.enable_html_snapshot),
          enable_auto_close_tab: Boolean(playwrightForm.enable_auto_close_tab),
          enable_replay_capture: Boolean(playwrightForm.enable_replay_capture),
        }),
      });
      setFeedback("Playwright 配置已保存。");
      await playwrightSettings.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存 Playwright 配置失败");
    }
  }

  async function saveSubmissionSettings() {
    try {
      await apiRequest("/settings/submission", {
        method: "PUT",
        body: JSON.stringify({
          default_execution_mode: String(submissionForm.default_execution_mode ?? "SEMI_AUTO"),
          auto_assisted_enabled: Boolean(submissionForm.auto_assisted_enabled),
          auto_assisted_test_mode: Boolean(submissionForm.auto_assisted_test_mode),
          full_auto_enabled: Boolean(submissionForm.full_auto_enabled),
          auto_assisted_real_submit_enabled: Boolean(submissionForm.auto_assisted_real_submit_enabled),
          max_retry: Number(submissionForm.max_retry ?? 1),
          verify_timeout_seconds: Number(submissionForm.verify_timeout_seconds ?? 20),
          capture_screenshot_enabled: Boolean(submissionForm.capture_screenshot_enabled),
          capture_html_enabled: Boolean(submissionForm.capture_html_enabled),
          max_reply_retry: Number(submissionForm.max_reply_retry ?? 1),
          max_submission_retry: Number(submissionForm.max_submission_retry ?? 1),
          screenshot_required: Boolean(submissionForm.screenshot_required),
          html_snapshot_on_failure: Boolean(submissionForm.html_snapshot_on_failure),
          manual_confirm_required: Boolean(submissionForm.manual_confirm_required),
          verification_level_default: String(submissionForm.verification_level_default ?? "MANUAL_CONFIRMED"),
          retry_on_browser_disconnect: Boolean(submissionForm.retry_on_browser_disconnect),
          retry_on_worker_offline: Boolean(submissionForm.retry_on_worker_offline),
          audit_enabled: Boolean(submissionForm.audit_enabled ?? true),
          verification_required: Boolean(submissionForm.verification_required ?? true),
        }),
      });
      setFeedback("Submission Policy 已保存。");
      await submissionSettings.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存 Submission Policy 失败");
    }
  }

  async function saveAutoAssistedPlatform(platform: string) {
    const item = autoAssistedEdits[platform] ?? {};
    try {
      await apiRequest(`/settings/auto-assisted-platforms/${platform}`, {
        method: "PUT",
        body: JSON.stringify({
          auto_assisted_enabled: Boolean(item.auto_assisted_enabled),
          max_daily_auto_submit: Number(item.max_daily_auto_submit ?? 3),
          allowed_accounts: String(item.allowed_accounts_text ?? item.allowed_accounts ?? "")
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
          allowed_time_window: {
            allowed_start_time: String(item.allowed_start_time ?? "09:00"),
            allowed_end_time: String(item.allowed_end_time ?? "22:00"),
            timezone: String(item.timezone ?? "Asia/Shanghai"),
          },
          remark: String(item.remark ?? ""),
        }),
      });
      setFeedback(`${platform} AUTO_ASSISTED 配置已保存。`);
      setAutoAssistedEdits({});
      await autoAssistedPlatforms.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存平台 AUTO_ASSISTED 失败");
    }
  }

  async function saveReplyTemplate(template: RecordItem) {
    const id = String(template.id);
    const edit = replyTemplateEdits[id] ?? template;
    try {
      await apiRequest(`/reply-templates/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          description: String(edit.description ?? ""),
          risk_level: String(edit.risk_level ?? template.risk_level ?? "LOW"),
          enabled: Boolean(edit.enabled),
        }),
      });
      setFeedback("Reply Template 已保存。");
      setReplyTemplateEdits((current) => {
        const next = { ...current };
        delete next[id];
        return next;
      });
      await replyTemplates.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存 Reply Template 失败");
    }
  }

  async function savePlatformTemplateRule(rule: RecordItem) {
    const id = String(rule.id);
    const edit = platformTemplateRuleEdits[id] ?? rule;
    try {
      await apiRequest(`/platform-template-rules/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          allowed: Boolean(edit.allowed),
          default_enabled: Boolean(edit.default_enabled),
          allow_auto_assisted: Boolean(edit.allow_auto_assisted),
          max_daily_ratio: Number(edit.max_daily_ratio ?? 0),
          risk_level: String(edit.risk_level ?? "LOW"),
          notes: String(edit.notes ?? ""),
        }),
      });
      setFeedback("Platform Template Rule 已保存。");
      setPlatformTemplateRuleEdits((current) => {
        const next = { ...current };
        delete next[id];
        return next;
      });
      await platformTemplateRules.reload();
      await templatePerformance.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存 Platform Rule 失败");
    }
  }

  async function emergencyStopAutoAssisted() {
    try {
      await apiRequest("/submission/emergency-stop", { method: "POST" });
      setFeedback("Emergency Stop 已执行，AUTO_ASSISTED 已全部关闭。");
      setSubmissionForm({});
      setAutoAssistedEdits({});
      await submissionSettings.reload();
      await autoAssistedPlatforms.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Emergency Stop 失败");
    }
  }

  async function createSelector() {
    try {
      await apiRequest("/platform-selectors", {
        method: "POST",
        body: JSON.stringify(selectorForm),
      });
      setFeedback("Platform selector 已创建。");
      setSelectorForm((current) => ({ ...current, selector_value: "", remark: "" }));
      await platformSelectors.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "创建 selector 失败");
    }
  }

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        {showProviderForm && (
          <form className="panel grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-4" onSubmit={saveLLMProvider}>
            <label className="text-xs font-semibold text-gray-600">
              Provider Name
              <input className="field mt-2" value={providerName} onChange={(e) => setProviderName(e.target.value)} required />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Provider Type
              <select className="field mt-2" value={providerType} onChange={(e) => {
                setProviderType(e.target.value);
                setIsMock(e.target.value === "mock");
              }}>
                {["mock", "openai", "anthropic", "gemini", "ollama", "custom_http", "custom"].map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
            </label>
            <label className="text-xs font-semibold text-gray-600">
              API Base URL
              <input className="field mt-2" value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              API Key
              <input className="field mt-2" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder={editingProviderId ? "留空则保持现有 Key" : "Mock 可留空"} autoComplete="new-password" />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Model Name
              <input className="field mt-2" value={modelName} onChange={(e) => setModelName(e.target.value)} required />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Priority
              <input className="field mt-2" type="number" value={priority} onChange={(e) => setPriority(e.target.value)} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Timeout Seconds
              <input className="field mt-2" type="number" min="1" value={timeoutSeconds} onChange={(e) => setTimeoutSeconds(e.target.value)} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Max Retries
              <input className="field mt-2" type="number" min="0" value={maxRetries} onChange={(e) => setMaxRetries(e.target.value)} />
            </label>
            <label className="text-xs font-semibold text-gray-600 md:col-span-2 xl:col-span-4">
              Remark
              <input className="field mt-2" value={remark} onChange={(e) => setRemark(e.target.value)} />
            </label>
            <div className="flex flex-wrap gap-4 text-sm font-medium text-gray-700 md:col-span-2 xl:col-span-4">
              <label className="flex items-center gap-2"><input type="checkbox" checked={providerEnabled} onChange={(e) => setProviderEnabled(e.target.checked)} />Enabled</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={useAnalysis} onChange={(e) => setUseAnalysis(e.target.checked)} />Analysis</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={useReply} onChange={(e) => setUseReply(e.target.checked)} />Reply</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={useEmbedding} onChange={(e) => setUseEmbedding(e.target.checked)} />Embedding</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={isMock} onChange={(e) => setIsMock(e.target.checked)} />Mock</label>
            </div>
            <div className="flex gap-2 md:col-span-2 xl:col-span-4">
              <button className="button" type="submit"><Settings className="h-4 w-4" />{editingProviderId ? "保存 Provider" : "创建 Provider"}</button>
              <button className="button-secondary" type="button" onClick={() => setShowProviderForm(false)}>取消</button>
            </div>
          </form>
        )}
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section
          title="TGE Configuration"
          action={<button className="button" onClick={saveTgeSettings}><Settings className="h-4 w-4" />保存 TGE</button>}
        >
          <div className="panel grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-xs font-semibold text-gray-600">
              TGE API Base URL
              <input className="field mt-2" value={String(tgeForm.tge_api_base_url ?? "")} onChange={(e) => updateTgeField("tge_api_base_url", e.target.value)} placeholder="http://127.0.0.1:50326" />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              TGE API Key
              <input className="field mt-2" type="password" value={String(tgeForm.tge_api_key ?? "")} onChange={(e) => updateTgeField("tge_api_key", e.target.value)} placeholder={String(tgeForm.tge_api_key_masked ?? "留空则保持现有 Key")} autoComplete="new-password" />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Timeout Seconds
              <input className="field mt-2" type="number" value={String(tgeForm.default_timeout_seconds ?? 10)} onChange={(e) => updateTgeField("default_timeout_seconds", Number(e.target.value))} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Remark
              <input className="field mt-2" value={String(tgeForm.remark ?? "")} onChange={(e) => updateTgeField("remark", e.target.value)} />
            </label>
            {[
              ["enable_tge_connection_test", "Connection Test"],
              ["enable_auto_start_environment", "Auto Start Environment"],
              ["enable_auto_attach_environment", "Auto Attach Environment"],
              ["enable_auto_close_tab", "Auto Close Tab"],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <input type="checkbox" checked={Boolean(tgeForm[key])} onChange={(e) => updateTgeField(key, e.target.checked)} />
                {label}
              </label>
            ))}
          </div>
        </Section>
        <Section
          title="Playwright Configuration"
          action={<button className="button" onClick={savePlaywrightSettings}><Settings className="h-4 w-4" />保存 Playwright</button>}
        >
          <div className="panel grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["playwright_enabled", "Playwright Enabled"],
              ["playwright_mock_mode", "Mock Mode"],
              ["playwright_headless", "Headless"],
              ["enable_screenshot", "Screenshot"],
              ["enable_html_snapshot", "HTML Snapshot"],
              ["enable_auto_close_tab", "Auto Close Tab"],
              ["enable_replay_capture", "Replay Capture"],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <input type="checkbox" checked={Boolean(playwrightForm[key])} onChange={(e) => updatePlaywrightField(key, e.target.checked)} />
                {label}
              </label>
            ))}
            <label className="text-xs font-semibold text-gray-600">
              Timeout Seconds
              <input className="field mt-2" type="number" value={String(playwrightForm.playwright_timeout_seconds ?? 30)} onChange={(e) => updatePlaywrightField("playwright_timeout_seconds", Number(e.target.value))} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Default Wait MS
              <input className="field mt-2" type="number" value={String(playwrightForm.playwright_default_wait_ms ?? 1000)} onChange={(e) => updatePlaywrightField("playwright_default_wait_ms", Number(e.target.value))} />
            </label>
          </div>
        </Section>
        <Section
          title="Submission Policy"
          action={
            <div className="flex flex-wrap gap-2">
              <button className="button-secondary" onClick={emergencyStopAutoAssisted}><ShieldCheck className="h-4 w-4" />Emergency Stop</button>
              <button className="button" onClick={saveSubmissionSettings}><Settings className="h-4 w-4" />保存 Submission</button>
            </div>
          }
        >
          <div className="panel grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="text-xs font-semibold text-gray-600">
              Default Execution Mode
              <select
                className="field mt-2"
                value={String(submissionForm.default_execution_mode ?? "SEMI_AUTO")}
                onChange={(e) => updateSubmissionField("default_execution_mode", e.target.value)}
              >
                {["SEMI_AUTO", "AUTO_ASSISTED", "FULL_AUTO"].map((mode) => (
                  <option key={mode} value={mode}>{mode}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Max Retry
              <input className="field mt-2" type="number" min="0" value={String(submissionForm.max_retry ?? 1)} onChange={(e) => updateSubmissionField("max_retry", Number(e.target.value))} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Verify Timeout Seconds
              <input className="field mt-2" type="number" min="1" value={String(submissionForm.verify_timeout_seconds ?? 20)} onChange={(e) => updateSubmissionField("verify_timeout_seconds", Number(e.target.value))} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Max Reply Retry
              <input className="field mt-2" type="number" min="0" value={String(submissionForm.max_reply_retry ?? 1)} onChange={(e) => updateSubmissionField("max_reply_retry", Number(e.target.value))} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Max Submission Retry
              <input className="field mt-2" type="number" min="0" value={String(submissionForm.max_submission_retry ?? 1)} onChange={(e) => updateSubmissionField("max_submission_retry", Number(e.target.value))} />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Verification Level Default
              <select
                className="field mt-2"
                value={String(submissionForm.verification_level_default ?? "MANUAL_CONFIRMED")}
                onChange={(e) => updateSubmissionField("verification_level_default", e.target.value)}
              >
                {["NONE", "MANUAL_CONFIRMED", "DOM_VERIFIED", "URL_VERIFIED", "EXTERNAL_ID_VERIFIED", "FULL_VERIFIED"].map((level) => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </label>
            <div className="rounded border border-line bg-gray-50 p-3 text-xs text-gray-600">
              默认 SEMI_AUTO。AUTO_ASSISTED / FULL_AUTO 仅保留策略结构，未开启时不会自动点击提交。
            </div>
            {[
              ["auto_assisted_enabled", "Auto Assisted Enabled"],
              ["auto_assisted_test_mode", "Auto Assisted Test Mode"],
              ["auto_assisted_real_submit_enabled", "Real Submit Enabled"],
              ["full_auto_enabled", "Full Auto Enabled"],
              ["capture_screenshot_enabled", "Capture Screenshot"],
              ["capture_html_enabled", "Capture HTML"],
              ["screenshot_required", "Screenshot Required"],
              ["html_snapshot_on_failure", "HTML Snapshot On Failure"],
              ["manual_confirm_required", "Manual Confirm Required"],
              ["retry_on_browser_disconnect", "Retry Browser Disconnect"],
              ["retry_on_worker_offline", "Retry Worker Offline"],
              ["audit_enabled", "Audit Enabled"],
              ["verification_required", "Verification Required"],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <input type="checkbox" checked={Boolean(submissionForm[key])} onChange={(e) => updateSubmissionField(key, e.target.checked)} />
                {label}
              </label>
            ))}
          </div>
        </Section>
        <Section title="AUTO_ASSISTED Platform Controls">
          <div className="grid gap-4 lg:grid-cols-2">
            {(autoAssistedPlatforms.data ?? []).map((item) => {
              const platform = String(item.platform);
              const edit = autoAssistedEdits[platform] ?? item;
              return (
                <div key={platform} className="panel space-y-4 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-bold uppercase text-ink">{platform}</p>
                      <p className="text-xs text-gray-500">平台级 AUTO_ASSISTED 闸门。默认关闭。</p>
                    </div>
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                      <input type="checkbox" checked={Boolean(edit.auto_assisted_enabled)} onChange={(e) => updateAutoAssistedPlatform(platform, "auto_assisted_enabled", e.target.checked)} />
                      Enabled
                    </label>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="text-xs font-semibold text-gray-600">
                      Max Daily Auto Submit
                      <input className="field mt-2" type="number" min="0" value={String(edit.max_daily_auto_submit ?? 3)} onChange={(e) => updateAutoAssistedPlatform(platform, "max_daily_auto_submit", Number(e.target.value))} />
                    </label>
                    <label className="text-xs font-semibold text-gray-600">
                      Allowed Accounts
                      <input className="field mt-2" value={String(edit.allowed_accounts_text ?? "")} onChange={(e) => updateAutoAssistedPlatform(platform, "allowed_accounts_text", e.target.value)} placeholder="account id / username, comma separated" />
                    </label>
                    <label className="text-xs font-semibold text-gray-600">
                      Start Time
                      <input className="field mt-2" value={String(edit.allowed_start_time ?? "09:00")} onChange={(e) => updateAutoAssistedPlatform(platform, "allowed_start_time", e.target.value)} />
                    </label>
                    <label className="text-xs font-semibold text-gray-600">
                      End Time
                      <input className="field mt-2" value={String(edit.allowed_end_time ?? "22:00")} onChange={(e) => updateAutoAssistedPlatform(platform, "allowed_end_time", e.target.value)} />
                    </label>
                    <label className="text-xs font-semibold text-gray-600">
                      Timezone
                      <input className="field mt-2" value={String(edit.timezone ?? "Asia/Shanghai")} onChange={(e) => updateAutoAssistedPlatform(platform, "timezone", e.target.value)} />
                    </label>
                    <label className="text-xs font-semibold text-gray-600">
                      Remark
                      <input className="field mt-2" value={String(edit.remark ?? "")} onChange={(e) => updateAutoAssistedPlatform(platform, "remark", e.target.value)} />
                    </label>
                  </div>
                  <button className="button-secondary" onClick={() => void saveAutoAssistedPlatform(platform)}>保存 {platform}</button>
                </div>
              );
            })}
          </div>
        </Section>
        <Section
          title="Platform Selector Registry"
          action={<button className="button" onClick={createSelector}><Settings className="h-4 w-4" />新增 Selector</button>}
        >
          <div className="panel grid gap-3 p-4 md:grid-cols-3 xl:grid-cols-6">
            <input className="field" value={String(selectorForm.platform ?? "")} onChange={(e) => updateSelectorField("platform", e.target.value)} placeholder="platform" />
            <select className="field" value={String(selectorForm.selector_key ?? "reply_box")} onChange={(e) => updateSelectorField("selector_key", e.target.value)}>
              {["reply_box", "comment_button", "login_required", "rate_limited", "comment_disabled"].map((key) => <option key={key} value={key}>{key}</option>)}
            </select>
            <input className="field xl:col-span-2" value={String(selectorForm.selector_value ?? "")} onChange={(e) => updateSelectorField("selector_value", e.target.value)} placeholder="selector value" />
            <select className="field" value={String(selectorForm.selector_type ?? "css")} onChange={(e) => updateSelectorField("selector_type", e.target.value)}>
              {["css", "xpath", "text"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <label className="flex items-center gap-2 rounded border border-line px-3 text-sm"><input type="checkbox" checked={Boolean(selectorForm.enabled)} onChange={(e) => updateSelectorField("enabled", e.target.checked)} />Enabled</label>
          </div>
          <div className="panel mt-3 overflow-x-auto">
            <table className="w-full min-w-[920px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["platform", "key", "type", "selector", "enabled", "remark"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(platformSelectors.data ?? []).map((selector) => (
                <tr key={String(selector.id)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 uppercase text-teal">{String(selector.platform)}</td>
                  <td className="px-4 py-3 font-mono text-xs">{String(selector.selector_key)}</td>
                  <td className="px-4 py-3">{String(selector.selector_type)}</td>
                  <td className="max-w-md px-4 py-3 font-mono text-xs">{String(selector.selector_value)}</td>
                  <td className="px-4 py-3">{String(selector.enabled)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{String(selector.remark ?? "")}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
        <Section
          title="Scheduler Defaults"
          action={<button className="button" onClick={saveSchedulerSettings}><Settings className="h-4 w-4" />保存 Scheduler</button>}
        >
          <div className="panel grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["scheduler_enabled", "Scheduler Enabled"],
              ["auto_queue_on_approval", "Auto Queue Approved"],
              ["enable_random_delay", "Random Delay"],
              ["enable_platform_round_robin", "Platform Round Robin"],
              ["enable_weighted_round_robin", "Weighted Round Robin"],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm font-medium text-gray-700">
                <input type="checkbox" checked={Boolean(schedulerForm[key])} onChange={(e) => updateSchedulerField(key, e.target.checked)} />
                {label}
              </label>
            ))}
            {[
              ["default_strategy", "Default Strategy"],
              ["min_delay_seconds", "Min Delay"],
              ["max_delay_seconds", "Max Delay"],
              ["max_tasks_per_account_per_day", "Max / Account / Day"],
              ["max_tasks_per_platform_per_day", "Max / Platform / Day"],
            ].map(([key, label]) => (
              <label key={key} className="text-xs font-semibold text-gray-600">
                {label}
                <input
                  className="field mt-2"
                  value={String(schedulerForm[key] ?? "")}
                  onChange={(e) => updateSchedulerField(key, key === "default_strategy" ? e.target.value : Number(e.target.value))}
                />
              </label>
            ))}
          </div>
        </Section>
        <Section
          title="Platform Weights"
          action={<button className="button-secondary" onClick={savePlatformWeights}>保存权重</button>}
        >
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Platform", "Weight", "Enabled", "Remark"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(platformWeights.data ?? []).map((item) => {
                const key = String(item.platform);
                const edit = weightEdits[key] ?? item;
                return (
                  <tr key={String(item.uuid)} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-semibold uppercase text-teal">{String(item.platform)}</td>
                    <td className="px-4 py-3"><input className="field w-24" type="number" value={String(edit.weight ?? 10)} onChange={(e) => setWeightEdits((current) => ({ ...current, [key]: { ...edit, platform: item.platform, weight: Number(e.target.value) } }))} /></td>
                    <td className="px-4 py-3"><input type="checkbox" checked={Boolean(edit.enabled)} onChange={(e) => setWeightEdits((current) => ({ ...current, [key]: { ...edit, platform: item.platform, enabled: e.target.checked } }))} /></td>
                    <td className="px-4 py-3"><input className="field min-w-64" value={String(edit.remark ?? "")} onChange={(e) => setWeightEdits((current) => ({ ...current, [key]: { ...edit, platform: item.platform, remark: e.target.value } }))} /></td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        </Section>
        <Section title="Reply Templates">
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1180px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["中文名称", "Intent", "CTA", "Risk", "Enabled", "Description", "Rules", "Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(replyTemplates.data ?? []).map((template) => {
                const edit = replyTemplateEdits[String(template.id)] ?? template;
                return (
                  <tr key={String(template.id)} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-semibold">{String(template.name_cn)}</td>
                    <td className="px-4 py-3 font-mono text-xs">{String(template.funnel_intent)}</td>
                    <td className="px-4 py-3">{String(template.cta_strength)}</td>
                    <td className="px-4 py-3">
                      <select className="field min-w-32" value={String(edit.risk_level ?? "LOW")} onChange={(e) => updateReplyTemplateEdit(template, "risk_level", e.target.value)}>
                        {["LOW", "LOW_MEDIUM", "MEDIUM", "HIGH", "CRITICAL"].map((level) => <option key={level} value={level}>{level}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3"><input type="checkbox" checked={Boolean(edit.enabled)} onChange={(e) => updateReplyTemplateEdit(template, "enabled", e.target.checked)} /></td>
                    <td className="px-4 py-3"><input className="field min-w-80" value={String(edit.description ?? "")} onChange={(e) => updateReplyTemplateEdit(template, "description", e.target.value)} /></td>
                    <td className="px-4 py-3 text-xs text-gray-500">{Array.isArray(template.platform_rules) ? template.platform_rules.length : 0}</td>
                    <td className="px-4 py-3"><button className="button-secondary" onClick={() => void saveReplyTemplate(template)}>保存</button></td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        </Section>
        <Section title="Platform Template Rules">
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1280px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Platform", "Template", "Allowed", "Default", "AUTO_ASSISTED", "Daily Ratio", "Risk", "Notes", "Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(platformTemplateRules.data ?? []).map((rule) => {
                const edit = platformTemplateRuleEdits[String(rule.id)] ?? rule;
                return (
                  <tr key={String(rule.id)} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 uppercase text-teal">{String(rule.platform)}</td>
                    <td className="px-4 py-3"><p className="font-semibold">{String(rule.template_name_cn)}</p><p className="text-xs text-gray-500">{String(rule.funnel_intent)}</p></td>
                    <td className="px-4 py-3"><input type="checkbox" checked={Boolean(edit.allowed)} onChange={(e) => updatePlatformTemplateRuleEdit(rule, "allowed", e.target.checked)} /></td>
                    <td className="px-4 py-3"><input type="checkbox" checked={Boolean(edit.default_enabled)} onChange={(e) => updatePlatformTemplateRuleEdit(rule, "default_enabled", e.target.checked)} /></td>
                    <td className="px-4 py-3"><input type="checkbox" checked={Boolean(edit.allow_auto_assisted)} onChange={(e) => updatePlatformTemplateRuleEdit(rule, "allow_auto_assisted", e.target.checked)} /></td>
                    <td className="px-4 py-3"><input className="field w-28" type="number" min="0" max="1" step="0.05" value={String(edit.max_daily_ratio ?? 0)} onChange={(e) => updatePlatformTemplateRuleEdit(rule, "max_daily_ratio", Number(e.target.value))} /></td>
                    <td className="px-4 py-3">
                      <select className="field min-w-32" value={String(edit.risk_level ?? "LOW")} onChange={(e) => updatePlatformTemplateRuleEdit(rule, "risk_level", e.target.value)}>
                        {["LOW", "LOW_MEDIUM", "MEDIUM", "HIGH", "CRITICAL"].map((level) => <option key={level} value={level}>{level}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3"><input className="field min-w-72" value={String(edit.notes ?? "")} onChange={(e) => updatePlatformTemplateRuleEdit(rule, "notes", e.target.value)} /></td>
                    <td className="px-4 py-3"><button className="button-secondary" onClick={() => void savePlatformTemplateRule(rule)}>保存</button></td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        </Section>
        <Section title="Template Performance">
          <DataTable
            rows={templatePerformance.data ?? []}
            columns={[
              { key: "date", label: "Date" },
              { key: "platform", label: "Platform" },
              { key: "template_name_cn", label: "Template" },
              { key: "funnel_intent", label: "Intent" },
              { key: "generated_count", label: "Generated" },
              { key: "approved_count", label: "Approved" },
              { key: "submitted_count", label: "Submitted" },
              { key: "verified_count", label: "Verified" },
              { key: "failed_count", label: "Failed" },
              { key: "success_rate", label: "Success %" },
              { key: "failure_rate", label: "Failure %" },
            ]}
          />
        </Section>
        <Section
          title="LLM Providers"
          action={
            <div className="flex gap-2">
              <button className="button-secondary" onClick={() => startProviderCreate("mock")}>Mock</button>
              <button className="button" onClick={() => startProviderCreate("openai")}>OpenAI</button>
            </div>
          }
        >
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1120px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Provider", "Type", "Model", "Key", "Purpose", "Priority", "Health", "Status", "Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>
                {(providers.data ?? []).map((provider) => (
                  <tr key={provider.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3"><p className="font-semibold">{provider.provider_name}</p><p className="mt-1 max-w-56 truncate text-xs text-gray-500">{provider.remark || "—"}</p></td>
                    <td className="px-4 py-3 text-gray-600">{provider.provider_type}{provider.is_mock ? " · mock" : ""}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{provider.model_name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{provider.api_key_masked || (provider.api_key_configured ? "********" : "Not set")}</td>
                    <td className="px-4 py-3 text-xs text-gray-600">{[
                      provider.use_for_analysis ? "Analysis" : "",
                      provider.use_for_reply ? "Reply" : "",
                      provider.use_for_embedding ? "Embedding" : "",
                    ].filter(Boolean).join(" / ") || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{provider.priority}</td>
                    <td className="px-4 py-3"><StatusBadge value={provider.health_status ?? "UNKNOWN"} /></td>
                    <td className="px-4 py-3"><StatusBadge value={provider.enabled ? provider.status : "DISABLED"} /></td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button className="icon-button" title="编辑" onClick={() => startProviderEdit(provider)}><Pencil className="h-4 w-4" /></button>
                        <button className="button-secondary" onClick={() => void testProvider(provider)}>测试</button>
                        <button className="button-secondary" onClick={() => void toggleProvider(provider)}>{provider.enabled ? "停用" : "启用"}</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
        <Section
          title="Provider Routing"
          action={<button className="button" onClick={createProviderRoute}><Settings className="h-4 w-4" />新增 Routing</button>}
        >
          <div className="panel grid gap-3 p-4 md:grid-cols-3 xl:grid-cols-6">
            <input className="field" value={String(routeForm.name ?? "")} onChange={(e) => updateRouteField("name", e.target.value)} placeholder="name" />
            <input className="field" value={String(routeForm.platform ?? "")} onChange={(e) => updateRouteField("platform", e.target.value)} placeholder="platform or empty" />
            <select className="field" value={String(routeForm.task_type ?? "REPLY")} onChange={(e) => updateRouteField("task_type", e.target.value)}>
              {["ANALYSIS", "REPLY", "EMBEDDING"].map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
            <input className="field" value={String(routeForm.strategy ?? "")} onChange={(e) => updateRouteField("strategy", e.target.value)} placeholder="strategy or empty" />
            <select className="field" value={String(routeForm.preferred_provider_id ?? "")} onChange={(e) => updateRouteField("preferred_provider_id", e.target.value)}>
              <option value="">Preferred Provider</option>
              {(providers.data ?? []).map((provider) => <option key={provider.id} value={provider.id}>{provider.provider_name}</option>)}
            </select>
            <select className="field" value={String(routeForm.fallback_provider_id ?? "")} onChange={(e) => updateRouteField("fallback_provider_id", e.target.value)}>
              <option value="">Fallback Provider</option>
              {(providers.data ?? []).map((provider) => <option key={provider.id} value={provider.id}>{provider.provider_name}</option>)}
            </select>
            <input className="field" type="number" value={String(routeForm.min_commercial_score ?? 0)} onChange={(e) => updateRouteField("min_commercial_score", Number(e.target.value))} placeholder="min commercial" />
            <input className="field" type="number" value={String(routeForm.max_risk_score ?? 100)} onChange={(e) => updateRouteField("max_risk_score", Number(e.target.value))} placeholder="max risk" />
            <input className="field" type="number" value={String(routeForm.priority ?? 100)} onChange={(e) => updateRouteField("priority", Number(e.target.value))} placeholder="priority" />
            <label className="flex items-center gap-2 rounded border border-line px-3 text-sm"><input type="checkbox" checked={Boolean(routeForm.enabled)} onChange={(e) => updateRouteField("enabled", e.target.checked)} />Enabled</label>
          </div>
          <div className="panel mt-3 overflow-x-auto">
            <table className="w-full min-w-[980px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Name", "Platform", "Task", "Strategy", "Scores", "Preferred", "Fallback", "Priority", "Status"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(providerRoutes.data ?? []).map((route) => (
                <tr key={String(route.uuid)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-semibold">{String(route.name)}</td>
                  <td className="px-4 py-3">{String(route.platform ?? "any")}</td>
                  <td className="px-4 py-3">{String(route.task_type)}</td>
                  <td className="px-4 py-3">{String(route.strategy ?? "any")}</td>
                  <td className="px-4 py-3 text-xs">{String(route.min_commercial_score)} / {String(route.max_risk_score)}</td>
                  <td className="px-4 py-3">{String(route.preferred_provider ?? "—")}</td>
                  <td className="px-4 py-3">{String(route.fallback_provider ?? "—")}</td>
                  <td className="px-4 py-3">{String(route.priority)}</td>
                  <td className="px-4 py-3"><StatusBadge value={route.enabled ? "ACTIVE" : "DISABLED"} /></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
        <Section
          title="Prompt Templates"
          action={<button className="button" onClick={createPromptTemplate}><Settings className="h-4 w-4" />新增 Template</button>}
        >
          <div className="panel grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-5">
            <input className="field" value={String(templateForm.name ?? "")} onChange={(e) => updateTemplateField("name", e.target.value)} placeholder="name" />
            <select className="field" value={String(templateForm.template_type ?? "reply_prompt")} onChange={(e) => updateTemplateField("template_type", e.target.value)}>
              {["analysis_prompt", "reply_prompt"].map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
            <input className="field" value={String(templateForm.platform ?? "")} onChange={(e) => updateTemplateField("platform", e.target.value)} placeholder="platform" />
            <input className="field" value={String(templateForm.strategy ?? "")} onChange={(e) => updateTemplateField("strategy", e.target.value)} placeholder="strategy" />
            <input className="field" value={String(templateForm.tone ?? "")} onChange={(e) => updateTemplateField("tone", e.target.value)} placeholder="tone" />
            <textarea className="field min-h-28 md:col-span-2 xl:col-span-5" value={String(templateForm.content ?? "")} onChange={(e) => updateTemplateField("content", e.target.value)} />
          </div>
          <div className="panel mt-3 overflow-x-auto">
            <table className="w-full min-w-[840px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Name", "Type", "Platform", "Strategy", "Tone", "Version", "Enabled"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(promptTemplates.data ?? []).map((template) => (
                <tr key={String(template.uuid)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-semibold">{String(template.name)}</td>
                  <td className="px-4 py-3">{String(template.template_type)}</td>
                  <td className="px-4 py-3">{String(template.platform ?? "any")}</td>
                  <td className="px-4 py-3">{String(template.strategy ?? "any")}</td>
                  <td className="px-4 py-3">{String(template.tone ?? "any")}</td>
                  <td className="px-4 py-3">{String(template.version)}</td>
                  <td className="px-4 py-3"><StatusBadge value={template.enabled ? "ACTIVE" : "DISABLED"} /></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
        <Section
          title="Prompt Versions"
          action={<button className="button" onClick={createPromptVersion}><Settings className="h-4 w-4" />新增 Version</button>}
        >
          <div className="panel grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-5">
            <select className="field" value={String(versionForm.prompt_template_id ?? "")} onChange={(e) => updateVersionField("prompt_template_id", e.target.value)}>
              <option value="">Prompt Template</option>
              {(promptTemplates.data ?? []).map((template) => <option key={String(template.id)} value={String(template.id)}>{String(template.name)}</option>)}
            </select>
            <input className="field" value={String(versionForm.version ?? "v1")} onChange={(e) => updateVersionField("version", e.target.value)} placeholder="version" />
            <input className="field" value={String(versionForm.platform ?? "")} onChange={(e) => updateVersionField("platform", e.target.value)} placeholder="platform" />
            <input className="field" value={String(versionForm.strategy ?? "")} onChange={(e) => updateVersionField("strategy", e.target.value)} placeholder="strategy" />
            <input className="field" value={String(versionForm.tone ?? "")} onChange={(e) => updateVersionField("tone", e.target.value)} placeholder="tone" />
            <textarea className="field min-h-28 md:col-span-2 xl:col-span-5" value={String(versionForm.content ?? "")} onChange={(e) => updateVersionField("content", e.target.value)} placeholder="prompt content" />
            <label className="flex items-center gap-2 rounded border border-line px-3 text-sm"><input type="checkbox" checked={Boolean(versionForm.is_default)} onChange={(e) => updateVersionField("is_default", e.target.checked)} />Default</label>
          </div>
          <div className="panel mt-3 overflow-x-auto">
            <table className="w-full min-w-[920px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Template", "Type", "Version", "Platform", "Strategy", "Tone", "Default", "Enabled"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(promptVersions.data ?? []).map((version) => (
                <tr key={String(version.uuid)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-semibold">{String(version.template_name ?? version.prompt_template_id)}</td>
                  <td className="px-4 py-3">{String(version.template_type ?? "—")}</td>
                  <td className="px-4 py-3">{String(version.version)}</td>
                  <td className="px-4 py-3">{String(version.platform ?? "any")}</td>
                  <td className="px-4 py-3">{String(version.strategy ?? "any")}</td>
                  <td className="px-4 py-3">{String(version.tone ?? "any")}</td>
                  <td className="px-4 py-3">{String(version.is_default)}</td>
                  <td className="px-4 py-3"><StatusBadge value={version.enabled ? "ACTIVE" : "DISABLED"} /></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
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
      </div>
    </StateView>
  );
}

function ExecutionPage() {
  const { data, error, loading, reload } =
    useApiData<RecordItem[]>("/execution/tasks");
  const runtime = useApiData<RecordItem>("/execution/runtime");
  const workers = useApiData<RecordItem[]>("/execution/workers");
  const counts = (data ?? []).reduce<Record<string, number>>((result, task) => {
    const status = String(task.status);
    result[status] = (result[status] ?? 0) + 1;
    return result;
  }, {});
  const [feedback, setFeedback] = useState("");

  async function executionAction(taskId: unknown, action: "precheck" | "mark-success" | "mark-failed" | "run-open-page" | "attach" | "close-tab" | "prepare-reply" | "mark-submitted" | "retry-fill" | "run-runtime" | "resume") {
    try {
      await apiRequest(`/execution/tasks/${String(taskId)}/${action}`, { method: "POST" });
      setFeedback(
        action === "precheck"
          ? "Precheck 已完成。"
          : action === "prepare-reply"
            ? "回复已填入，等待人工提交。"
            : action === "mark-submitted"
              ? "已确认人工提交并关闭当前 Tab。"
              : action === "retry-fill"
                ? "已重新执行填充。"
                : action === "run-open-page"
                  ? "OPEN_PAGE 执行链已完成。"
                  : action === "attach"
                    ? "Attach 已完成。"
                    : action === "close-tab"
                      ? "Tab 已关闭。"
                      : action === "mark-success"
                        ? "已标记成功。"
                        : "已标记失败。",
      );
      await reload();
      await runtime.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Execution 操作失败");
    }
  }

  async function runtimeAction(action: "claim-next" | "retry" | "cancel", taskId?: unknown) {
    try {
      if (action === "claim-next") {
        await apiRequest("/execution/claim-next", { method: "POST" });
        setFeedback("Local Worker 已 Claim 下一条队列任务。");
      } else {
        await apiRequest(`/execution/${action}`, {
          method: "POST",
          body: JSON.stringify({ task_id: Number(taskId) }),
        });
        setFeedback(action === "retry" ? "任务已重新入队。" : "任务已取消。");
      }
      await reload();
      await runtime.reload();
      await workers.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Runtime 操作失败");
    }
  }

  const groups = [
    ["队列", ["NEW", "QUEUED"]],
    ["已领取/运行中", ["CLAIMED", "RUNNING", "RECEIVED", "PRECHECKING", "ATTACHING", "PAGE_OPENING", "FINDING_REPLY_BOX", "FILLING_REPLY"]],
    ["已填充", ["ENVIRONMENT_READY", "REPLY_BOX_FOUND", "REPLY_FILLED"]],
    ["等待人工", ["WAITING_MANUAL", "MANUAL_SUBMITTED", "SUBMISSION_CONFIRMED"]],
    ["成功", ["SUCCESS", "TAB_CLOSED"]],
    ["失败", ["FAILED", "CANCELLED", "COMMENT_BOX_NOT_FOUND", "COMMENT_DISABLED", "LOGIN_REQUIRED", "RATE_LIMITED", "ATTACH_FAILED"]],
  ] as const;
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-6">
        <div className="panel flex items-start gap-4 p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-gray-100">
            <Play className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <h2 className="font-bold">Execution Runtime Status</h2>
            <p className="mt-1 text-sm text-gray-500">Sprint 02 建立独立 Execution Runtime、Queue、Worker 和状态流。本 Sprint 不打开浏览器、不执行 Playwright/TGE 动作。</p>
          </div>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <div className="panel flex flex-wrap items-center gap-3 p-4">
          <button className="button" onClick={() => void runtimeAction("claim-next")}><Bot className="h-4 w-4" />Claim Next</button>
          <span className="text-sm text-gray-500">Local Worker heartbeat: {String((workers.data ?? [])[0]?.last_heartbeat ?? "—")}</span>
        </div>
        <div className="grid gap-3 md:grid-cols-5">
          {([
            ["QUEUE", runtime.data?.queue ?? counts.QUEUED ?? 0],
            ["WORKER", runtime.data?.workers ?? workers.data?.length ?? 0],
            ["RUNNING", runtime.data?.running ?? counts.RUNNING ?? 0],
            ["WAITING_MANUAL", runtime.data?.waiting_manual ?? counts.WAITING_MANUAL ?? 0],
            ["SUCCESS", runtime.data?.success ?? counts.SUCCESS ?? 0],
          ] as Array<[string, unknown]>).map(([state, value]) => (
            <div key={state} className="panel p-4">
              <p className="text-xs font-semibold uppercase text-gray-500">{state}</p>
              <p className="mt-4 text-2xl font-bold">{String(value)}</p>
              <p className="mt-1 text-xs text-gray-400">Execution Runtime</p>
            </div>
          ))}
        </div>
        {groups.map(([title, statuses]) => {
          const rows = (data ?? []).filter((task) => (statuses as readonly string[]).includes(String(task.status)));
          return (
            <Section key={title} title={`${title} · ${rows.length}`}>
              <div className="panel overflow-x-auto">
                <table className="w-full min-w-[1180px] border-collapse text-left text-sm">
                  <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                    {["task_id", "platform", "account", "queue_status", "execution_status", "worker", "scheduler_status", "action_type", "retry", "created_at", "error_message", "actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
                  </tr></thead>
                  <tbody>{rows.map((task) => (
                    <tr key={String(task.uuid)} className="border-b border-line last:border-0">
                      <td className="px-4 py-3 font-mono text-xs">{String(task.task_id ?? task.id)}</td>
                      <td className="px-4 py-3 uppercase text-teal">{String(task.platform ?? "—")}</td>
                      <td className="px-4 py-3">{String(task.account ?? "—")}</td>
                      <td className="px-4 py-3"><StatusBadge value={task.queue_status ?? "—"} /></td>
                      <td className="px-4 py-3"><StatusBadge value={task.execution_status ?? task.status} /></td>
                      <td className="px-4 py-3 font-mono text-xs">{String(task.worker_node_id ?? "—")}</td>
                      <td className="px-4 py-3"><StatusBadge value={task.scheduler_status ?? "—"} /></td>
                      <td className="px-4 py-3">{String(task.action_type ?? "—")}</td>
                      <td className="px-4 py-3">{String(task.retry_count ?? 0)}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{task.created_at ? new Date(String(task.created_at)).toLocaleString() : "—"}</td>
                      <td className="max-w-xs px-4 py-3 text-xs text-red-600">{String(task.error_message ?? "—")}</td>
                      <td className="px-4 py-3"><div className="flex flex-wrap gap-2">
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "run-runtime")}>Run</button>
                        <button className="button-secondary" onClick={() => void runtimeAction("retry", task.id)}>Retry</button>
                        <button className="button-secondary" onClick={() => void runtimeAction("cancel", task.id)}>Cancel</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "resume")}>Resume</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "precheck")}>Precheck</button>
                        <button className="button" onClick={() => void executionAction(task.id, "prepare-reply")}>Prepare Reply</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "mark-submitted")}>Mark Submitted</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "retry-fill")}>Retry Fill</button>
                        <button className="button" onClick={() => void executionAction(task.id, "run-open-page")}>Run OPEN_PAGE</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "attach")}>Attach</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "close-tab")}>Close Tab</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "mark-success")}>Success</button>
                        <button className="button-secondary" onClick={() => void executionAction(task.id, "mark-failed")}>Failed</button>
                      </div></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </Section>
          );
        })}
        <Section title="Replay 占位">
          <div className="panel p-5 text-sm text-gray-600">Replay files are available after OPEN_PAGE or PREPARE_REPLY runs. v0.8 can save before/after fill screenshots and HTML snapshots, but it never clicks submit.</div>
        </Section>
        {(data ?? []).some((task) => task.status === "WAITING_MANUAL") && (
          <div className="panel border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
            回复内容已填入浏览器，请在平台页面人工确认并点击提交。提交后回到 ATOS 点击 Mark Submitted。
          </div>
        )}
      </div>
    </StateView>
  );
}

function SubmissionPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/submission-tasks");
  const dashboard = useApiData<RecordItem>("/submission/dashboard");
  const logs = useApiData<RecordItem[]>("/submission/logs");
  const stats = useApiData<RecordItem[]>("/submission-stats");
  const [feedback, setFeedback] = useState("");

  async function submissionAction(taskId: unknown, action: "submit" | "run-auto" | "confirm" | "cancel" | "retry" | "mark-failed") {
    try {
      if (action === "mark-failed") {
        const failureReason = window.prompt("请输入失败原因，例如 LOGIN_REQUIRED / REPLY_BOX_NOT_FOUND / UNKNOWN_ERROR");
        if (!failureReason) return;
        await apiRequest(`/submission-tasks/${String(taskId)}/mark-failed`, {
          method: "POST",
          body: JSON.stringify({ failure_reason: failureReason }),
        });
      } else if (action === "submit") {
        await apiRequest(`/submission/tasks/${String(taskId)}/submit`, { method: "POST" });
      } else if (action === "run-auto") {
        await apiRequest(`/submission-tasks/${String(taskId)}/run-auto-assisted`, { method: "POST" });
      } else {
        await apiRequest(`/submission-tasks/${String(taskId)}/${action}`, { method: "POST" });
      }
      setFeedback(
        action === "submit"
          ? "Submission policy 已评估。默认 SEMI_AUTO 不会自动提交。"
          : action === "run-auto"
            ? "AUTO_ASSISTED 已执行策略检查；未满足条件会回退人工。"
          : action === "confirm"
            ? "人工提交结果已记录。"
            : action === "retry"
              ? "Retry 已评估。"
              : action === "mark-failed"
                ? "任务已标记失败。"
                : "Submission task 已取消。",
      );
      await reload();
      await dashboard.reload();
      await logs.reload();
      await stats.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Submission 操作失败");
    }
  }

  const cards = [
    ["Ready", dashboard.data?.submission_ready ?? 0, CheckCircle2, "text-emerald-700"],
    ["Waiting Manual", dashboard.data?.submission_waiting_manual ?? 0, FileClock, "text-amber"],
    ["Submitting", dashboard.data?.submission_submitting ?? 0, Play, "text-blue-700"],
    ["Verified", dashboard.data?.submission_verified ?? 0, ShieldCheck, "text-emerald-700"],
    ["Failed", dashboard.data?.submission_failed ?? 0, CircleAlert, "text-red-700"],
    ["Manual Required", dashboard.data?.submission_manual_required ?? 0, Users, "text-amber"],
    ["Auto Completed", dashboard.data?.auto_assisted_completed ?? 0, ShieldCheck, "text-emerald-700"],
    ["Manual Review", dashboard.data?.auto_assisted_manual_review ?? 0, CircleAlert, "text-amber"],
  ] as const;

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-6">
        <div className="panel flex items-start gap-4 p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-gray-100">
            <CheckCircle2 className="h-5 w-5 text-emerald-700" />
          </div>
          <div>
            <h2 className="font-bold">Submission Runtime</h2>
            <p className="mt-1 text-sm text-gray-500">
              Submission 与 Fill Reply 分离。默认 SEMI_AUTO：ATOS 只记录人工确认和验证结果，不自动点击提交。
            </p>
          </div>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map(([label, value, Icon, tone]) => (
            <div key={label} className="panel p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold uppercase text-gray-500">{label}</p>
                <Icon className={`h-5 w-5 ${tone}`} />
              </div>
              <p className="mt-4 text-2xl font-bold">{String(value)}</p>
            </div>
          ))}
        </div>
        <Section title="Submission Tasks">
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1280px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                  {["id", "platform", "account", "mode", "status", "policy", "verify", "reply", "tab", "result", "failure", "retry", "actions"].map((label) => (
                    <th key={label} className="px-4 py-3 font-semibold">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data ?? []).map((task) => (
                  <tr key={String(task.uuid)} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-mono text-xs">{String(task.id)}</td>
                    <td className="px-4 py-3 uppercase text-teal">{String(task.platform ?? "—")}</td>
                    <td className="px-4 py-3">{String(task.account ?? "—")}</td>
                    <td className="px-4 py-3">{String(task.execution_mode)}</td>
                    <td className="px-4 py-3"><StatusBadge value={task.status} /></td>
                    <td className="max-w-xs px-4 py-3 text-xs text-gray-500">
                      {((task.policy_check as RecordItem | undefined)?.blocked) ? String((task.policy_check as RecordItem).reason ?? "BLOCKED") : "PASS"}
                    </td>
                    <td className="px-4 py-3 text-xs">{String(task.verification_status ?? task.verification_level ?? "NONE")}</td>
                    <td className="max-w-sm px-4 py-3 text-xs text-gray-600">{String(task.reply_content_preview ?? "—")}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">S {String(task.browser_session_id ?? "—")} / T {String(task.browser_tab_id ?? "—")}</td>
                    <td className="max-w-xs px-4 py-3 text-xs text-blue-700">{String(task.result_url ?? "—")}</td>
                    <td className="max-w-xs px-4 py-3 text-xs text-red-600">{String(task.error_code ?? task.failure_reason ?? "—")}</td>
                    <td className="max-w-xs px-4 py-3 text-xs text-gray-500">{task.retryable ? `可重试 · ${String(task.retry_count ?? 0)}` : String(task.retry_blocked_reason ?? "不可重试")}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button className="button-secondary" onClick={() => void submissionAction(task.id, "submit")}>Policy Check</button>
                        <button className="button-secondary" onClick={() => void submissionAction(task.id, "run-auto")}>Run AUTO_ASSISTED Now</button>
                        <button className="button" onClick={() => void submissionAction(task.id, "confirm")}>Confirm Submitted</button>
                        <button className="button-secondary" onClick={() => void submissionAction(task.id, "mark-failed")}>Mark Failed</button>
                        <button className="button-secondary" onClick={() => void submissionAction(task.id, "retry")} disabled={!task.retryable}>Retry</button>
                        <button className="button-secondary" onClick={() => void submissionAction(task.id, "cancel")}>Cancel</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
        <Section title="Submission Statistics">
          <DataTable
            rows={stats.data ?? []}
            columns={[
              { key: "platform", label: "Platform" },
              { key: "filled_count", label: "Filled" },
              { key: "manual_confirmed_count", label: "Manual Confirmed" },
              { key: "verified_count", label: "Verified" },
              { key: "failed_count", label: "Failed" },
              { key: "manual_required_count", label: "Manual Required" },
              { key: "auto_submit_attempts", label: "Auto Attempts" },
              { key: "auto_submit_success", label: "Auto Success" },
              { key: "manual_fallback", label: "Manual Fallback" },
              { key: "policy_blocked", label: "Policy Blocked" },
              { key: "retry_count", label: "Retry" },
              { key: "success_rate", label: "Success %" },
              { key: "fallback_rate", label: "Fallback %" },
              { key: "failure_rate", label: "Failure %" },
            ]}
          />
        </Section>
        <Section title="Recent Submission Timeline">
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                  {["task", "step", "level", "message", "created"].map((label) => (
                    <th key={label} className="px-4 py-3 font-semibold">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(logs.data ?? []).slice(0, 20).map((log) => (
                  <tr key={String(log.uuid)} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-mono text-xs">{String(log.submission_task_id)}</td>
                    <td className="px-4 py-3">{String(log.step)}</td>
                    <td className="px-4 py-3"><StatusBadge value={log.level} /></td>
                    <td className="px-4 py-3 text-xs text-gray-600">{String(log.message ?? "—")}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{log.created_at ? new Date(String(log.created_at)).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </div>
    </StateView>
  );
}

function EngagementPage() {
  const strategies = useApiData<RecordItem[]>("/engagement/strategies");
  const tasks = useApiData<RecordItem[]>("/engagement/tasks");
  const accounts = useApiData<RecordItem[]>("/accounts");
  const stats = useApiData<RecordItem[]>("/engagement/statistics");
  const [feedback, setFeedback] = useState("");
  const [strategyForm, setStrategyForm] = useState<Record<string, unknown>>({
    name: "Reddit Mixed Engagement",
    platform: "reddit",
    strategy_type: "MIXED_ENGAGEMENT",
    browse_count_min: 2,
    browse_count_max: 4,
    like_count_min: 1,
    like_count_max: 2,
    visit_profile_count_min: 0,
    visit_profile_count_max: 1,
    pause_min_seconds: 5,
    pause_max_seconds: 30,
    before_reply_enabled: false,
    weight: 10,
    remark: "",
  });
  const [taskForm, setTaskForm] = useState<Record<string, unknown>>({
    strategy_id: "",
    account_id: "",
    platform: "reddit",
    source_type: "POST_POOL",
    source_value: "",
    browse_target_count: 3,
    like_target_count: 1,
    visit_profile_target_count: 0,
    priority: "MEDIUM",
  });

  function updateStrategy(key: string, value: unknown) {
    setStrategyForm((current) => ({ ...current, [key]: value }));
  }

  function updateTask(key: string, value: unknown) {
    setTaskForm((current) => ({ ...current, [key]: value }));
  }

  async function createStrategy() {
    try {
      await apiRequest("/engagement/strategies", {
        method: "POST",
        body: JSON.stringify(strategyForm),
      });
      setFeedback("Engagement Strategy 已创建。");
      await strategies.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "创建 Strategy 失败");
    }
  }

  async function createTask() {
    try {
      await apiRequest("/engagement/tasks", {
        method: "POST",
        body: JSON.stringify({
          ...taskForm,
          strategy_id: taskForm.strategy_id ? Number(taskForm.strategy_id) : null,
          account_id: taskForm.account_id ? Number(taskForm.account_id) : null,
          browse_target_count: Number(taskForm.browse_target_count ?? 0),
          like_target_count: Number(taskForm.like_target_count ?? 0),
          visit_profile_target_count: Number(taskForm.visit_profile_target_count ?? 0),
        }),
      });
      setFeedback("Engagement Task 已加入 Scheduler。");
      await tasks.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "创建 Task 失败");
    }
  }

  async function taskAction(taskId: unknown, action: "run-mock" | "cancel" | "retry") {
    try {
      await apiRequest(`/engagement/tasks/${String(taskId)}/${action}`, { method: "POST" });
      setFeedback(action === "run-mock" ? "Mock Engagement 已执行。" : action === "cancel" ? "任务已取消。" : "任务已重试。");
      await tasks.reload();
      await stats.reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "操作失败");
    }
  }

  return (
    <StateView loading={strategies.loading || tasks.loading} error={strategies.error || tasks.error} reload={() => { void strategies.reload(); void tasks.reload(); }}>
      <div className="space-y-6">
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section title="Create Strategy" action={<button className="button" onClick={createStrategy}><Activity className="h-4 w-4" />保存 Strategy</button>}>
          <div className="panel grid gap-3 p-4 md:grid-cols-3 xl:grid-cols-6">
            <input className="field" value={String(strategyForm.name)} onChange={(e) => updateStrategy("name", e.target.value)} />
            <input className="field" value={String(strategyForm.platform)} onChange={(e) => updateStrategy("platform", e.target.value)} />
            <select className="field" value={String(strategyForm.strategy_type)} onChange={(e) => updateStrategy("strategy_type", e.target.value)}>
              {["SILENT_BROWSE", "LIKE_ONLY", "PROFILE_VISIT", "MIXED_ENGAGEMENT", "REPLY_WARMUP", "CUSTOM"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <input className="field" type="number" value={String(strategyForm.browse_count_min)} onChange={(e) => updateStrategy("browse_count_min", Number(e.target.value))} />
            <input className="field" type="number" value={String(strategyForm.like_count_min)} onChange={(e) => updateStrategy("like_count_min", Number(e.target.value))} />
            <label className="flex items-center gap-2 rounded border border-line px-3 text-sm"><input type="checkbox" checked={Boolean(strategyForm.before_reply_enabled)} onChange={(e) => updateStrategy("before_reply_enabled", e.target.checked)} />Reply Warm-up</label>
          </div>
        </Section>
        <Section title="Create Engagement Task" action={<button className="button" onClick={createTask}><CalendarClock className="h-4 w-4" />加入 Scheduler</button>}>
          <div className="panel grid gap-3 p-4 md:grid-cols-3 xl:grid-cols-7">
            <select className="field" value={String(taskForm.strategy_id)} onChange={(e) => updateTask("strategy_id", e.target.value)}>
              <option value="">Custom</option>
              {(strategies.data ?? []).map((strategy) => <option key={String(strategy.id)} value={String(strategy.id)}>{String(strategy.name)}</option>)}
            </select>
            <select className="field" value={String(taskForm.account_id)} onChange={(e) => updateTask("account_id", e.target.value)}>
              <option value="">自动选择账号</option>
              {(accounts.data ?? []).map((account) => <option key={String(account.id)} value={String(account.id)}>{String(account.platform)} · {String(account.username)}</option>)}
            </select>
            <select className="field" value={String(taskForm.source_type)} onChange={(e) => updateTask("source_type", e.target.value)}>
              {["KEYWORD", "COMMUNITY", "URL_LIST", "POST_POOL", "AUTHOR_PROFILE", "MIXED"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <input className="field" value={String(taskForm.source_value ?? "")} onChange={(e) => updateTask("source_value", e.target.value)} placeholder="source value" />
            <input className="field" type="number" value={String(taskForm.browse_target_count)} onChange={(e) => updateTask("browse_target_count", Number(e.target.value))} />
            <input className="field" type="number" value={String(taskForm.like_target_count)} onChange={(e) => updateTask("like_target_count", Number(e.target.value))} />
            <input className="field" type="number" value={String(taskForm.visit_profile_target_count)} onChange={(e) => updateTask("visit_profile_target_count", Number(e.target.value))} />
          </div>
        </Section>
        <Section title="Engagement Queue">
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1100px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["id", "strategy", "account", "platform", "status", "browse", "like", "profile", "source", "actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(tasks.data ?? []).map((task) => (
                <tr key={String(task.id)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-mono text-xs">{String(task.id)}</td>
                  <td className="px-4 py-3">{String(task.strategy_name ?? task.strategy_type ?? "CUSTOM")}</td>
                  <td className="px-4 py-3">{String(task.account ?? "—")}</td>
                  <td className="px-4 py-3 uppercase text-teal">{String(task.platform)}</td>
                  <td className="px-4 py-3"><StatusBadge value={task.status} /></td>
                  <td className="px-4 py-3">{String(task.browse_done_count ?? 0)} / {String(task.browse_target_count ?? 0)}</td>
                  <td className="px-4 py-3">{String(task.like_done_count ?? 0)} / {String(task.like_target_count ?? 0)}</td>
                  <td className="px-4 py-3">{String(task.visit_profile_done_count ?? 0)} / {String(task.visit_profile_target_count ?? 0)}</td>
                  <td className="px-4 py-3">{String(task.source_type)} · {String(task.source_value ?? "")}</td>
                  <td className="px-4 py-3"><div className="flex flex-wrap gap-2">
                    <button className="button-secondary" onClick={() => void taskAction(task.id, "run-mock")}>Run Mock</button>
                    <button className="button-secondary" onClick={() => void taskAction(task.id, "retry")}>Retry</button>
                    <button className="button-secondary" onClick={() => void taskAction(task.id, "cancel")}>Cancel</button>
                  </div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
        <Section title="Engagement Statistics">
          <pre className="panel overflow-x-auto p-4 text-xs text-gray-600">{JSON.stringify(stats.data ?? [], null, 2)}</pre>
        </Section>
      </div>
    </StateView>
  );
}

function StatisticsPage() {
  const { data, error, loading, reload } =
    useApiData<RecordItem[]>("/statistics");
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(data ?? []).map((item) => (
            <div key={String(item.uuid)} className="panel p-4">
              <p className="text-xs font-semibold uppercase text-gray-500">
                {String(item.metric).replace(/_/g, " ")}
              </p>
              <p className="mt-4 text-3xl font-bold">{String(item.value)}</p>
              <p className="mt-1 text-xs text-gray-400">
                {String(item.dimension)} · {String(item.period)}
              </p>
            </div>
          ))}
        </div>
        <div className="panel flex items-start gap-3 p-4 text-sm text-gray-600">
          <ChartNoAxesCombined className="h-5 w-5 shrink-0 text-cyan" />
          当前展示 Seed 统计快照。事件总线与实时聚合将在后续版本接入。
        </div>
      </div>
    </StateView>
  );
}

function PlatformCenterPage() {
  const overview = useApiData<RecordItem>("/platform-runtime");
  const health = useApiData<RecordItem[]>("/platform-runtime/health");
  const statistics = useApiData<RecordItem>("/platform-runtime/statistics");
  const [platform, setPlatform] = useState("reddit");
  const [actionType, setActionType] = useState("PREPARE_REPLY");
  const [checkResult, setCheckResult] = useState<RecordItem | null>(null);
  const [checking, setChecking] = useState(false);

  const discovered = (overview.data?.discovered as RecordItem[] | undefined) ?? [];
  const registry = (overview.data?.registry as RecordItem[] | undefined) ?? [];
  const stats = statistics.data ?? {};

  async function runCapabilityCheck() {
    setChecking(true);
    try {
      setCheckResult(
        await apiRequest<RecordItem>("/platform-runtime/capability-check", {
          method: "POST",
          data: { platform, action_type: actionType },
        }),
      );
    } finally {
      setChecking(false);
    }
  }

  return (
    <StateView loading={overview.loading} error={overview.error} reload={overview.reload}>
      <div className="space-y-6">
        <Section
          title="Adapter Discovery"
          action={
            <button className="icon-button" title="刷新" onClick={overview.reload}>
              <RefreshCw className="h-4 w-4" />
            </button>
          }
        >
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {discovered.map((item) => (
              <div key={String(item.platform_name)} className="panel p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{String(item.platform_name)}</p>
                    <p className="text-xs text-gray-500">
                      {String(item.adapter_name)} · {String(item.version)}
                    </p>
                  </div>
                  <SlidersHorizontal className="h-5 w-5 text-teal" />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {((item.capabilities as string[] | undefined) ?? []).map((capability) => (
                    <span key={capability} className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-600">
                      {capability}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Section title="Platform Registry">
            <DataTable
              rows={registry}
              columns={[
                { key: "platform_name", label: "Platform" },
                { key: "adapter_name", label: "Adapter" },
                { key: "version", label: "Version" },
                { key: "status", label: "Status" },
                { key: "capability_list", label: "Capabilities" },
              ]}
            />
          </Section>

          <Section title="Capability Check">
            <div className="panel space-y-3 p-4">
              <label className="block text-xs font-semibold uppercase text-gray-500">Platform</label>
              <input className="input" value={platform} onChange={(event) => setPlatform(event.target.value)} />
              <label className="block text-xs font-semibold uppercase text-gray-500">Action Type</label>
              <input className="input" value={actionType} onChange={(event) => setActionType(event.target.value)} />
              <button className="button" onClick={runCapabilityCheck} disabled={checking}>
                <ShieldCheck className="h-4 w-4" />
                {checking ? "Checking..." : "Check Capability"}
              </button>
              {checkResult && (
                <pre className="overflow-x-auto rounded bg-gray-50 p-3 text-xs text-gray-600">
                  {JSON.stringify(checkResult, null, 2)}
                </pre>
              )}
            </div>
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Platform Health">
            <DataTable
              rows={health.data ?? []}
              columns={[
                { key: "platform", label: "Platform" },
                { key: "adapter_name", label: "Adapter" },
                { key: "status", label: "Status" },
                { key: "error_count", label: "Errors" },
                { key: "last_health_check_at", label: "Last Check" },
              ]}
            />
          </Section>
          <Section title="Platform Statistics">
            <pre className="panel overflow-x-auto p-4 text-xs text-gray-600">
              {JSON.stringify(stats, null, 2)}
            </pre>
          </Section>
        </div>
      </div>
    </StateView>
  );
}

function WorkerCenterPage() {
  const runtime = useApiData<RecordItem>("/automation/runtime");
  const workers = useApiData<RecordItem[]>("/automation/workers");
  const queue = useApiData<RecordItem[]>("/automation/queue");
  const alerts = useApiData<RecordItem[]>("/automation/alerts");
  const metrics = useApiData<RecordItem>("/automation/metrics");
  const [claimResult, setClaimResult] = useState<RecordItem | null>(null);
  const [claiming, setClaiming] = useState(false);

  async function claimNext() {
    setClaiming(true);
    try {
      const result = await apiRequest<RecordItem | null>("/automation/claim", {
        method: "POST",
        data: {},
      });
      setClaimResult(result ?? { message: "No eligible task" });
      await runtime.reload();
      await workers.reload();
      await queue.reload();
    } finally {
      setClaiming(false);
    }
  }

  const overview = runtime.data ?? {};
  const metricData = metrics.data ?? {};
  const runtimeCards = [
    { label: "Queue", value: overview.task_queue ?? 0, icon: FileClock, tone: "text-amber" },
    { label: "Online Workers", value: overview.online_workers ?? 0, icon: Bot, tone: "text-teal" },
    { label: "Running", value: overview.running_tasks ?? 0, icon: Activity, tone: "text-blue-700" },
    { label: "Failed", value: overview.failed_tasks ?? 0, icon: CircleAlert, tone: "text-red-700" },
    { label: "Retry Pending", value: overview.retry_pending ?? 0, icon: RefreshCw, tone: "text-blue-700" },
    { label: "Worker Lost", value: overview.worker_lost ?? 0, icon: CircleAlert, tone: "text-red-700" },
    { label: "Throughput", value: overview.throughput ?? 0, icon: CheckCircle2, tone: "text-emerald-700" },
    { label: "Failure Rate", value: `${overview.failure_rate ?? 0}%`, icon: HeartPulse, tone: "text-amber" },
  ];

  return (
    <StateView loading={runtime.loading} error={runtime.error} reload={runtime.reload}>
      <div className="space-y-6">
        <Section
          title="Automation Runtime"
          action={
            <button className="button-secondary" onClick={claimNext} disabled={claiming}>
              <Play className="h-4 w-4" />
              {claiming ? "Claiming..." : "Claim Next"}
            </button>
          }
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {runtimeCards.map((card) => (
              <div key={card.label} className="panel p-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase text-gray-500">{card.label}</p>
                  <card.icon className={`h-5 w-5 ${card.tone}`} />
                </div>
                <p className="mt-4 text-2xl font-bold">{String(card.value)}</p>
              </div>
            ))}
          </div>
          {claimResult && (
            <pre className="panel mt-4 overflow-x-auto p-4 text-xs text-gray-600">
              {JSON.stringify(claimResult, null, 2)}
            </pre>
          )}
        </Section>

        <Section title="Worker Pool">
          <DataTable
            rows={workers.data ?? []}
            columns={[
              { key: "name", label: "Worker" },
              { key: "worker_type", label: "Type" },
              { key: "status", label: "Status" },
              { key: "runtime_status", label: "Runtime" },
              { key: "current_tasks", label: "Current" },
              { key: "max_concurrent_tasks", label: "Max" },
              { key: "health_score", label: "Health" },
              { key: "region", label: "Region" },
            ]}
          />
        </Section>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Execution Queue">
            <DataTable
              rows={queue.data ?? []}
              columns={[
                { key: "execution_task_id", label: "Task" },
                { key: "priority", label: "Priority" },
                { key: "status", label: "Status" },
                { key: "worker_node_id", label: "Worker" },
                { key: "required_capability", label: "Capability" },
                { key: "lock_uuid", label: "Lock" },
              ]}
            />
          </Section>
          <Section title="Alerts">
            <DataTable
              rows={alerts.data ?? []}
              columns={[
                { key: "alert_type", label: "Type" },
                { key: "severity", label: "Severity" },
                { key: "status", label: "Status" },
                { key: "message", label: "Message" },
                { key: "created_at", label: "Created" },
              ]}
            />
          </Section>
        </div>

        <Section title="Runtime Metrics">
          <pre className="panel overflow-x-auto p-4 text-xs text-gray-600">
            {JSON.stringify(metricData, null, 2)}
          </pre>
        </Section>
      </div>
    </StateView>
  );
}

function IntelligencePage() {
  const dashboard = useApiData<RecordItem>("/intelligence/dashboard");
  const recommendations = useApiData<RecordItem[]>("/intelligence/recommendations");
  const performance = useApiData<RecordItem>("/intelligence/performance");
  const similarity = useApiData<RecordItem[]>("/intelligence/similarity");
  const [scoring, setScoring] = useState(false);

  async function checkSimilarity() {
    setScoring(true);
    try {
      await apiRequest<RecordItem[]>("/intelligence/similarity", {
        method: "POST",
        data: { threshold: 80 },
      });
      await similarity.reload();
      await dashboard.reload();
    } finally {
      setScoring(false);
    }
  }

  const data = dashboard.data ?? {};
  const funnel = (data.funnel as RecordItem | undefined) ?? {};
  const perf = performance.data ?? {};

  return (
    <StateView loading={dashboard.loading} error={dashboard.error} reload={dashboard.reload}>
      <div className="space-y-6">
        <Section
          title="Intelligence Overview"
          action={
            <button className="button-secondary" onClick={checkSimilarity} disabled={scoring}>
              <RefreshCw className="h-4 w-4" />
              {scoring ? "Checking..." : "Check Similarity"}
            </button>
          }
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            {["posts", "ai_generated", "approved", "executed", "engaged", "converted"].map((key) => (
              <div key={key} className="panel p-4">
                <p className="text-xs font-semibold uppercase text-gray-500">{key.replace(/_/g, " ")}</p>
                <p className="mt-4 text-2xl font-bold">{String(funnel[key] ?? 0)}</p>
              </div>
            ))}
          </div>
        </Section>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Top Strategies">
            <DataTable
              rows={(data.top_strategies as RecordItem[] | undefined) ?? []}
              columns={[
                { key: "strategy", label: "Strategy" },
                { key: "platform", label: "Platform" },
                { key: "success_rate", label: "Success" },
                { key: "average_score", label: "Score" },
              ]}
            />
          </Section>
          <Section title="Top Replies">
            <DataTable
              rows={(data.top_replies as RecordItem[] | undefined) ?? []}
              columns={[
                { key: "reply_id", label: "Reply" },
                { key: "relevance", label: "Relevance" },
                { key: "quality", label: "Quality" },
                { key: "score", label: "Score" },
              ]}
            />
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <Section title="Best Accounts">
            <DataTable
              rows={(data.best_accounts as RecordItem[] | undefined) ?? []}
              columns={[
                { key: "account_id", label: "Account" },
                { key: "platform", label: "Platform" },
                { key: "success", label: "Success" },
                { key: "average_score", label: "Score" },
              ]}
            />
          </Section>
          <Section title="Best Time">
            <DataTable
              rows={(data.best_time as RecordItem[] | undefined) ?? []}
              columns={[
                { key: "platform", label: "Platform" },
                { key: "day", label: "Day" },
                { key: "hour", label: "Hour" },
                { key: "success_rate", label: "Success" },
              ]}
            />
          </Section>
          <Section title="Platform Ranking">
            <DataTable
              rows={(data.platform_ranking as RecordItem[] | undefined) ?? []}
              columns={[
                { key: "platform", label: "Platform" },
                { key: "success_rate", label: "Success" },
                { key: "reply_rate", label: "Reply" },
                { key: "average_score", label: "Score" },
              ]}
            />
          </Section>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section title="Recommendations">
            <DataTable
              rows={recommendations.data ?? []}
              columns={[
                { key: "recommendation_type", label: "Type" },
                { key: "title", label: "Title" },
                { key: "priority", label: "Priority" },
                { key: "score", label: "Score" },
              ]}
            />
          </Section>
          <Section title="Duplicate Reply Detection">
            <DataTable
              rows={similarity.data ?? []}
              columns={[
                { key: "reply_id", label: "Reply" },
                { key: "compared_reply_id", label: "Compared" },
                { key: "similarity_score", label: "Similarity" },
                { key: "method", label: "Method" },
              ]}
            />
          </Section>
        </div>

        <Section title="Performance Detail">
          <pre className="panel overflow-x-auto p-4 text-xs text-gray-600">
            {JSON.stringify(perf, null, 2)}
          </pre>
        </Section>
      </div>
    </StateView>
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
    case "platform-center":
      return <PlatformCenterPage />;
    case "worker-center":
      return <WorkerCenterPage />;
    case "intelligence":
      return <IntelligencePage />;
    case "account-center":
      return <AccountCenterPage />;
    case "settings":
      return <SettingsPage />;
    case "execution":
      return <ExecutionPage />;
    case "submission":
      return <SubmissionPage />;
    case "engagement":
      return <EngagementPage />;
    case "statistics":
      return <StatisticsPage />;
  }
}

function PermissionGuard({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const location = useLocation();
  const routerNavigate = useNavigate();
  const page = routePages[location.pathname] ?? "dashboard";
  const current = pageMeta[page];
  const currentNav = useMemo(() => navigation.find((item) => item.key === page), [page]);

  function navigate(next: PageKey) {
    routerNavigate(pageRoutes[next]);
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
            <p className="text-[10px] uppercase text-gray-500">Local Console v1.2</p>
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
          <Routes>
            {navigation.map((item) => (
              <Route
                key={item.key}
                path={pageRoutes[item.key]}
                element={
                  <PermissionGuard>
                    <PageContent page={item.key} />
                  </PermissionGuard>
                }
              />
            ))}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
