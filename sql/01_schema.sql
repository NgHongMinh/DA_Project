-- Phase 2 canonical data model.
-- Run this script against a staging database: it rebuilds every clean-layer
-- object so the resulting schema is deterministic.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

DROP VIEW IF EXISTS vw_wide;

DROP TABLE IF EXISTS validation_results;
DROP TABLE IF EXISTS cleaning_audit;
DROP TABLE IF EXISTS missingness_audit;
DROP TABLE IF EXISTS fact_energy;
DROP TABLE IF EXISTS dim_year;
DROP TABLE IF EXISTS dim_entity;
DROP TABLE IF EXISTS dim_metric;
DROP TABLE IF EXISTS source_metric_catalog;

CREATE TABLE source_metric_catalog (
    source_file         TEXT    NOT NULL,
    source_column       TEXT    NOT NULL,
    source_role         TEXT    NOT NULL,
    metric_key          TEXT    NOT NULL,
    technology          TEXT    NOT NULL,
    metric              TEXT    NOT NULL,
    source_unit         TEXT    NOT NULL,
    canonical_unit      TEXT    NOT NULL,
    conversion_factor   REAL    NOT NULL,
    scope               TEXT    NOT NULL,
    trace_threshold     REAL    NOT NULL,
    analysis_start_year INTEGER NOT NULL,
    analysis_end_year   INTEGER NOT NULL,
    decision_reason     TEXT    NOT NULL,

    PRIMARY KEY (source_file, source_column),

    CHECK (length(trim(source_file)) > 0),
    CHECK (length(trim(source_column)) > 0),
    CHECK (source_role IN ('canonical', 'audit', 'excluded')),
    CHECK (length(trim(metric_key)) > 0),
    CHECK (length(trim(technology)) > 0),
    CHECK (length(trim(metric)) > 0),
    CHECK (length(trim(source_unit)) > 0),
    CHECK (length(trim(canonical_unit)) > 0),
    CHECK (conversion_factor > 0.0 AND conversion_factor < 1.0e308),
    CHECK (length(trim(scope)) > 0),
    CHECK (trace_threshold > 0.0 AND trace_threshold < 1.0e308),
    CHECK (analysis_start_year BETWEEN 1800 AND 2100),
    CHECK (analysis_end_year BETWEEN 1800 AND 2100),
    CHECK (analysis_start_year <= analysis_end_year),
    CHECK (length(trim(decision_reason)) > 0)
) STRICT;

CREATE INDEX idx_source_metric_catalog_role
    ON source_metric_catalog (source_role, source_file);
CREATE INDEX idx_source_metric_catalog_metric
    ON source_metric_catalog (metric_key, source_role);

CREATE TABLE dim_metric (
    metric_key          TEXT    PRIMARY KEY NOT NULL,
    technology          TEXT    NOT NULL,
    metric              TEXT    NOT NULL,
    canonical_unit      TEXT    NOT NULL,
    source_unit         TEXT    NOT NULL,
    conversion_factor   REAL    NOT NULL,
    source_file         TEXT    NOT NULL,
    source_column       TEXT    NOT NULL,
    scope               TEXT    NOT NULL,
    trace_threshold     REAL    NOT NULL,
    analysis_start_year INTEGER NOT NULL,
    analysis_end_year   INTEGER NOT NULL,

    UNIQUE (source_file, source_column),
    UNIQUE (metric_key, source_file),

    FOREIGN KEY (source_file, source_column)
        REFERENCES source_metric_catalog (source_file, source_column)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK (length(trim(metric_key)) > 0),
    CHECK (length(trim(technology)) > 0),
    CHECK (length(trim(metric)) > 0),
    CHECK (length(trim(canonical_unit)) > 0),
    CHECK (length(trim(source_unit)) > 0),
    CHECK (conversion_factor > 0.0 AND conversion_factor < 1.0e308),
    CHECK (length(trim(source_file)) > 0),
    CHECK (length(trim(source_column)) > 0),
    CHECK (length(trim(scope)) > 0),
    CHECK (trace_threshold > 0.0 AND trace_threshold < 1.0e308),
    CHECK (analysis_start_year BETWEEN 1800 AND 2100),
    CHECK (analysis_end_year BETWEEN 1800 AND 2100),
    CHECK (analysis_start_year <= analysis_end_year)
) STRICT;

CREATE INDEX idx_dim_metric_technology_metric
    ON dim_metric (technology, metric);

CREATE TABLE dim_entity (
    entity                          TEXT    PRIMARY KEY NOT NULL,
    iso_code                        TEXT,
    entity_type                     TEXT    NOT NULL,
    is_aggregate                    INTEGER NOT NULL,
    is_current_country_or_territory INTEGER NOT NULL,
    is_asean                        INTEGER NOT NULL,
    is_source_variant               INTEGER NOT NULL,
    canonical_entity                TEXT,
    continent                       TEXT,
    income_group                    TEXT,

    FOREIGN KEY (canonical_entity)
        REFERENCES dim_entity (entity)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
        DEFERRABLE INITIALLY DEFERRED,

    CHECK (length(trim(entity)) > 0),
    CHECK (iso_code IS NULL OR length(trim(iso_code)) > 0),
    CHECK (
        entity_type IN (
            'country_or_territory',
            'continent',
            'income_group',
            'political_bloc',
            'region',
            'world',
            'historical'
        )
    ),
    CHECK (is_aggregate IN (0, 1)),
    CHECK (is_current_country_or_territory IN (0, 1)),
    CHECK (is_asean IN (0, 1)),
    CHECK (is_source_variant IN (0, 1)),
    CHECK (
        (entity_type = 'country_or_territory'
            AND is_aggregate = 0
            AND is_current_country_or_territory = 1)
        OR
        (entity_type = 'historical'
            AND is_aggregate = 0
            AND is_current_country_or_territory = 0)
        OR
        (entity_type NOT IN ('country_or_territory', 'historical')
            AND is_aggregate = 1
            AND is_current_country_or_territory = 0)
    ),
    CHECK (is_asean = 0 OR is_current_country_or_territory = 1),
    CHECK (is_source_variant = 0 OR is_aggregate = 1),
    CHECK (canonical_entity IS NULL OR length(trim(canonical_entity)) > 0),
    CHECK (
        entity_type <> 'country_or_territory'
        OR (continent IS NULL AND income_group IS NULL)
    )
) STRICT;

CREATE UNIQUE INDEX uq_dim_entity_iso_code
    ON dim_entity (iso_code)
    WHERE iso_code IS NOT NULL;
CREATE INDEX idx_dim_entity_type
    ON dim_entity (entity_type, is_aggregate);
CREATE INDEX idx_dim_entity_current_asean
    ON dim_entity (is_current_country_or_territory, is_asean);
CREATE INDEX idx_dim_entity_canonical
    ON dim_entity (canonical_entity)
    WHERE canonical_entity IS NOT NULL;

CREATE TABLE dim_year (
    year                 INTEGER PRIMARY KEY NOT NULL,
    is_main_asean_window INTEGER NOT NULL,

    CHECK (year BETWEEN 1800 AND 2100),
    CHECK (is_main_asean_window IN (0, 1)),
    CHECK (
        is_main_asean_window =
            CASE WHEN year BETWEEN 2000 AND 2021 THEN 1 ELSE 0 END
    )
) STRICT;

CREATE INDEX idx_dim_year_main_asean_window
    ON dim_year (is_main_asean_window, year);

CREATE TABLE fact_energy (
    entity      TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    metric_key  TEXT    NOT NULL,
    value       REAL    NOT NULL,
    value_class TEXT    NOT NULL,
    source_file TEXT    NOT NULL,

    PRIMARY KEY (entity, year, metric_key),

    FOREIGN KEY (entity)
        REFERENCES dim_entity (entity)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (year)
        REFERENCES dim_year (year)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (metric_key, source_file)
        REFERENCES dim_metric (metric_key, source_file)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK (value >= 0.0 AND value < 1.0e308),
    CHECK (value_class IN ('Zero', 'Trace', 'Material')),
    CHECK (
        (value = 0.0 AND value_class = 'Zero')
        OR
        (value > 0.0 AND value_class IN ('Trace', 'Material'))
    ),
    CHECK (length(trim(source_file)) > 0)
) STRICT;

CREATE INDEX idx_fact_energy_year_metric
    ON fact_energy (year, metric_key);
CREATE INDEX idx_fact_energy_metric_year_value
    ON fact_energy (metric_key, year, value);
CREATE INDEX idx_fact_energy_entity_metric_year
    ON fact_energy (entity, metric_key, year);
CREATE INDEX idx_fact_energy_source_file
    ON fact_energy (source_file);

CREATE TABLE missingness_audit (
    entity         TEXT    NOT NULL,
    year           INTEGER NOT NULL,
    metric_key     TEXT    NOT NULL,
    missing_region TEXT    NOT NULL,
    decision       TEXT    NOT NULL,
    source_file    TEXT    NOT NULL,

    PRIMARY KEY (entity, year, metric_key),

    FOREIGN KEY (entity)
        REFERENCES dim_entity (entity)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (year)
        REFERENCES dim_year (year)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (metric_key, source_file)
        REFERENCES dim_metric (metric_key, source_file)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK (
        missing_region IN (
            'NO_SERIES',
            'BEFORE_FIRST',
            'INTERNAL_GAP',
            'AFTER_LAST',
            'SAMPLING_GRID_NOT_MISSING'
        )
    ),
    CHECK (length(trim(decision)) > 0),
    CHECK (length(trim(source_file)) > 0)
) STRICT;

CREATE INDEX idx_missingness_audit_metric_region
    ON missingness_audit (metric_key, missing_region);
CREATE INDEX idx_missingness_audit_year
    ON missingness_audit (year, metric_key);
CREATE INDEX idx_missingness_audit_decision
    ON missingness_audit (decision);

CREATE TABLE cleaning_audit (
    source_file   TEXT    NOT NULL,
    source_column TEXT    NOT NULL,
    entity        TEXT    NOT NULL,
    year          INTEGER NOT NULL,
    old_value     REAL,
    new_value     REAL,
    action        TEXT    NOT NULL,
    reason        TEXT    NOT NULL,

    PRIMARY KEY (source_file, source_column, entity, year, action),

    FOREIGN KEY (source_file, source_column)
        REFERENCES source_metric_catalog (source_file, source_column)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (entity)
        REFERENCES dim_entity (entity)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CHECK (old_value IS NULL OR abs(old_value) < 1.0e308),
    CHECK (new_value IS NULL OR abs(new_value) < 1.0e308),
    CHECK (length(trim(action)) > 0),
    CHECK (length(trim(reason)) > 0)
) STRICT;

CREATE INDEX idx_cleaning_audit_entity_year
    ON cleaning_audit (entity, year);
CREATE INDEX idx_cleaning_audit_action
    ON cleaning_audit (action, source_file);

-- V1--V8 can emit both summary rows and detailed reconciliation rows.  The
-- surrogate key deliberately permits repeated check/entity/year combinations
-- when a validation has several comparison dimensions.
CREATE TABLE validation_results (
    check_id              TEXT    NOT NULL,
    scope                 TEXT    NOT NULL,
    metric                TEXT,
    year                  INTEGER,
    status                TEXT    NOT NULL,
    is_blocking           INTEGER NOT NULL,
    observed              REAL,
    expected              REAL,
    abs_diff              REAL,
    rel_diff_pct          REAL,
    abs_tol               REAL,
    rel_tol_pct           REAL,
    compared_rows         INTEGER NOT NULL DEFAULT 0,
    exception_rows        INTEGER NOT NULL DEFAULT 0,
    reason_code           TEXT    NOT NULL,
    note                  TEXT    NOT NULL,

    CHECK (length(trim(check_id)) > 0),
    CHECK (length(trim(scope)) > 0),
    CHECK (metric IS NULL OR length(trim(metric)) > 0),
    CHECK (year IS NULL OR year BETWEEN 1800 AND 2100),
    CHECK (status IN ('PASS', 'WARN', 'SKIP', 'FAIL')),
    CHECK (is_blocking IN (0, 1)),
    CHECK (
        is_blocking = 0
        OR status IN ('PASS', 'FAIL')
    ),
    CHECK (observed IS NULL OR abs(observed) < 1.0e308),
    CHECK (expected IS NULL OR abs(expected) < 1.0e308),
    CHECK (abs_diff IS NULL OR (abs_diff >= 0.0 AND abs_diff < 1.0e308)),
    CHECK (
        rel_diff_pct IS NULL
        OR (rel_diff_pct >= 0.0 AND rel_diff_pct < 1.0e308)
    ),
    CHECK (abs_tol IS NULL OR (abs_tol >= 0.0 AND abs_tol < 1.0e308)),
    CHECK (
        rel_tol_pct IS NULL
        OR (rel_tol_pct >= 0.0 AND rel_tol_pct < 1.0e308)
    ),
    CHECK (compared_rows >= 0),
    CHECK (exception_rows >= 0),
    CHECK (length(trim(reason_code)) > 0)
) STRICT;

CREATE INDEX idx_validation_results_check_status
    ON validation_results (check_id, status);
CREATE INDEX idx_validation_results_blocking_status
    ON validation_results (is_blocking, status);
CREATE INDEX idx_validation_results_metric_year
    ON validation_results (metric, year);

CREATE VIEW vw_wide AS
SELECT
    entity,
    year,
    MAX(CASE WHEN metric_key = 'renewables_share_primary_energy_pct'
             THEN value END) AS renewables_share_primary_energy_pct,
    MAX(CASE WHEN metric_key = 'wind_generation_twh'
             THEN value END) AS wind_generation_twh,
    MAX(CASE WHEN metric_key = 'hydro_generation_twh'
             THEN value END) AS hydro_generation_twh,
    MAX(CASE WHEN metric_key = 'solar_generation_twh'
             THEN value END) AS solar_generation_twh,
    MAX(CASE WHEN metric_key = 'other_renewables_generation_twh'
             THEN value END) AS other_renewables_generation_twh,
    MAX(CASE WHEN metric_key = 'renewables_share_electricity_pct'
             THEN value END) AS renewables_share_electricity_pct,
    MAX(CASE WHEN metric_key = 'hydro_share_primary_energy_pct'
             THEN value END) AS hydro_share_primary_energy_pct,
    MAX(CASE WHEN metric_key = 'hydro_share_electricity_pct'
             THEN value END) AS hydro_share_electricity_pct,
    MAX(CASE WHEN metric_key = 'wind_capacity_gw'
             THEN value END) AS wind_capacity_gw,
    MAX(CASE WHEN metric_key = 'wind_share_primary_energy_pct'
             THEN value END) AS wind_share_primary_energy_pct,
    MAX(CASE WHEN metric_key = 'wind_share_electricity_pct'
             THEN value END) AS wind_share_electricity_pct,
    MAX(CASE WHEN metric_key = 'solar_capacity_gw'
             THEN value END) AS solar_capacity_gw,
    MAX(CASE WHEN metric_key = 'solar_share_primary_energy_pct'
             THEN value END) AS solar_share_primary_energy_pct,
    MAX(CASE WHEN metric_key = 'solar_share_electricity_pct'
             THEN value END) AS solar_share_electricity_pct,
    MAX(CASE WHEN metric_key = 'biofuel_production_twh'
             THEN value END) AS biofuel_production_twh,
    MAX(CASE WHEN metric_key = 'geothermal_capacity_gw'
             THEN value END) AS geothermal_capacity_gw
FROM fact_energy
GROUP BY entity, year;

COMMIT;
