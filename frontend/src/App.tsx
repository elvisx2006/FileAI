import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  FolderOpen,
  Scan,
  Sparkles,
  Check,
  Undo2,
  Eye,
  Play,
  Square,
  ChevronDown,
  FileText,
  Image,
  Film,
  Music,
  Code2,
  Archive,
  Palette,
  Download,
  HelpCircle,
  RefreshCw,
  Settings,
  LayoutDashboard,
  History,
  Wand2,
  ExternalLink,
  FolderTree,
  Zap,
  Activity,
  AlertTriangle,
  Copy,
  X,
  Cloud,
} from "lucide-react";
import {
  scanAll,
  classifyFiles,
  buildPlanFromItems,
  confirmPlan,
  undoOperation,
  getHistory,
  getStats,
  startWatcher,
  stopWatcher,
  getWatcherStatus,
  connectWebSocket,
  openFolder,
  getOrganizedTree,
  getOrganizeStatus,
  fetchAppConfig,
  updateAppConfig,
  discoverIcloud,
  formatSize,
  formatTime,
  type ScanDirectory,
  type ClassifyItem,
  type OperationRecord,
  type OrganizedFolder,
  type FileInfo,
} from "./api";
import "./App.css";

type Page = "dashboard" | "organize" | "history" | "settings" | "browse";

/** Per-request file count for /classify to avoid huge JSON payloads on the main thread. */
const CLASSIFY_CHUNK_SIZE = 2500;
const CLASSIFY_PREVIEW_PAGE = 500;

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  Documents: <FileText size={16} />,
  Images: <Image size={16} />,
  Videos: <Film size={16} />,
  Audio: <Music size={16} />,
  Code: <Code2 size={16} />,
  Archives: <Archive size={16} />,
  Design: <Palette size={16} />,
  Installers: <Download size={16} />,
  Misc: <HelpCircle size={16} />,
};

const CATEGORY_COLORS: Record<string, string> = {
  Images: "var(--accent)",
  Videos: "var(--purple)",
  Code: "var(--green)",
  Documents: "var(--yellow)",
  Audio: "var(--pink)",
  Archives: "var(--orange)",
  Design: "var(--teal)",
  Installers: "var(--indigo)",
  Configs: "var(--orange)",
  Misc: "var(--text-tertiary)",
};

function getCatColor(cat: string): string {
  const top = cat.split("/")[0];
  return CATEGORY_COLORS[top] || "var(--text-tertiary)";
}

function DonutChart({ data, total }: { data: [string, number][]; total: number }) {
  const size = 120;
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  let accumulated = 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut-svg">
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="var(--bg-input)" strokeWidth={stroke} />
      {data.map(([cat, count]) => {
        const pct = total > 0 ? count / total : 0;
        const dashArray = `${circumference * pct} ${circumference * (1 - pct)}`;
        const offset = -circumference * accumulated + circumference * 0.25;
        accumulated += pct;
        return (
          <circle
            key={cat}
            cx={size/2} cy={size/2} r={radius}
            fill="none"
            stroke={getCatColor(cat)}
            strokeWidth={stroke}
            strokeDasharray={dashArray}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="donut-segment"
          />
        );
      })}
      <text x={size/2} y={size/2 - 6} textAnchor="middle" className="donut-value">{total}</text>
      <text x={size/2} y={size/2 + 12} textAnchor="middle" className="donut-label">已整理</text>
    </svg>
  );
}

function getFileIcon(fileName: string) {
  const ext = fileName.split(".").pop()?.toLowerCase() || "";
  if (["jpg","jpeg","png","gif","webp","svg","bmp","ico","tiff"].includes(ext)) return <Image size={14} />;
  if (["mp4","mov","avi","mkv","wmv","flv","webm"].includes(ext)) return <Film size={14} />;
  if (["mp3","wav","flac","aac","ogg","m4a"].includes(ext)) return <Music size={14} />;
  if (["zip","rar","7z","tar","gz","bz2","dmg"].includes(ext)) return <Archive size={14} />;
  if (["js","ts","py","jsx","tsx","go","rs","java","c","cpp","h","rb","php","swift"].includes(ext)) return <Code2 size={14} />;
  if (["psd","ai","sketch","fig","xd"].includes(ext)) return <Palette size={14} />;
  return <FileText size={14} />;
}

function getCategoryIcon(folder: string) {
  const top = folder.split("/")[0];
  return CATEGORY_ICONS[top] || <FolderOpen size={16} />;
}

function confidenceColor(c: number): string {
  if (c >= 0.85) return "var(--green)";
  if (c >= 0.7) return "var(--yellow)";
  return "var(--red)";
}

function confidenceLabel(c: number): string {
  if (c >= 0.85) return "高";
  if (c >= 0.7) return "中";
  return "低";
}

function relFromWatch(watchRoot: string, parentDir: string): string {
  const r = toPosix(watchRoot.replace(/[/\\]$/, ""));
  const p = toPosix(parentDir.replace(/[/\\]$/, ""));
  if (p === r) return "（根目录）";
  const prefix = r.endsWith("/") ? r : `${r}/`;
  if (p.startsWith(prefix)) {
    const inner = p.slice(prefix.length);
    return inner || "（根目录）";
  }
  return parentDir.replace(/^\/Users\/[^/]+\//, "~/");
}

function toPosix(s: string) {
  return s.replace(/\\/g, "/");
}

function groupFilesByParent(files: FileInfo[], watchRoot: string) {
  const map = new Map<string, FileInfo[]>();
  for (const f of files) {
    const k = f.parent_dir;
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(f);
  }
  const normRoot = watchRoot.replace(/\/$/, "");
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([parentDir, groupFiles]) => ({
      parentDir,
      rel: relFromWatch(normRoot, parentDir),
      files: groupFiles.sort((x, y) => x.name.localeCompare(y.name)),
    }));
}

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  // Dashboard
  const [stats, setStats] = useState<any>(null);

  // Organize
  const [scanData, setScanData] = useState<ScanDirectory[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [classifyResult, setClassifyResult] = useState<ClassifyItem[] | null>(null);
  const [planId, setPlanId] = useState<string | null>(null);
  const [organizing, setOrganizing] = useState(false);

  // History
  const [historyData, setHistoryData] = useState<OperationRecord[]>([]);
  const [historyPage, setHistoryPage] = useState(1);

  // Watcher
  const [watcherRunning, setWatcherRunning] = useState(false);
  const [liveEvents, setLiveEvents] = useState<string[]>([]);

  // Browse organized
  const [organizedFolders, setOrganizedFolders] = useState<OrganizedFolder[]>([]);
  const [organizedBase, setOrganizedBase] = useState("");

  // Settings — editable paths
  const [cfgWatchDirs, setCfgWatchDirs] = useState<string[]>([]);
  const [cfgOrganizeBase, setCfgOrganizeBase] = useState("");
  const [cfgLoading, setCfgLoading] = useState(false);
  const [cfgSaving, setCfgSaving] = useState(false);
  const [icloudHint, setIcloudHint] = useState<string | null>(null);
  const [cfgScanMaxDepth, setCfgScanMaxDepth] = useState(-1);
  const [cfgSkipProject, setCfgSkipProject] = useState(true);
  const [cfgCleanupEmpty, setCfgCleanupEmpty] = useState(true);
  const [collapsedSubfolders, setCollapsedSubfolders] = useState<Set<string>>(() => new Set());
  /** Default off: skip *.icloud placeholders to cut volume and avoid download-at-execute surprises. */
  const [includeIcloudInClassify, setIncludeIcloudInClassify] = useState(false);
  const [classifyPreviewLimit, setClassifyPreviewLimit] = useState(CLASSIFY_PREVIEW_PAGE);

  // Live feed collapse
  const [liveOpen, setLiveOpen] = useState(false);

  // Progress
  const [progress, setProgress] = useState<{ current: number; total: number; stage: string } | null>(null);

  // Error panel
  const [errorInfo, setErrorInfo] = useState<{
    title: string;
    detail: string;
    errors?: { file: string; error: string }[];
    moved?: number;
    failed?: number;
  } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  const donutData = useMemo(() => {
    if (!stats?.category_distribution) return [];
    return Object.entries(stats.category_distribution)
      .sort(([, a], [, b]) => (b as number) - (a as number))
      .slice(0, 8) as [string, number][];
  }, [stats]);

  const classifyStats = useMemo(() => {
    if (!classifyResult) return { high: 0, mid: 0, low: 0 };
    let high = 0;
    let mid = 0;
    let low = 0;
    for (const i of classifyResult) {
      if (i.confidence >= 0.85) high++;
      else if (i.confidence >= 0.7) mid++;
      else low++;
    }
    return { high, mid, low };
  }, [classifyResult]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }, []);

  useEffect(() => {
    wsRef.current = connectWebSocket((data) => {
      if (data.type === "new_file") {
        setLiveEvents((prev) => [`新文件: ${data.path.split("/").pop()}`, ...prev.slice(0, 19)]);
        setLiveOpen(true);
      } else if (data.type === "organize_done") {
        setProgress(null);
        setOrganizing(false);
        if (data.failed > 0) {
          setErrorInfo({
            title: `部分文件移动失败 (${data.failed} 个)`,
            detail: `成功 ${data.moved} 个，失败 ${data.failed} 个，跳过 ${data.skipped || 0} 个`,
            errors: data.errors,
            moved: data.moved,
            failed: data.failed,
          });
        } else {
          const removed = typeof data.empty_dirs_removed === "number" ? data.empty_dirs_removed : 0;
          const extra = removed > 0 ? `，已清理 ${removed} 个空文件夹` : "";
          showToast(`已移动 ${data.moved} 个文件${extra}，点击左侧「已整理文件」查看`);
        }
        setClassifyResult(null);
        setPlanId(null);
        setScanData([]);
        setCollapsedSubfolders(new Set());
        openFolder("organized");
      } else if (data.type === "organize_error") {
        setProgress(null);
        setOrganizing(false);
        setErrorInfo({
          title: "执行失败",
          detail: data.error || "后端执行过程中发生严重错误",
        });
      } else if (data.type === "undo") {
        showToast("撤销成功");
      } else if (data.type === "classify_progress") {
        setProgress({ current: data.current, total: data.total, stage: data.stage === "done" ? "classify_done" : "classify" });
        if (data.stage === "done") {
          setTimeout(() => setProgress(null), 600);
        }
      } else if (data.type === "organize_progress") {
        setProgress({ current: data.current, total: data.total, stage: "organize" });
      }
    });
    getWatcherStatus().then((s) => setWatcherRunning(s.running)).catch(() => {});
    return () => wsRef.current?.close();
  }, [showToast]);

  useEffect(() => {
    if (page === "dashboard") {
      getStats().then(setStats).catch(() => {});
    } else if (page === "history") {
      getHistory(historyPage).then((d) => setHistoryData(d.records)).catch(() => {});
    } else if (page === "browse") {
      getOrganizedTree().then((d) => {
        setOrganizedFolders(d.folders);
        setOrganizedBase(d.base);
      }).catch(() => {});
    } else if (page === "settings") {
      setCfgLoading(true);
      fetchAppConfig()
        .then((c) => {
          setCfgWatchDirs([...c.watch_directories]);
          setCfgOrganizeBase(c.organize_base);
          setCfgScanMaxDepth(typeof c.scan?.max_depth === "number" ? c.scan.max_depth : -1);
          setCfgSkipProject(c.scan?.skip_project_dirs !== false);
          setCfgCleanupEmpty(c.scan?.cleanup_empty_dirs !== false);
        })
        .catch(() => showToast("无法加载配置"))
        .finally(() => setCfgLoading(false));
      discoverIcloud()
        .then((d) => {
          setIcloudHint(
            d.icloud_drive.exists
              ? `已检测到本机 iCloud Drive，可点下方「添加 iCloud Drive」快捷加入。`
              : `未检测到默认 iCloud Drive 路径，仍可手动粘贴路径。${d.note ? ` ${d.note}` : ""}`,
          );
        })
        .catch(() => setIcloudHint(null));
    }
  }, [page, historyPage, showToast]);

  const ICLOUD_WATCH_PRESET = "~/Library/Mobile Documents/com~apple~CloudDocs";

  const addIcloudWatchPreset = () => {
    setCfgWatchDirs((prev) => {
      const norm = (s: string) => s.replace(/\s+/g, "");
      if (prev.some((p) => norm(p) === norm(ICLOUD_WATCH_PRESET))) return prev;
      return [...prev, ICLOUD_WATCH_PRESET];
    });
  };

  const savePathSettings = async () => {
    const dirs = cfgWatchDirs.map((d) => d.trim()).filter(Boolean);
    if (dirs.length === 0) {
      showToast("至少保留一个监控目录");
      return;
    }
    const base = cfgOrganizeBase.trim();
    if (!base) {
      showToast("整理目标路径不能为空");
      return;
    }
    setCfgSaving(true);
    try {
      await updateAppConfig({
        watch_directories: dirs,
        organize_base: base,
        scan: {
          max_depth: cfgScanMaxDepth,
          skip_project_dirs: cfgSkipProject,
          cleanup_empty_dirs: cfgCleanupEmpty,
        },
      });
      showToast("已保存；下次扫描将使用新配置");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "保存失败";
      showToast(msg);
    }
    setCfgSaving(false);
  };

  const handleScan = async () => {
    setLoading(true);
    setClassifyResult(null);
    setPlanId(null);
    try {
      const data = await scanAll();
      setScanData(data.directories);
      setCollapsedSubfolders(new Set());
      const allIds = new Set(data.directories.flatMap((d) => d.files.map((f) => f.path)));
      setSelectedFiles(allIds);
      showToast(`扫描完成: ${data.total_files} 个文件`);
    } catch {
      showToast("扫描失败，请确认后端已启动");
    }
    setLoading(false);
  };

  const handleClassify = async () => {
    if (selectedFiles.size === 0) return showToast("请先选择文件");
    setLoading(true);
    let allFiles = scanData.flatMap((d) => d.files).filter((f) => selectedFiles.has(f.path));
    if (!includeIcloudInClassify) {
      const before = allFiles.length;
      allFiles = allFiles.filter((f) => f.storage_state !== "icloud_placeholder");
      const skipped = before - allFiles.length;
      if (skipped > 0) {
        showToast(`已跳过 ${skipped} 个仅 iCloud 占位文件（勾选「包含 iCloud 占位」可参与分类）`);
      }
    }
    if (allFiles.length === 0) {
      showToast("没有可分类的文件；请勾选「包含 iCloud 占位」或重新选择");
      setLoading(false);
      return;
    }
    setProgress({ current: 0, total: allFiles.length, stage: "classify" });
    try {
      if (allFiles.length <= CLASSIFY_CHUNK_SIZE) {
        const result = await classifyFiles(allFiles, { persistPlan: true });
        setClassifyResult(result.items);
        setPlanId(result.plan_id);
        setClassifyPreviewLimit(CLASSIFY_PREVIEW_PAGE);
        showToast(`分类完成: 规则 ${result.rule_classified} 个, AI ${result.ai_classified} 个`);
      } else {
        const mergedItems: ClassifyItem[] = [];
        let totalRule = 0;
        let totalAi = 0;
        for (let offset = 0; offset < allFiles.length; offset += CLASSIFY_CHUNK_SIZE) {
          const chunk = allFiles.slice(offset, offset + CLASSIFY_CHUNK_SIZE);
          const result = await classifyFiles(chunk, { persistPlan: false });
          mergedItems.push(...result.items);
          totalRule += result.rule_classified;
          totalAi += result.ai_classified;
          setProgress({
            current: Math.min(offset + chunk.length, allFiles.length),
            total: allFiles.length,
            stage: "classify",
          });
        }
        const { plan_id } = await buildPlanFromItems(mergedItems);
        setClassifyResult(mergedItems);
        setPlanId(plan_id);
        setClassifyPreviewLimit(CLASSIFY_PREVIEW_PAGE);
        showToast(`分类完成: 规则 ${totalRule} 个, AI ${totalAi} 个`);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "网络错误或后端未启动，请检查后端服务是否正常运行。";
      setErrorInfo({
        title: "AI 分类失败",
        detail: msg,
      });
    }
    setProgress(null);
    setLoading(false);
  };

  const handleConfirm = async () => {
    if (!planId || !classifyResult) return;
    const pathSet = new Set(classifyResult.map((i) => i.original_path));
    const cloudOnly = scanData
      .flatMap((d) => d.files)
      .filter((f) => pathSet.has(f.path) && f.storage_state === "icloud_placeholder");
    if (cloudOnly.length > 0) {
      const ok = window.confirm(
        `有 ${cloudOnly.length} 个文件当前为 iCloud 仅云端占位符。确认执行时将尝试下载到本地后再移动，耗时与流量取决于文件大小。\n\n是否继续？`,
      );
      if (!ok) return;
    }
    const currentPlanId = planId;
    const total = classifyResult.length;
    setOrganizing(true);
    setProgress({ current: 0, total, stage: "organize" });

    let result;
    try {
      result = await confirmPlan(currentPlanId);
    } catch (e: any) {
      setProgress(null);
      setOrganizing(false);
      setErrorInfo({ title: "执行失败", detail: e?.message || "网络错误" });
      return;
    }

    if (!result.success) {
      setProgress(null);
      setOrganizing(false);
      setErrorInfo({ title: "执行失败", detail: result.error_detail || result.error || "未知错误" });
      return;
    }

    // 轮询兜底：每 1.5 秒检查一次执行状态，防止 WebSocket 不可用时卡住
    const startTime = Date.now();
    const pollInterval = setInterval(async () => {
      // 超过 10 分钟自动终止轮询
      if (Date.now() - startTime > 10 * 60 * 1000) {
        clearInterval(pollInterval);
        setProgress(null);
        setOrganizing(false);
        showToast("执行超时，请在「已整理文件」页面查看结果");
        return;
      }
      try {
        const status = await getOrganizeStatus(currentPlanId);
        if (!status.found) {
          clearInterval(pollInterval);
          return;
        }
        // 更新进度条
        if (status.current !== undefined && status.total !== undefined) {
          setProgress({ current: status.current, total: status.total, stage: "organize" });
        }
        if (status.done && status.result) {
          clearInterval(pollInterval);
          const res = status.result;
          setProgress(null);
          setOrganizing(false);
          if (res.error) {
            setErrorInfo({ title: "执行失败", detail: res.error });
          } else if (res.failed && res.failed > 0) {
            setErrorInfo({
              title: `部分文件移动失败 (${res.failed} 个)`,
              detail: `成功 ${res.moved} 个，失败 ${res.failed} 个`,
              errors: res.errors,
              moved: res.moved,
              failed: res.failed,
            });
            setClassifyResult(null); setPlanId(null); setScanData([]);
          } else {
            const removed = typeof res.empty_dirs_removed === "number" ? res.empty_dirs_removed : 0;
            const extra = removed > 0 ? `，已清理 ${removed} 个空文件夹` : "";
            showToast(`已移动 ${res.moved} 个文件${extra}，点击左侧「已整理文件」查看`);
            setClassifyResult(null); setPlanId(null); setScanData([]);
            setCollapsedSubfolders(new Set());
            openFolder("organized");
          }
        }
      } catch {
        // 轮询失败时静默忽略，等 WebSocket 推送
      }
    }, 1500);
  };

  const handleUndo = async (id: string) => {
    const result = await undoOperation(id);
    if (result.success) {
      showToast("撤销成功");
      getHistory(historyPage).then((d) => setHistoryData(d.records));
    } else {
      showToast(result.error || "撤销失败");
    }
  };

  const toggleWatcher = async () => {
    if (watcherRunning) {
      await stopWatcher();
      setWatcherRunning(false);
      showToast("实时监控已停止");
    } else {
      await startWatcher();
      setWatcherRunning(true);
      showToast("实时监控已开启");
    }
  };

  const toggleFile = (path: string) => {
    setSelectedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const toggleFileGroup = (files: FileInfo[], selectAll: boolean) => {
    setSelectedFiles((prev) => {
      const next = new Set(prev);
      for (const f of files) {
        if (selectAll) next.add(f.path);
        else next.delete(f.path);
      }
      return next;
    });
  };

  const toggleSubfolderCollapsed = (key: string) => {
    setCollapsedSubfolders((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleAllFiles = () => {
    const allFiles = scanData.flatMap((d) => d.files);
    if (selectedFiles.size === allFiles.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(allFiles.map((f) => f.path)));
    }
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <Wand2 size={22} />
          <span>FileAI</span>
        </div>
        <nav className="sidebar-nav">
          {(
            [
              ["dashboard", <LayoutDashboard size={18} />, "仪表盘"],
              ["organize", <Sparkles size={18} />, "整理文件"],
              ["browse", <FolderTree size={18} />, "已整理文件"],
              ["history", <History size={18} />, "操作历史"],
              ["settings", <Settings size={18} />, "设置"],
            ] as [Page, React.ReactNode, string][]
          ).map(([key, icon, label]) => (
            <button
              key={key}
              className={`nav-item ${page === key ? "active" : ""}`}
              onClick={() => setPage(key)}
            >
              {icon}
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className={`watcher-badge ${watcherRunning ? "running" : ""}`}>
            <div className="watcher-dot" />
            <span>{watcherRunning ? "监控中" : "监控关闭"}</span>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="main">
        {/* Toast */}
        {toast && <div className="toast">{toast}</div>}

        {/* Progress Bar */}
        {progress && (
          <div className="progress-overlay">
            <div className="progress-card">
              <div className="progress-title">
                {progress.stage === "classify" || progress.stage === "classify_done"
                  ? "AI 分类中..."
                  : "文件移动中..."}
              </div>
              <div className="progress-bar-track">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%` }}
                />
              </div>
              <div className="progress-text">
                {progress.current} / {progress.total}
                <span className="progress-pct">
                  {progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Error Panel */}
        {errorInfo && (
          <div className="error-overlay" onClick={() => setErrorInfo(null)}>
            <div className="error-panel" onClick={(e) => e.stopPropagation()}>
              <div className="error-header">
                <AlertTriangle size={18} />
                <span>{errorInfo.title}</span>
                <button className="error-close" onClick={() => setErrorInfo(null)}>
                  <X size={16} />
                </button>
              </div>
              <div className="error-body">
                {errorInfo.moved !== undefined && (
                  <div className="error-summary">
                    <span className="error-stat success">成功 {errorInfo.moved}</span>
                    <span className="error-stat fail">失败 {errorInfo.failed || 0}</span>
                  </div>
                )}
                <div className="error-detail">{errorInfo.detail}</div>
                {errorInfo.errors && errorInfo.errors.length > 0 && (
                  <div className="error-list">
                    <div className="error-list-title">失败详情：</div>
                    {errorInfo.errors.map((err, i) => (
                      <div className="error-item" key={i}>
                        <span className="error-file">{err.file}</span>
                        <span className="error-msg">{err.error}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="error-footer">
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    const text = [
                      errorInfo.title,
                      errorInfo.detail,
                      ...(errorInfo.errors || []).map((e) => `${e.file}: ${e.error}`),
                    ].join("\n");
                    navigator.clipboard.writeText(text);
                    showToast("已复制错误信息");
                  }}
                >
                  <Copy size={14} /> 复制错误信息
                </button>
                <button className="btn btn-primary btn-sm" onClick={() => setErrorInfo(null)}>
                  知道了
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Dashboard */}
        {page === "dashboard" && (
          <div className="page">
            <h1 className="page-title">仪表盘</h1>

            {/* Hero Card */}
            <div className="hero-card">
              <div className="hero-left">
                <div className="hero-number">{stats?.total_operations ?? 0}</div>
                <div className="hero-subtitle">个文件已整理</div>
                <div className="hero-dirs">
                  {stats?.watch_dirs &&
                    Object.entries(stats.watch_dirs).map(([dir, count]) => (
                      <span className="hero-dir-badge" key={dir}>
                        <FolderOpen size={12} /> {dir} <strong>{count as number}</strong>
                      </span>
                    ))}
                </div>
              </div>
              <div className="hero-right">
                <button className="btn btn-primary btn-lg" onClick={() => { setPage("organize"); setTimeout(handleScan, 100); }}>
                  <Scan size={18} /> 扫描并整理
                </button>
                <div className="hero-links">
                  <button className="hero-link" onClick={() => openFolder("organized")}>
                    <ExternalLink size={13} /> 在 Finder 中打开
                  </button>
                  <button className="hero-link" onClick={() => setPage("browse")}>
                    <FolderTree size={13} /> 浏览文件
                  </button>
                  <button className={`hero-link ${watcherRunning ? "active" : ""}`} onClick={toggleWatcher}>
                    {watcherRunning ? <Square size={13} /> : <Play size={13} />}
                    {watcherRunning ? "停止监控" : "开启监控"}
                  </button>
                </div>
              </div>
            </div>

            {/* Donut + Recent */}
            <div className="section-row">
              <div className="section-card donut-section">
                <h2 className="section-title">分类分布</h2>
                {donutData.length > 0 ? (
                  <div className="donut-layout">
                    <DonutChart data={donutData} total={stats?.total_operations ?? 0} />
                    <div className="donut-legend">
                      {donutData.map(([cat, cnt]) => (
                        <div className="legend-item" key={cat}>
                          <span className="legend-dot" style={{ background: getCatColor(cat) }} />
                          <span className="legend-name">{cat}</span>
                          <span className="legend-count">{cnt}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="empty-hint">暂无数据，整理一些文件后这里会显示分布</p>
                )}
              </div>

              <div className="section-card flex-1">
                <h2 className="section-title">
                  最近操作
                  {stats?.recent_operations?.length > 0 && (
                    <button className="section-more" onClick={() => setPage("history")}>查看全部 →</button>
                  )}
                </h2>
                <div className="recent-list">
                  {stats?.recent_operations?.slice(0, 6).map((op: OperationRecord) => (
                    <div className="recent-item" key={op.id}>
                      <span className="recent-icon">{getFileIcon(op.file_name)}</span>
                      <div className="recent-info">
                        <span className="recent-name">{op.file_name}</span>
                        <span className="recent-dest">{op.dest_path.split("Organized/")[1] || op.dest_path}</span>
                      </div>
                      <span className="recent-time">{formatTime(op.timestamp)}</span>
                    </div>
                  ))}
                  {(!stats?.recent_operations || stats.recent_operations.length === 0) && (
                    <p className="empty-hint">暂无操作记录</p>
                  )}
                </div>
              </div>
            </div>

            {/* Collapsible live feed */}
            <div className={`live-section ${liveOpen ? "open" : ""}`}>
              <button className="live-header" onClick={() => setLiveOpen(!liveOpen)}>
                <Activity size={15} />
                <span>实时动态</span>
                <span className={`live-dot ${watcherRunning ? "active" : ""}`} />
                {liveEvents.length > 0 && <span className="live-badge">{liveEvents.length}</span>}
                <ChevronDown size={16} className={`live-chevron ${liveOpen ? "rotated" : ""}`} />
              </button>
              {liveOpen && (
                <div className="live-body">
                  {liveEvents.length === 0 && <p className="empty-hint">开启监控后，新文件事件将在这里显示</p>}
                  {liveEvents.map((ev, i) => (
                    <div className="live-item" key={i}>
                      <Zap size={12} className="live-item-icon" />
                      {ev}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Organize */}
        {page === "organize" && (
          <div className="page">
            <div className="page-header">
              <h1 className="page-title">整理文件</h1>
              <div className="header-actions">
                <button className="btn btn-primary" onClick={handleScan} disabled={loading}>
                  <Scan size={16} /> {loading ? "扫描中..." : "扫描目录"}
                </button>
                {scanData.length > 0 && !classifyResult && (
                  <button className="btn btn-accent" onClick={handleClassify} disabled={loading || selectedFiles.size === 0}>
                    <Sparkles size={16} /> {loading ? "分类中..." : "AI 分类"}
                  </button>
                )}
                {classifyResult && planId && (
                  <button className="btn btn-success" onClick={handleConfirm} disabled={organizing}>
                    <Check size={16} /> {organizing ? "执行中..." : "确认执行"}
                  </button>
                )}
              </div>
            </div>

            {/* File list or classify result */}
            {!classifyResult && scanData.length > 0 && (
              <div className="file-panel">
                <div className="panel-header">
                  <label className="check-all">
                    <input
                      type="checkbox"
                      checked={selectedFiles.size === scanData.flatMap((d) => d.files).length && selectedFiles.size > 0}
                      onChange={toggleAllFiles}
                    />
                    全选 ({selectedFiles.size}/{scanData.flatMap((d) => d.files).length})
                  </label>
                  <label className="check-all check-icloud" title="关闭时：仅 iCloud 占位（未下载）的文件不参与分类，可显著减少请求量">
                    <input
                      type="checkbox"
                      checked={includeIcloudInClassify}
                      onChange={() => setIncludeIcloudInClassify((v) => !v)}
                    />
                    <Cloud size={14} />
                    包含 iCloud 占位
                  </label>
                </div>
                {scanData.map((dir) => {
                  const subGroups = groupFilesByParent(dir.files, dir.directory);
                  return (
                    <div key={dir.directory} className="dir-group">
                      <div className="dir-header">
                        <FolderOpen size={16} />
                        <span>{dir.directory.replace(/\/Users\/[^/]+\//, "~/")}</span>
                        <span className="dir-count">{dir.total_count} 个文件 · {formatSize(dir.total_size)} · 含子文件夹</span>
                      </div>
                      <div className="subfolder-list">
                        {subGroups.map((g) => {
                          const subKey = `${dir.directory}\0${g.parentDir}`;
                          const collapsed = collapsedSubfolders.has(subKey);
                          const allSel = g.files.length > 0 && g.files.every((f) => selectedFiles.has(f.path));
                          const sumSz = g.files.reduce((s, f) => s + f.size, 0);
                          return (
                            <div className="subfolder-block" key={subKey}>
                              <div className="subfolder-header">
                                <button
                                  type="button"
                                  className="subfolder-chevron"
                                  aria-label={collapsed ? "展开" : "折叠"}
                                  onClick={() => toggleSubfolderCollapsed(subKey)}
                                >
                                  <ChevronDown size={16} className={collapsed ? "subfolder-chevron-icon rotated" : "subfolder-chevron-icon"} />
                                </button>
                                <label className="subfolder-check">
                                  <input
                                    type="checkbox"
                                    checked={allSel}
                                    onChange={() => toggleFileGroup(g.files, !allSel)}
                                  />
                                </label>
                                <FolderOpen size={14} className="subfolder-folder-icon" />
                                <span className="subfolder-name" title={g.parentDir}>
                                  {g.rel}
                                </span>
                                <span className="subfolder-meta">
                                  {g.files.length} 个 · {formatSize(sumSz)}
                                </span>
                              </div>
                              {!collapsed && (
                                <div className="file-list file-list-nested">
                                  {g.files.map((f) => (
                                    <label className="file-row" key={f.path}>
                                      <input type="checkbox" checked={selectedFiles.has(f.path)} onChange={() => toggleFile(f.path)} />
                                      <span className="file-ext">{f.extension || "—"}</span>
                                      <span className="file-name">
                                        {f.storage_state === "icloud_placeholder" && (
                                          <span className="file-icloud-badge" title="仅 iCloud 云端；执行整理时会尝试下载到本地">
                                            <Cloud size={12} />
                                          </span>
                                        )}
                                        {f.name}
                                      </span>
                                      <span className="file-size">{formatSize(f.size)}</span>
                                    </label>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {classifyResult && (
              <div className="classify-panel">
                <div className="panel-header">
                  <Eye size={16} />
                  <span>
                    分类预览 — {classifyResult.length} 个文件
                    {classifyResult.length > classifyPreviewLimit && (
                      <span className="classify-preview-hint">
                        （列表显示前 {Math.min(classifyPreviewLimit, classifyResult.length)} 条，可加载更多）
                      </span>
                    )}
                  </span>
                  <div className="confidence-summary">
                    <span className="conf-badge high">{classifyStats.high} 高</span>
                    <span className="conf-badge mid">{classifyStats.mid} 中</span>
                    <span className="conf-badge low">{classifyStats.low} 低</span>
                  </div>
                </div>
                <div className="classify-list">
                  {classifyResult.slice(0, classifyPreviewLimit).map((item) => (
                    <div className="classify-row" key={item.original_path}>
                      <div className="classify-left">
                        <span className="classify-file">{item.original_path.split("/").pop()}</span>
                        <span className="classify-reason">{item.reason}</span>
                      </div>
                      <div className="classify-right">
                        <div className="classify-target">
                          {getCategoryIcon(item.target_folder)}
                          <span>{item.target_folder}</span>
                        </div>
                        <span className="conf-dot" style={{ background: confidenceColor(item.confidence) }}>
                          {confidenceLabel(item.confidence)} {Math.round(item.confidence * 100)}%
                        </span>
                        <span className={`source-tag ${item.source}`}>{item.source === "rule" ? "规则" : "AI"}</span>
                      </div>
                    </div>
                  ))}
                  {classifyResult.length > classifyPreviewLimit && (
                    <button
                      type="button"
                      className="btn btn-secondary classify-load-more"
                      onClick={() =>
                        setClassifyPreviewLimit((n) =>
                          Math.min(n + CLASSIFY_PREVIEW_PAGE, classifyResult.length),
                        )
                      }
                    >
                      加载更多（+{CLASSIFY_PREVIEW_PAGE}）
                    </button>
                  )}
                </div>
              </div>
            )}

            {scanData.length === 0 && !loading && (
              <div className="empty-state">
                <Scan size={48} strokeWidth={1} />
                <p>点击「扫描目录」开始整理文件</p>
                <p className="empty-sub">默认扫描下载/桌面/文档；可在「设置」中添加 iCloud Drive 等目录</p>
              </div>
            )}
          </div>
        )}

        {/* History */}
        {page === "history" && (
          <div className="page">
            <div className="page-header">
              <h1 className="page-title">操作历史</h1>
              <button className="btn btn-secondary" onClick={() => getHistory(historyPage).then((d) => setHistoryData(d.records))}>
                <RefreshCw size={16} /> 刷新
              </button>
            </div>
            <div className="history-table">
              <div className="table-header">
                <span className="col-time">时间</span>
                <span className="col-file">文件</span>
                <span className="col-from">来源</span>
                <span className="col-to">目标</span>
                <span className="col-action">操作</span>
              </div>
              {historyData.map((rec) => (
                <div className={`table-row ${rec.undone ? "undone" : ""}`} key={rec.id}>
                  <span className="col-time">{formatTime(rec.timestamp)}</span>
                  <span className="col-file">{rec.file_name}</span>
                  <span className="col-from">{rec.source_path.replace(/\/Users\/[^/]+\//, "~/")}</span>
                  <span className="col-to">{rec.dest_path.split("Organized/")[1] || rec.dest_path}</span>
                  <span className="col-action">
                    {rec.undone ? (
                      <span className="undone-label">已撤销</span>
                    ) : (
                      <button className="btn-icon" onClick={() => handleUndo(rec.id)} title="撤销">
                        <Undo2 size={14} />
                      </button>
                    )}
                  </span>
                </div>
              ))}
              {historyData.length === 0 && <p className="empty-hint table-empty">暂无操作记录</p>}
            </div>
            <div className="pagination">
              <button disabled={historyPage <= 1} onClick={() => setHistoryPage((p) => p - 1)}>上一页</button>
              <span>第 {historyPage} 页</span>
              <button onClick={() => setHistoryPage((p) => p + 1)}>下一页</button>
            </div>
          </div>
        )}

        {/* Browse organized files */}
        {page === "browse" && (
          <div className="page">
            <div className="page-header">
              <h1 className="page-title">已整理文件</h1>
              <div className="header-actions">
                <button className="btn btn-primary" onClick={() => openFolder("organized")}>
                  <ExternalLink size={16} /> 在 Finder 中打开
                </button>
                <button className="btn btn-secondary" onClick={() => getOrganizedTree().then((d) => { setOrganizedFolders(d.folders); setOrganizedBase(d.base); })}>
                  <RefreshCw size={16} /> 刷新
                </button>
              </div>
            </div>

            <div className="browse-base">
              <FolderOpen size={16} />
              <span>{organizedBase.replace(/\/Users\/[^/]+\//, "~/")}</span>
              <span className="browse-total">{organizedFolders.reduce((s, f) => s + f.count, 0)} 个文件</span>
            </div>

            <div className="browse-grid">
              {organizedFolders.map((folder) => {
                const topCategory = folder.relative.split("/")[0];
                return (
                  <div
                    className="browse-card"
                    key={folder.path}
                    onClick={() => openFolder(folder.path)}
                  >
                    <div className="browse-card-icon">{getCategoryIcon(topCategory)}</div>
                    <div className="browse-card-info">
                      <span className="browse-card-name">{folder.relative}</span>
                      <span className="browse-card-count">{folder.count} 个文件</span>
                    </div>
                    <ExternalLink size={14} className="browse-card-open" />
                  </div>
                );
              })}
              {organizedFolders.length === 0 && (
                <div className="empty-state">
                  <FolderTree size={48} strokeWidth={1} />
                  <p>还没有整理过文件</p>
                  <button className="btn btn-primary" onClick={() => setPage("organize")}>去整理文件</button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Settings */}
        {page === "settings" && (
          <div className="page">
            <h1 className="page-title">设置</h1>
            <div className="settings-panel">
              <div className="setting-group">
                <h3>监控目录</h3>
                {icloudHint && <p className="setting-desc">{icloudHint}</p>}
                {cfgLoading ? (
                  <p className="setting-desc">加载中…</p>
                ) : (
                  <>
                    <div className="setting-list setting-list-editable">
                      {cfgWatchDirs.map((dir, i) => (
                        <div className="setting-item setting-path-row" key={i}>
                          <input
                            type="text"
                            className="setting-path-input"
                            value={dir}
                            onChange={(e) => {
                              const next = [...cfgWatchDirs];
                              next[i] = e.target.value;
                              setCfgWatchDirs(next);
                            }}
                            placeholder="例如 ~/Downloads 或 iCloud 路径"
                          />
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => setCfgWatchDirs(cfgWatchDirs.filter((_, j) => j !== i))}
                            disabled={cfgWatchDirs.length <= 1}
                          >
                            移除
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="setting-actions-row">
                      <button type="button" className="btn btn-secondary" onClick={() => setCfgWatchDirs((p) => [...p, ""])}>
                        添加目录
                      </button>
                      <button type="button" className="btn btn-secondary" onClick={addIcloudWatchPreset}>
                        <Cloud size={14} /> 添加 iCloud Drive
                      </button>
                    </div>
                  </>
                )}
              </div>
              <div className="setting-group">
                <h3>整理目标</h3>
                <input
                  type="text"
                  className="setting-path-input setting-path-input-block"
                  value={cfgOrganizeBase}
                  onChange={(e) => setCfgOrganizeBase(e.target.value)}
                  placeholder="~/Organized"
                  disabled={cfgLoading}
                />
                <p className="setting-desc">整理后的文件将移动到此目录下的分类子文件夹中。可与监控目录同为 iCloud 路径以减少跨盘同步。</p>
              </div>
              <div className="setting-group">
                <h3>扫描行为</h3>
                <p className="setting-desc">默认会递归扫描监控目录内所有子文件夹；检测到项目根（如含 package.json）时整目录跳过；整理目标路径内不会再次扫描。</p>
                <div className="setting-item setting-scan-row">
                  <label className="setting-scan-label">扫描深度</label>
                  <select
                    className="setting-select"
                    value={String(cfgScanMaxDepth)}
                    onChange={(e) => setCfgScanMaxDepth(Number(e.target.value))}
                    disabled={cfgLoading}
                  >
                    <option value="-1">完全递归（推荐）</option>
                    <option value="0">仅监控目录顶层</option>
                    <option value="1">向下 1 层子文件夹</option>
                    <option value="2">向下 2 层子文件夹</option>
                  </select>
                </div>
                <label className="setting-item setting-scan-toggle">
                  <input
                    type="checkbox"
                    checked={cfgSkipProject}
                    onChange={(e) => setCfgSkipProject(e.target.checked)}
                    disabled={cfgLoading}
                  />
                  <span>跳过项目目录（含 package.json / .git / pyproject.toml 等标记时整树不扫）</span>
                </label>
                <label className="setting-item setting-scan-toggle">
                  <input
                    type="checkbox"
                    checked={cfgCleanupEmpty}
                    onChange={(e) => setCfgCleanupEmpty(e.target.checked)}
                    disabled={cfgLoading}
                  />
                  <span>整理完成后删除因此变空的文件夹（不删除监控根与整理根）</span>
                </label>
              </div>
              <div className="setting-group">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => void savePathSettings()}
                  disabled={cfgLoading || cfgSaving}
                >
                  {cfgSaving ? "保存中…" : "保存路径与扫描配置"}
                </button>
              </div>
              <div className="setting-group">
                <h3>AI 模型</h3>
                <div className="setting-item highlight">
                  <span className="provider-badge deepseek">DeepSeek V3</span>
                  deepseek-chat — 当前使用
                </div>
                <div className="setting-item">
                  <span className="provider-badge openai">OpenAI</span>
                  gpt-4o-mini — 备选
                </div>
                <div className="setting-item">
                  <span className="provider-badge gemini">Gemini</span>
                  gemini-2.0-flash — 备选
                </div>
                <p className="setting-desc" style={{marginTop: 8}}>
                  切换 provider 请编辑 backend/config.yaml 中的 ai.provider 字段。
                  支持: deepseek / openai / gemini / siliconflow
                </p>
              </div>
              <div className="setting-group">
                <h3>实时监控</h3>
                <button className={`btn ${watcherRunning ? "btn-danger" : "btn-primary"}`} onClick={toggleWatcher}>
                  {watcherRunning ? <Square size={16} /> : <Play size={16} />}
                  {watcherRunning ? "停止监控" : "开启监控"}
                </button>
              </div>
              <div className="setting-group">
                <h3>安全设置</h3>
                <p className="setting-desc">默认启用 dry_run 模式，所有操作需要确认后才会执行。已执行的操作可以在历史页面撤销。</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
