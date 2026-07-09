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
  const { data, error, loading, reload } = useApiData<RecordItem[]>("/data-sources");
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("Apify Source");
  const [actorId, setActorId] = useState("");
  const [token, setToken] = useState("");
  const [feedback, setFeedback] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setFeedback("");
    try {
      await apiRequest("/data-sources", {
        method: "POST",
        body: JSON.stringify({
          name,
          source_type: "APIFY",
          platform_id: 1,
          adapter_key: "apify",
          config: {
            actor_id: actorId,
            token_configured: Boolean(token),
            token_preview: token ? `${token.slice(0, 4)}...` : "",
          },
        }),
      });
      setFeedback("Apify 配置已保存。本版本不会运行 Actor。");
      setShowForm(false);
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        {showForm && (
          <form className="panel grid gap-4 p-4 md:grid-cols-3" onSubmit={submit}>
            <label className="text-xs font-semibold text-gray-600">
              配置名称
              <input className="field mt-2" value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              Actor ID
              <input className="field mt-2" value={actorId} onChange={(e) => setActorId(e.target.value)} placeholder="owner/actor-name" required />
            </label>
            <label className="text-xs font-semibold text-gray-600">
              API Token
              <input className="field mt-2" type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="仅保存配置状态" />
            </label>
            <div className="flex gap-2 md:col-span-3">
              <button className="button" type="submit"><CheckCircle2 className="h-4 w-4" />保存配置</button>
              <button className="button-secondary" type="button" onClick={() => setShowForm(false)}>取消</button>
            </div>
          </form>
        )}
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section
          title="Configured Sources"
          action={
            <button className="button" onClick={() => setShowForm(true)}>
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
      </div>
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
  const posts = useApiData<RecordItem[]>("/posts");
  const [postId, setPostId] = useState("1");
  const [feedback, setFeedback] = useState("");

  async function generateMock() {
    try {
      await apiRequest("/ai/generate-mock", {
        method: "POST",
        body: JSON.stringify({ post_id: Number(postId), strategy: "EDUCATION" }),
      });
      setFeedback("Mock Provider 已生成回复，等待人工批准。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "生成失败");
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

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        <div className="panel flex flex-wrap items-end gap-3 p-4">
          <label className="min-w-64 flex-1 text-xs font-semibold text-gray-600">
            选择帖子
            <select className="field mt-2" value={postId} onChange={(e) => setPostId(e.target.value)}>
              {(posts.data ?? []).map((post) => (
                <option key={String(post.id)} value={String(post.id)}>{String(post.title)}</option>
              ))}
            </select>
          </label>
          <button className="button" onClick={generateMock}><Sparkles className="h-4 w-4" />Mock 生成</button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
        <Section title="Review Queue">
          <div className="space-y-3">
            {(data ?? []).map((task) => (
              <div key={String(task.uuid)} className="panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{String(task.strategy)} · {String(task.model)}</p>
                    <p className="mt-1 text-xs text-gray-500">{String(task.provider)} · Commercial {String(task.commercial_score)} · Risk {String(task.risk_score)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge value={task.status} />
                    {task.status !== "APPROVED" && (
                      <button className="button-secondary" onClick={() => approve(task.id)}>批准</button>
                    )}
                  </div>
                </div>
                {Boolean(task.reply) && (
                  <p className="mt-4 border-t border-line pt-3 text-sm text-gray-600">
                    {String((task.reply as RecordItem).content)}
                  </p>
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
  const aiSetting = (data ?? []).find((item) => item.key === "ai.default_provider");
  const aiValue = (aiSetting?.value ?? {}) as RecordItem;
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (aiSetting && !provider) {
      setProvider(String(aiValue.provider ?? "mock"));
      setModel(String(aiValue.model ?? "mock-v0.1"));
    }
  }, [aiSetting, aiValue, provider]);

  async function saveProvider() {
    try {
      await apiRequest("/settings/ai.default_provider", {
        method: "PUT",
        body: JSON.stringify({ value: { provider, model, enabled: true } }),
      });
      setFeedback("LLM Provider 配置已保存。Mock 生成不会调用外部 API。");
      await reload();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "保存失败");
    }
  }

  return (
    <StateView loading={loading} error={error} reload={reload}>
      <div className="space-y-5">
        <div className="panel grid gap-3 p-4 md:grid-cols-[1fr_1fr_auto]">
          <label className="text-xs font-semibold text-gray-600">
            LLM Provider
            <select className="field mt-2" value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="mock">Mock Provider</option>
              <option value="ollama">Ollama</option>
              <option value="openai">OpenAI (未连接)</option>
              <option value="anthropic">Anthropic (未连接)</option>
              <option value="custom">Custom API (未连接)</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            Model
            <input className="field mt-2" value={model} onChange={(e) => setModel(e.target.value)} />
          </label>
          <button className="button self-end" onClick={saveProvider}><Settings className="h-4 w-4" />保存</button>
        </div>
        {feedback && <p className="text-sm text-teal">{feedback}</p>}
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
