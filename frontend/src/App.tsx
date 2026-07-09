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
import { apiGet, apiRequest } from "./api";

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
  const { data, error, loading, reload } = useApiData<DataSourceItem[]>("/data-sources");
  const platforms = useApiData<PlatformOption[]>("/data-sources/platforms");
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
      </div>
    </StateView>
  );
}

function PostPoolPage() {
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busyPostId, setBusyPostId] = useState<number | null>(null);
  const sources = useApiData<DataSourceItem[]>("/data-sources");
  const query = new URLSearchParams();
  if (platform) query.set("platform", platform);
  if (status) query.set("status", status);
  if (sourceId) query.set("source_id", sourceId);
  const { data, error, loading, reload } = useApiData<RecordItem[]>(
    `/posts${query.size ? `?${query.toString()}` : ""}`,
  );

  async function runPostAction(post: RecordItem, action: "analyze" | "reply" | "workspace") {
    const postId = Number(post.id);
    setBusyPostId(postId);
    setFeedback("");
    try {
      if (action === "reply") {
        await apiRequest(`/ai/tasks/${postId}/generate-reply`, {
          method: "POST",
          body: JSON.stringify({
            strategy: "PURE_HELP",
            tone: "supportive",
            variables: {},
          }),
        });
        setFeedback("回复草稿已生成，可到 AI Workspace 审核。");
      } else {
        await apiRequest(`/ai/tasks/${postId}/analyze`, { method: "POST" });
        setFeedback(
          action === "workspace"
            ? "帖子已送入 AI Workspace 并完成初步分析。"
            : "帖子已完成 AI 分析。",
        );
      }
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "AI 操作失败");
    } finally {
      setBusyPostId(null);
    }
  }

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-4">
        <div className="panel flex flex-wrap items-end gap-3 p-4">
          <SlidersHorizontal className="mb-2 h-5 w-5 text-gray-500" />
          <label className="text-xs font-semibold text-gray-600">Platform<select className="field mt-2 min-w-36" value={platform} onChange={(e) => setPlatform(e.target.value)}><option value="">All</option>{Array.from(new Set((sources.data ?? []).map((item) => item.platform).filter(Boolean))).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label className="text-xs font-semibold text-gray-600">Source<select className="field mt-2 min-w-48" value={sourceId} onChange={(e) => setSourceId(e.target.value)}><option value="">All</option>{(sources.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className="text-xs font-semibold text-gray-600">Status<select className="field mt-2 min-w-36" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All</option><option value="NEW">NEW</option><option value="ANALYZED">ANALYZED</option><option value="ARCHIVED">ARCHIVED</option></select></label>
          <button className="icon-button mb-0.5" title="刷新" onClick={reload}><RefreshCw className="h-4 w-4" /></button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section title={`Unified Post Pool · ${data?.length ?? 0}`}>
          <div className="panel overflow-x-auto">
            <table className="w-full min-w-[1380px] border-collapse text-left text-sm">
              <thead><tr className="border-b border-line bg-gray-50 text-xs uppercase text-gray-500">
                {["Platform", "Title", "Author", "Community", "Published", "Imported", "Source", "URL", "AI Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
              </tr></thead>
              <tbody>{(data ?? []).map((post, index) => (
                <tr key={String(post.uuid ?? index)} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-semibold uppercase text-teal">{String(post.platform ?? "—")}</td>
                  <td className="max-w-sm px-4 py-3"><p className="line-clamp-2 font-medium">{String(post.title || "(Untitled)")}</p></td>
                  <td className="px-4 py-3 text-gray-600">{String(post.author ?? "—")}</td>
                  <td className="px-4 py-3 text-gray-600">{String(post.community ?? "—")}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{post.published_at ? new Date(String(post.published_at)).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{post.created_at ? new Date(String(post.created_at)).toLocaleString() : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{String(post.source ?? "Seed / Manual")}</td>
                  <td className="px-4 py-3">{post.url ? <a className="inline-flex items-center gap-1 text-cyan hover:underline" href={String(post.url)} target="_blank" rel="noreferrer">Open<ExternalLink className="h-3.5 w-3.5" /></a> : "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button className="button-secondary" disabled={busyPostId === post.id} onClick={() => void runPostAction(post, "analyze")}>Analyze</button>
                      <button className="button-secondary" disabled={busyPostId === post.id} onClick={() => void runPostAction(post, "reply")}>Generate Reply</button>
                      <button className="button" disabled={busyPostId === post.id} onClick={() => void runPostAction(post, "workspace")}><BrainCircuit className="h-4 w-4" />Send</button>
                    </div>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </Section>
      </div>
    </StateView>
  );
}

function AIWorkspacePage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/ai/tasks");
  const posts = useApiData<RecordItem[]>("/posts");
  const [postId, setPostId] = useState("1");
  const [strategy, setStrategy] = useState("PURE_HELP");
  const [tone, setTone] = useState("supportive");
  const [feedback, setFeedback] = useState("");
  const [draftEdits, setDraftEdits] = useState<Record<string, string>>({});

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
        body: JSON.stringify({ strategy, tone, variables: {} }),
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
        body: JSON.stringify({ strategy: String(task.strategy ?? strategy), tone, variables: {} }),
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
      await apiRequest(`/ai/tasks/${String(taskId)}/approve`, { method: "POST" });
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

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        <div className="panel grid gap-3 p-4 lg:grid-cols-[1fr_160px_160px_auto_auto]">
          <label className="min-w-64 flex-1 text-xs font-semibold text-gray-600">
            选择帖子
            <select className="field mt-2" value={postId} onChange={(e) => setPostId(e.target.value)}>
              {(posts.data ?? []).map((post) => (
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
          <button className="button-secondary self-end" onClick={analyzeSelected}><BrainCircuit className="h-4 w-4" />Analyze</button>
          <button className="button self-end" onClick={generateSelected}><Sparkles className="h-4 w-4" />Generate</button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section title="Review Queue">
          <div className="space-y-3">
            {(data ?? []).map((task) => (
              <div key={String(task.uuid)} className="panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{String(task.strategy)} · {String(task.model)}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {String(task.provider)} · Commercial {String(task.commercial_score)} · Risk {String(task.risk_score)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={task.status} />
                    {task.status !== "APPROVED" && (
                      <>
                        <button className="button-secondary" onClick={() => void regenerate(task)}>重新生成</button>
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
      </div>
    </StateView>
  );
}

function SchedulerPage() {
  const { data, error, loading, reload } =
    useApiData<RecordItem[]>("/scheduler/tasks");
  const aiTasks = useApiData<RecordItem[]>("/ai/tasks");
  const accounts = useApiData<RecordItem[]>("/accounts");
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

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        <div className="panel grid gap-3 p-4 md:grid-cols-[1fr_1fr_auto]">
          <select className="field" value={aiTaskId} onChange={(e) => setAiTaskId(e.target.value)}>
            <option value="">选择已批准 AI Task</option>
            {approved.map((task) => <option key={String(task.id)} value={String(task.id)}>Task #{String(task.id)} · {String(task.strategy)}</option>)}
          </select>
          <select className="field" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">不指定账号</option>
            {(accounts.data ?? []).map((account) => <option key={String(account.id)} value={String(account.id)}>{String(account.username)}</option>)}
          </select>
          <button className="button" disabled={!aiTaskId} onClick={queueTask}><CalendarClock className="h-4 w-4" />加入队列</button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section
          title="Database Queue"
          action={<span className="rounded bg-cyan/10 px-2 py-1 text-xs font-semibold text-cyan">Execution 唯一入口</span>}
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
      </div>
    </StateView>
  );
}

function AccountCenterPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/accounts");
  const [showForm, setShowForm] = useState(false);
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [feedback, setFeedback] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await apiRequest("/accounts", {
        method: "POST",
        body: JSON.stringify({
          platform_id: 1,
          username,
          display_name: displayName,
          environment_id: environmentId,
          daily_limits: { browse: 20, like: 8, reply: 5 },
          working_time: { timezone: "Asia/Shanghai", ranges: ["09:00-12:00"] },
        }),
      });
      setFeedback("账号与 TGE Environment ID 已保存；本版本不会连接 TGE。");
      setShowForm(false);
      setUsername("");
      setEnvironmentId("");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  const rows = (data ?? []).map((item) => ({
    ...item,
    environment_id: item.tge_profile
      ? (item.tge_profile as RecordItem).environment_id
      : "—",
  }));
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        {showForm && (
          <form className="panel grid gap-4 p-4 md:grid-cols-3" onSubmit={submit}>
            <input className="field" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <input className="field" placeholder="Display Name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            <input className="field" placeholder="TGE Environment ID" value={environmentId} onChange={(e) => setEnvironmentId(e.target.value)} required />
            <div className="flex gap-2 md:col-span-3">
              <button className="button" type="submit">保存账号</button>
              <button className="button-secondary" type="button" onClick={() => setShowForm(false)}>取消</button>
            </div>
          </form>
        )}
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section title="Account Assets" action={<button className="button" onClick={() => setShowForm(true)}><Users className="h-4 w-4" />添加账号</button>}>
          <DataTable
            columns={[
              { key: "username", label: "Username" },
              { key: "display_name", label: "Display Name" },
              { key: "environment_id", label: "TGE Environment" },
              { key: "health_score", label: "Health" },
              { key: "risk_level", label: "Risk" },
              { key: "status", label: "Status" },
            ]}
            rows={rows}
          />
        </Section>
      </div>
    </StateView>
  );
}

function SettingsPage() {
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/settings");
  const providers = useApiData<LLMProviderItem[]>("/settings/llm-providers");
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
  const [feedback, setFeedback] = useState("");

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
                {["mock", "openai", "anthropic", "gemini", "ollama", "custom"].map((type) => <option key={type} value={type}>{type}</option>)}
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
                {["Provider", "Type", "Model", "Key", "Purpose", "Priority", "Status", "Actions"].map((label) => <th key={label} className="px-4 py-3 font-semibold">{label}</th>)}
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
                    <td className="px-4 py-3"><StatusBadge value={provider.enabled ? provider.status : "DISABLED"} /></td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button className="icon-button" title="编辑" onClick={() => startProviderEdit(provider)}><Pencil className="h-4 w-4" /></button>
                        <button className="button-secondary" onClick={() => void toggleProvider(provider)}>{provider.enabled ? "停用" : "启用"}</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
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
    useApiData<RecordItem[]>("/scheduler/tasks");
  const counts = (data ?? []).reduce<Record<string, number>>((result, task) => {
    const status = String(task.status);
    result[status] = (result[status] ?? 0) + 1;
    return result;
  }, {});
  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-6">
        <div className="panel flex items-start gap-4 p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-gray-100">
            <Play className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <h2 className="font-bold">Execution Runtime Status</h2>
            <p className="mt-1 text-sm text-gray-500">只读显示 Scheduler 队列，本版本不连接 TGE、不执行浏览器动作。</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {["QUEUED", "RUNNING", "FAILED"].map((state) => (
            <div key={state} className="panel p-4">
              <p className="text-xs font-semibold uppercase text-gray-500">{state}</p>
              <p className="mt-4 text-2xl font-bold">{counts[state] ?? 0}</p>
              <p className="mt-1 text-xs text-gray-400">来自 Scheduler 数据库队列</p>
            </div>
          ))}
        </div>
        <DataTable
          columns={[
            { key: "task_type", label: "Task" },
            { key: "priority", label: "Priority" },
            { key: "account_id", label: "Account" },
            { key: "status", label: "Status" },
          ]}
          rows={data ?? []}
        />
      </div>
    </StateView>
  );
}

function EngagementPage() {
  const settings = useApiData<RecordItem[]>("/settings");
  const schedulerConfig = (settings.data ?? []).find(
    (item) => item.key === "scheduler.defaults",
  );
  return (
    <StateView loading={settings.loading} error={settings.error} reload={settings.reload}>
      <div className="space-y-6">
        <div className="panel flex items-start gap-4 p-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-gray-100">
            <Activity className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <h2 className="font-bold">Engagement Configuration</h2>
            <p className="mt-1 text-sm text-gray-500">仅展示任务配置占位，不创建或执行平台互动。</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {[
            ["Browse", "Disabled"],
            ["Like", "Disabled"],
            ["Warm-up", "Disabled"],
          ].map(([name, state]) => (
            <div key={name} className="panel p-4">
              <p className="text-xs font-semibold uppercase text-gray-500">{name}</p>
              <p className="mt-4 font-bold">{state}</p>
              <p className="mt-1 text-xs text-gray-400">Future configurable strategy</p>
            </div>
          ))}
        </div>
        <div className="panel p-4">
          <p className="text-sm font-semibold">Scheduler defaults</p>
          <pre className="mt-3 overflow-x-auto text-xs text-gray-600">
            {JSON.stringify(schedulerConfig?.value ?? {}, null, 2)}
          </pre>
        </div>
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
      return <ExecutionPage />;
    case "engagement":
      return <EngagementPage />;
    case "statistics":
      return <StatisticsPage />;
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
            <p className="text-[10px] uppercase text-gray-500">Local Console v0.3</p>
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
