import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAdminConfigByKey,
  type AdminSiteConfigResponse,
  type LeadFormPayload,
  submitLead,
} from "../lib/api";
import { collectTechnicalMetrics, summarizeLeadMetrics } from "../lib/metrics";

const CONFIG_KEY = import.meta.env.VITE_ADMIN_CONFIG_KEY ?? "default";

const emptyForm = (): LeadFormPayload => ({
  contact: { fullName: "", email: "", phone: "", company: "" },
  business: { description: "", industry: "", website: "" },
  budget: "",
  contactPreference: "email",
  comments: "",
  companySize: "",
  taskVolume: "",
  role: "",
  businessSize: "",
  needVolume: "",
  resultDeadline: "",
  taskType: "",
  productInterest: "",
  preferredTime: "",
});

function validate(form: LeadFormPayload): string[] {
  const errors: string[] = [];
  if (!form.contact.fullName.trim()) {
    errors.push("Укажите имя или название контакта.");
  }
  if (!form.business.description.trim()) {
    errors.push("Кратко опишите бизнес и задачу.");
  }
  if (!form.contact.email.trim() && !form.contact.phone.trim()) {
    errors.push("Нужен e-mail или телефон для связи.");
  }
  const em = form.contact.email.trim();
  if (em && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) {
    errors.push("Проверьте формат e-mail.");
  }
  return errors;
}

function formatMoney(n: number, currency: string): string {
  try {
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: currency === "RUB" ? "RUB" : currency,
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `${n} ${currency}`;
  }
}

export function LeadForm() {
  const pageLoadTs = useRef(Date.now());
  const [form, setForm] = useState<LeadFormPayload>(emptyForm);
  const [adminCfg, setAdminCfg] = useState<AdminSiteConfigResponse | null>(null);
  const [budgetSlider, setBudgetSlider] = useState<number | null>(null);
  const [status, setStatus] = useState<{ type: "error" | "success" | "info"; text: string } | null>(
    null
  );
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const cfg = await fetchAdminConfigByKey(CONFIG_KEY);
      if (!cancelled) setAdminCfg(cfg);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const br = adminCfg?.budget_range;
  const rangeBounds = useMemo(() => {
    if (!br || br.min_amount == null || br.max_amount == null) return null;
    const min = br.min_amount;
    const max = Math.max(br.max_amount, min);
    const rawStep = br.step_amount ?? Math.round((max - min) / 100);
    const step = Math.max(1, rawStep || 1);
    return { min, max, step, currency: br.currency || "RUB", label: br.label };
  }, [br]);

  useEffect(() => {
    if (rangeBounds && budgetSlider === null) {
      setBudgetSlider(rangeBounds.min);
      setForm((f) => ({
        ...f,
        budget: formatMoney(rangeBounds.min, rangeBounds.currency),
      }));
    }
  }, [rangeBounds, budgetSlider]);

  const productOptions = useMemo(() => {
    const fromApi =
      adminCfg?.services
        ?.slice()
        .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id)
        .map((s) => s.title)
        .filter(Boolean) ?? [];
    const fallback = [
      "Автоматизация процессов",
      "Аналитика и отчётность",
      "Интеграции и API",
      "Консалтинг / аудит",
      "Другое (уточню в комментарии)",
    ];
    return fromApi.length ? fromApi : fallback;
  }, [adminCfg]);

  const setContact = useCallback((k: keyof LeadFormPayload["contact"], v: string) => {
    setForm((f) => ({ ...f, contact: { ...f.contact, [k]: v } }));
  }, []);

  const setBusiness = useCallback((k: keyof LeadFormPayload["business"], v: string) => {
    setForm((f) => ({ ...f, business: { ...f.business, [k]: v } }));
  }, []);

  const onBudgetRangeChange = (v: number) => {
    if (!rangeBounds) return;
    setBudgetSlider(v);
    setForm((f) => ({ ...f, budget: formatMoney(v, rangeBounds.currency) }));
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate(form);
    if (errs.length) {
      setStatus({ type: "error", text: errs.join(" ") });
      return;
    }
    setStatus(null);
    setSubmitting(true);
    try {
      const metrics = collectTechnicalMetrics({ pageLoadTs: pageLoadTs.current });
      await submitLead({
        schemaVersion: 1,
        submittedAt: new Date().toISOString(),
        form,
        metrics: metrics as unknown as Record<string, unknown>,
        metricsSummary: summarizeLeadMetrics(metrics) as Record<string, unknown>,
      });
      setStatus({
        type: "success",
        text: "Заявка отправлена. Мы свяжемся с вами удобным способом.",
      });
      const next = emptyForm();
      if (rangeBounds) {
        next.budget = formatMoney(rangeBounds.min, rangeBounds.currency);
        setBudgetSlider(rangeBounds.min);
      } else {
        setBudgetSlider(null);
      }
      setForm(next);
    } catch (err) {
      setStatus({
        type: "error",
        text: err instanceof Error ? err.message : "Ошибка сети. Попробуйте позже.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate id="lead-form">
      {status && (
        <div className={`status visible ${status.type}`} role="status" aria-live="polite">
          {status.text}
        </div>
      )}

      <section className="card" aria-labelledby="h-contact">
        <h2 id="h-contact">
          <span>01</span>
          Контактные данные
        </h2>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="fullName">
              Имя / контактное лицо<span className="req">*</span>
            </label>
            <input
              id="fullName"
              autoComplete="name"
              value={form.contact.fullName}
              onChange={(e) => setContact("fullName", e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="company">Компания</label>
            <input
              id="company"
              autoComplete="organization"
              value={form.contact.company}
              onChange={(e) => setContact("company", e.target.value)}
            />
          </div>
        </div>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={form.contact.email}
              onChange={(e) => setContact("email", e.target.value)}
            />
            <p className="hint">Обязателен e-mail или телефон</p>
          </div>
          <div className="field">
            <label htmlFor="phone">Телефон</label>
            <input
              id="phone"
              type="tel"
              autoComplete="tel"
              value={form.contact.phone}
              onChange={(e) => setContact("phone", e.target.value)}
            />
          </div>
        </div>
      </section>

      <section className="card" aria-labelledby="h-business">
        <h2 id="h-business">
          <span>02</span>
          О бизнесе
        </h2>
        <div className="field">
          <label htmlFor="businessDescription">
            Чем занимаетесь и что нужно решить<span className="req">*</span>
          </label>
          <textarea
            id="businessDescription"
            value={form.business.description}
            onChange={(e) => setBusiness("description", e.target.value)}
            placeholder="Продукт, аудитория, текущая задача, ожидания"
            required
          />
        </div>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="industry">Отрасль / ниша</label>
            <input
              id="industry"
              value={form.business.industry}
              onChange={(e) => setBusiness("industry", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="website">Сайт или соцсеть</label>
            <input
              id="website"
              type="url"
              placeholder="https://"
              value={form.business.website}
              onChange={(e) => setBusiness("website", e.target.value)}
            />
          </div>
        </div>
      </section>

      <section className="card" aria-labelledby="h-scale">
        <h2 id="h-scale">
          <span>03</span>
          Масштаб и роль
        </h2>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="companySize">Размер компании</label>
            <select
              id="companySize"
              value={form.companySize}
              onChange={(e) => setForm((f) => ({ ...f, companySize: e.target.value }))}
            >
              <option value="">Выберите</option>
              <option value="до 10 сотрудников">до 10 сотрудников</option>
              <option value="11–50">11–50</option>
              <option value="51–200">51–200</option>
              <option value="201–1000">201–1000</option>
              <option value="1000+">1000+</option>
              <option value="фриланс / ИП">фриланс / ИП</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="role">Ваша роль</label>
            <select
              id="role"
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
            >
              <option value="">Выберите</option>
              <option value="владелец / учредитель">владелец / учредитель</option>
              <option value="генеральный директор">генеральный директор</option>
              <option value="маркетинг">маркетинг</option>
              <option value="продажи">продажи</option>
              <option value="IT / цифровизация">IT / цифровизация</option>
              <option value="операционный блок">операционный блок</option>
              <option value="другое">другое</option>
            </select>
          </div>
        </div>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="businessSize">Масштаб бизнеса</label>
            <select
              id="businessSize"
              value={form.businessSize}
              onChange={(e) => setForm((f) => ({ ...f, businessSize: e.target.value }))}
            >
              <option value="">Выберите</option>
              <option value="самозанятый / микро">самозанятый / микро</option>
              <option value="малый бизнес">малый бизнес</option>
              <option value="средний бизнес">средний бизнес</option>
              <option value="крупный / холдинг">крупный / холдинг</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="taskVolume">Объём задач</label>
            <select
              id="taskVolume"
              value={form.taskVolume}
              onChange={(e) => setForm((f) => ({ ...f, taskVolume: e.target.value }))}
            >
              <option value="">Выберите</option>
              <option value="низкий">низкий</option>
              <option value="средний">средний</option>
              <option value="высокий">высокий</option>
              <option value="пиковый / сезонный">пиковый / сезонный</option>
            </select>
          </div>
        </div>
      </section>

      <section className="card" aria-labelledby="h-task">
        <h2 id="h-task">
          <span>04</span>
          Задача и сроки
        </h2>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="needVolume">Потребность по объёму работ</label>
            <select
              id="needVolume"
              value={form.needVolume}
              onChange={(e) => setForm((f) => ({ ...f, needVolume: e.target.value }))}
            >
              <option value="">Выберите</option>
              <option value="разовый проект">разовый проект</option>
              <option value="несколько задач в квартал">несколько задач в квартал</option>
              <option value="постоянный поток задач">постоянный поток задач</option>
              <option value="аудит с возможным продолжением">аудит с возможным продолжением</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="resultDeadline">Желаемые сроки результата</label>
            <select
              id="resultDeadline"
              value={form.resultDeadline}
              onChange={(e) => setForm((f) => ({ ...f, resultDeadline: e.target.value }))}
            >
              <option value="">Выберите</option>
              <option value="до 1 месяца">до 1 месяца</option>
              <option value="1–3 месяца">1–3 месяца</option>
              <option value="3–6 месяцев">3–6 месяцев</option>
              <option value="6+ месяцев">6+ месяцев</option>
              <option value="гибко / обсудим">гибко / обсудим</option>
            </select>
          </div>
        </div>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="taskType">Тип задачи</label>
            <select
              id="taskType"
              value={form.taskType}
              onChange={(e) => setForm((f) => ({ ...f, taskType: e.target.value }))}
            >
              <option value="">Выберите</option>
              <option value="аудит">аудит</option>
              <option value="внедрение">внедрение</option>
              <option value="сопровождение">сопровождение</option>
              <option value="консультация">консультация</option>
              <option value="разработка">разработка</option>
              <option value="другое">другое</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="productInterest">Интерес к продукту / услуге</label>
            <select
              id="productInterest"
              value={form.productInterest}
              onChange={(e) => setForm((f) => ({ ...f, productInterest: e.target.value }))}
            >
              <option value="">Выберите</option>
              {productOptions.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <section className="card" aria-labelledby="h-budget">
        <h2 id="h-budget">
          <span>05</span>
          Бюджет
        </h2>
        {rangeBounds ? (
          <div className="field">
            <label htmlFor="budgetRange">
              {rangeBounds.label ?? "Ориентир по бюджету"}
            </label>
            <div className="range-row">
              <span className="range-value" aria-live="polite">
                {budgetSlider != null ? formatMoney(budgetSlider, rangeBounds.currency) : form.budget}
              </span>
              <input
                id="budgetRange"
                type="range"
                min={rangeBounds.min}
                max={rangeBounds.max}
                step={rangeBounds.step}
                value={budgetSlider ?? rangeBounds.min}
                onChange={(e) => onBudgetRangeChange(Number(e.target.value))}
              />
            </div>
            <p className="hint">
              Значение уходит в заявку как текст; при необходимости уточните в комментарии.
            </p>
          </div>
        ) : (
          <div className="field">
            <label htmlFor="budget">Ориентир по бюджету</label>
            <input
              id="budget"
              placeholder="Например: 150–300 тыс., ежемесячно, обсудим"
              value={form.budget}
              onChange={(e) => setForm((f) => ({ ...f, budget: e.target.value }))}
            />
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="h-pref">
        <h2 id="h-pref">
          <span>06</span>
          Связь
        </h2>
        <div className="row row-2">
          <div className="field">
            <label htmlFor="contactPreference">Предпочтительный способ</label>
            <select
              id="contactPreference"
              value={form.contactPreference}
              onChange={(e) => setForm((f) => ({ ...f, contactPreference: e.target.value }))}
            >
              <option value="email">E-mail</option>
              <option value="phone">Звонок</option>
              <option value="telegram">Telegram</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="other">Другое (в комментарии)</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="preferredTime">Удобное время</label>
            <select
              id="preferredTime"
              value={form.preferredTime}
              onChange={(e) => setForm((f) => ({ ...f, preferredTime: e.target.value }))}
            >
              <option value="">Не важно</option>
              <option value="утро (до 12:00)">утро (до 12:00)</option>
              <option value="день (12:00–18:00)">день (12:00–18:00)</option>
              <option value="вечер (после 18:00)">вечер (после 18:00)</option>
            </select>
          </div>
        </div>
      </section>

      <section className="card" aria-labelledby="h-comments">
        <h2 id="h-comments">
          <span>07</span>
          Комментарии
        </h2>
        <div className="field">
          <label htmlFor="comments">Дополнительно</label>
          <textarea
            id="comments"
            placeholder="Сроки, ограничения, ссылки на материалы"
            value={form.comments}
            onChange={(e) => setForm((f) => ({ ...f, comments: e.target.value }))}
          />
        </div>
      </section>

      <div className="actions">
        <button type="submit" className="submit-btn" disabled={submitting}>
          {submitting ? "Отправка…" : "Отправить заявку"}
        </button>
      </div>
    </form>
  );
}
