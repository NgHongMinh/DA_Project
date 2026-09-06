-- Complete, independent Phase 3 SQL calculation surface.
-- Reads only Phase 2 tables; never reads Python-created fact_metrics.
DROP TABLE IF EXISTS temp.phase3_sql_results;
CREATE TEMP TABLE phase3_sql_results (
  subject_type TEXT, subject_key TEXT, period_type TEXT, period_key TEXT,
  series_key TEXT, metric_name TEXT, comparison_scope TEXT, filter_variant TEXT,
  method_version TEXT, question_id TEXT, period_start_year INTEGER,
  period_end_year INTEGER, metric_value REAL, metric_text_value TEXT, unit TEXT,
  value_status TEXT, exclusion_reason TEXT, population_n INTEGER,
  observed_n INTEGER, missing_n INTEGER, included_n INTEGER, zero_n INTEGER,
  trace_n INTEGER, material_n INTEGER, ranked_n INTEGER, component_count INTEGER,
  required_component_count INTEGER, denominator_basis TEXT, threshold_value REAL,
  source_metric_keys TEXT
);

DROP TABLE IF EXISTS temp.phase3_series;
CREATE TEMP TABLE phase3_series AS
SELECT 'HYDRO' series_key, '["hydro_generation_twh"]' source_keys, 1 required_count UNION ALL
SELECT 'WIND','["wind_generation_twh"]',1 UNION ALL
SELECT 'SOLAR','["solar_generation_twh"]',1 UNION ALL
SELECT 'OTHER_RENEWABLES','["other_renewables_generation_twh"]',1 UNION ALL
SELECT 'RENEWABLE_TOTAL','["hydro_generation_twh","other_renewables_generation_twh","solar_generation_twh","wind_generation_twh"]',4 UNION ALL
SELECT 'MODERN_WIND_SOLAR','["solar_generation_twh","wind_generation_twh"]',2;

DROP TABLE IF EXISTS temp.phase3_pct_series;
CREATE TEMP TABLE phase3_pct_series AS
SELECT 'RENEWABLE_TOTAL' series_key,'["renewables_share_electricity_pct"]' source_keys,1 required_count UNION ALL
SELECT 'HYDRO','["hydro_share_electricity_pct"]',1 UNION ALL
SELECT 'WIND','["wind_share_electricity_pct"]',1 UNION ALL
SELECT 'SOLAR','["solar_share_electricity_pct"]',1 UNION ALL
SELECT 'MODERN_WIND_SOLAR','["solar_share_electricity_pct","wind_share_electricity_pct"]',2;

DROP TABLE IF EXISTS temp.phase3_panel;
CREATE TEMP TABLE phase3_panel AS
WITH RECURSIVE years(year) AS (
  SELECT 2000 UNION ALL SELECT year+1 FROM years WHERE year<2021
), entities AS (
  SELECT entity,is_current_country_or_territory,is_asean FROM dim_entity
  WHERE is_current_country_or_territory=1 OR is_asean=1 OR entity='World'
), spine AS (
  SELECT e.*,y.year FROM entities e CROSS JOIN years y
), wide AS (
  SELECT s.entity,s.year,s.is_current_country_or_territory,s.is_asean,
    MAX(CASE WHEN f.metric_key='hydro_generation_twh' THEN f.value END) hydro,
    MAX(CASE WHEN f.metric_key='wind_generation_twh' THEN f.value END) wind,
    MAX(CASE WHEN f.metric_key='solar_generation_twh' THEN f.value END) solar,
    MAX(CASE WHEN f.metric_key='other_renewables_generation_twh' THEN f.value END) other_renewables,
    MAX(CASE WHEN f.metric_key='renewables_share_electricity_pct' THEN f.value END) renewable_pct,
    MAX(CASE WHEN f.metric_key='hydro_share_electricity_pct' THEN f.value END) hydro_pct,
    MAX(CASE WHEN f.metric_key='wind_share_electricity_pct' THEN f.value END) wind_pct,
    MAX(CASE WHEN f.metric_key='solar_share_electricity_pct' THEN f.value END) solar_pct
  FROM spine s LEFT JOIN fact_energy f
    ON f.entity=s.entity AND f.year=s.year AND f.metric_key IN (
      'hydro_generation_twh','wind_generation_twh','solar_generation_twh',
      'other_renewables_generation_twh','renewables_share_electricity_pct',
      'hydro_share_electricity_pct','wind_share_electricity_pct','solar_share_electricity_pct'
    )
  GROUP BY s.entity,s.year,s.is_current_country_or_territory,s.is_asean
)
SELECT *,
  CASE WHEN hydro IS NOT NULL AND wind IS NOT NULL AND solar IS NOT NULL AND other_renewables IS NOT NULL
       THEN hydro+wind+solar+other_renewables END renewable_total,
  (hydro IS NOT NULL)+(wind IS NOT NULL)+(solar IS NOT NULL)+(other_renewables IS NOT NULL) renewable_components,
  CASE WHEN wind IS NOT NULL AND solar IS NOT NULL THEN wind+solar END modern,
  (wind IS NOT NULL)+(solar IS NOT NULL) modern_components,
  CASE WHEN wind_pct IS NOT NULL AND solar_pct IS NOT NULL THEN wind_pct+solar_pct END modern_pct
FROM wide;

DROP TABLE IF EXISTS temp.phase3_six;
CREATE TEMP TABLE phase3_six AS
SELECT entity,year,is_current_country_or_territory,is_asean,'HYDRO' series_key,hydro value,(hydro IS NOT NULL) component_count,1 required_count FROM phase3_panel UNION ALL
SELECT entity,year,is_current_country_or_territory,is_asean,'WIND',wind,(wind IS NOT NULL),1 FROM phase3_panel UNION ALL
SELECT entity,year,is_current_country_or_territory,is_asean,'SOLAR',solar,(solar IS NOT NULL),1 FROM phase3_panel UNION ALL
SELECT entity,year,is_current_country_or_territory,is_asean,'OTHER_RENEWABLES',other_renewables,(other_renewables IS NOT NULL),1 FROM phase3_panel UNION ALL
SELECT entity,year,is_current_country_or_territory,is_asean,'RENEWABLE_TOTAL',renewable_total,renewable_components,4 FROM phase3_panel UNION ALL
SELECT entity,year,is_current_country_or_territory,is_asean,'MODERN_WIND_SOLAR',modern,modern_components,2 FROM phase3_panel;

DROP TABLE IF EXISTS temp.phase3_current_audit;
CREATE TEMP TABLE phase3_current_audit AS
WITH raw AS (
 SELECT year,series_key,SUM(value) value,COUNT(value) observed_n
 FROM phase3_six
 WHERE is_current_country_or_territory=1 AND series_key IN ('HYDRO','WIND','SOLAR','OTHER_RENEWABLES')
 GROUP BY year,series_key
), wide AS (
 SELECT year,
  MAX(CASE WHEN series_key='HYDRO' THEN value END) hydro,
  MAX(CASE WHEN series_key='WIND' THEN value END) wind,
  MAX(CASE WHEN series_key='SOLAR' THEN value END) solar,
  MAX(CASE WHEN series_key='OTHER_RENEWABLES' THEN value END) other_renewables,
  MAX(CASE WHEN series_key='HYDRO' THEN observed_n END) hydro_n,
  MAX(CASE WHEN series_key='WIND' THEN observed_n END) wind_n,
  MAX(CASE WHEN series_key='SOLAR' THEN observed_n END) solar_n,
  MAX(CASE WHEN series_key='OTHER_RENEWABLES' THEN observed_n END) other_n
 FROM raw GROUP BY year
)
SELECT year,series_key,value,observed_n,215 population_n FROM raw UNION ALL
SELECT year,'RENEWABLE_TOTAL',hydro+wind+solar+other_renewables,hydro_n+wind_n+solar_n+other_n,860 FROM wide UNION ALL
SELECT year,'MODERN_WIND_SOLAR',wind+solar,wind_n+solar_n,430 FROM wide;

DROP TABLE IF EXISTS temp.phase3_pct;
CREATE TEMP TABLE phase3_pct AS
SELECT entity,year,is_asean,'RENEWABLE_TOTAL' series_key,renewable_pct value,(renewable_pct IS NOT NULL) component_count,1 required_count FROM phase3_panel UNION ALL
SELECT entity,year,is_asean,'HYDRO',hydro_pct,(hydro_pct IS NOT NULL),1 FROM phase3_panel UNION ALL
SELECT entity,year,is_asean,'WIND',wind_pct,(wind_pct IS NOT NULL),1 FROM phase3_panel UNION ALL
SELECT entity,year,is_asean,'SOLAR',solar_pct,(solar_pct IS NOT NULL),1 FROM phase3_panel UNION ALL
SELECT entity,year,is_asean,'MODERN_WIND_SOLAR',modern_pct,(wind_pct IS NOT NULL)+(solar_pct IS NOT NULL),2 FROM phase3_panel;

-- Q1 descriptive statistics, including coverage counts and zero shares.
WITH scopes(scope,population_n) AS (VALUES('GLOBAL_CURRENT_COUNTRIES',215),('ASEAN_10',10)),
series_map(series_key,metric_key) AS (VALUES
 ('HYDRO','hydro_generation_twh'),('WIND','wind_generation_twh'),
 ('SOLAR','solar_generation_twh'),('OTHER_RENEWABLES','other_renewables_generation_twh')),
variants(filter_variant) AS (VALUES('ALL_OBSERVED'),('POSITIVE'),('MATERIAL')),
base AS (
 SELECT s.scope,s.population_n,f.year,m.series_key,m.metric_key,f.value,f.value_class
 FROM scopes s CROSS JOIN series_map m JOIN fact_energy f ON f.metric_key=m.metric_key
 JOIN dim_entity e ON e.entity=f.entity
 WHERE f.year IN (2000,2010,2021) AND e.is_current_country_or_territory=1
   AND (s.scope='GLOBAL_CURRENT_COUNTRIES' OR e.is_asean=1)
), coverage AS (
 SELECT scope,population_n,year,series_key,metric_key,COUNT(*) observed_n,
  population_n-COUNT(*) missing_n,SUM(value=0) zero_n,SUM(value_class='Trace') trace_n,
  SUM(value_class='Material') material_n
 FROM base GROUP BY scope,year,series_key
), filtered AS (
 SELECT b.*,v.filter_variant FROM base b CROSS JOIN variants v
 WHERE v.filter_variant='ALL_OBSERVED' OR (v.filter_variant='POSITIVE' AND b.value>0)
    OR (v.filter_variant='MATERIAL' AND b.value_class='Material')
), moments0 AS (
 SELECT scope,year,series_key,metric_key,filter_variant,COUNT(*) n,SUM(value) sum_v,
  AVG(value) mean_v,MIN(value) min_v,MAX(value) max_v
 FROM filtered GROUP BY scope,year,series_key,filter_variant
), moments AS (
 SELECT f.scope,f.year,f.series_key,f.filter_variant,m.n,m.sum_v,m.mean_v,m.min_v,m.max_v,
  AVG((f.value-m.mean_v)*(f.value-m.mean_v)) m2,
  AVG((f.value-m.mean_v)*(f.value-m.mean_v)*(f.value-m.mean_v)) m3,
  AVG((f.value-m.mean_v)*(f.value-m.mean_v)*(f.value-m.mean_v)*(f.value-m.mean_v)) m4
 FROM filtered f JOIN moments0 m USING(scope,year,series_key,filter_variant)
 GROUP BY f.scope,f.year,f.series_key,f.filter_variant
), ordered AS (
 SELECT f.*,ROW_NUMBER() OVER(PARTITION BY scope,year,series_key,filter_variant ORDER BY value)-1 rn,
  COUNT(*) OVER(PARTITION BY scope,year,series_key,filter_variant) n
 FROM filtered f
), qs(q,name) AS (VALUES(.10,'p10'),(.25,'p25'),(.50,'p50'),(.75,'p75'),(.90,'p90'),(.95,'p95'),(.99,'p99')),
quant AS (
 SELECT o.scope,o.year,o.series_key,o.filter_variant,q.name,
  MAX(CASE WHEN rn=CAST((n-1)*q.q AS INTEGER) THEN value END)+
  (((n-1)*q.q)-CAST((n-1)*q.q AS INTEGER))*
  (MAX(CASE WHEN rn=CAST((n-1)*q.q AS INTEGER)+(((n-1)*q.q)>CAST((n-1)*q.q AS INTEGER)) THEN value END)-
   MAX(CASE WHEN rn=CAST((n-1)*q.q AS INTEGER) THEN value END)) qvalue
 FROM ordered o CROSS JOIN qs q GROUP BY o.scope,o.year,o.series_key,o.filter_variant,q.name
), wideq AS (
 SELECT scope,year,series_key,filter_variant,
  MAX(CASE WHEN name='p10' THEN qvalue END) p10,MAX(CASE WHEN name='p25' THEN qvalue END) p25,
  MAX(CASE WHEN name='p50' THEN qvalue END) p50,MAX(CASE WHEN name='p75' THEN qvalue END) p75,
  MAX(CASE WHEN name='p90' THEN qvalue END) p90,MAX(CASE WHEN name='p95' THEN qvalue END) p95,
  MAX(CASE WHEN name='p99' THEN qvalue END) p99 FROM quant GROUP BY scope,year,series_key,filter_variant
), names(metric_name) AS (VALUES
 ('n'),('sum'),('mean'),('median'),('sd'),('cv'),('min'),('max'),('p10'),('p25'),
 ('p50'),('p75'),('p90'),('p95'),('p99'),('iqr'),('skewness'),('kurtosis'),
 ('zero_share_population'),('zero_share_observed')
), result AS (
 SELECT c.*,v.filter_variant,COALESCE(m.n,0) n,m.sum_v,m.mean_v,m.min_v,m.max_v,m.m2,m.m3,m.m4,
  q.p10,q.p25,q.p50,q.p75,q.p90,q.p95,q.p99,names.metric_name,
  CASE names.metric_name WHEN 'n' THEN COALESCE(m.n,0) WHEN 'sum' THEN sum_v WHEN 'mean' THEN mean_v
   WHEN 'median' THEN p50 WHEN 'sd' THEN sqrt(m2)
   WHEN 'cv' THEN CASE WHEN m.n>=2 AND mean_v>0 THEN sqrt(m2)/mean_v END
   WHEN 'min' THEN min_v WHEN 'max' THEN max_v WHEN 'p10' THEN p10 WHEN 'p25' THEN p25
   WHEN 'p50' THEN p50 WHEN 'p75' THEN p75 WHEN 'p90' THEN p90 WHEN 'p95' THEN p95
   WHEN 'p99' THEN p99 WHEN 'iqr' THEN p75-p25
   WHEN 'skewness' THEN CASE WHEN m.n>=3 AND m2>0 THEN sqrt(m.n*(m.n-1.0))/(m.n-2.0)*m3/pow(m2,1.5) END
   WHEN 'kurtosis' THEN CASE WHEN m.n>=4 AND m2>0 THEN (m.n-1.0)/((m.n-2.0)*(m.n-3.0))*((m.n+1.0)*(m4/(m2*m2)-3.0)+6.0) END
   WHEN 'zero_share_population' THEN 1.0*c.zero_n/c.population_n
   WHEN 'zero_share_observed' THEN 1.0*c.zero_n/NULLIF(c.observed_n,0) END metric_value
 FROM coverage c CROSS JOIN variants v
 LEFT JOIN moments m ON m.scope=c.scope AND m.year=c.year AND m.series_key=c.series_key AND m.filter_variant=v.filter_variant
 LEFT JOIN wideq q ON q.scope=c.scope AND q.year=c.year AND q.series_key=c.series_key AND q.filter_variant=v.filter_variant
 CROSS JOIN names
)
INSERT INTO phase3_sql_results
SELECT 'STATISTICAL_SCOPE',scope,'YEAR','Y'||year,series_key,metric_name,scope,filter_variant,
 'phase3_v1','Q1',year,year,metric_value,NULL,
 CASE WHEN metric_name='n' THEN 'count' WHEN metric_name IN ('cv','skewness','kurtosis','zero_share_population','zero_share_observed') THEN 'ratio' ELSE 'TWh' END,
 CASE WHEN metric_name='n' OR metric_value IS NOT NULL THEN 'CALCULATED'
      WHEN n=0 THEN 'NOT_DEFINED' ELSE 'INSUFFICIENT_N' END,
 CASE WHEN metric_name='n' OR metric_value IS NOT NULL THEN 'NONE'
      WHEN n=0 THEN 'EMPTY_GROUP'
      WHEN metric_name IN ('skewness','kurtosis') AND m2=0 THEN 'CONSTANT_GROUP' ELSE 'INSUFFICIENT_N' END,
 population_n,observed_n,missing_n,n,zero_n,trace_n,material_n,NULL,NULL,NULL,
 CASE WHEN metric_name='zero_share_population' THEN 'POPULATION'
      WHEN metric_name='zero_share_observed' THEN 'OBSERVED' ELSE 'NONE' END,
 CASE WHEN filter_variant='MATERIAL' THEN .05 END,'["'||metric_key||'"]'
FROM result;

-- Q2/Q5 source and derived country levels for the fixed ASEAN cohort.
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',s.entity,'YEAR','Y'||s.year,s.series_key,'generation_twh','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q2',s.year,s.year,s.value,NULL,'TWh',
 CASE WHEN s.value IS NULL THEN 'NOT_OBSERVED' ELSE 'CALCULATED' END,
 CASE WHEN s.value IS NULL THEN 'INCOMPLETE_COMPONENTS' ELSE 'NONE' END,
 10,(s.value IS NOT NULL),(s.value IS NULL),(s.value IS NOT NULL),NULL,NULL,NULL,NULL,
 s.component_count,s.required_count,'NONE',NULL,m.source_keys
FROM phase3_six s JOIN phase3_series m USING(series_key) WHERE s.is_asean=1;

INSERT INTO phase3_sql_results
SELECT 'COUNTRY',p.entity,'YEAR','Y'||p.year,p.series_key,'share_electricity_pct','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q5',p.year,p.year,p.value,NULL,'pct',
 CASE WHEN p.value IS NULL THEN 'NOT_OBSERVED' ELSE 'CALCULATED' END,
 CASE WHEN p.value IS NULL THEN 'INCOMPLETE_COMPONENTS' ELSE 'NONE' END,
 10,(p.value IS NOT NULL),(p.value IS NULL),(p.value IS NOT NULL),NULL,NULL,NULL,NULL,
 p.component_count,p.required_count,'NONE',NULL,m.source_keys
FROM phase3_pct p JOIN phase3_pct_series m USING(series_key) WHERE p.is_asean=1;

-- Global milestone source values, including explicit missing rows.
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',s.entity,'YEAR','Y'||s.year,s.series_key,'generation_twh','GLOBAL_CURRENT_COUNTRIES','NOT_APPLICABLE',
 'phase3_v1','Q1',s.year,s.year,s.value,NULL,'TWh',
 CASE WHEN s.value IS NULL THEN 'NOT_OBSERVED' ELSE 'CALCULATED' END,
 CASE WHEN s.value IS NULL THEN 'NOT_OBSERVED' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,s.component_count,1,'NONE',NULL,m.source_keys
FROM phase3_six s JOIN phase3_series m USING(series_key)
WHERE s.is_current_country_or_territory=1 AND s.year IN (2000,2010,2021)
  AND s.series_key IN ('HYDRO','WIND','SOLAR','OTHER_RENEWABLES');

-- ASEAN and reported-world annual generation levels.
WITH annual AS (
 SELECT 'REGION' subject_type,'ASEAN_10' subject_key,'ASEAN_10' comparison_scope,
  year,series_key,SUM(value) metric_value,COUNT(value) observed_n,SUM(component_count) component_count,
  10*MAX(required_count) required_count,10 population_n
 FROM phase3_six WHERE is_asean=1 GROUP BY year,series_key
 UNION ALL
 SELECT 'WORLD','WORLD_REPORTED','WORLD_REPORTED',year,series_key,value,(value IS NOT NULL),component_count,
  required_count,1 FROM phase3_six WHERE entity='World'
)
INSERT INTO phase3_sql_results
SELECT subject_type,subject_key,'YEAR','Y'||year,series_key,'generation_twh',comparison_scope,'NOT_APPLICABLE',
 'phase3_v1','Q1',year,year,CASE WHEN observed_n=population_n THEN metric_value END,NULL,'TWh',
 CASE WHEN observed_n=population_n THEN 'CALCULATED' ELSE 'NOT_OBSERVED' END,
 CASE WHEN observed_n=population_n THEN 'NONE' ELSE 'INCOMPLETE_COMPONENTS' END,
 population_n,observed_n,population_n-observed_n,observed_n,NULL,NULL,NULL,NULL,
 component_count,annual.required_count,CASE WHEN subject_key='ASEAN_10' THEN 'ASEAN_SUM_10' ELSE 'NONE' END,
 NULL,m.source_keys
FROM annual JOIN phase3_series m USING(series_key);

-- Current-country audit sums.
INSERT INTO phase3_sql_results
SELECT 'STATISTICAL_SCOPE','GLOBAL_CURRENT_COUNTRIES','YEAR','Y'||s.year,s.series_key,
 'current_country_sum_twh','WORLD_REPORTED','NOT_APPLICABLE','phase3_v1','Q1',s.year,s.year,
 s.value,NULL,'TWh','CALCULATED','NONE',s.population_n,s.observed_n,s.population_n-s.observed_n,s.observed_n,
 NULL,NULL,NULL,NULL,NULL,NULL,'CURRENT_COUNTRY_SUM_AUDIT',NULL,m.source_keys
FROM phase3_current_audit s JOIN phase3_series m USING(series_key);

-- Q2 country shares in ASEAN and technology composition.
WITH totals AS (
 SELECT year,series_key,SUM(value) total FROM phase3_six WHERE is_asean=1 GROUP BY year,series_key
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',s.entity,'YEAR','Y'||s.year,s.series_key,'country_share_asean','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q2',s.year,s.year,s.value/NULLIF(t.total,0),NULL,'ratio',
 CASE WHEN t.total=0 THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN t.total=0 THEN 'ZERO_DENOMINATOR' ELSE 'NONE' END,
 10,10,NULL,10,NULL,NULL,NULL,NULL,NULL,NULL,'ASEAN_SUM_10',NULL,m.source_keys
FROM phase3_six s JOIN totals t USING(year,series_key) JOIN phase3_series m USING(series_key)
WHERE s.is_asean=1;

WITH country_values AS (
 SELECT entity,year,series_key,value FROM phase3_six
 WHERE is_asean=1 AND series_key IN ('HYDRO','WIND','SOLAR','OTHER_RENEWABLES')
), totals AS (
 SELECT entity,year,value total FROM phase3_six WHERE is_asean=1 AND series_key='RENEWABLE_TOTAL'
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',v.entity,'YEAR','Y'||v.year,v.series_key,'technology_share','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q2',v.year,v.year,v.value/NULLIF(t.total,0),NULL,'ratio',
 CASE WHEN t.total=0 THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN t.total=0 THEN 'ZERO_DENOMINATOR' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,4,4,'TOTAL_RENEWABLE_GENERATION',NULL,
 '["hydro_generation_twh","other_renewables_generation_twh","solar_generation_twh","wind_generation_twh"]'
FROM country_values v JOIN totals t USING(entity,year);

WITH component AS (
 SELECT year,series_key,SUM(value) value FROM phase3_six
 WHERE is_asean=1 AND series_key IN ('HYDRO','WIND','SOLAR','OTHER_RENEWABLES') GROUP BY year,series_key
), totals AS (
 SELECT year,SUM(value) total FROM component GROUP BY year
)
INSERT INTO phase3_sql_results
SELECT 'REGION','ASEAN_10','YEAR','Y'||c.year,c.series_key,'technology_share','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q2',c.year,c.year,c.value/NULLIF(t.total,0),NULL,'ratio',
 CASE WHEN t.total=0 THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN t.total=0 THEN 'ZERO_DENOMINATOR' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,40,40,'TOTAL_RENEWABLE_GENERATION',NULL,
 '["hydro_generation_twh","other_renewables_generation_twh","solar_generation_twh","wind_generation_twh"]'
FROM component c JOIN totals t USING(year);

-- Q1 ASEAN share of the matching reported-world series.
WITH asean AS (
 SELECT year,series_key,SUM(value) value FROM phase3_six WHERE is_asean=1 GROUP BY year,series_key
), world AS (
 SELECT year,series_key,value FROM phase3_six WHERE entity='World'
)
INSERT INTO phase3_sql_results
SELECT 'REGION','ASEAN_10','YEAR','Y'||a.year,a.series_key,'asean_share_world','WORLD_REPORTED','NOT_APPLICABLE',
 'phase3_v1','Q1',a.year,a.year,a.value/NULLIF(w.value,0),NULL,'ratio',
 CASE WHEN w.value=0 OR w.value IS NULL THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN w.value=0 OR w.value IS NULL THEN 'ZERO_DENOMINATOR' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'REPORTED_WORLD',NULL,m.source_keys
FROM asean a JOIN world w USING(year,series_key) JOIN phase3_series m USING(series_key);

-- Q1/Q4 annual change, YoY, cumulative generation, and three-year rolling mean.
WITH base AS (
 SELECT 'REGION' subject_type,'ASEAN_10' subject_key,'ASEAN_10' comparison_scope,'Q1' question_id,
  year,series_key,SUM(value) value FROM phase3_six WHERE is_asean=1 GROUP BY year,series_key
 UNION ALL
 SELECT 'WORLD','WORLD_REPORTED','WORLD_REPORTED','Q1',year,series_key,value
 FROM phase3_six WHERE entity='World'
 UNION ALL
 SELECT 'COUNTRY','Vietnam','ASEAN_10','Q4',year,series_key,value
 FROM phase3_six WHERE entity='Vietnam'
), windowed AS (
 SELECT *,LAG(value) OVER(PARTITION BY subject_key,series_key ORDER BY year) previous_value,
  SUM(value) OVER(PARTITION BY subject_key,series_key ORDER BY year ROWS UNBOUNDED PRECEDING) cumulative_value,
  AVG(value) OVER(PARTITION BY subject_key,series_key ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) rolling_value,
  COUNT(value) OVER(PARTITION BY subject_key,series_key ORDER BY year ROWS UNBOUNDED PRECEDING) cumulative_n,
  COUNT(value) OVER(PARTITION BY subject_key,series_key ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) rolling_n,
  ROW_NUMBER() OVER(PARTITION BY subject_key,series_key ORDER BY year) row_n
 FROM base
), names(metric_name) AS (VALUES('annual_change_twh'),('yoy'),('cumulative_generation_twh'),('rolling_mean_3y_twh'))
INSERT INTO phase3_sql_results
SELECT subject_type,subject_key,'YEAR','Y'||year,series_key,metric_name,comparison_scope,'NOT_APPLICABLE',
 'phase3_v1',question_id,year,year,
 CASE metric_name WHEN 'annual_change_twh' THEN CASE WHEN previous_value IS NOT NULL THEN value-previous_value END
  WHEN 'yoy' THEN CASE WHEN previous_value>0 THEN value/previous_value-1 END
  WHEN 'cumulative_generation_twh' THEN CASE WHEN cumulative_n=row_n THEN cumulative_value END
  WHEN 'rolling_mean_3y_twh' THEN CASE WHEN row_n>=3 AND rolling_n=3 THEN rolling_value END END,NULL,
 CASE WHEN metric_name='yoy' THEN 'ratio' ELSE 'TWh' END,
 CASE WHEN metric_name='annual_change_twh' AND previous_value IS NULL THEN 'NOT_DEFINED'
      WHEN metric_name='yoy' AND previous_value IS NULL THEN 'NOT_DEFINED'
      WHEN metric_name='yoy' AND previous_value=0 THEN 'NOT_DEFINED'
      WHEN metric_name='cumulative_generation_twh' AND cumulative_n<>row_n THEN 'NOT_OBSERVED'
      WHEN metric_name='rolling_mean_3y_twh' AND (row_n<3 OR rolling_n<>3) THEN 'NOT_DEFINED'
      ELSE 'CALCULATED' END,
 CASE WHEN metric_name='annual_change_twh' AND previous_value IS NULL THEN 'MISSING_PREVIOUS'
      WHEN metric_name='yoy' AND previous_value IS NULL THEN 'MISSING_PREVIOUS'
      WHEN metric_name='yoy' AND previous_value=0 THEN 'ZERO_BASE'
      WHEN metric_name='cumulative_generation_twh' AND cumulative_n<>row_n THEN 'INCOMPLETE_HISTORY'
      WHEN metric_name='rolling_mean_3y_twh' AND row_n<3 THEN 'INSUFFICIENT_WINDOW'
      WHEN metric_name='rolling_mean_3y_twh' AND rolling_n<>3 THEN 'INCOMPLETE_WINDOW'
      ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,m.source_keys
FROM windowed CROSS JOIN names JOIN phase3_series m USING(series_key)
WHERE NOT (subject_key='WORLD_REPORTED' AND metric_name IN ('cumulative_generation_twh','rolling_mean_3y_twh'));

-- Q1 period absolute growth and CAGR for ASEAN and reported World.
WITH periods(a,b) AS (VALUES(2000,2010),(2010,2021),(2000,2021)),
base AS (
 SELECT 'REGION' subject_type,'ASEAN_10' subject_key,'ASEAN_10' comparison_scope,year,series_key,SUM(value) value
 FROM phase3_six WHERE is_asean=1 GROUP BY year,series_key
 UNION ALL
 SELECT 'WORLD','WORLD_REPORTED','WORLD_REPORTED',year,series_key,value FROM phase3_six WHERE entity='World'
), endpoints AS (
 SELECT s.subject_type,s.subject_key,s.comparison_scope,p.a,p.b,s.series_key,s.value start_value,e.value end_value
 FROM periods p JOIN base s ON s.year=p.a JOIN base e
  ON e.year=p.b AND e.subject_key=s.subject_key AND e.series_key=s.series_key
), names(metric_name) AS (VALUES('absolute_change_twh'),('cagr'))
INSERT INTO phase3_sql_results
SELECT subject_type,subject_key,'INTERVAL','I'||a||'_'||b,series_key,metric_name,comparison_scope,'NOT_APPLICABLE',
 'phase3_v1','Q1',a,b,
 CASE metric_name WHEN 'absolute_change_twh' THEN end_value-start_value
  ELSE CASE WHEN start_value>0 THEN pow(end_value/start_value,1.0/(b-a))-1 END END,NULL,
 CASE WHEN metric_name='cagr' THEN 'ratio' ELSE 'TWh' END,
 CASE WHEN start_value IS NULL OR end_value IS NULL THEN 'NOT_DEFINED'
      WHEN metric_name='cagr' AND start_value=0 THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN start_value IS NULL OR end_value IS NULL THEN 'MISSING_ENDPOINT'
      WHEN metric_name='cagr' AND start_value=0 THEN 'ZERO_BASE' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,m.source_keys
FROM endpoints CROSS JOIN names JOIN phase3_series m USING(series_key);

-- Q5 adjacent-year changes, YoY, and direction classification.
WITH base AS (
 SELECT t.entity,t.year,t.series_key,t.value twh,p.value pct,
  LAG(t.value) OVER(PARTITION BY t.entity,t.series_key ORDER BY t.year) previous_twh,
  LAG(p.value) OVER(PARTITION BY p.entity,p.series_key ORDER BY p.year) previous_pct
 FROM phase3_six t JOIN phase3_pct p USING(entity,year,series_key)
 WHERE t.is_asean=1 AND t.series_key IN ('RENEWABLE_TOTAL','MODERN_WIND_SOLAR','HYDRO','WIND','SOLAR')
), changes AS (
 SELECT *,CASE WHEN previous_twh IS NOT NULL THEN twh-previous_twh END delta_twh,
  CASE WHEN previous_pct IS NOT NULL THEN pct-previous_pct END delta_pct
 FROM base
), names(metric_name) AS (VALUES('q5_twh_change'),('q5_yoy'),('q5_pct_point_change'),('direction_relation'))
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',entity,'YEAR','Y'||year,series_key,metric_name,'ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q5',year,year,
 CASE metric_name WHEN 'q5_twh_change' THEN delta_twh
  WHEN 'q5_yoy' THEN CASE WHEN previous_twh>0 THEN twh/previous_twh-1 END
  WHEN 'q5_pct_point_change' THEN delta_pct END,
 CASE WHEN metric_name='direction_relation' AND delta_twh IS NOT NULL AND delta_pct IS NOT NULL THEN
   CASE WHEN abs(delta_twh)<=1e-12 OR abs(delta_pct)<=1e-12 THEN 'ONE_OR_BOTH_UNCHANGED'
        WHEN delta_twh*delta_pct>0 THEN 'SAME_DIRECTION' ELSE 'OPPOSITE_DIRECTION' END END,
 CASE metric_name WHEN 'q5_yoy' THEN 'ratio' WHEN 'q5_pct_point_change' THEN 'percentage_point'
  WHEN 'direction_relation' THEN 'STATUS_CODE' ELSE 'TWh' END,
 CASE WHEN metric_name='direction_relation' AND delta_twh IS NOT NULL AND delta_pct IS NOT NULL THEN 'CALCULATED_TEXT'
      WHEN metric_name='direction_relation' THEN 'NOT_DEFINED'
      WHEN metric_name='q5_yoy' AND previous_twh=0 THEN 'NOT_DEFINED'
      WHEN metric_name IN ('q5_twh_change','q5_yoy') AND previous_twh IS NULL THEN 'NOT_DEFINED'
      WHEN metric_name='q5_pct_point_change' AND previous_pct IS NULL THEN 'NOT_DEFINED'
      ELSE 'CALCULATED' END,
 CASE WHEN metric_name='direction_relation' AND delta_twh IS NOT NULL AND delta_pct IS NOT NULL THEN 'NON_NUMERIC_RESULT'
      WHEN metric_name='q5_yoy' AND previous_twh=0 THEN 'ZERO_BASE'
      WHEN (metric_name IN ('q5_twh_change','q5_yoy') AND previous_twh IS NULL)
        OR (metric_name='q5_pct_point_change' AND previous_pct IS NULL)
        OR metric_name='direction_relation' THEN 'MISSING_PREVIOUS' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,
 CASE series_key
  WHEN 'HYDRO' THEN '["hydro_generation_twh","hydro_share_electricity_pct"]'
  WHEN 'WIND' THEN '["wind_generation_twh","wind_share_electricity_pct"]'
  WHEN 'SOLAR' THEN '["solar_generation_twh","solar_share_electricity_pct"]'
  WHEN 'MODERN_WIND_SOLAR' THEN '["solar_generation_twh","solar_share_electricity_pct","wind_generation_twh","wind_share_electricity_pct"]'
  ELSE '["hydro_generation_twh","other_renewables_generation_twh","renewables_share_electricity_pct","solar_generation_twh","wind_generation_twh"]' END
FROM changes CROSS JOIN names;

-- Q5 endpoint changes for all locked periods.
WITH periods(a,b) AS (VALUES(2000,2010),(2010,2021),(2000,2021)),
base AS (
 SELECT t.entity,t.year,t.series_key,t.value twh,p.value pct FROM phase3_six t
 JOIN phase3_pct p USING(entity,year,series_key)
 WHERE t.is_asean=1 AND t.series_key IN ('RENEWABLE_TOTAL','MODERN_WIND_SOLAR','HYDRO','WIND','SOLAR')
), endpoints AS (
 SELECT s.entity,p.a,p.b,s.series_key,e.twh-s.twh delta_twh,e.pct-s.pct delta_pct
 FROM periods p JOIN base s ON s.year=p.a JOIN base e
  ON e.entity=s.entity AND e.year=p.b AND e.series_key=s.series_key
), names(metric_name) AS (VALUES('q5_twh_change'),('q5_pct_point_change'),('direction_relation'))
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',entity,'INTERVAL','I'||a||'_'||b,series_key,metric_name,'ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q5',a,b,
 CASE metric_name WHEN 'q5_twh_change' THEN delta_twh WHEN 'q5_pct_point_change' THEN delta_pct END,
 CASE WHEN metric_name='direction_relation' THEN
  CASE WHEN abs(delta_twh)<=1e-12 OR abs(delta_pct)<=1e-12 THEN 'ONE_OR_BOTH_UNCHANGED'
       WHEN delta_twh*delta_pct>0 THEN 'SAME_DIRECTION' ELSE 'OPPOSITE_DIRECTION' END END,
 CASE metric_name WHEN 'q5_pct_point_change' THEN 'percentage_point' WHEN 'direction_relation' THEN 'STATUS_CODE' ELSE 'TWh' END,
 CASE WHEN metric_name='direction_relation' THEN 'CALCULATED_TEXT' ELSE 'CALCULATED' END,
 CASE WHEN metric_name='direction_relation' THEN 'NON_NUMERIC_RESULT' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,
 CASE series_key
  WHEN 'HYDRO' THEN '["hydro_generation_twh","hydro_share_electricity_pct"]'
  WHEN 'WIND' THEN '["wind_generation_twh","wind_share_electricity_pct"]'
  WHEN 'SOLAR' THEN '["solar_generation_twh","solar_share_electricity_pct"]'
  WHEN 'MODERN_WIND_SOLAR' THEN '["solar_generation_twh","solar_share_electricity_pct","wind_generation_twh","wind_share_electricity_pct"]'
  ELSE '["hydro_generation_twh","other_renewables_generation_twh","renewables_share_electricity_pct","solar_generation_twh","wind_generation_twh"]' END
FROM endpoints CROSS JOIN names;

-- Q3 annual ASEAN ranks and the difference between the two ranking concepts.
WITH base AS (
 SELECT entity,year,series_key,value,
  SUM(value) OVER(PARTITION BY year,series_key) scope_total,
  COUNT(value) OVER(PARTITION BY year,series_key) ranked_n,
  RANK() OVER(PARTITION BY year,series_key ORDER BY value DESC) rank_value
 FROM phase3_six WHERE is_asean=1 AND series_key IN ('RENEWABLE_TOTAL','MODERN_WIND_SOLAR')
), ranks AS (
 SELECT *,CASE WHEN scope_total=0 THEN NULL ELSE rank_value END published_rank FROM base
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',entity,'YEAR','Y'||year,series_key,'asean_rank','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q3',year,year,published_rank,NULL,'rank',
 CASE WHEN published_rank IS NULL THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN published_rank IS NULL THEN 'ZERO_SCOPE_TOTAL' ELSE 'NONE' END,
 10,NULL,NULL,NULL,NULL,NULL,NULL,ranked_n,NULL,NULL,'NONE',NULL,
 m.source_keys
FROM ranks JOIN phase3_series m USING(series_key);

WITH ranked AS (
 SELECT entity,year,series_key,
  RANK() OVER(PARTITION BY year,series_key ORDER BY value DESC) rank_value,
  SUM(value) OVER(PARTITION BY year,series_key) scope_total
 FROM phase3_six WHERE is_asean=1 AND series_key IN ('RENEWABLE_TOTAL','MODERN_WIND_SOLAR')
), wide AS (
 SELECT entity,year,
  MAX(CASE WHEN series_key='RENEWABLE_TOTAL' AND scope_total<>0 THEN rank_value END) total_rank,
  MAX(CASE WHEN series_key='MODERN_WIND_SOLAR' AND scope_total<>0 THEN rank_value END) modern_rank
 FROM ranked GROUP BY entity,year
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',entity,'YEAR','Y'||year,'MODERN_WIND_SOLAR','modern_rank_gain','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q3',year,year,total_rank-modern_rank,NULL,'rank_change',
 CASE WHEN total_rank IS NULL OR modern_rank IS NULL THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN total_rank IS NULL OR modern_rank IS NULL THEN 'RANK_NOT_DEFINED' ELSE 'NONE' END,
 10,NULL,NULL,NULL,NULL,NULL,NULL,10,NULL,NULL,'NONE',NULL,
 '["hydro_generation_twh","other_renewables_generation_twh","solar_generation_twh","wind_generation_twh"]'
FROM wide;

-- Q3 rank movement at locked endpoints.
WITH periods(a,b) AS (VALUES(2000,2010),(2010,2021),(2000,2021)),
ranked AS (
 SELECT entity,year,series_key,
  RANK() OVER(PARTITION BY year,series_key ORDER BY value DESC) rank_value,
  SUM(value) OVER(PARTITION BY year,series_key) scope_total
 FROM phase3_six WHERE is_asean=1 AND series_key IN ('RENEWABLE_TOTAL','MODERN_WIND_SOLAR')
), endpoints AS (
 SELECT s.entity,p.a,p.b,s.series_key,
  CASE WHEN s.scope_total<>0 THEN s.rank_value END start_rank,
  CASE WHEN e.scope_total<>0 THEN e.rank_value END end_rank
 FROM periods p JOIN ranked s ON s.year=p.a JOIN ranked e
  ON e.entity=s.entity AND e.year=p.b AND e.series_key=s.series_key
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',entity,'INTERVAL','I'||a||'_'||b,series_key,'rank_gain_over_time','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q3',a,b,start_rank-end_rank,NULL,'rank_change',
 CASE WHEN start_rank IS NULL OR end_rank IS NULL THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN start_rank IS NULL OR end_rank IS NULL THEN 'RANK_NOT_DEFINED' ELSE 'NONE' END,
 10,NULL,NULL,NULL,NULL,NULL,NULL,10,NULL,NULL,'NONE',NULL,
 m.source_keys
FROM endpoints JOIN phase3_series m USING(series_key);

-- Q3 country CAGR, fixed-floor variants, and floor-specific ranks.
WITH periods(a,b) AS (VALUES(2000,2010),(2010,2021),(2000,2021)),
endpoints AS (
 SELECT s.entity,p.a,p.b,s.series_key,s.value start_value,e.value end_value
 FROM periods p JOIN phase3_six s ON s.year=p.a AND s.is_asean=1
 JOIN phase3_six e ON e.entity=s.entity AND e.year=p.b AND e.series_key=s.series_key
), calculated AS (
 SELECT *,CASE WHEN start_value>0 THEN pow(end_value/start_value,1.0/(b-a))-1 END cagr FROM endpoints
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',c.entity,'INTERVAL','I'||c.a||'_'||c.b,c.series_key,'country_cagr','ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q3',c.a,c.b,c.cagr,NULL,'ratio',
 CASE WHEN c.cagr IS NULL THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN c.cagr IS NULL THEN 'ZERO_BASE' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,m.source_keys
FROM calculated c JOIN phase3_series m USING(series_key);

WITH periods(a,b) AS (VALUES(2000,2010),(2010,2021),(2000,2021)),
floors(filter_variant,floor) AS (VALUES('CAGR_FLOOR_0_05',.05),('CAGR_FLOOR_0_1',.1),('CAGR_FLOOR_1_0',1.0)),
endpoints AS (
 SELECT s.entity,p.a,p.b,s.series_key,s.value start_value,e.value end_value
 FROM periods p JOIN phase3_six s ON s.year=p.a AND s.is_asean=1
 JOIN phase3_six e ON e.entity=s.entity AND e.year=p.b AND e.series_key=s.series_key
), eligible AS (
 SELECT e.*,f.filter_variant,f.floor,
  CASE WHEN e.start_value>0 THEN pow(e.end_value/e.start_value,1.0/(e.b-e.a))-1 END raw_cagr
 FROM endpoints e CROSS JOIN floors f
), ranked AS (
 SELECT *,SUM(start_value>=floor AND raw_cagr IS NOT NULL) OVER(PARTITION BY a,b,series_key,filter_variant) ranked_n,
  CASE WHEN start_value>=floor AND raw_cagr IS NOT NULL THEN
   RANK() OVER(PARTITION BY a,b,series_key,filter_variant ORDER BY
    CASE WHEN start_value>=floor AND raw_cagr IS NOT NULL THEN raw_cagr END DESC)
  END rank_value
 FROM eligible
), names(metric_name) AS (VALUES('country_cagr'),('cagr_rank'))
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',r.entity,'INTERVAL','I'||r.a||'_'||r.b,r.series_key,metric_name,'ASEAN_10',r.filter_variant,
 'phase3_v1','Q3',r.a,r.b,
 CASE WHEN metric_name='country_cagr' AND r.start_value>=r.floor THEN r.raw_cagr
      WHEN metric_name='cagr_rank' AND r.start_value>=r.floor AND r.ranked_n>=3 THEN r.rank_value END,NULL,
 CASE WHEN metric_name='cagr_rank' THEN 'rank' ELSE 'ratio' END,
 CASE WHEN r.start_value<r.floor OR r.raw_cagr IS NULL THEN 'NOT_DEFINED'
      WHEN metric_name='cagr_rank' AND r.ranked_n<3 THEN 'INSUFFICIENT_N' ELSE 'CALCULATED' END,
 CASE WHEN r.start_value<r.floor OR r.raw_cagr IS NULL THEN 'BELOW_START_FLOOR'
      WHEN metric_name='cagr_rank' AND r.ranked_n<3 THEN 'INSUFFICIENT_ELIGIBLE_ENTITIES' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,r.ranked_n,NULL,NULL,'NONE',r.floor,m.source_keys
FROM ranked r CROSS JOIN names JOIN phase3_series m USING(series_key);

-- Q4 Vietnam global rank with changing ranked_n disclosed.
WITH ranked AS (
 SELECT entity,year,series_key,value,
  COUNT(value) OVER(PARTITION BY year,series_key) ranked_n,
  SUM(value) OVER(PARTITION BY year,series_key) scope_total,
  RANK() OVER(PARTITION BY year,series_key ORDER BY value DESC) rank_value
 FROM phase3_six WHERE is_current_country_or_territory=1
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY','Vietnam','YEAR','Y'||year,series_key,'global_rank','GLOBAL_CURRENT_COUNTRIES','NOT_APPLICABLE',
 'phase3_v1','Q4',year,year,CASE WHEN scope_total<>0 THEN rank_value END,NULL,'rank',
 CASE WHEN scope_total=0 OR value IS NULL THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN scope_total=0 THEN 'ZERO_SCOPE_TOTAL' WHEN value IS NULL THEN 'NOT_OBSERVED' ELSE 'NONE' END,
 215,NULL,NULL,NULL,NULL,NULL,NULL,ranked_n,NULL,NULL,'NONE',NULL,m.source_keys
FROM ranked JOIN phase3_series m USING(series_key) WHERE entity='Vietnam';

-- Q4 entry and material-entry status per ASEAN country and technology.
DROP TABLE IF EXISTS temp.phase3_entry;
CREATE TEMP TABLE phase3_entry AS
WITH base AS (
 SELECT entity,series_key,COUNT(value) observed_n,
  MIN(CASE WHEN value>0 THEN year END) first_positive,
  MIN(CASE WHEN value>=.05 THEN year END) first_material,
  MAX(CASE WHEN year=2000 THEN value END) value_2000
 FROM phase3_six WHERE is_asean=1 AND series_key IN ('HYDRO','WIND','SOLAR','OTHER_RENEWABLES')
 GROUP BY entity,series_key
), classified AS (
 SELECT *,
  CASE WHEN observed_n<22 THEN 'UNKNOWN_INCOMPLETE_SERIES'
       WHEN value_2000>0 THEN 'ACTIVE_AT_WINDOW_START'
       WHEN first_positive IS NULL THEN 'NOT_OBSERVED_BY_2021' ELSE 'OBSERVED_TRANSITION' END entry_status,
  CASE WHEN observed_n<22 THEN 'UNKNOWN_INCOMPLETE_SERIES'
       WHEN value_2000>=.05 THEN 'MATERIAL_AT_WINDOW_START'
       WHEN first_material IS NULL THEN 'NOT_MATERIAL_BY_2021' ELSE 'OBSERVED_MATERIAL_TRANSITION' END material_status
 FROM base
)
SELECT *,CASE WHEN entry_status='OBSERVED_TRANSITION' THEN first_positive END observed_entry,
 CASE WHEN material_status='OBSERVED_MATERIAL_TRANSITION' THEN first_material END observed_material,
 CASE WHEN entry_status='UNKNOWN_INCOMPLETE_SERIES' THEN NULL WHEN entry_status='OBSERVED_TRANSITION' THEN 1 ELSE 0 END entry_exact,
 CASE WHEN material_status='UNKNOWN_INCOMPLETE_SERIES' THEN NULL WHEN material_status='OBSERVED_MATERIAL_TRANSITION' THEN 1 ELSE 0 END material_exact
FROM classified;

WITH earliest AS (
 SELECT series_key,
  CASE WHEN SUM(entry_status='ACTIVE_AT_WINDOW_START')>0 THEN NULL ELSE MIN(observed_entry) END earliest_exact
 FROM phase3_entry GROUP BY series_key
), expanded AS (
 SELECT e.*,x.earliest_exact FROM phase3_entry e JOIN earliest x USING(series_key)
), names(metric_name) AS (VALUES
 ('series_start_year'),('first_positive_in_window'),('observed_entry_year'),('is_entry_year_exact'),
 ('first_material_in_window'),('observed_material_entry_year'),('is_material_entry_year_exact'),
 ('entry_status'),('material_entry_status'),('lag_from_2000'),('relative_lag')
)
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',entity,'WINDOW','W2000_2021',series_key,metric_name,'ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q4',2000,2021,
 CASE metric_name WHEN 'series_start_year' THEN 2000 WHEN 'first_positive_in_window' THEN first_positive
  WHEN 'observed_entry_year' THEN observed_entry WHEN 'is_entry_year_exact' THEN entry_exact
  WHEN 'first_material_in_window' THEN first_material WHEN 'observed_material_entry_year' THEN observed_material
  WHEN 'is_material_entry_year_exact' THEN material_exact
  WHEN 'lag_from_2000' THEN observed_entry-2000
  WHEN 'relative_lag' THEN observed_entry-earliest_exact END,
 CASE metric_name WHEN 'entry_status' THEN entry_status WHEN 'material_entry_status' THEN material_status END,
 CASE WHEN metric_name IN ('entry_status','material_entry_status') THEN 'STATUS_CODE'
      WHEN metric_name IN ('series_start_year','first_positive_in_window','observed_entry_year','first_material_in_window','observed_material_entry_year','lag_from_2000','relative_lag') THEN 'year' ELSE 'count' END,
 CASE WHEN metric_name IN ('entry_status','material_entry_status') THEN 'CALCULATED_TEXT'
      WHEN metric_name='relative_lag' AND (earliest_exact IS NULL OR observed_entry IS NULL) THEN 'CENSORED'
      WHEN metric_name IN ('first_positive_in_window','observed_entry_year','is_entry_year_exact','lag_from_2000')
        AND CASE metric_name WHEN 'first_positive_in_window' THEN first_positive WHEN 'observed_entry_year' THEN observed_entry WHEN 'is_entry_year_exact' THEN entry_exact ELSE observed_entry END IS NULL
        THEN CASE WHEN entry_status='UNKNOWN_INCOMPLETE_SERIES' THEN 'NOT_OBSERVED' ELSE 'CENSORED' END
      WHEN metric_name IN ('first_material_in_window','observed_material_entry_year','is_material_entry_year_exact')
        AND CASE metric_name WHEN 'first_material_in_window' THEN first_material WHEN 'observed_material_entry_year' THEN observed_material ELSE material_exact END IS NULL
        THEN CASE WHEN material_status='UNKNOWN_INCOMPLETE_SERIES' THEN 'NOT_OBSERVED' ELSE 'CENSORED' END
      ELSE 'CALCULATED' END,
 CASE WHEN metric_name IN ('entry_status','material_entry_status') THEN 'NON_NUMERIC_RESULT'
      WHEN metric_name='relative_lag' AND earliest_exact IS NULL THEN 'EARLIEST_ENTRY_CENSORED'
      WHEN metric_name='relative_lag' AND observed_entry IS NULL THEN 'EVENT_NOT_EXACTLY_OBSERVED'
      WHEN metric_name IN ('first_positive_in_window','observed_entry_year','is_entry_year_exact','lag_from_2000')
        AND CASE metric_name WHEN 'first_positive_in_window' THEN first_positive WHEN 'observed_entry_year' THEN observed_entry WHEN 'is_entry_year_exact' THEN entry_exact ELSE observed_entry END IS NULL
        THEN CASE WHEN entry_status='UNKNOWN_INCOMPLETE_SERIES' THEN 'INCOMPLETE_SERIES' ELSE 'EVENT_NOT_EXACTLY_OBSERVED' END
      WHEN metric_name IN ('first_material_in_window','observed_material_entry_year','is_material_entry_year_exact')
        AND CASE metric_name WHEN 'first_material_in_window' THEN first_material WHEN 'observed_material_entry_year' THEN observed_material ELSE material_exact END IS NULL
        THEN CASE WHEN material_status='UNKNOWN_INCOMPLETE_SERIES' THEN 'INCOMPLETE_SERIES' ELSE 'EVENT_NOT_EXACTLY_OBSERVED' END
      ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,m.source_keys
FROM expanded CROSS JOIN names JOIN phase3_series m USING(series_key);

-- Q4 status summaries. Status is encoded in metric_name to preserve the nine-column key.
INSERT INTO phase3_sql_results
SELECT 'REGION','ASEAN_10','WINDOW','W2000_2021',e.series_key,
 'entry_count__'||e.entry_status,'ASEAN_10','NOT_APPLICABLE','phase3_v1','Q4',2000,2021,
 COUNT(*),NULL,'count','CALCULATED','NONE',10,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,m.source_keys
FROM phase3_entry e JOIN phase3_series m USING(series_key) GROUP BY e.series_key,e.entry_status;

INSERT INTO phase3_sql_results
SELECT 'REGION','ASEAN_10','WINDOW','W2000_2021',e.series_key,
 'material_entry_count__'||e.material_status,'ASEAN_10','NOT_APPLICABLE','phase3_v1','Q4',2000,2021,
 COUNT(*),NULL,'count','CALCULATED','NONE',10,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,m.source_keys
FROM phase3_entry e JOIN phase3_series m USING(series_key) GROUP BY e.series_key,e.material_status;

-- Q6 annual concentration and participation counts.
WITH valueset AS (
 SELECT entity,year,series_key,value FROM phase3_six
 WHERE is_asean=1 AND series_key IN ('RENEWABLE_TOTAL','MODERN_WIND_SOLAR')
), ranked AS (
 SELECT *,ROW_NUMBER() OVER(PARTITION BY year,series_key ORDER BY value DESC,entity) rdesc,
  ROW_NUMBER() OVER(PARTITION BY year,series_key ORDER BY value,entity) rasc,
  SUM(value) OVER(PARTITION BY year,series_key) total
 FROM valueset
), aggregate_values AS (
 SELECT year,series_key,total,MAX(CASE WHEN rdesc=1 THEN value END)/NULLIF(total,0) top1,
  SUM(CASE WHEN rdesc<=3 THEN value ELSE 0 END)/NULLIF(total,0) top3,
  SUM((value/NULLIF(total,0))*(value/NULLIF(total,0))) hhi,
  2.0*SUM(rasc*value)/(10.0*NULLIF(total,0))-11.0/10.0 gini,
  SUM(value>0) positive_n,SUM(value>=.05) above_n
 FROM ranked GROUP BY year,series_key
), names(metric_name) AS (VALUES('top1_share'),('top3_share'),('hhi'),('gini'),('positive_n'),('above_0_05_n'))
INSERT INTO phase3_sql_results
SELECT 'REGION','ASEAN_10','YEAR','Y'||year,series_key,metric_name,'ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q6',year,year,
 CASE metric_name WHEN 'top1_share' THEN top1 WHEN 'top3_share' THEN top3 WHEN 'hhi' THEN hhi
  WHEN 'gini' THEN gini WHEN 'positive_n' THEN positive_n WHEN 'above_0_05_n' THEN above_n END,NULL,
 CASE WHEN metric_name IN ('positive_n','above_0_05_n') THEN 'count' ELSE 'ratio' END,
 CASE WHEN total=0 AND metric_name NOT IN ('positive_n','above_0_05_n') THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN total=0 AND metric_name NOT IN ('positive_n','above_0_05_n') THEN 'ZERO_DENOMINATOR' ELSE 'NONE' END,
 10,10,NULL,10,NULL,NULL,NULL,NULL,NULL,NULL,
 CASE WHEN metric_name IN ('positive_n','above_0_05_n') THEN 'NONE' ELSE 'ASEAN_SUM_10' END,
 CASE WHEN metric_name='above_0_05_n' THEN .05 END,
 m.source_keys
FROM aggregate_values CROSS JOIN names JOIN phase3_series m USING(series_key);

-- Q6 positive-growth contribution, plus period summaries.
DROP TABLE IF EXISTS temp.phase3_growth;
CREATE TEMP TABLE phase3_growth AS
WITH periods(a,b) AS (VALUES(2000,2010),(2010,2021),(2000,2021)),
delta AS (
 SELECT s.entity,p.a,p.b,s.series_key,e.value-s.value country_delta
 FROM periods p JOIN phase3_six s ON s.year=p.a AND s.is_asean=1
 JOIN phase3_six e ON e.entity=s.entity AND e.year=p.b AND e.series_key=s.series_key
 WHERE s.series_key IN ('RENEWABLE_TOTAL','MODERN_WIND_SOLAR')
)
SELECT *,MAX(country_delta,0) positive_addition,
 SUM(MAX(country_delta,0)) OVER(PARTITION BY a,b,series_key) gross_positive,
 ROW_NUMBER() OVER(PARTITION BY a,b,series_key ORDER BY MAX(country_delta,0) DESC,entity) contribution_order
FROM delta;

WITH names(metric_name) AS (VALUES('country_delta_twh'),('positive_addition_twh'),('positive_growth_share'))
INSERT INTO phase3_sql_results
SELECT 'COUNTRY',entity,'INTERVAL','I'||a||'_'||b,series_key,metric_name,'ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q6',a,b,
 CASE metric_name WHEN 'country_delta_twh' THEN country_delta WHEN 'positive_addition_twh' THEN positive_addition
  ELSE positive_addition/NULLIF(gross_positive,0) END,NULL,
 CASE WHEN metric_name='positive_growth_share' THEN 'ratio' ELSE 'TWh' END,
 CASE WHEN metric_name='positive_growth_share' AND gross_positive=0 THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN metric_name='positive_growth_share' AND gross_positive=0 THEN 'ZERO_DENOMINATOR' ELSE 'NONE' END,
 NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,
 CASE WHEN metric_name='positive_growth_share' THEN 'GROSS_POSITIVE_ADDITION' ELSE 'NONE' END,
 NULL,m.source_keys
FROM phase3_growth CROSS JOIN names JOIN phase3_series m USING(series_key);

WITH summary AS (
 SELECT a,b,series_key,MAX(gross_positive) gross_positive,SUM(country_delta>0) positive_n,
  SUM(CASE WHEN contribution_order<=3 THEN positive_addition ELSE 0 END)/NULLIF(MAX(gross_positive),0) top3_share
 FROM phase3_growth GROUP BY a,b,series_key
), names(metric_name) AS (VALUES('gross_positive_addition_twh'),('growth_positive_n'),('top3_positive_growth_share'))
INSERT INTO phase3_sql_results
SELECT 'REGION','ASEAN_10','INTERVAL','I'||a||'_'||b,series_key,metric_name,'ASEAN_10','NOT_APPLICABLE',
 'phase3_v1','Q6',a,b,
 CASE metric_name WHEN 'gross_positive_addition_twh' THEN gross_positive WHEN 'growth_positive_n' THEN positive_n ELSE top3_share END,NULL,
 CASE metric_name WHEN 'growth_positive_n' THEN 'count' WHEN 'top3_positive_growth_share' THEN 'ratio' ELSE 'TWh' END,
 CASE WHEN metric_name='top3_positive_growth_share' AND gross_positive=0 THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN metric_name='top3_positive_growth_share' AND gross_positive=0 THEN 'ZERO_DENOMINATOR' ELSE 'NONE' END,
 10,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,
 CASE WHEN metric_name='top3_positive_growth_share' THEN 'GROSS_POSITIVE_ADDITION' ELSE 'NONE' END,
 NULL,m.source_keys
FROM summary CROSS JOIN names JOIN phase3_series m USING(series_key);

-- Q4 ASEAN-9 benchmarks for Vietnam.
WITH ordered AS (
 SELECT year,series_key,value,
  ROW_NUMBER() OVER(PARTITION BY year,series_key ORDER BY value) row_n,
  COUNT(*) OVER(PARTITION BY year,series_key) n
 FROM phase3_six WHERE is_asean=1 AND entity<>'Vietnam'
), benchmark AS (
 SELECT year,series_key,SUM(value)/9.0*9.0 sum_value,
  AVG(CASE WHEN row_n IN ((n+1)/2,(n+2)/2) THEN value END) median_value
 FROM ordered GROUP BY year,series_key
), names(metric_name) AS (VALUES('asean9_sum_twh'),('asean9_median_twh'))
INSERT INTO phase3_sql_results
SELECT 'COUNTRY','Vietnam','YEAR','Y'||year,series_key,metric_name,'ASEAN_9','NOT_APPLICABLE',
 'phase3_v1','Q4',year,year,
 CASE metric_name WHEN 'asean9_sum_twh' THEN sum_value ELSE median_value END,NULL,'TWh','CALCULATED','NONE',
 9,9,NULL,9,NULL,NULL,NULL,NULL,NULL,NULL,'NONE',NULL,m.source_keys
FROM benchmark CROSS JOIN names JOIN phase3_series m USING(series_key);

-- Q1 gap between current-country audit sum and the reported World row.
WITH world AS (
 SELECT year,series_key,value FROM phase3_six WHERE entity='World'
)
INSERT INTO phase3_sql_results
SELECT 'STATISTICAL_SCOPE','GLOBAL_CURRENT_COUNTRIES','YEAR','Y'||c.year,c.series_key,
 'world_reconciliation_gap_twh','WORLD_REPORTED','NOT_APPLICABLE','phase3_v1','Q1',c.year,c.year,
 c.value-w.value,NULL,'TWh',
 CASE WHEN c.value IS NULL OR w.value IS NULL THEN 'NOT_DEFINED' ELSE 'CALCULATED' END,
 CASE WHEN c.value IS NULL OR w.value IS NULL THEN 'MISSING_COMPONENT' ELSE 'NONE' END,
 c.population_n,c.observed_n,c.population_n-c.observed_n,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'REPORTED_WORLD',NULL,m.source_keys
FROM phase3_current_audit c JOIN world w USING(year,series_key) JOIN phase3_series m USING(series_key);

SELECT * FROM phase3_sql_results
ORDER BY subject_type,subject_key,period_type,period_key,series_key,metric_name,
 comparison_scope,filter_variant,method_version;
