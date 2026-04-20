const isDev = !('__TAURI_INTERNALS__' in window);
const API_BASE = isDev ? "/api" : "http://127.0.0.1:8000/api";

export interface FileInfo {
  path: string;
  name: string;
  extension: string;
  size: number;
  modified_time: number;
  modified_date: string;
  parent_dir: string;
  id: string;
  /** "local" | "icloud_placeholder" */
  storage_state?: string;
}

export interface AppConfigResponse {
  watch_directories: string[];
  organize_base: string;
  ai: Record<string, unknown>;
  safety: Record<string, unknown>;
  category_tree: Record<string, unknown>;
}

export interface ScanDirectory {
  directory: string;
  files: FileInfo[];
  total_count: number;
  total_size: number;
}

export interface ClassifyItem {
  original_path: string;
  target_folder: string;
  confidence: number;
  reason: string;
  source: string;
}

export interface OperationRecord {
  id: string;
  timestamp: string;
  source_path: string;
  dest_path: string;
  file_name: string;
  operation: string;
  undone: boolean;
}

class ApiError extends Error {
  status: number;
  url: string;
  body: string;
  constructor(msg: string, status: number, url: string, body: string) {
    super(msg);
    this.name = "ApiError";
    this.status = status;
    this.url = url;
    this.body = body;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const fullUrl = `${API_BASE}${url}`;
  let res: Response;
  try {
    res = await fetch(fullUrl, init);
  } catch (e: any) {
    const healthOk = await checkHealth();
    const hint = healthOk
      ? "后端正在运行，但此请求失败了。"
      : "无法连接后端服务（127.0.0.1:8000），后端可能已崩溃。";
    throw new ApiError(
      `网络请求失败: ${e?.message || "未知错误"}\n\n${hint}\n\n请求地址: ${fullUrl}`,
      0,
      fullUrl,
      "",
    );
  }

  if (!res.ok) {
    let body = "";
    try { body = await res.text(); } catch {}
    throw new ApiError(
      `HTTP ${res.status} ${res.statusText}\n\n响应内容:\n${body.slice(0, 1000)}\n\n请求地址: ${fullUrl}`,
      res.status,
      fullUrl,
      body,
    );
  }

  return res.json();
}

async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function scanAll() {
  return request<{
    directories: ScanDirectory[];
    total_files: number;
    total_size: number;
  }>("/scan");
}

export async function classifyFiles(files: FileInfo[]) {
  return request<{
    plan_id: string;
    total: number;
    rule_classified: number;
    ai_classified: number;
    items: ClassifyItem[];
  }>("/classify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(files),
  });
}

export async function confirmPlan(planId: string) {
  return request<{
    success: boolean;
    async?: boolean;
    message?: string;
    total?: number;
    moved?: number;
    skipped?: number;
    failed?: number;
    errors?: { file: string; source: string; dest: string; error: string }[];
    records?: OperationRecord[];
    error?: string;
    error_detail?: string;
  }>(`/organize/confirm/${planId}`, {
    method: "POST",
  });
}

export async function undoOperation(operationId: string) {
  return request<{ success?: boolean; error?: string }>(
    `/undo/${operationId}`,
    { method: "POST" },
  );
}

export async function getHistory(page: number = 1) {
  return request<{ page: number; records: OperationRecord[] }>(
    `/history?page=${page}`,
  );
}

export async function getStats() {
  return request<{
    total_operations: number;
    category_distribution: Record<string, number>;
    watch_dirs: Record<string, number>;
    recent_operations: OperationRecord[];
  }>("/stats");
}

export async function startWatcher() {
  return request<{ status: string }>("/watcher/start", { method: "POST" });
}

export async function stopWatcher() {
  return request<{ status: string }>("/watcher/stop", { method: "POST" });
}

export async function getWatcherStatus() {
  return request<{ running: boolean }>("/watcher/status");
}

export async function openFolder(path: string) {
  return request<{ success: boolean; path: string }>("/open-folder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
}

export interface OrganizedFolder {
  path: string;
  relative: string;
  count: number;
}

export async function getOrganizedTree() {
  return request<{ base: string; folders: OrganizedFolder[] }>("/organized-tree");
}

export async function fetchAppConfig() {
  return request<AppConfigResponse>("/config");
}

export async function updateAppConfig(body: {
  watch_directories?: string[];
  organize_base?: string;
}) {
  return request<{ ok: boolean; config: AppConfigResponse }>("/config", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function discoverIcloud() {
  return request<{
    platform: string;
    icloud_drive: { path: string; exists: boolean; recommended_watch_path: string };
    materialize_supported: boolean;
    note: string | null;
  }>("/icloud/discover");
}

export async function getOrganizeStatus(planId: string) {
  return request<{
    found: boolean;
    current?: number;
    total?: number;
    done?: boolean;
    result?: {
      type?: string;
      moved?: number;
      skipped?: number;
      failed?: number;
      errors?: { file: string; error: string }[];
      error?: string;
    } | null;
  }>(`/organize/status/${planId}`);
}

export function connectWebSocket(
  onMessage: (data: any) => void
): WebSocket {
  const wsUrl = isDev
    ? `ws://${window.location.host}/ws`
    : "ws://127.0.0.1:8000/ws";
  const ws = new WebSocket(wsUrl);
  ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  ws.onclose = () => {
    setTimeout(() => connectWebSocket(onMessage), 3000);
  };
  return ws;
}

export function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(1) + " " + sizes[i];
}

export function formatTime(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
