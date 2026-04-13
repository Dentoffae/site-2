/**
 * Сбор технических метрик в браузере (аналог legacy lead-metrics.js).
 */

export type DeviceClass = "mobile" | "tablet" | "desktop";

export interface TechnicalMetrics {
  collectedAt: string;
  pageUrl: string;
  path: string;
  referrer: string;
  userAgent: string;
  language: string | null;
  languages: string[] | null;
  timezone: string | null;
  timezoneOffsetMin: number;
  screen: Record<string, unknown> | null;
  viewport: { width: number | null; height: number | null };
  utm: Record<string, string>;
  connection: Record<string, unknown> | null;
  hardwareConcurrency: number | null;
  timeOnPageMs: number;
  sessionId: string;
  analysis: {
    deviceClass: DeviceClass;
    cookiesEnabled: boolean | null;
    doNotTrack: string | null;
  };
}

function getUtmParams(): Record<string, string> {
  const params: Record<string, string> = {};
  try {
    const search = new URLSearchParams(globalThis.location.search);
    for (const key of [
      "utm_source",
      "utm_medium",
      "utm_campaign",
      "utm_term",
      "utm_content",
    ]) {
      const v = search.get(key);
      if (v) params[key] = v;
    }
  } catch {
    /* ignore */
  }
  return params;
}

function getConnectionHints(): Record<string, unknown> | null {
  const nav = globalThis.navigator as Navigator & {
    connection?: {
      effectiveType?: string;
      downlink?: number;
      rtt?: number;
      saveData?: boolean;
    };
  };
  const c = nav.connection;
  if (!c) return null;
  return {
    effectiveType: c.effectiveType ?? null,
    downlink: typeof c.downlink === "number" ? c.downlink : null,
    rtt: typeof c.rtt === "number" ? c.rtt : null,
    saveData: !!c.saveData,
  };
}

export function classifyDevice(viewportW: number, ua: string): DeviceClass {
  const uaLower = (ua || "").toLowerCase();
  const tablet =
    /tablet|ipad|playbook|silk/i.test(uaLower) ||
    (/android/i.test(uaLower) && !/mobile/i.test(uaLower));
  if (tablet) return "tablet";
  if (viewportW < 640) return "mobile";
  if (viewportW < 1024) return "tablet";
  return "desktop";
}

function sessionId(): string {
  const key = "abl_sid";
  try {
    const existing = globalThis.localStorage.getItem(key);
    if (existing) return existing;
    const id =
      "s_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 12);
    globalThis.localStorage.setItem(key, id);
    return id;
  } catch {
    return "s_volatile_" + Math.random().toString(36).slice(2);
  }
}

export function collectTechnicalMetrics(opts: { pageLoadTs: number }): TechnicalMetrics {
  const nav = globalThis.navigator;
  const scr = globalThis.screen;
  const loadTs = opts.pageLoadTs ? opts.pageLoadTs : Date.now();

  const viewport = {
    width: globalThis.innerWidth || null,
    height: globalThis.innerHeight || null,
  };

  const screenInfo = scr
    ? {
        width: scr.width,
        height: scr.height,
        availWidth: scr.availWidth,
        availHeight: scr.availHeight,
        colorDepth: scr.colorDepth,
        pixelRatio: globalThis.devicePixelRatio || 1,
      }
    : null;

  const ua = nav ? nav.userAgent : "";
  const analysis = {
    deviceClass: classifyDevice(viewport.width || 0, ua),
    cookiesEnabled: nav ? !!nav.cookieEnabled : null,
    doNotTrack: nav && nav.doNotTrack != null ? String(nav.doNotTrack) : null,
  };

  let timezone: string | null = null;
  try {
    timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    timezone = null;
  }

  return {
    collectedAt: new Date().toISOString(),
    pageUrl: globalThis.location.href,
    path: globalThis.location.pathname,
    referrer: globalThis.document.referrer || "",
    userAgent: ua,
    language: nav ? nav.language : null,
    languages: nav && nav.languages ? Array.from(nav.languages) : null,
    timezone,
    timezoneOffsetMin: new Date().getTimezoneOffset(),
    screen: screenInfo,
    viewport,
    utm: getUtmParams(),
    connection: getConnectionHints(),
    hardwareConcurrency:
      nav && typeof nav.hardwareConcurrency === "number" ? nav.hardwareConcurrency : null,
    timeOnPageMs: Math.max(0, Date.now() - loadTs),
    sessionId: sessionId(),
    analysis,
  };
}

export function summarizeLeadMetrics(metrics: TechnicalMetrics): Record<string, unknown> {
  return {
    deviceClass: metrics.analysis.deviceClass,
    locale: metrics.language,
    timezone: metrics.timezone,
    hasUtm: Object.keys(metrics.utm).length > 0,
    referrerPresent: !!metrics.referrer,
    sessionId: metrics.sessionId,
  };
}
