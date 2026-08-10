'use client';

import { useState, useCallback } from 'react';
import {
  Globe, Search, Loader2, Download, Trash2, CheckCircle2,
  AlertTriangle, BarChart3, FileSpreadsheet, Settings2, ChevronDown,
  ChevronRight, Database, Sparkles, ArrowRight, Eye, Layers,
  GitBranch, Radar, Brain, MessageSquare, Fingerprint, Zap,
  FileJson, FileText, FileCode, Wand2, Clock, Info,
} from 'lucide-react';
import { useToast } from '@/components/Toast';
import {
  scraping,
  type ScrapeJob,
  type ScrapePreview,
  type AdvancedAnalysis,
  type SentimentAnalysis,
  type PatternAnalysis,
} from '@/lib/api';

type ScrapeMode = 'single' | 'batch' | 'recursive' | 'discover';
type UltraTab =
  | 'auth' | 'fingerprint' | 'distributed' | 'target'
  | 'automl' | 'anomaly' | 'forecast' | 'cluster'
  | 'features' | 'enrich' | 'validate' | 'dimreduce'
  | 'diff' | 'webhook' | 'scheduling' | 'ratelimit';
type UltraGroup = 'scraping' | 'ml' | 'data' | 'tools';

const ULTRA_GROUPS: { id: UltraGroup; label: string; icon: any; tabs: { id: UltraTab; label: string; icon: any }[] }[] = [
  { id: 'scraping', label: 'Scraping', icon: Globe, tabs: [
    { id: 'auth', label: 'Auth', icon: Globe },
    { id: 'fingerprint', label: 'Fingerprint', icon: Fingerprint },
    { id: 'distributed', label: 'Distributed', icon: Layers },
    { id: 'target', label: 'Target', icon: Radar },
  ]},
  { id: 'ml', label: 'Machine Learning', icon: Brain, tabs: [
    { id: 'automl', label: 'AutoML', icon: Brain },
    { id: 'anomaly', label: 'Anomaly', icon: AlertTriangle },
    { id: 'forecast', label: 'Forecast', icon: BarChart3 },
    { id: 'cluster', label: 'Cluster', icon: Database },
  ]},
  { id: 'data', label: 'Data Processing', icon: Sparkles, tabs: [
    { id: 'features', label: 'Features', icon: Sparkles },
    { id: 'enrich', label: 'Enrich', icon: Search },
    { id: 'validate', label: 'Validate', icon: CheckCircle2 },
    { id: 'dimreduce', label: 'Dim Reduce', icon: Radar },
  ]},
  { id: 'tools', label: 'Tools', icon: Settings2, tabs: [
    { id: 'diff', label: 'Diff', icon: GitBranch },
    { id: 'webhook', label: 'Webhook', icon: Zap },
    { id: 'scheduling', label: 'Schedule', icon: Clock },
    { id: 'ratelimit', label: 'Rate Limit', icon: AlertTriangle },
  ]},
];

function RequireResult({ result, children }: { result: ScrapeJob | null; children: React.ReactNode }) {
  if (!result) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center">
          <Info className="w-8 h-8 text-primary-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Butuh Data Scraping Dulu</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-sm mx-auto">
          Jalankan scraping terlebih dahulu menggunakan mode di atas.
        </p>
        <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
          <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">1. Scrape</span>
          <ArrowRight className="w-3 h-3" />
          <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">2. Pilih Tab</span>
          <ArrowRight className="w-3 h-3" />
          <span className="px-2 py-1 bg-primary-50 dark:bg-primary-900/30 text-primary-600 rounded">3. Analisis</span>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}

function JsonResult({ data, title }: { data: any; title?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {title && (
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">{title}</p>
        </div>
      )}
      <pre className="p-4 text-xs bg-gray-50 dark:bg-gray-900 overflow-auto max-h-80 font-mono text-gray-700 dark:text-gray-300">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function LoadingOverlay({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      <p className="text-sm text-gray-500 dark:text-gray-400">{text}</p>
    </div>
  );
}

function RequiredInput({ label, value, onChange, placeholder, type = 'text' }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">{label} <span className="text-red-500">*</span></label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className={`w-full px-3 py-2 border rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
          value.trim() ? 'border-gray-300 dark:border-gray-600' : 'border-gray-300 dark:border-gray-600'
        }`} />
    </div>
  );
}

function InputField({ label, value, onChange, placeholder, type = 'text' }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
    </div>
  );
}

export default function ScrapingPage() {
  const { toast } = useToast();
  const [mode, setMode] = useState<ScrapeMode>('single');
  const [url, setUrl] = useState('');
  const [batchUrls, setBatchUrls] = useState('');
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxPages, setMaxPages] = useState(10);
  const [previewData, setPreviewData] = useState<ScrapePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [processingLoading, setProcessingLoading] = useState(false);
  const [processingText, setProcessingText] = useState('');
  const [result, setResult] = useState<ScrapeJob | null>(null);
  const [jobs, setJobs] = useState<ScrapeJob[]>([]);
  const [showJobs, setShowJobs] = useState(false);
  const [importing, setImporting] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'advanced' | 'sentiment' | 'patterns' | 'export' | 'transform' | 'ultra'>('overview');
  const [ultraGroup, setUltraGroup] = useState<UltraGroup>('scraping');
  const [ultraTab, setUltraTab] = useState<UltraTab>('auth');
  const [ultraLoading, setUltraLoading] = useState(false);
  const [ultraLoadingText, setUltraLoadingText] = useState('');
  const [ultraResult, setUltraResult] = useState<any>(null);
  const [exporting, setExporting] = useState(false);
  const [autoCleaning, setAutoCleaning] = useState(false);
  const [useSelenium, setUseSelenium] = useState(false);
  const [autoRename, setAutoRename] = useState(true);
  const [deduplicate, setDeduplicate] = useState(true);
  const [detectTypes, setDetectTypes] = useState(true);
  const [clusterText, setClusterText] = useState(false);
  const [runAdvanced, setRunAdvanced] = useState(true);
  const [runSentiment, setRunSentiment] = useState(true);
  const [runPatterns, setRunPatterns] = useState(true);
  const [authTargetUrl, setAuthTargetUrl] = useState('');
  const [authLoginUrl, setAuthLoginUrl] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [distUrls, setDistUrls] = useState('');
  const [distStrategy, setDistStrategy] = useState('round_robin');
  const [distMaxPerWorker, setDistMaxPerWorker] = useState(10);
  const [targetUrl, setTargetUrl] = useState('');
  const [automlTargetCol, setAutomlTargetCol] = useState('');
  const [automlTask, setAutomlTask] = useState('');
  const [forecastValueCol, setForecastValueCol] = useState('');
  const [forecastPeriods, setForecastPeriods] = useState(10);
  const [selectedTransforms, setSelectedTransforms] = useState<string[]>([]);
  const [transformLoading, setTransformLoading] = useState(false);
  const [transformResult, setTransformResult] = useState<any>(null);
  const [diffOldJobId, setDiffOldJobId] = useState('');
  const [diffNewJobId, setDiffNewJobId] = useState('');
  const [webhookName, setWebhookName] = useState('');
  const [webhookUrls, setWebhookUrls] = useState('');
  const [webhookSlack, setWebhookSlack] = useState('');
  const [webhookDiscord, setWebhookDiscord] = useState('');
  const [schedName, setSchedName] = useState('');
  const [schedUrls, setSchedUrls] = useState('');
  const [schedInterval, setSchedInterval] = useState(60);
  const [schedList, setSchedList] = useState<any[]>([]);
  const [rlDomain, setRlDomain] = useState('');
  const [rlDelay, setRlDelay] = useState(1000);
  const [rlStats, setRlStats] = useState<any>(null);
  const [dimMethod, setDimMethod] = useState('auto');
  const [dimComponents, setDimComponents] = useState(2);

  const handlePreview = useCallback(async () => {
    if (!url.trim()) return;
    setLoading(true); setPreviewData(null); setResult(null);
    try { const res = await scraping.preview(url.trim()); setPreviewData(res.data); }
    catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal scrape URL'); }
    finally { setLoading(false); }
  }, [url, toast]);

  const handleScrapeAndProcess = useCallback(async () => {
    if (!url.trim()) return;
    setProcessingLoading(true); setProcessingText('Scraping & menganalisis...'); setResult(null);
    try {
      const res = await scraping.scrapeAndProcess({ url: url.trim(), auto_rename: autoRename, deduplicate, detect_types: detectTypes, cluster_text: clusterText, run_advanced_analysis: runAdvanced, run_sentiment: runSentiment, run_patterns: runPatterns, use_selenium: useSelenium });
      setResult(res.data); toast('success', `${res.data.clean_row_count} baris, kualitas: ${res.data.quality_score}%`); setActiveTab('overview');
    } catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal scrape'); }
    finally { setProcessingLoading(false); setProcessingText(''); }
  }, [url, autoRename, deduplicate, detectTypes, clusterText, runAdvanced, runSentiment, runPatterns, useSelenium, toast]);

  const handleBatchScrape = useCallback(async () => {
    const urls = batchUrls.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'));
    if (urls.length === 0) return;
    setProcessingLoading(true); setProcessingText(`Scraping ${urls.length} URL...`); setResult(null);
    try {
      const res = await scraping.batchScrape({ urls, run_advanced_analysis: runAdvanced, run_sentiment: runSentiment, run_patterns: runPatterns, use_selenium: useSelenium });
      setResult(res.data); toast('success', `${res.data.clean_row_count} baris dari ${urls.length} URL`); setActiveTab('overview');
    } catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal batch'); }
    finally { setProcessingLoading(false); setProcessingText(''); }
  }, [batchUrls, runAdvanced, runSentiment, runPatterns, useSelenium, toast]);

  const handleRecursiveScrape = useCallback(async () => {
    if (!url.trim()) return;
    setProcessingLoading(true); setProcessingText(`Recursive (depth: ${maxDepth})...`); setResult(null);
    try {
      const res = await scraping.recursiveScrape({ url: url.trim(), max_depth: maxDepth, max_pages: maxPages, run_advanced_analysis: runAdvanced, use_selenium: useSelenium });
      setResult(res.data); toast('success', `${res.data.clean_row_count} baris`); setActiveTab('overview');
    } catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal recursive'); }
    finally { setProcessingLoading(false); setProcessingText(''); }
  }, [url, maxDepth, maxPages, runAdvanced, useSelenium, toast]);

  const handleDiscoverScrape = useCallback(async () => {
    if (!url.trim()) return;
    setProcessingLoading(true); setProcessingText('Auto-discover...'); setResult(null);
    try {
      const res = await scraping.discoverScrape({ url: url.trim(), max_pages: maxPages, run_advanced_analysis: runAdvanced, use_selenium: useSelenium });
      setResult(res.data); toast('success', `${res.data.clean_row_count} baris`); setActiveTab('overview');
    } catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal discover'); }
    finally { setProcessingLoading(false); setProcessingText(''); }
  }, [url, maxPages, runAdvanced, useSelenium, toast]);

  const handleLoadJobs = useCallback(async () => {
    try { const res = await scraping.jobs(20); setJobs(res.data); setShowJobs(true); }
    catch { toast('error', 'Gagal memuat riwayat'); }
  }, [toast]);

  const handleImport = useCallback(async (jobId: string) => {
    setImporting(jobId);
    try { const res = await scraping.importToDataset({ job_id: jobId }); toast('success', `Dataset "${res.data.name}" (${res.data.row_count} baris)`); }
    catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal import'); }
    finally { setImporting(null); }
  }, [toast]);

  const handleDelete = useCallback(async (jobId: string) => {
    try { await scraping.deleteJob(jobId); setJobs(p => p.filter(j => j.id !== jobId)); toast('success', 'Dihapus'); }
    catch { toast('error', 'Gagal hapus'); }
  }, [toast]);

  const handleExport = useCallback(async (jobId: string, formats: string[]) => {
    setExporting(true);
    try { const res = await scraping.exportData({ job_id: jobId, formats }); toast('success', `Export: ${Object.keys(res.data.results).join(', ')}`); return res.data; }
    catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal export'); }
    finally { setExporting(false); }
  }, [toast]);

  const handleAutoClean = useCallback(async (jobId: string) => {
    setAutoCleaning(true);
    try { const res = await scraping.autoClean(jobId); toast('success', `Clean: ${res.data.result.columns_modified?.length || 0} kolom`); return res.data; }
    catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal clean'); }
    finally { setAutoCleaning(false); }
  }, [toast]);

  const runUltra = useCallback(async (text: string, fn: () => Promise<any>) => {
    if (!result) { toast('error', 'Jalankan scraping dulu'); return; }
    setUltraLoading(true); setUltraLoadingText(text); setUltraResult(null);
    try { const res = await fn(); setUltraResult(res.data); toast('success', `${text.replace('...', '')} selesai!`); }
    catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal'); }
    finally { setUltraLoading(false); setUltraLoadingText(''); }
  }, [result, toast]);

  const handleAuthScrape = useCallback(() => runUltra('Auth scrape...', () =>
    scraping.authScrape({ url: authTargetUrl.trim(), login_url: authLoginUrl.trim(), username: authUsername.trim(), password: authPassword.trim(), auth_type: 'session' })
  ), [authTargetUrl, authLoginUrl, authUsername, authPassword, runUltra]);

  const handleDistributedScrape = useCallback(() => {
    const urls = distUrls.split('\n').map(u => u.trim()).filter(u => u.startsWith('http'));
    if (urls.length === 0) { toast('error', 'Masukkan minimal 1 URL'); return; }
    runUltra('Distributed scrape...', async () => {
      const c = await scraping.createDistributedJob({ urls, strategy: distStrategy, max_per_worker: distMaxPerWorker });
      return scraping.executeDistributed(c.data.job_id);
    });
  }, [distUrls, distStrategy, distMaxPerWorker, runUltra, toast]);

  const handleTargetScrape = useCallback((type: string) => {
    if (!targetUrl.trim()) { toast('error', 'URL wajib'); return; }
    runUltra(`Target (${type})...`, () => scraping.targetScrape({ url: targetUrl.trim(), target_type: type }));
  }, [targetUrl, runUltra, toast]);

  const handleAutoML = useCallback(() => {
    if (!automlTargetCol.trim()) { toast('error', 'Target column wajib'); return; }
    runUltra('AutoML training...', () => scraping.runAutoML({ job_id: result!.id, target_column: automlTargetCol.trim(), task: automlTask || undefined }));
  }, [automlTargetCol, automlTask, result, runUltra, toast]);

  const handleAnomaly = useCallback(() => runUltra('Deteksi anomali...', () => scraping.detectAnomalies({ job_id: result!.id, method: 'all' })), [result, runUltra]);
  const handleForecast = useCallback(() => {
    if (!forecastValueCol.trim()) { toast('error', 'Value column wajib'); return; }
    runUltra('Forecasting...', () => scraping.forecastData({ job_id: result!.id, value_column: forecastValueCol.trim(), periods: forecastPeriods }));
  }, [forecastValueCol, forecastPeriods, result, runUltra, toast]);
  const handleCluster = useCallback(() => runUltra('Clustering...', () => scraping.clusterData({ job_id: result!.id, method: 'auto' })), [result, runUltra]);
  const handleFeatures = useCallback(() => runUltra('Feature engineering...', () => scraping.engineerFeatures({ job_id: result!.id, feature_types: ['all'] })), [result, runUltra]);
  const handleEnrich = useCallback(() => runUltra('Enrichment...', () => scraping.enrichData({ job_id: result!.id, enrichments: ['all'] })), [result, runUltra]);
  const handleValidate = useCallback(() => runUltra('Validasi...', () => scraping.validateData({ job_id: result!.id, remove_invalid: false })), [result, runUltra]);
  const handleDimReduce = useCallback(() => runUltra('Reduksi dimensi...', () => scraping.reduceDimensions({ job_id: result!.id, method: dimMethod, n_components: dimComponents })), [dimMethod, dimComponents, result, runUltra]);

  const handleDiff = useCallback(() => {
    if (!diffOldJobId.trim() || !diffNewJobId.trim()) { toast('error', 'Isi kedua Job ID'); return; }
    runUltra('Membandingkan...', () => scraping.diffScrapes({ job_id_old: diffOldJobId.trim(), job_id_new: diffNewJobId.trim() }));
  }, [diffOldJobId, diffNewJobId, runUltra, toast]);

  const handleTransform = useCallback(async () => {
    if (!result || selectedTransforms.length === 0) { toast('error', 'Pilih minimal 1 transformasi'); return; }
    setTransformLoading(true); setTransformResult(null);
    try { const rules = selectedTransforms.map(op => ({ operation: op, column: '*' })); const res = await scraping.transformData({ job_id: result.id, rules }); setTransformResult(res.data); toast('success', `${res.data.result?.operations_applied?.length || 0} operasi`); }
    catch (err: any) { toast('error', err?.response?.data?.detail || 'Gagal'); }
    finally { setTransformLoading(false); }
  }, [result, selectedTransforms, toast]);

  const toggleTransform = (op: string) => setSelectedTransforms(p => p.includes(op) ? p.filter(x => x !== op) : [...p, op]);
  const advanced = result?.advanced_analysis as AdvancedAnalysis | undefined;
  const sentiment = result?.sentiment_analysis as SentimentAnalysis | undefined;
  const patterns = result?.pattern_analysis as PatternAnalysis | undefined;
  const currentGroup = ULTRA_GROUPS.find(g => g.id === ultraGroup) || ULTRA_GROUPS[0];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Globe className="w-6 h-6 text-primary-600" /> Web Scraping & Super Analysis
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Scrape data dari website manapun, proses dengan ML, analisis statistik mendalam, sentimen, dan deteksi pola.</p>
      </div>

      {/* Mode Selector */}
      <div className="flex gap-2 mb-6">
        {[{ id: 'single', label: 'Single URL', icon: Globe }, { id: 'batch', label: 'Batch URLs', icon: Layers }, { id: 'recursive', label: 'Recursive', icon: GitBranch }, { id: 'discover', label: 'Auto Discover', icon: Radar }].map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setMode(id as ScrapeMode)} className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${mode === id ? 'bg-primary-600 text-white shadow-sm' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'}`}>
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>

      {/* Input Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
        {mode === 'batch' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">URLs (satu per baris)</label>
            <textarea value={batchUrls} onChange={e => setBatchUrls(e.target.value)} placeholder={"https://example.com/data1\nhttps://example.com/data2"} rows={5} className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 font-mono text-sm" />
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">URL Website</label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input type="url" value={url} onChange={e => setUrl(e.target.value)} onKeyDown={e => e.key === 'Enter' && handlePreview()} placeholder="https://example.com/data" className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500" />
              </div>
              {mode === 'single' && (
                <button onClick={handlePreview} disabled={loading || !url.trim()} className="px-5 py-3 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition flex items-center gap-2">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Preview
                </button>
              )}
            </div>
          </div>
        )}
        {(mode === 'recursive' || mode === 'discover') && (
          <div className="flex gap-4 mt-4">
            <div><label className="block text-xs text-gray-500 mb-1">Max Depth</label><input type="number" value={maxDepth} onChange={e => setMaxDepth(+e.target.value)} min={1} max={5} className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm" /></div>
            <div><label className="block text-xs text-gray-500 mb-1">Max Pages</label><input type="number" value={maxPages} onChange={e => setMaxPages(+e.target.value)} min={1} max={50} className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm" /></div>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-3">
          <ToggleChip label="Auto Rename" active={autoRename} onClick={() => setAutoRename(!autoRename)} />
          <ToggleChip label="Hapus Duplikat" active={deduplicate} onClick={() => setDeduplicate(!deduplicate)} />
          <ToggleChip label="Deteksi Tipe" active={detectTypes} onClick={() => setDetectTypes(!detectTypes)} />
          <ToggleChip label="Text Clustering" active={clusterText} onClick={() => setClusterText(!clusterText)} />
          <ToggleChip label="Advanced" active={runAdvanced} onClick={() => setRunAdvanced(!runAdvanced)} icon={Brain} />
          <ToggleChip label="Sentimen" active={runSentiment} onClick={() => setRunSentiment(!runSentiment)} icon={MessageSquare} />
          <ToggleChip label="Pola" active={runPatterns} onClick={() => setRunPatterns(!runPatterns)} icon={Fingerprint} />
          <ToggleChip label="JS Render" active={useSelenium} onClick={() => setUseSelenium(!useSelenium)} icon={Zap} />
        </div>
        <div className="mt-4 flex gap-2 items-center">
          {mode === 'single' && <button onClick={handleScrapeAndProcess} disabled={processingLoading || !url.trim()} className="px-5 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2 shadow-sm">{processingLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} {processingText || 'Scrape & Analyze'}</button>}
          {mode === 'batch' && <button onClick={handleBatchScrape} disabled={processingLoading || !batchUrls.trim()} className="px-5 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2 shadow-sm">{processingLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />} {processingText || 'Batch Scrape'}</button>}
          {mode === 'recursive' && <button onClick={handleRecursiveScrape} disabled={processingLoading || !url.trim()} className="px-5 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2 shadow-sm">{processingLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitBranch className="w-4 h-4" />} {processingText || 'Recursive Scrape'}</button>}
          {mode === 'discover' && <button onClick={handleDiscoverScrape} disabled={processingLoading || !url.trim()} className="px-5 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2 shadow-sm">{processingLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radar className="w-4 h-4" />} {processingText || 'Auto Discover'}</button>}
          {processingLoading && <span className="text-sm text-gray-500 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> {processingText}</span>}
        </div>
      </div>

      {/* Preview Results */}
      {previewData && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2"><Eye className="w-5 h-5" /> Preview: {previewData.title}</h2>
          <div className="flex flex-wrap gap-4 mb-4 text-sm text-gray-500 dark:text-gray-400">
            <StatBadge icon={FileSpreadsheet} value={previewData.row_count} label="baris" />
            <StatBadge icon={Database} value={previewData.column_count} label="kolom" />
            <StatBadge icon={BarChart3} value={previewData.tables.length} label="tabel" />
            <StatBadge icon={Globe} value={previewData.links?.length || 0} label="links" />
            <StatBadge icon={Zap} value={`${previewData.scrape_duration_ms}ms`} label="waktu" />
          </div>
          {previewData.keywords && previewData.keywords.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">{previewData.keywords.slice(0, 10).map((kw, i) => (<span key={i} className="px-2 py-1 text-xs bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full">{kw}</span>))}</div>
          )}
          {previewData.tables.slice(0, 3).map((table, i) => (
            <div key={i} className="mb-4 overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
              <p className="px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900">Tabel {i + 1} ({table.row_count} baris)</p>
              <table className="min-w-full text-sm"><thead><tr className="bg-gray-50 dark:bg-gray-800">{table.headers.map(h => (<th key={h} className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">{h}</th>))}</tr></thead>
                <tbody>{table.rows.slice(0, 5).map((row, ri) => (<tr key={ri} className="border-t border-gray-100 dark:border-gray-800">{table.headers.map(h => (<td key={h} className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">{row[h] != null ? String(row[h]).slice(0, 80) : '-'}</td>))}</tr>))}</tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* ML Processing Result */}
      {result && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2"><Sparkles className="w-5 h-5 text-primary-600" /> Hasil Super Analysis</h2>
            <button onClick={() => handleImport(result.id)} disabled={importing === result.id} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition flex items-center gap-2 shadow-sm">
              {importing === result.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Import Dataset
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <StatCard label="Raw Data" value={result.raw_row_count} />
            <StatCard label="Bersih" value={result.clean_row_count} />
            <StatCard label="Duplikat" value={result.duplicates_removed} color="text-orange-600" />
            <StatCard label="Kualitas" value={`${result.quality_score}%`} color={result.quality_score >= 70 ? 'text-green-600' : 'text-red-600'} />
            {advanced && <StatCard label="Outliers" value={advanced.outlier_summary?.total_outlier_rows || 0} color="text-purple-600" />}
          </div>
          <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-700 pb-2 overflow-x-auto">
            {[{ id: 'overview', label: 'Overview', icon: BarChart3 }, { id: 'advanced', label: 'Statistik', icon: Brain }, { id: 'sentiment', label: 'Sentimen', icon: MessageSquare }, { id: 'patterns', label: 'Pola', icon: Fingerprint }, { id: 'export', label: 'Export', icon: Download }, { id: 'transform', label: 'Transform', icon: Wand2 }, { id: 'ultra', label: 'Ultra', icon: Zap }].map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setActiveTab(id as any)} className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition whitespace-nowrap ${activeTab === id ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'}`}><Icon className="w-4 h-4" />{label}</button>
            ))}
          </div>

          {activeTab === 'overview' && (
            <div className="space-y-4">
              {result.ml_processing_applied.length > 0 && (<div className="flex flex-wrap gap-2">{result.ml_processing_applied.map(p => (<span key={p} className="px-2 py-1 text-xs bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded-full">{p}</span>))}</div>)}
              {advanced?.insights && advanced.insights.length > 0 && (<div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg"><h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">Insights</h3><ul className="space-y-1">{advanced.insights.map((ins, i) => (<li key={i} className="text-sm text-blue-700 dark:text-blue-400">• {ins}</li>))}</ul></div>)}
              {advanced?.auto_viz_suggestions && advanced.auto_viz_suggestions.length > 0 && (<div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg"><h3 className="text-sm font-medium text-purple-800 dark:text-purple-300 mb-2">Rekomendasi Visualisasi</h3><div className="flex flex-wrap gap-2">{advanced.auto_viz_suggestions.map((s, i) => (<span key={i} className="px-2 py-1 text-xs bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300 rounded">{s}</span>))}</div></div>)}
              {sentiment?.summary && (<div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg"><h3 className="text-sm font-medium text-green-800 dark:text-green-300 mb-1">Sentimen</h3><p className="text-sm text-green-700 dark:text-green-400">{sentiment.summary}</p></div>)}
              {patterns?.summary && (<div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg"><h3 className="text-sm font-medium text-orange-800 dark:text-orange-300 mb-1">Pola Terdeteksi</h3><p className="text-sm text-orange-700 dark:text-orange-400">{patterns.summary}</p></div>)}
            </div>
          )}

          {activeTab === 'advanced' && advanced && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <InfoCard title="Korelasi Kuat" items={(advanced.correlations?.strong_pairs || []).slice(0, 8).map((p: any) => `${p.col_1} ↔ ${p.col_2}: ${p.correlation} (${p.strength})`)} />
                <InfoCard title="Outlier" items={Object.entries(advanced.outlier_summary?.columns || {}).slice(0, 8).map(([col, data]: [string, any]) => `${col}: ${data.count} outlier (${data.pct}%)`)} />
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm"><thead><tr className="bg-gray-50 dark:bg-gray-900"><th className="px-3 py-2 text-left">Kolom</th><th className="px-3 py-2 text-left">Tipe</th><th className="px-3 py-2 text-left">Null%</th><th className="px-3 py-2 text-left">Unique</th><th className="px-3 py-2 text-left">Entropy</th><th className="px-3 py-2 text-left">Rekomendasi</th></tr></thead>
                  <tbody>{advanced.columns.map((col, i) => (<tr key={i} className="border-t border-gray-100 dark:border-gray-800"><td className="px-3 py-2 font-medium">{col.name}</td><td className="px-3 py-2"><span className={`px-2 py-0.5 text-xs rounded ${col.is_numeric ? 'bg-blue-100 text-blue-700' : col.is_categorical ? 'bg-green-100 text-green-700' : col.is_text ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700'}`}>{col.is_numeric ? 'Numeric' : col.is_categorical ? 'Kategori' : col.is_text ? 'Teks' : col.dtype}</span></td><td className="px-3 py-2">{col.null_pct}%</td><td className="px-3 py-2">{col.unique_count}</td><td className="px-3 py-2">{col.entropy?.toFixed(2)}</td><td className="px-3 py-2 text-xs text-gray-500">{col.recommendation}</td></tr>))}</tbody>
                </table>
              </div>
              {advanced.recommendations && advanced.recommendations.length > 0 && (<div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg"><h3 className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-2">Rekomendasi ML</h3><ul className="space-y-1">{advanced.recommendations.map((r, i) => (<li key={i} className="text-sm text-amber-700 dark:text-amber-400">• {r}</li>))}</ul></div>)}
            </div>
          )}

          {activeTab === 'sentiment' && sentiment && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4 mb-4">
                <StatCard label="Positif" value={`${sentiment.distribution?.positive_pct || 0}%`} color="text-green-600" />
                <StatCard label="Negatif" value={`${sentiment.distribution?.negative_pct || 0}%`} color="text-red-600" />
                <StatCard label="Netral" value={`${sentiment.distribution?.neutral_pct || 0}%`} color="text-gray-600" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg"><h3 className="text-sm font-medium text-green-800 dark:text-green-300 mb-2">Kata Positif</h3><div className="flex flex-wrap gap-1">{(sentiment.top_positive_words || []).slice(0, 15).map((w, i) => (<span key={i} className="px-2 py-0.5 text-xs bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300 rounded">{w.word} ({w.count})</span>))}</div></div>
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg"><h3 className="text-sm font-medium text-red-800 dark:text-red-300 mb-2">Kata Negatif</h3><div className="flex flex-wrap gap-1">{(sentiment.top_negative_words || []).slice(0, 15).map((w, i) => (<span key={i} className="px-2 py-0.5 text-xs bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300 rounded">{w.word} ({w.count})</span>))}</div></div>
              </div>
              {sentiment.column_sentiments && Object.keys(sentiment.column_sentiments).length > 0 && (
                <div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr className="bg-gray-50 dark:bg-gray-900"><th className="px-3 py-2 text-left">Kolom</th><th className="px-3 py-2 text-left">Avg Score</th><th className="px-3 py-2 text-left">Pos</th><th className="px-3 py-2 text-left">Neg</th><th className="px-3 py-2 text-left">Netral</th></tr></thead>
                  <tbody>{Object.entries(sentiment.column_sentiments).map(([col, data]: [string, any]) => (<tr key={col} className="border-t border-gray-100 dark:border-gray-800"><td className="px-3 py-2 font-medium">{col}</td><td className="px-3 py-2">{data.avg_score?.toFixed(3)}</td><td className="px-3 py-2 text-green-600">{data.distribution?.positive}</td><td className="px-3 py-2 text-red-600">{data.distribution?.negative}</td><td className="px-3 py-2 text-gray-500">{data.distribution?.neutral}</td></tr>))}</tbody>
                </table></div>
              )}
            </div>
          )}

          {activeTab === 'patterns' && patterns && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <StatCard label="Regex" value={patterns.regex_patterns?.length || 0} color="text-blue-600" />
                <StatCard label="Value Patterns" value={patterns.value_patterns?.length || 0} color="text-green-600" />
                <StatCard label="Anomalies" value={patterns.anomaly_patterns?.length || 0} color="text-red-600" />
                <StatCard label="Encoding" value={patterns.encoding_patterns?.length || 0} color="text-purple-600" />
              </div>
              {patterns.regex_patterns && patterns.regex_patterns.length > 0 && (<div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg"><h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">Regex Patterns</h3><div className="space-y-1">{patterns.regex_patterns.slice(0, 10).map((p, i) => (<div key={i} className="text-sm text-blue-700 dark:text-blue-400"><span className="font-mono bg-blue-100 dark:bg-blue-800 px-1 rounded">{p.pattern}</span> di <strong>{p.column}</strong> — {p.match_count} match ({p.match_pct}%)</div>))}</div></div>)}
              {patterns.anomaly_patterns && patterns.anomaly_patterns.length > 0 && (<div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg"><h3 className="text-sm font-medium text-red-800 dark:text-red-300 mb-2">Anomali</h3><div className="space-y-1">{patterns.anomaly_patterns.slice(0, 8).map((p, i) => (<div key={i} className="text-sm text-red-700 dark:text-red-400"><strong>{p.column}</strong>: {p.insight}</div>))}</div></div>)}
              {patterns.text_patterns && patterns.text_patterns.length > 0 && (<div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg"><h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-2">Pola Teks</h3><div className="space-y-1">{patterns.text_patterns.slice(0, 8).map((p, i) => (<div key={i} className="text-sm text-yellow-700 dark:text-yellow-400"><strong>{p.column}</strong>: {p.insight}</div>))}</div></div>)}
            </div>
          )}

          {activeTab === 'export' && result && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2"><Download className="w-5 h-5" /> Export Data</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[{ fmt: 'csv', label: 'CSV', icon: FileText, desc: 'Comma-separated' }, { fmt: 'json', label: 'JSON', icon: FileJson, desc: 'JSON format' }, { fmt: 'excel', label: 'Excel', icon: FileSpreadsheet, desc: '.xlsx' }, { fmt: 'parquet', label: 'Parquet', icon: Database, desc: 'Columnar' }, { fmt: 'xml', label: 'XML', icon: FileCode, desc: 'Markup' }, { fmt: 'sql', label: 'SQL', icon: FileCode, desc: 'INSERT statements' }].map(({ fmt, label, icon: Icon, desc }) => (
                  <button key={fmt} onClick={() => handleExport(result.id, [fmt])} disabled={exporting} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition text-left"><div className="flex items-center gap-2 mb-1"><Icon className="w-5 h-5 text-primary-600" /><span className="font-medium text-gray-900 dark:text-white">{label}</span></div><p className="text-xs text-gray-500">{desc}</p></button>
                ))}
              </div>
              <button onClick={() => handleExport(result.id, ['csv', 'json', 'excel'])} disabled={exporting} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2">
                {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Export Semua (CSV + JSON + Excel)
              </button>
            </div>
          )}

          {activeTab === 'transform' && result && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2"><Wand2 className="w-5 h-5" /> Data Transformation</h2>
              <button onClick={() => handleAutoClean(result.id)} disabled={autoCleaning} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition flex items-center gap-2">
                {autoCleaning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Auto-Clean Data
              </button>
              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Transformations</h3>
                <div className="flex flex-wrap gap-2">
                  {['lowercase', 'uppercase', 'strip', 'remove_html', 'extract_numbers', 'extract_emails', 'to_numeric', 'fill_na_mean', 'fill_na_zero', 'remove_duplicates', 'normalize_text', 'add_length', 'add_word_count', 'label_encode'].map(op => (
                    <button key={op} onClick={() => toggleTransform(op)} className={`px-3 py-1.5 text-xs rounded-full border transition font-medium ${selectedTransforms.includes(op) ? 'bg-primary-100 dark:bg-primary-900/30 border-primary-300 text-primary-700 dark:text-primary-300' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}>{op.replace(/_/g, ' ')}</button>
                  ))}
                </div>
              </div>
              <button onClick={handleTransform} disabled={transformLoading || selectedTransforms.length === 0} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2">
                {transformLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Apply {selectedTransforms.length} Transform{selectedTransforms.length !== 1 ? 's' : ''}
              </button>
              {transformResult && (<div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg"><p className="text-sm font-medium text-green-800">{transformResult.result?.summary || 'Complete'}</p>{transformResult.preview && (<pre className="mt-2 text-xs overflow-auto max-h-40 font-mono">{JSON.stringify(transformResult.preview.slice(0, 5), null, 2)}</pre>)}</div>)}
            </div>
          )}

          {/* Ultra Tab */}
          {activeTab === 'ultra' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2"><Zap className="w-5 h-5" /> Ultra Scraping Features</h2>
              <div className="flex gap-2">
                {ULTRA_GROUPS.map(g => { const Icon = g.icon; return (<button key={g.id} onClick={() => { setUltraGroup(g.id); setUltraTab(g.tabs[0].id); setUltraResult(null); }} className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${ultraGroup === g.id ? 'bg-primary-600 text-white shadow-sm' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'}`}><Icon className="w-4 h-4" />{g.label}</button>); })}
              </div>
              <div className="flex flex-wrap gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
                {currentGroup.tabs.map(tab => { const Icon = tab.icon; return (<button key={tab.id} onClick={() => { setUltraTab(tab.id); setUltraResult(null); }} className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1 transition ${ultraTab === tab.id ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'}`}><Icon className="w-3 h-3" />{tab.label}</button>); })}
              </div>

              {ultraLoading && <LoadingOverlay text={ultraLoadingText} />}

              {/* Auth */}
              {!ultraLoading && ultraTab === 'auth' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Scrape halaman yang butuh login.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <RequiredInput label="Target URL" value={authTargetUrl} onChange={setAuthTargetUrl} placeholder="https://example.com/secret" />
                  <InputField label="Login URL (opsional)" value={authLoginUrl} onChange={setAuthLoginUrl} placeholder="https://example.com/login" />
                  <RequiredInput label="Username / API Key" value={authUsername} onChange={setAuthUsername} placeholder="user@example.com" />
                  <RequiredInput label="Password / Token" value={authPassword} onChange={setAuthPassword} placeholder="Password" type="password" />
                </div>
                <button onClick={handleAuthScrape} disabled={!authTargetUrl.trim() || !authUsername.trim() || !authPassword.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><Globe className="w-4 h-4" /> Scrape with Auth</button>
                {ultraResult && <JsonResult data={ultraResult} title="Hasil Auth Scrape" />}
              </div></RequireResult>)}

              {/* Fingerprint */}
              {!ultraLoading && ultraTab === 'fingerprint' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Generate browser fingerprint anti-detection.</p>
                <button onClick={() => runUltra('Generate fingerprint...', () => scraping.generateFingerprint())} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"><Fingerprint className="w-4 h-4" /> Generate Fingerprint</button>
                {ultraResult && <><div className="grid grid-cols-2 md:grid-cols-4 gap-3">{Object.entries(ultraResult).filter(([k]) => !['headers', 'navigator'].includes(k)).map(([k, v]) => (<div key={k} className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg"><p className="text-xs text-gray-500">{k}</p><p className="text-sm font-medium text-gray-900 dark:text-white truncate">{String(v)}</p></div>))}</div><JsonResult data={ultraResult} title="Detail" /></>}
              </div></RequireResult>)}

              {/* Distributed */}
              {!ultraLoading && ultraTab === 'distributed' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Distribusi scraping ke banyak worker.</p>
                <textarea placeholder="URLs (satu per baris)" rows={4} value={distUrls} onChange={e => setDistUrls(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono" />
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="block text-xs text-gray-500 mb-1">Strategy</label><select value={distStrategy} onChange={e => setDistStrategy(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white"><option value="round_robin">Round Robin</option><option value="chunk">Chunk</option><option value="least_loaded">Least Loaded</option><option value="hash">Hash</option></select></div>
                  <div><label className="block text-xs text-gray-500 mb-1">Max per Worker</label><input type="number" value={distMaxPerWorker} onChange={e => setDistMaxPerWorker(+e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white" /></div>
                </div>
                <button onClick={handleDistributedScrape} disabled={!distUrls.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><Layers className="w-4 h-4" /> Start Distributed Job</button>
                {ultraResult && <><div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg"><p className="text-sm font-medium text-green-800">Completed: {ultraResult.completed_urls}/{ultraResult.total_urls} URLs{ultraResult.failed_urls > 0 && ` (${ultraResult.failed_urls} failed)`}</p></div><JsonResult data={ultraResult} title="Detail" /></>}
              </div></RequireResult>)}

              {/* Target */}
              {!ultraLoading && ultraTab === 'target' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Scraper spesialis per tipe website.</p>
                <InputField label="URL to scrape" value={targetUrl} onChange={setTargetUrl} placeholder="https://example.com" />
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {[{ type: 'ecommerce', label: 'E-Commerce', desc: 'Produk, harga, review', icon: FileSpreadsheet }, { type: 'news', label: 'News', desc: 'Artikel, feed, author', icon: FileText }, { type: 'financial', label: 'Financial', desc: 'Saham, market data', icon: BarChart3 }, { type: 'academic', label: 'Academic', desc: 'Paper, sitasi', icon: FileCode }, { type: 'job', label: 'Job Portal', desc: 'Lowongan, gaji', icon: Layers }, { type: 'real_estate', label: 'Real Estate', desc: 'Properti, fitur', icon: Database }].map(({ type, label, desc, icon: Icon }) => (
                    <button key={type} onClick={() => handleTargetScrape(type)} disabled={!targetUrl.trim()} className="p-3 rounded-lg text-left transition border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"><div className="flex items-center gap-2 mb-1"><Icon className="w-4 h-4 text-primary-600" /><p className="text-sm font-medium text-gray-900 dark:text-white">{label}</p></div><p className="text-xs text-gray-500">{desc}</p></button>
                  ))}
                </div>
                {ultraResult && <><div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg"><p className="text-sm font-medium text-green-800">Found {ultraResult.items_found} items ({ultraResult.target_type})</p></div><JsonResult data={ultraResult.items?.slice(0, 3) || ultraResult} title="Sample Data" /></>}
              </div></RequireResult>)}

              {/* AutoML */}
              {!ultraLoading && ultraTab === 'automl' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Auto-select best ML model.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <RequiredInput label="Target Column" value={automlTargetCol} onChange={setAutomlTargetCol} placeholder="e.g. price, category" />
                  <div><label className="block text-xs text-gray-500 mb-1">Task</label><select value={automlTask} onChange={e => setAutomlTask(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white"><option value="">Auto-detect</option><option value="classification">Classification</option><option value="regression">Regression</option></select></div>
                </div>
                <button onClick={handleAutoML} disabled={!automlTargetCol.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><Brain className="w-4 h-4" /> Run AutoML</button>
                {ultraResult?.best_model && (<div className="space-y-3">
                  <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg"><p className="text-sm font-medium text-green-800">Best: {ultraResult.best_model}</p><p className="text-xs text-green-600 mt-1">Score: {ultraResult.best_score?.toFixed(4)}</p></div>
                  {ultraResult.all_results && (<div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr className="bg-gray-50 dark:bg-gray-900"><th className="px-3 py-2 text-left">Model</th><th className="px-3 py-2 text-left">Score</th><th className="px-3 py-2 text-left">CV</th></tr></thead><tbody>{ultraResult.all_results.map((r: any, i: number) => (<tr key={i} className="border-t border-gray-100 dark:border-gray-800"><td className="px-3 py-2 font-medium">{r.model}</td><td className="px-3 py-2">{r.score?.toFixed(4)}</td><td className="px-3 py-2">{r.cv_score?.toFixed(4)}</td></tr>))}</tbody></table></div>)}
                  {ultraResult.recommendations?.length > 0 && <InfoCard title="Rekomendasi" items={ultraResult.recommendations} />}
                </div>)}
              </div></RequireResult>)}

              {/* Anomaly */}
              {!ultraLoading && ultraTab === 'anomaly' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Deteksi anomali: Z-score, IQR, Isolation Forest, LOF.</p>
                <button onClick={handleAnomaly} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> Detect Anomalies</button>
                {ultraResult?.consensus && (<div className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <StatCard label="Anomalies" value={ultraResult.consensus.total_unique_anomalies || 0} color="text-red-600" />
                    <StatCard label="Methods" value={ultraResult.consensus.methods_used?.length || 0} color="text-blue-600" />
                    <StatCard label="Rate" value={`${(ultraResult.consensus.anomaly_rate * 100)?.toFixed(1) || 0}%`} color="text-orange-600" />
                    <StatCard label="Columns" value={ultraResult.consensus.columns_checked?.length || 0} color="text-purple-600" />
                  </div>
                  {ultraResult.consensus.method_results && (<div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr className="bg-gray-50 dark:bg-gray-900"><th className="px-3 py-2 text-left">Method</th><th className="px-3 py-2 text-left">Count</th><th className="px-3 py-2 text-left">Threshold</th></tr></thead><tbody>{ultraResult.consensus.method_results.map((m: any, i: number) => (<tr key={i} className="border-t border-gray-100 dark:border-gray-800"><td className="px-3 py-2 font-medium">{m.method}</td><td className="px-3 py-2">{m.anomaly_count}</td><td className="px-3 py-2 text-gray-500">{m.threshold?.toFixed(4)}</td></tr>))}</tbody></table></div>)}
                </div>)}
              </div></RequireResult>)}

              {/* Forecast */}
              {!ultraLoading && ultraTab === 'forecast' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Forecast time series.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <RequiredInput label="Value Column" value={forecastValueCol} onChange={setForecastValueCol} placeholder="e.g. sales" />
                  <div><label className="block text-xs text-gray-500 mb-1">Periods</label><input type="number" value={forecastPeriods} onChange={e => setForecastPeriods(+e.target.value)} min={1} max={100} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white" /></div>
                </div>
                <button onClick={handleForecast} disabled={!forecastValueCol.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Run Forecast</button>
                {ultraResult?.predictions && (<div className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <StatCard label="Method" value={ultraResult.method || 'auto'} />
                    <StatCard label="Periods" value={ultraResult.predictions.length} color="text-blue-600" />
                    <StatCard label="R²" value={ultraResult.r2?.toFixed(4) || '-'} color="text-green-600" />
                    <StatCard label="MAE" value={ultraResult.mae?.toFixed(4) || '-'} color="text-orange-600" />
                  </div>
                  <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg"><p className="text-xs font-medium text-blue-800 dark:text-blue-300 mb-2">Trend: {ultraResult.trend}</p><div className="flex flex-wrap gap-1">{ultraResult.predictions.map((p: number, i: number) => (<span key={i} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 rounded">{i + 1}: {p.toFixed(2)}</span>))}</div></div>
                </div>)}
              </div></RequireResult>)}

              {/* Cluster */}
              {!ultraLoading && ultraTab === 'cluster' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Auto-cluster: KMeans, DBSCAN, Agglomerative, GMM.</p>
                <button onClick={handleCluster} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"><Database className="w-4 h-4" /> Auto Cluster</button>
                {ultraResult?.best && (<div className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <StatCard label="Best" value={ultraResult.best.method} />
                    <StatCard label="K" value={ultraResult.best.optimal_k || '-'} color="text-purple-600" />
                    <StatCard label="Silhouette" value={ultraResult.best.silhouette_score?.toFixed(3) || '-'} color="text-blue-600" />
                    <StatCard label="Samples" value={ultraResult.best.n_samples || '-'} />
                  </div>
                  {ultraResult.all_results && (<div className="overflow-x-auto"><table className="min-w-full text-sm"><thead><tr className="bg-gray-50 dark:bg-gray-900"><th className="px-3 py-2 text-left">Method</th><th className="px-3 py-2 text-left">K</th><th className="px-3 py-2 text-left">Silhouette</th><th className="px-3 py-2 text-left">CH</th><th className="px-3 py-2 text-left">DB</th></tr></thead><tbody>{ultraResult.all_results.map((r: any, i: number) => (<tr key={i} className="border-t border-gray-100 dark:border-gray-800"><td className="px-3 py-2 font-medium">{r.method}</td><td className="px-3 py-2">{r.optimal_k || r.k || '-'}</td><td className="px-3 py-2">{r.silhouette_score?.toFixed(3)}</td><td className="px-3 py-2">{r.calinski_harabasz?.toFixed(1)}</td><td className="px-3 py-2">{r.davies_bouldin?.toFixed(3)}</td></tr>))}</tbody></table></div>)}
                </div>)}
              </div></RequireResult>)}

              {/* Features */}
              {!ultraLoading && ultraTab === 'features' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Auto feature engineering: interactions, polynomials, statistical, text, datetime.</p>
                <button onClick={handleFeatures} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"><Sparkles className="w-4 h-4" /> Engineer Features</button>
                {ultraResult?.result && (<div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3"><StatCard label="Original" value={ultraResult.result.original_features || '-'} /><StatCard label="New Features" value={ultraResult.result.new_features || '-'} color="text-green-600" /></div>
                  <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg"><p className="text-sm font-medium text-yellow-800">{ultraResult.result.summary}</p></div>
                  {ultraResult.result.feature_names && <InfoCard title="Features Created" items={ultraResult.result.feature_names.slice(0, 20)} />}
                </div>)}
              </div></RequireResult>)}

              {/* Enrich */}
              {!ultraLoading && ultraTab === 'enrich' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Enrich data: extract emails, phones, classify content.</p>
                <button onClick={handleEnrich} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"><Search className="w-4 h-4" /> Enrich Data</button>
                {ultraResult?.result && (<div className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <StatCard label="Rows" value={ultraResult.result.rows_enriched || '-'} color="text-green-600" />
                    <StatCard label="Emails" value={ultraResult.result.emails_found || 0} color="text-blue-600" />
                    <StatCard label="Phones" value={ultraResult.result.phones_found || 0} color="text-purple-600" />
                    <StatCard label="Quality" value={ultraResult.result.quality_score?.toFixed(1) || '-'} color="text-green-600" />
                  </div>
                  <div className="p-3 bg-teal-50 dark:bg-teal-900/20 rounded-lg"><p className="text-sm font-medium text-teal-800">{ultraResult.result.summary}</p></div>
                </div>)}
              </div></RequireResult>)}

              {/* Validate */}
              {!ultraLoading && ultraTab === 'validate' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Validasi kualitas data: nulls, types, ranges, patterns.</p>
                <button onClick={handleValidate} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> Run Validation</button>
                {ultraResult?.validation && (<div className="space-y-3">
                  <div className={`p-4 rounded-lg ${ultraResult.validation.passed ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}><div className="flex items-center gap-2">{ultraResult.validation.passed ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : <AlertTriangle className="w-5 h-5 text-red-600" />}<p className={`text-sm font-medium ${ultraResult.validation.passed ? 'text-green-800' : 'text-red-800'}`}>{ultraResult.validation.passed ? 'PASSED' : 'FAILED'} — {ultraResult.validation.errors} errors, {ultraResult.validation.warnings} warnings</p></div><p className="text-xs text-gray-600 mt-1">{ultraResult.validation.summary}</p></div>
                  {ultraResult.validation.violations?.length > 0 && (<div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg max-h-40 overflow-auto">{ultraResult.validation.violations.slice(0, 20).map((v: any, i: number) => (<div key={i} className="flex items-start gap-2 text-xs mb-1"><span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${v.severity === 'error' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>{v.severity}</span><span className="text-gray-600 dark:text-gray-400">[{v.column}] {v.message} (row {v.row})</span></div>))}</div>)}
                </div>)}
              </div></RequireResult>)}

              {/* DimReduce */}
              {!ultraLoading && ultraTab === 'dimreduce' && (<RequireResult result={result}><div className="space-y-4">
                <p className="text-sm text-gray-500">Reduksi dimensi: PCA, t-SNE, atau auto.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div><label className="block text-xs text-gray-500 mb-1">Method</label><select value={dimMethod} onChange={e => setDimMethod(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white"><option value="auto">Auto</option><option value="pca">PCA</option><option value="tsne">t-SNE</option></select></div>
                  <div><label className="block text-xs text-gray-500 mb-1">Components</label><input type="number" value={dimComponents} onChange={e => setDimComponents(+e.target.value)} min={2} max={50} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white" /></div>
                </div>
                <button onClick={handleDimReduce} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center gap-2"><Radar className="w-4 h-4" /> Reduce Dimensions</button>
                {ultraResult && !ultraResult.error && (<div className="space-y-3">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3"><StatCard label="Method" value={ultraResult.method || 'auto'} /><StatCard label="Original" value={ultraResult.original_features || '-'} /><StatCard label="Reduced" value={ultraResult.n_components || '-'} color="text-green-600" /></div>
                  {ultraResult.total_variance_explained > 0 && (<div className="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg"><p className="text-sm font-medium text-indigo-800">Variance Explained: {(ultraResult.total_variance_explained * 100).toFixed(1)}%</p></div>)}
                  {ultraResult.best && <InfoCard title="Best Method" items={[`${ultraResult.best.method}: ${ultraResult.best.n_components} components`]} />}
                </div>)}
              </div></RequireResult>)}

              {/* Diff */}
              {!ultraLoading && ultraTab === 'diff' && (<div className="space-y-4">
                <p className="text-sm text-gray-500">Bandingkan dua scrape job.</p>
                <div className="grid grid-cols-2 gap-4">
                  <RequiredInput label="Old Job ID" value={diffOldJobId} onChange={setDiffOldJobId} placeholder="UUID" />
                  <RequiredInput label="New Job ID" value={diffNewJobId} onChange={setDiffNewJobId} placeholder="UUID" />
                </div>
                <button onClick={handleDiff} disabled={!diffOldJobId.trim() || !diffNewJobId.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><GitBranch className="w-4 h-4" /> Compare Jobs</button>
                {ultraResult?.has_changes !== undefined && (<div className={`p-4 rounded-lg ${ultraResult.has_changes ? 'bg-yellow-50 dark:bg-yellow-900/20' : 'bg-green-50 dark:bg-green-900/20'}`}><p className={`text-sm font-medium ${ultraResult.has_changes ? 'text-yellow-800' : 'text-green-800'}`}>{ultraResult.has_changes ? 'Changes Detected' : 'No Changes'}</p><p className="text-xs text-gray-600 mt-1">{ultraResult.summary}</p>{ultraResult.value_changes?.length > 0 && (<div className="mt-2 space-y-1 max-h-40 overflow-auto">{ultraResult.value_changes.slice(0, 10).map((c: any, i: number) => (<p key={i} className="text-xs text-gray-600">Row {c.row}: {c.column} "{c.old_value}" → "{c.new_value}"</p>))}</div>)}</div>)}
              </div>)}

              {/* Webhook */}
              {!ultraLoading && ultraTab === 'webhook' && (<div className="space-y-4">
                <p className="text-sm text-gray-500">Notifikasi via webhook, Slack, Discord.</p>
                <div className="grid grid-cols-1 gap-4">
                  <RequiredInput label="Config Name" value={webhookName} onChange={setWebhookName} placeholder="my-webhook" />
                  <div><label className="block text-xs text-gray-500 mb-1">Webhook URLs (satu per baris)</label><textarea rows={2} value={webhookUrls} onChange={e => setWebhookUrls(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono" /></div>
                  <div className="grid grid-cols-2 gap-4"><InputField label="Slack Webhook" value={webhookSlack} onChange={setWebhookSlack} placeholder="https://hooks.slack.com/..." /><InputField label="Discord Webhook" value={webhookDiscord} onChange={setWebhookDiscord} placeholder="https://discord.com/api/webhooks/..." /></div>
                </div>
                <div className="flex gap-2">
                  <button onClick={async () => { if (!webhookName.trim()) { toast('error', 'Name wajib'); return; } setUltraLoading(true); try { const urls = webhookUrls.split('\n').map(u => u.trim()).filter(u => u.startsWith('http')); const res = await scraping.configureWebhook({ name: webhookName.trim(), webhook_urls: urls, slack_webhook: webhookSlack.trim(), discord_webhook: webhookDiscord.trim(), events: ['completed', 'failed'], include_data: true }); setUltraResult(res.data); toast('success', 'Webhook configured!'); } catch (err: any) { toast('error', err?.response?.data?.detail || 'Failed'); } finally { setUltraLoading(false); } }} disabled={!webhookName.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><Zap className="w-4 h-4" /> Configure</button>
                  <button onClick={async () => { if (!webhookName.trim()) { toast('error', 'Name wajib'); return; } setUltraLoading(true); try { const res = await scraping.testWebhook(webhookName.trim()); setUltraResult(res.data); toast('success', `Test: ${res.data.sent_count} sent`); } catch (err: any) { toast('error', err?.response?.data?.detail || 'Failed'); } finally { setUltraLoading(false); } }} disabled={!webhookName.trim()} className="px-4 py-2 bg-gray-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition">Test Send</button>
                </div>
                {ultraResult?.config && <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg"><p className="text-sm text-green-800">Configured: {ultraResult.config.webhook_count} webhooks</p></div>}
              </div>)}

              {/* Scheduling */}
              {!ultraLoading && ultraTab === 'scheduling' && (<div className="space-y-4">
                <p className="text-sm text-gray-500">Jadwalkan scraping otomatis berkala.</p>
                <div className="grid grid-cols-1 gap-4">
                  <RequiredInput label="Schedule Name" value={schedName} onChange={setSchedName} placeholder="daily-scrape" />
                  <div><label className="block text-xs text-gray-500 mb-1">URLs (satu per baris)</label><textarea rows={3} value={schedUrls} onChange={e => setSchedUrls(e.target.value)} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-mono" /></div>
                  <div className="flex items-center gap-2"><label className="text-sm text-gray-600">Setiap</label><input type="number" value={schedInterval} onChange={e => setSchedInterval(+e.target.value)} min={5} max={1440} className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white" /><label className="text-sm text-gray-600">menit</label></div>
                </div>
                <button onClick={async () => { const urls = schedUrls.split('\n').map(u => u.trim()).filter(u => u.startsWith('http')); if (!schedName.trim() || urls.length === 0) { toast('error', 'Name & URLs wajib'); return; } setUltraLoading(true); try { const res = await scraping.schedules.create({ name: schedName.trim(), urls, interval_minutes: schedInterval }); setSchedList(p => [res.data, ...p]); toast('success', 'Schedule created!'); } catch (err: any) { toast('error', err?.response?.data?.detail || 'Failed'); } finally { setUltraLoading(false); } }} disabled={!schedName.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><Clock className="w-4 h-4" /> Create Schedule</button>
                {schedList.length > 0 && (<div className="space-y-2">{schedList.map((s: any, i: number) => (<div key={i} className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg flex justify-between items-center"><div><p className="text-sm font-medium text-gray-900 dark:text-white">{s.name}</p><p className="text-xs text-gray-500">{s.urls?.length} URLs, setiap {s.interval_minutes}min</p></div><span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full">Active</span></div>))}</div>)}
              </div>)}

              {/* Rate Limit */}
              {!ultraLoading && ultraTab === 'ratelimit' && (<div className="space-y-4">
                <p className="text-sm text-gray-500">Atur rate limit & robots.txt per domain.</p>
                <div className="grid grid-cols-2 gap-4">
                  <RequiredInput label="Domain" value={rlDomain} onChange={setRlDomain} placeholder="example.com" />
                  <div><label className="block text-xs text-gray-500 mb-1">Delay (ms)</label><input type="number" value={rlDelay} onChange={e => setRlDelay(+e.target.value)} min={100} max={60000} step={100} className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white" /></div>
                </div>
                <div className="flex gap-2">
                  <button onClick={async () => { if (!rlDomain.trim()) { toast('error', 'Domain wajib'); return; } setUltraLoading(true); try { const res = await scraping.configureRateLimit(rlDomain.trim(), rlDelay, true); setUltraResult(res.data); toast('success', `Rate limit: ${rlDomain} → ${rlDelay}ms`); } catch (err: any) { toast('error', err?.response?.data?.detail || 'Failed'); } finally { setUltraLoading(false); } }} disabled={!rlDomain.trim()} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> Configure</button>
                  <button onClick={async () => { setUltraLoading(true); try { const res = await scraping.getRateLimitStats(); setRlStats(res.data); setUltraResult(res.data); } catch (err: any) { toast('error', 'Failed'); } finally { setUltraLoading(false); } }} className="px-4 py-2 bg-gray-600 text-white rounded-lg text-sm font-medium transition">View Stats</button>
                </div>
                {rlStats && (<div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg"><div className="grid grid-cols-3 gap-4 mb-3">
                  <div className="text-center"><p className="text-lg font-bold text-gray-900 dark:text-white">{rlStats.total_requests || 0}</p><p className="text-xs text-gray-500">Requests</p></div>
                  <div className="text-center"><p className="text-lg font-bold text-red-600">{rlStats.total_blocked || 0}</p><p className="text-xs text-gray-500">Blocked</p></div>
                  <div className="text-center"><p className="text-lg font-bold text-orange-600">{rlStats.total_robots_blocked || 0}</p><p className="text-xs text-gray-500">Robots</p></div>
                </div>{rlStats.domains && Object.keys(rlStats.domains).length > 0 && (<div className="space-y-1">{Object.entries(rlStats.domains).map(([domain, config]: [string, any]) => (<div key={domain} className="flex justify-between text-xs"><span className="text-gray-700 dark:text-gray-300">{domain}</span><span className="text-gray-500">delay: {config.crawl_delay}s | reqs: {config.request_count}</span></div>))}</div>)}</div>)}
              </div>)}
            </div>
          )}
        </div>
      )}

      {/* Job History */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        <button onClick={() => showJobs ? setShowJobs(false) : handleLoadJobs()} className="w-full flex items-center justify-between p-4 text-left">
          <span className="font-medium text-gray-900 dark:text-white flex items-center gap-2"><BarChart3 className="w-5 h-5" /> Riwayat Scrape</span>
          {showJobs ? <ChevronDown className="w-5 h-5 text-gray-400" /> : <ChevronRight className="w-5 h-5 text-gray-400" />}
        </button>
        {showJobs && (<div className="border-t border-gray-200 dark:border-gray-700 p-4">
          {jobs.length === 0 ? (<p className="text-sm text-gray-400 text-center py-4">Belum ada riwayat</p>) : (<div className="space-y-2">
            {jobs.map(job => (<div key={job.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="flex-1 min-w-0"><div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${job.scrape_type === 'batch' ? 'bg-blue-100 text-blue-700' : job.scrape_type === 'recursive' ? 'bg-purple-100 text-purple-700' : job.scrape_type === 'discover' ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-700'}`}>{job.scrape_type || 'single'}</span>
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{job.title || job.url}</p>
              </div><p className="text-xs text-gray-500">{job.clean_row_count} baris | Kualitas: {job.quality_score}%{job.advanced_analysis ? ' | Stats ✓' : ''}{job.sentiment_analysis ? ' | Sent ✓' : ''}</p></div>
              <div className="flex items-center gap-2 ml-4">
                <button onClick={() => handleImport(job.id)} disabled={importing === job.id} className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition" title="Import">{importing === job.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}</button>
                <button onClick={() => handleDelete(job.id)} className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition" title="Hapus"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>))}
          </div>)}
        </div>)}
      </div>
    </div>
  );
}

function ToggleChip({ label, active, onClick, icon: Icon }: { label: string; active: boolean; onClick: () => void; icon?: any }) {
  return (
    <button onClick={onClick} className={`px-3 py-1.5 rounded-full text-xs font-medium border transition flex items-center gap-1 ${active ? 'bg-primary-50 dark:bg-primary-900/30 border-primary-300 dark:border-primary-700 text-primary-700 dark:text-primary-300' : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}`}>
      {Icon ? <Icon className="w-3 h-3" /> : active ? <CheckCircle2 className="w-3 h-3" /> : <Settings2 className="w-3 h-3" />} {label}
    </button>
  );
}

function StatCard({ label, value, color = 'text-gray-900 dark:text-white' }: { label: string; value: string | number; color?: string }) {
  return (<div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-center"><p className={`text-2xl font-bold ${color}`}>{value}</p><p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{label}</p></div>);
}

function StatBadge({ icon: Icon, value, label }: { icon: any; value: string | number; label: string }) {
  return (<span className="flex items-center gap-1"><Icon className="w-4 h-4" />{value} {label}</span>);
}

function InfoCard({ title, items }: { title: string; items: string[] }) {
  return (<div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg"><h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{title}</h3>{items.length === 0 ? (<p className="text-xs text-gray-400">Tidak ada data</p>) : (<ul className="space-y-1">{items.map((item, i) => (<li key={i} className="text-xs text-gray-600 dark:text-gray-400">• {item}</li>))}</ul>)}</div>);
}
