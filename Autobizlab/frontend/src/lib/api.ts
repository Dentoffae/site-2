const API_LEADS = "/api/v1/leads";
const API_CONFIG_PREFIX = "/api/v1/admin-config/by-key";

export interface LeadFormPayload {
  contact: {
    fullName: string;
    email: string;
    phone: string;
    company: string;
  };
  business: {
    description: string;
    industry: string;
    website: string;
  };
  budget: string;
  contactPreference: string;
  comments: string;
  companySize: string;
  taskVolume: string;
  role: string;
  businessSize: string;
  needVolume: string;
  resultDeadline: string;
  taskType: string;
  productInterest: string;
  preferredTime: string;
}

export interface LeadSubmitBody {
  schemaVersion: number;
  submittedAt: string;
  form: LeadFormPayload;
  metrics: Record<string, unknown>;
  metricsSummary: Record<string, unknown> | null;
}

export async function submitLead(body: LeadSubmitBody): Promise<{ id: number; status: string }> {
  const res = await fetch(API_LEADS, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  if (!res.ok) {
    const text = await res.text();
    let msg = `Сервер вернул код ${res.status}.`;
    try {
      const j = JSON.parse(text) as { detail?: unknown; message?: string };
      if (typeof j.detail === "string") msg = j.detail;
      else if (Array.isArray(j.detail) && j.detail[0] && typeof (j.detail[0] as { msg?: string }).msg === "string") {
        msg = (j.detail[0] as { msg: string }).msg;
      } else if (j.message) msg = j.message;
    } catch {
      /* use default */
    }
    throw new Error(msg);
  }
  return res.json() as Promise<{ id: number; status: string }>;
}

export interface AdminBudgetRange {
  id: number;
  min_amount: number | null;
  max_amount: number | null;
  step_amount: number | null;
  currency: string;
  label: string | null;
}

export interface AdminService {
  id: number;
  title: string;
  description: string | null;
  price_amount: number | null;
  execution_time: string | null;
  sort_order: number;
}

export interface AdminSiteConfigResponse {
  id: number;
  config_key: string;
  services: AdminService[];
  budget_range: AdminBudgetRange | null;
  extra_ui: { id: number; field_key: string; field_value: string }[];
  created_at: string;
  updated_at: string;
}

export async function fetchAdminConfigByKey(
  key: string
): Promise<AdminSiteConfigResponse | null> {
  try {
    const res = await fetch(`${API_CONFIG_PREFIX}/${encodeURIComponent(key)}`, {
      credentials: "same-origin",
    });
    if (!res.ok) return null;
    return (await res.json()) as AdminSiteConfigResponse;
  } catch {
    return null;
  }
}
