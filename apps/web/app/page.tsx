"use client";
import { useEffect, useState, useRef } from "react";
import { defaultHistoryRange } from "../lib/history";

import { validatePrices, estimationNote, type Prices } from "../lib/metrics";
import dynamic from 'next/dynamic';
import {readDelivery,validateOverview,validateEntities,shardKey} from '../lib/delivery';
import type {Entity} from '../lib/contract';
const OperatorsDashboard=dynamic(()=>import('./operators-dashboard').then(m=>m.OperatorsDashboard));
const AreasDashboard=dynamic(()=>import('./areas-dashboard').then(m=>m.AreasDashboard));
const ActivityDashboard=dynamic(()=>import('./activity-dashboard').then(m=>m.ActivityDashboard));
const ProductionDashboard=dynamic(()=>import('./production-dashboard').then(m=>m.ProductionDashboard));
import { SummaryDashboard, GlobalFilters } from "./dashboard-components";
import {
  tabs,
  readSelection,
  destinationLabel,
  type Selection,
} from "../lib/navigation";
import {
  validateRelease,
  validateManifest,
  validatePair,
  validateApproval,
  sha256,
  type Release,
  type Manifest,
  type Approval,
} from "../lib/contract";
import { LocaleProvider } from "../lib/locale";
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
export default function Page() {
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
  const priceDownload=useRef<Promise<[Response,Response]|null>|null>(null);
  const [data, setData] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [attempt, setAttempt] = useState(0),
    [selection, setSelection] = useState<Selection>(initial),
    [dark, setDark] = useState(false),
    [prices, setPrices] = useState<Prices | null>(null),
    [priceError, setPriceError] = useState("");
  const { tab, fluid, month: period, mode, comparison, range } = selection;
  const setRange = (range: number) => update({range});
  function readUrl() {
    return readSelection(window.location.search);
  }
  function update(patch: Partial<Selection>) {
    // URL updates are synchronous: rapid filter changes retain the latest context.
    const next = { ...readUrl(), ...patch };
    if (patch.tab) {
      if (patch.tab !== "operators") next.operator = "";
      if (patch.tab !== "areas") next.area = "";
    }
    const url = new URL(window.location.href);
    for (const [k, v] of Object.entries(next)) {
      if (v || k === "range") url.searchParams.set(k, String(v));
      else url.searchParams.delete(k);
    }
    window.history.pushState(null, "", url);
    setSelection(next);
  }
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
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    (async () => {
      try {
        priceDownload.current=Promise.all([fetch(`${base}/data/prices.json`),fetch(`${base}/data/valuation-manifest.json`)]).catch(()=>null);
        const mr = await fetch(`${base}/data/manifest.json`);
        if (!mr.ok) throw Error("No pudimos cargar los agregados.");
        const manifestBytes=await mr.arrayBuffer();
        const manifest=validateManifest(JSON.parse(new TextDecoder().decode(manifestBytes)));
        // Request approval alongside the overview, while retaining exact manifest binding.
        const approvalRequest=fetch(`${base}/data/approval.json`).catch(()=>null);
        let release:Release;
        if(manifest.delivery){
          release=validateOverview(await readDelivery(manifest.delivery.overview,base),manifest,manifest.delivery);
        }else{
          const dr=await fetch(`${base}/data/release.json`);if(!dr.ok)throw Error('No pudimos cargar los agregados.');
          const bytes=await dr.arrayBuffer();if(await sha256(bytes)!==manifest.data_sha256)throw Error('La versión no coincide con su manifiesto.');
          release=validateRelease(JSON.parse(new TextDecoder().decode(bytes)));validatePair(release,manifest);
        }
        const ar=await approvalRequest;if(!ar)throw Error('No pudimos verificar el estado de publicación.');
        let approval: Approval | null = null;
        if (ar.ok)
          approval = validateApproval(
            await ar.json(),
            manifest,
            await sha256(manifestBytes),
          );
        else if (ar.status !== 404)
          throw Error("No pudimos verificar el estado de publicación.");
        if (active) {
          setData({ release, manifest, approval });
          setSelection((prev) => {
            const next = {
              ...prev,
              month: manifest.source.accepted_periods.includes(prev.month)
                ? prev.month
                : [...manifest.source.accepted_periods].sort().at(-1)!,
            };
            const url = new URL(window.location.href);
            for (const [k, v] of Object.entries(next))
              if (v || k === "range") url.searchParams.set(k, String(v));
            window.history.replaceState(null, "", url);
            return next;
          });
        }
      } catch (e) {
        if (active)
          setError(e instanceof Error ? e.message : "Datos no disponibles.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [attempt]);
  useEffect(() => {
    if (!data) return;
    let active = true;
    setPrices(null);
    setPriceError("");
    (async () => {
      try {
        const downloaded=await priceDownload.current;if(!downloaded)throw Error('Referencia de precios no disponible.');
        const [pr,vr]=downloaded;
        if (!pr.ok || !vr.ok)
          throw Error("Referencia de precios no disponible.");
        const priceBytes = await pr.arrayBuffer(),
          vm = await vr.json();
        if (
          vm.schema_version !== 1 ||
          vm.status !== "candidate" ||
          vm.release_sha256 !== data.manifest.data_sha256 ||
          vm.prices_sha256 !== (await sha256(priceBytes))
        )
          throw Error(
            "La referencia de precios no corresponde a esta versión.",
          );
        const result = validatePrices(
          JSON.parse(new TextDecoder().decode(priceBytes)),
        );
        if (active) setPrices(result);
      } catch (e) {
        if (active)
          setPriceError(
            e instanceof Error ? e.message : "Precio no disponible.",
          );
      }
    })();
    return () => {
      active = false;
    };
  }, [data]);
  const rows = data?.release.production ?? [];
  const current = rows.find((r) => r.fluid === fluid && r.periodo === period);
  const [details,setDetails]=useState<Record<string,Entity[]>>({});
  const [detailFailure,setDetailFailure]=useState({key:'',message:''});
  const detailDimension=tab==='operators'?'company':tab==='areas'?'area':null;
  const detailKey=data&&detailDimension?`${data.manifest.data_sha256}/${shardKey(fluid,detailDimension)}`:'';
  const detailError=detailFailure.key===detailKey?detailFailure.message:'';
  useEffect(()=>{
    if(!data?.manifest.delivery||!detailDimension||details[detailKey])return;
    const controller=new AbortController();setDetailFailure({key:detailKey,message:''});
    const ref=data.manifest.delivery.entities[shardKey(fluid,detailDimension)];
    readDelivery(ref,base,controller.signal).then(v=>validateEntities(v,data.release,ref,fluid,detailDimension))
      .then(rows=>{if(!controller.signal.aborted)setDetails(old=>({...old,[detailKey]:rows}));})
      .catch(()=>{if(!controller.signal.aborted)setDetailFailure({key:detailKey,message:'No pudimos cargar los agregados.'});});
    return()=>controller.abort();
  },[data,fluid,detailDimension,detailKey,details,attempt]);
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
      <div className="page" data-fluid={fluid}>
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
              <button onClick={() => setAttempt((n) => n + 1)}>
                {t("Reintentar")}
              </button>
            </div>
          ) : detailError && detailDimension ? (
            <div className="state" role="alert"><p>{t(detailError)}</p><button onClick={()=>{setDetailFailure({key:detailKey,message:''});setAttempt(n=>n+1);}}>{t('Reintentar')}</button></div>
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
            <p>{t("El gráfico combinado utiliza escalas independientes para volumen y USD, ambas desde cero. Comparar la evolución de cada serie, no sus alturas entre sí.")}</p>
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
