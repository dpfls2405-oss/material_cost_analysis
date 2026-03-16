-- ============================================================
-- 채산 재료비율 분석 v2 — Supabase Schema
-- ============================================================

-- 입고실적 (제품별 매출/수량)
create table if not exists receipt_performance (
    month text not null,
    product_id text not null,          -- 단품코드+색상
    product_name text,
    receipt_qty numeric,               -- 입고수량
    sales_amount numeric,              -- 입고금액 (=매출)
    issue_qty numeric,
    issue_amount numeric,
    stock_qty numeric,
    brand text,
    product_category text,
    source_file_name text,
    uploaded_at timestamptz default now(),
    primary key (month, product_id)
);

-- 재료비 (제품별 단위원가)
create table if not exists material_cost (
    month text not null,
    product_id text not null,          -- 코드+색상
    product_name text,
    material_cost numeric,             -- 총자재비 (단위당)
    factory_price numeric,             -- 공장판매가
    manufacturing_cost numeric,        -- 제조원가
    manufacturing_ratio numeric,       -- 제조원가율
    series_name text,
    source_file_name text,
    uploaded_at timestamptz default now(),
    primary key (month, product_id)
);

-- 월별 BOM
create table if not exists bom_monthly (
    month text not null,
    product_id text not null,          -- 단품코드+단품컬러
    material_id text not null,         -- 자재코드+자재색상 (purchase와 동일 키)
    material_code text,                -- 순수 자재코드
    material_color text,               -- 자재색상
    material_name text,
    material_group text,
    usage_type text,                   -- 사용구분
    unit_cost numeric,                 -- 자재단가
    unit_qty numeric,                  -- 소요량
    bom_amount numeric,                -- 금액 (단가×소요량)
    source_file_name text,
    uploaded_at timestamptz default now(),
    primary key (month, product_id, material_id)
);

-- 구매
create table if not exists purchase (
    month text not null,
    material_id text not null,         -- 자재코드+색상
    material_code text,                -- 순수 자재코드
    material_color text,               -- 색상코드
    material_name text,
    vendor_name text,
    purchase_qty numeric,
    purchase_amount numeric,
    account_type text,
    source_file_name text,
    uploaded_at timestamptz default now(),
    primary key (month, material_id, vendor_name)
);

-- 기초재고
create table if not exists inventory_begin (
    month text not null,
    material_id text not null,         -- 자재코드+색상
    material_code text,
    material_color text,
    material_name text,
    begin_qty numeric,
    begin_amount numeric,
    avg_unit_cost numeric,
    unit_name text,
    source_file_name text,
    uploaded_at timestamptz default now(),
    primary key (month, material_id)
);

-- 기말재고
create table if not exists inventory_end (
    month text not null,
    material_id text not null,         -- 자재코드+색상
    material_code text,
    material_color text,
    material_name text,
    end_qty numeric,
    end_amount numeric,
    avg_unit_cost numeric,
    unit_name text,
    source_file_name text,
    uploaded_at timestamptz default now(),
    primary key (month, material_id)
);

-- JIT 자재 목록
create table if not exists jit_materials (
    month text not null,
    material_id text not null,         -- 자재코드+색상
    material_code text,
    material_color text,
    material_name text,
    vendor_name text,
    unit_cost numeric,
    unit text,
    order_policy text,
    production_mgmt_no text,
    source_file_name text,
    uploaded_at timestamptz default now(),
    primary key (month, material_id)
);

-- 업로드 로그
create table if not exists upload_log (
    upload_id bigint generated always as identity primary key,
    data_month text not null,
    dataset_type text not null,
    source_file_name text not null,
    row_count integer not null,
    status text not null,
    message text,
    uploaded_at timestamptz default now()
);

-- 기존 테이블 마이그레이션용 (컬럼 추가)
alter table bom_monthly add column if not exists material_code text;
alter table bom_monthly add column if not exists material_color text;
alter table bom_monthly add column if not exists usage_type text;
alter table material_cost add column if not exists factory_price numeric;
alter table purchase add column if not exists material_code text;
alter table purchase add column if not exists material_color text;
alter table inventory_begin add column if not exists material_code text;
alter table inventory_begin add column if not exists material_color text;
alter table inventory_end add column if not exists material_code text;
alter table inventory_end add column if not exists material_color text;
