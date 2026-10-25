"use client";
import { useEffect, useState } from "react";
import { defaultHistoryRange } from "../lib/history";

import { estimationNote, type Prices } from "../lib/metrics";
import dynamic from 'next/dynamic';
import {readDelivery,validateOverview,validateEntities,shardKey,createRequestCache} from '../lib/delivery';
import type {Entity} from '../lib/contract';
const OperatorsDashboard=dynamic(()=>import('./operators-dashboard').then(m=>m.OperatorsDashboard), {loading: TabLoading});
const AreasDashboard=dynamic(()=>import('./areas-dashboard').then(m=>m.AreasDashboard), {loading: TabLoading});
const ActivityDashboard=dynamic(()=>import('./activity-dashboard').then(m=>m.ActivityDashboard), {loading: TabLoading});
const ProductionDashboard=dynamic(()=>import('./production-dashboard').then(m=>m.ProductionDashboard), {loading: TabLoading});
import { GlobalFilters } from "./global-filters";
import { SummaryDashboard } from "./dashboard-components";
import {
  tabs,
  readSelection,
  destinationLabel,
  type Selection,
} from "../lib/navigation";
import type { Release, Manifest, Approval } from '../lib/contract';
import type { Bootstrap } from '../lib/bootstrap-types';
import { LocaleProvider, useLocale } from "../lib/locale";
import {
  formatters,
  readLanguage,
  languageStorageKey,
  translations,
  type Language,
} from "../lib/i18n";
const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "/vaca-muerta-pulse";
type Data = { release: Release; manifest: Manifest; approval: Approval | null };
const initial: Selection = {
  tab: "summary",
  fluid: "oil",
  mode: "volume",
  comparison: "yoy",
  month: "",
  operator: "",
  area: "",
  range: defaultHistoryRange,
};
function TabLoading() {
  const {t}=useLocale();
  return <div className="state" role="status">{t("Cargando agregados oficiales y verificando integridad…")}</div>;
}
export default function DashboardClient({bootstrap}:{bootstrap:Bootstrap}) {
  const [language, setLanguage] = useState<Language>("es");
  const { t, month, date } = formatters(language);
  function changeLanguage(next: Language) {
    setLanguage(next);
    try {
      localStorage.setItem(languageStorageKey, next);
    } catch {}
  }
  useEffect(() => {
    try {
      setLanguage(readLanguage(localStorage.getItem(languageStorageKey)));
    } catch {}
  }, []);
  useEffect(() => {
    document.documentElement.lang = language === "es" ? "es-AR" : "en-US";
    document.title = t("Vaca Muerta en Datos");
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        "content",
        t(
          "Producción mensual de petróleo y gas de Vaca Muerta. Vista previa de agregados oficiales.",
        ),
      );
  }, [language]);
  const data:Data=bootstrap.data;
  const prices:Prices|null=bootstrap.prices;
  const priceError=bootstrap.priceError;
  const loading=false;
  const error='';
  const [detailAttempt,setDetailAttempt]=useState(0),
    [selection,setSelection]=useState<Selection>({...initial,month:data.manifest.source.approved_period}),
    [dark,setDark]=useState(false);
  const { tab, fluid, month: period, mode, comparison, range } = selection;
  const setRange = (range: number) => update({range});
  function readUrl() {
    const value=readSelection(window.location.search);
    return {...value,month:data.manifest.source.accepted_periods.includes(value.month)?value.month:data.manifest.source.approved_period};
  }
  function update(patch: Partial<Selection>) {
    // URL updates are synchronous: rapid filter changes retain the latest context.
    const previous=readUrl();
    const next = { ...previous, ...patch };
    if (patch.tab) {
      if (patch.tab !== "operators") next.operator = "";
      if (patch.tab !== "areas") next.area = "";
    }
    if(Object.entries(next).every(([key,value])=>value===previous[key as keyof Selection]))return;
    const url = new URL(window.location.href);
    for (const [k, v] of Object.entries(next)) {
      if (v || k === "range") url.searchParams.set(k, String(v));
      else url.searchParams.delete(k);
    }
    window.history.pushState(null, "", url);
    setSelection(next);
  }
  // Start only the active view's module alongside the data bootstrap, not after it.
  // Read the URL here so a deep link never preloads the default Summary by mistake.
  useEffect(()=>{
    const active=readUrl().tab;
    const request=active==='summary'?import('./dashboard-components'):
      active==='production'?import('./production-dashboard'):
      active==='operators'?import('./operators-dashboard'):
      active==='areas'?import('./areas-dashboard'):import('./activity-dashboard');
    void request.catch(()=>{}); // The dynamic boundary retains its normal error handling.
  },[tab]);
  useEffect(() => {
    setSelection(readUrl());
    try { setDark(localStorage.getItem("vm-theme") === "dark"); } catch {}
    const restore = () => setSelection(readUrl());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  const rows = data?.release.production ?? [];
  const current = rows.find((r) => r.fluid === fluid && r.periodo === period);
  const [details,setDetails]=useState<Record<string,Entity[]>>({});
  const [detailRequests]=useState(()=>createRequestCache<Entity[]>());
  const [detailFailure,setDetailFailure]=useState({key:'',message:''});
  const detailDimension=tab==='operators'?'company':tab==='areas'?'area':null;
  const detailKey=data&&detailDimension?`${data.manifest.data_sha256}/${shardKey(fluid,detailDimension)}`:'';
  const detailError=detailFailure.key===detailKey?detailFailure.message:'';
  useEffect(()=>{
    if(!data?.manifest.delivery||!detailDimension||details[detailKey])return;
    let active=true;setDetailFailure({key:detailKey,message:''});
    const ref=data.manifest.delivery.entities[shardKey(fluid,detailDimension)];
    // A tab switch cancels this consumer, not a public immutable request another view may reuse.
    detailRequests.read(detailKey,()=>readDelivery(ref,base).then(v=>validateEntities(v,data.release,ref,fluid,detailDimension)))
      .then(rows=>{if(active)setDetails(old=>({...old,[detailKey]:rows}));})
      .catch(()=>{if(active)setDetailFailure({key:detailKey,message:'No pudimos cargar los agregados.'});});
    return()=>{active=false;};
  },[data,fluid,detailDimension,detailKey,details,detailAttempt]);
  const detailLoading=!!(data?.manifest.delivery&&detailDimension&&!details[detailKey]&&!detailError);
  const entities=(detailDimension&&details[detailKey])||data?.release.entities||[];
  function keyboardTab(
    e: React.KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    let target = index;
    if (e.key === "ArrowRight") target = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft")
      target = (index + tabs.length - 1) % tabs.length;
    else if (e.key === "Home") target = 0;
    else if (e.key === "End") target = tabs.length - 1;
    else return;
    e.preventDefault();
    update({ tab: tabs[target][0] });
    document.getElementById(`tab-${tabs[target][0]}`)?.focus();
  }
  return (
    <LocaleProvider language={language}>
      <a className="skip" href="#main">
        {t("Ir al contenido")}
      </a>
      <div className="page" data-fluid={fluid} data-workspace={(tab==='operators'&&!selection.operator)||(tab==='areas'&&!selection.area)?'explore':undefined}>
        <header className="masthead">
          <a
            className="brand"
            href={`${base}/`}
            onClick={(e) => {
              e.preventDefault();
              update({ tab: "summary" });
            }}
          >
            {t("Vaca Muerta en Datos")}
          </a>
          <div className="header-actions">
            <fieldset className="fluid-control language-control">
              <legend className="sr-only">{t("Idioma")}</legend>
              {(["es", "en"] as const).map((l) => (
                <button
                  key={l}
                  lang={l}
                  aria-pressed={language === l}
                  aria-label={l === "es" ? "Español" : "English"}
                  onClick={() => changeLanguage(l)}
                >
                  {l.toUpperCase()}
                </button>
              ))}
            </fieldset>
            <button
              className="theme-button"
              onClick={() => setDark((d) => { try {localStorage.setItem("vm-theme", d ? "light" : "dark");} catch {} return !d; })}
              aria-pressed={dark}
              aria-label={t(dark ? "Modo claro" : "Modo oscuro")}
              title={t(dark ? "Modo claro" : "Modo oscuro")}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                {dark ? (
                  <>
                    <circle cx="12" cy="12" r="4" />
                    <path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
                  </>
                ) : (
                  <path d="M20.5 14.2A8.7 8.7 0 0 1 9.8 3.5a8.7 8.7 0 1 0 10.7 10.7Z" />
                )}
              </svg>
            </button>
          </div>
        </header>
        <nav aria-label={t("Vistas de Vaca Muerta en Datos")}>
        <div
          className="tabs"
          role="tablist"
          aria-label={t("Vistas de Vaca Muerta en Datos")}
        >
          {tabs.map(([id, label], i) => (
            <button
              id={`tab-${id}`}
              key={id}
              role="tab"
              aria-selected={tab === id}
              aria-controls={tab === id ? `panel-${id}` : undefined}
              tabIndex={tab === id ? 0 : -1}
              onKeyDown={(e) => keyboardTab(e, i)}
              onClick={() => update({ tab: id })}
            >
              {t(label)}
            </button>
          ))}
        </div></nav>
        <main id="main">
          <GlobalFilters
            fluid={fluid}
            period={period}
            periods={data?.manifest.source.accepted_periods ?? []}
            mode={mode}
            comparison={comparison}
            onComparison={(comparison) => update({ comparison })}
            onMode={(mode) => update({ mode })}
            onFluid={(f) => update({ fluid: f })}
            onPeriod={(p) => update({ month: p })}
          />
          <p className="snapshot-status">
            {t("Datos: {period} · Ingesta: {ingested}", {
              period: month(data.manifest.source.approved_period),
              ingested: date(data.manifest.source.ingested_at),
            })}
            <span>{t("Integridad validada al construir; no certifica frescura del origen.")}</span>
          </p>
          {priceError && !loading && (
            <p className="availability-note" role="status">
              {t(
                translations[priceError]
                  ? priceError
                  : "Referencia de precios no disponible.",
              )}{" "}
              {t("Las métricas físicas siguen disponibles.")}
            </p>
          )}
          {loading ? (
            <div className="state" role="status">
              {t("Cargando agregados oficiales y verificando integridad…")}
            </div>
          ) : error ? (
            <div className="state" role="alert">
              <h1>{t("Datos no disponibles")}</h1>
              <p>{t(translations[error] ? error : "Datos no disponibles.")}</p>
              <button onClick={() => window.location.reload()}>
                {t("Reintentar")}
              </button>
            </div>
          ) : detailError && detailDimension ? (
            <div className="state" role="alert"><p>{t(detailError)}</p><button onClick={()=>{setDetailFailure({key:detailKey,message:''});setDetailAttempt(n=>n+1);}}>{t('Reintentar')}</button></div>
          ) : detailLoading ? (
            <div className="state" role="status">{t('Cargando agregados oficiales y verificando integridad…')}</div>
          ) : !current ? (
            <div className="state">
              <h1>{t("Sin datos para este período")}</h1>
              <button
                onClick={() =>
                  update({ month: data!.manifest.source.approved_period })
                }
              >
                {t("Volver al último mes disponible")}
              </button>
            </div>
          ) : (
            <section
              id={`panel-${tab}`}
              role="tabpanel"
              aria-labelledby={`tab-${tab}`}
              tabIndex={0}
            >
              {tab === "summary" ? (
                <SummaryDashboard
                  mode={mode}
                  comparison={comparison}
                  prices={prices}
                  current={current}
                  rows={rows}
                  entities={entities}
                  fluid={fluid}
                  period={period}
                  range={range}
                  setRange={setRange}
                  onNavigate={(destination, id) =>
                    update({
                      tab: destination,
                      operator: destination === "operators" ? (id ?? "") : "",
                      area: destination === "areas" ? (id ?? "") : "",
                    })
                  }
                />
              ) : tab === "production" ? (
                <ProductionDashboard rows={rows} current={current} prices={prices} mode={mode} comparison={comparison} range={range} setRange={setRange} />
              ) : tab === "areas" ? (
                <AreasDashboard entities={entities} rows={rows} current={current} prices={prices} mode={mode} comparison={comparison} range={range} setRange={setRange} area={selection.area} onArea={(area) => update({area})} />
              ) : tab === "activity" ? (
                <ActivityDashboard entities={entities} rows={rows} current={current} prices={prices} mode={mode} comparison={comparison} range={range} setRange={setRange} />
              ) : (
                <OperatorsDashboard entities={entities} rows={rows} current={current} prices={prices} mode={mode} comparison={comparison} range={range} setRange={setRange} operator={selection.operator} onOperator={(operator) => update({operator})} />
              )}
            </section>
          )}
        </main>
        <footer>
          <span>
            {t("Fuente:")}{" "}
            <a href="https://datos.energia.gob.ar/dataset/produccion-de-petroleo-y-gas-por-pozo">
              {t("Secretaría de Energía · Capítulo IV")}
            </a>
            {data && (
              <>
                {!data.approval && (
                  <span
                    className="status-badge"
                    title={t(
                      "Candidato validado técnicamente; promoción pública pendiente",
                    )}
                  >
                    {t("Preliminar")}
                  </span>
                )}
              </>
            )}
          </span>
          <details id="methodology" className="provenance">
            <summary>{t("Fuentes y metodología")}</summary>
            <p>
              {t(
                "Producción diaria = volumen mensual / días calendario. Volumen mensual = suma de la producción registrada. Pozos productivos = pozos únicos con producción positiva. Las comparaciones usan cada métrica y su período correspondiente; bases ausentes o cero no generan variaciones.",
              )}
            </p>
            <p>
              {t(
                "Universo: formación Vaca Muerta y recurso no convencional. Operador declarado por mes; transferencias de activos pueden modificar los rankings. Área: permiso o concesión. Los datos oficiales son revisables; se conserva el último snapshot validado y la promoción pública permanece pendiente.",
              )}
            </p>
            {data && (
              <div>
                <p>
                  {t(
                    "Producción: {period}. Ingesta: {ingested}. Versión preparada: {generated}. Publicación: {published}.",
                    {
                      period: month(data.manifest.source.approved_period),
                      ingested: date(data.manifest.source.ingested_at),
                      generated: date(data.manifest.generated_at),
                      published: data.approval
                        ? date(data.approval.approved_at)
                        : t("pendiente de aprobación"),
                    },
                  )}
                </p>
                {data.manifest.source.resources.map((r) => (
                  <p key={r.id}>
                    {t(
                      "{year}: fuente actualizada {updated}; extracción {extracted}.",
                      {
                        year: r.year ?? "—",
                        updated: date(r.source_last_modified),
                        extracted: date(r.extracted_at),
                      },
                    )}
                  </p>
                ))}
                <a download href={`${base}/data/manifest.json`}>
                  {t("Manifiesto de producción")}
                </a>
              </div>
            )}
            {prices && (
              <p>
                {t("Brent:")}{" "}
                <a href={prices.source.url}>
                  {t("EIA · promedio mensual USD/bbl")}
                </a>
                .{" "}
                {t(
                  "Actualizada {updated}; ingesta {retrieved}. Valor mensual = bbl × precio del mismo mes; diario = valor mensual / días calendario. Comparaciones calculadas sobre cada valor estimado. No representa facturación efectiva. Referencia uniforme para entidades; no incorpora calidad, descuentos, costos, regalías o tipo de cambio.",
                  {
                    updated: date(prices.source.source_updated_at),
                    retrieved: date(prices.source.retrieved_at),
                  },
                )}{" "}
                {t("Gas:")}{" "}
                <a href={prices.gas.status === "available" ? prices.gas.source.url : prices.gas.reviewed_sources[0]}>
                  {t(prices.gas.status === "available" ? "Henry Hub mensual · EIA" : "precios nacionales")}
                </a>{" "}
                {t(
                  prices.gas.status === "available" ? "Referencia internacional USD/MMBtu. Escenario energético de 1.036 BTU/pie³; no calorificidad medida de Vaca Muerta. Los faltantes no se rellenan." : "revisados, sin serie comparable y conversión energética validadas.",
                )}
              </p>
            )}
            <p>{t("El gráfico muestra una magnitud por vez, con su unidad y escala desde cero. El valor USD es una referencia, no facturación.")}</p>
            <p>
              {t(
                "Escala desde cero. Una vista porcentual o índice base 100 podría incorporarse en el futuro.",
              )}
            </p>
          </details>
        </footer>
      </div>
    </LocaleProvider>
  );
}
