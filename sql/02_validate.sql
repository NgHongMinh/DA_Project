-- Phase 2 validation and reconciliation audit.
--
-- Contract:
--   * V1-V5 are non-blocking reconciliation checks. A source difference is
--     reported, never repaired or coalesced.
--   * V6-V8 and Sxx structural checks are blocking quality gates.
--   * Running this script rebuilds the persistent validation_results table.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS validation_results;

CREATE TABLE validation_results (
    check_id       TEXT    NOT NULL,
    scope          TEXT    NOT NULL,
    metric         TEXT,
    year           INTEGER,
    status         TEXT    NOT NULL
                           CHECK (status IN ('PASS', 'WARN', 'FAIL', 'SKIP')),
    is_blocking    INTEGER NOT NULL
                           CHECK (is_blocking IN (0, 1)),
    observed       REAL,
    expected       REAL,
    abs_diff       REAL,
    rel_diff_pct   REAL,
    abs_tol        REAL,
    rel_tol_pct    REAL,
    compared_rows  INTEGER NOT NULL DEFAULT 0
                           CHECK (compared_rows >= 0),
    exception_rows INTEGER NOT NULL DEFAULT 0
                           CHECK (exception_rows >= 0),
    reason_code    TEXT    NOT NULL,
    note           TEXT    NOT NULL
) STRICT;

CREATE INDEX idx_validation_results_check
    ON validation_results (check_id, status, metric, year, scope);

-- -------------------------------------------------------------------------
-- Structural contract and fixed Phase 2 acceptance baselines.
-- -------------------------------------------------------------------------

WITH structural_checks (
    check_id,
    scope,
    observed,
    expected,
    compared_rows,
    exception_rows,
    reason_code,
    note
) AS (
    SELECT
        'S01_CATALOG_ROWS',
        'SOURCE_METRIC_CATALOG',
        CAST(COUNT(*) AS REAL),
        23.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 23 THEN 0 ELSE 1 END,
        'CATALOG_ROW_COUNT',
        'The catalog must map all 23 source value columns.'
    FROM source_metric_catalog

    UNION ALL

    SELECT
        'S02_SOURCE_FILES',
        'SOURCE_METRIC_CATALOG',
        CAST(COUNT(DISTINCT source_file) AS REAL),
        17.0,
        COUNT(DISTINCT source_file),
        CASE WHEN COUNT(DISTINCT source_file) = 17 THEN 0 ELSE 1 END,
        'SOURCE_FILE_COUNT',
        'All 17 archived CSV sources must be represented in the catalog.'
    FROM source_metric_catalog

    UNION ALL

    SELECT
        'S03_CANONICAL_FILES',
        'SOURCE_ROLE',
        CAST(COUNT(DISTINCT source_file) AS REAL),
        13.0,
        COUNT(DISTINCT source_file),
        CASE WHEN COUNT(DISTINCT source_file) = 13 THEN 0 ELSE 1 END,
        'CANONICAL_FILE_COUNT',
        'Exactly 13 source files are canonical.'
    FROM source_metric_catalog
    WHERE source_role = 'canonical'

    UNION ALL

    SELECT
        'S04_AUDIT_FILES',
        'SOURCE_ROLE',
        CAST(COUNT(DISTINCT source_file) AS REAL),
        1.0,
        COUNT(DISTINCT source_file),
        CASE WHEN COUNT(DISTINCT source_file) = 1 THEN 0 ELSE 1 END,
        'AUDIT_FILE_COUNT',
        'Exactly one source file is audit-only.'
    FROM source_metric_catalog
    WHERE source_role = 'audit'

    UNION ALL

    SELECT
        'S05_EXCLUDED_FILES',
        'SOURCE_ROLE',
        CAST(COUNT(DISTINCT source_file) AS REAL),
        3.0,
        COUNT(DISTINCT source_file),
        CASE WHEN COUNT(DISTINCT source_file) = 3 THEN 0 ELSE 1 END,
        'EXCLUDED_FILE_COUNT',
        'Exactly three duplicate-metric source files are excluded.'
    FROM source_metric_catalog
    WHERE source_role = 'excluded'

    UNION ALL

    SELECT
        'S06_CANONICAL_METRICS',
        'SOURCE_METRIC_CATALOG',
        CAST(COUNT(DISTINCT metric_key) AS REAL),
        16.0,
        COUNT(DISTINCT metric_key),
        CASE WHEN COUNT(DISTINCT metric_key) = 16 THEN 0 ELSE 1 END,
        'CANONICAL_METRIC_COUNT',
        'Canonical catalog rows must resolve to 16 metric keys.'
    FROM source_metric_catalog
    WHERE source_role = 'canonical'

    UNION ALL

    SELECT
        'S07_DIM_METRIC_ROWS',
        'DIM_METRIC',
        CAST(COUNT(*) AS REAL),
        16.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 16 THEN 0 ELSE 1 END,
        'DIM_METRIC_COUNT',
        'dim_metric must contain one row per canonical metric.'
    FROM dim_metric

    UNION ALL

    SELECT
        'S08_DIM_ENTITY_ROWS',
        'DIM_ENTITY',
        CAST(COUNT(*) AS REAL),
        256.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 256 THEN 0 ELSE 1 END,
        'DIM_ENTITY_COUNT',
        'The union of canonical sources must contain 256 entities.'
    FROM dim_entity

    UNION ALL

    SELECT
        'S09_CURRENT_ENTITIES',
        'DIM_ENTITY',
        CAST(COUNT(*) AS REAL),
        215.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 215 THEN 0 ELSE 1 END,
        'CURRENT_ENTITY_COUNT',
        'Current country/territory population, including Kosovo.'
    FROM dim_entity
    WHERE is_current_country_or_territory = 1

    UNION ALL

    SELECT
        'S10_ASEAN_ENTITIES',
        'DIM_ENTITY',
        CAST(COUNT(*) AS REAL),
        10.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 10 THEN 0 ELSE 1 END,
        'ASEAN_ENTITY_COUNT',
        'ASEAN membership is fixed to the ten Phase 2 countries.'
    FROM dim_entity
    WHERE is_asean = 1

    UNION ALL

    SELECT
        'S11_FACT_ROWS',
        'FACT_ENERGY',
        CAST(COUNT(*) AS REAL),
        89075.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 89075 THEN 0 ELSE 1 END,
        'FACT_ROW_COUNT',
        'Expected canonical observation count after source cutoffs.'
    FROM fact_energy

    UNION ALL

    SELECT
        'S12_ZERO_ROWS',
        'FACT_ENERGY',
        CAST(COUNT(*) AS REAL),
        36153.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 36153 THEN 0 ELSE 1 END,
        'ZERO_PRESERVATION',
        'Observed zeroes must remain observations and must not become NULL.'
    FROM fact_energy
    WHERE value = 0

    UNION ALL

    SELECT
        'S13_POSITIVE_ROWS',
        'FACT_ENERGY',
        CAST(COUNT(*) AS REAL),
        52922.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 52922 THEN 0 ELSE 1 END,
        'POSITIVE_ROW_COUNT',
        'Expected count of positive canonical observations.'
    FROM fact_energy
    WHERE value > 0

    UNION ALL

    SELECT
        'S14_ENTITY_YEAR_KEYS',
        'FACT_ENERGY',
        CAST(COUNT(*) AS REAL),
        8968.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 8968 THEN 0 ELSE 1 END,
        'ENTITY_YEAR_COUNT',
        'Expected distinct entity-year keys in the wide convenience view.'
    FROM (
        SELECT entity, year
        FROM fact_energy
        GROUP BY entity, year
    ) AS entity_years

    UNION ALL

    SELECT
        'S15_MAIN_WINDOW_YEARS',
        'DIM_YEAR',
        CAST(COUNT(*) AS REAL),
        22.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 22 THEN 0 ELSE 1 END,
        'MAIN_WINDOW_YEAR_COUNT',
        'The main ASEAN analysis window is 2000 through 2021 inclusive.'
    FROM dim_year
    WHERE is_main_asean_window = 1

    UNION ALL

    SELECT
        'S16_ASEAN_MAIN_PANEL',
        'ASEAN_10_2000_2021_EIGHT_MAIN_METRICS',
        CAST(COUNT(*) AS REAL),
        1760.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 1760 THEN 0 ELSE 1 END,
        'ASEAN_PANEL_COUNT',
        'Complete panel: 10 entities x 22 years x 4 generation and 4 electricity-share metrics.'
    FROM fact_energy AS f
    JOIN dim_entity AS e
      ON e.entity = f.entity
    WHERE e.is_asean = 1
      AND f.year BETWEEN 2000 AND 2021
      AND f.metric_key IN (
          'wind_generation_twh',
          'hydro_generation_twh',
          'solar_generation_twh',
          'other_renewables_generation_twh',
          'renewables_share_electricity_pct',
          'hydro_share_electricity_pct',
          'wind_share_electricity_pct',
          'solar_share_electricity_pct'
      )

    UNION ALL

    SELECT
        'S17_PERCENT_BOUNDARY_SNAPS',
        'CLEANING_AUDIT',
        CAST(COUNT(*) AS REAL),
        3.0,
        COUNT(*),
        CASE WHEN COUNT(*) = 3 THEN 0 ELSE 1 END,
        'PERCENT_BOUNDARY_SNAP_COUNT',
        'Exactly three near-boundary percentages are snapped to 0 or 100 and audited.'
    FROM cleaning_audit AS audit
    JOIN source_metric_catalog AS catalog
      ON catalog.source_file = audit.source_file
     AND catalog.source_column = audit.source_column
     AND catalog.metric_key LIKE '%_pct'
    WHERE audit.old_value <> audit.new_value
      AND audit.new_value IN (0, 100)

    UNION ALL

    SELECT
        'S18_NO_IMPUTATION',
        'CLEANING_AUDIT',
        CAST(COUNT(*) AS REAL),
        0.0,
        COUNT(*),
        COUNT(*),
        'NO_IMPUTATION',
        'No interpolation, forward/backward fill, or other imputation is allowed.'
    FROM cleaning_audit
    WHERE UPPER(COALESCE(action, '')) LIKE '%IMPUT%'
       OR UPPER(COALESCE(action, '')) LIKE '%FILL%'
       OR UPPER(COALESCE(action, '')) LIKE '%INTERPOL%'
       OR UPPER(COALESCE(reason, '')) LIKE '%IMPUT%'
       OR UPPER(COALESCE(reason, '')) LIKE '%FILL%'
       OR UPPER(COALESCE(reason, '')) LIKE '%INTERPOL%'

    UNION ALL

    SELECT
        'S19_GEOTHERMAL_SAMPLING_SERIES',
        'MISSINGNESS_AUDIT',
        CAST(COUNT(DISTINCT entity) AS REAL),
        23.0,
        COUNT(DISTINCT entity),
        CASE WHEN COUNT(DISTINCT entity) = 23 THEN 0 ELSE 1 END,
        'CURRENT_SAMPLING_GRID_SERIES_COUNT',
        'Phase 1 finds 31 sampling-grid series; the current-country-only missingness spine represents 23 of them.'
    FROM missingness_audit
    WHERE metric_key = 'geothermal_capacity_gw'
      AND (
          missing_region = 'SAMPLING_GRID_NOT_MISSING'
          OR decision = 'SAMPLING_GRID_NOT_MISSING'
      )
)
INSERT INTO validation_results (
    check_id,
    scope,
    metric,
    year,
    status,
    is_blocking,
    observed,
    expected,
    abs_diff,
    rel_diff_pct,
    abs_tol,
    rel_tol_pct,
    compared_rows,
    exception_rows,
    reason_code,
    note
)
SELECT
    check_id,
    scope,
    NULL,
    NULL,
    CASE WHEN exception_rows = 0 AND observed = expected THEN 'PASS' ELSE 'FAIL' END,
    1,
    observed,
    expected,
    ABS(observed - expected),
    CASE
        WHEN expected = 0 AND observed = 0 THEN 0.0
        WHEN expected = 0 THEN NULL
        ELSE ABS(observed - expected) * 100.0 / ABS(expected)
    END,
    0.0,
    NULL,
    compared_rows,
    exception_rows,
    reason_code,
    note
FROM structural_checks;

-- Structural integrity checks whose expected exception count is zero.
WITH integrity_checks (
    check_id,
    scope,
    compared_rows,
    exception_rows,
    reason_code,
    note
) AS (
    SELECT
        'S20_CATALOG_UNIQUE_MAPPING',
        'SOURCE_METRIC_CATALOG',
        COUNT(*),
        COALESCE(SUM(mapping_count - 1), 0),
        'DUPLICATE_SOURCE_MAPPING',
        'A source file/column pair may appear only once in the catalog.'
    FROM (
        SELECT source_file, source_column, COUNT(*) AS mapping_count
        FROM source_metric_catalog
        GROUP BY source_file, source_column
        HAVING COUNT(*) > 1
    ) AS duplicates

    UNION ALL

    SELECT
        'S21_CATALOG_VALID_ROLES',
        'SOURCE_METRIC_CATALOG',
        COUNT(*),
        SUM(CASE WHEN source_role NOT IN ('canonical', 'audit', 'excluded') THEN 1 ELSE 0 END),
        'INVALID_SOURCE_ROLE',
        'Catalog role must be canonical, audit, or excluded.'
    FROM source_metric_catalog

    UNION ALL

    SELECT
        'S22_DIM_METRIC_CATALOG_MATCH',
        'DIM_METRIC',
        COUNT(*),
        SUM(CASE WHEN c.metric_key IS NULL THEN 1 ELSE 0 END),
        'MISSING_CANONICAL_CATALOG_ROW',
        'Every dim_metric row must match one canonical catalog mapping.'
    FROM dim_metric AS m
    LEFT JOIN source_metric_catalog AS c
      ON c.metric_key = m.metric_key
     AND c.source_file = m.source_file
     AND c.source_column = m.source_column
     AND c.source_role = 'canonical'

    UNION ALL

    SELECT
        'S23_FACT_ENTITY_FK',
        'FACT_ENERGY',
        COUNT(*),
        SUM(CASE WHEN e.entity IS NULL THEN 1 ELSE 0 END),
        'ORPHAN_ENTITY',
        'Every fact row must resolve to dim_entity.'
    FROM fact_energy AS f
    LEFT JOIN dim_entity AS e
      ON e.entity = f.entity

    UNION ALL

    SELECT
        'S24_FACT_YEAR_FK',
        'FACT_ENERGY',
        COUNT(*),
        SUM(CASE WHEN y.year IS NULL THEN 1 ELSE 0 END),
        'ORPHAN_YEAR',
        'Every fact row must resolve to dim_year.'
    FROM fact_energy AS f
    LEFT JOIN dim_year AS y
      ON y.year = f.year

    UNION ALL

    SELECT
        'S25_FACT_METRIC_FK',
        'FACT_ENERGY',
        COUNT(*),
        SUM(CASE WHEN m.metric_key IS NULL THEN 1 ELSE 0 END),
        'ORPHAN_METRIC',
        'Every fact row must resolve to dim_metric.'
    FROM fact_energy AS f
    LEFT JOIN dim_metric AS m
      ON m.metric_key = f.metric_key

    UNION ALL

    SELECT
        'S26_FACT_CANONICAL_SOURCE',
        'FACT_ENERGY',
        COUNT(*),
        SUM(CASE WHEN c.source_file IS NULL THEN 1 ELSE 0 END),
        'NON_CANONICAL_FACT_SOURCE',
        'Every fact metric/source pair must have a canonical catalog row.'
    FROM fact_energy AS f
    LEFT JOIN source_metric_catalog AS c
      ON c.metric_key = f.metric_key
     AND c.source_file = f.source_file
     AND c.source_role = 'canonical'

    UNION ALL

    SELECT
        'S27_FACT_DIM_SOURCE_MATCH',
        'FACT_ENERGY',
        COUNT(*),
        SUM(
            CASE
                WHEN m.metric_key IS NULL OR f.source_file <> m.source_file THEN 1
                ELSE 0
            END
        ),
        'METRIC_SOURCE_MISMATCH',
        'Fact lineage must agree with the source selected by dim_metric.'
    FROM fact_energy AS f
    LEFT JOIN dim_metric AS m
      ON m.metric_key = f.metric_key

    UNION ALL

    SELECT
        'S28_FACT_VALUE_DTYPE',
        'FACT_ENERGY',
        COUNT(*),
        SUM(CASE WHEN TYPEOF(value) NOT IN ('integer', 'real') THEN 1 ELSE 0 END),
        'NON_NUMERIC_VALUE',
        'Canonical values must have a numeric SQLite storage class.'
    FROM fact_energy

    UNION ALL

    SELECT
        'S29_FACT_NO_NULL_VALUE',
        'FACT_ENERGY',
        COUNT(*),
        SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END),
        'NULL_IN_FACT',
        'Missing observations belong in missingness_audit, never fact_energy.'
    FROM fact_energy

    UNION ALL

    SELECT
        'S30_METRIC_CUTOFF',
        'FACT_ENERGY',
        COUNT(*),
        SUM(
            CASE
                WHEN f.year > m.analysis_end_year THEN 1
                ELSE 0
            END
        ),
        'YEAR_AFTER_METRIC_CUTOFF',
        'No fact observation may exceed its metric-specific Phase 2 cutoff.'
    FROM fact_energy AS f
    JOIN dim_metric AS m
      ON m.metric_key = f.metric_key

    UNION ALL

    SELECT
        'S31_VALUE_CLASS',
        'FACT_ENERGY',
        COUNT(*),
        SUM(
            CASE
                WHEN value = 0 AND value_class = 'Zero' THEN 0
                WHEN value > 0
                 AND value < m.trace_threshold
                 AND value_class = 'Trace' THEN 0
                WHEN value >= m.trace_threshold
                 AND value_class = 'Material' THEN 0
                ELSE 1
            END
        ),
        'VALUE_CLASS_MISMATCH',
        'Zero/Trace/Material must follow the metric-specific trace threshold.'
    FROM fact_energy AS f
    JOIN dim_metric AS m
      ON m.metric_key = f.metric_key
)
INSERT INTO validation_results (
    check_id,
    scope,
    metric,
    year,
    status,
    is_blocking,
    observed,
    expected,
    abs_diff,
    rel_diff_pct,
    abs_tol,
    rel_tol_pct,
    compared_rows,
    exception_rows,
    reason_code,
    note
)
SELECT
    check_id,
    scope,
    NULL,
    NULL,
    CASE WHEN COALESCE(exception_rows, 0) = 0 THEN 'PASS' ELSE 'FAIL' END,
    1,
    CAST(COALESCE(exception_rows, 0) AS REAL),
    0.0,
    CAST(COALESCE(exception_rows, 0) AS REAL),
    NULL,
    0.0,
    NULL,
    compared_rows,
    COALESCE(exception_rows, 0),
    reason_code,
    note
FROM integrity_checks;

-- -------------------------------------------------------------------------
-- V1: sum of current countries/territories versus World.
-- Four additive generation metrics from canonical file 03, 2000-2021.
-- PASS when abs_diff <= max(0.05 TWh, 0.01% of abs(World)).
-- -------------------------------------------------------------------------

WITH generation_metrics (metric_key) AS (
    VALUES
        ('wind_generation_twh'),
        ('hydro_generation_twh'),
        ('solar_generation_twh'),
        ('other_renewables_generation_twh')
),
metric_years AS (
    SELECT m.metric_key, y.year
    FROM generation_metrics AS m
    CROSS JOIN dim_year AS y
    WHERE y.year BETWEEN 2000 AND 2021
),
country_totals AS (
    SELECT
        f.metric_key,
        f.year,
        SUM(f.value) AS observed,
        COUNT(*) AS component_count
    FROM fact_energy AS f
    JOIN dim_entity AS e
      ON e.entity = f.entity
    WHERE e.is_current_country_or_territory = 1
      AND f.year BETWEEN 2000 AND 2021
      AND f.metric_key IN (
          'wind_generation_twh',
          'hydro_generation_twh',
          'solar_generation_twh',
          'other_renewables_generation_twh'
      )
    GROUP BY f.metric_key, f.year
),
world_values AS (
    SELECT metric_key, year, value AS expected
    FROM fact_energy
    WHERE entity = 'World'
      AND year BETWEEN 2000 AND 2021
      AND metric_key IN (
          'wind_generation_twh',
          'hydro_generation_twh',
          'solar_generation_twh',
          'other_renewables_generation_twh'
      )
),
comparisons AS (
    SELECT
        grid.metric_key,
        grid.year,
        countries.observed,
        world.expected,
        COALESCE(countries.component_count, 0) AS component_count,
        CASE
            WHEN countries.observed IS NULL OR world.expected IS NULL THEN NULL
            ELSE ABS(countries.observed - world.expected)
        END AS abs_diff,
        CASE
            WHEN world.expected IS NULL OR countries.observed IS NULL THEN NULL
            WHEN world.expected = 0 AND countries.observed = world.expected THEN 0.0
            WHEN world.expected = 0 THEN NULL
            ELSE ABS(countries.observed - world.expected) * 100.0 / ABS(world.expected)
        END AS rel_diff_pct,
        CASE
            WHEN world.expected IS NULL THEN NULL
            ELSE MAX(0.05, 0.0001 * ABS(world.expected))
        END AS abs_tol
    FROM metric_years AS grid
    LEFT JOIN country_totals AS countries
      ON countries.metric_key = grid.metric_key
     AND countries.year = grid.year
    LEFT JOIN world_values AS world
      ON world.metric_key = grid.metric_key
     AND world.year = grid.year
)
INSERT INTO validation_results (
    check_id,
    scope,
    metric,
    year,
    status,
    is_blocking,
    observed,
    expected,
    abs_diff,
    rel_diff_pct,
    abs_tol,
    rel_tol_pct,
    compared_rows,
    exception_rows,
    reason_code,
    note
)
SELECT
    'V1',
    'CURRENT_COUNTRIES_VS_WORLD',
    metric_key,
    year,
    CASE
        WHEN observed IS NULL OR expected IS NULL THEN 'SKIP'
        WHEN abs_diff <= abs_tol THEN 'PASS'
        ELSE 'WARN'
    END,
    0,
    observed,
    expected,
    abs_diff,
    rel_diff_pct,
    abs_tol,
    0.01,
    component_count,
    CASE WHEN observed IS NOT NULL AND expected IS NOT NULL AND abs_diff > abs_tol THEN 1 ELSE 0 END,
    CASE
        WHEN observed IS NULL OR expected IS NULL THEN 'MISSING_COMPARAND'
        WHEN abs_diff <= abs_tol THEN 'WITHIN_TOLERANCE'
        ELSE 'RECONCILIATION_DIFFERENCE'
    END,
    'Sum of observed values for the 215 current country/territory dimension members versus World.'
FROM comparisons;

-- V1 is deliberately skipped for non-additive percentages and metrics whose
-- source population/coverage is not the complete country aggregation basis.
INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V1',
    'INAPPLICABLE_METRIC',
    metric_key,
    NULL,
    'SKIP',
    0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    0,
    CASE
        WHEN metric_key LIKE '%_pct' THEN 'NON_ADDITIVE_PERCENTAGE'
        ELSE 'COVERAGE_LIMITED_METRIC'
    END,
    CASE
        WHEN metric_key LIKE '%_pct' THEN 'Percentage metrics cannot be summed across entities.'
        ELSE 'This metric does not use the complete file-03 country aggregation basis.'
    END
FROM dim_metric
WHERE metric_key NOT IN (
    'wind_generation_twh',
    'hydro_generation_twh',
    'solar_generation_twh',
    'other_renewables_generation_twh'
);

-- -------------------------------------------------------------------------
-- V2: sum of the six standard continent aggregates versus World.
-- -------------------------------------------------------------------------

WITH generation_metrics (metric_key) AS (
    VALUES
        ('wind_generation_twh'),
        ('hydro_generation_twh'),
        ('solar_generation_twh'),
        ('other_renewables_generation_twh')
),
metric_years AS (
    SELECT m.metric_key, y.year
    FROM generation_metrics AS m
    CROSS JOIN dim_year AS y
    WHERE y.year BETWEEN 2000 AND 2021
),
continent_totals AS (
    SELECT
        metric_key,
        year,
        SUM(value) AS observed,
        COUNT(*) AS component_count
    FROM fact_energy
    WHERE entity IN (
        'Africa',
        'Asia',
        'Europe',
        'North America',
        'Oceania',
        'South America'
    )
      AND year BETWEEN 2000 AND 2021
      AND metric_key IN (
          'wind_generation_twh',
          'hydro_generation_twh',
          'solar_generation_twh',
          'other_renewables_generation_twh'
      )
    GROUP BY metric_key, year
),
world_values AS (
    SELECT metric_key, year, value AS expected
    FROM fact_energy
    WHERE entity = 'World'
      AND year BETWEEN 2000 AND 2021
      AND metric_key IN (
          'wind_generation_twh',
          'hydro_generation_twh',
          'solar_generation_twh',
          'other_renewables_generation_twh'
      )
),
comparisons AS (
    SELECT
        grid.metric_key,
        grid.year,
        continents.observed,
        world.expected,
        COALESCE(continents.component_count, 0) AS component_count,
        CASE
            WHEN continents.observed IS NULL OR world.expected IS NULL THEN NULL
            ELSE ABS(continents.observed - world.expected)
        END AS abs_diff,
        CASE
            WHEN world.expected IS NULL OR continents.observed IS NULL THEN NULL
            WHEN world.expected = 0 AND continents.observed = world.expected THEN 0.0
            WHEN world.expected = 0 THEN NULL
            ELSE ABS(continents.observed - world.expected) * 100.0 / ABS(world.expected)
        END AS rel_diff_pct,
        CASE
            WHEN world.expected IS NULL THEN NULL
            ELSE MAX(0.05, 0.0001 * ABS(world.expected))
        END AS abs_tol
    FROM metric_years AS grid
    LEFT JOIN continent_totals AS continents
      ON continents.metric_key = grid.metric_key
     AND continents.year = grid.year
    LEFT JOIN world_values AS world
      ON world.metric_key = grid.metric_key
     AND world.year = grid.year
)
INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V2',
    'SIX_CONTINENTS_VS_WORLD',
    metric_key,
    year,
    CASE
        WHEN observed IS NULL OR expected IS NULL OR component_count <> 6 THEN 'SKIP'
        WHEN abs_diff <= abs_tol THEN 'PASS'
        ELSE 'WARN'
    END,
    0,
    observed,
    expected,
    abs_diff,
    rel_diff_pct,
    abs_tol,
    0.01,
    component_count,
    CASE
        WHEN component_count = 6 AND observed IS NOT NULL AND expected IS NOT NULL AND abs_diff > abs_tol THEN 1
        ELSE 0
    END,
    CASE
        WHEN observed IS NULL OR expected IS NULL THEN 'MISSING_COMPARAND'
        WHEN component_count <> 6 THEN 'INCOMPLETE_CONTINENT_SET'
        WHEN abs_diff <= abs_tol THEN 'WITHIN_TOLERANCE'
        ELSE 'RECONCILIATION_DIFFERENCE'
    END,
    'Africa + Asia + Europe + North America + Oceania + South America versus World.'
FROM comparisons;

INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V2',
    'INAPPLICABLE_METRIC',
    metric_key,
    NULL,
    'SKIP',
    0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    0,
    CASE
        WHEN metric_key LIKE '%_pct' THEN 'NON_ADDITIVE_PERCENTAGE'
        ELSE 'COVERAGE_LIMITED_METRIC'
    END,
    CASE
        WHEN metric_key LIKE '%_pct' THEN 'Percentage metrics cannot be summed across continent aggregates.'
        ELSE 'This metric does not use the complete file-03 continent aggregation basis.'
    END
FROM dim_metric
WHERE metric_key NOT IN (
    'wind_generation_twh',
    'hydro_generation_twh',
    'solar_generation_twh',
    'other_renewables_generation_twh'
);

-- -------------------------------------------------------------------------
-- V3: sum of the four World Bank income aggregates versus World.
-- -------------------------------------------------------------------------

WITH generation_metrics (metric_key) AS (
    VALUES
        ('wind_generation_twh'),
        ('hydro_generation_twh'),
        ('solar_generation_twh'),
        ('other_renewables_generation_twh')
),
metric_years AS (
    SELECT m.metric_key, y.year
    FROM generation_metrics AS m
    CROSS JOIN dim_year AS y
    WHERE y.year BETWEEN 2000 AND 2021
),
income_totals AS (
    SELECT
        metric_key,
        year,
        SUM(value) AS observed,
        COUNT(*) AS component_count
    FROM fact_energy
    WHERE entity IN (
        'High-income countries',
        'Upper-middle-income countries',
        'Lower-middle-income countries',
        'Low-income countries'
    )
      AND year BETWEEN 2000 AND 2021
      AND metric_key IN (
          'wind_generation_twh',
          'hydro_generation_twh',
          'solar_generation_twh',
          'other_renewables_generation_twh'
      )
    GROUP BY metric_key, year
),
world_values AS (
    SELECT metric_key, year, value AS expected
    FROM fact_energy
    WHERE entity = 'World'
      AND year BETWEEN 2000 AND 2021
      AND metric_key IN (
          'wind_generation_twh',
          'hydro_generation_twh',
          'solar_generation_twh',
          'other_renewables_generation_twh'
      )
),
comparisons AS (
    SELECT
        grid.metric_key,
        grid.year,
        incomes.observed,
        world.expected,
        COALESCE(incomes.component_count, 0) AS component_count,
        CASE
            WHEN incomes.observed IS NULL OR world.expected IS NULL THEN NULL
            ELSE ABS(incomes.observed - world.expected)
        END AS abs_diff,
        CASE
            WHEN world.expected IS NULL OR incomes.observed IS NULL THEN NULL
            WHEN world.expected = 0 AND incomes.observed = world.expected THEN 0.0
            WHEN world.expected = 0 THEN NULL
            ELSE ABS(incomes.observed - world.expected) * 100.0 / ABS(world.expected)
        END AS rel_diff_pct,
        CASE
            WHEN world.expected IS NULL THEN NULL
            ELSE MAX(0.05, 0.0001 * ABS(world.expected))
        END AS abs_tol
    FROM metric_years AS grid
    LEFT JOIN income_totals AS incomes
      ON incomes.metric_key = grid.metric_key
     AND incomes.year = grid.year
    LEFT JOIN world_values AS world
      ON world.metric_key = grid.metric_key
     AND world.year = grid.year
)
INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V3',
    'FOUR_INCOME_GROUPS_VS_WORLD',
    metric_key,
    year,
    CASE
        WHEN observed IS NULL OR expected IS NULL OR component_count <> 4 THEN 'SKIP'
        WHEN abs_diff <= abs_tol THEN 'PASS'
        ELSE 'WARN'
    END,
    0,
    observed,
    expected,
    abs_diff,
    rel_diff_pct,
    abs_tol,
    0.01,
    component_count,
    CASE
        WHEN component_count = 4 AND observed IS NOT NULL AND expected IS NOT NULL AND abs_diff > abs_tol THEN 1
        ELSE 0
    END,
    CASE
        WHEN observed IS NULL OR expected IS NULL THEN 'MISSING_COMPARAND'
        WHEN component_count <> 4 THEN 'INCOMPLETE_INCOME_GROUP_SET'
        WHEN abs_diff <= abs_tol THEN 'WITHIN_TOLERANCE'
        ELSE 'RECONCILIATION_DIFFERENCE'
    END,
    'Four income-group aggregates versus World; only additive file-03 TWh metrics are eligible.'
FROM comparisons;

INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V3',
    'INAPPLICABLE_METRIC',
    metric_key,
    NULL,
    'SKIP',
    0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    0,
    CASE
        WHEN metric_key LIKE '%_pct' THEN 'NON_ADDITIVE_PERCENTAGE'
        ELSE 'COVERAGE_LIMITED_METRIC'
    END,
    CASE
        WHEN metric_key LIKE '%_pct' THEN 'Percentage metrics cannot be summed across income aggregates.'
        ELSE 'This metric does not use the complete file-03 income aggregation basis.'
    END
FROM dim_metric
WHERE metric_key NOT IN (
    'wind_generation_twh',
    'hydro_generation_twh',
    'solar_generation_twh',
    'other_renewables_generation_twh'
);

-- -------------------------------------------------------------------------
-- V4: six exact-boundary canonical-versus-Ember aggregate pairs.
-- A difference is material only when BOTH abs_diff > 0.05 TWh and
-- rel_diff_pct > 1%, matching the Phase 1 conflict rule.
-- -------------------------------------------------------------------------

WITH region_pairs (canonical_entity, ember_entity) AS (
    VALUES
        ('Africa', 'Africa (Ember)'),
        ('Asia', 'Asia (Ember)'),
        ('Europe', 'Europe (Ember)'),
        ('European Union (27)', 'European Union (27) (Ember)'),
        ('North America', 'North America (Ember)'),
        ('Oceania', 'Oceania (Ember)')
),
generation_metrics (metric_key) AS (
    VALUES
        ('wind_generation_twh'),
        ('hydro_generation_twh'),
        ('solar_generation_twh'),
        ('other_renewables_generation_twh')
),
comparison_grid AS (
    SELECT
        pairs.canonical_entity,
        pairs.ember_entity,
        metrics.metric_key,
        years.year
    FROM region_pairs AS pairs
    CROSS JOIN generation_metrics AS metrics
    CROSS JOIN dim_year AS years
    WHERE years.year BETWEEN 2000 AND 2021
),
raw_comparisons AS (
    SELECT
        grid.canonical_entity,
        grid.ember_entity,
        grid.metric_key,
        grid.year,
        canonical.value AS canonical_value,
        ember.value AS ember_value
    FROM comparison_grid AS grid
    LEFT JOIN fact_energy AS canonical
      ON canonical.entity = grid.canonical_entity
     AND canonical.metric_key = grid.metric_key
     AND canonical.year = grid.year
    LEFT JOIN fact_energy AS ember
      ON ember.entity = grid.ember_entity
     AND ember.metric_key = grid.metric_key
     AND ember.year = grid.year
),
comparisons AS (
    SELECT
        canonical_entity,
        ember_entity,
        metric_key,
        year,
        canonical_value,
        ember_value,
        CASE
            WHEN canonical_value IS NULL OR ember_value IS NULL THEN NULL
            ELSE ABS(canonical_value - ember_value)
        END AS abs_diff,
        CASE
            WHEN canonical_value IS NULL OR ember_value IS NULL THEN NULL
            WHEN canonical_value = 0 AND ember_value = 0 THEN 0.0
            ELSE ABS(canonical_value - ember_value) * 100.0
                 / MAX(ABS(canonical_value), ABS(ember_value))
        END AS rel_diff_pct
    FROM raw_comparisons
)
INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V4',
    canonical_entity || ' vs ' || ember_entity,
    metric_key,
    year,
    CASE
        WHEN canonical_value IS NULL OR ember_value IS NULL THEN 'SKIP'
        WHEN abs_diff > 0.05 AND rel_diff_pct > 1.0 THEN 'WARN'
        ELSE 'PASS'
    END,
    0,
    canonical_value,
    ember_value,
    abs_diff,
    rel_diff_pct,
    0.05,
    1.0,
    CASE WHEN canonical_value IS NULL OR ember_value IS NULL THEN 0 ELSE 1 END,
    CASE
        WHEN canonical_value IS NOT NULL
         AND ember_value IS NOT NULL
         AND abs_diff > 0.05
         AND rel_diff_pct > 1.0 THEN 1
        ELSE 0
    END,
    CASE
        WHEN canonical_value IS NULL OR ember_value IS NULL THEN 'MISSING_COMPARAND'
        WHEN abs_diff = 0 THEN 'EXACT_MATCH'
        WHEN abs_diff > 0.05 AND rel_diff_pct > 1.0 THEN 'MATERIAL_DIFFERENCE'
        ELSE 'IMMATERIAL_DIFFERENCE'
    END,
    'Only like-for-like OWID aggregate boundaries are compared; differently bounded BP regions are excluded.'
FROM comparisons;

-- -------------------------------------------------------------------------
-- V5: renewables electricity share is at least hydro + wind + solar share,
-- allowing only a 0.0001 percentage-point numeric epsilon.
-- -------------------------------------------------------------------------

WITH component_comparisons AS (
    SELECT
        renewables.entity,
        renewables.year,
        entity.is_asean,
        renewables.value AS renewables_pct,
        hydro.value + wind.value + solar.value AS component_pct,
        CASE
            WHEN renewables.value + 0.0001
                 >= hydro.value + wind.value + solar.value THEN 0
            ELSE 1
        END AS is_exception
    FROM fact_energy AS renewables
    JOIN fact_energy AS hydro
      ON hydro.entity = renewables.entity
     AND hydro.year = renewables.year
     AND hydro.metric_key = 'hydro_share_electricity_pct'
    JOIN fact_energy AS wind
      ON wind.entity = renewables.entity
     AND wind.year = renewables.year
     AND wind.metric_key = 'wind_share_electricity_pct'
    JOIN fact_energy AS solar
      ON solar.entity = renewables.entity
     AND solar.year = renewables.year
     AND solar.metric_key = 'solar_share_electricity_pct'
    JOIN dim_entity AS entity
      ON entity.entity = renewables.entity
    WHERE renewables.metric_key = 'renewables_share_electricity_pct'
      AND renewables.year BETWEEN 2000 AND 2021
),
summary AS (
    SELECT
        'ALL_ENTITY_YEARS' AS scope,
        COUNT(*) AS compared_rows,
        COALESCE(SUM(is_exception), 0) AS exception_rows
    FROM component_comparisons

    UNION ALL

    SELECT
        'ASEAN_10_2000_2021',
        COUNT(*),
        COALESCE(SUM(is_exception), 0)
    FROM component_comparisons
    WHERE is_asean = 1
)
INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V5',
    scope,
    'renewables_share_electricity_pct',
    NULL,
    CASE
        WHEN compared_rows = 0 THEN 'SKIP'
        WHEN exception_rows = 0 THEN 'PASS'
        ELSE 'WARN'
    END,
    0,
    CAST(compared_rows - exception_rows AS REAL),
    CAST(compared_rows AS REAL),
    CAST(exception_rows AS REAL),
    CASE
        WHEN compared_rows = 0 THEN NULL
        ELSE exception_rows * 100.0 / compared_rows
    END,
    0.0001,
    NULL,
    compared_rows,
    exception_rows,
    CASE
        WHEN compared_rows = 0 THEN 'NO_COMPARABLE_ROWS'
        WHEN exception_rows = 0 THEN 'COMPONENT_BOUND_SATISFIED'
        ELSE 'COMPONENT_BOUND_EXCEEDED'
    END,
    'Pass count versus comparable entity-years for renewables >= hydro + wind + solar - 0.0001 percentage points.'
FROM summary;

-- -------------------------------------------------------------------------
-- V6-V8: blocking hard gates.
-- -------------------------------------------------------------------------

WITH duplicate_groups AS (
    SELECT COUNT(*) AS row_count
    FROM fact_energy
    GROUP BY entity, year, metric_key
    HAVING COUNT(*) > 1
),
duplicate_summary AS (
    SELECT COALESCE(SUM(row_count - 1), 0) AS exception_rows
    FROM duplicate_groups
)
INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V6',
    'CANONICAL_KEY',
    NULL,
    NULL,
    CASE WHEN exception_rows = 0 THEN 'PASS' ELSE 'FAIL' END,
    1,
    CAST(exception_rows AS REAL),
    0.0,
    CAST(exception_rows AS REAL),
    NULL,
    0.0,
    NULL,
    (SELECT COUNT(*) FROM fact_energy),
    exception_rows,
    CASE WHEN exception_rows = 0 THEN 'NO_DUPLICATE_KEYS' ELSE 'DUPLICATE_CANONICAL_KEY' END,
    'Canonical key is (entity, year, metric_key).'
FROM duplicate_summary;

INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V7',
    'ALL_CANONICAL_VALUES',
    NULL,
    NULL,
    CASE WHEN COALESCE(SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END), 0) = 0 THEN 'PASS' ELSE 'FAIL' END,
    1,
    CAST(COALESCE(SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END), 0) AS REAL),
    0.0,
    CAST(COALESCE(SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END), 0) AS REAL),
    NULL,
    0.0,
    NULL,
    COUNT(*),
    COALESCE(SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END), 0),
    CASE
        WHEN COALESCE(SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END), 0) = 0 THEN 'NO_NEGATIVE_VALUES'
        ELSE 'NEGATIVE_CANONICAL_VALUE'
    END,
    'All canonical energy values and percentage points must be non-negative.'
FROM fact_energy;

INSERT INTO validation_results (
    check_id, scope, metric, year, status, is_blocking,
    observed, expected, abs_diff, rel_diff_pct, abs_tol, rel_tol_pct,
    compared_rows, exception_rows, reason_code, note
)
SELECT
    'V8',
    'PERCENTAGE_METRICS',
    NULL,
    NULL,
    CASE
        WHEN COALESCE(SUM(CASE WHEN value < 0 OR value > 100 THEN 1 ELSE 0 END), 0) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END,
    1,
    CAST(COALESCE(SUM(CASE WHEN value < 0 OR value > 100 THEN 1 ELSE 0 END), 0) AS REAL),
    0.0,
    CAST(COALESCE(SUM(CASE WHEN value < 0 OR value > 100 THEN 1 ELSE 0 END), 0) AS REAL),
    NULL,
    0.0,
    NULL,
    COUNT(*),
    COALESCE(SUM(CASE WHEN value < 0 OR value > 100 THEN 1 ELSE 0 END), 0),
    CASE
        WHEN COALESCE(SUM(CASE WHEN value < 0 OR value > 100 THEN 1 ELSE 0 END), 0) = 0 THEN 'PERCENTAGES_IN_RANGE'
        ELSE 'PERCENTAGE_OUT_OF_RANGE'
    END,
    'All metrics whose key ends in _pct must lie in the closed interval [0, 100].'
FROM fact_energy
WHERE metric_key LIKE '%_pct';

-- Human-readable output for sqlite3 CLI and python/run_sql.py. The persistent
-- table is the machine-readable interface used for CSV export and gate status.
SELECT
    check_id,
    scope,
    metric,
    year,
    status,
    is_blocking,
    observed,
    expected,
    abs_diff,
    rel_diff_pct,
    abs_tol,
    rel_tol_pct,
    compared_rows,
    exception_rows,
    reason_code,
    note
FROM validation_results
ORDER BY check_id, metric, year, scope;
